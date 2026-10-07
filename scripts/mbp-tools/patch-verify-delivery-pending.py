#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch-verify-delivery-pending.py —— 区分「已解析但排队」与「解析失败」

【缺陷】（2026-10-03 22:30 实测）
  对端日志新形态：`📩 注入 mac-mini: <key> → session-fa1f9150-… [central] queued`
  —— **目标已解析成功**（拿到了完整会话 id），只是**排队待唤醒**。
  而我的 `judge()` 把任何 `queued` 一律判 `unroutable` ⇒ 报「**未送达 · 此卡对方收不到**」
  ⇒ **假警报**（且语气很重，会误导人以为丢了卡）。
  ★ 这正是"pending ≠ failed"的老问题，与 R31/R42 同族：**必须把"待投递"单列一档。**

【修法】四档：
  · `delivered`  ：target 非空 且 出现 `delivered`
  · **`pending`**：target 非空 且 `queued`（已解析、待唤醒投递 —— 对端 0.2.11 起会这么打）
  · `unroutable` ：target 为 `null`（解析失败 ⇒ 真丢）
  · `unconfirmed`：只有 `duplicate`（不算送达证据）或日志里查不到
"""
import io
import os

p = os.path.expanduser("~/dsh-collab/tools/verify-delivery.py")
s = io.open(p, encoding="utf-8").read()

old = '''    if not outcomes:
        return "unconfirmed", "⚠️"
    evidence_delivered = any(t not in ("null", "None", "") and v == "delivered"
                             for t, v in outcomes)
    evidence_unroutable = any(t in ("null", "None", "") or v == "queued"
                              for t, v in outcomes)
    if evidence_delivered:
        return "delivered", "✅"
    if evidence_unroutable:
        return "unroutable", "❌"
    return "unconfirmed", "⚠️"'''
new = '''    if not outcomes:
        return "unconfirmed", "⚠️"
    has_target = lambda t: t not in ("null", "None", "")
    evidence_delivered = any(has_target(t) and v == "delivered" for t, v in outcomes)
    # ★ 新增 pending：**目标已解析**但排队待唤醒（对端 0.2.11「排完整 id 待唤醒·不丢卡」的形态）
    evidence_pending = any(has_target(t) and v == "queued" for t, v in outcomes)
    evidence_unroutable = any(not has_target(t) for t, v in outcomes)
    if evidence_delivered:
        return "delivered", "✅"
    if evidence_unroutable:
        return "unroutable", "❌"
    if evidence_pending:
        return "pending", "⏳"
    return "unconfirmed", "⚠️"'''
assert old in s, "judge 锚点未命中"
s = s.replace(old, new, 1)

# 主流程：处理 pending 分支
old2 = '''    if status == "unroutable":'''
new2 = '''    if status == "pending":
        print("  %s **已解析但排队待唤醒** —— 目标已定位（%s），投递待对端唤醒。"
              % (level, outcomes[0][0] if outcomes else "?"))
        print("     ⇒ 这**不是**丢卡（与 `null`+queued 的解析失败不同）；可稍后用 --wait 复验。")
        return 3
    if status == "unroutable":'''
assert old2 in s, "unroutable 锚点未命中"
s = s.replace(old2, new2, 1)

# 自证补 3 例
old3 = '''    case("★ 对端日志 = null + queued（事故形态 ⇒ 必须判未送达）",'''
new3 = '''    case("★ target 已解析 + queued ⇒ **pending**（不是丢卡）",
         "[22:30:00] 📩 注入 mac-mini: %s → session-fa1f9150-c949 [central] queued" % K, K, "pending")
    case("★ target=null + queued ⇒ unroutable（**解析失败才是真丢**）",
         "[09:59:48] 📩 注入 mac-mini: %s → null [central] queued" % K, K, "unroutable")
    case("★ 对端日志 = null + queued（事故形态 ⇒ 必须判未送达）",'''
assert old3 in s, "自证锚点未命中"
s = s.replace(old3, new3, 1)

io.open(p, "w", encoding="utf-8").write(s)
print("✅ verify-delivery 已加 pending 档（已解析+queued ≠ 丢卡）")
