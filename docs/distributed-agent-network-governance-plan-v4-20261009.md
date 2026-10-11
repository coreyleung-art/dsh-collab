# CLD 跨会话跨设备分布式智能体节点网络 · 治理架构管理计划书 v4.0

> **state_version**: 3 ｜ **updated_at**: 2026-10-09T23:58+08:00 ｜ **samples**: 2026-10-08 单日下午 + 观测面不一致主题族（≈195 实例 / 3 会话）；本计划阈值均以此为样本窗，引用须连同样本窗一起引
> **本文件为锚点基线**（连续性信标四件套之①）。配套：索引键 `data/registry/continuity-index` · 续接提示词 `docs/resume-prompt-starbridge-v3.md` · 反遗忘校验 `tools/beacon-check.py`。
> ⚠️ **上述三件在 v1 时是「声明而未建」**（当时只①在位）；2026-10-09T06:4x 由外部第三方补建 ②③④（②双板写+回读 · ③由 `tools/mk-resume-prompt.py` 生成 · ④带 `--selftest` 自证每条判据都能红）。**④ 自启动注入（C4）仍未做** ⇒ M0 不成立。
> **v1→v2 更正账**：① 新增 **P26 会话硬死锁（compaction 下界 > 被遮内容）** 入 §7，并修正 W0.1/G-CR9 的验收判据（见 §7.8）；② 修正 §11 一处**悬空引用**——原文称「全文表见 `continuity-index` 的 `dod` 字段」，实测该字段从未建立（已在索引键里显式记为缺席，**不凭空补全**）。登记人：外部第三方（Claude Code 会话 · CU 实验台线），经用户 2026-10-09 授权。
> **v2→v3 更正账**：① P26 由**推断**升级为**代码核实**——摘要模板**强制 8 段**（`dsh-compaction-basic/lib/index.js:218`）、`BASIC_COMPACT_CONFIG_KEYS`（`:28`）**十把键无一把可改模板/判据**、失败两条路径**不兜底**（`:790` 只告警继续 / `:821` 保留原错误）均已定位到行号；② 补记**「机制一已修、机制二未解」**——2026-10-08 的 `llm-deepseek.maxTokens 65536`（修机制一）与 `standard-compact` 预设**同日落盘**，会话仍于 2026-10-09T05:39 bricked ⇒ 逐字证明「修机制一 ≠ 病好了」，且机制二**无配置解**（只能代码层覆盖）；③ 新增 **R049 上下文存活运营门**（会话限寿 + 交接前置）为本病**唯一保守保命机制**；④ 依据文档 `docs/context-survival-conservative-plan-20261009.md`。登记人：外部第三方（CU 实验台线），经用户 2026-10-09 批准「写」。
> **内容**：复核既有深度调研 + 逐项验收规格 + 沙箱模拟审查 + 独立审查员逐个审查 + 官方规范校对 + CLD 崩溃风险登记 + 连续性信标。
> 治理纪律：本计划自身受 R046（验收门）/ R048（审查协作）/ R022（治理工具不得制造同类问题）约束。

---

# §0 复核结论（既有深度调研 + 能力到位性）

## 0.1 能力到位性（机械复核，判定四态）
✅ **到位**：L2 死形态清理 · L3 TTL/DLQ · 黑板双写+域白名单 · 治理门（验收门/命名门/账本/名册）。
🟡 **在位未生效或不可观测**：L1 限速（32,634 条消息中 `rateLimited` 仅 **1 次**；无计数无日志）· L4 语义合并（无日志）· `antistorm`（名不副实，仅安全启动守卫一行文案 `index.js:740`）。
🔴 **名不副实或缺失**：去重不持久（实测发送侧真重复 **410 组**）· **compaction 在 web profile 未挂载**（`dsh.profile.bundles` 41 项无一项，而 4 个 compaction 包已装在 node_modules）· 黑板**零 GC**（审计 PUT 23,722 / DELETE **0**）· 两个注入器并存 · 无订阅唤醒 · 无 DLQ 重放工具 · **无计划级信标** · 单会话 **256MB**（本会话历史压缩 **50 次**）。

## 0.2 既有「单文件/键空间无限增长」深调研复核：足够深，且有已建成实现
来源 `research/agent-comm-paths/`（**12,101 行**，十七份 A0/A1–A5/B0/C0/C1/C1a/D0/E0/F0–F2/G0–G3 + L0/L1 + 原始笔记）：
- **纠正问题前提**：不是「单键追加」，而是**键空间无 GC**（实测 snapshot 中 list 型键 **0 个** ⇒ 覆盖式写入；「用新键代替覆盖」≡ 往全局日志追加，而该日志是 keyspace 本身，无 MaxAge/MaxMsgs/compaction/GC）。
- **Q1–Q5 五病灶**（§1）。
- **OOM 完整因果链**（一手日志）与**监控测错对象**。
- **跨来源收敛**：**事件 WAL + 确定性投影**（AG2 已核实 append-only MemoryStream + `TailWindowCompact`；ESAA 一族写侧 append-only / 读侧确定性投影 / agent 只读投影）· **TTL/Lease 是唯一不需共识的回收安全点**（三路独立）· **大对象应外置为引用**（三路独立）。
- **Hearsay-II 两条真经验**（一手核实）：① **焦点机制**（限制「此刻执行什么」，非「存什么」）② **「草稿不入共享区」**——把 parse tree 放黑板被原文定性为 *misuse of the blackboard*，改内部结构后**快两个数量级** ⇒ 我方把 `assistant/chunk` **108,692 条**落进会话正是同一错误。
- **已建成 L1**：`~/dsh-collab/comm-server/agent-mailbox.py` **799 行**（`PRAGMA`×8 · `journal_mode`×10 · `busy_timeout`×3 · `BEGIN IMMEDIATE`×3 · `expires_at`×8 · `claim`×49 · 23 函数），报告 41 PASS、导入 30,755 行/3.97s、幂等重跑 0 新增；SQLite **语言中立已实证**（Rust/Python/Node 并发写同一 DB 400/400，integrity ok）。
- **其自认缺口（照录）**：`audience=[]` 未一手核实 · 「压缩能否真解 OOM」未验证 · 404 会话事件数为**体积外推** · **从未复现崩溃**（因果链是证据推断）。

