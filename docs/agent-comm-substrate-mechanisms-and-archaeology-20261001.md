# 智能体通信底座 · 机制考古与现状全图

> **日期** 2026-10-01 ｜ **节点** mac-mini ｜ **会话** session-fa1f9150（中枢）
> **起因**：用户手动清理约 190 条上下文注入后追问「是不是我们的架构设计存在缺陷？需要重新分析设计？」
> **这份文档的用途**：把「**已经做过的调研** / **已经修过的缺陷** / **今天新查到的机制**」合成一份可索引的底账，
> 让下一次追问不必第 N 次从零推导。**读它之前先读第 0 节，读它之后直接看第 7 节要决策什么。**

---

## 0. 证据约定（先立规矩，因为今天最大的故障是证据不合规）

| 标记 | 含义 |
|---|---|
| ★★★ | **代码行级或对照实验坐实**。给出文件:行号或 A/B 观测值 |
| ★★ | 有观测值，但**未做对照实验**；可能受混杂因素影响 |
| ★ | **推断**，待验证。**不得**据此下结论或动手改 |
| ⛔ | **已被证伪的推论**，留档防止复发 |

**今天两次误判都源于用 ★★ 当 ★★★**（见附录 B）。本系统的存量规则 **R021「行为验证优先，日志缺失≠功能缺失」**
和 **R022「治理工具不得制造同类问题」** 就是为这类错误立的（`docs/queue-tool-storm-incident-postmortem-20260831.md` §5）。

---

## 1. 一句话结论（三条）

1. **今天查到的全部缺陷收敛到一个根因**：身份相关判定（自回声 / 自注入 / 去重键 / @提及 / 审计）**建立在 `from` 字段上，而 `from` 是自由文本——既不校验、又可被硬编码标签覆盖**。它在 **08-28、10-01 被"修过"至少三次**，每次都只修了**站点**，没有修**不变量**。
2. **我们并不缺调研——已至少做过三轮，存量文档自己就写明了**（`A0b-存量调研盘点.md` 标题即「这个题目我们已经做过三次」）。缺的是**把结论接进动作点**：S6 架构评估的 A 级 PoC（订阅唤醒）至今未落地。
3. **成本最大的一项不是"外部智能体说话太多"，而是我们自己的留痕动作触发自我注入**：`repair_report` **每写一份报告，必定绕回写作者自己的上下文一次**（★★★ 有 central-inbox 自己的日志为证）。

---

## 2. 考古时间线（08-17 → 10-01）：做过什么，以及**落地了没有**

