#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-canfail.py — 通用判据能红门（v1.0.0）

为什么需要
    星桥审查线 2026-10-09：对侧的三个判据（M1 索引 / 版本登记 / 状态机）只**记录**不合规
    而进程仍 exit 0 ⇒ 判据**没有失败路径** ⇒ 「等于不会红」。
    其自述：**「一个判据若没有能让它失败的输入，它就不是判据，是日志。」**
    ⇒ 抽象自 tools/selftest-starbridge-gates.py（首次运行即抓出 4 项假 closed）。

    机械搜索确认本机无同类通用门：`must_fail`/`expect_fail`/`canfail` **命中 0 文件**
    （`INJECT_BAD` 仅存在于星桥三个专用脚本里）⇒ J44 查重 `no-overlap`。

判据（★ 三态，不看单次退出码，看「期望 vs 实得」是否一致）
    CAN_FAIL   负控例：不合规输入 ⇒ 退出码落在期望集合 ∧ 输出含期望文本 ⇒ **判据会红**
    CANNOT_FAIL 负控例：不合规输入 ⇒ 退出码不在期望集合 ⇒ **判据不会红**（= 日志，不是判据）
    POSITIVE_OK 正例：合规输入 ⇒ 退出码落在期望集合

★ 输出纪律（照抄本线教训）
    **分离报告「判据不红」与「数据不合规」**（`is_data_case: true` 的例）。
    —— 前者是**判据的问题**；后者是**数据的问题，而判据正确地红了**。

用法
    python3 gate-canfail.py --cases cases.json
    python3 gate-canfail.py --cases cases.json --dry-run     # 只列将执行什么，不执行
    python3 gate-canfail.py --selftest                       # ★ 门自己的负控
    python3 gate-canfail.py --selfcheck                      # R006 ② TCC 边界自检
    python3 gate-canfail.py --version

cases.json 规格
    [
      {"name": "负例1 索引·指针不可解",
       "cmd": ["python3", "tools/build-starbridge-index.py", "--check"],
       "cwd": "~/dsh-collab",
       "inject_env": {"STARBRIDGE_INJECT_BAD": "unresolvable"},
       "expect_rc": [4],
       "expect_text": "✗ 判据未通过",
       "is_data_case": false,
       "kind": "negative"}
    ]
    字段：name / cmd(数组，必填) / cwd / inject_env / expect_rc(数组；null ⇒ 只要求非 0)
          / expect_text / is_data_case(bool) / kind: "positive"|"negative"

限度（自陈）
    1. **只支持「退出码 + 输出文本」两类断言** —— 不做通用注入框架（有意为之，避免抽象过度）。
    2. `inject_env` 是**约定式**：被检脚本须自行识别该变量并注入坏数据；本门**不生成**坏数据。
    3. 不判断「期望值本身是否正确」 —— 那须人/第三方设定（本门只判「判据是否响应」）。
    4. **超时即失败**（不是跳过）：判据若挂住，不能算通过。

约束门（R006 ⑩）
    ★ 本工具**会执行 cases 里指定的命令**（这是它的用途）⇒ 风险受控方式：
      ① 必须 `--cases` 显式给出（不内置任何命令）；
      ② `--dry-run` 可先看将执行什么；
      ③ 本工具自身**不写任何被检对象文件**，只在需要时用 /tmp；
      ④ 静态扫描本文件：无 eval / exec / os.remove / rmtree / os.chmod / os.kill / pkill。