---

# §1 病理模型（Q1–Q5，实测）

| # | 病灶 | 实测 | 本质 | 解法 |
|---|---|---|---|---|
| Q1 | **键只增不减** | 56,439 键 / 累计 DELETE **116** / `data/audit/channel-violations/` 588 键 @1/秒 ×26.7 天 | 键基数失控、无回收路径 | TTL/lease + 周期键改覆盖式 + 大对象外置 |
| Q2 | **写入信噪比极低** | `tasks/i9/results/` 12,891 键中 **12,435（96%）** 为 `ok:true` 且 `output=""` | 缺写前准入/判空 | 焦点机制 + 写前准入 |
| Q3 | **大对象污染 KV** | **19 个 ≥1MB 键 = 全部字节 41%（26.6MB）**，含 1.0–2.3MB PNG 截图 | 缺二进制外置+引用 | 外置为引用（不必换黑板即回收 41%） |
| Q4 | **消息无队列语义** | inbox **1,822 平铺文件**；sessions **1.0GB/413** | 缺分箱/ack/背压/TTL | per-agent inbox 四件套（`queue_size` 满则拒 + `retention_s` + `expires_at` + `since_msg_id`） |
| **Q5** | **会话事件数 ⇒ OOM** | 星桥 **11,777,249 events / 185MB 压缩 / 0.44GB 解压**；compaction 仅跑 **14 次**；`CRASH 67 / SIGKILL 17`（09-09→09-24） | **长度本身**（非噪声） | 挂载 compaction + 约束钉住 + 监控改对象 + 装载前拒绝；中期改投影 |

---

# §2 因果链（含失忆与自设计）

**直接机制**（代码级）：
```
agent_send(from,to,text)   dsh-plugin-agent-bus/lib/index.js:1381
 └─ ① normalizeTo(to):1111 ② 短id前缀解析:1125 ③ 自回声检查(normalizeTo(from)∩normalizeTo(to))
    ④ checkDedup（内存窗口 10 分钟）⑤ store.addMessage:1140 ⑥ persist()（整份 22.8MB；实测三次 `Unterminated string` 撕裂读）
    ⑦ flushQueue() ⑧ deliver → agentsSvc.get(to).followup()   ← 注入完整上下文并唤醒一个回合
```
**放大器**：A1 平方级成本（19 天 26B tokens；agent_send 占工具调用 61.8%）· A2 上下文只增不减（某会话 10,701 条中 72% 是碎片/tool 块）· A3 inbox 逐条 splice（160 次）· A4 无订阅唤醒 · A5 两个注入器 · A6 去重不持久 · A7 无熔断无优先级 · A8 治理工具可制造同类问题（08-31 回灌 121 条）· **A9 自设计 + 重启失忆（本会话压缩 50 次）+ 半修被记为已修**。
**根因（08-17 实测原话）**：**「根因不是总线锁，而是上下文膨胀放大了每个会话的处理时间，队列只是结果。」**
**Q5 链条（09-28 一手）**：协调者角色收全网报告 ⇒ 累计 1,178 万事件 ⇒ 装载实例化 ~1,180 万对象 ⇒ 超 V8 堆上限 **4192MB**（pointer compression 硬顶，**调大 heap 无效**）⇒ SIGABRT ⇒ `dsh-crash-after-child` 拖垮 CLD；而监控只看本体（崩溃前 10 分钟本体 RSS 平的 105MB）。

---

# §3 最优性评估

## 3.1 L1 载体：SQLite/WAL 为当前最优
| 候选 | 崩溃安全 | 并发/claim | 语言中立 | 运维重量（1 vCPU/957MB） | 有界手段 | 我们已有 | 判定 |
|---|---|---|---|---|---|---|---|
| **SQLite+WAL（既有 L1）** | 强（WAL+`BEGIN IMMEDIATE`） | 事务级 claim | **已实证** | **零**（嵌入式） | `expires_at`+vacuum/覆盖式 | **799 行+41 PASS** | ✅ **最优** |
| append-only JSONL 分片 | 中 | 弱（需自造锁/claim） | 强 | 零 | 需自造 rotation | 无 | ⚠️ 次优（先前误选，已废弃） |
| NATS JetStream | 强（WorkQueue: first ack removes for everyone，已核实） | consumer ack | 强 | **+1 进程**；★限额默认 unlimited | MaxAge/MaxMsgs+Nats-TTL | 无 | ⚠️ 备选（L2/规模化；**必须显式设限额**） |
| Redis Streams | 中 | XACK+XAUTOCLAIM | 强 | +1 进程 | `MAXLEN ~`/`XTRIM ACKED`（默认不裁） | 无 | ⚠️ 备选 |
| Kafka compaction | 强 | 分区消费 | 强 | 重（JVM） | **体积上界=key 空间** | 无 | ❌ 过重 |
| CRDT | — | — | — | — | **无天赋**（eg-walker：图单调增长） | 无 | ❌ 不解决有界 |

