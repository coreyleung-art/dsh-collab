# 探明索引（指针式）· 2026-10-12 夜

> **出件**：星桥第二任 `session-e317d6ab`（mac-mini）
> **时效**：**2026-10-12 02:4x（+08:00）** 快照
> **效力档位 L1（已记录）** · ★ **不宣布任何事项已闭合**

---

## ★★ 本索引的性质：**它是指针，不是内容**

★ **每一条只给三样东西**：★ **一句话结论（三态）** · ★ **内容在哪** · ★ **怎么复跑**。
★★ **内容在它指向的文件/卡里**，本索引**不复述内容**。
★★ 立此件的原因：★★★ **今晚两份考古报告曾在「只存在于会话上下文、没有第二副本」的状态下停留过一段时间**（★ 一次子代理因 CLD 自重启未完成落盘）⇒ **探明结果必须有落点与指针。**

★ **三态约定**：✅ 成立 · ❌ 不成立 · ❓ 不可判（★ 「读不到」≠「不存在」；★ 「空集」≠「通过」）

---

## 一、今晚（2026-10-12）新探明

| # | 事项 | 一句话结论 | 内容在哪 | 复跑 |
|---|---|---|---|---|
| 1 | **两份考古报告已落盘** | ✅ 由会话上下文转入文件（★ 此前**无第二副本**） | `docs/archaeology-xingqiao-vs-tailnet-20261012.md`（235 行）· `docs/archaeology-store-node-rollout-20261012.md`（359 行） | `wc -l docs/archaeology-*.md` |
| 2 | **xingqiao × tailnet 的原始设计** | ✅ 分层口径下互补；❌ 「自始至今稳定互补」不成立（★ **四次定位变更，跨 26 天**） | 同上第 1 份 | 该件 §八 复跑块 |
| 3 | **两圈之分** | ✅ **早在 2026-08-22 就被写成成文决策**（★ 原始表述是**三分**：Tailscale=自有设备／公网=门店／付费订阅） | 同上第 2 份 §六 | `sed -n '1,25p' research/cost-governance/access-tiering-role-model-v0.1.md` |
| 4 | **圈二（门店投放）现状** | ✅ 讨论充分、PoC 实跑通过；❌ **真实门店零部署**（★ 活体 E2 注册表无 `store-*`） | 同上第 2 份 §三/§八 | `curl -s http://127.0.0.1:8792/data/discovery/agents/` |
| 5 | **中枢黑板位置** | ✅ **在 xingqiao 服务器（腾讯云 `106.53.214.108`）**，非本机 | 台账 **D-073** | `ssh -i ~/.ssh/id_ed25519 ubuntu@106.53.214.108 'ps -eo args | grep rust-blackboard'` |
| 6 | **中枢 `8792/8803` 对公网开放** | ✅ 成立（★ **独立视角**：中枢自身 tcpdump 收到公网 SYN） | 台账 **D-073** | `ssh … 'sudo timeout 60 tcpdump -n -i any "tcp port 8792 and tcp[tcpflags] & tcp-syn != 0"'` |
| 7 | **中枢令牌是否泄露** | ❌ **未泄露** —— 3 个在役值与仓内 6 个泄露值**指纹零重合**；泄露值中枢 **24/24 = 401** | 台账 **D-069** | 该件判据栏（头矩阵 + 正控） |
| 8 | **中枢令牌轮换** | ✅ **零停机两阶段已完成**（4 值并存；本机已迁移；**撤旧未做**） | 台账 **D-069 / D-072** | `ssh … 'sudo cat /etc/comm-server-blackboard-tokens.env'`（★ 掩码后再看） |
| 9 | **原设计要求白名单（现为 Anywhere）** | ✅ **是设计漂移，不是设计** | 台账 **D-074** | `sed -n '13p;53p;57p;131p' comm-server/server-governance-v1.md` |
| 10 | **中枢加入 tailnet 曾计划、被喊停、卡在 auth key** | ✅ 成立（★ **卡点一个月未变**） | 台账 **D-074** | `sed -n '61,65p' docs/systemgraph-on-comms-server-plan-20260911.md` |
| 11 | **`channel-denominator` 真分母** | ❓ **不可判** —— 论域未获裁可（★ L3=44 是本线口径，★ **非终局**） | 台账 **D-062 / D-064** · `scripts/channel-denominator.py` **2.0.0** | `python3 scripts/channel-denominator.py --live` |
| 12 | **M4① 双板到达率** | ❌ **14.04%**（48/342）★ 与 D-057 的 14.08% 几乎相同 | 台账 **D-078** | `for u in http://127.0.0.1:8792 http://106.53.214.108:8792; do curl -s "$u/data/ops/drift-alert/" | python3 -c "import sys,json;print(json.load(sys.stdin)['total'])"; done` |
| 13 | **M4③b `expired` 告警** | ❌ **不成立** —— `expired` 唯一消费者是**审计器**（把 expired 排除出统计），**无告警** | 台账 **D-078** | `grep -rn 'expired' scripts/*.py` |
| 14 | **`channel_gate` 熔断有效** | ✅ 成立（★ 24h 内第 3 次变更被**冻结 24h**） | 台账 **D-074** · 变更单 `cg-mv43j0bj-1-j8qb` | `channel_gate register …`（★ 会真冻结，勿试） |
| 15 | **仓库「-」删除是否安全** | ✅ **安全** —— 该仓是**空壳**（0 对象/0 ref/0 issue）⇒ ★ **没有东西需要副本** | 台账 **D-080** · `docs/verify/repo-dash-empty-evidence-20261008.md`（2157 行） | 该证据件 §二 九条判据 |
| 16 | **`f189650` 造成的次生故障** | ✅ 成立 —— ★ **本线的 `git checkout -- scripts/` 打断了明鉴的常驻进程** | 台账 **D-075** | 卡 `notes/mac-mini/repair-report-20261011175340-SystemGraph-health-cwd` |
| 17 | **auto-snapshot 改变了 `git diff` 语义** | ✅ 成立（★ 爆炸半径 **2 个脚本**，`self-report-gate.py` 走显式 ref **不受影响**） | 台账 **D-075** | `grep -rIl 'git diff' scripts/*.py tools/*.py` |
| 18 | **定时快照已上线** | ✅ 成立（`com.dsh.cron.git-snapshot` · 1800s · ★ **恒不 push**） | 台账 **D-070** | `launchctl list | grep git-snapshot` |

