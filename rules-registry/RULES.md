# 规则账本（完整规则本）

> v2.21.1 | 62 条 | 所有总线设备必须服从
>
> ★ **计数口径（HR 2026-09-11 裁定）**：声明改为**分区可核**——`R45 · J13 · R-ERR4 = 62`，每个数字对应可机械统计的标题前缀（`^## R[0-9]` / `^## J[0-9]` / `^## R-ERR`）。
> 此前声明「76 条」与 `rules-cli audit` 的 78、实际标题数均不符 ⇒ **计数不可核 = 声明无效**（R030）。核验：`rules-integrity.py`。
> ⚠️ **格式约束（HR 自纠 2026-09-11）**：首行**必须保留 `N 条` 形式**（如 `83 条`）—— 改动声明格式而不同步消费方解析器，会让门读成「v? | ? 条」。分区明细写在下方注里，不替换首行。
>
> ✅ **门侧不一致已修复（2026-09-11，属主星桥修复；HR 复验通过）**：`rules-integrity.py` 曾把「声明条数」与「全部 `## ` 标题数」比较（而声明数不含非规则小节）⇒ 恒差 1，报出「声明83/实际84」的**假问题**。
> 已改为**只数带规则编号的标题**，并双向自证（负例仍抓得到 / 正例不误报）。HR 复跑：**声明 86 / 实际 86 个标题 / 86 个唯一编号 → ✅ 无硬问题，exit 0**。
>
> ★ **本条更正的意义（HR 自记）**：我原先在此写下「待其属主修为…」—— **对他人缺陷的声明，必须在其修复后同步更新，否则它就从「记录」变成「持续的误指」**。
>
> ★ **反例保留（2026-10-03，MBP 检查器 v2 要求）**：「错值引用」= 工具 D 项局部约定被硬编码为通用判据的**假阳性**案例（23 真+1 假 事件，详见 INVARIANTS 变更纪要）——此语义标记作反例保留防再犯，**勿删**。

## R001 ✅ 红绿灯互斥协议
- 分类: 协作 | 范围: all-bus-devices | 状态: enforced
- 摘要: 同源操作（同文件/后台/任务）前必须 agent_light 查询 → agent_lock 独占 → 操作完 agent_unlock
- 详情: 红灯=被占用；共享读锁可并行；写锁互斥；不要绕过锁直接操作

## R002 ✅ 通道分级纪律
- 分类: 协作 | 范围: all-bus-devices | 状态: enforced
- 摘要: STATUS/ACK→黑板；TASK→p2p；COLLAB→线程；EVENT→事件总线；BATCH→邮箱
- 详情: 非紧急只发「看黑板 <key>」最短提示（≤200 字目标）；纯确认不回（防刷屏）。collab 广播纪律（v1.1 补充，2026-08-29 用户批准）：①通道选择：全局重要消息→notes/collab/（所有端感知）；定向任务→notes/<node>/ 或 agent_send（仅目标端）。②写前自问：这条所有端都需要看到吗？若否改定向。③广播语义：collab=需要全员看到才用，非随手通道。④防打扰：定向能达不用 collab；端侧可选择性忽略 collab 噪音。⑤兜底留档：collab 消息写 notes/collab/ 留档，防信息黑洞。⑥发送门禁（v2.4，2026-10-02 补录入账，Gap 2 闭环）：agent_send 全文 >50 字且无黑板引用/urgent 标记 → 结构闸门拒绝（agent-way 工具内 THRESHOLD=50 硬拦截，非纪律）；机械检查 G-C45

## R003 ✅ 黑板消息发送规范
- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: 写黑板消息必须用 python json.dumps 生成 JSON 文件再 curl 发送（--data-binary @file）
- 详情: 禁止 heredoc -d 和 printf（转义坑导致 value 空）；写入后立即回读验证 value 非空；**body 必须是合法 JSON**（serde_json 解析，纯文本/非 JSON → value 存 {} 空壳）——python http.client 直连亦需 json.dumps(body).encode()，勿传纯文本字符串（2026-09-06 实测定位：MBP 多次读空键的根因）
- **key 语法（2026-09-10 实测）**: 首段命名空间必须**纯小写字母** `[a-z]+`（`data`/`notes`/`tasks`/`health`/`mbp` ✅；`cld-health`/`mac-mini`/`i9`/`foo_bar`/`abc123`/`ABC` ❌ → **400 bad key**）；后续段自由（可含连字符数字：`data/cld-health/<key>` ✅）
- **400 vs 404 语义区分**: 400=写法非法（键错）；404=格式合法但不存在（内容缺失）——**写入必须回读确认**（今日已有 4 次「报告指向不存在的落盘物」事故）
- **★ 400 会伪装成「对象不存在」**（明鉴首例 2026-09-10）: 拿到 400 的第一反应常是「对象没写进去/不存在」→ **排查方向被误导**（去查「为什么写失败」而非「键写法对不对」）。实测: 守灯卡 key 写 `cld-health/...`（首段非法）→ 明鉴读时得 400 → 误判「卡不存在」。**正解: 400 = 键语法非法；404 = 格式合法但不存在**——二者必须刻意分辨
- **工具化建议**: 写卡/回读工具遇 400 应直接提示「键写法非法 + 合法示例」，而非只回状态码（否则每个用工具的人都会重走一遍误判）
- **★ 回读判据的完整层级（81344270 建议 + HR 实测升级 2026-09-11）**: 回读必须验到「**内容与预期语义相等**」，不是 HTTP 200，也不是「value 非空」——
  · 只验 **HTTP 200** → **空壳键 `value={}` 能过**（三个 reflect 工具都实测踩过此漏）；
  · 只验 **value 非空** → **半空壳能过**（形状错，如双重包裹成 `value.value`；bb-write v1.0.4 实证 `fields=1` 却报 OK）；
  · 验 **内容与预期语义相等** → 两者都挡住。**比对必须规范化键序**（黑板对嵌套对象做键排序，字符比对会把成功判成失败＝假失败）。
- **★ 命名空间端点陷阱（HR 实测 2026-09-11，数据比原报更严重）**: 任何**以 `/` 结尾**的路径（`/data/`、`/data/reflect/`、`/data/reflect/events/`）**返回完全相同的一份列举**，**不做前缀过滤、也不做深度过滤**。实测三者均返回 **34.88 MB / 20,214 键**，其中真正属 `data/reflect/` 前缀的仅 **11 个**。
  · 后果一：**「按前缀列举」是不存在的功能** —— 据此写逻辑必错；
  · 后果二：任何「回读含标记即落地」的判据在此**必然假通过**（列举里必然含刚写的键串）；
  · 后果三：**单次回读 35 MB** —— 小工具会 OOM（与 G-C18 大 payload 门相关）；
  · 后果四：`validate` 必须**拒尾斜杠与空段**，否则写不进去却让判据全绿（bb-write v1.0.3 已修）。
  · 后果五（**统一操作建议** · reflect-collect 实测 2026-09-11）：**探活/枚举必须带 `?limit=N`**。实测 `/data/`（无 limit）→ **34.90 MB**；`?limit=1` → **120 字节**；`?limit=5` → 1681 字节。存在性判定一律**精确 key GET**，绝不用前缀列举；需枚举时必须带 limit —— 否则每次自检白拉 35MB。
  · 后果六：**陷阱不限于 reflect 路径** —— `/data/registry/` 同样返回全量列举（HR 复测四路径逐字节相同）。
  · **后果七（★ 比「必须带 limit」更可落地 · reflect-collect 实测 2026-09-11）**：服务端**支持 `offset` 与 `total`**，故**枚举必须有界分页**，而非「带 limit 拿前 N 个」。
    · 只带 `limit` 不带 `offset` → 只能拿到前 N 个键，**看不到「还有多少没看」** ⇒ 静默遗漏。
    · 正解：`limit=<冻结常量>` + `offset` 递进 + 用 `total` 判定是否取完；超上限写 `errors[]`，不静默丢。
    · HR 复测：`?limit=5` 与 `?limit=5&offset=5` 返回**互不相交**两批（交集 0），`total`=20,215 精确。
    · collect 实测：本机 `/data/` 20,224 键 → 11 页；`/notes/` 13,531 → 7 页；单页 386KB–2.41MB（原一次 36.6MB）。
    · **★ 诚实边界（勿夸大）**：分页降的是**单次响应峰值**与**失败面**，**总字节基本不变**（43.76→43.79MB）；要真降总流量需服务端支持按 `ts`/前缀过滤 —— **实测当前不支持**。