**架构**：L1 设备内（SQLite/WAL，热路径零网络）· L2 跨设备（信封传递，`comm_domains` 前缀单一来源）· L3 服务器（中继+收敛点+健康裁决；**非投递权威**）。

## 3.2 会话（Q5）双层解法
短期 P0：挂载 compaction + **约束钉住**（不先抽约束，压缩后违规率 0%→30%，`arXiv:2606.22528` 已核实）+ 监控改对象 + 装载前拒绝。
中期：会话改**投影**（写侧 append-only、读侧确定性投影、agent 只读投影）。未知项：压缩后是「投影」还是「截断」决定能否恢复会话语义 ⇒ **必须 POC**。

## 3.3 明确不做
❌ 不为「注入风暴」引学术方案（该词 arXiv 0 命中）——当工程可观测性问题治。
❌ 不假设「换载体就安全」（JetStream unlimited / etcd '0' / Redis 不裁三条默认值证明相反）。
❌ 不跳过 POC 直接落地。
❌ 不全量迁 A2A/ANP/Coral（产业级协议**无一做 per-agent inbox**；只借设计模式）。
❌ 不用 CRDT 求有界。

---

# §4 连续性信标体系（治「计划失忆」）

## 4.1 四件套
| 件 | 载体 | 判据 |
|---|---|---|
| ① 锚点文档 | 本文件 | 头部 `state_version` 单调递增；`samples` 在位 |
| ② 单一索引键 | 黑板 `data/registry/continuity-index`（双板+回读） | 可解析；`closed_with_evidence` 项必有可解 `evidence` |
| ③ 续接提示词 | `docs/resume-prompt-starbridge-v3.md`（≤40 行）+ 生成脚本 | 新会话按前 3 步复述出「当前 wave + 下一步」 |
| ④ 自启动注入 | agent preset prompt section | 新会话首回合即引用索引键 |

## 4.2 状态机与闭环三要素
`open → in_flight → closed_with_evidence →(回归) regressed → in_flight`；旁支 `blocked(reason,owner,next_action)`。
**closure 三要素**：**DoD（含边界+负控）** · **evidence（可解指针）** · **verifier（第三方，禁自证）**。

## 4.3 半修防护与证伪门
半修可检形态：① 激活计数 0 且无日志 ② 依赖装了没挂载 ③ 修站点不修不变量 ④ 声明面 > 证据面。
**半修清单（9）**：compaction 未挂载 · antistorm 名不副实 · L4 无日志 · L1 几乎未触发 · `from` 三次「已修」 · 端口漂移第 5 次 · 两个注入器 · 黑板无 GC · inbox 物化点未识别。
**⛔ 证伪清单（6）**：热重载不成立 · `mbp-ops` 非真人（硬编码署名） · `/opt/homebrew/bin/node` 不区分来源 · 留痕层不能判投递层 · 「一律对 version 偏移告警」（噪声 27.8–53.4%）· 「`dv>0` 可作判据」（18.4% 噪声级）。

## 4.4 反遗忘校验（每次启动/新会话必跑）
索引 ↔ 锚点 `state_version` 比对 · 与 `~/.dsh/continuity-last-version` 比对（回退即告警）· `closed_with_evidence` 的 evidence 可解性抽检（**本轮已实测过 evidence 因归档轮转而不可解**）。

## 4.5 自设计安全 S1–S5
S1 四步变更（备份→暂存→窗口应用→启动冒烟失败自动回滚）· S2 在役身份可观测（`runtimeVersion`/`std`/cdhash）· S3 不可自审 · S4 崩溃即回滚 · S5 一次一变量。

---

# §5 审查流水线（沙箱模拟审查 + 独立审查员逐个审查 + 信息包）

## 5.1 三段式（缺一不得记 closed）
```
① 自证（作者）       跑自检/负控/边界，产出证据
② 沙箱模拟审查（隔离）在隔离环境复跑同一产物，断言不触碰生产路径
③ 独立审查员审查      一件一裁（禁打包批量），按 §5.3 信息包给足信息
```
**裁决三态**：通过 / 不通过 / 未证（R046）；未证不得记 closed；作者不得自审。

## 5.2 沙箱模拟形态（按产物类型）
| 产物类型 | 沙箱做法 | 必测 |
|---|---|---|
| 插件（P2 常驻/树外） | 复制 profile 到临时 DSH_HOME → 挂载 → `--dump-config` 验证组合 → 真挂载冒烟（不写生产 profile）→ 「不该发生路径」拒绝证明 | 只读/可写能力清单；拒绝码；依赖两级解析 |
| 脚本/CLI | 临时目录 + 假输入；**断言未写生产路径**（路径白名单比对）；幂等复跑 | 幂等；失败态 exit≠0；无静默成功 |
| 配置/组合（profile/cordis） | 复制 profile → 改动 → `dump-config` 前后比对 → 再决定是否上生产；红线文件走 `dsh plugin add` | 组合树差异可解释；无「patch entry not found」 |
| 数据/迁移（如载体换） | 影子库导入对账 → 杀进程完整性 → 并发写 → **回滚演练** | integrity_check；并发不丢；回滚可执行 |
| 观测/判据工具 | 合成输入正例+负例+边界；**负控必须能红** | 负控红；未知不并入任何一侧 |

