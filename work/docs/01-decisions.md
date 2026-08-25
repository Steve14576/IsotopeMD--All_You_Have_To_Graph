# 01 — 决策台账：定了什么，没定什么

> 本项目所有架构决策的唯一清单。**做任何新决定之前先查这里。**
> 编号全局唯一：D = 已定（Decided），U = 未决（Undecided），R = 预留字段/能力（Reserved，数据结构留位、实现延后）。
> 出处一栏指向前次设计推演的主题（完整推演过程见 `work/Former_Chat_Refs/chat1_claudeopus5_1.md`）。

---

## 一、已定决策（D 系列）

### 定位层

| # | 决策 | 理由 | 出处 |
| --- | --- | --- | --- |
| D-01 | 定位为**可执行的渐进形式化黑板**，个人/小团队外脑，不是平台 | "应用层统一元工具"在历史上反复失败（Yahoo Pipes/Quartz Composer）；个人自用场景可两三周出 MVP | 需求澄清轮 |
| D-02 | 差异化根基 = 渐进形式化（死块→抓块→正式块），允许残缺草稿部分求值 | 现有工具（Scratch/CubeMX/所有 dataflow 工具）都不允许"还没想清楚"状态存在，这是它们缺的一半 | 架构评审轮 |
| D-03 | 节点内严谨性可选：专业性靠外接电池（python 脚本/预制节点），核心不承诺专业计算 | 与 Aspen/Simulink 反着来；草稿定位；真 COMSOL 级计算难在网格/求解器不在图结构 | 需求澄清轮 |

### 数据模型层

| # | 决策 | 理由 | 出处 |
| --- | --- | --- | --- |
| D-04 | **四层分离**：内容层（md 死文本）/ 语义层（唯一真相源，只能走 API）/ 运行时层（status/缓存，求值器独占）/ 视图与导出层（只读投影） | md 是线性文本、表达不了带属性的图；md 当真相源 = 改残即碎（Obsidian 的病根）；agent 改 Layer1 文本自由、改 Layer2 必须受控 | 存储讨论轮 |
| D-05 | md 是**输入法不是文件系统**：编辑态 100% md；存储态不用 md；导出态是单向 md 快照（不保证无损回读） | "万物皆 md"的四个诱人点（打字流/agent 快/可读/互通）没有一个需要 md 当存储 | 存储讨论轮 |
| D-06 | 数据结构 = **扁平表 + ID 引用 + parent 指针**（Scratch/Blender 模式），不用嵌套 JSON | 支持任意嵌套而不撑爆；md 表达不了图；"块在哪一级切成文件"这种伪问题随之消失 | 存储讨论轮 |
| D-07 | **边是一等公民**：id / type / props / status / delay 俱全；但 UI 默认哑线，仅当 props 非空时渲染标记 | "谁替谁"这类关系自带状态；主流 dataflow 工具全是哑管道，本项目向属性图方向偏离是自觉的 | 边地位讨论轮 |
| D-08 | 一切皆块、**结构同构，差异只在 promote 时声明的契约**：`kind` 是开放字符串（非封闭枚举）+ ports 契约 + eval 声明 | "你敢定义我就敢跑"的精确化；用户可自定义 kind，无需预设所有类型 | 存储讨论轮 |
| D-09 | **不分单件/装配体**：Group/Subgraph 递归嵌套统一该概念；`sealed` 标记区分"成品黑箱"与"正在拼接的容器" | SolidWorks 的三分混乱是历史遗留+内存补丁，本项目扁平表+parent 天然免疫 | 元数据轮 |
| D-10 | **Group 与 Subgraph 分开**：Group 纯视觉（可穿透连边、不影响求值）；Subgraph 是封装（必须走端口）；允许违规穿透边存在但标 `violating: true` 虚线渲染 | 对应 Figma-group vs Blender-node-group；草稿需要"临时拉一条穿透线"的自由，哲学是不阻止只标记 | 完备度盘点轮 |
| D-11 | 正式对象**引用文本而非包含文本**（Anchor 机制），同一段文本可被多个对象以不同粒度引用 | 一行 `流量 Q = 3.5 m³/s` 可抓出变量/数值/单位/赋值四个对象；包含 = 复制四份 = 同步地狱 | 存储讨论轮 |
| D-12 | Anchor = tokenId 优先跟随 + quote/prefix/suffix 指纹降级重定位；彻底失配 → 对象不删除，标 `status: orphan` | 裸字符偏移一编辑就全崩；这是 Google Docs/Hypothesis 的标准解法 | 存储讨论轮 |
| D-13 | 孤儿正式对象、悬空出/入度**允许存在**，草稿必须允许残缺 | 悬空不是错误，是 undefined 状态的一支，图仍能部分求值 | 架构评审轮 |
| D-14 | 数据格式从第一天起携带 `schema_version`（v1 = 1），迁移函数随版本演进 | schema 必改，不留版本号 = 老文件全废；Blender DNA 机制的最低配版 | 元数据轮 |
| D-15 | 抓块语义：**正式对象抓完依旧正式，非正式文本抓完依旧非正式**；抓取 = 在语义层建对象并引用文本，不改变文本本身的形式化程度 | 渐进形式化的自洽性 | 需求原文 |

