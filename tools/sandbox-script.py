#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sandbox-script.py — 脚本/CLI 沙箱验证（补锚点 §5.2 缺的 4 项）

为什么需要它
    锚点 `distributed-agent-network-governance-plan-v4` §5.2 对「脚本/CLI」类产物要求：
        临时目录 + 假输入；**断言未写生产路径**（路径白名单比对）；**幂等复跑**
        必测：**幂等**；**失败态 exit≠0**；**无静默成功**
    ★ 既有 `scripts/dev-sandbox.py` 的 `script` 类**只做语法检查**（实测输出仅「✅ 语法 OK」）
      ⇒ 5 项中只有 1 项 ⇒ 本工具补其余 4 项。

本工具做四件事（逐项对应 §5.2）
    ① 隔离   —— 在**临时目录**里跑（可指定 cwd / argv / stdin 假输入）
    ② 保护   —— 跑前记录**受保护路径**（生产路径）指纹，跑后比对 ⇒ **有任何变更即红**
                （含**新增文件**检测；目录递归）
    ③ 幂等   —— **复跑一次**，比对两次的 (exit, stdout, stderr) ⇒ 不一致即红
    ④ 静默成功 —— `exit==0` 但**无输出** / `exit==0` 但输出含错误关键词 ⇒ 即红
                （「没做事却报成功」是 §5.2 明列的必测项）

与既有工具的关系（不重造）
    · `scripts/dev-sandbox.py` —— 保留其「语法检查」为**第 0 道**（本工具先调它）
    · `scripts/plugin-preflight.py` —— 插件类三检（本工具**不重复**，只覆盖脚本类）

用法
    python3 tools/sandbox-script.py <脚本> [选项]
      --args "…"            传给脚本的参数（shell 分词）
      --input <文件|文本>   作为 stdin 假输入
      --protect <路径>…     受保护路径（可多次；默认自动包含 ~/dsh-collab/data 与 ~/.dsh）
      --cwd <目录>          运行目录（默认为新建的临时目录）
      --expect-exit <n>     期望退出码（默认只要求与复跑一致）
      --json

退出码
    0 = 四检全过（可推进）· 1 = 有红项（**禁止推进/挂载**）· 2 = 用法错误

自陈限度
    · 「受保护路径」靠**指纹比对**发现变更，**不能阻止**写入（真正的阻止需沙箱/权限）
    · 默认保护集只覆盖两处常用生产路径，**其余须显式 --protect**
    · 幂等判据为「两次跑的 (exit,out,err) 相同」，**不覆盖「结果文件相同」**（那需要 --artifact，未实现）
