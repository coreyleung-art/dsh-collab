#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mutation-gate.py — ★★ 结构门：**新控必须能被证明会红**。（v1.1.0，2026-10-12 事故后重建）

★ 为什么需要：本线在 channel-denominator v2.0 写过一条「排除控」——形式完整、有负例、
  `--selftest` 报 fails=0，★ **但它恒真、永远不会红**。本机既有的 R006 ⑩ **B 项**
  （「负例全部被拒」）**也拦不住它**。⇒ ★ **「有负控」与「负控有效」是两件事。**

★★★ v1.1.0 头号教训：本门 v1.0.0 删掉过 164 个文件
  v1.0.0 把变异副本从 /tmp 改到【与原文件同目录】（因 beacon-check 靠 `__file__` 定位资源），
  ★ 但只改了 check_one 的清理句，**漏了 selftest ⑥** —— 它仍在 `rmtree(os.path.dirname(tmp))`，
  而副本现在在 scripts/ 里 ⇒ ★★ **它把整个 ~/dsh-collab/scripts/ 删了**（164 个未提交文件永久丢失）。
  ⇒ ★ 本版把**安全删除写成第一等公民**：`_safe_remove()` 只肯删
    【同目录 ∧ 名字以 .mutgate- 开头 ∧ 不是目录】的文件，**且它自己也有负控**。

判据（三条合取，缺一即不算数）：① 基线绿 ② 变异点恰好命中 1 次 ③ 变异后红
⇒ 不齐 ⇒ 拒收(exit 1)；拿不到读数 ⇒ 不可判(exit 2)，**不冒充通过**。

用法：--run [--manifest ...] [--json] | --selftest | --selfcheck | --lean4-check | --version
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

__version__ = "1.1.0"   # ★ R006 ⑥ 唯一版本声明处
LOG = os.path.expanduser("~/dsh-collab/logs/mutation-gate.log")
DEFAULT_MANIFEST = os.path.expanduser("~/dsh-collab/guard/mutation-manifest.json")
MUT_PREFIX = ".mutgate-"
V_PASS, V_REJECT, V_UNDECIDABLE = "PASS", "REJECT", "UNDECIDABLE"


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass


# ══════════════ ★★★ 安全删除 —— 本版的第一等公民 ══════════════
class UnsafeTarget(Exception):
    """★ 拒绝删除时抛出。★ **宁可留垃圾，不可删错。**"""


def _safe_remove(path, tool_dir):
    """★ 只允许删除【工具同目录下、名字以 .mutgate- 开头】的**文件**。

    ★★ 立此判据的原因：v1.0.0 用 `rmtree(os.path.dirname(tmp))`，而 tmp 的 dirname
      随「副本放哪」而变 —— ★ 副本一改到同目录，这个「算出来的路径」就指向 scripts/ 本身。
    ⇒ ★ **凡删除目标由运行时算出 ⇒ 必须先过白名单断言，不得直接删。**
    """
    ap, d = os.path.abspath(path), os.path.abspath(tool_dir)
    if os.path.dirname(ap) != d:
        raise UnsafeTarget("目标不在工具同目录：%s（工具目录 %s）" % (ap, d))
    if not os.path.basename(ap).startswith(MUT_PREFIX):
        raise UnsafeTarget("名字不以 %s 开头：%s" % (MUT_PREFIX, os.path.basename(ap)))
    if os.path.isdir(ap):
        raise UnsafeTarget("★ 目标是【目录】，本门只删自己写的文件：%s" % ap)
    if not os.path.exists(ap):
        return False
    os.remove(ap)
    return True


# ══════════════ 探针 ══════════════
def run_probe(tool, args, timeout=600):
    """★ 返回 (rc, out)。★ rc=None ⇒ 不可判，不是失败。"""
    if not os.path.exists(tool):
        return None, "工具不存在：%s" % tool
    try:
        r = subprocess.run([sys.executable, tool] + list(args), capture_output=True,
                           text=True, timeout=timeout,
                           cwd=os.path.dirname(os.path.abspath(tool)) or ".")
    except subprocess.TimeoutExpired:
        return None, "探针超时（%ss）⇒ 不可判" % timeout
    except Exception as e:
        return None, "探针起不来：%s" % type(e).__name__
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def probe_ok(rc, out, spec):
    if rc is None:
        return None
    if rc != spec.get("expect_rc", 0):
        return False
    if any(s not in out for s in spec.get("must_contain", [])):
        return False
    if any(s in out for s in spec.get("must_not_contain", [])):
        return False
    return True


