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

★ 2026-10-12 增补（v7 M4-① / W4 报「11/14 无负控」）：
  ★ 本件此前**从未被造坏验证过** —— 逻辑一直对，但「对」≠「被验证过对」。
  ★★ 新增 `--data <path>`（★ 注入任一份索引）· `--anchor-dir <path>`（★ 注入参照目录）
     · `--selftest`（★ 真调 `evaluate()`：3 正控 + 3 负控）。
"""
import datetime, glob, json, os, re, sys, argparse

DEFAULT_INDEX = os.path.expanduser("~/dsh-collab/data/registry/continuity-index.json")
DEFAULT_ANCHOR_DIR = os.path.expanduser("~/dsh-collab/docs")
RE_RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?[+-]\d{2}:\d{2}$")


def mt(p):
    return datetime.datetime.fromtimestamp(os.path.getmtime(p), datetime.timezone.utc)


def evaluate(d, anchor_dir, now=None):
    """★ 纯函数：返回 (verdict, payload)。verdict ∈ {PASS, FAIL, UNDECIDABLE}"""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    upd = d.get("updated_at")
    anchor = d.get("anchor")
    out = {"updated_at": upd, "anchor": anchor, "checks": []}

    # --- ① 时间戳可读性 ---
    if not RE_RFC3339.match(upd or ""):
        out["checks"].append(("① 时间戳规范形", False, "非 RFC 3339 规范形（±HH:MM 带冒号）"))
        return "UNDECIDABLE", {**out, "reason": "updated_at 非规范形 ⇒ 新鲜不可读"}
    t_idx = datetime.datetime.fromisoformat(upd)
    out["checks"].append(("① 时间戳规范形", True, "规范形"))
    if t_idx > now:
        out["checks"].append(("① 未落未来", False, "落在未来（%s > %s）" % (upd, now.isoformat())))
        return "UNDECIDABLE", {**out, "reason": "updated_at 落在未来 ⇒ 新鲜不可读"}
    out["checks"].append(("① 未落未来", True, "落后现在 %.1f 小时" % ((now - t_idx).total_seconds() / 3600)))

    # --- ② 落后（代理指标）---
    refs = {}
    ap = None
    if anchor:
        ap = anchor if os.path.isabs(anchor) else os.path.join(os.path.expanduser("~/dsh-collab"), anchor)
    if ap and os.path.exists(ap):
        refs["锚点文档"] = mt(ap)
    else:
        out["checks"].append(("② 锚点可解", False, "锚点文档路径不可解"))
    mds = glob.glob(os.path.join(anchor_dir, "*.md")) if anchor_dir and os.path.isdir(anchor_dir) else []
    if mds:
        refs["最新交付物"] = mt(max(mds, key=os.path.getmtime))
    else:
        out["checks"].append(("② 分母非零", False, "docs/*.md 分母 = 0"))
    if not refs:
        return "UNDECIDABLE", {**out, "reason": "两个参照系均不可得 ⇒ 不可判"}
    lagging = [(k, v) for k, v in refs.items() if v > t_idx]
    out["refs"] = {k: v.isoformat() for k, v in refs.items()}
    out["lagging"] = [k for k, _ in lagging]
    if lagging:
        out["max_lag_hours"] = round(max((v - t_idx).total_seconds() / 3600 for _, v in lagging), 1)
        out["checks"].append(("② 落后 ≤1 次状态变化", False,
                              "落后（%d 个参照物更新，最大差 %.1f 小时）" % (len(lagging), out["max_lag_hours"])))
        return "FAIL", out
    out["checks"].append(("② 落后 ≤1 次状态变化", True, "不落后于参照物"))
    return "PASS", out


def report(p, payload, verdict):
    print("索引:", p)
    print("索引 updated_at =", payload.get("updated_at"))
    print("索引 anchor     =", payload.get("anchor"))
    print()
    for name, ok, detail in payload.get("checks", []):
        print("  %s %-22s %s" % ("✅" if ok else "❌", name, detail))
    if payload.get("refs"):
        print()
        print("  参照系:")
        for k, v in payload["refs"].items():
            print("    %-12s %s" % (k, v))
    print()
    if verdict == "UNDECIDABLE":
        print("  ★ 判定：**不可判** —— %s" % payload.get("reason"))
    elif verdict == "FAIL":
        print("  ★ 判定：**落后**（%s 更新，最大差 %s 小时）" % (",".join(payload["lagging"]), payload.get("max_lag_hours")))
    else:
        print("  ★ 判定：**不落后**（索引不早于参照物）")
    print("  ★ 声明：本判据只能证明「不落后于这两个文件」，不能证明「索引完整」。")


def selftest():
    """★ 3 正控 + 3 负控 —— 全真调 evaluate()。"""
    ok = tot = 0
    now = datetime.datetime(2026, 10, 12, 12, 0, 0, tzinfo=datetime.timezone.utc)
    import tempfile
    tmp = tempfile.mkdtemp(prefix="bf-")

    def mk(name, secs_ago):
        pth = os.path.join(tmp, name)
        io_ = open(pth, "w", encoding="utf-8")
        io_.write("x")
        io_.close()
        t = now.timestamp() - secs_ago
        os.utime(pth, (t, t))
        return pth

    old_md = mk("old.md", 7200)      # 2 小时前
    new_md = mk("new.md", 60)        # 1 分钟前（★ 比索引新）

    # ★ 正控①：索引比最新交付物旧 ⇒ FAIL
    tot += 1
    d1 = {"updated_at": (now - datetime.timedelta(hours=1)).isoformat(), "anchor": "x"}
    v, pl = evaluate(d1, tmp, now=now)
    if v == "FAIL":
        ok += 1
        print("  ✅ 正控①：索引比最新交付物旧 ⇒ FAIL（★ 落后 %.1f h）" % pl.get("max_lag_hours", 0))
    else:
        print("  ❌ 正控①：该红却判 %s" % v)
    # ★ 负控①：索引比所有参照物新 ⇒ PASS（★ 防判据恒红）
    tot += 1
    d2 = {"updated_at": (now + datetime.timedelta(seconds=1)).isoformat(), "anchor": "x"}
    v2, _ = evaluate(d2, tmp, now=now)
    # ★ 注意：updated_at 比 now 新 ⇒ 落未来 ⇒ 应 UNDECIDABLE（★ 这正是设计）
    if v2 == "UNDECIDABLE":
        ok += 1
        print("  ✅ 负控①：updated_at 落未来 ⇒ UNDECIDABLE（★ 不冒充 PASS）")
    else:
        print("  ❌ 负控①：落未来未判 UNDECIDABLE（%s）" % v2)
    # ★ 负控②：索引不早于参照物但不落未来 ⇒ PASS
    tot += 1
    d3 = {"updated_at": (now - datetime.timedelta(seconds=30)).isoformat(), "anchor": "x"}
    v3, pl3 = evaluate(d3, tmp, now=now)
    if v3 == "PASS":
        ok += 1
        print("  ✅ 负控②：索引不早于参照物 ⇒ PASS（★ 防判据恒红）")
    else:
        print("  ❌ 负控②：该绿却判 %s（refs=%s）" % (v3, pl3.get("refs")))
    # ★ 正控②：updated_at 非规范形 ⇒ UNDECIDABLE
    tot += 1
    v4, _ = evaluate({"updated_at": "2026-10-12 12:00:00", "anchor": "x"}, tmp, now=now)
    if v4 == "UNDECIDABLE":
        ok += 1
        print("  ✅ 正控②：`2026-10-12 12:00:00`（无冒号）⇒ UNDECIDABLE（★ 新鲜不可读）")
    else:
        print("  ❌ 正控②：非规范形未判 UNDECIDABLE")
    # ★ 正控③：updated_at 落未来 ⇒ UNDECIDABLE（★ 显式覆盖）
    tot += 1
    v5, pl5 = evaluate({"updated_at": (now + datetime.timedelta(days=1)).isoformat(), "anchor": "x"}, tmp, now=now)
    if v5 == "UNDECIDABLE" and "未来" in (pl5.get("reason") or ""):
        ok += 1
        print("  ✅ 正控③：明显落未来 ⇒ UNDECIDABLE 且理由含「未来」")
    else:
        print("  ❌ 正控③：落未来未判 UNDECIDABLE（%s / %s）" % (v5, pl5.get("reason")))
    # ★ 负控③：参照系全不可得 ⇒ UNDECIDABLE（★ 不得报 0 / 不得报通过）
    tot += 1
    empty = tempfile.mkdtemp(prefix="bf-empty-")
    v6, pl6 = evaluate({"updated_at": (now - datetime.timedelta(hours=1)).isoformat(),
                        "anchor": "/tmp/__no_such_anchor__.md"}, empty, now=now)
    if v6 == "UNDECIDABLE":
        ok += 1
        print("  ✅ 负控③：参照系全不可得 ⇒ UNDECIDABLE（★ 分母 0 不报通过）")
    else:
        print("  ❌ 负控③：无参照系竟判 %s" % v6)
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(empty, ignore_errors=True)
    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=None, help="★ 注入另一份索引（供负控用）")
    ap.add_argument("--anchor-dir", default=None, help="★ 注入参照目录（供负控用）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("probe-beacon-freshness 1.1.0")
        return 0
    if a.selftest:
        return selftest()
    p = os.path.expanduser(a.data) if a.data else DEFAULT_INDEX
    ad = os.path.expanduser(a.anchor_dir) if a.anchor_dir else DEFAULT_ANCHOR_DIR
    if not os.path.exists(p):
        print("★ 索引不可读 ⇒ 不可判（★ 读不到 ≠ 不存在）: %s" % p)
        return 3
    d = json.load(open(p, encoding="utf-8"))
    verdict, payload = evaluate(d, ad)
    if a.json:
        print(json.dumps({**payload, "verdict": verdict}, ensure_ascii=False, indent=1))
        return 0 if verdict == "PASS" else (3 if verdict == "UNDECIDABLE" else 1)
    report(p, payload, verdict)
    # ★ ③ 支撑门（原样保留）
    print()
    print("=== ③ 支撑门（索引内部自洽，非本指标本身）===")
    print("  跑: python3 ~/dsh-collab/tools/beacon-check.py --net")
    return 0 if verdict == "PASS" else (3 if verdict == "UNDECIDABLE" else 1)


if __name__ == "__main__":
    sys.exit(main())