## 5.3 信息包规格（给独立审查员「足够信息量」，14 项）
1 目标与范围 · 2 **声明面** · 3 **未测面**（R046 必填）· 4 全部产物路径 + **版本 + sha256 + 生成时刻** · 5 **自包含复跑命令**（禁引用 /tmp 等易失路径）· 6 负控结果（能红的证据）· 7 边界用例结果 · 8 **官方规范引用**（条款+来源）· 9 已知未覆盖项 · 10 **回滚点 + 回滚演练结果** · 11 **提问清单**（要它裁什么）· 12 样本窗 · 13 机制激活证据 · 14 载体身份（onDisk vs inService）。
**硬要求**：不得只给概述——审查员必须能读到实现（源码路径+行号）；数字须带分子/分母定义。

## 5.4 禁止事项
不自审 · 不打包批量裁 · 未评审不上生产 · 不给概述代实现 · **不以「重复投递」标签替代内容比对**。

---

# §6 dsh 官方规范校对流程

## 6.1 强制前置
1. 跑 `guard_doc_check`（本地官方镜像 `~/tech-research/dsh-docs`，24h 留证 `gate-state.json`）；
2. 镜像无命中且需落地 ⇒ 官方来源 web 补证后再动；
3. 产物记录「官方条款 → 我们的设计 → 差异（一致/未覆写/未证）」。

## 6.2 权威来源与核对点
| 主题 | 官方来源 | 核对点 |
|---|---|---|
| 配置项与类型 | `config-catalog.md` | 例 `@deepseek-ai/dsh-host-webserver`：`host: '127.0.0.1'\|'0.0.0.0'` · **`port: number`（0=OS 随机）** · `compression` / `compressionLevel` / `compressionThresholdBytes` |
| 架构与端口 | `architecture.md` | **Desktop 默认端口 19387，profile 配置可覆盖** ⇒ 端口固定化官方路径 |
| 插件 DSL | 官方工具 schema 规则（10-06 实测汇总） | **根节点禁 `required`** · `type:"object"` 必须显式布尔 `additionalProperties` · `type` 单字符串 · 数组 `items` 禁 `required` · `defineTool` 的 `output.render` **必需** |
| 插件挂载 | 官方路径 | `dsh.profile.bundles` / `link:` 依赖 / `cordis.patch.yml` insert 三处一致 |
| 会话与上下文 | compaction 插件族 | `dsh-compaction` / `-basic` / `dsh-command-compact` / `-tool-result-pruner`（`thresholdChars=8192` / `head=4096` / `tail=1024`） |
| GUI/运行模式 | 官方 `postmortem/0003` | **当前 URL 与运行模式须可被 shell 查询**；**不得**另起不受管理的 `dsh web` |

## 6.3 纪律
- 引用须**连同限定域**一起引（本日已发现三次「丢限定语」属系统性）；
- 官方文档亦可能过期 ⇒ 引用附**镜像时点**，落地前 POC；
- 差异必须显式声明，禁静默偏离。

---

# §7 CLD 崩溃风险登记（已复现确定的坑 → 逐条设门）

## 7.1 插件树加载类
| # | 触发 | 症状 | 根因 | 证据 | 门 | 回滚 |
|---|---|---|---|---|---|---|
| P1 | 任一插件 import/`apply()` 抛错 | **整棵插件树失败** + `installFailLoud` exit(1)，连续崩溃卡启动 | loader `Promise.allSettled` 收齐整组再抛 `AggregateError` | `docs/cld-boot-and-session-list-fix-20261006.md` §2.1 | **G-CR1** | 移除插件行 |
| P2 | 缺原生绑定 | `dsh-doc` 缺 `@xberg-io/xberg-darwin-arm64` | 依赖未写 `link:` | 同上 index 170 | G-CR1 | 补绑定/改 link |
| P3 | output schema 根级 `required` | `gov`/`gate` 加载失败 | 官方 DSL 根节点禁 `required` | 同上 index 171/172 §2.2 | **G-CR2** | 改 schema |
| P4 | 用不存在的 API + 无 `inject` | `knowledge-tools` 加载失败 | API 漂移 | 同上 index 173 | G-CR2 | 重写 defineTool |
| P5 | bundle/包名三处不一致 | 启动崩（手册崩溃 #3） | 目录名 / `package.json name` / patch `name` 必须一致 | `~/Desktop/归档/2026-08-18/DSH-macmini-防崩溃运维手册.md` | **G-CR3** 命名门 N1–N3 | 改至一致 |
| P6 | bundle 缺失 | 启动崩（手册崩溃 #1） | 打包不完整 | 同上 | G-CR1 | 重建 bundle |
| P7 | `patch entry not found` | dump-config 警告、条目空转 | 只写 config 无完整 insert | 存量已知 | G-CR2 | 改完整 insert |

## 7.2 模块实例分裂（遮蔽）类
| # | 触发 | 症状 | 根因 | 证据 | 门 | 回滚 |
|---|---|---|---|---|---|---|
| P8 | profile 有 `@deepseek-ai/*` **物理目录** | `dsh-tools` 双实例 ⇒ Symbol 不一致 ⇒ **每回合 `reading 'prepare'`** | loader 锚=profile、运行时内部 import 锚=运行时 | `docs/cld-tools-instance-split-fix-20261006.md` §2 | **G-CR4** | 移走遮蔽 |
| P9 | 同上 | 客户端 `dsh-client-runtime` 旧版 ⇒ **会话列表全空** | profile 旧副本被服务 | `docs/cld-boot-and-session-list-fix-20261006.md` §3 | G-CR4 | 软链回运行时 |
| P10 | **去遮蔽顺序错** | `ERR_MODULE_NOT_FOUND` 启动崩 | 树外插件自有软链指向被移走的 web 遮蔽 | 同上 §5 | **G-CR5**（先重指→再移走） | 恢复链接 |
| P11 | `build-bundle.sh` 制造物理副本 | 新遮蔽 | 脚本注释原文「peerDependencies 物理副本（从 CLD runtime 拷，**避免符号链接**）」 | `scripts/build-bundle.sh:2,29` | G-CR4 | 去遮蔽 |
| P12 | 100 个惰性残骸目录 | 不崩但污染信号/易回流 | 历史备份未清 | 存量已知 | G-CR4 | 归档清理 |