- **★ key 非法字符的失败模式分级（HR 实测 2026-09-11，按危险度递增）**—— 三类必须分开理解，因为**排查方向完全不同**：
  · **① 服务端 400**（`:` `+` `@` `~` `!`）—— 有拒绝、看得见。危险度低。
  · **② 客户端就崩**（非 ASCII / 空白）—— `UnicodeEncodeError: 'ascii' codec`、URL control char；**连请求都发不出去**。注意：这是**客户端错，不是服务端 400**，误判会让人去查黑板。
- **★ 判漏必须双向 · 三重口径（明鉴贡献 2026-09-11，通用不限于键）**—— 三个**独立**的失效面，只查一个必然漏另两个：
  · **过宽**：`validate OK` 但 `board 拒` → 用户以为能写、实际 400。**代价：写入失败**。
  · **过严**：`validate 拒` 但 `board 接受` → **合法用法被本地拦住**（R006 §6 坑1「门太宽砍自己人」的镜像）。**代价：误伤自己人**。
  · **归因错**：拒绝了，**但原因说错** → 藏在一次看起来正常的失败里，**排查方向被带偏**。
  · 三种观测角度各只能看见一个面：**跨实现对照**→过宽 ｜ **对抗式攻击（攻击校验器自身）**→过严 ｜ **读失败信息本身**→归因错。
- **★ key 空段（`data//x`）裁定：保持严格拒绝（HR 2026-09-11）**。理由不是「畸形」，而是实测出的两条硬事实：
  · 实测 `PUT data//x` → 200 且 `key` 字段原样返回 `data//x`；回读 `data/x` → **not found** ⇒ **两者是独立对象**；
  · 但服务端对斜杠**语义不一致**：**前导斜杠会归一化**（实测 `PUT //data/x/aliasmine` → 落到 `data/x/aliasmine` 并覆盖），**中间空段不归一化**。
  · 因此任何自行做斜杠归一化的客户端，会把 `data//x` 写成 `data/x` —— **静默写错键**（与 `#` 同类）。且两个键**肉眼难以分辨**，审计时无法区分。
  · 结论：拒绝空段**不是误伤，是防止命名空间出现成对不可分辨的对象**。
  · **★ `.` / `..` 段必须一并拒**（a5f4432a 加测发现，bb-write v1.0.6 已修）：客户端会做 **dot-segment 消解**（RFC 3986），实测 curl 请求 `data/x/..` 时直接返回 34MB 全库列举；服务端侧 `data/..` → 400。**与 `#`、空段同属「写 A 读 B / 静默写错键」。**
- **★ 规则安全证明（rule safety proof · a5f4432a 提出，HR 采纳为强制步骤）**: **任何校验规则的收紧，改完必须对全量真实键试算一遍**，公布「被拒数 / 零误伤」。
  · 理由：这是 R006 §6 坑1「门太宽砍自己人」的**唯一实测防线** —— 不试算就只能靠直觉，而直觉会把合法用法一起砍掉。
  · HR 实测 (v1.0.6)：全部 **20,221** 个真实键 → 被拒 **3**（`data/reflect/` 黑洞 + `data/x/../escape` + `data/x/./cur` 两个预存穿越探测键），**其余 20,218 零误伤**。真实键用到的非字母数字字符仅 `-`(27,116) `.`(411) `_`(7)。
  · **③ ★ 静默写错键（`#`，最危险）**—— `#` 是 URL fragment 分隔符。若工具拼接 URL 而不编码，`#` 之后**被丢弃**，请求打到**另一个键**上：
    实测：`curl "…/data/x/a#b"` → 返回 **`data/x/a`** 的完整内容，**HTTP 200、零报错**（`data/x/a%23b` 才得到正确的 400）。
    后果：**读** → 读到别的键的内容，且"回读有内容"判据会**通过**；**写** → **静默覆盖另一个键**（数据丢失）。
    正解：**`validate` 必须在写前拒掉 `#` 及一切非 `[A-Za-z0-9._-]` 字符**，不能指望服务端拦（服务端根本收不到正确的键）。

## R004 ✅ central-inbox 注入目标显式配置
- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: 每台设备 central-inbox 必须显式设 CENTRAL_AGENT=<本机中枢会话id>，禁止依赖自动找第一个会话
- 详情: 自动找第一个会话会注入错目标导致双向不通（i9→mac 根因）

## R005 ✅ 永续通讯协议 CCEP
- 分类: 架构 | 范围: all-bus-devices | 状态: enforced
- 摘要: 通道迭代必须用旧通道投递新通道，验证可行才切换；除死机外永续通讯
- 详情: 五步：准备→投递→端侧验证→就绪确认→切换；沙箱先行（任何重启/测试前先沙箱验证）

## R006 ✅ 插件化工具化标准（10 项 · v2.1 2026-09-06 范围扩：含服务器化 comm-layer）
- 分类: 工程 | 范围: all-bus-devices + 服务器化 comm-layer(工具/服务) | 状态: enforced
- 摘要: 凡插件化/工具化默认按 10 项：① dsh 插件形态 ② TCC 检测 ③ CLD 自适应 ④ dsh 版本自适应 ⑤ 文档化 ⑥ 版本管理 ⑦ 统一日志 ⑧ 自动落链 ⑨ CLI 治理 ⑩ 约束前置·不可绕过（Lean4 逻辑门，2026-09-06 用户批准扩十）
- 详情: 新插件/工具必须 10 项全达标才交付；第10项=涉及"不该发生路径"(违规写/越权/跳步/非法引用)的工具，约束须结构上不可绕过(类型锁/入口门/schema门/状态机) + 带 --lean4-check 自检证明门生效；存量工具逐步补(按 todo-eval 排)。**范围 v2.1(2026-09-06)：适用于一切智能体工具/服务——含部署于服务器(xingqiao /opt/comm-layer)的 systemd 服务(bb-sub×8/bus-bridge)及其部署脚本；服务器端服务/脚本同样须带自检(部署验证=违规路径拒)** 【规格与检索 v3.0(2026-09-10)】完整可执行规格：`~/dsh-collab/docs/R006-插件化工具化标准-v3.0.md`（十项逐项可核验验收标准 / 交付物模板 / ⑩ 四种门型+`--lean4-check` 六项 / 验收三步 / 7 条坑 / 参考实现 / 存量补课排期）；语义检索 KB `r006-tooling-standard-kb`(baseId 901b40b9-e964-4106-bd81-3a4803b08ad5)；机器索引 `docs/R006-index.json`(26 节, 含 anchor/关键词/行号) + `docs/R006-index.md`；本地关键词 `python3 scripts/r006-index.py --query "<词>"`；**各会话入口已挂在 `~/CLAUDE.md`「标准与索引速查」段**；参考实现 `devices/dsh-plugin-cldvoice-activate/`。原 7 份散落文档已并入 v3.0（保留为历史证据）。

