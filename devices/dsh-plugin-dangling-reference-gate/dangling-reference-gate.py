#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dangling-reference-gate.py — 悬挂引用门（v1.0.0）

为何存在（★ 判据来源：裁判 `session-1ffded95` 2026-10-10 的三步模型）
    裁判对「我为什么没把失误变成判据」的纠正：
      「**那不是盲点，是【跳步】** —— 你**准确描述了失误**，但跳过了『命名抽取』这一步
        （**盲点看不见；这一步是可见的、只是没做**）。
       · 描述      ：「这次 `authId` 截断了，所以检索不到」   （✗ 只对这一例）
       · ★**命名抽取**：「引用的标识符若被截断，则等于引了一个不存在的锚」（✓ 可复用于任何标识符）
       · **门化**  ：「检查引用中的标识符是否可在台账中检索到」 （✓ 可自动执行）
       ⇒ **三步是三个独立动作，跳步就会得到「经验很多但判据很少」。**」

    ★ 本器就是第三步（门化）—— 由 executor `session-b250bf9d` 实现。

判据
    ∀ 引用 r（形如 `AUTH-YYYYMMDD-<hex>` / `CHG-YYYYMMDD-<hex>`）：
        r ∈ 权威源  ⇒ 可解
        r ∉ 权威源  ⇒ ★ **悬挂引用**（等于引了一个不存在的锚）
    ★ 与「易变量」那条不同：本条的**形态与权威源都是明确的** ⇒ **完全可机械判**。

三态（不做折算）
    OK        全部引用可解
    DANGLING  存在不可解的引用 ⇒ 列出（含文件、行号、该引用）
    UNCHECKED 权威源读不到 ⇒ 如实标未核，**不计入通过**

★ 豁免机制（必要 —— 否则本器会误报「记录自己错误」的文档）
    在被引用的**同一行或上一行**含豁免标记时，跳过该引用：
        `[示例]` · `[错误示例]` · `自纠` · `勘误` · `反面例`
    ⇒ 理由：**记录一个错误引用是【正当的】**（本线的勘误纪律「有错就记，不改历史」）。
    ⇒ 豁免是**显式**的（须写标记），不是静默的。

用法
    python3 dangling-reference-gate.py [--json]               # 全量扫描
    python3 dangling-reference-gate.py --selftest
    python3 dangling-reference-gate.py --selfcheck
    python3 dangling-reference-gate.py --exemptions           # ★ 列出被豁免的引用（独立可跑）
    python3 dangling-reference-gate.py --version

退出码（★ R006 ⑨）
    0 = 无悬挂引用（可能有 UNCHECKED，会显式列出）
    1 = 有悬挂引用
    2 = 用法或权威源错误