## 7.3 签名与 dylib 类
| # | 触发 | 症状 | 根因 | 证据 | 门 | 回滚 |
|---|---|---|---|---|---|---|
| P13 | `install_name_tool` 后未重签 | **SIGKILL exit137**（无报错），表现为 `Timed out waiting for dsh web to announce its URL` | dlopen 签名无效 ⇒ AMFI 杀进程 | 10-06 报告 §2.3（`libaom.3.dylib`/`libheif.1.dylib`） | **G-CR6** | `codesign --force -s -` |
| P14 | 逐二进制签名遗漏嵌套 Mach-O | 公证/启动失败 | `--deep` 不足 | 我方公证三轮（24 个 Mach-O） | G-CR6 | 全量重签 |
| P15 | 重签后 TCC 权限重置 | 每次启动弹辅助功能授权 | 权限绑定代码签名 | 实测（残留多条目 ×3） | **G-CR7** | 重置+重新授权 |

## 7.4 内存/事件数类
| # | 触发 | 症状 | 根因 | 证据 | 门 | 回滚 |
|---|---|---|---|---|---|---|
| P16 | 会话事件数过大 | `MarkCompactCollector: young object promotion failed` ⇒ SIGABRT ⇒ `dsh-crash-after-child` | 装载 ~1,180 万对象 > V8 堆上限 4192MB（pointer compression 硬顶；**调大无效**） | `~/.cld/logs/dsh-web.log`（OOM ×13）+ 09-28 报告 Q5 | **G-CR8 装载前拒绝** + G-CR9 挂载 compaction+约束钉住 | 归档重建+记忆继承包 |
| P17 | 监控只测本体 | 崩溃前无告警（本体 RSS 平的 105MB） | OOM 在 dsh 子进程 | 09-28 报告 §2.3 | **G-CR10** | — |

## 7.5 热重载/升级类
| # | 触发 | 症状 | 根因 | 证据 | 门 | 回滚 |
|---|---|---|---|---|---|---|
| P18 | `POST /reload`（31888） | `main.js:462 reading 'reloading' undefined` 崩 | 热重载路径缺陷 | 崩溃三模式① + 08-31 事故 | **G-CR11** | 不用即安全 |
| P19 | 运行中改 `app.asar` | `main.js:440 resolveUrl not a function` | 升级引入 + 初始化时序 | 崩溃三模式② | **G-CR12** | 还原 `.bak` |

## 7.6 动态插件沙箱类
| # | 坑 | 事实 | 门 |
|---|---|---|---|
| P20 | 无 `setTimeout` | 用 `ctx.get('timer')` | G-CR13 |
| P21 | `ctx.get('tools')` 是 façade | 只有 register/schemas/get，**无 guard** | G-CR13 |
| P22 | 动态沙箱 `webServer.register` 不生效 | 须 reactive 注册（`ctx.on('internal/service')`） | G-CR13 |
| P23 | client inject 未声明服务 | 静默失效 | G-CR13 |

## 7.7 运维/端口类
| # | 问题 | 症状 | 门 |
|---|---|---|---|
| P24 | `--port 0` = OS 随机 | 每次重启换地址（6 个历史端口）⇒ 用户侧 `Failed to fetch` | **G-CR14** 端口固定 |
| P25 | 重启语义 SIGTERM=关闭不自动拉起 | 需手动打开 | **G-CR15** 重启票 |

## 7.8 会话上下文/压缩类（**v2 新增**；P16 的同族不同病）
| # | 触发 | 症状 | 根因 | 证据 | 门 | 回滚 |
|---|---|---|---|---|---|---|
| **P26** | 活跃窗口已瘦到**低于压缩器自身开销** | **不崩**、进程与 CLD 均存活，但该会话**再也发不出请求**：`CONTEXT_WINDOW_EXCEEDED`（超 3,242 token，**全来自 completion 预留**）；自动 + 手动 `compact` **各失败一次**，报 `summary is not smaller than the shadowed content (3435/3450 ≥ 2466)` ⇒ **会话内唯一自救路径关闭** | 压缩判据「摘要必须小于被遮内容」的**必然推论**：待遮内容 2,466 < 压缩器开销 3.4k ⇒ **存在一个下界，越过它 compaction 永久失效** | `docs/compaction-lowerbound-crash-20261009.md`（一手 JSONL：`session-fa1f9150-…`，03:03:28 / 03:06:16 / 05:39:52 三条） | **G-CR16** 请求前 token 预算门 + **G-CR17** 压缩有效性门（降幅 ≤0 ⇒ 告警，不静默重试） | 会话外接手（新会话 + 锚点）／归档重建 |

**与 P16 的分界（别混成一条）**：P16 是**崩溃**（SIGABRT，操作系统杀）；P26 是**不崩的死锁**（谁都没杀它，是它自己再也张不开嘴）。
⇒ **P26 不被现有崩溃监控覆盖**（崩溃监控只看"有没有死"，看不到"活着但发不出请求"）。

