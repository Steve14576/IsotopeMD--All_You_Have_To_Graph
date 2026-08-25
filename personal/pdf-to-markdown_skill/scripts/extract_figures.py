"""Caption-anchored figure extractor for PDF -> Markdown (mechanical only).

Usage:
    uv run --with pymupdf python extract_figures.py <pdf_path> [out_dir]

Produces in out_dir (default: <pdf_stem>_assets):
  - figure_NN.png : figure cropped from directly above its "Figure N:" caption
  - page_NN.png    : full-page render (fallback)
  - manifest.json  : {figure_no: {page, caption, file, size}}

Design notes:
  * Locates "Figure N:" caption blocks, crops the region ABOVE each caption
    (column-aware: full-width caption -> both columns, else single column).
  * Over-crop guard: when the crop height approaches a full column, re-crops
    using the union of vector drawings + image blocks above the caption.
  * This is mechanical pixel cropping only; typesetting and placeholder
    placement are done manually per the skill's core principle.
"""

import json
import os
import re
import sys

import fitz  # PyMuPDF

DPI = 220
CAP_RE = re.compile(r"^Figure\s+(\d+)\s*[:.]", re.I)


def block_text(b: dict) -> str:
    return " ".join(
        "".join(s["text"] for s in line.get("spans", []))
        for line in b.get("lines", [])
    ).strip()


def find_captions(page):
    res = []
    for b in page.get_text("dict").get("blocks", []):
        if b.get("type") != 0:
            continue
        t = block_text(b)
        m = CAP_RE.match(t)
        if m:
            res.append((int(m.group(1)), t, fitz.Rect(b["bbox"])))
    return res


def column_bounds(cap, pw):
    if (cap.x1 - cap.x0) > 0.55 * pw:  # full-width caption => spans both columns
        return 0.0, pw
    cx = (cap.x0 + cap.x1) / 2
    return (0.0, pw / 2) if cx < pw / 2 else (pw / 2, pw)


def crop_above(page, cap):
    pr = page.rect
    x0, x1 = column_bounds(cap, pr.width)
    top = 0.0
    for b in page.get_text("dict").get("blocks", []):
        if b.get("type") != 0:
            continue
        br = fitz.Rect(b["bbox"])
        if br.y1 >= cap.y0 - 1:
            continue
        if br.x0 < x1 and br.x1 > x0:  # overlaps the column
            top = max(top, br.y1)
    y0 = max(0.0, top + 1)
    y1 = cap.y0 - 1
    if y1 - y0 < 25:  # fallback: from page top
        y0 = 0.0
    clip = fitz.Rect(x0, y0, x1, y1)
    if clip.is_empty or clip.height < 20 or clip.width < 80:
        return None
    return clip


def recrop_by_drawings(page, cap, fpath):
    """Re-crop using union of drawings + image blocks above caption (over-crop guard)."""
    pr = page.rect
    x0, x1 = column_bounds(cap, pr.width)
    rects = []
    for d in page.get_drawings():
        r = d.get("rect")
        if r:
            rr = fitz.Rect(r)
            if rr.width > 5 and rr.height > 5 and rr.x0 < x1 and rr.x1 > x0 and rr.y1 < cap.y0:
                rects.append(rr)
    for b in page.get_text("dict").get("blocks", []):
        if b.get("type") == 1:
            br = fitz.Rect(b["bbox"])
            if br.x0 < x1 and br.x1 > x0 and br.y1 < cap.y0:
                rects.append(br)
    if not rects:
        return False
    u = fitz.Rect(
        min(r.x0 for r in rects),
        min(r.y0 for r in rects),
        max(r.x1 for r in rects),
        max(r.y1 for r in rects),
    )
    mat = fitz.Matrix(DPI / 72, DPI / 72)
    page.get_pixmap(matrix=mat, clip=u, alpha=False).save(fpath)
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: extract_figures.py <pdf_path> [out_dir]")
        return 1
    pdf = sys.argv[1]
    stem = os.path.splitext(os.path.basename(pdf))[0]
    out = sys.argv[2] if len(sys.argv) > 2 else stem + "_assets"
    os.makedirs(out, exist_ok=True)

    doc = fitz.open(pdf)
    mat = fitz.Matrix(DPI / 72, DPI / 72)

    for i, page in enumerate(doc, 1):  # full-page renders (fallback)
        page.get_pixmap(matrix=mat, alpha=False).save(os.path.join(out, f"page_{i:02d}.png"))

    manifest = {}
    for pno, page in enumerate(doc, 1):
        for num, txt, cap in find_captions(page):
            entry = {"page": pno, "caption": txt}
            clip = crop_above(page, cap)
            if clip is None:
                entry["file"] = f"page_{pno:02d}.png"
            else:
                fn = f"figure_{num:02d}.png"
                fpath = os.path.join(out, fn)
                page.get_pixmap(matrix=mat, clip=clip, alpha=False).save(fpath)
                # over-crop guard: if crop ~ full column, re-crop by drawings
                if int(clip.height * DPI / 72) > 0.6 * page.rect.height * DPI / 72:
                    recrop_by_drawings(page, cap, fpath)
                try:
                    pm = fitz.Pixmap(fpath)
                    entry["size"] = [pm.width, pm.height]
                except Exception:
                    entry["size"] = None
                entry["file"] = fn
            manifest[num] = entry

    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"figures: {sorted(manifest)}")
    for n in sorted(manifest):
        e = manifest[n]
        print(f"  Figure {n}: {e.get('file')} size={e.get('size')} page={e['page']}")
    doc.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
