#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cahac-envelope —— 【共享】CAHAC §3 信封字段补全

★★ 立据（2026-10-13 实测）：
  `notes/collab` 现测 **envelope_ok = 0/642 = 0.0000%**（v6.1 时 0/564）
  ⇒ ★★ **两版之间一点没变**。
  ★ 而根因不是「写得少」—— 抽三张真实卡，**字段名各不相同**
  （甚至有用中文标题当键名的）⇒ ★★ **是【没有写卡侧的 schema 约定】**。

★ 本模块把 CAHAC §3 的 14 字段（必填 12）**补齐到一个已有的卡 dict 上**，
  ★ 供各写者调用 ⇒ **一次改、覆盖全部经它的卡**。

★ 设计（★ 三条纪律）：
  ① **只补能从上下文推出的** —— 推不出的**留空并如实报**，★ **不臆造**。
  ② **不改已有值** —— 若卡里已有同名字段，以卡里的为准（★ 卡作者更懂）。
  ③ **纯函数** —— 不写盘、不发网络、不改调用方状态（★ 可被任意写者安全调用）。

★ 用法：
    from cahac_envelope import complete_envelope
    card = complete_envelope(card, key="notes/collab/x-123", to="session-abc", sender="session-def")
    # 或 CLI：
    python3 scripts/cahac-envelope.py <card.json>            # 补全并打印到 stdout
    python3 scripts/cahac-envelope.py <card.json> --check    # 只判，不改
    python3 scripts/cahac-envelope.py --selftest