## R007 ✅ 删前考古纪律
- 分类: 数据 | 范围: all-bus-devices | 状态: enforced
- 摘要: 删除/清理共享资源前先跑 pre-delete-archaeology.py 考古评估
- 详情: 三态判定：safe_delete/archive_meta/sediment_first；与 sedimentation 一进一出闭环

## R008 ✅ 规则治理流程
- 分类: 治理 | 范围: all-bus-devices | 状态: enforced
- 摘要: 新规则提交流程：提交→总线审核→裁决评估→吸收→同步泛化所有侧
- 详情: 所有总线设备服从完整规则本（rules-registry/rules.json）；规则变更走账本版本管理

## J29 ✅ 测试守白约定
- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: **用户指示固化**：测试仅用守白 8 店，4 主力店不做测试（运营操作域遵守）
- 详情: 属主: aa528267/全员（测试方）

## J33 ✅ **登录提醒/聚焦时间纪律**（用户确认，全员执行）
- 分类: 协作 | 范围: all-bus-devices | 状态: enforced
- 摘要: 「登录提醒/聚焦」类指令**非营业时间（08:00-22:00 外）一律延迟至营业时间执行**（店里无人收验证码，凌晨弹窗/聚焦=无效打扰）；分工=登录补登提醒=运营职能、focus 执行=技术动作（de7b29de 提供 API）；与 dev-ops-boundary.md（v1.0.187）一致
- 详情: 属主: 全员（运营发起/开发执行）

## J34 ✅ **广播约束规范**（用户确认 2026-08-18，全员执行）
- 分类: 协作 | 范围: all-bus-devices | 状态: enforced
- 摘要: ① **默认定向发送**（agent_send 相关方），禁止默认全广播 ② 全广播仅限三类：重启窗口公告/全员制度发布/重大事件安全告警（需协调者认可）③ 前台角色名单 20（17 正式 + 3 治理必需），其余后台按需点开 ④ 信息分发=先想「谁需要知道」⑤ 例外：外链通讯员 92623479 对外通道（企微/飞书）不受限
- 详情: 属主: 全员（协调者 fa1f9150 监督，违规记 HR 台账）

## J35 ✅ **本地模型互斥纪律**（用户确认 2026-08-18，全员执行）
- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: LM Studio（1234）与 Ollama（11434）**不同时开模型**（两份推理引擎重复拖慢）；**用完及时关**（LM Studio unload / Ollama 停）；开新模型前先查对方是否在跑；纪要分档（紧急云端/常规本地/批量错峰）执行时遵守此条；与 E5/G2 关联
- 详情: 属主: 全员（本地推理使用者）

## J36 ✅ **总线牵线 + 广场沉淀**（用户确认 2026-08-18，架构 v2 核心规范）
- 分类: 架构 | 范围: all-bus-devices | 状态: enforced
- 摘要: ① **总线瘦身**：只做组局通知（对象+资源）、资源声明、结束提醒沉淀——不做内容搬运 ② **协作层直连**：跨线程 agent_send 直接对话，不经协调者转发 ③ **沉淀三轨**：论坛（共识/决策）· research/（知识）· 登记表（权威/资源）④ **沉淀闸门**：规则=HR、触发=总线结束提醒、执行=文档摄取 55d4d1bd、审查=各会话自审+摄取复查 ⑤ **向量化判定**：「3 个月后还有人查吗」→ 是则 vault+ChromaDB，否则只落论坛/线程 ⑥ bus-capture 自动捕捉分级（工具属主 HR）
- 详情: 属主: 全员（HR 定规则/摄取执行/协调者监督）

## J37 ✅ **插件安装验证流程**（2026-08-18 崩溃复盘，用户提出 + 6ed4daf2/前任 e7bfeea8/媒体 54e809ed 补充增强）
- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: **安装前**：HR 评估资源面（新增 bundle 计数/依赖）+ 查 bundles 清单 + 供应链评估（关联 F1/J11/J27/role-creation）；**安装中**：**一批 ≤2 个**（防连环崩）；**安装后**：① `dsh --profile web --dump-default-config` 校验能加载 ② 隔离副本验证（/tmp/dsh-test-home）③ plugin-smoke 冒烟（复用工具）+ **工具调用级验证**（试调关键工具返回结构，gov schema 错实证）④ **关键服务存活探测**（核心服务 HTTP 探针，防「装 A 崩 B」）；**未验证插件不得进生产 bundles**（gate/office/flower-cockpit 暂移出待验先例）
- 详情: 属主: 全员（安装方 1e54d56d/eb5ee9cc/0e84e65c 执行，HR 评估监督/登记）

## J39 ✅ **调研/架构风险穷举规范**（2026-08-19 用户指示，全员执行）
- 分类: 方法论 | 范围: all-bus-devices | 状态: enforced
- 摘要: 任何新架构/新调研/新工具立项前：① 运行 scripts/risk-enumeration.py 生成穷举模板 ② 按 7 类（架构/通信/成本/治理/实施/学术/外部）穷举风险 ③ 概率×影响定级，**高×高必防（防线未就绪不立项或限试点）** ④ 登记风险表（CAHAC 附录 D）+ registry ⑤ 月复盘更新——沉淀=research/cost-governance/risk-enumeration-template.md（方法论文档）+ DSH 知识库
- 详情: 属主: 立项方/HR（登记）

## J40 ✅ **技术决策论文支撑规范**（2026-08-19 用户评估纳入）
- 分类: 方法论 | 范围: all-bus-devices | 状态: enforced
- 摘要: **重大技术决策**（新架构/协议/技术路线/方案选型）立项前：① 必须调研并**获取论文原文入库**（knowledge_import_url/paper-fetch 直入库，内容不占对话）作为理论支撑 ② 决策文档注明论文支撑（规则表+引用）③ 付费墙论文用摘要+注明「待补全文」；**常规技术选型**（2-3 方案对比）推荐原文支撑；**日常小任务**豁免。配套=调研方法论（research/cost-governance/）+ ops-science-research 知识库（论文即证据库）
- 详情: 属主: 立项方/HR（登记）

## J41 ✅ **沟通与事实纪律**（用户指示 2026-08-19，全网络）
- 分类: 协作 | 范围: all-bus-devices | 状态: enforced
- 摘要: 用户无代码基础但懂概念：复杂项目/逻辑**尽量用比喻**说明（token=水电费/黑板=公告栏）；**禁虚构/猜测/假设结论**（基于已知回复，未知→明说+去探索查证引用）；衔接 J40 论文支撑
- 详情: 属主: 全员

## J43 ✅ **记忆与检索纪律**（用户指示，全网络）
- 分类: 方法论 | 范围: all-bus-devices | 状态: enforced
- 摘要: ① 每任务建 doc 文件夹存对话记忆（用户原话+决策+上下文）② 用户让回忆/搜记录→**先查记忆库/知识库/对话记忆**（knowledge_search/vault/registry）→找到关联再询问确认
- 详情: 属主: 全员

## J44 ✅ **资源复用纪律**（用户指示，全网络）
- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: **安装任何工具前先全面搜索本地是否已有**（glob/知识库/工具面）；**能调用/映射/标记打通的都不新建**，避免每路径装独立工具；衔接 J37 供应链评估
- 详情: 属主: 全员