| 日期 | 事件 / 文档 | 关键结论 | 落地状态 |
|---|---|---|---|
| **08-17** | `research/compute-optimization/bus-queue-solutions-2026W34.md`（203 行，数据调查员） | **根因不是总线锁，而是上下文膨胀放大了每会话处理时间，队列只是结果**。且发现 DSH **已内置整套 compaction 插件但未挂载** ⇒「解法可能不在换技术路径，而在**把已装好的开关打开**」 | **✅ 已落地**：今日实测 `compaction-basic` / `command-compact` / `tool-result-pruner` **均已在组合树**（dump 第 235/238/297 行） |
| 08-18 | `research/compute-optimization/` 系列、`node-bus-design` | 节点总线设计候选 | 部分 |
| **08-19** | `research/cost-governance/bus-vs-async-comparison.md`（HR 驾驶舱） | 现状本质 = **同步点对点 + 全量上下文 ⇒ 成本平方级**；推荐 **事件驱动总线 + 黑板状态 + 邮箱队列**混合；预期**结构性降本 70–85%** | 部分（黑板在跑，总线/邮箱未建） |
| **08-20** | `research/cost-governance/s6-architecture-comparison-v1.0.md`（69 行，论文支撑） | 四架构成本权重（p2p 1.0 / 黑板写 0.1 / 邮箱 0.05 / 事件总线 0.5 / 广播 10.0）；★「**当前唯一缺口就是「无订阅唤醒」**」；给出 A→B→C→D 分级引入 + A 级 PoC 设计 | **❌ 未落地**（今天实测仍是「无订阅、硬编码单目标注入」） |
| 08-27 | agent-bus `36bb52f v1.0.0 dsh 首个原生插件正式定版`；central-inbox git 初始化 | — | ✅ |
| **08-28** | central-inbox `85b8990 v0.1.1 自注入防护 + 探针噪音过滤` | 判据 `value.from === NODE_ID` 跳过本节点自写消息，「根治 LLM 自动应答无限回声」 | **⚠️ 修过但没修住**（今天证明回路仍活，见 §4） |
| **08-31** | `docs/queue-tool-storm-incident-postmortem-20260831.md`（70 行，星桥） | 为治理队列风暴而做的 queue 工具，**把 121 条历史已处理消息原样回灌** ⇒ 亲手制造了「历史上下文回灌」风暴。**治理工具制造了它要治理的同类问题** ⇒ 立 **R022** | **规则立了，同类回路今天仍在**（用户昨日 truncate 后 145G 回灌即此形态） |
| 09-01 | `research/agent-network-blueprint-candidate.md`（279 行）+ `data/blueprint/agent-network/blueprint-v1.0→v1.3.md` | agent-network 底座**建议立项**；论文清单、框架对比、五大能力域、Rust 化缺口；已点名三条工程债（①上下文只增不减 ②inbox 拼接串行无背压 ③重启唤醒风暴） | 蓝图到 v1.3，**底座未建** |
| 09-05 | M1–M6 根因模式考古 | M1 版本遮蔽 / M2 全量物化 OOM / M3 重启竞态 / M4 插件加载协议不符 / M5 凭旧认知 / M6 不验证 | ✅ 已用于本次诊断 |
| 09-09 | `comm-server/comm-confirmation-chain-v1.md`、`docs/comms-convention-candidates-eval-v1.md` | 两级确认链 `done ⟹ 已delivered ∧ 已agent-processed`；5 条通讯公约候选 | 部分 |
| **09-28** | `research/agent-comm-paths/A0b-存量调研盘点.md`（78 行）、`A1-agent间协议标准.md`（566 行） | ★ **「这个题目我们已经做过三次」**；A2A 协议全景（含「A2A 是否避免『共享可变文档无限追加』」判据）；黑板侧首次量化 | 文档在，**结论未被接进动作点** |
| **10-01** | 双通道路线图 / L1-L2-L3 / CAHAC 增量 / **A4·A4b·A4c·A6 修复** / **本文** | 见 §3–§5 | A 批已改，**待重启生效**（见 §7） |

**读法**：右上角「落地状态」列比左列更重要。三轮调研的结论质量都高，**卡点全在最后一公里**。

---

## 3. 机制全图（现状实测 · 代码级）

### 3.1 两条通道 · 三个载体

| 通道 | 载体 | 写入方式 | 已实测风险 |
|---|---|---|---|
| **A · bus** | `~/.dsh/agent-bus.json` **单文件 20.3 MB**（4050 线程 / 30,771 消息） | 内存 `store` + **整份 `persist()`** | 整份读写 ⇒ 撕裂读与 OOM 风险（M2）；**无过期、无 DLQ** |
| **B · 黑板注入器** | 黑板 KV（09-28 实测 snapshot **79 MB / 56,439 键**，DELETE 仅 116 次 ⇒ **无 GC**）+ `~/.dsh/inbox/` **1945 个平铺文件 / 409 MB** | 事件桥 8803 SSE → 过滤前缀 → `agentBus.send` 注入 | 前缀匹配即注入，**无订阅、无相关性过滤** |
| — | 会话 | `~/.dsh/sessions` **1.1 GB** | 上下文只增不减 |

### 3.2 投递路径（代码级 · `dsh-plugin-agent-bus/lib/index.js`）