"""
import argparse
import hashlib
import json
import os
import sys

# ★ CAHAC §3 的 14 字段（★ 源：research/cost-governance/cahac-protocol-v1.2.md:128-145）
FIELDS = ["cahac", "id", "type", "channel", "sender", "recipient", "thread",
          "priority", "cost_cap", "dedup_key", "ts", "expires", "payload", "signature"]

# ★ 可选（★ 依 §3 字段规则：signature v1.0 可选；expires 为 TTL 可选）
OPTIONAL = {"signature", "expires"}

# ★ 必填 12
REQUIRED = [f for f in FIELDS if f not in OPTIONAL]

CAHAC_VERSION = "v1.2"


def _dedup(card):
    """★ 内容指纹（★ 依 CAHAC v1.2 裁定：dedup_key = `sha256:<hex>`）"""
    basis = {k: v for k, v in card.items()
             if k not in ("dedup_key", "ts", "sent_at_epoch_ms")}
    try:
        blob = json.dumps(basis, ensure_ascii=False, sort_keys=True,
                          allow_nan=False).encode("utf-8")
    except Exception:
        blob = repr(sorted(basis.items())).encode("utf-8", "replace")
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def _id_from_key(key):
    if not key:
        return None
    return str(key).rstrip("/").split("/")[-1] or None


def resolve_author(env=None):
    """★ ★ Python 版【作者解析】—★ 与 JS 侧 `dsh-comm-shared/identity.js:180` 同形。

    ★ 依据：该 JS 版的三条路径 —★
      `exec.agent.id`（★ 运行时身份）→ `env.DSH_SESSION_ID`（★ 环境回退）→ `unattributed`；
      ★ 且**输出 identitySource**（exec/env/none）使「值从哪来」可核（★ 防「看起来对其实是别人」）。
    ★ 本版只有 env 一条（★ Python 侧无 exec 对象）⇒ ★ 如实标为 `env`。
    """
    env = env if env is not None else os.environ
    _id = env.get("DSH_SESSION_ID") or env.get("AUTHOR_SESSION") or ""
    return {"id": _id or "unattributed",
            "resolved": bool(_id),
            "identitySource": "env" if _id else "none"}


def complete_envelope(card, key=None, to=None, sender=None, channel="blackboard",
                      now_iso=None):
    """★ 就地把 card 补到 CAHAC §3 齐备（★ 不覆盖已有值）。

    :returns: (card, report) —— report = {"filled":[...], "kept":[...], "missing":[...]}
    """
    if not isinstance(card, dict):
        raise TypeError("card 必须是 dict")
    import datetime as _dt
    now_iso = now_iso or _dt.datetime.now().astimezone().isoformat(timespec="seconds")

    # ★★ 2026-10-13：sender 缺时用【resolve_author】推（★ 而不直接臭在 None）
    _auth = resolve_author()
    _sender = sender or card.get("from") or card.get("sender")
    if not _sender and _auth["resolved"]:
        _sender = _auth["id"]

    # ★ 派生值（★ 只从上下文推，推不出即 None）
    derived = {
        "cahac": CAHAC_VERSION,
        "id": _id_from_key(key) or card.get("id"),
        "type": card.get("type") or card.get("card_type") or card.get("类型") or "card",
        "channel": channel,
        "sender": _sender,
        "recipient": to or card.get("to") or card.get("recipient"),
        "thread": card.get("thread"),
        # ★ priority：卡里已有则保留；否则 normal（★ 依 §3 的 urgency/priority 语义）
        "priority": card.get("priority") or "normal",
        # ★ cost_cap：规格 :148「任务级预算（0=无限制）」⇒ 缺省 0
        "cost_cap": card.get("cost_cap") if card.get("cost_cap") is not None else 0,
        "ts": card.get("ts") or now_iso,
    }

    filled, kept, missing = [], [], []
    for f in FIELDS:
        if f == "payload":
            # ★ ★ payload = 卡体自身（★ 侧录当前 card 的快照，★ 不无限套）
            #   ★ 已有 ⇒ 保留；无 ⇒ 补一个浅快照（★ 不套自身）
            if card.get("payload") not in (None, ""):
                kept.append(f)
            else:
                card["payload"] = {kk: vv for kk, vv in card.items() if kk != "payload"}
                filled.append(f)
            continue
        if f == "dedup_key":
            if card.get("dedup_key"):
                kept.append(f)
            else:
                card["dedup_key"] = _dedup(card)
                filled.append(f)
            continue
        if f == "signature" or f == "expires":
            continue  # ★ 可选，不补
        if card.get(f) not in (None, ""):
            kept.append(f)
            continue
        # ★★ thread：CAHAC 列为必填（★ 非可选），★ 而它【经常无值】—★
        #   ★ 故【补 null 占位】（★ 键在 ⇒ 工具的 `f in v` 判据成立）—★
        #   ★ 而不伪造一个假的 thread 值。
        if f == "thread":
            card["thread"] = card.get("thread") or None
            filled.append(f + "(空占位)")
            continue
        v = derived.get(f)
        if v in (None, ""):
            missing.append(f)       # ★ 推不出 ⇒ 如实报，★ 不臆造
        else:
            card[f] = v
            filled.append(f)

    return card, {"filled": filled, "kept": kept, "missing": missing}


def check_envelope(card):
    """★ 只判：返回 (ok, missing_required, present_optional)"""
    if not isinstance(card, dict):
        return False, list(REQUIRED), []
    # ★ thread 允许为 None（★ 键在即可）；其余必填需有非空值
    miss = [f for f in REQUIRED
            if (f not in card) or (f != "thread" and card.get(f) in (None, ""))]
    opt = [f for f in OPTIONAL if card.get(f) not in (None, "")]
    return (not miss), miss, opt


def selftest():
    ok = tot = 0
    # ★ 正控 1：空卡 + 上下文 ⇒ 应补到齐
    tot += 1
    c1, r1 = complete_envelope({"subject": "x", "notify_only": True},
                               key="notes/collab/abc-1", to="session-t", sender="session-s")
    o1, m1, _ = check_envelope(c1)
    if o1 and not m1:
        ok += 1; print("  ✅ 正控：空卡 + 上下文 ⇒ 补到齐（filled=%d）" % len(r1["filled"]))
    else:
        print("  ❌ 正控失败：缺 %s" % m1)
    # ★ 正控 2：不覆盖已有值
    tot += 1
    c2, _ = complete_envelope({"type": "MINE", "priority": "P0", "cost_cap": 999},
                              key="notes/collab/k", to="t", sender="s")
    if c2["type"] == "MINE" and c2["priority"] == "P0" and c2["cost_cap"] == 999:
        ok += 1; print("  ✅ 正控：已有值【不被覆盖】")
    else:
        print("  ❌ 正控失败：已有值被改了")
    # ★ 负控 1：无 key/to/sender ⇒ recipient 等应【如实报缺】而不是臆造
    tot += 1
    c3, r3 = complete_envelope({})
    if "recipient" in r3["missing"]:
        ok += 1; print("  ✅ 负控：推不出的字段进 missing（★ 不臆造）")
    else:
        print("  ❌ 负控失败：recipient 未被报缺")
    # ★ 正控 3：dedup_key 是 sha256 形态
    tot += 1
    if str(c1.get("dedup_key", "")).startswith("sha256:") and len(c1["dedup_key"]) == 71:
        ok += 1; print("  ✅ 正控：dedup_key 为 sha256:<64hex>")
    else:
        print("  ❌ 正控失败：dedup_key 形态不对：%s" % c1.get("dedup_key"))
    # ★ 正控 4：check 能认齐备卡
    tot += 1
    okc, _, _ = check_envelope(c1)
    if okc:
        ok += 1; print("  ✅ 正控：check_envelope 认齐备卡")
    else:
        print("  ❌ 正控失败：check 不认齐备卡")
    # ★ 负控 2：check 对缺字段的卡必须红
    tot += 1
    bad, mb, _ = check_envelope({"type": "x"})
    if (not bad) and "cahac" in mb:
        ok += 1; print("  ✅ 负控：check 对缺字段的卡报红（缺 %d）" % len(mb))
    else:
        print("  ❌ 负控失败：check 未报红")
    # ★ resolve_author：环境有则解析，无则 unattributed
    tot += 1
    if resolve_author({"DSH_SESSION_ID": "session-abc"})["id"] == "session-abc":
        ok += 1; print("  ✅ 正控：resolve_author 能从 env 解出")
    else:
        print("  ❌ resolve_author env 解析失败")
    tot += 1
    if resolve_author({})["id"] == "unattributed" and resolve_author({})["resolved"] is False:
        ok += 1; print("  ✅ 负控：无 env ⇒ unattributed（★ 不臆造）")
    else:
        print("  ❌ 负控失败：无 env 未报 unattributed")
    # ★ 必填数口径
    tot += 1
    if len(REQUIRED) == 12:
        ok += 1; print("  ✅ 正控：必填恰 12（14 − 2 可选）")
    else:
        print("  ❌ 必填数=%d 应为 12" % len(REQUIRED))
    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="\u5361 JSON \u6587\u4ef6")
    ap.add_argument("--key", default=None)
    ap.add_argument("--to", default=None)
    ap.add_argument("--sender", default=None)
    ap.add_argument("--check", action="store_true", help="\u53ea\u5224\u4e0d\u8865")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("cahac-envelope 1.0.0"); return 0
    if a.selftest:
        return selftest()
    if not a.path:
        ap.print_help(); return 2
    card = json.load(open(a.path, encoding="utf-8"))
    if a.check:
        ok, miss, opt = check_envelope(card)
        print("  envelope_ok = %s" % ("TRUE" if ok else "false"))
        print("  \u7f3a\u5fc5\u586b: %s" % (miss or "\u65e0"))
        print("  \u5df2\u6709\u53ef\u9009: %s" % (opt or "\u65e0"))
        return 0 if ok else 1
    card, rep = complete_envelope(card, key=a.key, to=a.to, sender=a.sender)
    print(json.dumps(card, ensure_ascii=False, indent=1))
    print("\n  \u8865\u4e86: %s" % (rep["filled"] or "\u65e0"), file=sys.stderr)
    print("  \u4fdd\u7559: %s" % (rep["kept"] or "\u65e0"), file=sys.stderr)
    print("  \u63a8\u4e0d\u51fa: %s" % (rep["missing"] or "\u65e0"), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
