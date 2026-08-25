# 06 — 路线图

> 本文回答"先做什么、后做什么、怎么算做完了"。范围依据见 01，交互细节见 04。
> 总原则：**先验证领域模型，再决定宿主平台；先机制，后 UI 面板；痒了再加，不预支复杂度。**

## 1. 阶段总览

| 阶段 | 目标 | 形态 | 数据 |
| --- | --- | --- | --- |
| **v1 自用 Web 版** | 证明"渐进形式化黑板"的交互与模型成立 | `pnpm dev` → localhost:5173 + PWA | IndexedDB + JSON 导出 |
| **v2 活起来** | 有环的图能跑、历史可查、agent 进场 | 同上（可选桌面壳） | 同上 |
| **v3 生态与分发** | 电池/插件、真分发、桌面壳 | npm + Releases（D-37 三线） | 可迁 SQLite |

## 2. v1 施工步骤与验收

### 步骤 1：骨架（1-2 天）

- 初始化 pnpm monorepo（05 §2 目录）。
- `graph-schema`：把 03 的全部接口 + Zod schema 写进去，能编译、有快照测试。
- `graph-core`：内存对象表 + ID 索引 + add/remove/connect + 环检测，**不碰 React**，纯单测驱动。

**验收**：`graph-core` 单测覆盖 03 §8 边界 case 表中不依赖 UI 的条目（1/2/7/10/11/18/19 等）。

### 步骤 2：产品本体（1-2 周）

- `apps/web`：Vite + React + React Flow + Zustand；三区域布局（04 §1）。
- `graph-commands`：Command Bus + undo/redo；UI 全部写操作走总线。
- `markdown-layer`：块编辑（CodeMirror）+ anchor 三级定位（03 §4）。
- `graph-storage`：IndexedDbProjectRepository + JSON 导出/导入（D-41 三件套同步落实）。
- `graph-runtime`：v1 只做 status 传播 + 单步求值（manual/constant/builtin 纯函数），不跑 tick 循环。

**验收 = v1 最小闭环**（00-charter §成功判据，逐条过）：

```
双击黑板写死文本 ✅ → 框选 ✅ → chip 确认抓成正式对象（出端口）✅
→ 连线（类型校验 + 成环提示）✅ → 手填 manual 值 → 下游 undefined 变 fresh ✅
→ 保存 → 重开 → 加载一致 ✅ → undo/redo 全程正确 ✅ → 导出 JSON 可回导 ✅
```

### 步骤 3：自用期（数周，按痒加点）

- 把自己当第一个真实用户：画 MCM 人员调度、算法研究方向、外勤排班。
- 按痒排序的候补：空格自动布局（U-07）、打组 UI（Group/Subgraph）、orphan 修复交互、md 导出投影。
- 每发现一个文档没写到的边界 case → 补进 03 §8 并回归测试。

### v1 明确不做

tick 循环、delay 边求值、agent、真电池、桌面壳、SQLite、多面板、Rhino 手势、分发打包。全部有编号归属（R 系列 / U 系列），不是遗忘是纪律。

## 3. v2：活起来

| 项 | 内容 | 触发/依据 |
| --- | --- | --- |
| tick 循环 + delay 边 | 有环的图连续跑；R-01 启用 | 画第一张反馈环图时 |
| 历史快照 | 环形缓冲 + pin（D-22/R-10） | 随 tick 同批 |
| 违规边 | Subgraph 封装 + violating 边（D-10/R-04） | 第一次需要封装时 |
| Agent 四步走 | ①手动调 API ②假 agent（固定命令序列）③真模型输出结构化 Command ④插件化 | U-06；权限框见 02 §6 |
| 命令历史面板 | Command 日志可视化（北极星的第一块面板） | agent 进场后需要审计 |

## 4. v3：生态与分发

- 桌面壳（U-05 倾向 Tauri）+ HostBridge 桌面实现（R-06）+ 可选 SQLite 迁移（U-09）。
- python/WASM 电池运行时（R-08）：独立进程异步（U-03 挂起-恢复）。
- 分发三线 + CI（D-37/39）；签名按 D-38 阶梯。
- 插件接口文档化公开（D-40）。

## 5. 北极星（不做承诺，保持方向）

9 区域 15+ 面板的完整工作台（04 §1 所述）、多开小窗、gumball 全形态、菜谱/UML/Aspen 草稿等场景模板、"谁又要上厕所了"级别的实时调度体验。它们的存在意义是给 v1-v3 的每个决策提供方向校验：**任何 v1 决策不得在结构上杀死北极星**（这正是扁平表、Command 总线、HostBridge 笼子存在的原因）。