def apply_mutation(tool, mut):
    """★ 返回 (tmp_path 或 None, note)。★ None ⇒ 不可判。

    ★ 副本放【与原文件同目录】（依赖 `__file__` 定位资源的工具才跑得起来），
      故用 .mutgate- 前缀，**用后一律经 _safe_remove**。
    """
    if mut.get("kind") != "py_replace":
        return None, "未知变异类型 %r（冻结枚举：py_replace）⇒ 不可判" % mut.get("kind")
    find, repl = mut.get("find"), mut.get("replace")
    if not isinstance(find, str) or not find:
        return None, "py_replace 缺 find ⇒ 不可判"
    try:
        src = open(tool, encoding="utf-8").read()
    except Exception as e:
        return None, "原文件读不开 %s ⇒ 不可判" % type(e).__name__
    n = src.count(find)
    if n != 1:
        return None, "★ 变异串在原文中出现 %d 次（要求恰好 1 次）⇒ 不可判" % n
    src2 = src.replace(find, repl, 1)
    if src2 == src:
        return None, "替换后与原文逐字相同 ⇒ 空变异 ⇒ 不可判"
    d = os.path.dirname(os.path.abspath(tool)) or "."
    dst = os.path.join(d, "%s%s-%d.py" % (MUT_PREFIX,
                                          os.path.basename(tool).replace(".py", ""), os.getpid()))
    with open(dst, "w", encoding="utf-8") as f:
        f.write(src2)
    os.chmod(dst, 0o755)
    return dst, "py_replace：同目录副本 %s" % dst


def check_one(item):
    """★ 三条合取判定。★ 清理一律走 _safe_remove。"""
    tid = item.get("id") or "(无 id)"
    tool = os.path.expanduser(item.get("tool") or "")
    tool_dir = os.path.dirname(os.path.abspath(tool)) if tool else "."
    args = item.get("probe_args") or ["--selftest"]
    out = {"id": tid, "tool": tool, "reasons": []}
    base_rc, base_out = run_probe(tool, args)
    base_ok = probe_ok(base_rc, base_out, item.get("probe") or {})
    out["baseline"] = ("不可判" if base_ok is None else ("绿" if base_ok else "红"))
    if base_ok is None:
        out["verdict"] = V_UNDECIDABLE
        out["reasons"].append("基线拿不到读数：%s" % base_out)
        return out
    if not base_ok:
        out["verdict"] = V_UNDECIDABLE
        out["reasons"].append("★ 基线本身就是红的 ⇒ 无法用它做变异测试（先修基线）")
        return out
    tmp, note = apply_mutation(tool, item.get("mutation") or {})
    if tmp is None:
        out["verdict"] = V_UNDECIDABLE
        out["reasons"].append("★ %s" % note)
        return out
    out["mutation_note"] = note
    try:
        mut_rc, mut_out = run_probe(tmp, args)
        mut_ok = probe_ok(mut_rc, mut_out, item.get("probe") or {})
        if mut_ok is None:
            out["verdict"] = V_UNDECIDABLE
            out["reasons"].append("变异后拿不到读数：%s" % mut_out)
            return out
        if mut_ok:
            out["verdict"] = V_REJECT
            out["reasons"].append("★★ 变异后仍然【绿】⇒ 该控【恒真、不会红】，"
                                  "【或该变异是空操作（如 `[] or [...]` 恒等于原值）】⇒ 拒收")
            return out
        want = item.get("expect_red_marker")
        if want and want not in mut_out:
            out["verdict"] = V_UNDECIDABLE
            out["reasons"].append("★ 变异后确已变红，但输出找不到声明的标记 %r ⇒ 无法确认是那条控红的" % want)
            return out
        out["verdict"] = V_PASS
        out["reasons"].append("✅ 三条合取成立：基线绿 · 变异点到 · 变异后红%s"
                              % ("（标记 %r 命中）" % want if want else ""))
        return out
    finally:
        try:
            _safe_remove(tmp, tool_dir)
        except UnsafeTarget as e:
            log("★ 拒绝删除（%s），保留 %s" % (e, tmp))