```
agent_send.execute(exec.agent.id → from, args.to, text)      :1381
  └─ sendMessage(from, to, text, thread)
       ├─ ① A4  normalizeTo(to) → to = norm[0]                :1111
       ├─ ② A4b 短 id（session-xxxxxxxx）→ 唯一前缀解析        :1125
       ├─ ③ A6  normalizeTo(from) ∩ normalizeTo(to) ≠ ∅ ？→ self-echo（新增）
       ├─ ④ checkDedup(from, tid, text)  → duplicate ?
       ├─ ⑤ store.addMessage(tid, from, to, text)             :1140
       ├─ ⑥ deliver(msg, kind)
       │     ├─ 节点别名（NODE_ALIASES）→ 黑板 notes/<node>/agentbus-*
       │     └─ 否则 agentsSvc.get(to).followup()  ← 真正的上下文注入
       └─ ⑦ 失败 ⇒ msg.status='queued'；flushQueue() 兜底重投   :1087
```

**关键**：`status='queued'` 不是"正在路上"，而是**"解析不到收件人"**。这就是 queued 累积的语义根源。

### 3.3 收件人解析链与三处缺口

`normalizeTo`（`~/dsh-comm-shared/identity.js`）→ 剥括号/via/列表 → 抽 id → `to = norm[0]`。

| 缺口 | 机制 | 实测规模 | 状态 |
|---|---|---|---|
| **A4** | `to` 带显示名后缀/列表 ⇒ `agentsSvc.get()` 精确匹配失败 | queued 中含 `(` 后缀 **52 条** | ✅ 已修（归一化） |
| **A4a** | **`normalizeTo` 第 20 行无条件删括号内容，且发生在 id 匹配之前** ⇒ `明鉴 (a190c54c)` 只剩 `明鉴` | 9 条 | ✅ 已修（先抢救括号内 id） |
| **A4b** | 归一化产出**8 位短 id**，而 `agentsSvc.get()` 需完整 UUID ⇒ 归一化了照样 queued | 纯短 id 形态 **16 种 / 103 条** | ✅ 已修（唯一前缀解析） |
| **A4c** | `broadcast` 收件人**原样入库**未归一化 | 4509 条广播中 **0 条**受害（未激活） | ✅ 已修（同路径） |

★★★ **前缀歧义实证（决定了 A4b 必须 fail-closed）**：会话 id 是**时间序 UUID**，8 位高位前缀会跨会话碰撞。
同一份 agent-bus.json 内实测：`session-e7bfeea8-fa2e-46…` 与 `session-e7bfeea8-7f4c-46…`、
`0e84e65c-d932-43…` 与 `0e84e65c-7f4c-46…`、`f38244df-b6c7-4a…` 与 `f38244df-9225-42…`
**各对应 2 个不同真实会话**。⇒ 歧义时**猜一个等于投递错人**，且回执外观与成功无异。故 `resolveShortId` 歧义一律返回 `null`。

### 3.4 身份与去重（**本系统最脆弱的一环**）

`from` 的三条实测性质（共同构成 §4 的根因）：

1. **不校验**：`deliver()` 只看 `to`，`from` 是自由文本 ⇒ **任何调用方都能自称任何人**
2. **可被硬编码覆盖**：`dsh-plugin-guard/lib/index.js:434`
   ```js
   const value = { title, node, ts, from: "mbp-ops", ... }   // ← 无论谁调用 repair_report，署名恒为 mbp-ops
   ```
   `dsh-collab/scripts/send-repair-report.py:52,79` 同样硬编码 `X-Writer`/`from`
3. **一切身份判定都读它**：自回声守卫、去重键、@提及解析、显示名

**去重机制（键与淘汰是两件事，别混）**：

| 消费者 | 键 | 淘汰策略 | 后果 |
|---|---|---|---|
| `agent-way` | `from｜canonicalTo｜内容指纹`（**不含 thread**）✅ | `Map` + **10 分钟窗口** | 同内容重发间隔 >10 分钟**仍会漏判**（即最初观察到的「相隔 10 分 16 秒」场景，换键后并未被拦住） |
| `central-inbox` | `<key>@<version>` | `BoundedSeen`（**成员集合**，容量淘汰） | 成员资格语义 ✅ |

⚠️ `dsh-comm-shared/identity.js` 的 `dedupKey` 文档**曾声称**两者都用成员集合——**与事实不符，已改准**。
是否把 `agent-way` 也统一到成员集合属**产品决策**（成员集合会永久拦住合法重发），**未擅自变更**。

