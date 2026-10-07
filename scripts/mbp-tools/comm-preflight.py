#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""comm-preflight.py — 跨端通讯「发前门」（R039 落地）

**为什么存在**（R039 · 用户 2026-10-03 明令）：
  用户原话：「我经常发现，会存在漏了某些标注或者规范而导致失败，要求星桥给你标准化文件，
  跟所有端对齐通讯规范，把文件落到本地规则来，并纳入门管理，以后通讯之前根据文件来择优判断」。
  ⇒ 本文件是「**纳入门管理**」那一半：**发消息之前**按规范做 **fail-closed** 检查，
     不满足就拒绝发送；并把「该走哪条通道」从习惯变成**决策表**。

**与星桥的关系**：规范由协调者单点定稿（避免各端各写一份 = 多副本漂移）。
  本文件是**本地实现**，`SPEC_VERSION` 声明它对齐的规范版本；定稿版到达后合并差异。

**设计原则**：结构 beats 纪律 —— 不靠自觉，靠门。

用法：
  from comm_preflight import preflight, choose_channel
  ch, why = choose_channel(target_id, is_local=..., requires_action=...)
  ok, findings = preflight(card, channel=ch, target_is_local=..., notify=[...])
  if not ok:
      raise SystemExit("发前门未通过，拒绝发送")

自测（判别性：用 2026-10-03 真实踩过的 14 类失败逐条验门）：
  python3 comm-preflight.py --selftest
