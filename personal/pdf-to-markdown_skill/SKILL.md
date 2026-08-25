---
name: pdf-to-markdown
description: Convert PDF documents (especially academic papers) into high-quality, readable Markdown with extracted figures, LaTeX equations, and proper tables. Use when converting PDFs to Markdown (especially research papers with figures/tables/equations), or when re-typesetting already-converted documents. Enforces a manual-first workflow — no automated reflow or auto-injected images.
---

# PDF to Markdown (manual-first)

将 PDF（尤其是学术论文）转换为可流畅阅读的 Markdown：提取原图、公式转 LaTeX、表格转 markdown 表格、图占位符按正文位置对应。

## 核心原则（不可妥协）

- **排版必须手工**：通读全文 → 逐段手写 Markdown。禁止用脚本自动 reflow、自动注入图占位符。
- **脚本只做机械裁剪**：仅允许用于"按已定位图注裁剪图区"这类像素级操作。
- **图—占位符对应必须手工**：由人阅读正文决定每张图插在哪个位置，不可用正则自动注入。

> 自动 reflow 的典型翻车：Figure 描述文字被误判成公式塞进 `\[..\]`；ALL CAPS 章节标题没转 `#`；表格被压成"每格一行"。这些都必须手工避免。

## 工作流

### Phase 0：环境
- Python 依赖用 uv：`uv run --with pymupdf python <script>`
- PDF 解析默认用 PyMuPDF（fitz）

### Phase 1：通读全文
取全文（`page.get_text("text")` 或 `get_text("dict")`），**人工通读**，理清：标题/作者/摘要、章节层级、公式位置与编号、表格结构、每张 Figure 的图注与所在页。

### Phase 2：图片提取（机械，可用脚本）
运行 `scripts/extract_figures.py <pdf> [out_dir]`，它做：
1. 按 `Figure N:` 图注锚定，裁剪图注正上方图区（列感知：全宽图注→跨双列，窄图注→单列）。
2. 过裁保护：当裁剪高度≈整列时，改用该列图注上方的"绘图/图像簇并集"二次限定裁剪。
3. 渲染整页 PNG 作为回退；输出 `manifest.json`（图号→文件→尺寸→页号）。

裁剪后**人工核对**尺寸（无法直接看图时的 sanity check）：宽>150px、高>80px 且 <整页为合理；过高（≈整列/整页）=过裁。

### Phase 3：手工排版（逐段手写）
- 标题层级：`#` 文档标题、`##` 章节、`###` 小节/附录
- 段落：合并硬换行为流式段落；去行内连字符断词
- 公式：块级 `\[...\]`（带 `\tag{N}`），行内 `$...$`
- 表格：转 markdown 表格；prompt/代码示例用 ```text 代码块保真
- 图占位符：`![Figure N：中文说明](assets_dir/figure_0N.png)`，按正文位置一一插入
- 路径：assets 目录用**无空格/括号**的简洁名（如 `paper_assets/`），避免 `![](...)` 被括号截断

### Phase 4：核对
- grep 图引用数 == 素材文件数，且一一对应
- 抽查公式块、表格、标题渲染是否正常

## 大文件分块写入
- 首段用 Write；后续段用 SearchReplace，以**唯一锚点**（如某脚注行 + `---`）定位追加。
- 避免 Write append 的 `continuation_context` 不匹配（文件被覆写后末尾会变）；若要用 append，先 Read 末尾取准确上下文。

## 高频踩坑
详见 [reference.md](reference.md)。一句话版：
- 自动 reflow 误判公式/标题/表格 → 手工排版
- 绘图簇聚类裁图漏图/过裁 → 用图注锚定裁剪
- assets 路径含空格/括号 → 重命名简洁名
- 图注正则误匹配正文引用 → 仅匹配 `^Figure\s+\d+\s*[:.]`
- 双栏论文裁图未按列 → 按图注宽度判断列边界
