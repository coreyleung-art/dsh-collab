#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S1 信标新鲜度 —— 现测口径

§12 目标原文：「落后 ≤1 次状态变化，启动即校验」
§12 现状原文：「落后 ≥1 次状态变化 · 且 updated_at 落在未来使「新鲜」不可读」

★★ 为什么不能只跑 `beacon-check --net`：
   它读的是**索引内部的自洽**（waves/items、时间戳形制、板值一致）。
   而「落后」是**索引与外部交付物之间**的关系 —— 索引自己不可能发现自己落后。
   ⇒ 必须**另取一个参照系**（锚点文档 mtime / 最新交付物 mtime）才有判别力。

★★ 「落后 ≥1 次状态变化」的可机器判形态（本文件采用的口径，可替换）：
   设 T_index = 索引 updated_at，T_anchor = 锚点文档 mtime，
      T_newest = docs/ 下最新 .md 的 mtime。
   落后 = (T_anchor > T_index) 或 (T_newest > T_index)。
   ★ 这是**下界代理**：它只能判「索引比某个文件旧」，判不了「索引漏了 N 次状态变化」。
     本文件如实标为【代理指标】，不冒充原判据。
"""
import datetime, glob, json, os, re

INDEX = os.path.expanduser("~/dsh-collab/data/registry/continuity-index.json")
ANCHOR_DIR = os.path.expanduser("~/dsh-collab/docs")

d = json.load(open(INDEX, encoding="utf-8"))
upd = d.get("updated_at")
anchor = d.get("anchor")
print("索引:", INDEX)
print("索引 updated_at =", upd)
print("索引 anchor     =", anchor)

now = datetime.datetime.now(datetime.timezone.utc)

# --- ① RFC 3339 规范形 + 不落在未来 ---
print()
print("=== ① 时间戳可读性 ===")
if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?[+-]\d{2}:\d{2}$", upd or ""):
    print("  ❌ updated_at 非 RFC 3339 规范形（±HH:MM 带冒号）⇒ ★「新鲜」不可读")
    t_idx = None
else:
    t_idx = datetime.datetime.fromisoformat(upd)
    print("  ✅ 规范形")
if t_idx:
    if t_idx > now:
        print("  ❌ updated_at 落在未来（%s > %s）⇒ ★「新鲜」不可读" % (upd, now.isoformat()))
    else:
        print("  ✅ 未落在未来（落后现在 %.1f 小时）" % ((now - t_idx).total_seconds() / 3600))

# --- ② 落后判据（代理）---
print()
print("=== ② 落后 ≤1 次状态变化（★ 代理指标）===")
def mt(p):
    return datetime.datetime.fromtimestamp(os.path.getmtime(p), datetime.timezone.utc)

ap = os.path.join(os.path.expanduser("~/dsh-collab"), anchor) if anchor else None
if ap and os.path.exists(ap):
    t_a = mt(ap)
    print("  锚点文档 %s mtime = %s" % (os.path.basename(ap), t_a.isoformat()))
    print("  锚点 mtime %s 索引 updated_at" % ("晚于" if t_a > t_idx else "不晚于"))
else:
    t_a = None
    print("  ❌ 锚点文档路径不可解 ⇒ ★ 不可判")

mds = glob.glob(os.path.join(ANCHOR_DIR, "*.md"))
if mds:
    newest = max(mds, key=os.path.getmtime)
    t_n = mt(newest)
    print("  docs 下最新 .md = %s mtime = %s" % (os.path.basename(newest), t_n.isoformat()))
    print("  最新交付物 mtime %s 索引 updated_at" % ("晚于" if t_n > t_idx else "不晚于"))
else:
    t_n = None
    print("  ❌ docs/*.md 分母 = 0 ⇒ ★ 不可判")

lagging = [x for x in (t_a, t_n) if x and x > t_idx]
print()
if lagging:
    print("  ★ 判定：落后（索引比 %d 个参照物旧，最大差 %.1f 小时）"
          % (len(lagging), max((x - t_idx).total_seconds() / 3600 for x in lagging)))
else:
    print("  ★ 判定：**不落后**（索引不早于两个参照物）")
print("  ★ 声明：本判据只能证明「不落后于这两个文件」，不能证明「索引完整」。")

print()
print("=== ③ 支撑门（索引内部自洽，非本指标本身）===")
print("  跑: python3 ~/dsh-collab/tools/beacon-check.py --net")
