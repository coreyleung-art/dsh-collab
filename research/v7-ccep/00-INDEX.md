# 00 · INDEX · v7 CCEP 五原则调研（R-M3）

> **调研代理**：**R-M3**（v7 计划 · **M3 · 跨会话协作协议族**）
> **现测时刻**：**2026-10-12T20:04:34+08:00（+08:00）**
> **工作目录**：`/Users/coreyleung/dsh-collab`
> ★★ **本目录 7 篇均为本轮现测**；★ **未照抄 v6.1 任何读数**。
> ★ **未修改 `docs/` 下任何既有文件**（CCEP 原文与 v6.1 锚点 sha256 见下）。

**输入件指纹（供复跑核对）**

```
0f6ba8bc40f179b95edd37f1af779bb915beea7d16b285c3dc90307871af7944  docs/CCEP-continuity-protocol-v1.md          (4508 B)
bf5a4e6b76fdedeb3c7c48cc5d3830ea29c441ca0051091ec4f6adb7948e49e3  docs/distributed-agent-network-governance-plan-v6.1-20261011.md
```

★ 复跑：`shasum -a 256 docs/CCEP-continuity-protocol-v1.md docs/distributed-agent-network-governance-plan-v6.1-20261011.md`

---

## 一、篇目与每篇一句话结论

| # | 文件 | ★ 一句话结论 |
|---|---|---|
| **01** | `01-业界等价物-CCEP五原则.md` | ★ **五条原则在业界【无一条完全等价】**——因为 CCEP 的取证对象是「**通道本身**」，而业界对应物全部作用在**应用/流量/制品/配置**层；★ 其中**原则 2「自举」语义无直接对应物**，★ **原则 5 在单机进程级有 nginx 这一近乎完全等价的先例**。 |
| **02** | `02-本机遵守现测-逐条判据.md` | ★ **五条里只有原则 5 成立**；★ 原则 1/3/4 **部分成立（工具在、强制不在）**；★ **原则 2 不成立**；★ **禁令「依赖人类手工重连」本机确实在依赖**。 |
| **03** | `03-专项-单点与自举缺口.md` | ★★ **8792 与 8803 同进程 PID 1221**（已连跑 4 天 15 小时），一次 kill 带走 **30 条 SSE / 4 类客户端** ⇒ ★ **「全部断掉」物理可达**；★★ **`bb-upgrade.py` 落链在 `[7/7]` 且走新板自己 ⇒ 不是旧通道投递**。 |
| **04** | `04-专项-值班投递协议现状.md` | ★★ **§18.2 管道全链路静默**：★ 生产者停于 `2026-10-03`、消费者停于 `2026-09-02`（已 ~40.7 天），★ **111 条 pending 全部指向同一个已 bricked 会话**，★ **且无任何告警器在看这个数**。 |
| **05** | `05-专项-沙箱验证快照回滚四件套.md` | ★ **四件套全在位**（`verify-deploy` / `sandbox-script` / `guard/backups` 376 项 / 具名回滚点），★ **但只有 `channel_gate` 一处是真门，且它的四条判据真的红过（`exit=1`）**。 |
| **06** | `06-判据有效性与最易违反项.md` | ★★ **最容易被违反的是【原则 2】——因为违反它【不需要做任何事】、【不报错】、且判据不可红**；★ 判据有效性呈**哑铃形**（门那端硬、通道那端软）。 |
| **07** | `07-CCEP该不该升版-裁决依据.md` | ★ **只给裁决依据（A/B/C 三条路线的代价 + J1–J6 判据读数），★ 不给结论**；★ 指出一条**与路线无关**的发现：★ **本机的问题不是缺工具，是缺门**。 |

---

## 二、★★ 三条最重要的发现

### 发现 1 · 原则 2「通道自举」是**唯一不可红的硬缺口**

★★ 现测逐字（`scripts/bb-upgrade.py:199-210`）：★ 黑板升级的**第 7/7 步才是落链登记**，★ 且 PUT 到的是 **`BB`（被升级的黑板自己）**。

```python
    # 7. 落链登记
    print("[7/7] 落链登记...")
    body = json.dumps({
        ...
        "verify": "冒烟全过 + 生产验证",     ← ★ 冻结字符串，无输出/时刻/退出码
        "rollback": "plist 指回 blackboard-server-%s.py" % args.vfrom,
    }).encode()
    req = urllib.request.Request(BB + "/data/iterations/upgrade-%s" % args.vto, ...)
```

★★ **⇒ 三件事同时成立**：★ ①**先升级后登记**（不是先投递再切换）②**登记走新板自己**（不是旧通道）③**`verify` 字段永远不可能变成「未通过」**。
★ **这解释了为什么它排「最易违反」第一**（`06` §2.2）。

### 发现 2 · §18.2 值班投递协议**全链路已死，且无人告警**