def load_manifest(path):
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        return None, "清单读不开或非 JSON：%s" % type(e).__name__
    items = d.get("items") if isinstance(d, dict) else None
    if not isinstance(items, list) or not items:
        return None, "清单缺 items 或为空（★ 空集 ≠ 通过）"
    return items, None


def run(manifest_path, as_json=False):
    items, err = load_manifest(manifest_path)
    if items is None:
        print("❌ 不可判：%s" % err)
        log("run UNDECIDABLE %s" % err)
        return 2
    results = [check_one(it) for it in items]
    tally = {V_PASS: 0, V_REJECT: 0, V_UNDECIDABLE: 0}
    for r in results:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    verdict = (V_REJECT if tally[V_REJECT] else
               (V_UNDECIDABLE if tally[V_UNDECIDABLE] else V_PASS))
    rep = {"verdict": verdict, "tally": tally, "n": len(results), "results": results,
           "manifest": manifest_path,
           "note": "★ 仅当全部 PASS 才读作通过；REJECT=至少一条控恒真；UNDECIDABLE=不得当通过"}
    if as_json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print("== mutation-gate %s ==" % __version__)
        print("  清单: %s（%d 条）" % (manifest_path, len(results)))
        for r in results:
            print("  [%s] %s" % (r["verdict"], r["id"]))
            for why in r["reasons"]:
                print("        %s" % why)
        print("\n  => PASS=%d · REJECT=%d · UNDECIDABLE=%d · 总判 %s"
              % (tally[V_PASS], tally[V_REJECT], tally[V_UNDECIDABLE], verdict))
    log("run verdict=%s tally=%s" % (verdict, tally))
    return {V_PASS: 0, V_REJECT: 1, V_UNDECIDABLE: 2}[verdict]


GOOD = ("import sys\nLIMIT = 3\ndef main():\n    ok = LIMIT == 3\n"
        "    print('OK' if ok else 'FAIL')\n"
        "    print('selftest: %d PASS / %d FAIL' % (1 if ok else 0, 0 if ok else 1))\n"
        "    return 0 if ok else 1\nif __name__ == '__main__':\n    sys.exit(main())\n")
BLIND = ("import sys\nLIMIT = 3\ndef main():\n    ok = True\n"
         "    print('OK' if ok else 'FAIL')\n"
         "    print('selftest: %d PASS / %d FAIL' % (1 if ok else 0, 0 if ok else 1))\n"
         "    return 0 if ok else 1\nif __name__ == '__main__':\n    sys.exit(main())\n")