⚠️ **P26 修正 W0.1 / G-CR9 的验收判据（本类是 v2 最重要的产出）**：W0.1 现判据为「**触发 ≥1 且体积降 ≥50%**」——
P26 形态下**触发了、降幅为负**，该判据会**给出绿**。**必须补负控**：
> **负控**：构造「活跃窗口已低于压缩器开销」的会话 ⇒ **必须判「压缩不可用」并告警**；若判「已压缩」或静默通过，本条**不得记 `closed_with_evidence`**。

**v3 补记（2026-10-09，P26 代码核实 + 修法账）**——把 P26 拆成**两个机制**，别再当一条：

| 机制 | 内容 | 代码位置 | 配置能修吗 |
|---|---|---|---|
| **一 · 阈值不可达** | 压力阈值 `floor(contextWindow × thresholdRatio)` 默认 `floor(1e6×.8)=800,000`，而消息侧可达上限仅 `1,048,576 − 256,000(适配器默认 completion 预留) = 792,576` ⇒ **压力检查永远晚于溢出，主动压缩从不触发** | `dsh-compaction-basic/lib/index.js:13` · `dsh-llm-deepseek/lib/index.js:1735` | ✅ **已修**：`~/.dsh/settings.yaml:62` 的 `maxTokens 65536` ⇒ 上限升到 983,040，留 183,040 余量 |
| **二 · 模板地板**（**终局死因**） | 摘要**强制 8 段**且 "never drop a section" ⇒ 摘要体量有结构性下界；判据「摘要必须小于被遮内容」（`:556`）⇒ 活跃窗口低于该下界时**压缩在数学上永久失效** | `:218`（8 段指令）· `:322`（`frameSummary`）· `:556`（判据） | ❌ **无配置解**：`BASIC_COMPACT_CONFIG_KEYS`（`:28`）**十把键无一把可改模板或判据**；源码 docstring `:231` 自述 "Override this sole hook" = 仅**代码层**可覆盖 |

**决定性时间线（本补记的立论）**：`maxTokens 256000→65536`（机制一之修）与 `standard-compact` 预设**同为 2026-10-08 落盘**；会话 `session-fa1f9150` 仍于 **2026-10-09T05:39 bricked**，报的正是**机制二**的 `summary is not smaller than the shadowed content (3435/3450 ≥ 2466)`。
⇒ **「修了机制一 ≠ 病好了」有一手证据**；且换不换 `standard-compact`（Q-F）**只能扩大机制一的余量，治不了机制二**，因为 `thresholdRatio` 管的是「多久压一次」不是「能不能压成」。

**失败路径均不兜底（代码核实）**：压力路径抛错只 `logger.warn("…; continuing the turn")` 继续本轮（`:790`）；溢出恢复抛错 `"…preserving the original request error"` 保留原错误（`:821`）⇒ **不崩、不自救、不被崩溃监控覆盖**。

**本病的保守保命机制 = R049（上下文存活运营门：会话限寿 + 交接前置）**——在活跃窗口到达下界**之前**交班，让机制二没有发作机会。执行依据：`docs/context-survival-conservative-plan-20261009.md`；一手证据：`docs/compaction-lowerbound-crash-20261009.md`。**治本**须自研「无摘要、按构造必减」的后端（照 R006 交付）。

## 7.9 预防门汇总（结构约束，可机器校验）
**G-CR1** 插件变更→沙箱挂载+dump-config+真挂载冒烟三态 ｜ **G-CR2** schema/DSL 过官方规则 ｜ **G-CR3** 命名门 N1–N3 常驻 ｜ **G-CR4** 依赖操作后扫遮蔽（含 `.bak/.pnpmcopy`）｜ **G-CR5** 去遮蔽顺序固定（先重指树外插件软链→再移走）｜ **G-CR6** dylib/binary 改动后逐个验签（含 `Resources/**/node_modules`）｜ **G-CR7** 重签后 TCC 流程 ｜ **G-CR8** 装载前事件数门（拒绝而非崩）｜ **G-CR9** compaction 挂载+约束钉住（**v2：判据须含 P26 负控**）｜ **G-CR10** 子进程内存监控 ｜ **G-CR11** 禁用/沙箱验证 31888 reload ｜ **G-CR12** 不动运行中的 app.asar ｜ **G-CR13** 动态插件只用沙箱原语 ｜ **G-CR14** 端口固定 ｜ **G-CR15** 重启票流程 ｜ **G-CR16** 请求前 token 预算门（含 completion 预留；超限须指出超额来自哪一侧）｜ **G-CR17** 压缩有效性门（记录降幅；降幅 ≤0 ⇒ 会话级告警）。

---

# §8 目标、原则、成本模型

**七目标**：G1 可信 · G2 有界 · G3 可退 · G4 根因受控 · G5 可观测 · G6 可治理 · **G7 连续性**。
**六原则**：① 优势优先 ② 开源优先→过渡自研 ③ 判据先行 ④ 不得制造同类问题（R022）⑤ 不依赖记性 ⑥ **一切产物先沙箱模拟、再经独立审查员逐个审查（信息包给足）**。
**成本权重**（CAHAC §5.2）：广播 10.0 ≫ p2p 1.0 > 事件总线 0.5 > 黑板写 0.1 / 读 0.05 > 邮箱 0.05。

---

# §9 架构（L0–L6 + I1–I4）

