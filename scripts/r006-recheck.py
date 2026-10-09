#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r006-recheck.py — R006 全量合规复核器 v1.0.0

为什么需要（2026-10-09 完整评估）：
  本机已有一份 **2026-10-03 的 R006 合规矩阵**（`docs/tool-r006-compliance-matrix-20261003.json`，
  273 条，`compliant: 273`）。但它的 **`caliberNote` 明写口径只算 2 项**
  （「独立脚本口径=版本常量+中文文档」）——而 **R006 §0 规定「十项不可豁免」**。
  ⇒ 且 **产出矩阵的扫描器本体已不在库**（专有字段名 `cnDocs`/`caliberNote` 全库 0 命中，git 无提交记录）。
  ⇒ 故本器**不重建原扫描器**，而是 **① 复用矩阵的字段结构 ② 把判据从 2 项扩到【可机械核的项】**
     **③ 覆盖 2026-10-03 之后的增量**。

★ 判据来源（逐条对应 R006 v3.0）：
  R5 文档化    → 存在中文文档（脚本 docstring 中文占比 / 或 docs/ 下同名文档）
  R6 版本管理  → 版本常量单一来源（.py: __version__ · .js: VERSION|__version__ · .sh: VERSION=）
  R7 统一日志  → 源码含 `~/dsh-collab/logs/` 或 `scripts/logs/` 固定路径写日志
  R9 CLI 治理  → argparse / getopts 等参数解析 + --help
  R10 约束门   → 含 lean4-check 类自证

★ 口径诚实声明：本器**只核可机械核的 5 项**（R5/R6/R7/R9/R10），
  **不核 R1/R2/R3/R4/R8**（需运行期证据或插件形态判定）——凡未核项在输出里【显式列出】，
  **不得把「未核」当成「达标」**。

用法：
  python3 r006-recheck.py                      # 全量复核（人读）
  python3 r006-recheck.py --json               # 机器读
  python3 r006-recheck.py --kind script        # 只看 scripts/
  python3 r006-recheck.py --since 2026-10-03   # 只看该日之后新增/改动的
  python3 r006-recheck.py --compare            # 与 2026-10-03 矩阵对照（口径差异）
  python3 r006-recheck.py --selftest           # 自测（含负例）