### 执行与求值层

| # | 决策 | 理由 | 出处 |
| --- | --- | --- | --- |
| D-16 | **必须支持环**；实现方式 = **tick + delay 边**（Simulink UnitDelay 模型）：delay 边不参与拓扑排序、读上一 tick 值；建边成环时提示设为 delay 边（默认 yes） | 人员调度/反馈环/循环物流天然有环，纯 DAG 工具出局；不动点迭代对草稿过重；tick 同时就是时序，且 tick 快照序列 = "过程即结果"的兑现 | 完备度盘点轮 |
| D-17 | status 六态：`fresh / stale / undefined / manual / error / orphan`；传播规则：undefined 传染、**manual 阻断且向下游发 fresh**、error 传染并携带 `causedBy`、stale 仅懒求值时出现、orphan 不阻断求值（UI 标黄） | manual 阻断是"上游没定义我先手填、下游照样算"的技术兑现，是半正式黑板能跑的关键 | 完备度盘点轮 |
| D-18 | v1 求值触发 = 全量 tick + status 标脏剪枝（fresh 且上游未变则跳过）；真增量脏标记后置 | 实现成本接近全量、性能接近增量的中间态 | 完备度盘点轮 |
| D-19 | **所有写操作走 Command API**：UI / Agent / CLI / 插件共用一套；每个 Command 可序列化、有版本、可 undo；invariant 由 API 保证不靠自觉 | CAD 领域标准做法（Rhino API / VSCode WorkspaceEdit）；agent 是"高级用户"不是 root；命令历史面板免费获得 | 存储讨论轮 |
| D-20 | Agent 权限分层：内容层文本自由读写 ✅；语义对象只能走 API ⚠️；拓扑改动走 API 且建议需确认 ⚠️；status/lastEval 等运行时字段禁止 ❌ | agent 改语义层的正确方式是 `promote/connect/setProps` 这类 tool call（几十 token、schema 校验），不是改 md（几千 token、没人拦错） | 存储讨论轮 |
| D-21 | Agent 本体不进核心：不依赖 LangGraph 等任何框架；MCP 只是外部适配层（外部 agent 发现/调用工具的协议），不是内部模型 | 防"技术协议传染"；内部协议自定义（Command 联合类型），对外以后适配 MCP/HTTP/CLI | 技术栈轮 |
| D-22 | tick 历史存储 = 环形缓冲区（最近 N tick）+ 手动 pin 永久保存（类 Rhino 命名视图 / git tag） | 全量快照会爆炸；过程即结果要求历史可查 | 完备度盘点轮 |
| D-23 | v1 全局单一 tick，Subgraph 不得有独立时钟；v1 求值器只做同步纯函数（数值运算），异步电池/挂起恢复后置 | multi-rate 复杂度陡增；但异步挂起/恢复能力要在接口层从底层设计进去（见 R-07） | 完备度盘点轮 |

### 架构与形态层

