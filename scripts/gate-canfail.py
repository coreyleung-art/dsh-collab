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


if __name__ == "__main__":
    sys.exit(main())