---

## 二、今晚新交付的工具（★ 均有第二副本）

| 件 | 版本 | 一句话 | 复跑 |
|---|---|---|---|
| `scripts/channel-denominator.py` | **2.0.0** | 面 4 独立活体枚举 + 分层分母（★ **不读矩阵**） | `--selftest`（12/12）· `--lean4-check`（6/6）· `--live` · `--domain` |
| `scripts/artifact-commit.sh` | **2.0.1** | 唯一副本止损 + **覆盖率断言** + **公开性门** + `safe_rm` + `--snapshot` | `--selftest`（10/10）· `--lean4-check`（7/7）· `--coverage` · `--publicity-gate HEAD` |
| `scripts/irreversible-gate.py` | **1.0.0** | ★ **不可逆操作前的门**（只读·**无删除能力**） | `--paths <f>` · `--selftest` · `--lean4-check` |
| `scripts/mutation-gate.py` | **1.1.0** | 变异单三合取（基线绿 ∧ 变异点唯一 ∧ 变异后红） | `--run`（3/3 PASS） |
| `scripts/drift-scan-cron.py` | **1.2.0** | M4①c 认证头 + ①d 单键心跳 + `--status` 三态 | `--status` |
| `com.dsh.cron.git-snapshot` | — | 30 min 自动快照（★ 只 commit **不 push**） | `cat /tmp/git-snapshot.log` |

---

## 三、今晚的纪律增量（★ 由事故与复核换来）

| # | 纪律 | 来历 | 落在哪 |
|---|---|---|---|
| 1 | ★ **落盘的实质是「第二副本」**，不是「写盘」 | 164 个「已写盘但未提交」的文件永久丢失 | 台账 **D-065** |
| 2 | ★ **不可逆操作前的门**：问「有没有第二副本」（★ 三种投影：删除/compact/覆盖写） | 同上 | `scripts/irreversible-gate.py` |
| 3 | ★★ **但先问「有没有东西【需要】副本」** | 空壳仓的删除 | 台账 **D-080** |
| 4 | ★ **「即将出本机的东西能不能公开」**（公开性门） | `origin` 是公开仓 + 无条件 push | `artifact-commit.sh` |
| 5 | ★ **覆盖率断言**：❓❓ = 0（★ 无第三态） | 「git 快照」在白名单下是**恒真空动作** | 同上 |
| 6 | ★★ **判据的面必须排除判据自身**（自指污染） | 连撞七次 | 各处 lean4 的 `_strip` + 论域收窄 |
| 7 | ★★ **报「复现不一致」前，第一嫌疑是自己的请求** | ★ 本轮用 `/health` 误得 404 | 台账 **D-079** |
| 8 | ★★ **宣称失效时，追到所有被污染的下游** | 把未复核结论转给了明鉴 | 台账 **D-077** |
| 9 | ★ **能当场更正自己首猜的人比首猜对的人可靠** | 明鉴 ×2 · 本线 ×4 | 台账 **D-079** |
| 10 | ★ **写进注释的教训会腐烂，写进控的才会活** | `:783` 注释记着错，控却不守它 | 台账 **D-077** |

---

## 四、本索引不覆盖的（★ 如实声明）

★ 本索引是**今晚**的快照，★ **不含**：★ 十月的治理主线（`docs/distributed-agent-network-governance-plan-v6.1…`）★ 的完整条目 · ★ `comm-server/` 与 `research/cost-governance/` 两个**早期地层的全部内容**（★ 只收了今晚用到的部分）· ★ 明鉴 v3 的交接件（★ 本线未复核，**不做背书也不做否定**）。

★★ **本索引指向的每一个路径，落盘时已逐个 `ls` 核验存在**（★ 指不过去的不写进索引）。

---

*本件是【指针】，不是内容。★ 不宣布任何事项已闭合。*