```
$ python3 scripts/event-bus.py --status
events: 122 {'task.completed': 4, 'agent.online': 59, 'agent.offline': 59}
instructions: total=122 pending=111
[exit=0]
```

★ **现测增量**（本件新取，v6.1 未给）：★ **最后一次真消费 `2026-09-02T00:44:28`（已 ~40.7 天）**；★ **事件生产者停于 `2026-10-03`**（`events/` 最新文件，9.2 天无新）。
★★ **111 / 111 条 pending 收件人【同一个】已 bricked 会话** `session-fa1f9150-c949-401f-ba8c-d265f6221676`。
★★ **且告警器 `logs/bus-delivery-alert.log` 全程 `verdict=OK alerts=0`**，★ **但它盯的是【另一条队列】的 `{"q": 8, "e": 2377}`** ⇒ ★ **这 111 条【没有读者】。**

### 发现 3 · 「依赖人类手工重连」**不是风险，是现状**

```
$ ls -la ~/Library/LaunchAgents/com.dsh.cld-auto-relaunch.plist
ls: No such file or directory
[exit=1]

$ ls -la ~/Library/LaunchAgents/com.dsh.cld-auto-relaunch*
-rw-------  1 coreyleung  staff  912 Sep  4 13:47 .../com.dsh.cld-auto-relaunch.plist.bak-pre-heapfix
[exit=0]
```

★ 备份件内容为 `KeepAlive=false` + `RunAtLoad=false`；★ `launchctl list` 中**无** `auto-relaunch`。
★ 叠加 `execution-audit-anchor-v5-20261010.md:171`：★ C4 自启动注入 `open`。
★ 叠加历史事故（`docs/pitfalls/2026-08-29-upgrade-no-standby.md` 逐字）：★ **「i9 升级阻塞 7 分钟无人处理（直到用户问 i9 插件情况才触发排查）」**。
★★ **⇒ 恢复面被【主动交给了人】。** ★ **须与「本运行环境 SIGTERM 不自动拉起」区分**（见 `02` §2.4 两层表）。

---

## 三、★★ ★ 清点件 M3 计数的更正（★ 本件的独立发现）

> ★★ **题目提示：「若只有 1 条说明抽取漏了，你要自己去 §18 补全」** —— ★ **经查，情况比提示更复杂：不是漏抽，是【两个数字用了两把不同的尺】。**

### 3.1 两个数字互相矛盾

| 件 | ★ §18 口径 | 值 |
|---|---|---|
| `docs/v7-outline-revised-20261012.md:37` | §18 跨会话协作协议族 \| **❌ 5** \| open 0 \| **待 7** \| 合计 **12** | **12** |
| `docs/v7-unfinished-inventory-20261012.md:18,56` | **M3 跨会话协作协议族（CCEP）** | ★★ **1 条** |

### 3.2 ★ 根因：**「5 个 ❌」被当成了「5 条」**

★ 现测（`awk 'NR>=2675 && NR<=2872' <v6.1> | grep -c '❌'`）：

```
❌ 行数（文本行）: 1
❌ 字符数:        5   ← ★ 单个文本行上有 5 个 ❌ 字形
[exit=0]
```

★★ **⇒ 那 5 个 ❌ 全部落在【同一行】（`v6.1:2699`），是【一条禁止事项清单里的五个「❌」字形】，★ 不是五条独立待办。**
★ 故：★ **清点件「1 条」在【行级抽取口径】下是对的**（★ 其 `§四` 已自陈「本件是行级抽取」）；★ **大纲「5」是把字形数当条数** ⇒ ★ **两个数字【都对不上事实】，只是各错一边。**

### 3.3 ★ 按 §18 全文逐条计（★ 本件口径，**可核**）

| 来源 | ★ 条目 | 数 |
|---|---|---|
| §18.1 | 五原则 + 五步流程 + 五禁止 = **规范文本**（★ **非待办**，★ 除条件外无措辞表明未完成） | — |
| §18.2 | ★ 实测缺陷段 + 「**属主：HR / 协调者**」 | **1** |
| §18.3 | ★ 「**待裁的两条路**」(a)/(b) | **1** |
| §18.5 | ★ 无「待/open/❌」（★ 全是定义与更正注） | **0** |
| **§18.6.3** | ★★ **「本节待办」表 5 行** | **5** |
| ★ §18.1 的禁止事项行 | ★ **1 行 / 5 个 ❌ 字形** | **1** |
| ★ **合计** | | ★★ **8 条** |

★★ **⇒ 本件判定**：★ **§18 的真实未完成条目约为 8 条，★ 既不是大纲的 12，也不是清点件的 1。**
★★ **两者都须更正**：
- ★ **大纲**应把「❌ **5**」改为「❌ **1 行（含 5 个 ❌ 字形）**」；
- ★ **清点件**应把 M3 的 **1 条**扩为 **8 条**（★ 补入 §18.2 属主项、§18.3 待裁项、§18.6.3 的 5 条待办）。