### 3.5 三条回路（互不相同，别混为一谈）

| 类 | 形态 | 实测规模 | 根因 | 状态 |
|---|---|---|---|---|
| **1** | `from == to == 自身` | **33 条** `fa1f9150→fa1f9150` 的【迭代报告】/【交付修正】，全部 `delivered` ⇒ 千字级报告被注入回**发件人自己的上下文** | 发送侧拿 `isSelfEcho(from)` 判 `from`，而发送时 `from` 恒为调用者自己 ⇒ **语义颠倒** | ✅ 已修（A6 v2：`from ∩ to`） |
| **2** | `from` 为**硬编码伪身份**、`to` 硬编码为中枢（=作者自己） | **每写一份 `repair_report` 必触发 1 次** | 作者身份未被记录；收件人被硬编码 | ❌ **未修**（见下） |
| **3** | `to` 不可解析 ⇒ **永久 `queued`** | queued **2059 条**，其中 **1757 条（85%）超 7 天** | A4/A4a/A4b | ⚠️ 只拦新增，**未回收历史** |

#### 回路 2 的完整证据链（今天新查，★★★）

```
我调用 repair_report
  → guard:434 写入 notes/mac-mini/repair-report-*  {from:"mbp-ops"}   （硬编码署名）
  → 黑板事件桥 8803 SSE
  → central-inbox:3   过滤 notes/<本节点>/*
  → central-inbox:80  收件人硬编码 = 中枢会话 fa1f9150 = 我
  → central-inbox:218 agentBus.send(from, target, text)              （from 直接取卡片字段）
  → bus delivered → 注入我自己的上下文
```

**机械级证据**（不是我推的，是 central-inbox 自己写的日志）：
```
[2026-10-01T16:20:06.649Z] [central-inbox] 📩 注入 mac-mini:
  notes/mac-mini/repair-report-20261001162006-Agent-Bus-Recipient-Resolution-And-Self-Echo-Roo
  → session-fa1f9150-c949-401f-ba8c-d265f6221676 [central] delivered
```
时间戳同秒佐证：卡片 `seq=1790871606⁰⁰⁰⁰⁰¹` 与 bus `time=1790871606⁶⁴⁴` 同属 epoch 秒 `1790871606`。

**为什么 A6 拦不住它**：A6 比的是 `normalizeTo(from) ∩ normalizeTo(to)`，而这里 `from="mbp-ops"`（字面标签）、
`to=我的完整会话 id`，**永不相交**。**不是漏判，是判据不存在**——卡片的真实作者当前**没有任何字段记录**。

**成本量级**：回路 1 是一次性 33 条；**回路 2 是持续性的，报告越勤、自我注入越多**，且注入正文是指针，
逼我**再花一次工具调用**去读一张我自己刚写的卡。§1 第 3 条即由此而来。

#### 回路 3 的构成（用于第 2 步清淤定规模）

| 目标 | 条数 | 最早 | 最新 | 性质 |
|---|---|---|---|---|
| `session-8c2494e0-…` | 1261 | 09-05 | **10-01（今天）** | 单一目标，**仍在被投递**（收件人间歇离线） |
| `cld-monitor` | 157 | 09-05 | 09-09 | 目标已消失 |
| 明鉴（**3 种写法**） | 36+32+25=93 | 09-10 | 09-14 | 同一条命被拆成 3 个桶，均不可解析 |
| `star-bridge` / `bus:i9` | 51 / 23 | 09-06 | 09-09 | 目标已消失 |
| 含 `(` 后缀 | 52 | — | — | A4 历史受害者 |

### 3.6 闸门体系与其空转（**组织层面的机制缺陷**）

R006 十项标准 + R014 自查门是这套体系的"防呆"，今日实测**三处空转**：