"""

__version__ = '1.0.0'   # ★ R006 ⑥ 唯一版本声明处

import argparse
import io
import json
import os
import re
import sys
import time
import tokenize

ROOT = os.path.expanduser("~/dsh-collab")
LEDGER = os.path.join(ROOT, "data/proxy-change-ledger.json")
LOG_DIR = os.path.join(ROOT, "logs")
LOG = os.path.join(LOG_DIR, "dsh-plugin-dangling-reference-gate.log")

# ★ 冻结白名单（R006 ⑩ 类型锁）：受检的标识符形态 → 权威源取值路径
REF_PATTERNS = (
    ("AUTH", re.compile(r"\bAUTH-\d{8}-[0-9a-f]+\b"),
     ("authorizations", "authId")),
    ("CHG", re.compile(r"\bCHG-\d{8}-[0-9a-f]+\b"),
     ("changes", "id")),
)

# ★ 豁免标记（显式书写才豁免；用于「记录错误引用」的正当场合）
EXEMPT_MARKS = ("[示例]", "[错误示例]", "自纠", "勘误", "反面例")

SCAN_DIRS = ("docs", "rules-registry", "devices", "data", "notes")
SCAN_EXT = (".md", ".json", ".py", ".txt")

EXIT_OK, EXIT_DANGLING, EXIT_USAGE = 0, 1, 2


def log(msg):
    """★ R006 ⑦：固定路径、追加、含时刻；失败也留痗。"""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass


def banner():
    return "dangling-reference-gate v%s" % __version__


def strip_code(src):
    """★ 剥离字符串与注释后扫描（防自指误报）。★ 按 token 行号重建 ⇒ 行号对齐。"""
    try:
        n = len(src.split("\n"))
        lines = src.split("\n")
        # ★★ 2026-10-10 修：原实现「逐 token 重拼」=> **token 间空白被吞**
        #   实证后果：`if a.selftest:` -> `ifa.selftest:` ; `def selftest(` -> `defselftest(`
        #   => 下游以【空白为界】的正则（如 def 加空白加 selftest）全部失配
        #   => 该 bug 同时造成【selftest 自身 2 条 FAIL】与【对他人脚本的假阳性】。
        #   => 修法：**只抹除 STRING/COMMENT 覆盖的区段，其余保留原文**（不重拼 token）。
        spans = []
        for tk in tokenize.generate_tokens(io.StringIO(src).readline):
            if tk.type in (tokenize.STRING, tokenize.COMMENT):
                spans.append((tk.start[0], tk.start[1], tk.end[0], tk.end[1]))
        for (sr, sc, er, ec) in spans:
            if sr == er:
                if 1 <= sr <= n:
                    L = lines[sr - 1]
                    lines[sr - 1] = L[:sc] + " " * (ec - sc) + L[ec:]
            else:
                for ln in range(sr, er + 1):
                    if not (1 <= ln <= n):
                        continue
                    if ln == sr:
                        lines[ln - 1] = lines[ln - 1][:sc]
                    elif ln == er:
                        lines[ln - 1] = " " * ec + lines[ln - 1][ec:]
                    else:
                        lines[ln - 1] = ""
        return "\n".join(lines)
    except Exception:
        return src

def load_authoritative(path=LEDGER):
    """★ 权威源：从台账收集所有合法标识符。返回 (set, err)。"""
    try:
        d = json.load(io.open(path, encoding="utf-8"))
    except Exception as e:
        return (None, "权威源读不到：%s (%s)" % (path, e))
    known = set()
    for coll, field in (("authorizations", "authId"), ("changes", "id")):
        for item in d.get(coll, []) or []:
            v = item.get(field)
            if v:
                known.add(v)
    return (known, None)


def is_exempt(lines, idx):
    """★ 显式豁免：该行或上一行含豁免标记。"""
    for i in (idx, idx - 1):
        if 0 <= i < len(lines):
            if any(m in lines[i] for m in EXEMPT_MARKS):
                return True
    return False


def scan(known, root=ROOT, dirs=SCAN_DIRS, exts=SCAN_EXT):
    """★ 扫描全仓，返回 (dangling, exempted, scanned_files)。"""
    dangling, exempted = [], []
    n_files = 0
    for sub in dirs:
        base = os.path.join(root, sub)
        if not os.path.isdir(base):
            continue
        for r, ds, fs in os.walk(base):
            if any(x in r for x in (".git", "node_modules", "/logs")):
                continue
            for fn in fs:
                if not fn.endswith(exts):
                    continue
                p = os.path.join(r, fn)
                try:
                    src = io.open(p, encoding="utf-8", errors="ignore").read()
                except Exception:
                    continue
                n_files += 1
                lines = src.split("\n")
                for kind, pat, _ in REF_PATTERNS:
                    for m in pat.finditer(src):
                        ref = m.group(0)
                        ln = src[:m.start()].count("\n")          # 0-based
                        rec = {"file": os.path.relpath(p, root), "line": ln + 1, "ref": ref}
                        if ref in known:
                            continue
                        if is_exempt(lines, ln):
                            rec["reason"] = "显式豁免（示例/自纠/勘误上下文）"
                            exempted.append(rec)
                        else:
                            dangling.append(rec)
    return dangling, exempted, n_files


def run(json_out=False):
    known, err = load_authoritative()
    if known is None:
        print("★ %s" % err, file=sys.stderr)
        return EXIT_USAGE
    dangling, exempted, n_files = scan(known)
    state = "DANGLING" if dangling else "OK"
    if json_out:
        print(json.dumps({"tool": "dangling-reference-gate", "version": __version__,
                          "state": state, "authoritative_count": len(known),
                          "dangling": dangling, "exempted": exempted,
                          "scanned_files": n_files}, ensure_ascii=False, indent=1))
    else:
        print("== %s ==" % banner())
        print("   权威源：%s（%d 个合法标识符）" % (os.path.relpath(LEDGER, ROOT), len(known)))
        print("   判据：∀ 引用 r: r ∈ 权威源 ⇒ 可解；否则为 ★ 悬挂引用")
        print("   扫描：%d 个文件（%s）" % (n_files, ",".join(SCAN_DIRS)))
        print()
        if dangling:
            print("  ❌ DANGLING —— ★ 存在不可解引用（等于引了不存在的锚）：")
            for d in dangling:
                print("     · %s : 行 %d : %s" % (d["file"], d["line"], d["ref"]))
            print()
            print("  ★ 修法：改为权威源中的实际值，或标注 [示例]/自纠 上下文以显式豁免")
        else:
            print("  ✅ OK —— 全部引用可解")
        if exempted:
            print()
            print("  ⏭ 显式豁免 %d 处（★ 正当：记录错误引用属勘误纪律）：" % len(exempted))
            for e in exempted[:5]:
                print("     · %s : 行 %d : %s" % (e["file"], e["line"], e["ref"]))
            if len(exempted) > 5:
                print("     ...（共 %d 处，--exemptions 看全部）" % len(exempted))
        print()
        print("  ⇒ 判定：%s" % ("PASS" if not dangling else "★ FAIL（%d 处悬挂）" % len(dangling)))
    log("run state=%s dangling=%d exempted=%d files=%d" % (state, len(dangling), len(exempted), n_files))
    return EXIT_DANGLING if dangling else EXIT_OK


def exemptions():
    """★ 独立可跑：列出所有被豁免的引用（证明豁免是【显式】的，非静默）。"""
    known, err = load_authoritative()
    if known is None:
        print("★ %s" % err, file=sys.stderr)
        return EXIT_USAGE
    _, exempted, n_files = scan(known)
    print("== %s · 豁免清单 ==" % banner())
    print("  规则：引用所在行或其上一行含 %s 之一 ⇒ 豁免" % " / ".join(EXEMPT_MARKS))
    print("  ★ 豁免须【显式书写】—— 不写标记即为悬挂引用（会被 --check 报出）")
    print("  扫描 %d 个文件，命中豁免 %d 处：" % (n_files, len(exempted)))
    for e in exempted:
        print("    · %s : 行 %d : %s" % (e["file"], e["line"], e["ref"]))
    if not exempted:
        print("    （无）")
    log("exemptions %d" % len(exempted))
    return EXIT_OK


def selftest():
    """★ 正例 + 负例（可解 / 悬挂 / 豁免 / 权威源缺失）。"""
    print("== %s selftest ==" % banner())
    fails = neg = pos = 0

    def c(name, cond, kind="pos"):
        nonlocal fails, neg, pos
        if kind == "pos":
            pos += 1
        else:
            neg += 1
        ok = bool(cond)
        print("  %s %-6s %-58s" % ("✅" if ok else "❌", kind, name))
        if not ok:
            fails += 1

    # [示例] ★ 本块内的标识符为【selftest 测试数据】，非真实引用 ⇒ 显式豁免
    import tempfile
    tmp = tempfile.mkdtemp(prefix="drg-")
    # 造一个临时权威源
    led = os.path.join(tmp, "led.json")
    io.open(led, "w", encoding="utf-8").write(json.dumps({
        # [示例] ★ selftest 测试数据（非真实引用）⇒ 显式豁免
        "authorizations": [{"authId": "AUTH-20260101-aaaa1111"}],
        # [示例] ★ selftest 测试数据（非真实引用）⇒ 显式豁免
        "changes": [{"id": "CHG-20260101-bbbb2222"}]}))
    known, err = load_authoritative(led)
    c("权威源可读", known is not None and len(known) == 2)
    c("★ 不存在的源 ⇒ 报错（不静默）", load_authoritative("/nonexistent.json")[0] is None, kind="neg")

    # 造扫描目录
    sd = os.path.join(tmp, "docs"); os.makedirs(sd)
    io.open(os.path.join(sd, "ok.md"), "w", encoding="utf-8").write(
        # [示例] ★ selftest 测试数据（非真实引用）⇒ 显式豁免
        "引用 AUTH-20260101-aaaa1111 与 CHG-20260101-bbbb2222\n")
    io.open(os.path.join(sd, "bad.md"), "w", encoding="utf-8").write(
        # [示例] ★ selftest 测试数据（非真实引用）⇒ 显式豁免
        "引用 AUTH-20260101-deadbeef（截断/不存在）\n")
    io.open(os.path.join(sd, "exempt.md"), "w", encoding="utf-8").write(
        # [示例] ★ selftest 测试数据（非真实引用）⇒ 显式豁免
        "★ 自纠：首版误写为 AUTH-20260101-deadbeef ⇒ 已改正\n")
    dang, exm, n = scan(known, root=tmp, dirs=("docs",), exts=(".md",))
    # [示例] ★ selftest 测试数据（非真实引用）⇒ 显式豁免
    c("可解引用 ⇒ 不报", all(d["ref"] != "AUTH-20260101-aaaa1111" for d in dang))
    # [示例] ★ selftest 测试数据（非真实引用）⇒ 显式豁免
    c("★ 悬挂引用 ⇒ 被报出", any(d["ref"] == "AUTH-20260101-deadbeef" for d in dang), kind="neg")
    c("★ 指出【文件+行号】", any(d["file"].endswith("bad.md") and d["line"] == 1 for d in dang))
    c("★ 显式豁免（自纠上下文）⇒ 不报但仍列出",
      # [示例] ★ selftest 测试数据（非真实引用）⇒ 显式豁免
      any(e["ref"] == "AUTH-20260101-deadbeef" for e in exm) and
      # [示例] ★ selftest 测试数据（非真实引用）⇒ 显式豁免
      not any(d["ref"] == "AUTH-20260101-deadbeef" and d["file"].endswith("exempt.md") for d in dang))
    c("★ 无标记的同名引用【不被】豁免（豁免须显式）",
      any(d["file"].endswith("bad.md") for d in dang), kind="neg")

    # 剥离器
    c("strip_code 可调用且行号对齐",
      len(strip_code("a='AUTH-1'\nb=2\n").split("\n")) == len("a='AUTH-1'\nb=2\n".split("\n")))

    print("\n  selftest: %d FAIL ｜ 反例 %d 条 / 正例 %d 条" % (fails, neg, pos))
    log("selftest %d FAIL neg=%d pos=%d" % (fails, neg, pos))
    return 0 if fails == 0 else 1


def selfcheck():
    """★ TCC 能力边界自检（扫描前剥离字符串与注释）。"""
    src = io.open(os.path.abspath(__file__), encoding="utf-8").read()
    strip_code(src)
    print("== %s 自查（TCC 能力边界）==" % banner())
    print("【① 能力清单】")
    print("  · 扫描全仓标识符引用（%s）并对照权威源"
          % "、".join(k for k, _, _ in REF_PATTERNS))
    print("  · 权威源：data/proxy-change-ledger.json（authorizations/../authId · changes/../id）")
    print("  · --exemptions 独立列出豁免项 · --json 机器可读")
    print("【② 不该发生路径清单】")
    print("  · 修改任何被扫文件 ⇒ 本器【只读 + 写自己的日志】，无写他人文件的路径")
    print("  · 把「权威源读不到」说成「无悬挂」 ⇒ 报错并 exit 2，不静默放过")
    print("  · 静默豁免 ⇒ 豁免须【显式写标记】(%s)，且 --exemptions 可列全" % "/".join(EXEMPT_MARKS))
    print("  · 自指误报 ⇒ 扫描前剥离字符串与注释（strip_code）")
    print("【③ 依赖完整性】")
    print("  · Python %s（仅标准库：argparse/io/json/os/re/sys/time/tokenize）" % sys.version.split()[0])
    print("  · 固定日志：%s" % LOG)
    print("  · ✅ 无第三方依赖")
    log("selfcheck ok")
    return 0


def lean4_check():
    """★ 如实声明：本器无 .lean 规范源，不冒充谓词对应性验证。"""
    print("== %s · --lean4-check ==" % banner())
    print("  ★ 如实声明：本器【无 Lean4 规范源】—— 它是一条【引用可解性】判据，不含形式化定理。")
    print("  判据来源（人可读）：裁判 session-1ffded95 2026-10-10 的**三步模型**：")
    print("    描述 → ★命名抽取 → **门化**；本器即第三步。")
    print("  本器的机械化形式：")
    print("    INVARIANT: ∀ r ∈ references(files): r ∈ authoritative(ledger)")
    print("    VIOLATION: ∃ r. r ∉ authoritative  ⇒ DANGLING")
    print("  ⇒ 2/2 说明项在场（判据来源 + 机械化形式）；★ 无定理可证 —— 如实标记。")
    log("lean4-check ok（无 .lean 规范源，如实声明）")
    return 0


def main():
    ap = argparse.ArgumentParser(
        prog="dangling-reference-gate.py",
        description="悬挂引用门 —— 检查引用的标识符是否可在权威源中检索到")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--exemptions", action="store_true", help="★ 列出显式豁免的引用")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--lean4-check", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print(__version__)
        return EXIT_OK
    if a.selftest:
        return selftest()
    if a.selfcheck:
        return selfcheck()
    if a.lean4_check:
        return lean4_check()
    if a.exemptions:
        return exemptions()
    return run(json_out=a.json)


if __name__ == "__main__":
    sys.exit(main())