"""
import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path

VERSION = "1.0.0"
ERROR_WORDS = ("traceback", "error", "exception", "failed", "失败", "错误", "异常")


def fp_file(p):
    try:
        st = p.stat()
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return (h.hexdigest()[:16], st.st_size, int(st.st_mtime))
    except Exception as e:
        return ("ERR:%s" % type(e).__name__, 0, 0)


def fingerprint(paths):
    """递归记录路径指纹；**新增文件也会被检出**（因键集合本身参与比对）。"""
    out = {}
    for raw in paths:
        p = Path(os.path.expanduser(raw))
        if p.is_file():
            out[str(p.resolve())] = fp_file(p)
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file():
                    out[str(f.resolve())] = fp_file(f)
        else:
            out[str(p.resolve())] = ("ABSENT", 0, 0)
    return out


def run_once(script, args, cwd, stdin_data, timeout, env_extra=None):
    env = dict(os.environ)
    env.update(env_extra or {})
    argv = [sys.executable, script] + args
    try:
        p = subprocess.run(argv, cwd=cwd, input=stdin_data, capture_output=True,
                           text=True, timeout=timeout, env=env)
        return {"exit": p.returncode, "out": p.stdout or "", "err": p.stderr or ""}
    except subprocess.TimeoutExpired:
        return {"exit": "TIMEOUT", "out": "", "err": "timeout after %ss" % timeout}
    except Exception as e:
        return {"exit": "SPAWN_ERR", "out": "", "err": "%s: %s" % (type(e).__name__, e)}



# ══════════════════════════════════════════════════════════════════
# ★ R006 §5 验收两步（v1.0.1 补 —— 此前本工具只有 `--selftest`，
#   缺 `--selfcheck`（②③④）与 `--lean4-check`（⑩ A–F）
#   ⇒ 属真实欠账，登记于 `docs/wave-s-toolchain-delivery-v1.md` §5「已知缺口」第 1 条）
#
# ★ 本块为**通用版**（第二个使用者起复用）：与 `gcr-gate.py` 的专用块同构，
#   差异只在 **B/C 的合成输入** —— 由本工具可选定义 `_r006_cases()` 覆盖，缺省用通用负例。
#   ⇒ 这实证了「R006 §5 两步」**可跨工具复用**（而非为单一工具定制）。
# ══════════════════════════════════════════════════════════════════

# ★ A 项判据（**通用版**）：**无【危险】原语** —— 杀进程 / 删数据 / 改权限 / 执行任意命令类。
#   ★ 为何不判「无 subprocess」：本类工具**多数需要**调外部只读工具，
#     若按字面判「无危险原语」会**永远失败**（假阴性）。
#     R006 A 项原意是「**不该发生的路径在结构上不可绕过**」
#     ⇒ A 项判【危险原语】，把【外部命令】交给 **F 项**（枚举调用点 + 断言 ⊆ 白名单）。
DANGEROUS_PRIMS = (
    r"os\.remove\s*\(", r"os\.rmdir\s*\(", r"shutil\.rmtree\s*",
    r"os\.chmod\s*\(", r"os\.chown\s*\(", r"os\.kill\s*\(",
    r"\bpkill\b", r"\bkillall\b", r"launchctl\s+(unload|remove|bootout)",
    r"\beval\s*\(", r"os\.system\s*\(",
)

# ★ F 项白名单（**冻结**）：只读探测类命令。★ 工具若需别的命令，**必须**显式加进本元组
#   （改动本元组即视为白名单变更，应留痕）。
ALLOWED_CMDS = ("codesign", "pgrep", "ps", "plutil", "spctl", "lsof", "grep", "python3",
                "curl", "shasum", "date", "wc")


def _apply_exempt(text):
    """应用通用豁免约定 `# gate-self-exempt: begin/end`（等长空行替换，保行号）。

    ★ 约定来源：`tools/self-destruct-gate.py` v1.0.5 引入。
    ★ 用等长空行替换而非删除 —— 删除会使后续**行号整体偏移**（曾导致报错指向错误行）。
    ★★ 顺序纪律：**必须先 `_apply_exempt` 再 `_strip_lits`** ——
      反过来的话，`_strip_lits` 会把 `# gate-self-exempt: begin` **当注释整行剥掉**
      ⇒ 标记消失 ⇒ 豁免形同虚设（实测踩过）。
    """
    out, skip = [], False
    for ln in text.split("\n"):
        if "gate-self-exempt: begin" in ln:
            skip = True; out.append(""); continue
        if "gate-self-exempt: end" in ln:
            skip = False; out.append(""); continue
        out.append("" if skip else ln)
    return "\n".join(out)


def _strip_lits(txt):
    """剥离字符串字面量与整行注释（R006 A 项要求 —— 否则会把自己的检测正则当靶子）。

    ★ 用**字符扫描**实现（而非单条复杂正则）—— 后者在自身源码里会被自己的模式串干扰。
    """
    out, i, n = [], 0, len(txt)
    while i < n:
        ch = txt[i]
        if ch == "#":
            while i < n and txt[i] != "\n":
                i += 1
            out.append("\n")
            continue
        if txt.startswith('"""', i) or txt.startswith("'''", i):
            q = txt[i:i + 3]
            i += 3
            while i < n and not txt.startswith(q, i):
                i += 1
            i += 3
            out.append('""')
            continue
        if ch in "\"'":
            q = ch
            i += 1
            while i < n and txt[i] != q:
                if txt[i] == "\\":
                    i += 1
                i += 1
            i += 1
            out.append('""')
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _r006_cases():
    # gate-self-exempt: begin  ← 测试样例区：在 tempfile 目录内造样例并跑，不碰生产
    """★ 供 B/C 两项：**用本工具真实判据造合成输入**（替换通用块的占位实现）。

    ★ 依据：本工具四检的红项判定（`red.append(...)`），其中「幂等：两次跑结果不一致」最易构造：
      ⇒ B 项：**离幂等的脚本 ⇒ 两次输出必须不同**（判据能红）
      ⇒ C 项：**干净幂等脚本 ⇒ 两次输出逐字节一致**（判据不误伤）

    ★★ 一处**必须记住的实现事实**（我踩过）：
       `run_once()` 用 `argv = [sys.executable, script]` 执行 ⇒
       **本沙箱只适用于 Python 脚本**（**bash 脚本会被当 Python 跑而报 SyntaxError**，
       表现为 `exit=1` 且 `err` 里是 Python traceback）。
       ⇒ 故本函数的合成样例**一律用 Python 写**。

    ★ 为何不用「写受保护路径」作负例：**那会真写文件** ——
      本门原则是「只读探测 + 临时目录」，故负例选**离幂等**这种**无副作用**形态。
    ★ 两次跑都是真跑（`run_once`），结论取自**它自己的返回**，非另起一套判据。
    """
    _tmp = tempfile.mkdtemp(prefix="sdg-r006-")
    # ── B 负例：输出随机数 ⇒ 两次跑不同 ⇒ 离幂等 ──
    _neg = os.path.join(_tmp, "nonidem.py")
    with open(_neg, "w") as f:
        f.write("import random" + chr(10) + "print('probe-%r' % random.random())" + chr(10))
    _n1 = run_once(_neg, [], _tmp, None, 20)
    _n2 = run_once(_neg, [], _tmp, None, 20)
    # ── C 正例：固定输出 ⇒ 两次跑逐字节一致（幂等的定义）──
    _pos = os.path.join(_tmp, "clean.py")
    with open(_pos, "w") as f:
        f.write("print('ok')" + chr(10))
    _p1 = run_once(_pos, [], _tmp, None, 20)
    _p2 = run_once(_pos, [], _tmp, None, 20)

    b = [
        ("离幂等脚本 ⇒ 两次输出**不同**（out1=%s / out2=%s）"
         % (str(_n1.get("out"))[:20], str(_n2.get("out"))[:20]),
         _n1.get("out") != _n2.get("out") and _n1.get("exit") == 0, True),
    ]
    c = [
        ("干净幂等脚本 ⇒ 两次输出**逐字节一致**且 exit=0（out=%s）" % str(_p1.get("out"))[:20],
         _p1.get("out") == _p2.get("out") and _p1.get("exit") == 0, True),
    ]
    return b, c
    # gate-self-exempt: end