| 闸门 | 缺陷 | 证据 | 状态 |
|---|---|---|---|
| `selfcheck.js` ①② | 守卫用 `typeof require === 'function'` 与 `typeof __filename !== 'undefined'`——**在 ESM 下恒为 undefined** ⇒ peerDeps 探测与关键符号检查**双双被跳过**，只跑 ③ `type:module` 却打印 `✅ 自查通过` | ★★★ 负例控制：传入绝不可能存在的符号，`missing` 仍为 `[]` | ✅ 已修（`createRequire` / `fileURLToPath`）+ 新增 `resolved` 字段（顺带成为 **M1 遮蔽探测器**） |
| 两个自检模块**无 CLI 入口** | `node lib/selfcheck.js` / `node lib/selftest.js` **静默退出 0、零输出**，外观与"全过"完全无异 | ★★★ 实测踩中：我一度报"自检通过"，其实什么都没跑 | ✅ 已修（补 CLI 入口） |
| `plugin-preflight.py` A 项 | 只按**目录名**查 `name:<目录名>`，而 agent-way 包目录是 `dsh-plugin-agent-bus`、自报 `name: dsh-plugin-agent-way` ⇒ **0 命中 ⇒ 恒假 NO-GO** | ★★★ 一个永远说"不许"的闸门会被绕过，比没闸门更糟 | ✅ 已修（按自报 name/id 查）+ 补 5 条回归断言（自检 8→13） |
| `plugin-preflight.py` B 项 | 真挂载冒烟**真的执行 `apply()`** ⇒ 在**生产日志**写入痕迹、调 `runSelfCheck`（失败时写黑板告警）、连 SSE。**闸门的探针污染它要测量的对象** | ★★★ 对照实验：`central-inbox.log` 启动行 **224 → 225**（正好 +1） | ⚠️ **未修**（修法明确：`CENTRAL_INBOX_LOG` 指向临时文件即可隔离；见 §7） |

---

## 4. 单一根因：判定建立在**不可信的身份字段**上

把三次"修过"并排放，模式立刻显现：

| 时间 | 位置 | 判据 | 为什么没修住 |
|---|---|---|---|
| **08-28** | `central-inbox` `handleEvent` | `value.from === NODE_ID`（NODE_ID=`'mac-mini'`） | ★★ **`from` 被 guard 硬编码为 `'mbp-ops'`**，永不等于节点名 ⇒ 守卫恒不触发（今天实测回路 2 仍在跑） |
| 09-14 | `agent-bus` 形态闸门 v2.5 | 裸 UUID 形态检查（`^[0-9a-f-]{36}$`） | ✔ 对——但挡的是**形态**不是**身份**（不同问题，修得对） |
| **10-01 早先** | `agent-bus` A6 **v1** | `isSelfEcho(from, _SELF)` | ★★★ 判 `from`，而发送时 `from` 恒为调用者自己 ⇒ **语义颠倒**；仅因 `_SELF.ownSession` 恒为 `''` 才没炸。**一旦有人把 ownSession 填上（v1 注释写的意图），本机发出的每一条消息都会被拦** ⇒ 是哑火地雷 |
| **10-01 本文** | `agent-bus` A6 **v2** | `normalizeTo(from) ∩ normalizeTo(to) ≠ ∅` | ★★★ 修住了 `from==to`（回路 1）；但**修不住 `from` 被伪造**（回路 2） |

### ⇒ 应立的不变量（当前不存在）

> **I-Identity**：每条消息必须携带**可验证的真实作者身份**；所有身份相关判定（自回声 / 自注入 / 去重 / @提及 / 审计）
> **统一读这一个字段**；任何硬编码的展示用别名**不得**进入该字段。

现状 `from` 是自由文本，**四条不变量的载体全部悬空**。这也解释了为什么
`dedupKey(from, to, text)` 会把不同会话的报告判成同一发件人（都叫 `mbp-ops`）——
**键的输入本身是脏的**，键设计得再对也没用。

---

## 5. 量化现状快照（2026-10-01 实测）

| 指标 | 值 |
|---|---|
| `~/.dsh/agent-bus.json` | **20.3 MB** · 4050 线程 · **30,771 消息** |
| 消息状态 | `delivered` 28,712 · **`queued` 2,059** |
| queued 年龄 | **>7 天 1,757 条（85%）** |
| `from === to` 自回路 | **34 条**（今日实测；含我探针新增的 1 条，见附录 B） |
| dedup / approvals | 3 / 33 |
| `~/.dsh/inbox` | **1945 个平铺文件 / 409 MB** |
| `~/.dsh/sessions` | **1.1 GB** |
| `central-inbox.log` | 5,525 行 / 0.7 MB |
| 黑板（09-28 测） | snapshot **79 MB / 56,439 键**；DELETE 仅 116 次 ⇒ 无 GC |