```
L6 连续性层  锚点·索引·续接·自启动·反遗忘·证伪门
L5 治理层    规则账本·验收门·命名门·名册·样本窗·审计留痕 + §5 审查流水线 + §6 官方校对门
L4 观测层    storm_score·队列滞后·机制激活计数·子进程内存·装载事件数·cron·告警
L3 上下文层  compaction（必须挂载）+ 约束钉住 + 体积/事件数 SLO + 投影（中期）
L2 拥塞层    反压·token bucket·优先级/公平·熔断·泄洪态
L1 传输层    SQLite/WAL 邮箱（已建）+ 持久幂等键 + DLQ + 信封 + 时序
L0 节点层    节点注册·心跳 SLO·HMAC 身份·归属双载体·端口稳定
```
**I1** 载体不得整份读入回写（零 torn read）· **I2** 入站串行（活跃 claim≤1）· **I3** 失败谱系（新 attempt 不覆盖，DLQ 可枚举可回放）· **I4** 投递≠消费（`done` ⟹ delivered ∧ agent receipt）。

---

# §10 WBS（30 项）

- **Wave S（门，适用于其余每一项）**：S1 沙箱模拟框架 · S2 信息包模板 · S3 独立审查员逐个审查流程 · S4 官方规范校对门 · S5 G-CR 十五条校验脚本。
- **Wave C（信标）**：C1 索引键 · C2 锚点文档 · C3 续接提示词 · C4 自启动注入 · C5 反遗忘校验 · C6 状态机登记（对齐 `item-validity-review-check` 五态）· C7 证伪门与半修清单。
- **Wave 0（开关合上+可观测）**：W0.1 挂载 compaction + 约束钉住 · W0.2 定位现存压缩来源 · W0.3 机制激活计数 · W0.4 注入器合并 · W0.5 子进程内存监控 · W0.6 装载前事件数门。
- **Wave 1（P0）**：W1.1 持久幂等键 · W1.2 熔断 · W1.3 根因指标（事件数实测）· W1.4 floodgate 改造 · W1.5 L4 可观测化 · W1.6 `expires_at`+DLQ · W1.7 accumulator upsert+rotation · W1.8 定位 inbox 物化点。
- **Wave 2（结构性；含唯一高危）**：W2.1 token bucket · W2.2 优先级/公平 · W2.3 inbox 分箱四件套 · W2.4 泄洪态 · **W2.5 载体换 SQLite（独立窗口+回滚演练）** · W2.6 DLQ 重放 · W2.7 两级确认 · W2.8 大对象外置 · W2.9 TTL/lease · W2.10 周期键改覆盖式+历史另存。
- **Wave 3（可信）**：W3.1 X-Writer HMAC · W3.2 identitySource 入卡 · W3.3 归属四级分档。
- **Wave 4（跨设备/载体）**：W4.1 端口固定 · W4.2 黑板 GC · W4.3 ts+HLC · W4.4 换代率告警 · W4.5 凭据纪律 · W4.6 订阅唤醒 PoC。
- **Wave 5（长期）**：W5.1 判据入工具 · W5.2 规则标样本窗 · W5.3 能力前置清单 · W5.4 名册扩席 · W5.5 会话改投影 · W5.6 OTel。

---

# §11 验收标准（八字段 + 六者齐备规则）

**八字段**：`正向判据` · `负控（必须能红）` · `边界用例` · `测量方法与样本量` · `阈值与判定规则` · `证据形态` · `审查员` · `沙箱复跑方式`。
**通过规则**：正向 ∧ 负控红 ∧ 边界不崩 ∧ 阈值达标 ∧ 沙箱复跑一致 ∧ 官方条款无未声明差异 —— **六者缺一不得记 `closed_with_evidence`**。

代表性条目（全文表见 `data/registry/continuity-index` 的 `dod` 字段）：

| 项 | 正向 | 负控 | 边界 | 样本/测量 | 阈值 | 证据/审查员 | 沙箱复跑 |
|---|---|---|---|---|---|---|---|
| S5 G-CR 门 | 15 条门各有可跑校验 | 造「遮蔽目录」「根级 required」「未重签 dylib」⇒ 必须红 | 干净仓库应全绿 | 3 类 ×2 | 3/3 红、0 误红 | 校验输出 / 独立复核员 | 临时仓库 |
| C5 反遗忘校验 | 一致时 exit 0 | 版本不一致 / evidence 被删 ⇒ 必告警 | 索引不存在 | 4 用例 | 4/4 | selftest / 独立复核员 | 合成 fixture |
| W0.1 挂载 compaction | dump 三行 + 新 `compaction/*` 事件 | 不挂载 ⇒ 事件数继续单调增（对照） | <1MB 不触发 | 前后各 1 次激活 | 触发≥1 且体积降 ≥50% | dump+事件计数 / 裁判 | 复制 profile |
| W0.6 装载事件数门 | 超阈值**报错而非崩** | 阈值内必须放行 | 恰好阈值 | 3 例 | 拒绝率 100% | 拒绝日志 / 裁判 | 合成超大会话 |
| W1.1 幂等键 | 重启后重放 0 重复；>10 分钟重发被抑制 | 不同内容/首次必放行 | 空/超大内容 | 每条 5 例 + 重启 | 抑制 100%、误伤 0 | 边车+注入记录 / 裁判 | 临时边车 |
| W2.5 载体换 | I1–I4 成立；30,755 行一致；幂等重跑 0 新增 | 中途 kill ⇒ integrity ok；3 语言并发 400 行全在 | 空库/超大/超时 | 各 ≥1 | integrity ok、400/400 | 迁移日志 / 裁判（独立窗口） | 影子库+回滚演练 |
| W4.1 端口固定 | 3 次重启地址不变 | 改端口后旧地址应失效 | 端口被占用 | 3 次重启 | 3/3 不变 | 进程表 / 你+裁判 | 副本 profile |

---

# §12 SLO

