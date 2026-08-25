# 03 — 数据模型规格（graph-schema）

> 本文是 `packages/graph-schema` 的完整规格：类型定义、status 传播规则、求值伪代码、anchor 机制、边界 case 表、序列化。写代码以本文为准；改本文须更新 01 决策台账。

## 1. 顶层容器

```ts
interface Project {
  schemaVersion: number          // 当前 = 1（D-14）
  id: string
  name: string
  createdAt: number
  updatedAt: number
  // 全部扁平表，ID 引用，绝不嵌套（D-06）
  blocks: Record<BlockId, Block>
  objects: Record<ObjId, FormalObject>
  ports:   Record<PortId, Port>
  edges:   Record<EdgeId, Edge>
  groups:  Record<GroupId, Group>
}

type BlockId = string   // 统一使用带前缀的稳定 ID，如 "blk_01J…"
type ObjId   = string   // "obj_…"
type PortId  = string   // "prt_…"
type EdgeId  = string   // "edg_…"
type GroupId = string   // "grp_…"
```

## 2. 内容层：Block

```ts
interface Block {
  id: BlockId
  text: string                    // 原始 md 文本，Layer 1 的全部
  parentId: BlockId | GroupId | null   // 空间/嵌套归属
  rect: { x: number; y: number; w: number; h: number }
  z: number                       // 叠放次序
}
```

## 3. 语义层：FormalObject / Port / Edge / Group

```ts
type PortDType = 'number' | 'text' | 'quantity' | 'ref'   // v1 四件套，禁止扩张（D-24）

interface FormalObject {
  id: ObjId
  kind: string                    // 开放字符串：'variable'|'param'|'process'|'formula'…（D-08）
  source: Anchor | null           // 引用内容层文本；孤儿/纯 API 创建的对象可为 null（R 方向）
  props: Record<string, unknown>  // 结构化语义属性：name / dtype / unit / value / latex …
  ports: PortId[]
  parentId: GroupId | null        // 所属 group/subgraph
  eval?: EvalSpec                 // 怎么算（可缺省 = 不求值，仅存在）
}

interface Port {
  id: PortId
  objectId: ObjId
  dir: 'in' | 'out'
  dtype: PortDType
  required: boolean               // required 输入悬空 → undefined 传染（见 §5）
  label?: string
}

interface Edge {
  id: EdgeId
  from: PortId                    // 必须是 out 口
  to: PortId                      // 必须是 in 口
  delay: boolean                  // R-01：true = 读上一 tick 值，不参与拓扑排序（v2 启用）
  violating: boolean              // R-04：穿透 Subgraph 边界的草稿边，虚线渲染
  props: Record<string, unknown>  // R-03：一等公民属性位，v1 恒为空对象，UI 非空才渲染标记
}

interface Group {
  id: GroupId
  kind: 'group' | 'subgraph'      // D-10：group 纯视觉可穿透；subgraph 封装走端口
  parentId: GroupId | null        // 支持任意深度嵌套（D-09）
  ports: PortId[]                 // 仅 subgraph 使用
  sealed?: boolean                // R-05：成品黑箱标记
  rate?: number                   // R-02：multi-rate 预留，v1 全局单 tick 下忽略
}

type EvalSpec =
  | { type: 'manual' }                                  // 人手填值（v1 主力）
  | { type: 'constant'; value: unknown }                // 常量
  | { type: 'builtin'; fn: string }                     // v1 内置纯函数（数值运算）
  | { type: 'plugin'; pluginId: string }                // R-08：未来电池挂载点
```

## 4. Anchor：文本引用机制（D-11 / D-12）

正式对象引用而非包含文本。字符偏移会在编辑后失效，所以用锚点：

```ts
interface Anchor {
  blockId: BlockId
  tokenIds?: string[]   // 主：编辑器维护的稳定 token ID，编辑时跟随
  quote: string         // 备 1：被抓的文本本身（内容指纹）
  prefix: string        // 备 2：前 32 字符
  suffix: string        // 备 3：后 32 字符
}
```

定位流程（每次 `editBlock` 后对受影响块执行）：

1. 有 `tokenIds` → 直接跟随（正常路径）。
2. token ID 失效（粘贴外来文本、格式重建）→ 用 `quote + prefix + suffix` 在块内模糊重定位；唯一命中则更新锚点。
3. 多重命中或零命中 → **对象不删除**，`source` 保留但标 `status: 'orphan'`（对应 D-13 的孤儿对象）；UI 标黄提示，用户可重新框选修复。

跨块抓取：v1 禁止（U-01 有倾向记录）。同一段文本允许多个对象以不同粒度引用（一行 `流量 Q = 3.5 m³/s` 可同时承载变量/数值/单位/赋值四个对象）。

## 5. Status 与传播规则（D-17）

```ts
type Status = 'fresh' | 'stale' | 'undefined' | 'manual' | 'error' | 'orphan'

interface RuntimeError { causedBy: ObjId; message: string }
```

| 规则 | 内容 |
| --- | --- |
| S1 undefined 传染 | 任一 `required` 输入为 undefined → 输出 undefined。悬空不报错（D-13），该支路整体 undefined，其余支路正常求值 |
| S2 manual 阻断 | 手填值不被上游覆盖（即使上游已定义）；**向下游发出 fresh**。这是"上游没定义我先手填、下游照样算"的兑现 |
| S3 error 传染带来源 | 求值失败 → 输出 error，向下游传播时保留 `causedBy` 链，可一路定位到源头 |
| S4 stale 仅懒求值 | 全量 tick 模式下不产生 stale；仅当用户关闭自动求值时，上游变化使下游标 stale |
| S5 orphan 不阻断 | anchor 丢失但对象仍在：`props` 里的值继续有效、照常参与求值，只是失去文本溯源；UI 标黄 |
| S6 status 归属 | status 是运行时派生量（Layer 3），由求值器独占写入；持久化时可选保存最后一次结果作初始显示，但加载后必须重算确认 |