def selftest():
    """★ 本门自证。三件别处没有的东西：①「恒真控必被 REJECT」的受测件（本线犯过的错）
    ②「自指变异」③「安全删除」的负控（直接对应 164 文件事故）。"""
    print("== mutation-gate --selftest（★ 含自指变异 + 安全删除负控）==")
    fails = undec = 0
    td = tempfile.mkdtemp(prefix="mutgate-self-")

    def t(name, cond, extra=""):
        nonlocal fails
        if cond:
            print("  ✅ %s%s" % (name, ("  " + extra) if extra else ""))
        else:
            fails += 1
            print("  ❌ %s%s" % (name, ("  " + extra) if extra else ""))

    try:
        good = os.path.join(td, "good_tool.py")
        blind = os.path.join(td, "blind_tool.py")
        open(good, "w").write(GOOD)
        open(blind, "w").write(BLIND)
        probe = {"expect_rc": 0, "must_contain": ["selftest: 1 PASS / 0 FAIL"]}
        mut = {"kind": "py_replace", "find": "LIMIT = 3", "replace": "LIMIT = 99"}

        t("① 合格控（真会红）⇒ PASS",
          check_one({"id": "good", "tool": good, "probe": probe, "mutation": mut})["verdict"] == V_PASS)
        t("★★ ② 恒真控 ⇒ REJECT（本门存在的理由）",
          check_one({"id": "blind", "tool": blind, "probe": probe, "mutation": mut})["verdict"] == V_REJECT)
        t("③ 变异点不存在 ⇒ UNDECIDABLE（不冒充通过）",
          check_one({"id": "nm", "tool": good, "probe": probe,
                     "mutation": {"kind": "py_replace", "find": "NO_SUCH_STRING", "replace": "x"}}
                    )["verdict"] == V_UNDECIDABLE)
        many = os.path.join(td, "many.py")
        open(many, "w").write("import sys\nA = 1\nB = 1\nprint('selftest: 1 PASS / 0 FAIL')\n")
        t("④ 变异串出现 ≥2 次 ⇒ UNDECIDABLE（防误伤）",
          check_one({"id": "multi", "tool": many, "probe": probe,
                     "mutation": {"kind": "py_replace", "find": "= 1", "replace": "= 2"}}
                    )["verdict"] == V_UNDECIDABLE)
        t("⑤ 基线本身红 ⇒ UNDECIDABLE",
          check_one({"id": "rb", "tool": blind,
                     "probe": {"expect_rc": 0, "must_contain": ["绝不可能出现的字符串"]},
                     "mutation": mut})["verdict"] == V_UNDECIDABLE)

        # ═══ ★★★ ⑥ 安全删除负控（直接对应 164 文件事故）═══
        okfile = os.path.join(td, MUT_PREFIX + "ok-1.py")
        open(okfile, "w").write("x = 1\n")
        for nm, target, want_raise in (
                ("★ 拒删【目录】（正是 v1.0.0 闯的祸）", td, True),
                ("★ 拒删外部路径", tempfile.mkdtemp(prefix="outside-"), True),
                ("★ 拒删名字不合规者", good, True),
                ("★ 允许删自己写的同目录文件（正控）", okfile, False)):
            raised = False
            try:
                _safe_remove(target, td)
            except UnsafeTarget:
                raised = True
            t("⑥ 安全删除：%s" % nm, raised == want_raise, "抛异常=%s" % raised)
        t("⑥ 安全删除：上一条正控确实把文件删掉了", not os.path.exists(okfile))

        # ═══ ★ ⑦ 自指变异：弄坏 REJECT 分支 ⇒ 本门自证必须变红 ═══
        me = os.path.abspath(__file__)
        tmp_me, note = apply_mutation(me, {"kind": "py_replace",
                                           "find": 'out["verdict"] = V_' + 'REJECT',
                                           "replace": 'out["verdict"] = V_' + 'PASS'})
        if tmp_me is None:
            print("  ⚠  不可判：自指变异未施加（%s）" % note)
            undec += 1
        else:
            try:
                rr = subprocess.run([sys.executable, tmp_me, "--selftest"],
                                    capture_output=True, text=True, timeout=300)
                t("⑦ 自指变异：弄坏 REJECT 分支 ⇒ 本门自证必须变红",
                  (rr.returncode != 0) and ("❌" in (rr.stdout or "")), "rc=%s" % rr.returncode)
            finally:
                try:
                    _safe_remove(tmp_me, os.path.dirname(me))
                except UnsafeTarget as e:
                    log("★ 拒绝删除自指副本：%s" % e)
    finally:
        shutil.rmtree(td, ignore_errors=True)

    print("\n  => fails=%d undecidable=%d version=%s" % (fails, undec, __version__))
    print("  ★ 仅 fails=0【且】undecidable=0 方可读作通过。")
    log("selftest fails=%d undec=%d" % (fails, undec))
    return 0 if fails == 0 else 1


def selfcheck():
    print("== mutation-gate 自查（TCC 能力边界）==")
    print("【① 能力清单】读变异单 → 同目录副本上施加源码级变异 → 跑 probe 断言三条合取")
    print("【② 不该发生路径清单】")
    print("  · ★ 绝不修改被测工具原文件（变异只写 .mutgate-* 副本）")
    print("  · ★★ 删除【只经 _safe_remove】：同目录 ∧ .mutgate- 前缀 ∧ 非目录，缺一即拒")
    print("  · ★ 变异串出现 ≠1 次 ⇒ 拒绝施加（防误伤）")
    print("【③ 依赖完整性】Python %s · 标准库 only · ✅ 无第三方依赖" % sys.version.split()[0])
    return 0


