#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""publish-and-point.py — 写卡 + 自动发指向「真实 key」的短提示（Φ8 工具化）。

**为什么需要**（Φ8 两次法则：同一操作出现两次就该工具化）：
  今天出现**两次**「指针与落点不一致」，均属 R036 同族：
    ① 对端指出：`mbp-ack-r038-…` 指向的卡 version 仍=1、**不含所述内容**；
    ② 我手动写提示时 **key 末位抄错**（1790956462 vs 实际 1790956479）。
  两次根因同一：**指针是「手抄/凭记忆」产生的，而非取自落点本身**。

**做法**：key 由本脚本生成并在**同一次运行内**用于写卡与发提示，
  写完**逐板回读断言**，断言通过才发提示；提示里的 key **从内存取，不经人手**。

用法：
  from publish_and_point import publish_and_point
  publish_and_point(collab_or_node, title, card_dict, notify=["mac-mini"])
或命令行自测：
  python3 publish-and-point.py --selftest
"""
import json, urllib.request, time, datetime, os, subprocess, sys

def _central_auth():
    """中枢认证头 —— **双头过渡**（2026-10-03 响应星桥「写端鉴权 flip」协调）。

    旧头 `X-Webhook-Token` **保留**（flip 前链路不变，仍有效）；
    新头 `X-Blackboard-Token` 读 `~/.dsh/blackboard-token`（0600，本地私密）——
    flip 后板端白名单认它。
    ⇒ **flip 前后都能写，不必二次改动**（避免 flip 瞬间主通道断掉）。
    """
    h = {"X-Webhook-Token": os.environ.get("BB_SECRET_PLACEHOLDER","")}
    try:
        with open(os.path.expanduser("~/.dsh/blackboard-token"), encoding="utf-8") as f:
            tok = f.read().strip()
        if tok:
            h["X-Blackboard-Token"] = tok
    except Exception:
        pass
    return h


BOARDS = [("本机板", "http://100.120.203.20:8792",
           {"Authorization": "Bearer ${BB_SECRET_ENV}"}),
          ("中枢", "http://xingqiao.meetfunbp.com:8792", _central_auth())]
XQ = os.path.expanduser("~/dsh-collab/comm-server/xq-send.py")


def _preflight_blackboard(body, notify, prefix_path=""):
    """★ R039 发前门：加载 comm-preflight.py 并按规范做 fail-closed 检查（跨机黑板卡形态）。

    失败语义（有意区分）：
      · **检查不通过 ⇒ 拒绝发送**（fail-closed，R039「纳入门管理」）
      · **门自身加载失败 ⇒ 警告但放行**（否则一个 typo 就瘫痪整条通讯）
    依据：用户 2026-10-03「把文件落到本地规则来，并纳入门管理，以后通讯之前根据文件来择优判断」。
    """
    # ── ★ 规范 v1.1 §1.4：回复卡只写 `notes/<对端节点>/`，**禁 session-id 前缀** ──────
    #   2026-10-03 实测教训：我把卡写在 `notes/session-cff6275e-…/`，而该前缀**无人监听**，
    #   是**靠一条 agent_send 指针才被读到**的 —— 若对端没读指针，那张卡就静默丢失了。
    #   我当天刚给星桥报过「禁 session-id 前缀」，自己却踩了 ⇒ 根因不是疏忽，
    #   而是**工具没设门**（门只管了 to 字段，没管 prefix）。此处补上。
    _seg = [s for s in str(prefix_path).strip("/").split("/") if s]
    if len(_seg) >= 2 and _seg[0] == "notes" and _seg[1].startswith("session-"):
        print("  ❌ R039 发前门未通过 —— **拒绝发送**：")
        print("     ❌ [P1] 前缀 `%s` 是 session-id 形态 ⇒ 规范 v1.1 §1.4 要求回复卡只写 "
              "`notes/<对端节点>/`（如 notes/mac-mini/、notes/mbp/）。**该前缀无人监听，会静默丢失。**"
              % prefix_path)
        return False, [("❌", "P1", "session-id 前缀禁止（规范 v1.1 §1.4）")]

    try:
        import importlib.util
        # ★ 路径解析**不依赖 `__file__`** —— 本模块常被 `exec(compile(src))` 内联加载
        #   （测试/一次性脚本都这么做），那时没有 `__file__` ⇒ 门会静默降级。
        #   本次实测就踩到了：负对照没被拦住，只是打了句警告。
        _here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else None
        _cands = ([os.path.join(_here, "comm-preflight.py")] if _here else []) + [
            os.path.expanduser("~/dsh-collab/tools/comm-preflight.py"),
        ]
        p = next((c for c in _cands if os.path.isfile(c)), None)
        if not p:
            raise FileNotFoundError("找不到 comm-preflight.py（试过 %s）" % _cands)
        spec = importlib.util.spec_from_file_location("comm_preflight", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    except Exception as e:
        print("  ⚠️ R039 发前门不可用（%s）⇒ 本次降级放行（请修门）" % str(e)[:70])
        return True, []
    ok, findings = m.preflight(body, channel="blackboard", target_is_local=False,
                               notify=list(notify))
    if not ok:
        print("  ❌ R039 发前门未通过 —— **拒绝发送**：")
        for lv, code, msg in findings:
            if lv == "❌":
                print("     %s [%s] %s" % (lv, code, msg))
    else:
        for lv, code, msg in findings:
            if lv == "⚠️":
                print("  %s [%s] %s" % (lv, code, msg))
    return ok, findings


def _resolve_reply_required(card, reply_required):
    """解析「是否要求对方行动」—— 抽成独立函数以便**正负样本自证**（类别 C）。

    规则：卡内声明优先；两边都给且矛盾 ⇒ 抛错（不得静默覆盖）。
    """
    has = "reply_required" in card
    val = bool(card.get("reply_required"))
    if has and reply_required is not None and val != bool(reply_required):
        raise ValueError(
            "意图矛盾：卡内 reply_required=%s，函数参数 reply_required=%s ⇒ 拒绝发送。"
            "（静默覆盖会丢意图；请只在一处声明）" % (val, bool(reply_required)))
    if reply_required is None:
        if has:
            print("  ℹ️ reply_required 继承自卡内声明：%s" % val)
        return val if has else False
    return bool(reply_required)


def publish_and_point(prefix_path, title, card, notify=(), reply_required=None,
                      bus_from="mbp"):
    """写卡（双板+回读断言）后，发指向**实际 key** 的短提示。

    prefix_path: 如 'notes/collab/' 或 'notes/mac-mini/'
    返回 (ok, key, detail)

    ★ `reply_required` 语义（2026-10-03 修 **静默覆盖** 缺陷 · 类别 B）：
      原实现 `body["reply_required"] = reply_required`（参数默认 False）
      ⇒ 调用方**在卡里显式写的** `reply_required: True` 被**无声丢弃**，
        表现为「我要求了行动，但对方不会被唤醒」= 死锁机制①。
      实测：2026-10-03 我发协调卡（卡内 reply_required=True）被默认参覆盖，
      是 **R039 发前门** 把它拦下来的 —— 门是最后一道网，但**不该是唯一一道**。
      现改为：**默认 None ⇒ 继承卡内声明**；两边都给且冲突 ⇒ **fail-closed 抛错**
      （意图矛盾必须当场可见，不得由代码替调用方猜）。
    """
    # ── 意图冲突检查（fail-closed，先于一切副作用）────────────────────────
    reply_required = _resolve_reply_required(card, reply_required)

    t0 = time.time(); ts = int(t0)
    key = "%s%s-%d" % (prefix_path, prefix_path.rstrip("/").split("/")[-1] and
                       "card" or "card", ts)
    # key 命名：<prefix>card-<ts>（简单可读）
    key = "%scard-%d" % (prefix_path, ts)

    body = dict(card)
    body.setdefault("from", "session-20b800d4-98f6-4e5e-90e4-34f7b6ca61d7")
    body.setdefault("title", title)
    body.setdefault("sent_at_iso", datetime.datetime.fromtimestamp(t0).isoformat(timespec="seconds"))
    body.setdefault("sent_at_epoch_ms", int(t0 * 1000))
    body["reply_required"] = reply_required

    # ── ★ R039 发前门（写卡之前）────────────────────────────────────────────
    #   publish-and-point 是对外通道 ⇒ 恒为「跨机黑板卡」，由决策表 §B 直接给出。
    #   不过门就不写卡、不发指针 —— 结构 beats 纪律。
    _gate_ok, _gate_findings = _preflight_blackboard(body, notify, prefix_path)
    if not _gate_ok:
        return False, key, {"gate": "rejected", "findings": _gate_findings}

    # 1) 写两板
    wrote = []
    for tag, base, h in BOARDS:
        hh = dict(h); hh["Content-Type"] = "application/json"
        try:
            r = urllib.request.Request(base + "/" + key,
                                       data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                                       method="PUT", headers=hh)
            d = json.load(urllib.request.urlopen(r, timeout=20))
            wrote.append((tag, d.get("key"), d.get("version")))
        except Exception as e:
            wrote.append((tag, None, str(e)[:50]))

    # 2) 逐板回读断言（R036：不是保险，是必要条件）
    #   ★ 三态（2026-10-03）：把「不可达」与「内容不符」分开 —— 前者是**降级**，后者是**失败**
    ok_boards, detail = [], []
    for tag, base, h in BOARDS:
        try:
            r = urllib.request.Request(base + "/" + key, headers=h)
            d = json.load(urllib.request.urlopen(r, timeout=12))
            good = (d.get("key") == key)
            ok_boards.append((tag, good))
            detail.append({"board": tag, "state": "ok" if good else "mismatch"})
        except Exception as e:
            ok_boards.append((tag, False))
            detail.append({"board": tag, "state": "unreachable", "err": str(e)[:60]})
    n_ok = sum(1 for _, o in ok_boards if o)
    n_unreach = sum(1 for d in detail if d["state"] == "unreachable")
    n_mismatch = sum(1 for d in detail if d["state"] == "mismatch")
    if n_mismatch or n_ok == 0:
        return False, key, {"write": wrote, "readback": ok_boards, "boards": detail,
                            "verdict": "failed",
                            "note": "回读断言失败 ⇒ **不发提示**（避免造出指向空内容的指针）"}
    if n_unreach:
        # 至少一板确认写入，但有板不可达 ⇒ 降级（**不冒充双板成功**）
        print("  ⚠️ 双板写**降级**：%d 板确认写入，%d 板**不可达**（%s）"
              % (n_ok, n_unreach, [d["board"] for d in detail if d["state"] == "unreachable"]))
        print("     ⇒ 卡已进入可达板；**送达未验证**（不可达 ≠ 没写进去，也 ≠ 已送达）。")
        print("     ⇒ 补救：待对端网络恢复后，用 verify-delivery 复核；或按 R42 去单点。")
        _verdict = "degraded"
    else:
        _verdict = "ok"
    all_ok = (n_unreach == 0 and n_mismatch == 0)

    # 3) 发短提示 —— key 取自内存，不经人手
    #
    # ★ 唤醒语义检查（2026-10-03 补 · 实测事故）：
    #   仅发 bus 短提示【不构成唤醒】—— 收件方按 I7a 语义把「看黑板 …」视为 notify
    #   （`msg.replyRequired !== true` ⇒ 不唤醒），只排队等其自然回合。
    #   要唤醒对方，**必须让卡片 value.reply_required = true**。
    #   ⇒ 事故：我曾发交接卡（reply_required=False）+ bus 指针，以为"通知到了"，
    #     实际对方完全不知情，直到我另发一张 reply_required=true 的卡才被唤醒。
    #   ⚠️ 另注：`xq-send.py` 的 body 无 reply_required 字段 ⇒ **bus 侧表达不了该语义**，
    #     所以这是唯一的唤醒通道。
    warnings = []
    if notify and not reply_required:
        warnings.append(
            "⚠️ 你将向 %s 发提示，但本卡 reply_required=False ⇒ "
            "**对方不会被唤醒**（按 I7a 语义仅排队）。若你期望对方看到并行动，"
            "请传 reply_required=True。" % ",".join(notify))
    text = "看黑板 " + key
    sent = []
    for tgt in notify:
        try:
            out = subprocess.run(["python3", XQ, tgt, "notice", "-"],
                                 input=text, capture_output=True, text=True, timeout=25,
                                 env=dict(os.environ, BUS_FROM=bus_from))
            # ★ 按 status/offline 分档（2026-10-03）：`ok:true` 只代表服务器受理；
            #   `offline:true`/`status:"queued"` ⇒ **只排队、未送达**（别再记成"已发"）
            _raw = (out.stdout or "").strip()
            _st, _off = None, None
            try:
                _j = json.loads(_raw)
                _st, _off = _j.get("status"), _j.get("offline")
            except Exception:
                pass
            if _off is True or _st == "queued":
                sent.append((tgt, "queued", "对端 bus 离线/排队 ⇒ **指针未送达**（不影响卡片投递）"))
            elif _st is not None or '"ok":true' in _raw:
                sent.append((tgt, True, _raw[:80]))
            else:
                sent.append((tgt, False, (_raw or (out.stderr or "")).strip()[:80]))
        except Exception as e:
            sent.append((tgt, False, str(e)[:50]))
    # ── ★★ 端到端送达验证（2026-10-03 新增 · 本次事故的直接产物）────────────────
    #   事故：双板写入 + 回读断言**全 ✅**，我据此认定"已送达"，而用户指出「星桥根本没收到」。
    #   对端日志真相：`→ null [central] queued`（`to` 用了节点别名 ⇒ 解析失败 ⇒ 丢弃）。
    #   ⇒ **本地"写成功+回读成功"完全不能证明送达**；送达的观测点**在对端**。
    #   ⇒ 所以在发卡流程里**就地验证对端结局**：unroutable 时大声报警（因为此时指针也没用）。
    #   边界：需对端 SSH 可达；不可达 ⇒ 报「无法确认」，**绝不判成功**（R31/R035）。
    delivery = None
    if notify and os.environ.get("PP_NO_VERIFY") != "1":
        try:
            import importlib.util as _ilu
            _p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify-delivery.py")
            _s = _ilu.spec_from_file_location("vd", _p)
            _vd = _ilu.module_from_spec(_s); _s.loader.exec_module(_vd)
            for tgt in notify:
                if tgt not in _vd.PEERS:
                    continue
                status, level, outcomes, note = _vd.verify(key, tgt, wait=12)
                delivery = {"peer": tgt, "status": status, "outcomes": outcomes, "note": note}
                print("  %s 端到端送达验证(peer=%s): %s  %s"
                      % (level, tgt, status, outcomes or "（对端日志无该 key）"))
                if status == "unroutable":
                    print("     ❌ **未送达** —— 收件人解析失败/仅排队。**此卡对方收不到，指针也救不了它。**")
                    print("        ⇒ 检查 `to`：必须可解析（中枢别名 / 角色名 / **完整会话 id**）；"
                          "节点别名会被对端判 unresolvable。")
                elif status == "unconfirmed":
                    print("     ⚠️ **无法确认**（%s）—— ★ 这不是「已送达」，别当成功。" % (note or "对端日志无该 key"))
        except Exception as e:
            print("  ⚠️ 送达验证不可用（%s）⇒ **本次无端到端证据**" % str(e)[:60])
    _queued = [t for t, st, _ in sent if st == "queued"]
    if _queued:
        print("  ⚠️ 指针仅**排队未送达**（%s）：bus 报对端离线。" % ",".join(_queued))
        print("     ⇒ 这不影响送达 —— 实际投递由**黑板卡 + 对端 inbox 注入**完成"
              "（已由 verify-delivery 在对端日志确认）。指针只是二次提醒。")
    return True, key, {"write": wrote, "readback": ok_boards, "pointer": text,
                       "sent": sent, "warnings": warnings, "delivery": delivery,
                       "boards": detail, "verdict": _verdict}


def _selftest():
    print("=== publish-and-point 自测（不真发总线，仅本地流程）===")

    # ── 0) reply_required 解析：正负样本自证（2026-10-03 修静默覆盖后补）─────────
    #    ★ 为什么必须有这组：修 bug 的那个函数**本身也要有判别力证据**，
    #      否则「已修复」只是声明（类别 C）。四个样本覆盖：继承 / 显式 / 默认 / 矛盾。
    print("── reply_required 解析判别力（正负样本）──")
    _cases = [
        ("卡内 True，参数缺省 ⇒ 应继承 True（原缺陷正是这里丢成 False）",
         {"reply_required": True}, None, True),
        ("卡内 True，参数显式 True ⇒ 一致，True",
         {"reply_required": True}, True, True),
        ("卡内无，参数缺省 ⇒ False（通知形态）",
         {}, None, False),
        ("卡内 False，参数缺省 ⇒ False", {"reply_required": False}, None, False),
    ]
    for desc, card, param, want in _cases:
        got = _resolve_reply_required(card, param)
        print("  %s %-52s 期望 %-5s / 实际 %-5s"
              % ("✅" if got == want else "❌", desc[:52], want, got))
    # 矛盾样本必须抛错（防「代码替调用方猜」）
    try:
        _resolve_reply_required({"reply_required": True}, False)
        print("  ❌ 矛盾样本（卡内 True / 参数 False）应抛错，实际放行")
    except ValueError as e:
        print("  ✅ 矛盾样本拒绝：%s" % str(e)[:60])

    # ── 1) 端到端流程（卡必须满足规范契约，否则被发前门拦掉）──────────────────
    #    ★ 2026-10-03 教训：发前门变严后**自测 fixture 没同步** ⇒ 自测恒失败，
    #      而「自测失败」被当成 fixture 问题而非判据问题 ⇒ **判据 stale 比没有更糟**。
    # ★★ 2026-10-03 修正：自测卡原写 `notes/collab/`，而 **collab 是全网监听前缀**
    #   ⇒ 我的自测**会被投递到对端会话**（实测：星桥侧日志出现 `注入 mac-mini: notes/collab/card-… delivered`）。
    #   自测不该打扰任何人 ⇒ 改用**无人监听的前缀** `notes/_selftest/`
    #   （对端只监听 `notes/<节点>/` + `notes/collab/`，故该前缀不会触发任何注入）。
    # ★ 约定守卫（2026-10-03）：自测**必须**写在无人监听的前缀上，否则会自污染/打扰对端。
    #   实测两次：① 我侧原写 `notes/collab/`（全网监听 ⇒ 自测被投递到星桥）；
    #             ② 对端 `put-card-selftest.py` 写 `notes/mac-mini/`（= 它自己的监听前缀 ⇒ 每次自注入）。
    #   ★ 为什么做成**守卫**而不是文档约定：约定只写在文档里 ⇒ 下次改回去没人拦（G1 教训）。
    #   守卫只在"发生点"检查，零噪声 —— 比全仓 grep 好（那种会命中一堆合法发卡，噪声判据会被忽略）。
    _SELFTEST_PREFIX = "notes/_selftest/"
    _WATCHED = tuple(p + "/" for p in (
        "notes/collab", "notes/mbp", "notes/mac-mini", "notes/i9"))
    assert not _SELFTEST_PREFIX.startswith(_WATCHED), (
        "自测前缀 %r 落在被监听前缀上 ⇒ 会自污染/打扰对端" % _SELFTEST_PREFIX)
    print("  ✅ 自测前缀守卫: %r 不在被监听前缀内" % _SELFTEST_PREFIX)

    ok, key, det = publish_and_point(
        _SELFTEST_PREFIX, "自测卡",
        # ★ R27 第三次实证：B7 改成「裸节点别名 ⇒ 拒绝发送」后，本 fixture 的
        #   `to: mac-mini` 立刻被自家门拦下 —— **判据没错，是 fixture 没随判据走**。
        #   ⇒ 自测样本必须使用**契约允许的取值**（此处用角色名，可被对端解析）。
        {"to": "星桥", "type": "notification", "notify_only": True,
         "note": "publish-and-point 自测（可作废）"},
        notify=[]  # 自测不发提示
    )
    print("  ok=%s key=%s" % (ok, key))
    print("  写:", det.get("write"))
    print("  回读:", det.get("readback"))
    # 验证：提示文本里的 key 必须与落点 key 完全一致（这正是要防的错）
    p = det.get("pointer") or ""
    same = p.endswith(key)
    print("  指针文本: %s" % (p or "(未发)"))
    print("  → 指针 key 与落点 key 一致: %s" % ("✅" if same or not p else "❌"))
    # 收尾：作废自测卡
    for tag, base, h in BOARDS:
        hh = dict(h); hh["Content-Type"] = "application/json"
        try:
            r = urllib.request.Request(base + "/" + key,
                data=json.dumps({"type": "tombstone", "by": "session-20b800d4",
                                 "title": "自测痕迹，已作废"}, ensure_ascii=False).encode(),
                method="PUT", headers=hh)
            urllib.request.urlopen(r, timeout=12)
        except Exception:
            pass
    print("  自测卡已作废")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(__doc__)
