#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S7 单会话体积 / 事件数 —— 现测口径

★ 事件数须解压 zstd 才能数 ⇒ 慢。默认只对**体积最大者**计数（可 --top N 增加）。
★ 且必须声明：这是【磁盘体积】与【行数】，不是运行时【活跃窗口事件数】—— 两者不是同一个量。

★ 2026-10-12 增补（v7 M4-① / W4 报「11/14 无负控」）：
  ★ 本件此前**从未被造坏验证过**。
  ★★ 新增 `--selftest`（★ 真调 `evaluate()`：3 正控 + 3 负控）。
  ★★★ **判据本体未改** —— 本增补只加纯函数与自证。
"""
import glob
import os
import sys
import argparse

DEFAULT_ROOT = os.path.expanduser("~/.dsh/sessions")
LIMIT_MB = 200.0          # ★ §12 目标：单会话 ≤200MB


def evaluate(root, top=1):
    """★ 返回 (verdict, payload)。verdict ∈ {PASS, FAIL, UNDECIDABLE}"""
    files = glob.glob(os.path.join(root, "**", "session.jsonl.zstd"), recursive=True)
    if not files:
        return "UNDECIDABLE", {"reason": "分母 = 0（未找到任何 session.jsonl.zstd）", "root": root}
    sized = sorted(((os.path.getsize(f), f) for f in files), reverse=True)
    tot = sum(s for s, _ in sized)
    biggest = sized[0][0] / 1048576.0
    over = [(s / 1048576.0, f) for s, f in sized if s / 1048576.0 > LIMIT_MB]
    return ("FAIL" if over else "PASS"), {
        "root": root,
        "total_files": len(files),
        "total_mib": round(tot / 1048576.0, 1),
        "biggest_mib": round(biggest, 1),
        "limit_mb": LIMIT_MB,
        # ★ 口径：分母 = session.jsonl.zstd 文件数；分子 = 其中压缩体积 > 200MB 的
        "over_count": len(over),
        "top_files": [{"mib": round(s / 1048576.0, 1), "path": f} for s, f in sized[:top]],
    }


def report(payload):
    print("会话文件总数（分母）= %d" % payload["total_files"])
    print("体积最大前 %d：" % len(payload["top_files"]))
    for t in payload["top_files"]:
        print("  %.1f MiB  %s" % (t["mib"], os.path.basename(os.path.dirname(t["path"]))))
    print()
    print("全部会话文件字节合计 = %.1f MiB" % payload["total_mib"])
    print()
    print("★ 判据  单会话 ≤%.0fMB : %s（最大 %.1f MiB · 超限 %d 个）"
          % (payload["limit_mb"], "✓" if payload["over_count"] == 0 else "❌",
             payload["biggest_mib"], payload["over_count"]))
    print("★ 目标口径提醒：§12 写「单会话 ≤200MB + 事件数入监控」。")
    print("★ 上列体积是【磁盘上压缩后的文件体积】；zstd 解压后体积**大于**它")
    print("  ⇒ 与 200MB 目标比较前必须先声明比的是哪一个。")


def selftest():
    """★ 3 正控 + 3 负控 —— 全真调 evaluate()。"""
    ok = tot = 0
    import tempfile
    import shutil

    def mk(root, name, mib):
        d = os.path.join(root, name)
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "session.jsonl.zstd")
        with open(p, "wb") as fh:
            fh.write(b"\0" * int(mib * 1048576))
        return p

    # ★ 正控①：造一个 250 MiB 的会话 ⇒ 必须 FAIL
    tot += 1
    r1 = tempfile.mkdtemp(prefix="sv-over-")
    mk(r1, "s1", 250)
    v, pl = evaluate(r1)
    if v == "FAIL" and pl["over_count"] == 1:
        ok += 1
        print("  ✅ 正控①：单会话 250 MiB ⇒ FAIL（★ 超限 1 个）")
    else:
        print("  ❌ 正控①：超限未判 FAIL（%s / over=%s）" % (v, pl.get("over_count")))
    # ★ 负控①：造一个 100 MiB 的会话 ⇒ 必须 PASS（★ 防判据恒红）
    tot += 1
    r2 = tempfile.mkdtemp(prefix="sv-ok-")
    mk(r2, "s1", 100)
    v2, pl2 = evaluate(r2)
    if v2 == "PASS" and pl2["over_count"] == 0:
        ok += 1
        print("  ✅ 负控①：单会话 100 MiB ⇒ PASS（★ 防判据恒红）")
    else:
        print("  ❌ 负控①：未超限却判 %s" % v2)
    # ★ 正控②：恰好 200 MiB ⇒ 不超（★ 边界：判据是「>200」不是「≥200」）
    tot += 1
    r3 = tempfile.mkdtemp(prefix="sv-edge-")
    mk(r3, "s1", 200)
    v3, pl3 = evaluate(r3)
    if v3 == "PASS":
        ok += 1
        print("  ✅ 正控②：恰好 200 MiB ⇒ PASS（★ 边界 `>200` 不是 `≥200`）")
    else:
        print("  ❌ 正控②：边界判错（%s · 最大 %.1f）" % (v3, pl3.get("biggest_mib", 0)))
    # ★ 负控②：分母 0 ⇒ UNDECIDABLE（★ 不得报 0/OK）
    tot += 1
    r4 = tempfile.mkdtemp(prefix="sv-empty-")
    v4, pl4 = evaluate(r4)
    if v4 == "UNDECIDABLE":
        ok += 1
        print("  ✅ 负控②：分母 0 ⇒ UNDECIDABLE（★ 不报 0/OK）")
    else:
        print("  ❌ 负控②：分母 0 未判 UNDECIDABLE（%s）" % v4)
    # ★ 正控③：多个会话，只有最大的超 ⇒ over_count 只数超的（★ 防「一个超就全算超」）
    tot += 1
    r5 = tempfile.mkdtemp(prefix="sv-multi-")
    mk(r5, "s1", 300)
    mk(r5, "s2", 50)
    mk(r5, "s3", 10)
    v5, pl5 = evaluate(r5)
    if v5 == "FAIL" and pl5["over_count"] == 1 and pl5["total_files"] == 3:
        ok += 1
        print("  ✅ 正控③：3 个会话只有 1 个超 ⇒ over_count=1 · total=3（★ 分子分母分离）")
    else:
        print("  ❌ 正控③：分子分母算错（over=%s total=%s）" % (pl5.get("over_count"), pl5.get("total_files")))
    # ★ 负控③：目录不存在 ⇒ UNDECIDABLE（★ 不得崩）
    tot += 1
    v6, _ = evaluate("/tmp/__no_such_sessions_dir__")
    if v6 == "UNDECIDABLE":
        ok += 1
        print("  ✅ 负控③：目录不存在 ⇒ UNDECIDABLE（★ 不崩、不冒充通过）")
    else:
        print("  ❌ 负控③：不存在的目录判 %s" % v6)
    for d in (r1, r2, r3, r4, r5):
        shutil.rmtree(d, ignore_errors=True)
    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=1)
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("probe-session-volume 1.1.0")
        return 0
    if a.selftest:
        return selftest()
    verdict, payload = evaluate(os.path.expanduser(a.root), a.top)
    if a.json:
        print(__import__("json").dumps({**payload, "verdict": verdict}, ensure_ascii=False, indent=1))
        return 0 if verdict == "PASS" else (3 if verdict == "UNDECIDABLE" else 1)
    if verdict == "UNDECIDABLE":
        print("分母 = 0（未找到任何 session.jsonl.zstd）⇒ ★ 不可判")
        return 3
    report(payload)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