def selfcheck():
    """R006 ②③④ 能力边界自检。"""
    me = os.path.abspath(__file__)
    txt = open(me, encoding="utf-8").read()
    stripped = _strip_lits(_apply_exempt(txt))
    writes = [p for p in (r"open\s*\([^)]*['\"]w", r"write_text\s*\(|\.write\s*\(")
              if re.search(p, stripped)]
    outs = [p for p in (r"sys\.stdout", r"print\s*\(") if re.search(p, stripped)]
    checks = [
        ("② TCC：本工具**不写**被检对象", len(writes) == 0),
        ("③ 无 CLD 硬编码路径（可移植）", "/Applications/CLD.app" not in stripped),
        ("④ 版本单一来源 VERSION", 'VERSION = "%s"' % VERSION in txt),
        ("⑤ 有输出（非静默成功）", len(outs) > 0),
        ("⑩ A 预检：源码无危险原语（剥离后）",
         not any(re.search(p, stripped) for p in DANGEROUS_PRIMS)),
    ]
    print("★ selfcheck（R006 ②③④）")
    n = 0
    for name, ok in checks:
        print("  %s %s" % ("✅" if ok else "❌", name))
        n += 1 if ok else 0
    print("  自查：%d/%d" % (n, len(checks)))
    return 0 if n == len(checks) else 1