### 验证资产（今日新建/修复，均已跑通）

| 资产 | 结果 |
|---|---|
| `~/dsh-comm-shared/selftest.js`（**新建**，此前该模块**零断言**） | **44 PASS / 0 FAIL** |
| `dsh-plugin-central-inbox/lib/selftest.js`（经 CLI 直跑） | 15 PASS / 0 FAIL |
| `plugin-preflight.py --selftest` | 13 PASS / 0 FAIL（原 8 + 新增 5） |
| 两插件 `plugin-preflight.py` | 均 **GO** |
| **`normalizeTo` 真实语料差分**（改前备份 vs 改后，输入 = 全量 **221** 个真实 `to` 值） | **218 个输出完全一致**；3 个变化**全部为修复目标** ⇒ 零非预期行为改动 |

---

## 6. 与业界机制对照（存量已有，此处只做"我们 vs 缺口"的映射）

来源：`s6-architecture-comparison-v1.0.md`（08-20，论文支撑版）+ `A1-agent间协议标准.md`（09-28）+ 本次新增判据。

| 机制 | 代表性证据 | 我们已有 | 缺口（本系统对应缺陷） |
|---|---|---|---|
| **黑板（共享状态）** | arXiv:2507.01701 bMAS（消息全存黑板 ⇒ 免记忆模块、prompt 变短）；2510.01285 | 黑板 KV 在跑，HLC + `since_seq` + X-Writer 审计 | **无订阅唤醒**；无 GC（DELETE 116 次）；**注入目标硬编码单会话** |
| **Mailbox（文件优先）** | Zenodo:19369171（1744 条签名消息、30 分钟**零协议失败 / 98.8% 成功**）；arXiv:2301.01919 | `~/.dsh/inbox` 平铺文件 | 无状态机、无背压、无容量上限；**1945 个平铺文件** |
| **事件总线** | arXiv:2602.23193 ESAA（append-only + 哈希校验回放）；**2501.05207 CoDe**：异步延迟会误导协作、**甚至差于不通信** ⇒ 事件必须带 ts 并显式处理乱序 | 事件桥 8803 SSE；HLC 时间轴 | 无断点续读契约、无 dedup_key 统一规范 |
| **通信定价** | **arXiv:2608.07532**：贪心边际价值路由达最优效用 **99.5%**，**仅激活 1.96/8 个 agent**，而**全广播仅 38.8%**；2511.13193 拍卖分配发言权 | CAHAC 成本权重（广播 10 / p2p 1 / 黑板写 0.1 / 邮箱 0.05） | **权重有了，选择器没接进动作点** |
| **协议分层** | arXiv:2504.16736：p2p 是**底座而非替代**，各通道应分层组合；2602.11583 Five Ws（who/when/what/why） | 两通道并存 | 当前 `who=全部、when=即时、why=不过滤`（结构性浪费） |
| **保序与乱序** | CoDe（同上） | 事件带 ts | ★★★ **实测踩中**：我的 v1.0 单调游标静默丢弃 **8 条乱序项**（到达序≠时间序，07:37:44 晚于 07:42:38 到达）⇒ 已改集合成员判定 |

**最刺眼的一条**：`2608.07532` 说的"全广播仅 38.8% 效用"，正是我们当前的形态——
**注入进单个中枢会话，既付了广播的成本，又只拿到广播的效用，还把负载压在一个会话上。**

---

## 7. 未解 / 待决（下次动手前先看这一节）

### 7.1 需要用户决策