★★ **⇒ 顺带印证清点件自身的限制声明**（其 `§四` 第 3 条逐字）：
> ★★★ **★ 抽到的是【文本登记】，不是【事实】**

★ **本件与之一致**：★ 那 5 个 ❌ 是**字形**，★ 而非**事实条目**。

---

## 四、★ 判据有效性：红过的 / 没红过的

★ **本项目纪律：「一个断言若从未红过，它就不是判据」。** ★ 逐条实测：

| 判据 | ★ 红过？ | 证据（退出码） |
|---|---|---|
| `channel_gate` 未知通道拒绝 | ✅ | `门拒绝: channel 不在冻结枚举` **`[exit=1]`** |
| `channel_gate` 缺必填字段拒绝 | ✅ | `门拒绝: 变更单缺必填字段 evidence` **`[exit=1]`** |
| `channel_gate` 回滚点存在性 | ✅ | `门拒绝: 回滚点路径不存在` **`[exit=1]`** |
| `channel_gate` 未知旗标 | ✅ | `用法错误: 未知旗标 --action` **`[exit=2]`** |
| `bb-upgrade.py` 的 `"verify"` 字段 | ❌ **不可能红** | ★ 冻结字符串 ⇒ **不是判据** |
| `event-bus` 的 `sent` 标志 | ❌ **无读者** | ★ 111 条 pending 无告警器 |
| `verify-deploy.py` 不一致即非零 | ⚠️ **本件未测** | ★ 未造不一致样本 |
| `sandbox-script.py --expect-exit` | ⚠️ **本件未测** | ★ 未跑实作 |
| `channel_gate status` 的 `24h变更 0/2` | ⚠️ **不可判** | ★ **空 ≠ 无** ⇒ 判「不可判」，★ **不读成「通道健康」** |

---

## 五、★★ 未查到的部分（★ 如实列）

### 5.1 本件**未做**的验证（⇒ 相关结论**不成立**，只标「未测」）

| # | 未做 | ★ 后果 |
|---|---|---|
| 1 | ★ **未做破坏性演练**（未 kill PID 1221） | ★ **「一次 kill 真的带走 30 条 SSE」是【推演】，非【实测】** |
| 2 | ★ **未做回滚演练** | ★★ **CCEP 原则 5 的「秒级」措辞【不可判】** |
| 3 | ★ **未跑 `verify-deploy.py` 的失败路径** | ★ 其**退出码三态**未验证（仅读 `--help`） |
| 4 | ★ **未跑 `sandbox-script.py` 实作** | ★ `--expect-exit` 的判别力未验证 |
| 5 | ★ **未跑 `event-bus.py --consume`** | ★ **无法区分「生产者死」与「消费者死」**（★ 且 `logs/event-bus.log` **不存在**） |
| 6 | ★ **未测 `drift-scan` 输出侧是否只打成功侧** | ★ `06` #8 只确认其**负控注入点存在** |
| 7 | ★ **未核 `guard/backups` 的保留/修剪策略** | ★ **不得判「快照有界」** |
| 8 | ★ **未测 `drift` 告警双板到达率** | ★ **不得判 M4① 已达成**（★ 只报 `total= 352 / 58` 两个读数） |

### 5.2 本件**搜过但没找到**的（⇒ ★ **未搜到 ≠ 不存在**）

| # | 搜索面 | ★ 结果 |
|---|---|---|
| 1 | ★ 「经旧通道投递」的**可执行实现**（`scripts/` / `tools/`） | ★ **未命中任何脚本**，★ 只命中**协议文本自身** |
| 2 | ★ 业界以「**必须走旧通道**」为硬约束的成文标准（`01` 篇 7 轮检索） | ★ **未搜到** |
| 3 | ★ 业界把「**任何时刻至少一条通道**」写成 **invariant** 的规范 | ★ **未搜到** |
| 4 | ★ staging 环境的**一手权威定义** | ★ **未搜到**（★ 只有博文，★ 已标来源等级） |
| 5 | ★ 面向「**多异构通道**」的快照—回滚规范 | ★ **未搜到**（★ 只有应用/镜像/配置/DB schema 四层） |
| 6 | ★ `<https://source.android.com/docs/core/ota>` 与 `.../virtual_ab` | ★ **Timeout 15s，未能读取** |

### 5.3 本件**覆盖不到**的面（★ 明确的范围边界）