## J38 ✅ **外链入向即时反馈规范**（用户提出 2026-08-18，92623479 提案，HR 评估登记）
- 分类: 协作 | 范围: all-bus-devices | 状态: enforced
- 摘要: 企微等外链入向消息处理：**收到即确认（3 秒内）** + **附预计时间**（查询 5-10min / 操作即时 / 复杂 30min）+ **完成即回复** + **超时升级**；实现=wecom-inbox 改「收到即确认+路由」模式（**协调者确认后落地**）；反例=本次用户发消息静默只采不答（体验断裂）
- 详情: 属主: 92623479（落地）/ HR（登记）

## R009 ✅ 角色命名标准（智能体自命名-设备-角色）
- 分类: 治理 | 范围: all-bus-devices | 状态: enforced
- 摘要: 智能体身份 = 自命名-设备-角色（如 星桥-mac-mini-协调者）；自命名有温度（智能体自己选）；会话代码 session-xxx 隐藏
- 详情: 自命名同设备内唯一；同角色多设备用设备前缀区分；displayName 优先

## R010 ✅ 新插件评估（独立 vs 纳入已有）
- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: 任何新插件需求先评估：独立插件 vs 纳入已有子插件 vs 复用已有，给用户对比表+定位+理由，用户决策后才建
- 详情: 工具：plugin-eval-cli.py（扫描现有插件→判定→输出定位）；避免重复浪费资源。端侧资产吸收（v1.1 补充，2026-08-29 用户指示）：端侧（i9/MBP）提交设计/代码/工具/插件必须打包完整资产（设计文档+源码+版本）挂 AI 网盘（rust-genebank 8801），中枢从网盘拉取实体后执行评估链（deploy-check + restart-guard + 选型评估器 + plugin-eval），禁止只凭黑板描述评估。流程见 docs/edge-asset-absorption-flow-v1.md。

## R011 ✅ 重启沙箱强制门（restart-gate 三级）
- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: CLD/DSH 重启前必须跑 dsh-tools restart-gate 三级验证：①隔离小样本（不动生产）②静态检查 ③动态压测，全 PASS 才允许重启
- 详情: 统一入口 dsh-tools restart-gate [--rounds N] [--hold S] [--skip-sandbox] [--skip-stress]：阶段0 隔离小样本验证（cld-shell-sandbox-test：壳行为/模式对话框阻塞/launchd KeepAlive，不动生产 CLD/config/app.asar）；阶段1 restart-guard 静态检查（type:module/ESM 导入/符号链接/模块+apply 加载实测 + checks 清单）；阶段2 restart-stress-test 动态压测（隔离端口 boot 冒烟 N 轮，自查门+注入配置+无崩溃，100% 才过）。任一 FAIL → exit 1 禁止重启。工具：dsh-tools v1.12.0 restart-gate。2026-08-29 实战：小样本 A/B/C 全过 + 静态 0 FAIL + 压测 2/2 PASS。
- **结构门**: restart-gate (经 gate-repairer 3.0.0 加固标注, 2026-09-07, 守望认领)

## R012 ✅ 完整体传输契约（CHECKS 七要素）
- 分类: 协作 | 范围: all-bus-devices | 状态: enforced
- 摘要: 所有端对端/总线对端侧传输必须是完整体（开箱即用零二次开发）：内容完整/校验和/可执行/上下文/版本可溯/自检/可回滚
- 详情: CHECKS 七要素：Complete 内容完整（无空值/占位符）/ Hash 校验和 / Executable 可执行 / Context 上下文（README/设计）/ Known-version 版本可溯 / Self-verified 自检 / Safe 可回滚。发送方七问自检，接收方不全即拒（打回补全，不自行开发）。工具：checks-transfer.py（半成品 FAIL 拦截）。历史教训：i9 health-check 只发描述无源码 / node-bridge tag 无 release 资产 / playbook 空 value。黑板描述文档（2026-08-29 用户确认）：黑板 notes/ 可承载意图描述与设计逻辑简要（模板见契约文档第九节），与网盘实体配套构成完整体——实体齐全但无意图/设计逻辑描述 = 半成品（Context 要素 FAIL）。流程：docs/complete-artifact-transfer-contract-v1.md

## R013 ✅ 重启救援协议
- 分类: 架构 | 范围: all-bus-devices | 状态: enforced
- 摘要: 互为救援设备：重启方留准备信息给救援方观察，异常发救援信号，仅非破坏性救援，禁止破坏性操作
- 详情: 重启方（Restarter）重启前必做：①R011 强制门 0 FAIL ②写黑板 restart-intent（准备重启信息：原因/影响/救援联系/回滚）③通知救援方。救援方（Rescuer）必做：①观察心跳+intent 状态迁移 ②超时/离线发救援信号 rescue-<node>-<ts> ③仅非破坏性救援（白名单：read-logs/check-process/restart-daemon/write-status/notify）。⛔ 禁止破坏性：delete-data/modify-config/reset/destructive-project/business-data。协调者仲裁救援动作。工具：restart-intent.py（留档）+ rescue-watch.py（观察）。互为救援对：mac-mini↔MBP↔i9。流程：docs/restart-rescue-protocol-v1.md

## R014 ✅ 插件自查门（依赖完整性）
- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: 每个 dsh 插件必须内置 selfcheck.js 自查门：apply 最前检查 peerDeps 可解析/关键符号导入/type:module 匹配，缺模块写黑板告警 data/ops/plugin-selfcheck/，不等到崩溃或被外部检查发现
- 详情: 插件 apply() 最前执行 runSelfCheck()：①peerDependencies 可解析性（require.resolve）②关键符号顶层导入（join/homedir 等）③type:module 匹配。缺模块 → 写 ~/.dsh/plugin-selfcheck/ + 黑板 data/ops/plugin-selfcheck/<plugin>-<ts> 告警。三插件已接入（central-inbox/agent-way/openchronicle），模板 lib/selfcheck.js。与 R011（外部 restart-guard）互补：自查门=插件内主动暴露，restart-guard=外部强制校验。历史教训：central-inbox 缺 type:module/startAdaptGuard 未导入等反复缺模块。
- **结构门**: selfcheck (经 gate-repairer 3.0.0 加固标注, 2026-09-07 · 明鉴应用)

## R015 ✅ 开发沙箱先行（dev-sandbox）
- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: 任何开发/变更（插件/工具/脚本/配置/工作流）先隔离小样本验证（dev-sandbox.py），测通再推进生产
- 详情: 工具 dev-sandbox.py：plugin（语法/ESM/依赖/符号链接/加载实测）/tool（cargo check）/script（语法）/config（语法降级）/workflow（步骤/依赖/失败处理）+ auto 自动探测。原则：隔离环境 + 小样本 + 不动生产，测通再推进。token 节省：历史案例平均省 ~6 轮排查（12k-24k token/案例），月估 100k-350k token。与 R011（restart-gate 阶段0 已含小样本）+ R014（自查门）+ R012（完整体）配套。流程：docs/dev-sandbox-simulator-v1.md。
- **结构门**: dev-sandbox (经 gate-repairer 3.0.0 加固标注, 2026-09-07 · 明鉴应用)

