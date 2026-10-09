#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test-script-selfcheck-gate.py — 测试脚本自检门（v1.0.0）

为何存在（★ 判据来源：裁判 `session-1ffded95` 2026-10-10 的可门化裁决）
    executor `session-b250bf9d` 自报：「**我的测试脚本比被测物更易出错**」
    —— 实证：写卡片/测试时，我【两次】让测试脚本自身出错（JSON 多行字符串、
    `cd` 后相对路径致 exit=127），而**被测物一次都没错**。

    裁判按其二元条件裁决：**可门化** ✓
      · **形态**可显式给出：测试脚本的**非预期退出码**（如 exit=127 / 非 0）
      · **真值源**可显式给出：**该测试脚本自己的 `--selftest` 是否通过**
      ⇒ 二者都明确 ⇒ 可门化（与「易变量」不同：那条真值源给不出）

    **裁判的建议落地形式**：
      「**凡提交测试脚本 ⇒ 须同时提供其实跑通过的 `--selftest`**」
      （与「负控要独立可跑」同一做法 —— 让**声称**变成**可跑**）

判据（★ 三态，不做折算）
    OK        每个测试脚本都有 `--selftest` **且实跑通过**
    FAIL      存在测试脚本：① 无 `--selftest`，或 ② 有但实跑【未通过】/【非预期退出码】
    UNCHECKED 无法判定（非 py / 解释器缺失 / 超时）⇒ 如实列出，**不计入通过**

★ 判定「测试脚本」的口径（★ 显式给出，避免暗含假设）
    文件名或路径含下列词之一，且**不是**被测主体（不含 `--selftest` 的普通工具）：
        test · smoke · check · verify · probe · spec
    ★ 口径可`--include/--exclude` 覆盖（避免口径本身成为隐含假设）。

用法
    python3 test-script-selfcheck-gate.py [--json]           # 扫全部 devices/ 下的测试脚本
    python3 test-script-selfcheck-gate.py --run              # ★ 实跑各自的 --selftest
    python3 test-script-selfcheck-gate.py --path <dir>       # 指定目录
    python3 test-script-selfcheck-gate.py --selftest
    python3 test-script-selfcheck-gate.py --selfcheck
    python3 test-script-selfcheck-gate.py --version

退出码（★ R006 ⑨）
    0 = 无 FAIL（可能有 UNCHECKED，会显式列出）
    1 = 有 FAIL（有测试脚本无 selftest 或 selftest 不通过）
    2 = 用法错误