| # | 事项 | 选项 |
|---|---|---|
| D1 | `agent-way` 去重**淘汰策略**是否统一到成员集合语义 | 统一（彻底防重复宣告，但会永久拦住合法重发）／ 保持 10 分钟窗口（放过迟到的合法重发） |
| D2 | 重启窗口 | A 批（A4/A4b/A4c/A6 + 两处空转闸门）已验证 GO，**待重启生效**；回路 2 抑制要不要并进同一次 |
| D3 | 是否把「投报告给自己」的留痕习惯从机制上取消 | ①修 `from` 记真实作者 + 抑制自我注入（正解，但要动注入器核心路径）／ ②仅改习惯（落本地文件，本文即是） |

### 7.2 未修缺陷（按性价比排序）

| # | 缺陷 | 修法 | 风险 |
|---|---|---|---|
| F1 | **回路 2 自我注入**（每次 repair_report 必触发） | ① 卡片记真实作者（`DSH_SESSION_ID`），`mbp-ops` 降为展示别名；② central-inbox 注入前判「作者==收件人」则跳过；③ `:80` 硬编码兜底后按 `agentBus.list()` 复核 | 动注入器核心路径；需 §7.1 D3 裁决 |
| F2 | **preflight B 项污染生产** | 冒烟时把 `CENTRAL_INBOX_LOG` 等指到临时路径；或断言"冒烟前后生产日志字节数不变" | 低（只改我的工具） |
| F3 | **A5 淘汰策略**（见 D1） | 换 `BoundedSeen` | 产品语义变更 |
| F4 | **queued 2059 条清淤**（85% 超 7 天） | 路线图第 2 步：`expires_at` + DLQ（新 attempt 不覆盖、DLQ 可枚举可回放） | 中；**这是唯一能让 queued 数下降的动作** |
| F5 | **`~/.dsh/inbox` 1945 平铺文件 / 409 MB** | 定位 accumulator 物化点（**至今未识别**）+ 轮转 | 中 |
| F6 | **黑板无 GC**（DELETE 116 次） | 保留策略 + 定期 compact | 中 |
| F7 | **两个注入器并存**（central-inbox + mac-mini-inbox-watch） | 合并；验收标准 = **一卡一次注入** | 中；路线图第 4 步 |
| F8 | `dsh-doc` 声明但静默未挂载 | 依赖写 `link:` 而非 `^0.1.1`；profile patch 里的"只有 config"条目应改为完整 insert，或依赖其自带 bundle patch | 低，独立议题 |
| F9 | 100 个惰性残骸目录（`@deepseek-ai/*.bak/.pnpmcopy`） | 清理（不判红，但污染 C 项信号） | 低 |

### 7.3 已被证伪的推论（⛔ 留档防复发）

| 推论 | 为什么错 |
|---|---|
| ⛔「宿主插件被**热重载**了，所以'改动要重启才生效'这条边界是错的」 | 四条「启动」日志其实是**我自己跑预检**时 `apply()` 的副作用（对照实验 224→225 坐实）；`agent-way.json` 里的 `resolved` 是**我自己的 CLI 测试**写的。**常驻 CLD 进程缓存旧码，重启边界成立**——A6 探针返回 `delivered` 而非 `self-echo` 亦反向证实 |
| ⛔「`from="mbp-ops"` 是 MBP 上的一个智能体在跟我对话」 | `agent_peers` 只有 3 个本机会话，无 `mbp-ops`；它是 `guard:434` 的**硬编码署名标签**。回复它只会得到 `status='queued'` **永久滞留**（静态求值：`NODE_ALIASES` 不含、`agentsSvc.get` 无命中） |
| ⛔「日志里显示 `/opt/homebrew/bin/node` ⇒ 是本地脚本发的」 | Node 默认 `process.execPath` 就是当前二进制路径，而 CLI 里我始终用该路径，**两者是同一个可执行文件**，无法区分来源 |

---

## 8. 附录 A · 证据索引（可逐条复核）

