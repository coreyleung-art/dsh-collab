#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""record-g21-inbound-single-point.py —— 归档「收信通道单点依赖」事故与结构修法

【事故】2026-10-03 21:48–22:00
  mac-mini（星桥机器）**Tailscale 掉线**（`offline, last seen 9m, rx 0`），
  而我的 central-inbox **SSE 信源恰好是它的本地桥**（`100.120.203.20:8803`）
  ⇒ **我收信中断**（末次成功注入 21:47:27），日志连续 `SSE 错误: fetch failed`，退避到 30s。
  ★ 同期它**机器是活的**：它自己的心跳 21:59 仍新鲜（走公网直写中枢）⇒ 断的只是 tailnet；
    副证：`nodes/mbp`／`nodes/i9` 心跳停在 ~21:47（它们靠 mac-mini 经 tailnet 转发）。
  ★ 影响：它写的卡**已在往中枢转发**，而**我读不到** ⇒ 存在**静默漏收窗口**。

【结构修法（已验证，非推测）】
  实测两项后才改：
   ① 中枢桥**确实为「写入中枢的卡」推 change 事件**（真写一张 → 捕获 `event: change` + `id: 2023`）
   ② 45s 订阅中捕获到 `nodes/mac-mini/heartbeat` 事件 ⇒ **「mac-mini 转发的键」也会触发事件**
  ⇒ 把 `CENTRAL_INBOX_SSE` 由 mac-mini 本地桥改为**中枢桥**（公网服务器，不依赖某台笔记本的 tailnet）。
  备份 `~/.dsh/.env.bak-sse-*`；改后 `.env` 校验（12 行/无非法行/无 `DSH_NODE_ID=`/仅一行赋值）✅
  **生效需重启**（插件 boot 时读 env）⇒ 已纳入本次重启前审查。
"""
import io
import os

H = os.path.expanduser("~/dsh-collab/hazards")

# ── ① rules.md: R42 ────────────────────────────────────────────────────
p = os.path.join(H, "rules.md")
s = io.open(p, encoding="utf-8").read()
s = s.replace("R1–R41 + R025", "R1–R42 + R025", 1)
s = s.replace("## R27–R41（2026-10-03 建立 · 判据 / 工具 / 交付 / 判定同源）",
              "## R27–R42（2026-10-03 建立 · 判据 / 工具 / 交付 / 判定同源 / 链路可用性）", 1)
row = ("| R42 | **关键链路不得单点依赖「某台终端 + 某种私有网络」** —— 收发通道应指向**公共/服务端**路径，"
       "或实现**回落**。实测：我的收信 SSE 只指 mac-mini 的本地桥，对方 Tailscale 一掉，"
       "**我即静默漏收**（而对方机器与公网都是好的）。⇒ 依赖某台笔记本的 tailnet ＝ **把可用性押在它身上** |\n")
s = s.replace('| R31 | **判据"什么都没测到"必须报失败，不得报成功**',
              row + '| R31 | **判据"什么都没测到"必须报失败，不得报成功**', 1)
inst = '''
> **R42 实例**（2026-10-03 21:48–22:00 · 正在发生的收信中断）：
> mac-mini 的 **Tailscale 掉线**（`offline, last seen 9m ago, tx 4524 rx 0`；ping 100% 丢包；
> 板 8792／桥 8803／SSH 全部超时），而**我的 inbox 信源正是它的本地桥** ⇒ **我收不到卡**。
> ★ **它机器其实活着**：它自己的心跳 21:59 仍新鲜（直写中枢）⇒ 断的只是 tailnet。
> ★ 代价：它的卡**已在往中枢转发**，而我读不到 ⇒ **静默漏收**（最坏的一类：看起来一切正常）。
> **修法（先实测再改）**：① 真写一张卡 → 中枢桥确实推 `event: change` + `id:` ✅
> ② 45s 订阅捕获 `nodes/mac-mini/heartbeat` → **转发内容也触发事件** ✅
> ⇒ 信源改为**中枢桥**（公网服务器）⇒ 不再把可用性押在一台笔记本的 tailnet 上。
> ⇒ 与 R38/R39 同一立场：**能在结构上消除的单点，不要留给人肉发现。**
'''
s = s.replace("\n## R025（本目录的规则来源", inst + "\n## R025（本目录的规则来源", 1)
io.open(p, "w", encoding="utf-8").write(s)
print("✅ rules.md: R42 入册，条目 %d" % len([l for l in s.splitlines() if l.startswith("| R")]))

# ── ② patterns 类 F：加实例 ───────────────────────────────────────────
p2 = os.path.join(H, "patterns", "00-总表.md")
u = io.open(p2, encoding="utf-8").read()
anchor = "| **「我把文件放到本机某目录」= 已交付** ★ |"
add = ("| **收信只听 `100.120.203.20:8803`（对端笔记本的本地桥）** ★★ | "
       "**对方 Tailscale 一掉，我即静默漏收**（而对方机器与公网都正常）。实测 21:48–22:00 收信中断、"
       "退避到 30s；同期它的卡已在往中枢转发 ⇒ **我读不到**。⇒ 已改指中枢桥（公网），并实测其事件覆盖 ✅ |\n")
if "收信只听" not in u and anchor in u:
    u = u.replace(anchor, add + anchor, 1)
    io.open(p2, "w", encoding="utf-8").write(u)
    print("✅ patterns: 类 F 加「收信单点」实例")
else:
    print("⚠️ patterns 跳过")

# ── ③ INDEX: 标题 + G21 ────────────────────────────────────────────────
p3 = os.path.join(H, "INDEX.md")
t = io.open(p3, encoding="utf-8").read()
t = t.replace("R1–R41 + R025", "R1–R42 + R025", 1)
a = "| **G8b** | **SSE 断连频率**"
add2 = ("| **G21** | ★★ **收信通道单点依赖（2026-10-03 21:48–22:00 实际中断）**：我的 central-inbox SSE "
        "只指 **mac-mini 的本地桥**（`100.120.203.20:8803`）⇒ 对方 **Tailscale 掉线**即**我静默漏收**"
        "（末次收信 21:47；同期**它机器活着**、卡已在往中枢转发，只是我读不到）。"
        "**已修（先实测后改）**：真写卡验证中枢桥推 `change`+`id` ✅、订阅捕获 mac-mini 转发键的事件 ✅ "
        "⇒ 信源改指**中枢桥**（公网）。`.env` 已备份、格式校验通过；**生效需重启**，已纳入重启前审查。"
        "→ 立 **R42** | ✅ 已改（待重启生效） |\n")
assert a in t
io.open(p3, "w", encoding="utf-8").write(t.replace(a, add2 + a, 1))
print("✅ INDEX: G21 入册，标题→R1–R42")

# ── ④ 重启前审查报告：追加本节 ────────────────────────────────────────
rp = os.path.expanduser("~/dsh-collab/docs/pre-restart-review-20261003-1900.md")
r = io.open(rp, encoding="utf-8").read()
add3 = """