优先级（多规则竞争时）：`error > undefined > manual > stale > orphan > fresh`。

## 6. 求值模型：tick + delay 边（D-16 / D-18 / D-23）

```
function tick(graph, prevState) -> Snapshot:
    E = graph.edges.filter(e => !e.delay)        // delay 边剪掉（R-01，v2 生效）
    order = topologicalSort(graph.objects, E)     // 剩余必为 DAG；成环由 connect 时拦截
    state = {}
    for obj in order:
        inputs = readInputs(obj, prevState)       // delay 输入从 prevState 读
        if obj.eval?.type == 'manual':
            state[obj] = { value: props.value, status: 'manual→fresh 下游' }   // S2
        else if anyRequiredUndefined(inputs):
            state[obj] = { status: 'undefined' }                                // S1
        else if obj.eval == null:
            state[obj] = { status: 'undefined' }  // 无求值声明 = 未定义
        else:
            try:    state[obj] = { value: run(obj.eval, inputs), status: 'fresh' }
            catch e: state[obj] = { status: 'error', causedBy: obj.id }          // S3
        // 剪枝（D-18）：obj 与上游自上次 tick 均未变且上次 fresh → 跳过重算
    pushSnapshot(history.ringBuffer, state)       // D-22 环形缓冲；pin 的快照另存
    return state
```

v1 简化：单 tick 手动/触发式执行（"跑一步"按钮），不跑连续循环；连续 tick 循环属 v2（与 delay 边同批上线）。

## 7. Command 与 Event（graph-commands 契约）

```ts
interface Command {
  v: number                       // Command 自身版本号
  type: string                    // 'createBlock' | 'promote' | 'connect' | …
  payload: Record<string, unknown>
}
// 具体词汇表与语义见 02-architecture §4；每个 Command 必须能提供逆操作或前快照。

type GraphEvent =
  | { type: 'objects-changed'; ids: ObjId[] }
  | { type: 'edges-changed';    ids: EdgeId[] }
  | { type: 'blocks-changed';   ids: BlockId[] }
  | { type: 'status-changed';   ids: ObjId[] }      // 求值器发
  | { type: 'anchor-orphaned';  ids: ObjId[] }      // markdown-layer 发
```

## 8. 边界 case 表（20 条，实现与测试的共同依据）

| # | 场景 | 预期行为 |
| --- | --- | --- |
| 1 | required 输入悬空（未连线） | 对象及其下游闭包 status=undefined；其余支路正常；不报错 |
| 2 | 输出悬空（无人消费） | 无影响，正常求值 |
| 3 | 孤儿正式对象（框丢失/被删） | 对象继续存在并可参与求值；UI 标记；来源见 case 11 |
| 4 | anchor 失配（文本改到认不出） | status=orphan；props 值仍有效；标黄可手动修复（§4 流程） |
| 5 | 同一段文本被多个对象引用 | 各自独立合法；渲染按层级区分高亮（U-01 倾向） |
| 6 | 重叠范围抓取 | 允许（嵌套引用）；重复 promote 同范围 → 提示复用已有对象 |
| 7 | connect 形成环 | 拦截并提示"设为 delay 边？"，默认 yes（D-16） |
| 8 | delay 边的求值 | 不参与拓扑排序；读 prevState（v2 生效，v1 字段存在但不求值） |
| 9 | 上游已定义但用户手填 | manual 优先（S2），下游拿 fresh |
| 10 | 求值抛错 | 该对象 error，下游 error 且全链带 causedBy（S3） |
| 11 | 删除被引用的块 | deleteBlock 先返回"被 N 个对象引用"警告；确认后引用对象 source 置空转 orphan |
| 12 | 编辑块内文本 | anchor 按 §4 三级流程跟随；成功则对象无感 |
| 13 | 穿透 Subgraph 的边 | 允许创建，violating=true，虚线红渲染，求值照常生效，导出/正式化时报警（D-10） |
| 14 | 跨 Group 连边 | 完全自由；Group 对求值不可见 |
| 15 | Subgraph 内外通信 | 必须经 subgraph 端口；内部拓扑对外不可见 |
| 16 | sealed subgraph | 内部只读视角，仅端口契约可交互（R-05，v1 不实现 UI） |
| 17 | tick 历史 | 环形缓冲保留最近 N；pin 的永久保留（D-22） |
| 18 | Command 校验失败 | 拒绝执行并返回结构化错误；图状态零变化；不写入 undo 栈 |
| 19 | 部分 undefined 混合图 | 只污染相关闭包，其余支路照常出 fresh（"允许残缺"的技术兑现） |
| 20 | demote（正式退回死文本） | 删除语义对象与相关边（边删除进 undo 栈），文本一字不动保留 |

## 9. 序列化

- v1：整个 `Project` 序列化为单个 JSON blob，经 `ProjectRepository` 存 IndexedDB（D-29）。
- JSON 顶层必含 `schemaVersion`；加载时校验，不匹配走迁移函数链（R-09，v1 无迁移仅报错提示）。
- 运行时量（tick 中缓存、临时标脏）默认不入存档；`status` 可选存最后一次结果仅用于开屏显示，加载后重算。
- 导出 JSON 快照 = 同一格式的落盘文件（git 友好）；导出 md = Layer 4 单向投影器，不承诺回读无损（D-05）。