"""

# ── R006 早期旗标垫片（★ 必须在任何【模块级】参数校验之前） ──
# 动因：本器可能在模块级就校验 argv（如「不认识的参数 ⇒ 拒绝」），那会先于文件末的
# canonical 块，把 --selfcheck / --lean4-check / --r006-sets 当成非法参数拒掉
# （实测：selftest-inventory 与 verification-level-lint 都这样）。
# 做法：此处先把三个旗标摘出并暂存，再由文件末块的守卫统一分派 ——
# 既不绕过本器的严格参数治理，也不让治理挡掉自检入口本身。
import sys as _r006_sys
if __name__ == "__main__":
    _R006_EARLY_FLAGS = [f for f in ("--selfcheck", "--lean4-check", "--r006-sets")
                         if f in _r006_sys.argv]
    if _R006_EARLY_FLAGS:
        _r006_sys.argv = [x for x in _r006_sys.argv if x not in _R006_EARLY_FLAGS]
else:
    _R006_EARLY_FLAGS = []
# ── 垫片结束 ──

import os
import argparse
import json
import time
import subprocess
import sys
import re


# === R006 7 统一日志（本批补课新增）===
#   契约不变：log() 只【追加写日志】，不改变 stdout 内容与退出码。
LOG_DIR = os.path.expanduser("~/dsh-collab/logs")
LOG = os.path.join(LOG_DIR, "gate-canfail.log")


def log(msg):
    """R006 7：固定路径、追加、含时刻；失败也留痕（绝不因日志失败影响主流程）。"""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%dT%H:%M:%S") + " " + msg + "\n")
    except Exception:
        pass

VERSION = "1.0.1"
TIMEOUT = 120


def load_cases(path):
    with open(os.path.expanduser(path), encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise SystemExit("★ cases.json 必须是数组")
    for i, c in enumerate(data):
        if "cmd" not in c or not isinstance(c["cmd"], list):
            raise SystemExit("★ cases[%d] 缺 cmd（须为数组）" % i)
        if "name" not in c:
            c["name"] = "case-%d" % i
        c.setdefault("kind", "negative")
        c.setdefault("is_data_case", False)
        c.setdefault("expect_rc", None)
        c.setdefault("expect_text", None)
        c.setdefault("inject_env", {})
        c.setdefault("cwd", os.path.expanduser("~"))
    return data


def run_case(c, dry):
    if dry:
        return {"name": c["name"], "dry": True, "cmd": " ".join(c["cmd"]),
                "cwd": c["cwd"], "inject_env": c["inject_env"], "expect_rc": c["expect_rc"]}
    env = dict(os.environ)
    # ★ v1.0.1 修正（F65）：全部走 c.get() 兜底 —— selftest() 自建的 case 未经 load_cases()
    #   的 setdefault ⇒ 直接 c["cwd"] 抛 KeyError ⇒ **门自己的负控跑不起来**。
    #   这正是本门要防的形态（语法全绿 ≠ 能跑）发生在门自身 ⇒ 故兜底放在 run_case，
    #   使任何调用路径（load_cases / selftest / 未来调用方）都不崩。
    for k, v in (c.get("inject_env") or {}).items():
        env[str(k)] = str(v)
    try:
        p = subprocess.run([str(x) for x in c["cmd"]], cwd=os.path.expanduser(c.get("cwd") or "~"),
                           capture_output=True, text=True, env=env, timeout=TIMEOUT)
        rc = p.returncode
        out = (p.stdout or "") + (p.stderr or "")
        timeout = False
    except subprocess.TimeoutExpired:
        rc, out, timeout = None, "", True
    except FileNotFoundError as e:
        rc, out, timeout = None, "★ 命令不可执行: %s" % e, False

    exp_rc = c.get("expect_rc")
    if timeout:
        rc_ok = False
    elif exp_rc is None:
        rc_ok = (rc != 0)          # 只要求非 0
    else:
        rc_ok = rc in exp_rc
    expect_text = c.get("expect_text")
    txt_ok = True if not expect_text else (expect_text in out)

    # ★ v1.0.1（F66）：本段原先仍用 c["expect_text"] / c["kind"] / c["is_data_case"] / c["name"]
    #   ⇒ 只修了前半、漏了后半 ⇒ selftest 换一个键继续崩（同一个错连犯两次）。
    #   已全部改 c.get()：对任何调用路径传入的不完整 case 都兜底。
    kind = c.get("kind", "negative")
    name = c.get("name", "case")
    if kind == "positive":
        verdict = "POSITIVE_OK" if (rc_ok and txt_ok) else "POSITIVE_FAIL"
    else:
        verdict = "CAN_FAIL" if (rc_ok and txt_ok) else "CANNOT_FAIL"
    return {"name": name, "kind": kind, "rc": rc, "timeout": timeout,
            "rc_ok": rc_ok, "txt_ok": txt_ok, "verdict": verdict,
            "is_data_case": c.get("is_data_case", False), "expect_rc": exp_rc,
            "expect_text": expect_text, "tail": "\n".join(out.strip().split("\n")[-3:])[:300]}


def report(results):
    print("★ 判据能红门（gate-canfail v%s）" % VERSION)
    print("=" * 96)
    n_ok = 0
    cannot = []
    data_findings = []
    for r in results:
        if r.get("dry"):
            print("  [dry] %-34s cmd=%s" % (r["name"][:34], r["cmd"][:60]))
            print("        cwd=%s inject=%s expect_rc=%s" % (r["cwd"], r["inject_env"], r["expect_rc"]))
            continue
        v = r["verdict"]
        mark = {"CAN_FAIL": "✅", "POSITIVE_OK": "✅", "CANNOT_FAIL": "❌", "POSITIVE_FAIL": "❌"}[v]
        n_ok += 1 if mark == "✅" else 0
        print("  %s %-34s %-14s rc=%-5s 期望=%-8s 文本=%s%s" % (
            mark, r["name"][:34], v, r["rc"],
            r["expect_rc"] if r["expect_rc"] is not None else "非0",
            "✅" if r["txt_ok"] else "❌", "  ★超时" if r["timeout"] else ""))
        if v == "CANNOT_FAIL":
            cannot.append(r)
            print("        ★ 判据不会红 ⇒ 等同日志。末 3 行：")
            for l in r["tail"].split("\n"):
                print("          | %s" % l[:120])
        if v == "CAN_FAIL" and r["is_data_case"]:
            data_findings.append(r)
    print("-" * 96)
    print("  通过 %d / %d" % (n_ok, len([r for r in results if not r.get("dry")])))
    if cannot:
        print()
        print("★★ **判据不红**（判据的问题 —— 无失败路径）：")
        for r in cannot:
            print("   · %s（rc=%s，期望 %s）" % (r["name"], r["rc"], r["expect_rc"]))
    if data_findings:
        print()
        print("★ **另发现数据不合规**（**判据正确地红了** —— 这是数据的问题，不是判据的问题）：")
        for r in data_findings:
            print("   · %s" % r["name"])
            for l in r["tail"].split("\n"):
                if "缺" in l or "missing" in l.lower():
                    print("       %s" % l.strip()[:120])
    print()
    print("★ 限度：只支持「退出码 + 输出文本」两类断言；超时计失败；不判断期望值本身是否正确。")
    return 0 if n_ok == len([r for r in results if not r.get("dry")]) else 1


def selftest():
    """★ 门自己的负控：给一个【不会红】的判据 ⇒ 本门必须报 ❌"""
    import tempfile
    tmp = tempfile.mkdtemp(prefix="canfail-self-")
    # 一个永远 exit 0 的假判据（不会红）
    fake = os.path.join(tmp, "fake_never_fails.py")
    open(fake, "w").write("import sys\nprint('判据通过')\nsys.exit(0)\n")
    # 一个会按注入值红的假判据（能红）
    good = os.path.join(tmp, "fake_can_fail.py")
    open(good, "w").write(
        "import os,sys\n"
        "if os.environ.get('INJECT_BAD')=='1':\n"
        "    print('✗ 判据未通过：注入生效'); sys.exit(4)\n"
        "print('✓ 判据通过'); sys.exit(0)\n")
    cases = [
        {"name": "自测·能红（应 CAN_FAIL）", "cmd": [sys.executable, good],
         "inject_env": {"INJECT_BAD": "1"}, "expect_rc": [4], "expect_text": "✗ 判据未通过",
         "kind": "negative"},
        {"name": "自测·不会红（应 CANNOT_FAIL）", "cmd": [sys.executable, fake],
         "inject_env": {"INJECT_BAD": "1"}, "expect_rc": [4], "expect_text": "✗ 判据未通过",
         "kind": "negative"},
        {"name": "自测·正例（应 POSITIVE_OK）", "cmd": [sys.executable, good],
         "expect_rc": [0], "expect_text": "✓ 判据通过", "kind": "positive"},
    ]
    res = [run_case(c, False) for c in cases]
    print("  门自身负控矩阵：")
    for r in res:
        print("    %-34s ⇒ %s" % (r["name"], r["verdict"]))
    ok = (res[0]["verdict"] == "CAN_FAIL" and
          res[1]["verdict"] == "CANNOT_FAIL" and
          res[2]["verdict"] == "POSITIVE_OK")
    for f in os.listdir(tmp):
        os.unlink(os.path.join(tmp, f))
    os.rmdir(tmp)
    print("  ⇒ %s" % ("✅ 门能区分「会红」与「不会红」—— 不是空转" if ok
                     else "❌ 门无法区分 ⇒ 它自己就是日志，不是门"))
    return 0 if ok else 1


def selfcheck():
    """R006 ② TCC 能力边界自检（★ 剥离字符串/注释，避免自指误报）"""
    import io, tokenize
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    parts = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type in (tokenize.STRING, tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE):
                continue
            parts.append(tok.string)
    except Exception:
        parts = src.split("\n")
    code = " ".join(parts)
    danger = ["eval(", "exec(", "os.remove", "rmtree", "os.chmod", "os.chown",
              "os.kill", "pkill", "launchctl", "os.system"]
    found = [d for d in danger if d in code]
    print("R006 ② TCC 能力边界自检 · gate-canfail v%s" % VERSION)
    print("  ★ 声明：会执行 cases 指定的命令（用途所需）· 必须 --cases 显式给出 · 自身不写被检对象文件")
    print("  危险原语（剥离字符串后）: %s" % (found if found else "无 ✅"))
    print("  ⇒ %s" % ("✅ 声明与实现一致" if not found else "★ 有危险原语，须逐条说明"))
    return 0 if not found else 1


def lean4_check():
    """R006 10 约束门 —— 本器的不变量声明（如实标注限度）。"""
    print("== " + os.path.basename(__file__) + " · --lean4-check ==")
    print("  如实声明：本器【无 .lean 规范源】—— 它是判据执行器，不含形式化定理。")
    print("  => 本检查【不冒充】编译或谓词对应性验证；仅声明其判据形态与限度。")
    print("  本器的不变量（机械化形式）：见 docstring 的「判据」节逐条定义。")
    print("  可独立跑的负控：--selftest（它才是本器的能力边界证据）")
    log("lean4-check ok（无 .lean 规范源，如实声明）")
    return 0


def main():
    ap = argparse.ArgumentParser(description="通用判据能红门（负控验证）")
    ap.add_argument("--cases", help="cases.json 路径")
    ap.add_argument("--dry-run", action="store_true", help="只列将执行什么")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true", help="★ 门自身的负控矩阵")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--lean4-check", action="store_true", help="R006 10 约束门")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("gate-canfail %s" % VERSION); return 0
    if a.selftest:
        return selftest()
    if a.selfcheck:
        return selfcheck()
    if a.lean4_check:
        return lean4_check()
    if not a.cases:
        ap.print_help(); return 2
    cases = load_cases(a.cases)
    results = [run_case(c, a.dry_run) for c in cases]
    if a.json:
        print(json.dumps(results, ensure_ascii=False, indent=1)); return 0
    return report(results)


# ═══════════ R006 ② TCC 能力边界自检 + ⑩ 约束门（canonical 块 · 自包含 · 勿手改） ═══════════
# 由 scripts/r006-u6-apply.py 注入；改模板后重跑注入器，勿在本块内手工编辑。
# 设计原则（三条，均有本线实证来源）：
#   1) ② 的每一句声明都必须【被本块结构核验】—— 只打印不检查的「纸面声明」不算 TCC。
#   2) ⑩ 的 A/ E/F 是【冻结声明 + 变更检测】：新增危险原语/写入点/外部命令调用点 ⇒ 立刻红。
#   3) 反空洞：写入点与命令点扫描器必须先在【合成恶意源】上自证会红，否则判「不能判定」。
#      （依据 R006 §4.2 坑 3：剥字面量后读不到实参 ⇒ 调用点枚举为 0 ⇒ 「0 ⊆ 允许」空洞通过）
import sys as _r006_sys
import os as _r006_os
import io as _r006_io
import re as _r006_re
import json as _r006_json
import ast as _r006_ast
import time as _r006_time
import tokenize as _r006_tokenize
import subprocess as _r006_subprocess

_R006_DECL = {
    'tool': 'gate-canfail',
    'version': '1.0.1',
    'capability': ['通用判据能红门：对一组 cases 逐条判「期望 vs 实得」是否一致（三态 CAN_FAIL / CANNOT_FAIL / POSITIVE_OK）', '会执行 cases 指定的命令 —— 这是它的用途；命令全部来自显式 --cases，本器不内置任何命令', '--dry-run 只列将执行什么，不执行；--json 机器可读'],
    'impossible': ['自身不写任何被检对象文件（只在需要时用 tempfile 自建的 /tmp 临时目录）', '无 --cases 则不执行任何命令', '不判断「期望值本身是否正确」—— 那须人/第三方设定（本门只判判据是否响应）'],
    'log': 'gate-canfail.log',
    'write_roots': ['/tmp', '~/dsh-collab/logs'],
    'negatives': [['--definitely-not-a-flag'], ['--cases']],
    'positive': ['--selftest'],
    'dryrun': None,
    'watch': [],
    'allowed_danger': {
        'os.unlink': '只删本器 tempfile.mkdtemp() 自建临时目录内的文件（os.listdir(tmp) 枚举，非用户输入）',
        'os.rmdir': '只删本器 tempfile.mkdtemp() 自建的临时目录',
    },
    'frozen_exec': frozenset({'subprocess.run'}),
    'frozen_write': frozenset({'<expr>'}),
    'frozen_danger': frozenset({'os.rmdir', 'os.unlink'}),
    'positive_expect_rc': [0],
}

_R006_EXEC_ATTRS = ("run", "Popen", "call", "check_call", "check_output")
_R006_DANGER_ATTRS = {
    "os": ("system", "popen", "remove", "unlink", "rmdir", "removedirs", "chmod", "chown", "kill"),
    "shutil": ("rmtree", "move"),
    "subprocess": _R006_EXEC_ATTRS,
}
_R006_DANGER_NAMES = ("eval", "exec", "compile", "__import__")
_R006_SYNTH_EXEC = "import subprocess as _sp\nfrom subprocess import Popen\n_sp.run(['ls'], shell=True)\nPopen(['x'])\n"
_R006_SYNTH_WRITE = "open('x','w')\nopen(p, mode='a')\n"
_R006_SYNTH_EXEC_WANT = frozenset({"subprocess.run", "subprocess.Popen"})
_R006_SYNTH_WRITE_WANT = frozenset({"const:x", "<expr>"})


def _r006_src():
    return open(_r006_os.path.abspath(__file__), encoding="utf-8").read()


def _r006_strip(s):
    """tokenize 抹除注释与字符串【内容】：按原文区间置空。
    ★ 不重拼 token —— 重拼会吞掉 token 间空白（`if a.selftest:` 变 `ifa.selftest:`）。"""
    buf = list(s)
    off = [0]
    for ln in s.splitlines(True):
        off.append(off[-1] + len(ln))
    try:
        for tk in _r006_tokenize.generate_tokens(_r006_io.StringIO(s).readline):
            if tk.type in (_r006_tokenize.COMMENT, _r006_tokenize.STRING):
                a = off[tk.start[0] - 1] + tk.start[1]
                b = off[tk.end[0] - 1] + tk.end[1]
                for i in range(a, min(b, len(buf))):
                    if buf[i] not in "\r\n":
                        buf[i] = " "
    except Exception:
        return s
    return "".join(buf)


def _r006_aliases(t):
    """import 别名解析：`import subprocess as sp` / `from subprocess import run` 都要认得。
    ★ 不做这步，改个别名就能绕过扫描器（= 空洞通过）。"""
    m = {}
    for n in _r006_ast.walk(t):
        if isinstance(n, _r006_ast.Import):
            for a in n.names:
                m[(a.asname or a.name.split(".")[0])] = a.name.split(".")[0]
        elif isinstance(n, _r006_ast.ImportFrom):
            for a in n.names:
                m[(a.asname or a.name)] = (n.module or "").split(".")[0] + "." + a.name
    return m


def _r006_scan(src):
    """AST 三面读数：外部命令调用点 / 写入点 / 危险原语。
    ★ 用 AST 而非正则：注释与字符串天生不进 AST ⇒ 免除「扫到自己的检测正则」假阳性。"""
    r = {"exec": set(), "write": set(), "danger": set(), "imports": set(), "err": ""}
    try:
        t = _r006_ast.parse(src)
    except Exception as e:
        r["err"] = "AST 解析失败: %s" % e
        return r
    al = _r006_aliases(t)
    for n in _r006_ast.walk(t):
        if isinstance(n, _r006_ast.Import):
            for a in n.names:
                r["imports"].add(a.name.split(".")[0])
        elif isinstance(n, _r006_ast.ImportFrom):
            if n.module:
                r["imports"].add(n.module.split(".")[0])
        elif isinstance(n, _r006_ast.Call):
            f = n.func
            if isinstance(f, _r006_ast.Attribute) and isinstance(f.value, _r006_ast.Name):
                mod = al.get(f.value.id, f.value.id)
                if mod in _R006_DANGER_ATTRS and f.attr in _R006_DANGER_ATTRS[mod]:
                    if mod == "subprocess":
                        r["exec"].add("subprocess." + f.attr)
                    else:
                        r["danger"].add(mod + "." + f.attr)
            elif isinstance(f, _r006_ast.Name):
                tgt = al.get(f.id, f.id)
                if tgt.startswith("subprocess."):
                    r["exec"].add("subprocess." + tgt.split(".", 1)[1])
                elif f.id in _R006_DANGER_NAMES:
                    r["danger"].add(f.id)
                elif f.id == "open":
                    mode = ""
                    if len(n.args) >= 2 and isinstance(n.args[1], _r006_ast.Constant):
                        mode = str(n.args[1].value)
                    for kw in n.keywords:
                        if kw.arg == "mode" and isinstance(kw.value, _r006_ast.Constant):
                            mode = str(kw.value.value)
                    if any(c in mode for c in ("w", "a", "x", "+")):
                        p = "<expr>"
                        if n.args and isinstance(n.args[0], _r006_ast.Constant):
                            p = "const:" + str(n.args[0].value)
                        r["write"].add(p)
    return r


def _r006_regex_pass(s):
    """A 的【独立第二通道】：在 tokenize-剥离后的文本上做正则扫描。
    两通道结论不一致 ⇒ 判「不能判定」，**不得**假设其中某一个对。"""
    code = _r006_strip(s)
    hits = set()
    for pat, name in ((r"\beval\s*\(", "eval"), (r"\bexec\s*\(", "exec"),
                      (r"\b__import__\s*\(", "__import__"),
                      (r"\bos\.system\s*\(", "os.system"), (r"\bos\.popen\s*\(", "os.popen"),
                      (r"\.rmtree\s*\(", "shutil.rmtree"), (r"\bos\.remove\s*\(", "os.remove")):
        if _r006_re.search(pat, code):
            hits.add(name)
    return hits


def _r006_run(argv, timeout=60):
    try:
        p = _r006_subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                                 cwd=_r006_os.path.dirname(_r006_os.path.abspath(__file__)))
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except _r006_subprocess.TimeoutExpired:
        return 124, "TIMEOUT"
    except Exception as e:
        return 125, str(e)


def _r006_snap(paths):
    import hashlib
    out = {}
    for p in paths:
        try:
            st = _r006_os.stat(p)
            with open(p, "rb") as fh:
                h = hashlib.sha256(fh.read()).hexdigest()[:16]
            out[p] = [st.st_size, h]
        except OSError:
            out[p] = None
    return out


def _r006_std_imports(imports):
    """③ 依赖完整性：把顶层 import 分类为 内置 / 标准库 / 第三方（Python 3.9 无 stdlib_module_names）。"""
    import importlib.util as _u
    import sysconfig
    std = _r006_os.path.realpath(sysconfig.get_paths()["stdlib"])
    third, stdlib = [], []
    for m in sorted(imports):
        if m in _r006_sys.builtin_module_names:
            stdlib.append(m)
            continue
        try:
            sp = _u.find_spec(m)
        except Exception:
            sp = None
        if sp is None:
            third.append(m + "(未解析)")
        elif sp.origin and _r006_os.path.realpath(sp.origin).startswith(std):
            stdlib.append(m)
        elif sp.origin in (None, "built-in", "frozen"):
            stdlib.append(m)
        else:
            third.append(m)
    return stdlib, third


def _r006_legacy_narrative():
    """沿用本器【原有的 selfcheck() 自述】—— 不因迁移到 canonical 块而丢失既有声明内容。
    取不到时如实说明（不静默当空）。"""
    f = globals().get("selfcheck")
    if not callable(f) or getattr(f, "__module__", None) != __name__:
        return []
    try:
        import io as _i
        import contextlib as _c
        buf = _i.StringIO()
        with _c.redirect_stdout(buf):
            f()
        return [l.rstrip() for l in buf.getvalue().splitlines() if l.strip()]
    except Exception as e:
        return ["(沿用原有 selfcheck() 失败，如实报出: %s)" % e]


def _r006_selfcheck():
    """R006 ② TCC 能力边界自检：三段输出 + 【结构核验】（不做纸面声明）。"""
    name = _R006_DECL["tool"]
    src = _r006_src()
    sc = _r006_scan(src)
    stdlib, third = _r006_std_imports(sc["imports"])
    W = _R006_DECL
    lines = ["R006 ② TCC 能力边界自检 · %s v%s" % (name, W["version"])]
    lines.append("【① 能力清单】")
    for x in W["capability"]:
        lines.append("  · " + x)
    legacy = _r006_legacy_narrative()
    if legacy:
        lines.append("  · —— 以下沿用本器原有 selfcheck() 自述 ——")
        for l in legacy:
            lines.append("  " + l)
    lines.append("【② 不该发生路径清单】")
    for x in W["impossible"]:
        lines.append("  · " + x)
    lines.append("【③ 依赖完整性】")
    lines.append("  · Python %s（本机）" % _r006_sys.version.split()[0])
    lines.append("  · 标准库 %d 个：%s" % (len(stdlib), ", ".join(stdlib) if stdlib else "无"))
    lines.append("  · 第三方 %d 个：%s" % (len(third), ", ".join(third) if third else "无"))
    lines.append("  · 外部命令调用点（冻结）：%s" % (", ".join(sorted(W["frozen_exec"])) or "无"))
    lines.append("  · 写入点（冻结）：%s" % (", ".join(sorted(W["frozen_write"])) or "无"))
    lines.append("  · 固定日志：%s" % (W["log"] or "无"))

    chk = []
    chk.append(("依赖无第三方", not third, "第三方: %s" % (", ".join(third) or "无")))
    ext_ok = (frozenset(sc["exec"]) == frozenset(W["frozen_exec"]))
    chk.append(("外部命令面与冻结集一致", ext_ok,
                "实测 %s / 冻结 %s" % (sorted(sc["exec"]) or "无", sorted(W["frozen_exec"]) or "无")))
    wr_ok = (frozenset(sc["write"]) == frozenset(W["frozen_write"]))
    chk.append(("写入面与冻结集一致", wr_ok,
                "实测 %s / 冻结 %s" % (sorted(sc["write"]) or "无", sorted(W["frozen_write"]) or "无")))
    roots = [r for r in W.get("write_roots", [])]
    bad = [p for p in sc["write"] if p.startswith("const:") and not any(
        _r006_os.path.expanduser(p[6:]).startswith(_r006_os.path.expanduser(r)) for r in roots)]
    chk.append(("常量写入点在允许根内", not bad, "越界: %s" % (", ".join(bad) if bad else "无")))
    dg_ok = (frozenset(sc["danger"]) == frozenset(W["frozen_danger"]))
    chk.append(("危险原语面与冻结集一致", dg_ok,
                "实测 %s / 冻结 %s" % (sorted(sc["danger"]) or "无", sorted(W["frozen_danger"]) or "无")))
    lg_ok = (not W["log"]) or (W["log"] in src)
    chk.append(("声明的日志路径真实存在于源码", lg_ok, W["log"] or "N/A（本器无日志）"))
    need = ["【① 能力清单】", "【② 不该发生路径清单】", "【③ 依赖完整性】"]
    chk.append(("R006 ② 规格要求的三段齐备", all(n in lines for n in need), " / ".join(need)))
    # ★ 声明的正例必须实测可用（非空转）—— 此前这里放的是「读过自己打印的行」，那是同义反复。
    _pos = W.get("positive", [])
    _prc = None
    if _pos:
        _prc, _po = _r006_run([_r006_sys.executable, _r006_os.path.abspath(__file__)] + list(_pos))
    chk.append(("声明的正例实测可用（非空转）",
                bool(_pos) and _prc in W.get("positive_expect_rc", [0]) and _prc not in (2, 124, 125),
                "%s → rc=%s" % (" ".join(_pos), _prc)))

    fails = [c for c in chk if not c[1]]
    lines.append("⇒ 声明核验：%d/%d 一致%s" % (len(chk) - len(fails), len(chk),
                                        "" if not fails else " · ❌ " + "; ".join(c[0] for c in fails)))
    for nm, ok, dt in chk:
        lines.append("   %s %s — %s" % ("✅" if ok else "❌", nm, dt))
    print("\n".join(lines))
    return 0 if not fails else 1


def _r006_dryrun_proof():
    """⑩ D：有 --dry-run ⇒ 实测 run 前后外部状态一致；无 ⇒ 【结构证明】（并如实标注为变体）。"""
    W = _R006_DECL
    dr = W.get("dryrun")
    watch = [_r006_os.path.expanduser(p) for p in W.get("watch", [])]
    if dr:
        b = _r006_snap(watch)
        rc, out = _r006_run([_r006_sys.executable, _r006_os.path.abspath(__file__)] + list(dr))
        a = _r006_snap(watch)
        return (rc == 0 and a == b), "★ 实测：rc=%s · watch %d 项前后一致=%s" % (rc, len(watch), a == b), "实测"
    src = _r006_src()
    wr = _r006_scan(src)["write"]
    roots = [_r006_os.path.expanduser(r) for r in W.get("write_roots", [])]
    outside = [p for p in wr if p.startswith("const:") and not any(
        _r006_os.path.expanduser(p[6:]).startswith(r) for r in roots)]
    ok = (frozenset(wr) == frozenset(W["frozen_write"])) and not outside
    return ok, ("△ 变体（非实测）：本器无 --dry-run ⇒ 以【写入面冻结 + 全部写入点在允许根内】作结构证明"
                "（%s）" % (", ".join(sorted(wr)) or "零写入点")), "结构证明"


def _r006_lean4_check():
    """R006 ⑩ 约束门 A–F。每项都带【反空洞】控制：扫描器先在合成恶意源上自证会红。"""
    W = _R006_DECL
    src = _r006_src()
    sc = _r006_scan(src)
    me = _r006_os.path.basename(_r006_os.path.abspath(__file__))
    rows = []

    # 反空洞前置：扫描器自证
    syn_e = frozenset(_r006_scan(_R006_SYNTH_EXEC)["exec"])
    syn_w = frozenset(_r006_scan(_R006_SYNTH_WRITE)["write"])
    scanner_live = (syn_e == _R006_SYNTH_EXEC_WANT) and (syn_w == _R006_SYNTH_WRITE_WANT)
    vac = [] if scanner_live else ["合成源未被完整检出 exec=%s write=%s" % (sorted(syn_e), sorted(syn_w))]

    # A 危险原语面（★ 不是「一定没有」—— 有则必须逐条声明并冻结；未声明即红）
    allowed_dg = dict(W.get("allowed_danger", {}))
    a_ast = frozenset(sc["danger"])
    a_rx = frozenset(_r006_regex_pass(src))
    a_frozen = frozenset(W["frozen_danger"])
    unallowed = sorted(a_ast - set(allowed_dg))
    a_ok = (scanner_live and a_ast == a_frozen and not (a_rx - a_ast) and not unallowed)
    rows.append(("A", "危险原语面全部已声明并冻结（无未声明原语）", a_ok,
                 "实测=%s · 已声明 %d 项 · 双通道一致=%s%s"
                 % (sorted(a_ast) or "无（零危险原语）", len(allowed_dg), (a_rx - a_ast) == set(),
                    "" if not unallowed else " · ★未声明: %s" % unallowed)))

    # B 负例全部被拒（非空，且实测 rc != 0）
    negs = W.get("negatives", [])
    b_det, b_ok = [], len(negs) >= 2
    for nv in negs:
        rc, _o = _r006_run([_r006_sys.executable, _r006_os.path.abspath(__file__)] + list(nv))
        b_det.append("%s→rc%s" % (" ".join(nv), rc))
        if rc == 0:
            b_ok = False
    if not scanner_live:
        b_ok = False
    rows.append(("B", "负例全部被拒（≥2 条，实测 rc≠0）", b_ok, " · ".join(b_det) or "无负例"))

    # C 正例可用（防门太宽砍掉自己）
    # ★ 口径：合法输入必须被【受理并产出结果】。默认 rc==0；对「报告器」类工具，
    #   rc=1（报告有发现）是合法结果 —— 但须在 decl 里显式声明 expect_rc 并给出理由，
    #   不得拿它当免检口（否则 C 退化为空转）。rc∈{2,124,125} 一律算门失效。
    pos = W.get("positive", [])
    want_rc = W.get("positive_expect_rc", [0])
    c_ok, c_det = bool(pos), "无正例 ⇒ 不能判定"
    if pos:
        rc, _o = _r006_run([_r006_sys.executable, _r006_os.path.abspath(__file__)] + list(pos))
        c_ok = (rc in want_rc) and (rc not in (2, 124, 125))
        c_det = "%s → rc=%s（期望 %s）%s" % (" ".join(pos), rc, want_rc,
                                            "" if rc in want_rc else " · ★门太宽或用法被拒")
    if len(want_rc) > 1:
        c_det += " · 放宽理由：" + W.get("positive_expect_reason", "（未给理由 ⇒ 视为未声明）")
    rows.append(("C", "正例可用（防门太宽砍掉自己）", c_ok, c_det))

    # D 零变更
    d_ok, d_det, d_kind = _r006_dryrun_proof()
    rows.append(("D", "零变更（%s）" % d_kind, d_ok, d_det))

    # E 白名单冻结 + 写入面变更检测
    e_ok = (scanner_live and isinstance(W["frozen_write"], frozenset)
            and frozenset(sc["write"]) == frozenset(W["frozen_write"]))
    rows.append(("E", "写入面白名单冻结（frozenset + 变更即红）", e_ok,
                 "类型=%s · 元素=%d · 变更检测=on" % (type(W["frozen_write"]).__name__, len(W["frozen_write"]))))

    # F 外部命令白名单 + 别名逃逸检测
    f_ok = scanner_live and isinstance(W["frozen_exec"], frozenset) and frozenset(sc["exec"]) == frozenset(W["frozen_exec"])
    f_alias = "import subprocess as _sp" in _R006_SYNTH_EXEC and "subprocess.run" in syn_e
    rows.append(("F", "外部命令白名单（别名逃逸已覆盖 + 变更即红）", f_ok and f_alias,
                 "命令集=%s · 别名形式检出=%s" % (sorted(sc["exec"]) or "无", f_alias)))

    nf = [r for r in rows if not r[2]]
    print("== %s · --lean4-check（六项 A–F）==" % me)
    for k, nm, ok, dt in rows:
        print("  %s %s %-38s %s" % ("OK  " if ok else "FAIL", k, nm, dt))
    if vac:
        print("  ★ 反空洞控制未过：%s" % "; ".join(vac))
    print("\n  => %d/%d pass, %d FAIL" % (len(rows) - len(nf), len(rows), len(nf)))
    return 0 if not nf else 1


def _r006_sets():
    """诊断口：给出本器【实际】三面读数与冻结集，供注入器「先算后填」。"""
    sc = _r006_scan(_r006_src())
    print(_r006_json.dumps({
        "tool": _R006_DECL["tool"],
        "observed_exec": sorted(sc["exec"]), "frozen_exec": sorted(_R006_DECL["frozen_exec"]),
        "observed_write": sorted(sc["write"]), "frozen_write": sorted(_R006_DECL["frozen_write"]),
        "observed_danger": sorted(sc["danger"]), "frozen_danger": sorted(_R006_DECL["frozen_danger"]),
        "imports": sorted(sc["imports"]), "err": sc["err"],
    }, ensure_ascii=False, indent=2))
    return 0


def _r006_want(flag):
    """旗标本器是否被请求：既认当前 argv，也认【早期垫片】暂存的旗标。
    （垫片必须存在：本器可能在模块级就校验 argv，会先于本块把旗标当「不认识的参数」拒掉。）"""
    return (flag in _r006_sys.argv) or (flag in globals().get("_R006_EARLY_FLAGS", []))


if __name__ == "__main__" and _r006_want("--selfcheck"):
    _r006_sys.exit(_r006_selfcheck())

if __name__ == "__main__" and _r006_want("--lean4-check"):
    _r006_sys.exit(_r006_lean4_check())

if __name__ == "__main__" and _r006_want("--r006-sets"):
    _r006_sys.exit(_r006_sets())
# ══════════════════════════════ R006 块结束 ══════════════════════════════

if __name__ == "__main__":
    sys.exit(main())