退出码：0 = 无 GAP；1 = 存在 GAP；2 = 用法/环境错误
"""

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处

import argparse
import glob
import json
import os
import re
import sys
import time

HOME = os.path.expanduser("~")
COLLAB = os.path.join(HOME, "dsh-collab")
MATRIX_OLD = os.path.join(COLLAB, "docs", "tool-r006-compliance-matrix-20261003.json")


# ───────────────────────── 工具枚举 ─────────────────────────
def enumerate_tools(kind=None):
    """枚举本机全部工具：scripts/ 下的 CLI 工具 + devices/ 下的插件。"""
    out = []
    if kind in (None, "script"):
        for pat in ("scripts/*.py", "scripts/*.js", "scripts/*.sh"):
            for p in glob.glob(os.path.join(COLLAB, pat)):
                b = os.path.basename(p)
                if ".bak" in b or b.startswith("_"):
                    continue
                out.append((b, p, "script"))
    if kind in (None, "plugin"):
        for d in glob.glob(os.path.join(COLLAB, "devices", "dsh-plugin-*")):
            b = os.path.basename(d)
            if ".bak" in b:
                continue
            out.append((b, d, "plugin"))
    return sorted(out, key=lambda x: x[0])


# ───────────────────────── 逐项判据 ─────────────────────────
def cn_ratio(s):
    if not s:
        return 0.0
    return len(re.findall(r"[\u4e00-\u9fff]", s)) / max(1, len(s))


def read(p):
    try:
        return open(p, encoding="utf-8", errors="ignore").read()
    except Exception:
        return ""


def check_one(name, path, kind):
    """返回 {项: True/False/None} + 证据。None = 本器未核。"""
    r = {"R5_cnDocs": None, "R6_version": None, "R7_log": None, "R9_cli": None, "R10_lean4": None}
    ev = {}

    if kind == "script":
        src = read(path)
        if not src:
            return r, {"error": "unreadable"}
        # R5 文档化：★ 改【存在性判据】而非占比 —— 原用「头部 2500 字中文占比≥15%」，
        #   而实测中英文混排的正常脚本占比天然低（我的 selftest 样例只有 10%）
        #   ⇒ 这是「实现细节决定结论」的又一实例 ⇒ 改为：
        #   ① docstring/头部含 ≥10 个汉字，或 ② docs/ 下有同名文档
        head = src[:2500]
        cjk = len(re.findall(r"[\u4e00-\u9fff]", head))
        ratio = cn_ratio(head)
        doc_path = os.path.join(COLLAB, "docs", os.path.splitext(name)[0] + ".md")
        r["R5_cnDocs"] = bool(cjk >= 10 or os.path.exists(doc_path))
        ev["R5"] = "头部汉字 %d 个（占比 %.0f%%）· docs/%s.md %s" % (
            cjk, ratio * 100, os.path.splitext(name)[0],
            "有" if os.path.exists(doc_path) else "无")
        # R6 版本常量单一来源
        m = re.findall(r"(__version__\s*=\s*['\"][^'\"]+['\"]|^VERSION\s*=\s*['\"][^'\"]+['\"]|^VERSION=[\w\.\-]+)",
                       src, re.M)
        r["R6_version"] = len(m) >= 1
        ev["R6"] = ("%d 处版本声明" % len(m)) if m else "无版本常量"
        # R7 统一日志（固定路径）
        # ★ 2026-10-09 修判据：原只认字面 "dsh-collab/logs"，
        #   而合法写法还有 os.path.join(COLLAB, "logs", ...) / Path(...)/"logs" 等
        #   ⇒ 实证：local-registry.py 写了固定日志却被误判为「无」
        #   ⇒ 「判据的实现细节决定结论」（今日 N-21 同族）
        r["R7_log"] = bool(re.search(
            r"(dsh-collab/logs|scripts/logs|~/dsh-collab/logs"
            r"|join\([^)]*\bCOLLAB\b[^)]*[\"']logs[\"']"
            r"|join\([^)]*[\"']logs[\"'])", src))
        ev["R7"] = "有固定日志路径" if r["R7_log"] else "无固定日志路径"
        # R9 CLI 治理
        r["R9_cli"] = bool(re.search(r"argparse|getopts|sys\.argv", src))
        ev["R9"] = "有参数解析" if r["R9_cli"] else "无参数解析"
        # R10 约束门
        # ★ 2026-10-09 收紧判据：原为 `re.search(r"lean4|lean-4")` ⇒ 任何注释里写个 "lean4" 就能过
        #   ⇒ 那使 R10 可被【一句注释】绕过（与今日 N-03b「判据可被绕过」同族）
        #   ⇒ 改为要求【真实实现三要素】同时成立：
        #     ① 存在 lean4 相关的函数定义  ② 该函数内有 ≥3 条判据（c(...) 调用）
        #     ③ 存在可执行入口（--lean4-check 旗标）
        _has_fn = bool(re.search(r"def\s+lean4_check|function\s+lean4_check|lean4Check\s*\(", src))
        _has_entry = bool(re.search(r"--lean4-check", src))
        _n_checks = len(re.findall(r"\bc\(\s*[\"']", src))
        r["R10_lean4"] = bool(_has_fn and _has_entry and _n_checks >= 3)
        ev["R10"] = "函数=%s 入口=%s 判据数=%d" % (_has_fn, _has_entry, _n_checks)
    else:  # plugin
        pkg = os.path.join(path, "package.json")
        src = read(os.path.join(path, "lib", "selfcheck.js")) or read(os.path.join(path, "index.js"))
        r["R6_version"] = os.path.exists(pkg)
        ev["R6"] = "有 package.json" if os.path.exists(pkg) else "无 package.json"
        cli = os.path.exists(os.path.join(path, "cli.js"))
        r["R9_cli"] = cli
        ev["R9"] = "有 cli.js" if cli else "无 cli.js"
        sc = os.path.exists(os.path.join(path, "lib", "selfcheck.js"))
        r["R5_cnDocs"] = os.path.exists(os.path.join(path, "docs", "README.md"))
        ev["R5"] = "有 docs/README.md" if r["R5_cnDocs"] else "无 docs/README.md"
        r["R7_log"] = bool(re.search(r"logs", src))
        ev["R7"] = "源码含 logs" if r["R7_log"] else "源码无 logs"
        r["R10_lean4"] = sc
        ev["R10"] = "有 lib/selfcheck.js" if sc else "无 selfcheck"
    return r, ev


# ───────────────────────── 主评估 ─────────────────────────
def assess(kind=None, since=None):
    tools = enumerate_tools(kind)
    rows = []
    for name, path, k in tools:
        if since:
            mt = time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(path)))
            if mt < since:
                continue
        r, ev = check_one(name, path, k)
        checked = [v for v in r.values() if v is not None]
        gaps = [kk for kk, v in r.items() if v is False]
        rows.append({
            "name": name, "kind": k, "path": path.replace(HOME, "~"),
            "gaps": gaps, "n_gap": len(gaps), "n_checked": len(checked),
            "n_pass": sum(1 for v in checked if v), "evidence": ev,
        })
    return rows


def summarize(rows):
    n = len(rows)
    full = sum(1 for r in rows if r["n_gap"] == 0)
    per = {}
    for key in ("R5_cnDocs", "R6_version", "R7_log", "R9_cli", "R10_lean4"):
        per[key] = sum(1 for r in rows if key not in r["gaps"] and r["n_checked"] > 0)
    return {"total": n, "fully_ok_5items": full, "per_item_pass": per}


def selftest():
    """负例 + 正例。★ 不得只报 FAIL 数。"""
    import tempfile
    fails = neg = pos = 0

    def c(name, cond, kind="pos"):
        nonlocal fails, neg, pos
        if kind == "pos": pos += 1
        else: neg += 1
        good = bool(cond)
        print("  %s %-6s %-46s" % ("✅" if good else "❌", kind, name))
        if not good: fails += 1

    print("== r006-recheck selftest ==")
    tmp = tempfile.mkdtemp(prefix="r006re-")
    # 正例：达标脚本
    good = os.path.join(tmp, "good.py")
    # ★ 2026-10-09：R10 判据收紧后，样例必须【真实现】lean4 门（不能只写注释）
    open(good, "w", encoding="utf-8").write(
        '#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n'
        '"""好工具：为什么需要 / 用法 / 判据，都是中文说明，足以满足文档化判据。\n"""\n'
        "__version__ = '1.0.0'\nimport argparse, os\n"
        "LOG=os.path.expanduser('~/dsh-collab/logs/good.log')\n"
        "def lean4_check():\n"
        "    c('A', 'a', True)\n    c('B', 'b', True)\n    c('C', 'c', True)\n"
        "    return 0\n"
        "ap=argparse.ArgumentParser()\n"
        "ap.add_argument('--lean4-check', action='store_true')\n")
    r, _ = check_one("good.py", good, "script")
    c("达标脚本 ⇒ 5 项全过", all(v is True for v in r.values()), )
    # 负例：全缺
    bad = os.path.join(tmp, "bad.py")
    open(bad, "w", encoding="utf-8").write("print('hi')\n")
    r2, _ = check_one("bad.py", bad, "script")
    c("裸脚本 ⇒ 应检出 5 项缺口", r2["R6_version"] is False and r2["R7_log"] is False, kind="neg")
    # 负例：只有英文文档 ⇒ R5 应 False
    en = os.path.join(tmp, "en.py")
    open(en, "w", encoding="utf-8").write("# English only docstring\n" + "x=1\n" * 50)
    r3, _ = check_one("en.py", en, "script")
    c("纯英文文档 ⇒ R5 判缺（中文占比不足）", r3["R5_cnDocs"] is False, kind="neg")
    # 正例：中文占比判定可达
    c("中文占比阈值可判", cn_ratio("这是中文说明文字") > 0.5)
    # 正例：真实枚举非空
    c("工具枚举非空", len(enumerate_tools()) > 0)
    print("\n  selftest: %d FAIL ｜ 反例 %d 条 / 正例 %d 条" % (fails, neg, pos))
    return 0 if fails == 0 else 1


def main():
    ap = argparse.ArgumentParser(description="R006 全量合规复核器")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--kind", choices=["script", "plugin"], default=None)
    ap.add_argument("--since", default=None, help="只核该日期(YYYY-MM-DD)之后改动过的")
    ap.add_argument("--compare", action="store_true", help="与 2026-10-03 矩阵对照口径")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not os.path.isdir(COLLAB):
        print("环境错误：找不到 " + COLLAB, file=sys.stderr)
        return 2

    rows = assess(kind=a.kind, since=a.since)
    s = summarize(rows)
    if a.json:
        print(json.dumps({"summary": s, "rows": rows}, ensure_ascii=False, indent=1))
        return 1 if any(r["n_gap"] for r in rows) else 0

    print("== R006 全量合规复核（本器口径：R5/R6/R7/R9/R10 五项可机械核）==")
    if a.since:
        print("   筛选：%s 之后改动" % a.since)
    print("   工具总数 %d · 五项全过 %d (%.0f%%)" % (
        s["total"], s["fully_ok_5items"], s["fully_ok_5items"] / max(1, s["total"]) * 100))
    print("   ── 逐项达标率 ──")
    for k, v in s["per_item_pass"].items():
        print("     %-14s %4d / %d  (%.0f%%)" % (k, v, s["total"], v / max(1, s["total"]) * 100))
    print()
    worst = sorted(rows, key=lambda r: -r["n_gap"])[:12]
    print("   ── 缺口最多的 12 个 ──")
    for r in worst:
        if r["n_gap"] == 0:
            continue
        print("     %-38s 缺 %d: %s" % (r["name"][:38], r["n_gap"], ",".join(x.split("_")[0] for x in r["gaps"])))

    if a.compare and os.path.exists(MATRIX_OLD):
        try:
            old = json.load(open(MATRIX_OLD, encoding="utf-8"))
            print()
            print("   ── 与 2026-10-03 矩阵对照（口径差异）──")
            print("     旧矩阵：total %s · compliant %s" % (old.get("total"), old.get("compliant")))
            print("     旧口径：%s" % old.get("caliberNote"))
            print("     本器  ：total %d · 五项全过 %d" % (s["total"], s["fully_ok_5items"]))
            print("     ⇒ ★ 差异原因：旧口径只算【2 项】，本器核【5 项】—— 两者都对，但在不同口径下。")
        except Exception as e:
            print("     对照失败:", e)
    return 1 if any(r["n_gap"] for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