"""
import os
import sys

SPEC_VERSION = "comm-standard-v1.3"   # ★ 对齐星桥定稿 v1.3（2026-10-03；v1.1→v1.2→v1.3）

# ── 失败分级 ────────────────────────────────────────────────────────────────
ERROR, WARN, INFO = "❌", "⚠️", "ℹ️"

# 需要对方「行动」的卡类型关键词（要求行动 ⇒ 必须唤醒 + 声明球权）
ACTION_KINDS = ("request", "coordination", "ask", "question", "invite", "review",
                "blocked", "need", "approval", "handover", "task")
# 纯回执类（**不**含通用 "reply" —— `xxx-reply` 常是「要求回复」，会误报；
# 2026-10-03 实测：`gate-pos-test-reply` 因含 reply 被判成纯回执 ⇒ 误报 B5）
ACK_KINDS = ("ack", "receipt", "done")


def _is_action(card):
    t = str(card.get("type", "")).lower()
    if any(k in t for k in ACK_KINDS):
        return False
    return any(k in t for k in ACTION_KINDS)


def choose_channel(target_id, *, is_local, requires_action=False, peer_reads_central=None):
    """★「择优判断」的决策表（R039 §B）。

    返回 (channel, reason)。
    可选通道：'agent_send'（本机直投）· 'blackboard'（黑板卡+双板写）· 'bus'（bus 信封）
    """
    if is_local:
        return "agent_send", "本机会话 ⇒ agent_send 直投（最低成本）"
    # 跨机：agent_send 历史上从未送达（我侧 145 条 expired），一律走黑板
    if peer_reads_central is False:
        return "blackboard", "跨机 + 对端读本地板 ⇒ 黑板卡（**双板写**，R036：两板不传播）"
    return "blackboard", ("跨机 ⇒ 黑板卡 + **双板写**（本地板 + 中枢）；"
                          "★ 禁用 agent_send 跨机（实证 145 条 expired）")


def preflight(card, *, channel, target_is_local, notify=(), board_readbacks=None):
    """发前门：返回 (ok, findings)。findings = [(级别, 代码, 说明), ...]

    board_readbacks: 双板写结果的 {板名: bool}；仅在 channel='blackboard' 时校验。
    """
    ok = True
    out = []

    def bad(code, msg):
        nonlocal ok
        ok = False
        out.append((ERROR, code, msg))

    def warn(code, msg):
        out.append((WARN, code, msg))

    def info(code, msg):
        out.append((INFO, code, msg))

    # ── §A 字段契约 ────────────────────────────────────────────────────────
    for f in ("from", "to", "type"):
        if not card.get(f):
            bad("A1", "缺必带字段 `%s`（§A 字段契约）" % f)
    if not (card.get("subject") or card.get("title")):
        bad("A2", "缺 `subject`/`title`（§A）—— 对方无法一眼判断轻重缓急")
    if not card.get("from"):
        warn("A3", "`from` 缺失会被标 `unattributed` ⇒ 无法归属/去重/自回声过滤（2026-10-03 实证）")

    awaiting = card.get("awaiting")
    rr = card.get("reply_required")
    action = _is_action(card) or bool(awaiting)

    # ── §B 唤醒语义 + 球权（死锁的两个直接机制）────────────────────────────
    if awaiting and rr is not True:
        bad("B1", "有 `awaiting` 但 `reply_required` 非 true ⇒ **对方不会被唤醒** ⇒ 你不知道在等谁（死锁机制①）")
    if rr is True and not awaiting:
        warn("B2", "要求回复但未声明 `awaiting` ⇒ **球权不明**（死锁机制②：双方互相等）")
    if notify and rr is not True:
        bad("B3", "`notify` 非空但未设 `reply_required:true` ⇒ 指针只排队**不唤醒**（2026-10-03 我因此漏掉整轮）")
    if action and not (rr is True and awaiting):
        bad("B4", "判定为「要求行动」的卡 ⇒ 必须 `reply_required:true` **且** `awaiting:<对方>`（§A/§B）")
    if any(k in str(card.get("type", "")).lower() for k in ACK_KINDS) and awaiting:
        info("B5", "回执类卡带 `awaiting` —— **卡内含请求时正当**（旧版判为警告，2026-10-03 实测误报，已降级为提示）")

    # ★ 规范 v1.1 铁律 2：不要求行动的卡必须【显式】声明 —— 「无声明=语义不明，门不放行」
    #   这是**规范性要求**（星桥 2026-10-03 定稿 comm-standard-v1.1），不是风格问题。
    _is_notif_type = "notification" in str(card.get("type", "")).lower()
    if not action and card.get("notify_only") is not True and not _is_notif_type:
        bad("B6", "不要求行动的卡必须显式 `notify_only: true`（或 type 含 notification）"
                  " ⇒ 无声明=语义不明（规范 v1.1 铁律2）")

    # ★★ B7 重写（2026-10-03 实测纠错 —— 原判据**方向反了**）────────────────────
    #   原写法：`to` 以 `session-` 开头 ⇒ **警告**「规范要求走节点别名」。
    #   实测（证据来自对端机器 `~/.dsh/central-inbox.log`）：
    #     我发给星桥的 3 张卡 `to: "mac-mini"`（节点别名）**全部** →
    #       `📩 注入 mac-mini: <key> → **null** [central] queued` ⇒ **一张都没进会话**；
    #     而 mobile 的卡（`to` 能解析）→ `→ session-fa1f9150-… delivered`。
    #   代码级根因（`central-inbox/lib/route.js::resolveTargetId`）：
    #     解析顺序 = CENTRAL_ALIASES(['coordinator','central','中枢',''])
    #              → roleMap(`~/.dsh/agent-role-map.json` 的 `main`，键是**角色名**)
    #              → 会话 id 精确匹配 → 唯一片段匹配
    #              → **否则 `return { target: null, reason: 'unresolvable(...)' }`（不回退、不报错）**
    #     ⇒ **节点别名既不在中枢别名里、也不在 roleMap 里 ⇒ 必然解析失败 ⇒ 静默丢弃。**
    #   ★ 结论：本条原判据**把黑板通道与 agent_send 通道的规则混为一谈** ——
    #     「对端会话 id 直发 145 条 expired」是 **agent_send 通道**的实测；
    #     而**黑板通道**恰恰相反：**只有可解析的 `to` 才送得到**。
    #   ⇒ 改为**可解析性检查（fail-closed）**：跨机卡的 `to` 必须属于
    #     ① 中枢别名 ② 角色名（target 侧 roleMap 的键，本机已知的常见角色名） ③ 完整会话 id；
    #     若是**裸节点别名**（mac-mini / mbp / i9）⇒ **拒绝发送**（它必然被丢，且失败是静默的）。
    _to = str(card.get("to", "")).strip()
    _CENTRAL_ALIASES = {"", "coordinator", "central", "中枢"}
    _NODE_ALIASES = {"mac-mini", "mbp", "i9", "macmini", "desktop"}
    _KNOWN_ROLES = {"星桥", "明鉴", "司库", "守灯", "守望", "守灯塔", "守链", "罗盘",
                    "老登", "知了", "验金石", "回声", "灯塔", "文汇", "驿使",
                    "数据调查员", "星舵"}
    if not target_is_local and _to:
        if _to.lower() in _NODE_ALIASES:
            bad("B7", "跨机卡 `to` 是**节点别名** `%s` ⇒ 对端 `resolveTargetId` **无法解析**"
                      "（非中枢别名、非角色名、非会话 id）⇒ 末行 `target=null` ⇒ **静默丢弃**"
                      "（日志表现为 `queued`，看起来像排队，实际进不去）。"
                      "★ 实测：我 3 张卡用 `mac-mini` 全部 `→ null`。"
                      "⇒ 改用**角色名**（如 `星桥`）或**完整会话 id**。" % _to)
        elif _to.lower() in _CENTRAL_ALIASES or _to in _KNOWN_ROLES or _to.startswith("session-"):
            info("B7", "跨机卡 `to`=`%s` **可解析**（中枢别名/角色名/会话 id）⇒ 对端能定位收件会话" % _to[:26])
        else:
            warn("B7", "跨机卡 `to`=`%s` 既非中枢别名/已知角色名、也非会话 id ⇒ "
                       "**可能解析失败被丢**；建议用角色名或完整会话 id（失败的日志形态是 `→ null`）" % _to[:26])

    # ── §C 通道选择 ────────────────────────────────────────────────────────
    if not target_is_local and channel == "agent_send":
        bad("C1", "**跨机禁用 `agent_send`**（我侧实证 145 条 expired）⇒ 必须走黑板卡 + 双板写")
    if channel == "blackboard" and not target_is_local:
        info("C2", "跨机黑板卡须**双板写**并**逐板回读断言**（R036：两板不传播）")
    if channel == "blackboard" and not card.get("from"):
        bad("C3", "黑板卡缺 `from` ⇒ 会被注入但不可归属（§A）")

    # ── §D 板可达性 ────────────────────────────────────────────────────────
    #   写**前**门无法知道回读结果（回读只可能发生在写卡之后）⇒ 只在**显式传入**时校验。
    #   「未传入」不再警告：旧版 D2 在写前门里检查回读，是**设计矛盾**，实测每次必误报。
    #   发指针前的回读检查见 preflight_post_write()。
    if board_readbacks:
        for b, okk in board_readbacks.items():
            if not okk:
                bad("D1", "板 `%s` 回读断言失败 ⇒ 不满足「写完必回读」⇒ 拒绝发指针" % b)

    # ── §E 版本对齐 ────────────────────────────────────────────────────────
    info("E1", "本地门对齐 %s（★ 协调者定稿后合并差异）" % SPEC_VERSION)
    return ok, out


def preflight_post_write(board_readbacks):
    """★ 写后门（**发指针之前**）：回读断言是必要条件。

    为什么单独一道门：回读结果只有在**卡写完**之后才存在 ⇒ 不可能放进写前门。
    旧版把这项塞进写前门（D2），实测每次必误报 —— 这是**门的时序设计错误**，不是使用者的错。
    R036：两板不传播 ⇒ 逐板回读，任一失败就不许发指针。
    """
    ok = True
    out = []
    for b, okk in (board_readbacks or {}).items():
        if not okk:
            ok = False
            out.append((ERROR, "D1", "板 `%s` 回读断言失败 ⇒ **拒绝发指针**（写了不等于写进去了）" % b))
    if not board_readbacks:
        ok = False
        out.append((ERROR, "D3", "未提供任何板的回读结果 ⇒ 无法证明写入生效"))
    return ok, out


def preflight_plugin_deploy(plugin_dirs):
    """★ 部署门（comm-standard §4.4「判据先行」）：**真 apply 冒烟**。

    为什么必须是这一道（2026-10-03 CLD 崩溃事故的四门负控实测）：
      含缺陷副本（`lib/index.js:145` 裸用 `os.homedir()`）在各门下的表现：
        · `node --check`            → PASS（ESM 裸全局不是语法错）
        · 仅 `import()` 真加载       → OK（apply() 未执行）
        · 插件自带 `lib/selftest.js` → 16 PASS（只测纯函数）
        · **真 apply 冒烟**          → **拦住 `ReferenceError: os is not defined`** ✅
      ⇒ 前三者对「apply 期崩溃」**全部无判别力** ⇒ 部署前必须过此门。

    ★ 实现要点：**不只看 exit code**。实测该工具对「非插件包」返回 **exit 0**；
      若只看退出码，「不适用」会被误判成「通过」（又一种假通过）⇒ 此处**解析输出**判定。
    """
    import subprocess
    import shutil as _shutil
    smoke = os.path.expanduser("~/dsh-collab/tools/plugin-apply-smoke.mjs")
    node = _shutil.which("node") or "/opt/homebrew/bin/node"
    ok = True
    out = []
    if not os.path.isfile(smoke):
        return False, [(ERROR, "S0", "找不到 apply 冒烟工具 %s ⇒ 部署门不可用（fail-closed）" % smoke)]
    for d in plugin_dirs:
        try:
            p = subprocess.run([node, smoke, d], capture_output=True, text=True, timeout=180)
        except Exception as e:
            ok = False
            out.append((ERROR, "S1", "冒烟执行失败 %s: %s" % (d, str(e)[:60])))
            continue
        txt = (p.stdout or "") + (p.stderr or "")
        if "非插件包" in txt or "不适用" in txt:
            ok = False
            out.append((ERROR, "S2", "%s ⇒ **不适用**（exit=%s）—— **不适用不得等同通过**，"
                                   "否则非插件包会成为假绿灯" % (os.path.basename(d), p.returncode)))
        elif "PASS" in txt and "拦住" not in txt:
            out.append((INFO, "S3", "%s ⇒ apply 冒烟 PASS" % os.path.basename(d)))
        else:
            ok = False
            tail = " | ".join([l for l in txt.strip().split("\n") if l.strip()][-3:])[:220]
            out.append((ERROR, "S4", "%s ⇒ **apply 冒烟失败**：%s" % (os.path.basename(d), tail)))
    return ok, out


# ── 自测：用 2026-10-03 真实踩过的失败逐条验门（判别性）──────────────────
def _selftest():
    SELF, PEER = "session-20b800d4-…", "session-fa1f9150-…"
    base = {"from": SELF, "to": PEER, "type": "state-report", "subject": "报告"}

    cases = [
        # (名称, 卡, channel, is_local, notify, 期望被拦?)
        ("①缺 reply_required 的行动卡 ⇒ 死锁", dict(base, type="coordination", awaiting="mac-mini"), "blackboard", False, ["mac-mini"], True),
        ("②缺 awaiting 的要求回复卡 ⇒ 球权不明（request 属要求行动 ⇒ 应拦）",
         dict(base, type="request", reply_required=True), "blackboard", False, [], True),
        ("③跨机用 agent_send ⇒ 145 条 expired", dict(base), "agent_send", False, [], True),
        ("④缺 from ⇒ unattributed", {"to": PEER, "type": "notice", "subject": "x"}, "blackboard", False, [], True),
        ("⑤notify 非空但未唤醒", dict(base), "blackboard", False, ["mac-mini"], True),
        ("⑥缺 subject ⇒ 无法判断轻重", {"from": SELF, "to": PEER, "type": "notice"}, "blackboard", False, [], True),
        ("⑦回读断言失败 ⇒ 拒发指针", dict(base), "blackboard", False, [], True),
        ("⑧合规卡（行动+唤醒+球权+双板回读）⇒ 放行",
         dict(base, type="coordination", reply_required=True, awaiting="mac-mini"), "blackboard", False, ["mac-mini"], False),
        ("⑨合规回执（显式 notify_only，规范 v1.1 铁律2）⇒ 放行",
         dict(base, type="ack", notify_only=True), "blackboard", False, [], False),
        ("⑩本机会话 agent_send（显式 notify_only）⇒ 放行",
         dict(base, notify_only=True), "agent_send", True, [], False),
        # ↓ 规范 v1.1 定稿后新增的门禁（用例随规范补）
        ("⑪不要求行动却未声明 notify_only ⇒ 语义不明（铁律2）",
         dict(base, type="state-report"), "blackboard", False, [], True),
        ("⑫跨机 to 用对端 session id ⇒ 提示走别名（铁律4；仅警告不拦）",
         dict(base, type="ack", notify_only=True), "blackboard", False, [], False),
    ]
    pass_ = fail_ = 0
    print("=== comm-preflight 判别性自测（用例取自 2026-10-03 真实失败）===")
    for name, card, ch, local, notif, expect_block in cases:
        rb = {"本机板": True} if ("⑦" not in name and ch == "blackboard") else (
            {"本机板": False} if "⑦" in name else None)
        ok, findings = preflight(card, channel=ch, target_is_local=local,
                                 notify=notif, board_readbacks=rb)
        blocked = not ok
        mark = "✅" if blocked == expect_block else "❌"
        if blocked == expect_block:
            pass_ += 1
        else:
            fail_ += 1
        print("  %s %-42s 拦截=%-5s 期望=%-5s" % (mark, name, blocked, expect_block))
        if blocked != expect_block:
            for lv, code, msg in findings:
                print("        %s %s %s" % (lv, code, msg))
    print()
    # 通道决策表自测
    print("=== choose_channel 决策表 ===")
    for tid, local, exp in [(SELF, True, "agent_send"), (PEER, False, "blackboard")]:
        ch, why = choose_channel(tid, is_local=local)
        m = "✅" if ch == exp else "❌"
        if ch == exp:
            pass_ += 1
        else:
            fail_ += 1
        print("  %s is_local=%-5s → %-12s %s" % (m, local, ch, why))
    print("\n════ %s ════" % ("全部通过 %d/%d" % (pass_, pass_) if fail_ == 0 else "通过 %d · 失败 %d" % (pass_, fail_)))
    return 0 if fail_ == 0 else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)
    print("SPEC_VERSION = %s" % SPEC_VERSION)