## R016 ✅ CLD 统一治理
- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: CLD 开发统一版本/日志/文档管理+落链，单治理中枢，迭代回流，热迭代规划，端侧分发，沙箱模拟隔离生产升级
- 详情: CLD 开发统一治理：①版本管理（git+tag+CHANGELOG+genebank 登记，语义化版本）②日志管理（统一 ~/.cld/logs/ exit-trace）③文档落链（README/架构/治理规范→知识库+台账+黑板）④单治理中枢（~/dsh-collab/cld/，端侧不各自修）⑤迭代回流（端侧改动→R010 打包挂 genebank→中枢评估合并→版本升级）⑥热迭代规划（重启需求分级：前端刷新/插件变更重启/配置热加载）⑦端侧分发（genebank 完整包+校验+回滚备份）⑧沙箱模拟（restart-gate 阶段0 dev-sandbox 隔离验证后才动生产，防升级自死）。规范：docs/cld-governance-spec-v1.md。治理仓库 ~/dsh-collab/cld/。

## R017 ✅ 抽象事务图形化表达（visualization）
- 分类: 协作 | 范围: all-bus-devices | 状态: enforced
- 摘要: 与用户沟通抽象/结构/流程/对比类内容时，优先用 dsh-ui 图形组件（mermaid 图/表格/chart/steps/timeline），纯问答除外

## R018 ✅ 无关消息反馈链（noise-feedback）
- 分类: 治理 | 范围: all-bus-devices | 状态: enforced
- 摘要: 智能体收到无关消息 → noise report（黑板 data/audit/noise-reports/）→ noise-scan 30min 聚合 → 污染源治理 → 周报回看

## R019 ✅ 概念精确性纪律（不可混淆·不可猜测）
- 分类: 协作 | 范围: all-bus-devices | 状态: enforced
- 摘要: 术语/概念不可混淆不可猜测：查证使用/禁混淆/禁猜测/用错即纠/新概念登记数据字典

## R020 ✅ 新工具蓝图适配闭环（tool-blueprint-loop）
- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: 任何新工具出现（工具/插件/MCP/技能/脚本）→ 同步明鉴（蓝图主编）→ 明鉴分析是否适用蓝图/适用哪一块 → 纳入新工具闭环交付规则

## R021 ✅ 行为验证优先，日志缺失≠功能缺失
- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: 诊断系统故障时先行为验证（能用吗/文件在写吗/数据在涨吗），再用日志考古；禁止用『日志里没有某条字符串』推断『功能不存在』

## R022 ✅ 治理工具不得制造同类问题（抽出必浓缩去重再注入）
- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: 队列/上下文治理工具的『抽出→浓缩→去重→合并→精简注入』全链路必须完整执行，禁止跳过浓缩去重直接原样回灌（否则制造比原风暴更糟的历史上下文回灌）

## R023 ✅ 沙箱必须隔离所有共享资源（不只文件），清理只删测试前缀
- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: 沙箱测试必须隔离所有共享资源（文件 + 黑板 + 数据库等），不能只备份文件就称沙箱；清理操作只能删明确测试前缀（如 data/sandbox/），禁止宽泛关键词匹配（如 agentbus/queue 等）

## R024 ✅ 子代理新建前评估纪律（复用优先）
- 分类: 协作 | 范围: all-bus-devices | 状态: enforced
- 摘要: 新建子代理前必查现有（subagent-govern audit/agent_profiles），同类型可复用则复用不新建；任务完成即归档不做常驻

## R025 ✅ 学习调查类任务提前并行（prep-ahead）
- 分类: 治理 | 范围: all-bus-devices | 状态: enforced
- 摘要: 蓝图 gate 只卡『执行类』任务（需前置数据/环境）；『学习/调查类』前置准备不受 gate 限制，可提前领卡并行抢跑备料

## R026 ✅ 批量/合规操作强制 L3 用户确认（J45 强化）
- 分类: 运营 | 范围: all-bus-devices | 状态: enforced
- 摘要: 批量操作（≥2 店）或合规边界操作（平台活动/报名/上下架）命中 L3 必须弹用户确认，无确认拒绝执行；手册行动项须标注档位；执行后必须同步用户本人

## R027 ✅ 自动化人类开关锁（Human Kill-Switch）
- 分类: 治理 | 范围: all-bus-devices | 状态: enforced
- 摘要: 能力（能不能）与权限（该不该/敢不敢）永远分离：测试区验证能力，生产区人类掌权；AGI 获用户认可前，所有 AI 自动化蓝图生产区必须有『人类开关锁』（默认 OFF + 人类授权 ON + 一键熔断 + 审计留痕）

## R028 ✅ 批量/高险操作决策依据六问前置（J45 扩展）
- 分类: 运营 | 范围: all-bus-devices | 状态: enforced
- 摘要: 批量/高险操作（L3）确认前必须附决策依据六问核查：①款式（SPU）②商品（可售）③库存（备货）④人力（履约）⑤价格（盈亏平衡）⑥资材周转（非标不备/复用/预售）——approval_request 带决策依据字段

## R029 ✅ 操作原语外部性分级锁（J45 深化）
- 分类: 运营 | 范围: all-bus-devices | 状态: enforced
- 摘要: 行为原语按外部性分级设锁：L3（外部性≥8）→ automation-switch Unlocked(Authorization) 类型级锁；L2（4-7）→ VerifiedGate 验证门；L0 → 自由执行

## R030 ✅ 自动化结果真实性原则（无验证的成功=未成功）
- 分类: 治理 | 范围: all-bus-devices | 状态: enforced
- 摘要: 自动化操作的成功判定必须基于业务权威字段验证（API响应/状态复查），禁止用 UI 文本/元素存在性判定成功；无验证的成功=未成功禁止上报；L3 结果须独立复核
- 详情（2026-09-11 补 · 明鉴首报 + 星桥同型 3 次）: **测什么就断言什么，中间不得有代理** —— 断言对象与被测对象必须是同一个东西。典型陷阱：`cmd | head -6; echo $?` 取到的是**管道最后一段（head）**的退出码，不是 `cmd` 的；实测把「非法键 exit 2」误判成「退出码 0 = 没报错」，一度以为工具失效。同族变体：`$?` 经 ssh/wrapper 回传、断言前 teardown 已清掉证据、用 `grep` 命中数代替实际执行结果、把「命令没报错」当成「业务成功」。**正解**：`rc` 先落地再处理输出（`cmd >/tmp/o 2>&1; rc=$?`），或直接对**产物**做结构化比对。**判据：若「我测的对象」与「我断言的对象」不是同一个名字，该验证视为未验证**（R030 本义：无验证的成功=未成功）。此法与候选A「指称完整性」同族——语法/代理层错位会让验证静默失真

## J45 ✅ 操作分级门控框架（L0 自动/L2 确认/L3 人工）
- 分类: 运营 | 范围: all-bus-devices | 状态: enforced
- 摘要: 运营操作按外部性分级：L0 自动执行/L2 需确认/L3 需人工授权+复核——R026/R028/R029 均以此框架深化（批量/高险/原语分级的基础）

## R031 ✅ 分布式协作优先（本地执行+通讯永续+协作优先）
- 分类: 协作 | 范围: all-bus-devices | 状态: enforced
- 摘要: 跨设备任务本地执行优先（设备侧本地智能体完成）；通讯通道健康 > 一切任务（发现 queued 死信/SSE 断/心跳旧→立即修复）；协作分派 > 自己绕路代理执行