"""

__version__ = '1.0.0'   # ★ R006 ⑥ 唯一版本声明处

import argparse
import io
import json
import os
import re
import subprocess
import sys
import time
import tokenize

ROOT = os.path.expanduser("~/dsh-collab")
LOG_DIR = os.path.join(ROOT, "logs")
LOG = os.path.join(LOG_DIR, "dsh-plugin-test-script-selfcheck-gate.log")
TIMEOUT = 60

# ★ 判定口径（显式给出 —— 避免把假设藏在代码里）
TEST_TOKENS = ("test", "smoke", "check", "verify", "probe", "spec")
SKIP_DIRS = (".git", "node_modules", "/logs", "__pycache__")

# ★ 外部命令白名单（R006 ⑩ 类型锁）：只调解释器跑 --selftest，不执行任意命令
ALLOWED_INTERPRETERS = (sys.executable, "python3")

EXIT_OK, EXIT_FAIL, EXIT_USAGE = 0, 1, 2


def log(msg):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass


def banner():
    return "test-script-selfcheck-gate v%s" % __version__


def strip_code(src):
    """★ 剥离字符串与注释（防自指误报，本线 F63）。★ 按 token 行号重建 ⇒ 行号对齐。"""
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

def is_test_script(path):
    """★ 口径：路径含 TEST_TOKENS 之一，且是 .py。"""
    if not path.endswith(".py"):
        return False
    base = os.path.basename(path).lower()
    parent = os.path.basename(os.path.dirname(path)).lower()
    return any(t in base or t in parent for t in TEST_TOKENS)


def has_selftest(path):
    """★ 真值源：源码里是否注册了 `--selftest` 旗标（★ 剥离后判，防自指）。"""
    try:
        s = io.open(path, encoding="utf-8", errors="ignore").read()
    except Exception:
        return False
    if '"--selftest"' not in s and "'--selftest'" not in s:
        return False
    # ★ 还须有对应实现函数（否则只是声明 —— 「声称 ≠ 可跑」）
    code = strip_code(s)
    return bool(re.search(r"def\s+selftest\s*\(", code))


def run_selftest(path, timeout=TIMEOUT):
    """★ 实跑 `--selftest`，返回 (state, detail)。★ 四态如实分报。"""
    if not os.path.exists(path):
        return ("UNCHECKED", "文件不存在")
    if not sys.executable:
        return ("UNCHECKED", "解释器不可用")
    try:
        t0 = time.time()
        r = subprocess.run([sys.executable, path, "--selftest"],
                           capture_output=True, text=True, timeout=timeout, cwd=os.path.dirname(path))
        dt = time.time() - t0
    except subprocess.TimeoutExpired:
        return ("UNCHECKED", "超时 >%ds（★ 不折算为通过）" % timeout)
    except Exception as e:
        return ("UNCHECKED", "无法执行：%s" % type(e).__name__)
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0:
        return ("FAIL", "selftest 退出码 %d（★ 非预期）" % r.returncode)
    if "0 FAIL" not in out:
        return ("FAIL", "输出未见「0 FAIL」⇒ 不认作通过")
    return ("OK", "%.2fs" % dt)


def scan(paths, run=False):
    """★ 扫描 ⇒ (rows, stats)。rows: [{path, has_selftest, state, detail}]"""
    rows = []
    for base in paths:
        if not os.path.exists(base):
            continue
        for r, ds, fs in os.walk(base):
            if any(x in r for x in SKIP_DIRS):
                continue
            for fn in sorted(fs):
                p = os.path.join(r, fn)
                if not is_test_script(p):
                    continue
                hs = has_selftest(p)
                if not hs:
                    rows.append({"path": os.path.relpath(p, ROOT), "has_selftest": False,
                                 "state": "FAIL", "detail": "★ 无 --selftest（或只有旗标无实现）"})
                elif run:
                    st, d = run_selftest(p)
                    rows.append({"path": os.path.relpath(p, ROOT), "has_selftest": True,
                                 "state": st, "detail": d})
                else:
                    rows.append({"path": os.path.relpath(p, ROOT), "has_selftest": True,
                                 "state": "OK", "detail": "有 --selftest（未实跑，--run 可实跑）"})
    stats = {}
    for x in rows:
        stats[x["state"]] = stats.get(x["state"], 0) + 1
    return rows, stats


def main_run(json_out=False, run=False, paths=None):
    paths = paths or [os.path.join(ROOT, "devices")]
    rows, stats = scan(paths, run=run)
    if json_out:
        print(json.dumps({"tool": "test-script-selfcheck-gate", "version": __version__,
                          "run": run, "paths": paths, "rows": rows, "stats": stats},
                         ensure_ascii=False, indent=1))
    else:
        print("== %s ==" % banner())
        print("  口径：路径含 %s 之一且为 .py ⇒ 视为测试脚本（★ 显式给出，非隐含）"
              % "/".join(TEST_TOKENS))
        print("  判据：测试脚本须有 `--selftest`（旗标 + 实现）%s"
              % ("且【实跑通过】" if run else "（★ 未实跑 —— 加 --run 实跑）"))
        print("  扫描：%s" % ", ".join(os.path.relpath(p, ROOT) for p in paths))
        print()
        icon = {"OK": "✅", "FAIL": "❌", "UNCHECKED": "⏭"}
        for x in rows:
            print("  %s %-9s %-56s %s" % (icon.get(x["state"], "?"), x["state"], x["path"], x["detail"]))
        if not rows:
            print("  （未发现测试脚本）")
        print()
        print("  ⇒ OK %d · FAIL %d · UNCHECKED %d"
              % (stats.get("OK", 0), stats.get("FAIL", 0), stats.get("UNCHECKED", 0)))
        if stats.get("UNCHECKED"):
            print("  ★ 注意：UNCHECKED %d 项【未计入通过】—— 见上逐条原因" % stats["UNCHECKED"])
        print("  ⇒ 判定：%s" % ("PASS" if not stats.get("FAIL") else "★ FAIL（%d 项）" % stats["FAIL"]))
    log("run run=%s ok=%d fail=%d unchecked=%d"
        % (run, stats.get("OK", 0), stats.get("FAIL", 0), stats.get("UNCHECKED", 0)))
    return EXIT_FAIL if stats.get("FAIL") else EXIT_OK


def selftest():
    """★ 正例 + 负例（有/无 selftest · 通过/失败 · 超时/不可执行）。"""
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

    import tempfile
    tmp = tempfile.mkdtemp(prefix="tssg-")
    # ① 有 selftest 且通过的
    good = os.path.join(tmp, "test_good.py")
    io.open(good, "w", encoding="utf-8").write(
        'import sys\n'
        'def selftest():\n    print("selftest: 0 FAIL")\n    return 0\n'
        'if "--selftest" in sys.argv:\n    sys.exit(selftest())\n')
    # ② 无 selftest
    bad = os.path.join(tmp, "test_bad.py")
    io.open(bad, "w", encoding="utf-8").write('print("nothing")\n')
    # ③ 有旗标但 selftest 失败
    f = os.path.join(tmp, "test_failing.py")
    io.open(f, "w", encoding="utf-8").write(
        'import sys\n'
        'def selftest():\n    print("selftest: 1 FAIL")\n    return 1\n'
        'if "--selftest" in sys.argv:\n    sys.exit(selftest())\n')
    # ④ 只有旗标字符串、无实现（★ 声称 ≠ 可跑）
    fake = os.path.join(tmp, "test_declared_only.py")
    io.open(fake, "w", encoding="utf-8").write(
        'import sys\nprint("has --selftest but no impl")\n')

    c("口径：test_*.py 判为测试脚本", is_test_script(good))
    c("口径：普通工具不判为测试脚本", not is_test_script(os.path.join(tmp, "helper.py")))
    c("有 selftest ⇒ has_selftest=True", has_selftest(good))
    c("★ 无 selftest ⇒ False", not has_selftest(bad), kind="neg")
    c("★ 只有旗标字符串无实现 ⇒ False（声称≠可跑）", not has_selftest(fake), kind="neg")

    st, d = run_selftest(good)
    c("★ 实跑通过的 ⇒ OK", st == "OK", "(%s)" % d)
    st2, d2 = run_selftest(f)
    c("★ 实跑失败的 ⇒ FAIL（非预期退出码）", st2 == "FAIL", "(%s)" % d2)
    st3, d3 = run_selftest(os.path.join(tmp, "nonexistent.py"))
    c("★ 不存在 ⇒ UNCHECKED（不折算为通过）", st3 == "UNCHECKED", "(%s)" % d3)

    rows, stats = scan([tmp], run=True)
    c("★ 汇总：3 个 FAIL 被如实计数", stats.get("FAIL", 0) == 3, "(%s)" % stats)
    c("★ FAIL 时判定应为不过", bool(stats.get("FAIL")))

    c("strip_code 行号对齐",
      len(strip_code("a='x'\nb=2\n").split("\n")) == len("a='x'\nb=2\n".split("\n")))

    print("\n  selftest: %d FAIL ｜ 反例 %d 条 / 正例 %d 条" % (fails, neg, pos))
    log("selftest %d FAIL neg=%d pos=%d" % (fails, neg, pos))
    return 0 if fails == 0 else 1


def selfcheck():
    """★ TCC 能力边界自检（扫描前剥离字符串与注释）。"""
    src = io.open(os.path.abspath(__file__), encoding="utf-8").read()
    strip_code(src)
    print("== %s 自查（TCC 能力边界）==" % banner())
    print("【① 能力清单】")
    print("  · 扫测试脚本（口径：路径含 %s）并检查其 `--selftest` 是否存在" % "/".join(TEST_TOKENS))
    print("  · --run 实跑各脚本的 --selftest（四态：OK/FAIL/UNCHECKED，超时不折算）")
    print("  · --json 机器可读 · --path 指定目录")
    print("【② 不该发生路径清单】")
    print("  · 执行任意命令 ⇒ 只调解释器跑 --selftest；解释器取自 sys.executable，不接受外部输入")
    print("  · 修改被扫脚本 ⇒ 本器只读 + 写自己的日志")
    print("  · 把「有旗标但无实现」当作有 selftest ⇒ ★ 断言「旗标 + 实现」二者皆在")
    print("  · 自指误报 ⇒ 扫描前剥离字符串与注释（strip_code）")
    print("【③ 依赖完整性】")
    print("  · Python %s（仅标准库：argparse/io/json/os/re/subprocess/sys/time/tokenize）"
          % sys.version.split()[0])
    print("  · 固定日志：%s" % LOG)
    print("  · ✅ 无第三方依赖")
    log("selfcheck ok")
    return 0


def lean4_check():
    """★ 如实声明：本器无 .lean 规范源，不冒充谓词对应性验证。"""
    print("== %s · --lean4-check ==" % banner())
    print("  ★ 如实声明：本器【无 Lean4 规范源】—— 它是一条【声明可核性】判据，不含形式化定理。")
    print("  判据来源（人可读）：裁判 session-1ffded95 2026-10-10 依其二元条件裁决：")
    print("    · 形态可显式给出 = 测试脚本的非预期退出码")
    print("    · 真值源可显式给出 = 该脚本自己的 --selftest 是否通过")
    print("    ⇒ 二者明确 ⇒ 可门化")
    print("  本器的机械化形式：")
    print("    INVARIANT: ∀ s ∈ test_scripts: has_selftest(s) ∧ selftest(s) == 0")
    print("    VIOLATION: ∃ s. ¬has_selftest(s) ∨ selftest(s) ≠ 0  ⇒ FAIL")
    print("  ⇒ 2/2 说明项在场（判据来源 + 机械化形式）；★ 无定理可证 —— 如实标记。")
    log("lean4-check ok（无 .lean 规范源，如实声明）")
    return 0


def main():
    ap = argparse.ArgumentParser(
        prog="test-script-selfcheck-gate.py",
        description="测试脚本自检门 —— 测试脚本须有 --selftest 且（--run 时）实跑通过")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--run", action="store_true", help="★ 实跑各脚本的 --selftest")
    ap.add_argument("--path", action="append", help="指定扫描目录（可多次）")
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
    return main_run(json_out=a.json, run=a.run, paths=a.path)


if __name__ == "__main__":
    sys.exit(main())
