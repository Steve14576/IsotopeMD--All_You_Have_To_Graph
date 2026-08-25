# 05 — 技术栈与工程

> 本文回答"用什么工具、仓库怎么摆、怎么跑起来、以后怎么发出去"。决策依据见 01（D-24/28/29/34–41）。

## 1. v1 技术清单（D-34）

| 类别 | 选型 | 说明 |
| --- | --- | --- |
| 语言 | TypeScript（严格模式） | 全生态唯一主语言 |
| 包管理 | pnpm + pnpm workspace | monorepo 最低成本方案 |
| 构建/开发 | Vite | dev server 端口固定 5173 + strictPort（D-41） |
| UI | React 18+ | 只做视图，不持有图状态 |
| 画布 | React Flow（D-28） | MVP；撞墙后换 PixiJS/Konva 属换皮肤（U-08） |
| 视图状态 | Zustand | 只存 UI 态（选择、视口、面板开关）；图数据不在 React 态里 |
| 校验 | Zod | Command/Project 的 schema 校验与类型推导一体 |
| 本地存储 | IndexedDB（Dexie 封装） | v1 存整个 Project JSON blob（D-29） |
| 文本编辑 | CodeMirror 6（首选）或 Monaco | md 块编辑；CodeMirror 的装饰/锚点生态更适合 anchor 机制 |
| md 解析 | remark/unified 系 | 内容层解析与导出投影共用 |
| 测试 | Vitest | graph-core / graph-runtime 纯函数单测为主 |
| PWA | vite-plugin-pwa | manifest + 离线缓存，独立窗口观感（D-27） |

明确不用：后端框架（库形态，D-24）、Electron/Tauri（v1 不套壳）、SQLite（D-29 后置）、Python（插件运行时阶段才出现）、WASM（插件运行方式之一，非架构）、LangGraph/MCP（adapter 层以后）。

## 2. monorepo 目录结构（D-35）

```
IsotopeMD/
├── AGENTS.md                  # AI 协作纪律（已存在）
├── docs/                      # 架构决策真相源（本目录）
├── pnpm-workspace.yaml
├── package.json
├── packages/
│   ├── graph-schema/          # 纯类型 + Zod schema，零依赖
│   ├── graph-core/            # 内存图：索引/增删连/环检测/事件，只依赖 schema
│   ├── graph-commands/        # Command 定义 + Bus + undo/redo
│   ├── graph-runtime/         # tick 求值器 + status 传播
│   ├── graph-storage/         # ProjectRepository 接口 + IndexedDb 实现 + 导入导出
│   ├── markdown-layer/        # md 解析 + anchor 维护
│   ├── plugin-api/            # ComputePlugin 契约（v1 只有接口）
│   ├── agent-api/             # agent 工具集定义（v1 只有接口 + 假实现）
│   └── ui-components/         # 画布/块/面板 React 组件
├── apps/
│   └── web/                   # Vite + React 应用本体（未来桌面壳加载同一产物）
└── examples/                  # 示例项目 JSON（MCM 调度图等，兼作集成测试素材）
```

依赖方向与禁令见 02-architecture §3 与 AGENTS.md。`packages/graph-*` 全部是纯 TS 库，可被未来的 CLI/测试器/桌面端复用。

## 3. 运行方式（开发期 = 使用期）

```bash
pnpm install
pnpm --filter web dev        # → http://localhost:5173（端口锁死，D-41）
pnpm --filter graph-core test
pnpm --filter web build      # 产出 dist/，PWA 可安装
```

本机自用阶段这就是全部形态：不打包、不签名、不部署（D-27/D-37）。

## 4. IndexedDB 三条自保纪律（D-41）

1. `vite.config.ts` 写死 `server: { port: 5173, strictPort: true }`——IndexedDB 绑定 origin，端口一变数据不通。
2. 不用无痕窗口运行（无痕关闭可能清数据）。
3. 导出 JSON 快照按钮置于顶部工具条显眼位置——"清除浏览数据"会连 IndexedDB 一起清；重要草稿随手导一份落盘。

## 5. 渲染层演进路径（D-28 / U-08）

React Flow 是 DOM 渲染，500+ 节点开始掉帧。应对路线已定死：数据模型与渲染库解耦（ui-components 内部适配层），届时换 PixiJS（WebGL）或 Konva（Canvas 2D）+ 视口裁剪，逻辑层不动。触发条件是实测掉帧，不是预测。

## 6. 未来桌面壳（v1 不实施，路线留档）

- 触发条件：需要真文件系统 / 子进程（python 电池）/ git 集成时（U-05）。
- 方式：新增 `apps/desktop`（倾向 Tauri），WebView 加载 apps/web 的同一份产物；补 `host.tauri.ts` 实现 HostBridge 的 fs/exec/llm；其余代码零改动（D-25/26）。
- 届时存储可换 `SQLiteProjectRepository`（同一接口，D-29/U-09）。

## 7. 分发与签名（D-37 / D-38 / D-39，自用阶段不实施，路线留档）

三线分发，全部 $0，一次 `git tag` 由 CI 自动产出：

| 线 | 入口 | 适用 | 签名问题 |
| --- | --- | --- | --- |
| A 源码 | `git clone → pnpm i → pnpm dev` | 自己 / 会折腾的人 | 无 |
| B 安装包 | GitHub Releases（Actions matrix 三平台构建） | 普通用户 | 无签名，双击可能弹一次窗，README 写两行绕过步骤 |
| C npm | `npx isotope-md` 拉起（GUI 可住浏览器 localhost） | 开发者用户 | **完全免签**：npm 通道不触发 SmartScreen/Gatekeeper 的两个检查条件（浏览器下载标记 + 图形双击）；Node-RED/n8n/ComfyUI 同类先例 |

签名升级阶梯：$0（现状）→ $99/年 Apple Developer（第一个值得买的）→ Windows OV/EV 证书（有真实分发量再说；且 SmartScreen 看声誉，新证书前期照样弹窗）。

CI：GitHub Actions 公开仓库免费不限时；`tauri-apps/tauri-action` 与 electron-builder workflow 均为现成模板。个人自用阶段不开 CI。

## 8. 版本与备份

- 源码：git 管理，`docs/` 与代码同库（架构决策随代码演进）。
- 作品数据：v1 靠 IndexedDB + 手动导出 JSON 快照；快照文件可单独入 git 或云盘做历史追溯（"过程即结果"的 MCM 调度史就是这么留档的）。
- 数据格式版本：`Project.schemaVersion`，变更流程见 03 §9 与 R-09。