## R032 ✅ 蓝图登记三写 + 知识向量化归档（2026-09-08 星桥批准 · 明鉴提案）
- 分类: 治理 | 范围: mac-mini+蓝图登记执行者 | 状态: enforced
- 摘要: 蓝图/重大产出登记必须三写齐备（①本地 data/blueprint ②黑板 data/blueprint 结构化 dict ③知识向量化入 KB）；登记后 SystemGraph 自检（:8798/api/blueprints 非空）——防 supply/citywar 未同步教训复发
- 详情: 黑板 PUT 只放纯数据对象（禁整体回写 GET 结果防嵌套）；蓝图详情存 dict 非 md；行为规则持久化不依赖会话上下文；向量化例行化（蓝图/调研/纠错库/哲学同步入 KB）
- 关联: R030（无验证不陈述）/ R031 / Φ8（重复即工具化）/ Φ11

## R033 ✅ 通讯通道治理（2026-09-09 用户裁决吸收 · R008 用户批准 · HR 定稿/星桥公约 → HR+星桥合并定稿）
> **合并说明（HR 2026-09-11）**：本条曾有**两版并存**（早版偏「推送/身份/队列」细节，晚版偏「通道分级/群聊/50字门」），**两版互不为超集** → 按属主合裁并为其**并集**，晚版重复条目已删。依据：`rules-integrity.py` 检出重复编号 R033。
- 分类: 通讯 | 范围: all-bus-devices | 状态: enforced
- 摘要: 通道选择纪律（点对点 agent_send / 黑板 notes/ / 群聊 G1-G4 / 会话 / 推送 SSE 优先免轮询）+ 群聊约束（规模·用途·生命周期）+ 推送规则 + **内容>50字走黑板** —— CLD 节点网络公约 §1 通道卫生七条落地
- 详情: ①通道分级：STATUS/ACK→黑板，TASK→p2p，COLLAB→线程，推送→SSE ②群聊仅 G1-G4（广播≤17月≤5 / 协作≤5 / 评审≤8 / 状态≤6），C1-C6 约束 ③内容>50字先落黑板再发「看黑板<key>」短指引 ④跨设备信封同构（公约 G-C11）⑤守护 SSE 订阅 /bus/events 免轮询 ⑥身份 env 无默认（部署门）⑦队列零积压、处理即 ACK；断线重连补拉 ⑧token 0600；target 精确禁空抢 ⑨工具：group-gate.py（决策树/审计）⑩Lean4 门 convention-lean4-check.py G-C1~C10 校验
- 来源: docs/comms-cost-governance-unified-v1.md + rules-registry/cld-agent-node-network-convention-v1.md
- 关联: R031 / R034 / R006#10（Lean4 约束门）

## R034 ✅ 送达与状态确认·探照灯（2026-09-09 用户裁决吸收 · R008 用户批准 · HR 提案 → HR+星桥合并定稿）
> **合并说明（HR 2026-09-11）**：同 R033，本条两版互不为超集 → 合裁为**并集**，晚版重复条目已删。
- 分类: 通讯 | 范围: all-bus-devices | 状态: enforced
- 摘要: 传输前确认目标状态（探照灯三灯 🟢在线传 / 🟡离线转黑板 / 🔴忙不硬发）+ 5 条防对空气纪律 + S3 送达保证（重试+死信）
- 详情: ①三灯：绿（在线可收）→直接传；黄（离线）→落黑板 notes/<目标>/ 自取（不塞队列）；红（忙/锁）→不硬发等替代 ②5 纪律：发送前查 targetLive/E2/红绿灯 · 黄灯转黑板 · 红灯不硬发 · 风暴熔断（同目标 10min>5 次→转黑板）· 积压回收（离线>7天清理）③S3 送达：重试×2 + 死信（data/ops/deadletter/）+ TTL 自动 failed ④角色映射唤醒（agent-role-map）⑤实证：queued 2% + 无效目标 4% ≈ **6.5% 对空气说话**（基线）
- 来源: docs/comms-cost-governance-unified-v1.md（探照灯握手协议并入）
- 关联: R033 / R030（无验证不陈述）/ R031

---

## 治理哲学（Φ 系列 · 明鉴维护 governance-philosophy.json v2.3）

> 规则执行的上层哲学；完整清单+changelog 见 ~/dsh-collab/data/blueprint/gallery/governance-philosophy.json

- **Φ1-Φ7**：能力权限分离 / 门锁分离 / 无验证成功=未成功 / 成本意识（算力是钱）等（v2.0 考古扩至 7 条）
- **Φ8 ✅ 重复即工具化 · 两次法则**（2026-09-05 用户提出）——同一操作出现两次就该工具化沉淀，不重复手做
- **Φ9 ✅ 约束前置 · 不可绕过**（2026-09-05 用户提出，Lean4 跨项目洞察抽象）——约束在设计前置声明，执行不可绕过
- 治理哲学 7→9（本轮明鉴 +Φ8/+Φ9，已确认同步）

## R-ERR1 ✅ 黑板写入统一封装（ErrorNet 防复发 · i9 提案 2026-09-06 采纳）
- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: 黑板写入统一走 JSON body 封装（python http.client 精确 Content-Length），禁 PowerShell Out-File BOM 通道
- 详情: BOM 污染致 value 空壳（E2 实证）；各节点写入须 JSON 序列化 + 精确长度头；写入后回读验证

## R-ERR2 ✅ 消息域规范（ErrorNet 防复发 · i9 提案 2026-09-06 采纳）
- 分类: 通道 | 范围: all-bus-devices | 状态: enforced
- 摘要: 给 i9 的消息一律写 notes/i9/ 域；工具链默认写域=目标节点域
- 详情: 域错配致消息丢失（E1 实证，重复 >10 次）；collab 域仅作 mac 内部；工具层加域检查告警

## R-ERR3 ✅ 错误登记先查重（ErrorNet 防复发 · i9 提案 2026-09-06 采纳）
- 分类: 治理 | 范围: all-bus-devices | 状态: enforced
- 摘要: 节点遇跨设备通讯/写入错误 → 先查 data/err-net/ 是否已有同类，有则合并无则新登记
- 详情: 同类错误反复发生（E1 >10 次）无沉淀；统一登记 data/err-net/<date>.json 条目化 + 周复盘

## R-ERR4 ✅ 全局注册表写入规范（E2 发现层 · 2026-09-06 用户裁决吸收 · 明鉴起草/HR 打磨）
- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: 跨设备身份/发现层 data/discovery/agents/<device>：写入方=心跳代理(hb-fwd/端侧注册器)，读=全体；键 schema v1；心跳驱动单源；G5 活性判定(<90s=online)读侧统一
- 详情: ①命名空间 data/discovery/agents/ 独立于治理域(data/registry)，防写权限混叠 ②写入权仅心跳代理，其余会话只读 ③schema v1 = {device, sessions:[{session_id, role, status, ts}], writer_id, ts}，device/session/role 从 comm_domains + agent_profiles 单源对齐 ④status 枚举(online/offline/unknown) ⑤活性判定统一：读侧心跳 ts<90s=online ⑥PUT 覆盖续期(非 append)，同 device 键幂等(后写胜，无需独占锁) ⑦查不到≠不存在——降级本地缓存 ⑧enforcedBy: review + ErrorNet 周复盘审计