| # | 范围 | ★ 说明 |
|---|---|---|
| 1 | ★ **原则 2 的「未找到实现」只覆盖 `scripts/` 与 `tools/`** | ★ **未穷举**其它目录（如插件目录、`devices/`） |
| 2 | ★ **MBP / i9 两端未现测** | ★ 本件**只测本机（mac-mini）** ⇒ ★ **「就绪清单」三端一致性【未核】** |
| 3 | ★ **中央实例（106.53.214.108）只取了一个读数** | ★ `drift-alert total= 58`，★ **未做更多核验** |
| 4 | ★ **未读** `docs/pitfalls/2026-08-29-nodebridge-sandbox-missed-mode.md` 正文 | ★ 只确认其**存在**（`05` §2.2） |
| 5 | ★ **§18.5 失败可见性体系** | ★ ★ **本件未做实现面核查**（★ 只读 v6.1 内联文本） |

---

## 六、★ 本目录的整体限制（★ 三条纪律的自查）

| 纪律 | ★ 本目录的遵守情况 |
|---|---|
| ★ **「空 ≠ 无」：分母为 0 必须报「不可判」** | ✅ ★ 已应用于 `channel_gate status` 的 `24h变更 0/2`（判**不可判**，★ **未读成 OK**）与 `drift` 到达率 |
| ★ **「一个断言若从未红过，它就不是判据」** | ✅ ★ 已建**判据有效性矩阵**（§四 + `06` §一），★ 逐条标「红过 / 没红过 / 未测」 |
| ★ **「凡读状态必问『这是哪个时刻的』」** | ✅ ★ 全篇带 **`2026-10-12T20:04:34+08:00`** 时刻锚；★ 且**已证明必要性**：★ `drift-alert` 现测 **352/58**，★ 而 v6.1 记 **304/19** ⇒ ★ **照抄旧读数会得出错误现状** |
| ★ **「不得升格」** | ✅ ★ 全文凡本线判定均标「**本线判定**」；★ 凡推断均标「**推断/未验证**」；★ **引用用户或他方一律逐字并给行号** |
| ★ **不得修改 `docs/`** | ✅ ★ **本目录 7 篇 + 本 INDEX 全部写在 `research/v7-ccep/`**；★ `docs/` **零改动** |

---

## 七、★ 复跑总表（★ 一屏可跑完）

```bash
cd ~/dsh-collab

# ── 时刻锚 + 输入件指纹
date -Iseconds
shasum -a 256 docs/CCEP-continuity-protocol-v1.md \
  docs/distributed-agent-network-governance-plan-v6.1-20261011.md

# ── 原则 1：单点
lsof -nP -iTCP:8792 -sTCP:LISTEN ; lsof -nP -iTCP:8803 -sTCP:LISTEN
lsof -nP -iTCP:8803 | grep -c ESTABLISHED
ps -o pid,ppid,etime,command -p 1221

# ── 原则 1：备用通道是否活
tail -1 ~/.dsh/inbox/bb/coordinator.jsonl
curl -s -m 8 http://127.0.0.1:8792/data/central/wake-trigger

# ── 原则 2：投递时序
sed -n '199,210p' scripts/bb-upgrade.py
grep -n '"verify"' scripts/bb-upgrade.py

# ── 禁令：人工重连
ls -la ~/Library/LaunchAgents/com.dsh.cld-auto-relaunch*
launchctl list | grep -i "auto-relaunch"

# ── §18.2 值班投递
python3 scripts/event-bus.py --status
ls -la ~/dsh-collab/token-monitor/event-bus/events/
cat logs/bus-delivery-alert.log

# ── 判据有效性（负控，★ 应全部非 0 退出）
export PATH="/opt/homebrew/bin:$PATH"
node ~/dsh-plugin-channel-gate/cli.js status
node ~/dsh-plugin-channel-gate/cli.js register --channel no-such-channel \
  --evidence x --rollback /tmp/x --blast none            # 期望 exit=1
node ~/dsh-plugin-channel-gate/cli.js register --channel board-local  # 期望 exit=1
node ~/dsh-plugin-channel-gate/cli.js register --channel board-local \
  --evidence x --rollback /tmp/nope-$$ --blast none      # 期望 exit=1

# ── (2)(4) 目治漂移读数（★ 会变，引用须带时刻）
curl -s -m 8  "http://127.0.0.1:8792/data/ops/drift-alert/" | python3 -c "import sys,json;print('local=',json.load(sys.stdin).get('total'))"
curl -s -m 10 "http://106.53.214.108:8792/data/ops/drift-alert/" | python3 -c "import sys,json;print('central=',json.load(sys.stdin).get('total'))"
```

---

★ **本目录不主张任何 CCEP 原则已被闭合，也不主张 CCEP 应升版或不应升版。**
★ **本目录不替用户裁决**（★ 待裁事项见 `07` §五）。
★ 「最易违反」排序、「等价程度」评级、「A/B/C 路线」★ **均为本线判定，非既有文档结论**。

---

*R-M3 · v7 CCEP 调研 · 00/INDEX · 7 篇 + 本件 · 2026-10-12T20:04:34+08:00*