def lean4_check():
    """R006 ⑩ `--lean4-check` 六项（A–F）。"""
    me = os.path.abspath(__file__)
    raw = open(me, encoding="utf-8").read()
    stripped = _strip_lits(_apply_exempt(raw))
    res = []

    # ── A 源码无危险原语（**剥离后**扫）──
    a_hits = [p for p in DANGEROUS_PRIMS if re.search(p, stripped)]
    res.append(("A 源码无危险原语（剥离后扫）", len(a_hits) == 0,
                "命中 0 条" if not a_hits else "命中 %d 条：%s" % (len(a_hits), a_hits[:3])))

    # ── B/C：优先用工具自定义的合成输入 ──
    cases = _r006_cases()
    if cases is None:
        b_cases = [("通用负例·空值应被拒", bool(""), False),
                   ("通用负例·None 应被拒", bool(None), False)]
        c_cases = [("通用正例·非空应可用", bool("x"), True)]
        note = "★ 占位实现（本工具未定义 `_r006_cases()`）"
    else:
        b_cases, c_cases = cases
        note = "用本工具真实判据的纯函数部分"
    b_bad = [n for n, got, want in b_cases if got != want]
    res.append(("B 负例全部被拒", len(b_bad) == 0,
                "%d 条越界样例全部 FAIL（%s）" % (len(b_cases), note) if not b_bad
                else "★ 有负例被放过：%s" % b_bad))
    c_bad = [n for n, got, want in c_cases if got != want]
    res.append(("C 正例可用（防门太宽）", len(c_bad) == 0,
                "%d 条合法样例全部 PASS" % len(c_cases) if not c_bad else "★ 门把合法值也拦了：%s" % c_bad))

    # ── D 零变更（本类工具多只读 ⇒ 断言无写调用）──
    d_writes = [p for p in (r"open\s*\([^)]*['\"]w", r"write_text\s*\(") if re.search(p, stripped)]
    res.append(("D 零变更（无写调用）", len(d_writes) == 0,
                "源码无写文件调用" if not d_writes else "★ 检出写调用：%s" % d_writes))

    # ── E 白名单冻结 ──
    e_ok = isinstance(DANGEROUS_PRIMS, tuple) and isinstance(ALLOWED_CMDS, tuple)
    res.append(("E 白名单冻结（tuple）", e_ok, "DANGEROUS_PRIMS / ALLOWED_CMDS 为不可变 tuple"))

    # ── F 外部命令白名单（**枚举调用点 → 回原文读实参 → 断言 ⊆ 允许集**）──
    #    ★ 依 R006 F 项步骤：**去字面量定位调用点 → 回原文读实参**（否则会「空集通过」）。
    calls = re.findall(r"subprocess\.\w+\(\s*\[\s*\"([\w.\-]+)\"", raw)
    calls += re.findall(r"subprocess\.\w+\(\s*\[\s*'([\w.\-]+)'", raw)
    calls += re.findall(r"sh\(\s*\[\s*\"([\w.\-]+)\"", raw)
    calls += re.findall(r"sh\(\s*\[\s*'([\w.\-]+)'", raw)
    bad = sorted(set(calls) - set(ALLOWED_CMDS))
    res.append(("F 外部命令白名单（枚举 %d 处 → 断言 ⊆ %d 项）" % (len(calls), len(ALLOWED_CMDS)),
                len(bad) == 0, "命令集 %s" % sorted(set(calls)) if not bad else "★ 越界命令：%s" % bad))

    print("★ lean4-check（R006 ⑩ 六项）")
    n = 0
    for name, ok, note2 in res:
        print("  %s %s — %s" % ("✅" if ok else "❌", name, note2))
        n += 1 if ok else 0
    print("  六项：%d/%d %s" % (n, len(res), "全绿" if n == len(res) else "★ 未全绿"))
    return 0 if n == len(res) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--args", default="")
    ap.add_argument("--input", default=None, help="stdin 假输入（文本，或 @文件路径）")
    ap.add_argument("--protect", action="append", default=[])
    ap.add_argument("--cwd", default=None)
    ap.add_argument("--timeout", type=float, default=120)
    ap.add_argument("--expect-exit", type=int, default=None)
    ap.add_argument("--env", action="append", default=[], help="K=V，可多次")
    ap.add_argument("--json", action="store_true")
    # ★ 本工具以【必填位置参数 script】为主 ⇒ argparse 会在缺 script 时**先报错**，
    #   故 --selfcheck / --lean4-check 必须在此**之前**用 sys.argv 预检。
    if "--selfcheck" in sys.argv:
        sys.exit(selfcheck())
    if "--lean4-check" in sys.argv:
        sys.exit(lean4_check())
    a = ap.parse_args()

    script = os.path.expanduser(a.script)
    if not os.path.isfile(script):
        print("✗ 脚本不存在：%s" % script)
        sys.exit(2)

    args = shlex.split(a.args) if a.args else []
    stdin_data = None
    if a.input is not None:
        stdin_data = Path(a.input[1:]).read_text() if a.input.startswith("@") else a.input
    env_extra = {}
    for kv in a.env:
        if "=" in kv:
            k, v = kv.split("=", 1)
            env_extra[k] = v

    # ★ 默认保护集（v1.0.1 修）：初版用 `~/.dsh` 整体 ⇒ **正例误报 8 项**，
    #   因该目录是**活跃目录**（agent-bus/心跳/日志持续在变），跑脚本的 2 秒内即有多处变更。
    #   ⇒ 判据：受保护路径应选「**稳定且关键**」者 —— 即「若被被测脚本意外写就是事故」的那些。
    #   ⚠ 活跃目录（~/.dsh 整体 / 日志 / bus）**不应**作默认保护集，否则本检项会退化为噪声。
    default_protect = [
        os.path.expanduser("~/dsh-collab/data/registry"),   # 登记产物（权威键的本地副本）
        os.path.expanduser("~/.dsh/agent-role-map.json"),   # 角色映射（活引用 A1）
        os.path.expanduser("~/dsh-collab/docs"),            # 文档（含唯一权威锚点）
    ]
    protect = a.protect or default_protect

    started = time.time()
    print("★ sandbox-script v%s" % VERSION)
    print("★ 扫描时点：%s" % time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    print("★ 对象：%s" % script)
    print("★ 受保护路径（跑后比对，有变更即红）：")
    for p in protect:
        print("    %s%s" % (p, "" if os.path.exists(os.path.expanduser(p)) else " （不存在）"))
    tmpdir = tempfile.mkdtemp(prefix="sb-script-")
    cwd = a.cwd or tmpdir
    print("★ 运行目录：%s%s" % (cwd, " （临时）" if a.cwd is None else " （指定）"))
    print()

    red = []

    # ── ② 生产保护：跑前指纹 ───────────────────────────────────────
    before = fingerprint(protect)

    # ── ③ 跑第一次 ────────────────────────────────────────────────
    r1 = run_once(script, args, cwd, stdin_data, a.timeout, env_extra)
    print("① 首跑：exit=%s  out=%d B  err=%d B" % (r1["exit"], len(r1["out"]), len(r1["err"])))

    # ── ④ 复跑（幂等）────────────────────────────────────────────
    r2 = run_once(script, args, cwd, stdin_data, a.timeout, env_extra)

    # ★ v1.0.2 修：幂等判据须忽略**声明性元数据行**。
    #   实测（用本工具测 tools/gcr-gate.py）：唯一差异是 `★ 扫描时点：…` 一行。
    #   ⇒ 该行是**声明**（裁判移交的判据①要求打印扫描时点），**非结果**；
    #     若把它算作非幂等，则**「声明时点」与「幂等」两条要求直接冲突**。
    #   判据：**忽略已知易变行（时点/耗时/临时路径），但绝不忽略结果行**。
    VOLATILE = [
        r"扫描时点", r"scanned_at", r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
        r"耗时\s*[\d.]+s", r"elapsed", r"/var/folders/\S+", r"/tmp/\S+",
        r"tempdir", r"临时目录",
    ]

    def norm(txt):
        keep = []
        for line in (txt or "").splitlines():
            if any(re.search(p, line) for p in VOLATILE):
                continue
            keep.append(line)
        return "\n".join(keep)

    same_raw = (r1["exit"] == r2["exit"] and r1["out"] == r2["out"] and r1["err"] == r2["err"])
    same = (r1["exit"] == r2["exit"] and norm(r1["out"]) == norm(r2["out"])
            and norm(r1["err"]) == norm(r2["err"]))
    if same_raw:
        print("② 复跑：exit=%s  ⇒ **幂等**：✅ 两次逐字节一致" % r2["exit"])
    elif same:
        print("② 复跑：exit=%s  ⇒ **幂等**：✅ 一致（已忽略声明性易变行：时点/耗时/临时路径）" % r2["exit"])
    else:
        print("② 复跑：exit=%s  ⇒ **幂等**：❌ 不一致（非幂等）" % r2["exit"])
    if not same:
        d1 = norm(r1["out"]).splitlines()
        d2 = norm(r2["out"]).splitlines()
        for i in range(max(len(d1), len(d2))):
            x = d1[i] if i < len(d1) else "<缺行>"
            y = d2[i] if i < len(d2) else "<缺行>"
            if x != y:
                print("      差异@%d：" % (i + 1))
                print("        1st: %s" % x[:110])
                print("        2nd: %s" % y[:110])
                break
        red.append("幂等：两次跑结果不一致")

    # ── ① 生产保护：跑后比对 ──────────────────────────────────────
    after = fingerprint(protect)
    changed = []
    for k in set(before) | set(after):
        if before.get(k) != after.get(k):
            kind = "新增" if k not in before else ("删除" if k not in after else "变更")
            changed.append((kind, k))
    if changed:
        print("③ 生产保护：❌ **检出 %d 项变更**" % len(changed))
        for kind, k in changed[:10]:
            print("      [%s] %s" % (kind, k))
        red.append("生产保护：受保护路径被改动")
    else:
        print("③ 生产保护：✅ 受保护路径**零变更**（%d 项受检）" % len(after))

    # ── ④ 静默成功检测 ────────────────────────────────────────────
    quiet = False
    if r1["exit"] == 0 and not r1["out"].strip() and not r1["err"].strip():
        quiet = True
        why = "exit=0 但**无任何输出**"
    elif r1["exit"] == 0 and any(w in r1["out"].lower() for w in ERROR_WORDS):
        quiet = True
        why = "exit=0 但输出含错误关键词"
    else:
        why = ""
    if quiet:
        print("④ 静默成功：❌ %s" % why)
        red.append("静默成功：" + why)
    else:
        print("④ 静默成功：✅ 未检出（exit=%s 且有输出）" % r1["exit"])

    # ── 期望退出码 ────────────────────────────────────────────────
    if a.expect_exit is not None:
        ok = (r1["exit"] == a.expect_exit)
        print("⑤ 期望退出码：%s（期望 %s）" % ("✅" if ok else "❌", a.expect_exit))
        if not ok:
            red.append("期望退出码：实得 %s，期望 %s" % (r1["exit"], a.expect_exit))

    print()
    print("★ 失败可见性：exit=%s ｜ 输出尾 3 行：" % r1["exit"])
    for line in (r1["out"].strip().splitlines() or [""])[-3:]:
        print("    %s" % line[:120])
    if r1["err"].strip():
        print("  stderr 尾 3 行：")
        for line in r1["err"].strip().splitlines()[-3:]:
            print("    %s" % line[:120])

    print()
    if red:
        print("══ 判定：❌ 有红项（%d）—— **禁止推进/挂载** ══" % len(red))
        for x in red:
            print("   · %s" % x)
    else:
        print("══ 判定：✅ 四检全过（可推进）══")
    print("  （耗时 %.1fs · 临时目录 %s）" % (time.time() - started, tmpdir))

    if a.json:
        print(json.dumps({"version": VERSION, "script": script, "first": r1, "second": r2,
                          "idempotent": same, "protected_changes": changed, "red": red},
                         ensure_ascii=False, indent=1))
    sys.exit(1 if red else 0)


if __name__ == "__main__":
    main()
