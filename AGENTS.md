# AGENTS.md — AI 协作纪律

本文件是本项目对 AI（vibe coding 协作者）的架构纪律书。**写任何代码之前，先读 `docs/`，重点是 `docs/01-decisions.md`（决策台账）与 `docs/03-data-model.md`（数据模型）。** 当你的倾向与本文件冲突时，以本文件为准；当本文件与用户的新指示冲突时，先与用户确认，改完本文件再改代码。

## 项目一句话

IsotopeMD 是一个**可执行的渐进形式化黑板**：以自由文本为入口、以渐进形式化图为核心、支持状态传播与可选求值的个人外置思维系统。

## 绝对边界（模块依赖方向）

- `packages/graph-schema`、`graph-core`、`graph-commands`、`graph-runtime`、`graph-storage`、`markdown-layer`、`plugin-api` **不得** import：React、Electron、Tauri、任何 Agent 框架、任何 UI 组件库、任何具体数据库驱动。
- `graph-core` 只允许知道这些概念：Object / Slot / Edge / Group / Block / Doodle / Command / Event / Value / Status。
- React 只能通过 Command Bus 修改图，禁止直接改图模型内部状态。
- UI 状态与领域状态分开：图数据永远不在 React 组件里安家。
- 所有平台差异（文件系统 / 存储 / 子进程 / 网络 / 窗口件）只允许出现在 `HostBridge` 的实现文件里（`host.browser.ts`，将来的 `host.tauri.ts`），其他任何地方不得出现。

## 八条纪律

1. 图模型不得定义在 React 组件中。
2. 所有写操作必须变成 Command（可序列化、有版本号）。
3. 所有 Command 必须可撤销（自带逆操作或快照）。
4. UI 和 Agent 共用同一套 Command API，不存在第二套写路径。
5. 数据格式必须携带 `schema_version`。
6. 插件 / Agent 不得直接访问存储层，只能通过 Command API 与查询 API。
7. 外部框架（LangGraph、MCP 等）只能出现在 adapter 层，不进入核心。
8. 核心对象不得依赖任何特定 Agent 框架。

## v1 四条已定决策（不再讨论，详见 D-24）

1. **库形态，不是服务形态**：graph-core 是 npm 包，同进程函数调用。禁止引入 localhost 后端服务器、HTTP/WebSocket 内部通信。
2. **槽类型四件套**：`number | text | quantity | ref`。禁止发明第五种。
3. **v1 快捷键子集**：左键选/框选、中键平移、滚轮缩放、右键菜单、空格整理。不做 Rhino 式右键重复上一步。
4. **Web 端即成品形态**：含 PWA。不做桌面壳（Tauri/Electron 延后）。

## 禁止清单

- 禁止：`if (isDesktop)` / `if (window.__TAURI__)` 散落各处。只允许 `host.capabilities.has(...)` 查询能力。
- 禁止：把 md 当存储格式（把语义结构塞进 frontmatter 或自定义 md 语法）。md 只是内容层文本与导出投影。
- 禁止：Agent 写 `status`、`lastEval` 等运行时字段（求值器独占，写了等于伪造计算结果）。
- 禁止：在正式块与原文之间建立任何形式的"实时跟随"锚定（双向同步/tokenId/指纹重定位）。正式块是原文的独立副本，关联只有 origin 软回链（见 `docs/03-data-model.md` §4）。
- 禁止：空格键同时触发"重新布局"和"后端整理"两件事。空格只触发重新布局，后端整理在 idle 时静默做。
- 禁止：在 v1 实现 delay 边求值、multi-rate 子图、异步电池——它们只在数据结构里预留字段（见 R 系列编号）。

## 文档优先约定

- `docs/` 是架构决策的唯一真相源。
- 任何涉及架构决策的代码改动：先改 `docs/` 对应文档（更新或新增决策编号），再改代码。
- 决策编号 D-xx（已定）/ U-xx（未决）/ R-xx（预留字段）全局唯一；同一决策原地迭代、复用旧编号，禁止另起重复编号。
- 拿不准某件事是否已定：查 `docs/01-decisions.md`，里面没有就当未决，先问再动。