| # | 决策 | 理由 | 出处 |
| --- | --- | --- | --- |
| D-24 | **v1 四条**（写入 AGENTS.md）：① 库形态不是服务形态（graph-core 是 npm 包，同进程调用，禁止 localhost 内部服务器）② 端口类型四件套 `number \| text \| quantity \| ref` ③ v1 快捷键子集 ④ Web 端 + PWA 即成品形态 | ① 服务化只在多客户端并发连引擎时才需要（三个信号：TUI 并存/agent 独立进程/手机访问），且库→服务是薄包装、服务→库是重构，单向性决定先库；② 不定最小集 AI 会发明二十种类型；③ Rhino 右键手势需精细状态机，不值得挡路；④ 桌面壳的收益（双击/真 fs/子进程/分发）本机自用阶段一个都用不上 | 收官轮 |
| D-25 | GUI 永远一份代码；平台分支只存在于 HostBridge 实现文件；纪律 = 查询能力（`host.capabilities.has(...)`）而不是判断环境（`if isDesktop`） | Electron/Tauri 跑的是同一份 React 代码，画布交互零差异；差异只在五条缝 | 公共部分轮 |
| D-26 | **五条缝关进两个接口笼子**：① 文件系统 ② 存储 ③ 子进程 ④ 网络（CORS/API key）⑤ 窗口件 → `HostBridge`（fs/exec/llm…）+ `ProjectRepository`（load/save/list） | 干净的标志不是没有差异，而是差异被关进笼子；v1 只需接口名 + 浏览器降级实现 | 公共部分轮 |
| D-27 | Web 版不是前身而是**永久第一形态**；桌面壳 = 以后给同一份应用套皮（Tauri WebView 加载同一个 app）；PWA（manifest.json）提供独立窗口/图标/双击启动的八成桌面观感 | 不存在"web 版做完扔掉重写"；先壳后内核是最经典死法 | 公共部分轮 |
| D-28 | 渲染层：v1 用 React Flow（上手最快、教程最多）；逻辑层与渲染库解耦，节点数撞墙（500+ 掉帧）后换 PixiJS/Konva 属于换皮肤 | DOM 渲染的性能天花板已知且可预见，现在不解决但路线定死 | 技术栈轮 |
| D-29 | 存储演进：v1 = JSON 全图 blob 进 IndexedDB（或项目文件夹 JSON）；模型稳定后再迁 SQLite；导出 JSON 快照可进 git，SQLite 本体不进 git | 不让数据库选择反过来影响领域模型；内存模型不变则序列化层可换实现 | 元数据轮 + 技术栈轮 |
| D-30 | v1 UI 范围 = **三区域**：中央画板 + 右侧单一属性/agent 面板 + 底部命令行；北极星里那 9 区域 15+ 面板全部延后 | 面板间状态同步是指数级复杂度，画面清晰 ≠ 机制清晰；SolidWorks 是几百人年 | 架构评审轮 |
| D-31 | 抓块的位置意图识别（左输入右输出）**只作默认值提示**，抓取瞬间弹轻量确认 chip（`[输入][输出][参数]`，默认高亮猜测项，回车确认，方向键改） | 嵌套时位置歧义（对父容器在左、对祖父在右）；全自动改错成本 > 确认一次成本 | 架构评审轮 |
| D-32 | 空格键绑定**重新计算布局**，不绑定"整理后端"；后端碎片整理在 idle 时静默做（requestIdleCallback） | 卡顿来源是布局算法+重绘，不是数据结构丑；两件事分开否则按一次空格触发两个无关开销 | 架构评审轮 |
| D-33 | v1 键位最小集：左键选/框选、中键平移、滚轮缩放、右键菜单、空格整理；Rhino 式"右键重复上一步"+ 修饰键手势全部留 v2 | 需要精细命中测试+状态机，v1 阶段消耗过多精力 | 架构评审轮 + 收官轮 |

### 技术与分发层