---

## 10. ★★ 22:00 追加：一处**重启前配置变更**（收信通道去单点）＋ 一起正在发生的对端掉线

### 10.1 事件（21:48–22:00，实测）
- **mac-mini（星桥机器）Tailscale 掉线**：`offline, last seen 9m ago, tx 4524 rx 0`；
  ping **100% 丢包**；其板 `8792`／桥 `8803`／SSH **全部超时**
- **我的 inbox 信源正是它的本地桥** ⇒ **收信中断**：`SSE 错误: fetch failed` 连续重试，退避到 30s；
  **末次成功注入 21:47:27**
- ★ **它机器其实活着**：它自己的心跳 21:59 仍新鲜（直写中枢）⇒ 断的只是 **tailnet**；
  副证：`nodes/mbp`／`nodes/i9` 心跳停在 ~21:47（它们靠 mac-mini 经 tailnet 转发）
- ⇒ **静默漏收**：它的卡已在往中枢转发，而**我读不到**（最坏的一类：两边都"看起来正常"）

### 10.2 处置（**先实测两条，再改**）
1. 真写一张卡到中枢 → 中枢桥**确实推** `event: change` + `id: 2023` ✅
2. 45s 订阅中枢桥 → 捕获到 `nodes/mac-mini/heartbeat` 事件 ⇒ **「mac-mini 转发的键」也触发事件** ✅
⇒ 结论：换到中枢桥**不会丢**我关心的两类（我写的 / 它转发的）。
**已改** `~/.dsh/.env`：`CENTRAL_INBOX_SSE` 由 `http://100.120.203.20:8803/events`（mac-mini 本地桥）
改为 **`http://xingqiao.meetfunbp.com:8803/events`（中枢，公网）**。
- 备份：`~/.dsh/.env.bak-sse-20261003-220045`
- 改后校验：12 行、**无非法行**、**无 `DSH_NODE_ID=` 赋值**、`CENTRAL_INBOX_SSE` 仅 1 行 ✅
- **回退**：把该行换回旧值并重启即可

### 10.3 对本次重启的影响（**加入验证清单**）
- 该项**需重启才生效**（插件 boot 时读 env）⇒ 重启后请确认：
  **inbox 连的是中枢桥**、且能收到卡（`~/.dsh/central-inbox.log` 应显示
  `SSE 已连接 http://xingqiao.meetfunbp.com:8803/events`）
- 同时提醒：mac-mini 掉线期间，**我发给它的卡只落到中枢**（本机板写入超时），
  历史证据表明中枢会再同步给它 ⇒ 但**它何时收回不可控**，故本次重启后**先别再依赖"双板写"这一条做判据**。

### 10.4 归属与纪律
- **这是设计缺口，不是操作失误**：把可用性押在"某台笔记本 + 它的 tailnet"上。
- 已立 **R42**（关键链路不得单点依赖某台终端/私有网络）· **G21** · 类别 F 实例。
- **未做**：未自行重启（用户动作）；未改 mac-mini 侧任何配置（它不可达）。
"""
if "## 10. ★★ 22:00 追加" not in r:
    io.open(rp, "w", encoding="utf-8").write(r + add3)
    print("✅ 重启前审查报告已追加第 10 节")
else:
    print("⚠️ 报告已含第 10 节")
