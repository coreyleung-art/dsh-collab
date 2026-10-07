#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch-publish-and-point-tri-state.py —— 双板写入的**三态报告**（ok / degraded / failed）

【缺陷】（2026-10-03 22:02 实测，mac-mini Tailscale 掉线期间）
  `publish-and-point` 的逐板回读断言只有 True/False：
    · 板**可达但内容不对** ⇒ False（真失败）
    · 板**不可达（超时/拒连）** ⇒ 也 False
  ⇒ 两者被混为一谈。实测：本机板（mac-mini 的板）超时，而**卡确实已写进中枢**
    ⇒ 我却只能报 `ok=False`，看不出"其实写成功了 1/2 板"。
  ★ 与今天反复打的同一类：**"没观测到" 与 "确实失败" 必须分开**（R31/R035 家族）。

【修法】三态 + 明确语义：
  · `ok`       ：**所有**板回读通过（双板写成立，R036 不变量满足）
  · `degraded` ：**至少一块可达且通过**，但有板**不可达** ⇒ 已降级为单板写入，
                 **送达未验证**（不冒充成功）；指针仍发（若总线可用）
  · `failed`   ：没有一块板确认写入，**或**有板可达但内容不符 ⇒ 不发送指针
  报告里区分 `readback`（约定俗成：True/False 保持向后兼容）与新增 `boards` 明细。
"""
import io
import os

p = os.path.expanduser("~/dsh-collab/tools/publish-and-point.py")
s = io.open(p, encoding="utf-8").read()

old = '''    # 2) 逐板回读断言（R036：不是保险，是必要条件）
    ok_boards = []
    for tag, base, h in BOARDS:
        try:
            r = urllib.request.Request(base + "/" + key, headers=h)
            d = json.load(urllib.request.urlopen(r, timeout=12))
            ok_boards.append((tag, d.get("key") == key))
        except Exception:
            ok_boards.append((tag, False))
    all_ok = all(o for _, o in ok_boards)
    if not all_ok:
        return False, key, {"write": wrote, "readback": ok_boards,
                            "note": "回读断言失败 ⇒ **不发提示**（避免造出指向空内容的指针）"}'''
new = '''    # 2) 逐板回读断言（R036：不是保险，是必要条件）
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
    all_ok = (n_unreach == 0 and n_mismatch == 0)'''
assert old in s, "回读锚点未命中"
s = s.replace(old, new, 1)

# 返回体里带上 verdict/boards
old2 = '''    return True, key, {"write": wrote, "readback": ok_boards, "pointer": text,
                       "sent": sent, "warnings": warnings, "delivery": delivery}'''
new2 = '''    return True, key, {"write": wrote, "readback": ok_boards, "pointer": text,
                       "sent": sent, "warnings": warnings, "delivery": delivery,
                       "boards": detail, "verdict": _verdict}'''
assert old2 in s, "返回锚点未命中"
s = s.replace(old2, new2, 1)

io.open(p, "w", encoding="utf-8").write(s)
print("✅ 已改为三态：ok / degraded / failed（不可达 ≠ 没写进去）")