| 指标 | 现状 | 目标 |
|---|---|---|
| 信标新鲜度 | 无 | 落后 ≤1 次状态变化，启动即校验 |
| 闭环率 | 无统计 | ≥80%，每项有 verifier |
| **审查覆盖** | 无流程 | 100% 产物经沙箱+独立审查，一件一裁，信息包 14 项齐 |
| **官方校对覆盖** | 无 | 100% 涉 dsh 设计项有条款引用与差异声明 |
| **崩溃复发** | 25 类已复现坑 | 同类复发 = 0（G-CR 门全绿） |
| 单会话体积/事件数 | 256MB（峰值 1,178 万事件） | ≤200MB + 事件数入监控 + 超限拒绝 |
| 会话目录 | 1.2GB | ≤500MB |
| inbox | 2,645 文件/108MB | ≤500/≤50MB |
| bus 单文件 | 22.8MB（撕裂 3 次） | 迁移后无整份读写 |
| 黑板数据 | 148MB / snapshot 96MB / DELETE 0 | 有 GC/TTL、大对象外置（-41%） |
| 真积压 / 去重漏判 / 风暴发现 | 103 / >10 分钟必漏 / 人肉 | ≤10 / 0 / 系统自动提前 ≥10 分钟 |
| 机制激活可观测 | 0 | 每次激活可计数可查 |
| 端口稳定性 | 6 个历史端口 | 固定 |

---

# §13 风险登记

R1 治理工具制造同类问题 · R2 阈值无样本 · R3 不可逆操作 · R4 仪器失真 · R5 小机资源 · R6 双轨并存 · R7 时钟漂移 · R8 开关装了没合上 · R9 失忆 · R10 自设计崩溃 · R11 半修记为已修 · **R12 引用丢限定语（系统性，已三例）** · **R13 载体换 SQLite 唯一高危** · **R14 审查信息包不足 ⇒ 审查失效**。

---

# §14 执行序与里程碑

```
Wave S（门）→ Wave C（信标）→ Wave 0（开关合上+可观测）→ Wave 1（P0）
并行：NATS 影子 PoC（只读，必须显式设限额）
Wave 2（含唯一高危载体换）→ Wave 3 → Wave 4 → Wave 5
```
**M0**：审查与校对门可跑；信标四件套在位 ⇒ 新会话 ≤5 分钟恢复计划认知。
**M1**：compaction 生效、单会话体积降 ≥50%；装载超限拒绝而非崩；子进程内存可见；同内容重放 0 重复；熔断可触发；风暴系统自动发现；一卡一次注入。
**M2**：真积压 ≤10；限速无边界缺陷；风暴期关键消息通过率 ≥90%；端口固定。
**M3**：载体迁移完成且 I1–I4 成立；归属可验；黑板有 GC；时序可全序复原；订阅唤醒上线；**25 类崩溃坑零复发**。

---

# §15 未决问题

Q-A 去重淘汰语义（建议分层）· Q-B 端口固定值（你定）· Q-C 是否引入 NATS（先影子 PoC）· Q-D 注入器保留哪个（建议 SSE）· Q-E HMAC 密钥分发（本机 0600）· **Q-F（v3 改题）原「挂载 compaction 批准」已废**——机制二（模板下界 > 被遮内容）**无配置解**（`BASIC_COMPACT_CONFIG_KEYS` 十把键无一把可改模板/判据），故原题不再适用于官方 `compaction-basic`；用户 2026-10-09 以「**立项**」改为自研后端（见 Q-K）· **Q-G 自启动注入批准** · **Q-H 载体换独立窗口安排** · **Q-I `item-validity-review-check` 是否收编为闭环判定器（其 open 口径待裁判裁）** · Q-J 四项历史决策（板鉴权/A 类仓/meituan-multi/「-」仓）· **Q-K 自研 no-summary 压缩后端——用户 2026-10-09 已批「立项」**（走 `agent/pre-step` 守卫 seam，**与官方 backend 并存、不替换 `ctx.compaction`**；N→1 有界非摘要检查点，按 R006 十项交付）· **Q-L R049 接入 C4（自启动注入）——待做**（「运营门」目前靠人执行，未机器化；M0 依赖它）。

---

# §16 附录

**证据索引**：`agent-bus/lib/index.js:{70-78,191,561,740,1111,1125,1140,1296-1303,1375-1405}` · `dsh-plugin-bus-queue-triage/cli.js:{14-16}` · `~/.dsh/profiles/web/package.json`（41 bundles 无 compaction）· `~/.dsh/sessions/--Users-coreyleung--/session-fa1f9150-…/session.jsonl.zstd`（256MB，压缩 50 次）· 黑板审计 PUT 23,722 / DELETE 0 · `rust-blackboard/src/http.rs:237` · `comm-server/{comm_domains.py,agent-mailbox.py}` · `scripts/build-bundle.sh:2,29` · `~/.cld/logs/dsh-web.log`（OOM ×13）· `~/Desktop/归档/2026-08-18/DSH-macmini-防崩溃运维手册.md` · `docs/cld-{boot-and-session-list,tools-instance-split}-fix-20261006.md` · 既有深调研 12,101 行（`research/agent-comm-paths/`）· `docs/item-validity-index.json`（2,642 条）+ `devices/dsh-plugin-item-validity-review-check`。
**复用而非新造**：会话级继承（2 份）· 规则级闭环（R020）· 投递闭环语义 · L1 SQLite 实现 · `item-validity-review-check` 五态；本计划新增**计划级信标 + 审查流水线 + 官方校对门 + 崩溃坑登记**。