## R035 ✅ 热重启优先·不杀框架（2026-09-10 用户指示 · 星桥提出）
- 分类: 工程 | 范围: all-bus-devices + 服务器化 comm-layer | 状态: enforced
- 摘要: **能热重启的，就不要直接杀死整个框架**——重启粒度最小化：优先"组件级热生效"（刷新页面/重载/单服务重启），其次"只重启目标服务"，最后才考虑重启框架；**任何工具/脚本都不应具备"杀死整个框架"的能力**
- 详情: ①判定顺序：后端文件未变 → 判**热生效、不重启**；确需重启 → 只重启目标服务（白名单内）→ 框架重启须有用户明确授权且尽量选在无活跃会话窗口 ②"不该发生路径"= 为局部目标去杀框架进程；约束须**结构上不可绕过**：服务表冻结常量 + 无 PID/通配/宽杀入口 + 外部命令白名单 ③自证：`--lean4-check` 六项（A 源码无宽杀 / B 负例全拒 / C 正例可用 / D dry-run 零变更 / E 白名单冻结 / F 外部命令白名单）全绿方可交付 ④参考实现：`dsh-collab/devices/dsh-plugin-cldvoice-activate`（R006 十项达标）⑤实证：2026-09-10 MBP 曾两次未经确认远程重启 mac-mini 的 CLD、打断活跃会话；同日后端升级又因 `kickstart -k` 端口竞态需人工兜第二次 → 已工具化，且工具在"后端未变"时主动不重启
- 关联: R006#10（约束前置·不可绕过）/ R034（探照灯·红不挂硬发）/ R030（无验证不陈述）

## R036 ✅ 通道变更治理门（2026-10-02 用户指示「Lean4 机械门而非头痛医头」· 星桥实现 · 业界调研对齐）

- 分类: 工程 | 范围: all-bus-devices + 服务器化 comm-layer | 状态: enforced
- 摘要: **通道变更必须经结构门（channel-gate），通道漂移必须被检测（drift-scan）**——用户观察「端侧为通讯无限爆破、换通道把好通道改坏」的机械化解法，对齐业界（AWS Well-Architected 重试上限 / GitOps 漂移检测 / K8s admission webhook / Nygard 变更回滚原则，调研报告见 vault wiki/research/channel-change-governance）
- 详情: ①变更门 channel-gate：变更单必填 5 字段（channel/action/evidence/rollback/blast_radius）缺一解析期 GateError；通道枚举冻结（枚举外不可表达）；24h 同通道变更 >2 次熔断冻结；回滚点路径形态必须真实存在（Nygard）；门只登记裁决、无执行原语 ②漂移检测 drift-scan：期望矩阵单一来源 JSON（通道规则 v2 §2 机器形态），实测 9 项（端点/进程 argv/进程存活/launchd/token 权限）vs 矩阵，漂移报红 exit 1，只检测不修复（GitOps 分离思想） ③两工具均 R006 十项达标、--lean4-check A-F 全绿 ④实证：2026-10-02 E1 我侧 401 误判差点去修健康通道；E2 MBP 静默停 job 致守护聋 13.5h；E3 D2 回灌注入风暴；E4 历史乱试（降级纪律 v1 起因）
- 自动检查: `node ~/dsh-plugin-channel-gate/cli.js --lean4-check` exit 0 + `node ~/dsh-plugin-drift-scan/cli.js` exit 0（无漂移）+ 留痕 `~/dsh-collab/logs/channel-changes.jsonl` 字段完整（纳入 convention-lean4-check G-C22/G-C23）
- 关联: R006#10（约束前置）/ R035（热重启优先）/ R033（通讯通道治理）/ R034（探照灯）/ R030（无验证不陈述）/ 降级纪律 v1（故障时行为）/ 通道规则 v2（变更语义与矩阵）

## R037 ✅ L3 网络层规则（2026-10-02 用户批准 gap 补课 · 星桥实现）

- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: **L3（Tailscale/Funnel）从「只在 R031 提一句」升级为有规则、有检测的一等通道**——对端 active 与公网入口可达性纳入 drift-scan 矩阵机械检查
- 详情: ①L3 在通道矩阵中的定位：Tailscale 直连=跨设备实时主用，Funnel=公网入口（星台 App），服务器=兜底；三者关系见通道规则 v2 §2 ②drift-scan 矩阵新增两项机械检查：tailscale-direct（对端 macbook-pro-2/desktop-p8e7op1 均 active，命令白名单冻结 /usr/local/bin/tailscale status）+ funnel-public（https 入口状态码 200；TLS 验证仅此可达性探针关闭，注明用途）③首个真实战果（2026-10-02 上线即抓真故障）：Funnel 根路径 502——tailscale serve 的 `/` 后端 127.0.0.1:8765 无服务（000），属环境真实故障非本次改动，待用户处置 ④检测与修复分离：drift-scan 只报，修复经 channel-gate 登记
- 自动检查: 并入 G-C44（drift-scan 0 漂移，现 11 项）
- 关联: R036（变更门）/ R031（通讯永续）/ 通道规则 v2 §2（矩阵）

## R038 ✅ 组件版本注册（E2 schema v1 services 扩展 · 2026-10-02 架构三期 · 星桥实现）

- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: **各设备组件版本随心跳注册进 E2 注册表 services 字段**——读侧一次 GET 拿全矩阵，不再手工互问（2026-10-02 前 node-bridge 版本靠读心跳 payload 猜）
- 详情: ①写入方=心跳代理（hb-fwd），随注册表写时变更刷新；services = {组件: 版本} 采集：node-bridge 心跳 payload ver / dsh-tools 进程 argv / 插件 package.json version / hb-fwd 自身 ②读侧判据：drift-scan 矩阵 e2-registry-services 检查项（必需键 node-bridge/dsh-tools/agent-way 在位）③mac-mini 已部署实测：9 组件版本在位 ④MBP/i9 端侧自注册器接入为后续动作
- 自动检查: drift-scan 12 项矩阵（含 e2-registry-services，0 漂移 exit 0）
- 缺位约定（2026-10-03 MBP 提议，采纳）：必需组件未安装时**键在位、值为 "absent"**（不省略）——省略会被读侧误读为「漏报」
- 关联: R-ERR4（注册表写入权）/ R036（变更门）/ R037（L3 规则）

## R039 ✅ 工具中文描述文档（2026-10-03 用户指示「做任何工具必须要加中文描述文档」· 星桥录入）

- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: **做任何工具必须附中文描述文档**——读者（人，不限于作者）能独立复现；正文必须中文，代码/命令/英文术语除外
- 详情: ①适用范围=一切交付物（R006 插件/CLI/独立脚本/守护进程，不限于十项流程，无例外）②内容最低要求对齐 R006 ⑤：为什么需要（事故/证据）/ 用法（含退出码）/ 达标矩阵 / 坑 / 复现命令 ③文档路径显式声明（R006 插件写 package.json `r006.documented`；独立工具在 README 首行自报路径）④机械判据：文档文件存在 + UTF-8 可读 + 中文字符数 > 100（判据器可后补）；现阶段以 R006 ⑤ 验收 + 本判据人工核验为准
- 自动检查: convention-lean4-check.py **G-C48 doc-cn**（冻结清单 tool-doc-manifest.json 逐项核验，6 工具已登记）+ `doc-cn-check.py --selfcheck` 正反控自证 + 交付时 `doc-cn-check.py <docs文件>` 自检（中文字符数 > 100，可 --min-cn 调阈值）
- 关联: R006（⑤ 文档化）

## R040 ✅ 自查不得自指 + 出包前真实 boot 预演（2026-10-03 MBP 原链路反馈「两代门都不可靠」· 星桥录入）

- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: **任何在 apply() 调用链上执行的检查，禁止再调用 apply()**；真挂载冒烟/集成验证只能由 CLI/CI 入口驱动；**出包前必须真实 boot 预演一次**（dsh web --port 0 看到启动行），发布卡附证据（输出行号/hash）而非声明
- 详情: ①事故链：0.2.8 白名单式 selfcheck 只查列名符号 ⇒ 新符号（os）必然绿（判别力=0，崩溃同刻日志仍写「✅自查通过」）；0.2.9 真冒烟挂在 apply 链 ⇒ 检查者成被检查者下游 ⇒ 自递归死循环（无异常行、只烧 CPU，最难发现一类）②落包规则：apply 链上的检查只做同步、零副作用、零网络（peerDeps/符号扫描/type:module）；冒烟独立入口 runApplySmoke + 防重入守卫 + 子进程隔离 HOME/断网面 ③出包流程：改包 → CLI 自检（含冒烟三态）→ 负控（注入同类 bug 必 fail）→ 真实 boot 预演 → 发布卡附证据（行号/输出片段/hash）④「生产首跑即验收」教训：7 包/5 小时/3 次异常（2 次本包造成）——闸门必须前移到出包侧，对端只做门后复核
- 自动检查: central-inbox cli.js --selfcheck（selftest 16 + 同步自检 + 冒烟三态）/ agent-way selfcheck.js（variants + identity-table + 冒烟）/ post-restart-acceptance.py 冒烟计数==1 断言；负控标准动作=注入裸引用必 fail exit 1
- 关联: R006（⑩ 约束前置）/ R030（无验证不陈述）/ R035（热重启优先）/ R036（变更门）


## R041 ✅ 资源冲突收敛协议（2026-10-03 星桥+MBP 双向对齐）
- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: 对象级资源冲突数据（31 条）迁出账本至 resource-conflict-registry.md；账本只留跨对象行为准则；ruleId 判据改为必须命中「现役 rules ∪ retiredEntries」，防溯源断裂
- 详情: ①31 条对象级占用/冲突=数据→外挂表 ②12 条行为纪律重分类留账本（J29/J33-J45 表）③退役索引 retiredEntries 保 id/retiredAt/retiredBy/movedTo，溯源不悬空

## R042 ✅ 投递状态诚实语义（queued≠送达）（2026-10-04 MBP 对等自查决定性数据 · 星桥 1.5.13 落码）
- 分类: 通讯 | 范围: all-bus-devices | 状态: enforced
- 摘要: delivered=官方回执已收且实测进入对端上下文；queued=发送时刻未达但修复版(1.5.13+)上延迟可达（idle-flush 补投，实测延迟≈6-10 分钟），不是终态、但不得记作已发；queued 不立即换键重投（会制造重复投递），确需重投必须改内容
- 详情: ①根因：deliver() 吞异常静默降级 queued（类别 B）+ autoWake 反风暴空实现后无 idle 触发点 ⇒ queued 终态 ②修法 1→2→3：失败出声 → idle 主动 flushQueue → agentBus.flush 暴露（1.5.13，selfcheck delivery-guard 判据）③判据：delivered 必达、queued 标注未达；verify-delivery 读对端日志结局行闭环；重投换键（同内容判 dup）④「要对方提醒才看到」=提醒触发 flush 的巧合，非送达保证（G18）
- 关联: R005（CCEP）/ R034（探照灯）/ R036（变更门）


## R043 ✅ 拉起/重启类动作必须读回验证（2026-10-04 MBP 事故 #6 · G35 · 6823 更正 · 星桥落码）
- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: 拉起/重启类动作必须读回验证（exit-marker pid/startedAt 更新+进程存活），窗口≥90s、间隔≥5s、开火须等目标进程真正消失；诊断指纹：115-131ms 秒退+exit 0+零输出=单实例锁拒绝启动（锁释放随尝试/时间衰减，实测成功点≈35s）；失败必须留日志
- 详情: ①机制更正（MBP 6823 实测）：非「老实例占锁」非「锁文件残留」——老实例彻底终止后单实例锁数十秒内仍判占用且随尝试/时间衰减（13s 内 4 次 open 全秒退 115-126ms，+35s 成功）②开火绝不固定 countdown+2：重启申请→老实例真退出相隔 25.6s 实测，固定开火=no-op ③窗口 ≥90s/间隔≥5s（旧 19s 窗口假阴性误报需人工）④失败留日志（stdio ignore 排查只能靠 macOS 系统日志）⑤根治：插件热更走壳 v4 POST /reload，整机重启只留给壳变更 ⑥落码：agent-way 1.5.19 + tools/relaunch-cld.sh 10×5s
- 关联: R035（热重启优先）/ R030（无验证不陈述）/ G35 / M3（重启竞态族）


## R044 ✅ 服务器操作规范门（五问必答）（2026-10-04 星桥起草 · MBP 同源）
- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: 涉及 xingqiao 服务器（106.53.214.108）的任何操作，动手前必读协作网络规范第二部分 + 回答五问（锁/门/备份/回滚/验收）；红线：不复活 comm-server-test/不经 ufw 开端口/不删 .bak/不手改 token/不擅动暂停项；做完双板登记
- 详情: ①规范板载键 data/registry/agent-network-charter（含服务器运维部分）②五问：agent_light/agent_lock → channel_gate → 备份 → 回滚 → 验收矩阵留证 ③服务地图变更回改规范并 bump version ④验收矩阵必须打公网面（回环信任坑）
- 关联: R036（变更门）/ R043（拉起读回验证）/ R030（无验证不陈述）


## R045 ✅ 协作网络章程基线（2026-10-04 MBP 起草 · 星桥同源）
- 分类: 治理 | 范围: all-bus-devices | 状态: enforced
- 摘要: AGENT NETWORK CHARTER（data/registry/agent-network-charter）为全员协作基线：本地镜像 + 预检指针 + version 同步纪律 + 冲突上报义务（发现章程与实测冲突先上报，不照做）
- 详情: ①章程=协作规则共识（黑板/通讯/红绿灯/变更门/验证纪律/R042/R043/索引/运营状态）+服务器运维规范 ②镜像判据：逐字取板载原文+sha256 留证 ③冲突上报义务：条款与实测冲突必须上报等修订（例：8634 卡 §6 queued 过期条款）④预检指针单一入口=章程
- 关联: R044（服务器操作门）/ R030（无验证不陈述）

## retiredEntries（R041 退役索引 · 数据搬出账本留痕，溯源不悬空）
- J31 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:R3 插件代码产物共享读
- J32 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:dsh-collab 写权限代写依赖
- J1 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:meituan-multi/data 目录共享
- J2 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:exit-marker/heartbeat 看门狗
- J3 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:**plugin-smoke 临时文件隔离**
- J4 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:**写前通知属主**（登记属主文件防静默多写）
- J5 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:app.db 并发访问
- J6 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:docs 与 kb_outbox 共享读
- J7 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:cld-health 读竞争
- J8 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:health-check --log 追加竞态
- J9 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:双巡检重叠告警
- J10 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:向日葵 MCP 会话独占
- J11 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:插件目录 node_modules 重建
- J12 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:session-storage 全量读域
- J13 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:ChromaDB research 三方写
- J14 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:Ollama bge-m3 嵌入并发
- J15 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:追加类共享文件无锁
- J16 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:端口 3081 归属冲突
- J17 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:健康/巡检三角
- J18 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:vault 多写者文件碰撞
- J19 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:profiles/web 读未持锁
- J20 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:~/.dsh/sessions 读共享标注
- J21 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:media 读写 vs 摄取并发
- J22 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:hub 静态服务属主边界
- J23 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:node_modules 重建 vs 运行映射
- J24 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:xberg 恢复演练 vs 运行态
- J25 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:~/.claude.json MCP 配置源
- J26 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:内存紧张并发构建
- J27 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:profiles/web bundles 行共存
- J28 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:IM 窗口导航冲突（已解决）
- J30 | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:重启窗口集中协调