| # | 决策 | 理由 | 出处 |
| --- | --- | --- | --- |
| D-34 | 核心技术栈：TypeScript 全生态 + pnpm monorepo + React + Vite + React Flow + Zustand/Zod + IndexedDB（Dexie）+ md 解析 + CodeMirror/Monaco（如需） | 图编辑器/编辑器组件生态 Web 最全；Flutter/Kotlin 要重造"VSCode+Figma+ReactFlow+Obsidian"的交互基建；Python 降级为未来插件运行时 | 技术栈轮 |
| D-35 | monorepo 分包：`graph-schema / graph-core / graph-commands / graph-runtime / graph-storage / markdown-layer / plugin-api / agent-api / ui-components` + `apps/web`；graph-core 零外部依赖纪律 | Orange 三分库（canvas-core/widget-base/本体）的验证；逻辑全写进 React 组件后患无穷 | 技术栈轮 |
| D-36 | Python / WASM / MCP 都不是核心依赖：Python = 未来插件运行时（桌面壳阶段，独立进程异步）；WASM = 插件的一种沙箱运行方式（纯函数适合，系统级不适合）；MCP = 外部适配器 | 防架构耦合；本体不依赖任何 agent/计算框架 | 技术栈轮 |
| D-37 | 分发三线（全部 $0，同一仓库一次 git tag 自动产出）：线 A 源码（git clone 自跑）/ 线 B GitHub Releases 安装包（Actions 自动构建，README 写两行绕弹窗）/ 线 C npm 包（`npx` 拉起，免签名首选） | npm/pip/git 通道不触发 SmartScreen/Gatekeeper 的两个检查条件（浏览器下载标记 + 图形双击）；Node-RED/n8n/ComfyUI 证明"GUI 住浏览器里"对本类应用完全成立 | 分发轮 |
| D-38 | 签名策略：有真实陌生用户之前 $0 不签；第一个值得买的是 $99/年 Apple Developer；Windows OV/EV 证书最后再说（且 SmartScreen 看声誉，新证书照样弹窗） | 无签名不是封锁只是警告；个人开源软件不签名发布是社区常态 | 分发轮 |
| D-39 | CI/CD = GitHub Actions（公开仓库免费不限时，三平台 matrix 并行），tauri-action / electron-builder workflow 是填空题；个人阶段暂不实施 | 免费且成熟，知道路线存在即可 | 分发轮 |
| D-40 | 开源策略分轴：schema 规格文档公开方向（现在就该有）；核心引擎建议开源；UI 可后置；"格式开放 ≠ 软件开源"是两条独立轴（Obsidian 路线：闭源软件+开放格式成立） | 公开 schema 倒逼接口设计规范；用户信任来自"数据随时能走" | 元数据轮 |
| D-41 | IndexedDB 自保三件套：固定 dev 端口（vite `server.port: 5173, strictPort: true`）；不用无痕窗口；导出 JSON 快照做成显眼按钮 | IndexedDB 绑定 origin，端口一变数据不通；清浏览数据会连库一起清 | 公共部分轮 |

---

## 二、未决问题（U 系列）

每条含：问题 / 何时必须定（触发时机）/ 现有倾向。

| # | 问题 | 触发时机 | 现有倾向 |
| --- | --- | --- | --- |
| U-01 | Anchor 重定位的完整边界 case（重叠引用怎么渲染、编辑中 token 断裂、跨块抓取是否允许、同文本重复 promote 是否合并） | 写 markdown-layer 时边写边定；接口已定不阻塞架构 | 允许重叠引用、按层级渲染；跨块 v1 先禁 |
| U-02 | 增量求值脏标记的具体算法（拓扑序内标脏传播范围） | 节点数过百且全量 tick 明显卡顿时 | 沿下游闭包标 stale，剪枝按 D-18 |
| U-03 | 异步节点（LLM 电池/python 进程）如何融入 tick：挂起-恢复的状态机形态 | 桌面壳阶段接第一个真 python 电池时 | tick 不假设同步完成；节点可处于 `pending`，下一 tick 再收割 |
| U-04 | multi-rate 子图（Subgraph 独立时钟）的具体语义 | 出现真实"快慢时标"需求时 | 数据结构已留 `rate` 字段（R-02） |
| U-05 | 桌面壳选型 Tauri vs Electron | 真需要文件系统/子进程时（电池上线或 git 集成时） | Tauri（轻、权限边界干净），但要碰一点 Rust |
| U-06 | Agent 对话面板的产品形态、模型选择、便宜 API 分级（斜杠呼出贵 agent vs 默认便宜意图识别） | v1 闭环跑通后、自己觉得需要时 | agent 走 Command API 工具调用（D-19/20 已框死权限），框架随意 |
| U-07 | 自动布局算法选型（空格键触发的重排用力导向还是层次布局） | 画第一张 30+ 节点的图觉得乱时 | 层次布局（dagre/elkjs）优先，有 delay 边时环不干扰布局 |
| U-08 | 渲染层何时换 PixiJS/Konva | React Flow 实测 500+ 节点掉帧时 | 按 D-28 换皮肤，逻辑层不动 |
| U-09 | SQLite 迁移时机与表结构细化（objects/edges/blocks/groups 四表 + 索引 + 外键） | IndexedDB blob 保存明显变慢、或需要跨项目查询时 | 表直接映射内存扁平表 |
| U-10 | 是否做 VSCode 式文件树/图层面板等北极星面板 | 逐个按痒了评估；文件树实质是"块的层级视图"与真实文件系统无关 | v2+ 再说，D-30 已把 v1 锁在三区域 |
| U-11 | LaTeX 公式 vibe 抓取、翻译等特例电池的意图识别细节 | 第一次真的想用时 | 走 plugin-api 的 eval 声明，不进核心 |
| U-12 | 多开与小窗、命令历史面板、调试面板的具体交互 | 北极星阶段 | 数据结构（Command 日志）已天然支持，纯 UI 问题 |
| U-13 | 移动端 | 桌面形态稳定后很久 | 不在可见路线图内 |
| U-14 | 框选集合语义（交/并集、Ctrl 点选、加减选）的完整定义 | v1 只需"框选=加入选择、Ctrl 点选=切换"；复杂语义用起来再补 | 最小集先用 |
| U-15 | gumball（选中物体的平移/旋转/缩放手柄）在二维画布上的形态 | 画布基本交互稳定后 | 2D 版：移动 + 缩放，旋转大概率不需要 |

