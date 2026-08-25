# 02 — 架构总览

> 本文回答"模块怎么切、边界在哪、数据怎么流"。决策依据见 01，数据结构细节见 03。

## 1. 四层数据视图（D-04 / D-05）

```
┌────────────────────────────────────────────────────────┐
│ Layer 4  视图与导出层                                    │
│   md 渲染 / 图渲染 / 表格渲染（只读投影，可多种）           │
│   导出器：md 快照（给 Obsidian/git）、JSON 快照（git 友好） │
├────────────────────────────────────────────────────────┤
│ Layer 3  运行时层                                        │
│   status 派生值、求值缓存、tick 历史环形缓冲               │
│   写权限：只有求值器；Agent/UI 一律禁止（D-20）            │
├────────────────────────────────────────────────────────┤
│ Layer 2  语义层 —— 唯一真相源                             │
│   FormalObject / Port / Edge / Group（扁平表 + ID 引用）  │
│   写权限：只能走 Command API（schema 校验 + 事务 + undo）  │
├────────────────────────────────────────────────────────┤
│ Layer 1  内容层                                          │
│   Block：原始 md 文本 blob（死文本的家）                   │
│   写权限：人 + Agent 自由读写（改坏了只是文本乱，图不崩）    │
└────────────────────────────────────────────────────────┘
```

关键不变量：

- 正式对象**引用**内容层文本（Anchor），不包含文本（D-11）。
- 死块只有 Layer 1；promote（抓块）= 在 Layer 2 建立语义对象并引用 Layer 1 的一段文本。
- Layer 2 的 invariant（端口连通、外键完整、schema 合法）由 Command API 保证，不靠调用方自觉（D-19）。

## 2. 形态：库，不是服务（D-24）

```
浏览器标签页（单进程）
├── React UI（apps/web）
├── graph-core / graph-runtime ← npm 包，同进程函数调用
├── markdown-layer
└── IndexedDB（经 ProjectRepository 接口）
```

v1 **没有**后端服务器、没有 HTTP/WebSocket 内部通信。`graph.connect(a, b)` 就是一行函数调用。

服务化的唯一合法触发条件（三个信号，一个都没出现前服务化是纯负债）：

1. 想做 TUI/CLI 与 GUI 同时操作同一张图；
2. agent 要跑在独立进程（长任务不占浏览器标签）；
3. 想从手机访问电脑的图。

单向性论证：库 → 服务 = 薄包装（函数包成 endpoint，一个周末）；服务 → 库 = 重构（拆网络调用改到到处都是）。所以永远先库。

## 3. 模块划分与依赖方向（D-35）

```
apps/web                     ← React 应用本体（也是未来桌面壳的内容）
  │ 依赖
  ▼
ui-components                ← 画布/块/面板/快捷键（React 组件，可依赖 graph-* 全部）
  │
  ├─► graph-commands         ← Command 定义 + Command Bus + undo/redo 栈
  ├─► graph-runtime          ← tick 求值器、status 传播
  ├─► markdown-layer         ← md 解析、anchor 维护、意图识别钩子
  ├─► graph-storage          ← ProjectRepository 接口 + IndexedDbProjectRepository
  ├─► plugin-api / agent-api ← 电池契约 / agent 工具集（v1 只留接口与假实现）
  │
  ▼ 全部依赖（反向禁止）
graph-core                   ← 内存对象图：add/remove/connect、ID 索引、环检测、事件
  ▼
graph-schema                 ← 纯类型定义：Block/FormalObject/Edge/Port/Group/Status/Command
```

依赖纪律（绝对）：

- 箭头只能向下。`graph-schema` 零依赖；`graph-core` 只认识 schema 里的概念，不得 import React/Electron/Tauri/agent 框架/数据库驱动。
- 任何模块不得绕过 `graph-commands` 直接 mutate 图状态；查询可以直接走 `graph-core` 的只读 API。
- 外部框架（LangGraph、MCP、任何 LLM SDK）只能出现在 adapter 文件或 `agent-api` 的可选实现里（D-21）。

## 4. 命令流（写路径，一切写操作的唯一通道）