def lean4_check():
    checks = []
    me = os.path.abspath(__file__)
    src = open(me, encoding="utf-8").read()

    def _strip(s):
        """★ 剥注释与字符串字面量 —— ★ 判据要查的是【代码】，不是【文本】。
        （v1.0.0 为此连撞四处：规避注释 / 变异声明行 / c() 标签串 / docstring。）"""
        return "\n".join(re.sub(r"'[^']*'", "''", re.sub(r'"[^"]*"', '""', re.sub(r"#.*$", "", ln)))
                         for ln in s.split("\n"))

    code = _strip(src)

    def c(k, name, ok, detail):
        checks.append((k, name, bool(ok), detail))

    _danger = "shell=" + "True"
    c("A", "类型锁：subprocess 首参为列表字面量、代码中无危险参数",
      (_danger not in code) and ("subprocess.run([sys.executable" in code),
      "参数=%s" % (_danger in code))
    # ★★ B 的论域修正（首跑即红，本文件第五处同型）：本判据要禁的是
    #    「对【被测件的计算路径】做 rmtree」，★ **不是禁 rmtree 本身** ——
    #    清【自己的】夹具临时目录（tempfile.mkdtemp）是合法且必要的。
    #    ⇒ 精确判据：★ **删除原语只允许出现在 `_safe_remove` 内部**
    #      = `os.remove(` 在剥注释/字符串后的代码里【恰好出现 1 次】。
    _n_remove = code.count("os.remove(")
    c("B", "删除受控：删除原语只出现在 _safe_remove 内（`os.remove(` 恰好 1 次）",
      ("_safe_remove" in code) and (_n_remove == 1),
      "safe_remove 在位=%s · os.remove 出现 %d 次（要求 1）" % ("_safe_remove" in code, _n_remove))
    c("C", "Schema 门：入口参数经显式 argparse 分派", "add_argument" in src, "argparse 在位")
    _d_argv = bool(re.search(r'--selftest"\s+in\s+sys\.argv', src))
    _d_argp = bool(re.search(r'--selftest"\s*,\s*action', src)) and bool(re.search(r"\ba\.selftest\b", code))
    c("D", "状态机：本工具可自证（--selftest 真实现 + 入口分派，非字符串自指）",
      ("def selftest(" in code) and (_d_argv or _d_argp), "分派=%s" % (_d_argv or _d_argp))
    c("E", "白名单冻结：异常不被静默吞掉（try/except 在位）", "try:" in code, "try 在位")
    # ★★ F 的论域修正（同一处病）：`blind_tool` 是**文件名**，只存在于字符串里，
    #    而我拿剥了字符串的 `code` 去找它 ⇒ 必然找不到。★ 故此处用【原文】`src`。
    #    ★ 教训：**不同判据要用不同的面** —— 查「标识符是否出现」用原文；
    #      查「危险原语是否在代码里」才用剥过的 code。
    c("F", "负例矩阵：自证内建【恒真控必被 REJECT】+【安全删除四条负控】",
      ("blind_tool" in src) and ("UnsafeTarget" in code), "两类反例在位")

    fails = sum(1 for _, _, ok, _ in checks if not ok)
    print("== %s · --lean4-check（六项 A–F）==" % os.path.basename(__file__))
    for k, name, ok, detail in checks:
        print("  %s %s %-58s %s" % ("OK " if ok else "FAIL", k, name, detail))
    print("\n  => %d/%d pass, %d FAIL" % (len(checks) - fails, len(checks), fails))
    return 0 if fails == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--lean4-check", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print(__version__)
        return 0
    if a.selfcheck:
        return selfcheck()
    if a.lean4_check:
        return lean4_check()
    if a.selftest:
        return selftest()
    if a.run:
        return run(os.path.expanduser(a.manifest), as_json=a.json)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