---

## 三、预留字段/能力（R 系列）

数据结构里现在就有位置，实现明确延后。禁止提前实现（见 AGENTS.md 禁止清单）。

| # | 预留 | 字段/位置 | 何时启用 |
| --- | --- | --- | --- |
| R-01 | delay 边求值 | `Edge.delay: boolean` | v2 tick 循环上线 |
| R-02 | multi-rate 子图 | `Subgraph.rate?: number` | U-04 |
| R-03 | 边属性面板 | `Edge.props`（非空时 UI 才渲染标记） | 第一次需要给边挂状态时 |
| R-04 | 违规边机制 | `Edge.violating: boolean` | Subgraph 封装上线即启用 |
| R-05 | 成品黑箱标记 | `Subgraph.sealed?: boolean` | 复用/封装需求出现时 |
| R-06 | 桌面宿主 | `HostBridge` 接口 + `host.browser.ts` 降级实现 | U-05 桌面壳阶段 |
| R-07 | 异步求值/挂起恢复 | `EvalSpec` 形态 + 求值器接口签名 | U-03 |
| R-08 | 外部计算电池 | `plugin-api` 的 `ComputePlugin { manifest(); evaluate() }` 契约 | python/WASM 电池阶段 |
| R-09 | 版本迁移 | `meta.schema_version = 1` + 迁移函数挂载点 | schema 第一次改动时 |
| R-10 | 历史快照 pin | 环形缓冲 + pin 标记 | tick 循环上线后 |

---

## 四、明确否决的路线（防回头路）

| 否决项 | 否决理由 |
| --- | --- |
| md 当底层存储（含"底层 md→编译→跑→落盘 md"往返方案） | 运行时状态写回污染 git diff；md→图→md 往返不可能无损；删个标题全图错位且无法检测 |
| 一上来做 Electron/Tauri 桌面壳 | 先壳后内核是经典死法；自用阶段桌面收益为零（D-24） |
| 核心引擎用 Python/FastAPI 本地服务 | 已修正：v1 无后端，库形态（D-24）；Python 只在插件运行时出现 |
| Fork VSCode / 做 VSCode 插件 | 核心创新与 VSCode 的"文本编辑器+文件树"抽象几乎不重叠；插件 webview 受限、键位打架 |
| 让 Agent 直接改 SQLite/JSON 源文件 | 改崩无人拦；正确路径是 Command API（D-19/20） |
| 用 pickle 式对象直序列化做存档 | Orange `.ows` 的反面教材：跨版本迁移与安全性双输 |
| 在应用层做"统一五个工具的元工具" | Yahoo Pipes/Quartz Composer 死因重演；统一应发生在窄边界协议层 |
| 自动排版实时跟随（每次后端变动自动重排画面） | 一卡一卡；整理权交给用户（空格键，D-32） |