```
来源：用户交互 / Agent tool call / 未来的 CLI / 插件
   │  生成可序列化 Command（含版本号）
   ▼
Command Bus
   ├── schema 校验（非法直接拒绝，返回结构化错误）
   ├── invariant 检查（如：connect 成环 → 触发 D-16 的 delay 边提示）
   ├── 应用到 graph-core（产生逆操作/快照入 undo 栈）
   └── 发出 Event（Changed: {scope, ids}）
   ▼
订阅方：React 视图重渲染 / 命令历史日志 / 求值器标脏
```

由此免费获得：统一 undo/redo、可审计的 agent 行为（喂给未来的命令历史面板）、UI 与 agent 行为一致性（D-19）。

核心 Command 词汇表（v1 最小集，签名以 03 为准）：

```
createBlock(text, parentId?, rect?)        → BlockId
editBlock(blockId, newText)                → void     // 自动触发 anchor 重定位
deleteBlock(blockId)                       → void     // 被引用时先警告（case 11）
promote(blockId, anchor, kind, props)      → ObjId    // "抓块"
demote(objId)                              → void     // 正式退回死文本（对象删除，文本保留）
setProps(objId, partialProps)              → void
setManualValue(objId, value)               → void     // status → manual
connect(fromPortId, toPortId)              → EdgeId   // 成环 → 提示 delay
disconnect(edgeId)                         → EdgeId⁻¹
group(objIds, kind: 'group'|'subgraph')    → GroupId
move(objIds, parentId?)                    → void
```

## 5. 平台差异：五条缝与两个笼子（D-25 / D-26）

浏览器与桌面（未来）能力不同的五个位置，全部收敛到两个接口，其余代码只查能力、不判环境：

| 缝 | 浏览器（v1） | 桌面（未来） | 收口 |
| --- | --- | --- | --- |
| ① 文件系统 | 只能下载/上传 | 任意路径读写 | `host.fs.*` |
| ② 存储 | IndexedDB | SQLite/项目文件 | `ProjectRepository` |
| ③ 子进程 | ❌（python 电池全废） | ✅ | `host.exec()` |
| ④ 网络 | CORS 限制、API key 暴露 | 无限制、key 存后端 | `host.llm()` |
| ⑤ 窗口件 | 无系统菜单/全局快捷键/真多窗口 | 有 | 暂不封装，需要时加 |

接口骨架：

```ts
interface ProjectRepository {
  load(id: string): Promise<Project>
  save(project: Project): Promise<void>
  list(): Promise<ProjectSummary[]>
}

interface HostBridge {
  capabilities: Set<'fs' | 'exec' | 'nativeDialog' | 'globalShortcut' | ...>
  fs: { exportFile(data, name): Promise<void>; /* 桌面版再实现 read/write */ }
  // exec / llm 等：v1 只声明不实现
}
```

v1 只需 `host.browser.ts`（降级实现）；`host.tauri.ts` 现在不存在。**GUI 永远一份代码**；如果发现自己在写"浏览器版画布"和"桌面版画布"两份东西，架构已被写歪，立即收回。

## 6. Agent 的位置（D-20 / D-21）

Agent 是"高级用户"，不是 root：

| 层 | Agent 权限 |
| --- | --- |
| Layer 1 内容层文本 | ✅ 自由读写（agent 是语言模型，写自然语言是它的本职） |
| Layer 2 语义对象 | ⚠️ 只能调 Command API（promote/connect/setProps…，schema 校验 + undo） |
| Layer 2 拓扑改动 | ⚠️ 走 API 且建议弹确认 |
| Layer 3 运行时字段（status/lastEval） | ❌ 禁止（写它 = 伪造计算结果） |

Agent 的快速建图能力来自**语义密度而非文本**：`insertTemplate('heat-conduction-1d')` 一次调用生成 8 节点 6 边，而不是读几千 token 的 md 再解析。预制模板是 agent 的高层词汇表（R-08 方向）。

v1 不实现真 agent；验证路径：手动调 Command API → 假 agent（返回固定命令序列）→ 真模型输出结构化 Command → 插件化（见 06-roadmap）。

## 7. 与外部世界的边界

- **导入/导出**：JSON 全图快照（双向，git 友好的真相副本）；md 快照（单向投影，"导出即快照"，明确告知不保证无损回读）。
- **未来电池运行时**：Python = 独立进程异步插件；WASM = 沙箱纯函数插件；统一实现 `ComputePlugin { manifest(); evaluate(input) → output }` 契约（R-08）。
- **MCP**：外部适配层（外部 agent → MCP Adapter → Command API），不是内部模型。