| 断言 | 文件:行 / 命令 |
|---|---|
| 卡片署名硬编码 `mbp-ops` | `~/dsh-plugin-guard/lib/index.js:434`；`~/dsh-collab/scripts/send-repair-report.py:52,79` |
| 注入目标硬编码中枢会话 | `~/dsh-plugin-central-inbox/lib/index.js:80`（自检里 `CENTRAL='session-fa1f9150-…'` 同源） |
| 注入即一次 bus 投递、`from` 取卡片字段 | `~/dsh-plugin-central-inbox/lib/index.js:218` |
| 前缀过滤 `notes/<本节点>/*` | `~/dsh-plugin-central-inbox/lib/index.js:3` |
| 自注入回路实测日志 | `grep "repair-report-20261001162006" ~/.dsh/central-inbox.log` |
| A4/A4b/A6 代码位置 | `~/dsh-plugin-agent-bus/lib/index.js:1111 / :1125 / :1131` |
| 广播收件人未归一化（原文） | 同文件 `broadcast()` 内 `store.addMessage(tid, from, to, text)` |
| `normalizeTo` 括号删除缺陷 | `~/dsh-comm-shared/identity.js` 第 20 行附近（修复注释在原处） |
| 前缀碰撞真实样本 | `agent-bus.json` 中 `e7bfeea8` / `0e84e65c` / `f38244df` 各 ≥2 个不同完整 id |
| selfcheck ESM 死码 + 负例控制 | `~/dsh-plugin-agent-bus/lib/selfcheck.js`；`runSelfCheck('neg',{requiredSymbols:['NOPE']})` → `missing:[]`（修复前） |
| preflight B 项污染生产 | `grep -c "启动 node=mac-mini" ~/.dsh/central-inbox.log` 在预检前后 224→225 |
| A 项恒假 NO-GO | `dsh --dump-config` 输出含 `- id: agent-bus / name: dsh-plugin-agent-way`，不含 `dsh-plugin-agent-bus` |
| 08-28 自注入防护实现 | `git -C ~/dsh-plugin-central-inbox show 85b8990` |
| 08-31 治理工具风暴复盘 | `~/dsh-collab/docs/queue-tool-storm-incident-postmortem-20260831.md` |
| 存量三轮盘点 | `~/dsh-collab/research/agent-comm-paths/A0b-存量调研盘点.md` |
| 论文支撑架构对比 | `~/dsh-collab/research/cost-governance/s6-architecture-comparison-v1.0.md` |

---

## 9. 附录 B · 方法论警告（今天最贵的教训）

**08-31 复盘 §3.1 已写明**：「『日志缺失』→『功能缺失』的错误推断：grep 日志无某字符串 ≠ 功能不存在。
**日志是旁证非真相**。……**确认偏差**：先有结论再找证据，忽略反面铁证。」

**今天我把它犯了两次，且两次都是自己工具的副作用**：

| # | 我的错误 | 我误当成 | 真相 |
|---|---|---|---|
| 1 | 看到 `agent-way.json` 里有新字段 `resolved`（mtime 16:19:53） | "正在跑的插件加载了新码 ⇒ 热重载发生" | **那是我自己 CLI 测试调 `runSelfCheck('agent-way')` 写的**（新进程） |
| 2 | 看到 4 条「启动」日志紧贴我的编辑时间 | 同上 | **那是我跑预检时 B 项真执行 `apply()` 的副作用** |

⇒ **沉淀为判据（建议入规则）**：

> **R-New-1（探针无副作用）**：任何"真挂载/真运行"型验证，必须把副作用**隔离到临时载体**
> （日志、状态文件、黑板键），并在断言里**校验生产侧字节数/键数未变**。
> 一个会写入被测量系统的探针，**不能**用来判断该系统处于什么状态。

> **R-New-2（自己的产物不算证据）**：判定"某机制是否生效"时，
> **必须先用一个已知阳性对照确认观测通道本身可信**（如：先验证"旧码会写 X、新码会写 Y"，
> 再看观测到的是 X 还是 Y），且**排除自己刚才的命令/工具写下的产物**。

**并且**：我那个 A6 自回声探针（`agent_send` 发给本会话）因旧码仍在线而**真的被投递了**，
使 `from===to` 从 33 增至 **34**——**我的验证动作本身往它要测的缺陷里加了一条实例**。
这正是 R022「治理工具不得制造同类问题」的又一实例。

---

*本文由 mac-mini 中枢（session-fa1f9150）于 2026-10-01 整理。所有 ★★★ 断言均附可复核路径；
★/★★ 项已在文中标注，**不得**据此直接动手改。*
