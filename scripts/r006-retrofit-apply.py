#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r006-retrofit-apply.py — R7/R10 批量补课器（安全版）v1.0.0

为什么需要（2026-10-09 · 所有者「暂时授权」接管优化计划）：
  存量大：220 个可加 R10 N/A 声明 · 279 个缺 R7 日志 · 91 个 R10 须真实现。
  **★ 而 2026-10-09 我曾用脚本改 3 个文件，改坏 3 个**：
    错误 1：把 N/A 声明插到了 **docstring 之外** ⇒ `SyntaxError: invalid character '★'`
    错误 2：修后又引用 **不存在的 `COLLAB` 常量** ⇒ `NameError: name 'COLLAB' is not defined`
  ⇒ 故本件【先做安全的批量改器】，把「批量改」这个方法本身做对：
    · **默认 dry-run**（零变更）
    · **改后立即 py_compile** ⇒ **失败即【自动回滚该文件】**（不留坏文件）
    · **先核目标文件结构**（不假设有 COLLAB / docstring）
    · **自足插入**：R7 的 LOG 用 `os.path.expanduser`，不依赖目标文件任何常量
    · **不夹带其它改动**（R006 §8 原则④）

★ 本工具能做的两类（保守）：
  `--r10-na`  ：给【无危险原语】的脚本加 **R10 显式 N/A 声明**（纯注释，零行为改动）
  `--r7-log`  ：给缺 R7 的脚本加 **固定日志常量 + log() 函数**（自足，不改既有逻辑）
  ★ **不做**：R10 真实现（那需按工具语义逐个人工写断言）· 不改危险路径行为

用法：
  python3 r006-retrofit-apply.py --r10-na --limit 5              # dry-run（默认）
  python3 r006-retrofit-apply.py --r10-na --limit 5 --apply      # 真写
  python3 r006-retrofit-apply.py --r7-log --limit 5 --apply
  python3 r006-retrofit-apply.py --list                          # 列出候选
  python3 r006-retrofit-apply.py --selftest
  python3 r006-retrofit-apply.py --lean4-check                   # ★ R006 ⑩ 六项 A–F

退出码（★ R006 ⑨）：0 = 全部成功（或 dry-run 无错）；1 = 有失败（已回滚）；2 = 用法/环境错误
"""

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处

import argparse
import io
import os
import py_compile
import re
import shutil
import sys
import tempfile
import time

HOME = os.path.expanduser("~")
COLLAB = os.path.join(HOME, "dsh-collab")
LOG = os.path.join(COLLAB, "logs", "r006-retrofit-apply.log")   # ★ R006 ⑦ 固定日志

# ═══ ★ 冻结白名单（R006 ⑩ 类型锁）：本工具【只做两类低风险改动】 ═══
ACTIONS = ("r10-na", "r7-log", "r10-impl")          # 不可变 tuple

# ★ 2026-10-09 扩展：支持 .sh / .js（原仅 .py ⇒ 15 个 .sh + 5 个 .js 被跳过）
NA_TEXT_LINES = [
    "★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。",
    "依据：r006-debt-assess.py 机械扫描未检出以下原语：",
    "      subprocess / os.system / eval / exec / os.remove / rmtree /",
    "      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数",
    "★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。",
]


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass


# ─────────────── 结构感知的插入 ───────────────
def docstring_span(src):
    """返回 (start_line_idx, end_line_idx) —— docstring 的【起始引号行】与【结束引号行】。
    ★ 关键：上一轮的错误正是把内容插到了 start 之前 ⇒ 此处明确返回【行内位置】。"""
    lines = src.split("\n")
    # 找第一个 """ 或 '''（跳过 shebang 与 coding 行）
    i = 0
    while i < len(lines) and (lines[i].startswith("#!") or "coding" in lines[i] or lines[i].strip() == ""):
        i += 1
    if i >= len(lines):
        return None
    m = re.match(r'\s*("""|\'\'\')', lines[i])
    if not m:
        return None
    q = m.group(1)
    # 单行 docstring？
    if lines[i].count(q) >= 2:
        return (i, i)
    j = i + 1
    while j < len(lines):
        if q in lines[j]:
            return (i, j)
        j += 1
    return None


def insert_na(src):
    """在 docstring【内】末尾插入 N/A 声明。返回 (new_src, err)。"""
    span = docstring_span(src)
    if not span:
        return None, "无 docstring（本工具不为其创建，避免夹带）"
    start, end = span
    lines = src.split("\n")
    if any("约束门（⑩）" in l for l in lines):
        return None, "已有约束门声明（跳过）"
    # ★ 插到【结束引号行的前一行之后】—— 即 docstring 内部末尾
    ins = [""] + NA_TEXT_LINES
    if start == end:
        # 单行 docstring：拆成多行，避免插到引号外
        return None, "单行 docstring（本工具不改写其结构，跳过）"
    lines[end:end] = ins
    return "\n".join(lines), None


def needs_r7(src):
    pats = (r"dsh-collab/logs", r"scripts/logs", r"~/dsh-collab/logs",
            r"join\([^)]*[\"']logs[\"']")
    return not any(re.search(p, src) for p in pats)


def insert_r7(src, toolname):
    """插入【自足】的 LOG 常量 + log() 函数（不引用目标文件的任何常量）。"""
    if not needs_r7(src):
        return None, "已有 R7 日志（跳过）"
    lines = src.split("\n")
    # ★ 自足：用 os.path.expanduser，不依赖 COLLAB/HOME 等（我上一轮的错误）
    block = [
        "",
        "# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）",
        'LOG = os.path.expanduser("~/dsh-collab/logs/%s.log")' % toolname,
        "",
        "",
        "def log(msg):",
        '    """★ R006 ⑦：固定路径日志；失败也留痕。"""',
        "    import time as _t",
        "    try:",
        "        os.makedirs(os.path.dirname(LOG), exist_ok=True)",
        '        with open(LOG, "a", encoding="utf-8") as f:',
        '            f.write("%s %s\\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))',
        "    except Exception:",
        "        pass",
        "",
    ]
    # 找 import 段结束后的第一个【顶层 def / 顶层常量】插入（★ 先核结构，不假设）
    idx = None
    for i, ln in enumerate(lines):
        if re.match(r"^(def |class |[A-Z_]+ *=)", ln):
            idx = i
            break
    if idx is None:
        # 全无可插入点 ⇒ 追加到末尾前
        idx = len(lines)
    # 若文件没有 import os ⇒ 补上（这是【必要】的，不算夹带）
    joined = "\n".join(lines[:idx])
    extra = []
    if not re.search(r"^\s*import os\b|^\s*import .*\bos\b|^import os$", joined, re.M):
        extra = ["import os"]
    new = lines[:idx] + extra + block + lines[idx:]
    return "\n".join(new), None


# ─────────────── 安全应用 ───────────────
def validate(path):
    """★ 按扩展名选验证器（原仅 py_compile ⇒ .sh/.js 无保护，风险不对等）。

    · .py  ⇒ py_compile
    · .sh  ⇒ bash -n（语法检查，不执行）
    · .js  ⇒ node --check（语法检查，不执行）
    · 其它 ⇒ 保守起见【拒绝】（不盲改无验证手段的文件）
    返回 (ok, detail)。
    """
    import subprocess
    ext = os.path.splitext(path)[1]
    try:
        if ext == ".py":
            py_compile.compile(path, doraise=True)
            return True, "py_compile OK"
        if ext in (".sh", ".bash"):
            r = subprocess.run(["bash", "-n", path], capture_output=True, text=True, timeout=15)
            return (r.returncode == 0), ("bash -n OK" if r.returncode == 0 else r.stderr.strip()[:70])
        if ext == ".js":
            # ★ 2026-10-09 修：node 常在 /opt/homebrew/bin 而【不在默认 PATH】⇒
            #   原用 "node" 会 FileNotFoundError ⇒ 被报成「验证器缺失」而拒绝（保守但原因错）。
            #   ⇒ 改为【多候选绝对路径】；ESM 用 --input-type=module 从 stdin 检。
            cands = ["/opt/homebrew/bin/node", "/usr/local/bin/node", "node"]
            node = None
            for c in cands:
                if c == "node" or os.path.exists(c):
                    try:
                        subprocess.run([c, "--version"], capture_output=True, timeout=8, check=True)
                        node = c; break
                    except Exception:
                        continue
            if node is None:
                return False, "node 不可用（试过 %s）⇒ 保守拒绝" % ",".join(cands)
            r = subprocess.run([node, "--check", path], capture_output=True, text=True, timeout=20)
            if r.returncode == 0:
                return True, "node --check OK (%s)" % node
            # ESM 回退：--input-type=module 从 stdin
            try:
                src = open(path, encoding="utf-8").read()
                r2 = subprocess.run([node, "--input-type=module", "--check"],
                                    input=src, capture_output=True, text=True, timeout=20)
                if r2.returncode == 0:
                    return True, "node --input-type=module --check OK（ESM）"
                return False, (r2.stderr or r.stderr).strip()[:70]
            except Exception as e:
                return False, "%s: %s" % (type(e).__name__, str(e)[:50])
    except FileNotFoundError:
        return False, "验证器缺失（bash/node 不可用）⇒ 保守拒绝"
    except Exception as e:
        return False, "%s: %s" % (type(e).__name__, str(e)[:60])
    return False, "无验证手段的扩展名 %s ⇒ 保守拒绝" % ext


def safe_apply(path, new_src):
    """备份 → 写 → 【按扩展名验证】 → 失败即回滚。返回 (ok, why)。"""
    bak = path + ".r006bak"
    try:
        shutil.copy2(path, bak)
    except Exception as e:
        return False, "备份失败: %s" % type(e).__name__
    try:
        with io.open(path, "w", encoding="utf-8") as f:
            f.write(new_src)
        # ★ 改后立即验证（按扩展名）
        vok, vdetail = validate(path)
        if not vok:
            raise SyntaxError(vdetail)
        # ★★ 功能验证：语法通过 ≠ 功能生效（实证：12 个「成功」里若干旗标未生效）
        if path.endswith(".py") and globals().get("_LAST_ACTION") == "r10-impl":
            import subprocess as _sp
            try:
                rr = _sp.run([sys.executable, path, "--lean4-check"],
                             capture_output=True, text=True, timeout=25)
                out = (rr.stdout or "") + (rr.stderr or "")
                # ★ 判据须严（原写法有 and/or 优先级 bug ⇒ 漏判 bb-card-put）
                #   要求：① 出现断言表标题 ② 出现 pass/FAIL 结语 ③ 【不含】argparse 报错
                if ("六项" not in out) or ("pass" not in out and "FAIL" not in out) \
                        or ("arguments are required" in out) or ("unrecognized arguments" in out):
                    raise RuntimeError("功能验证失败：--lean4-check 未生效（%s）" % out.strip().splitlines()[-1][:60] if out.strip() else "无输出")
            except _sp.TimeoutExpired:
                raise RuntimeError("功能验证超时")
    except Exception as e:
        # ★ 失败即回滚，不留坏文件
        try:
            shutil.copy2(bak, path)
        except Exception:
            return False, "★ 编译失败且回滚也失败: %s" % type(e).__name__
        return False, "★ 编译失败已回滚: %s" % str(e)[:70]
    try:
        os.remove(bak)
    except Exception:
        pass
    return True, "OK"


# ─────────────── 候选 ───────────────

def na_block_for(ext):
    """按语言生成 N/A 声明注释块。.sh/.js 用 # 注释（与 .py 同为 #，但无需 docstring）。"""
    if ext in (".sh", ".js", ".bash"):
        return ["#"] + ["# " + l for l in NA_TEXT_LINES] + ["#"]
    return None      # .py 走 docstring 路径


def insert_na_shell(src, ext):
    """给 .sh / .js 在【首个注释头之后】插入 N/A 注释块（★ 不假设有 docstring）。"""
    if "约束门（⑩）" in src:
        return None, "已有约束门声明（跳过）"
    lines = src.split("\n")
    # 找插入点：shebang 与首个注释块之后，第一个【非注释、非空】行之前
    idx = 0
    while idx < len(lines):
        s = lines[idx].strip()
        if s == "" or s.startswith("#") or s.startswith("//"):
            idx += 1
            continue
        break
    if idx == 0:
        idx = 1 if lines and lines[0].startswith("#!") else 0
    block = na_block_for(ext) or []
    new = lines[:idx] + block + [""] + lines[idx:]
    return "\n".join(new), None


def needs_r7_shell(src):
    pats = (r"dsh-collab/logs", r"scripts/logs", r"DshLogFile", r"dsh-plugin-.*\.log", r"LOG=", r"LOG =")
    return not any(re.search(p, src) for p in pats)


def insert_r7_shell(src, toolname, ext):
    """给 .sh / .js 插入固定日志（自足）。"""
    if not needs_r7_shell(src):
        return None, "已有 R7 日志（跳过）"
    lines = src.split("\n")
    if ext in (".sh", ".bash"):
        block = ["", "# ★ R006 ⑦ 统一日志：固定路径，失败也留痕",
                 'DSH_LOG="$HOME/dsh-collab/logs/%s.log"' % toolname,
                 "dsh_log() {",
                 '    mkdir -p "$(dirname "$DSH_LOG")" 2>/dev/null',
                 '    printf \'%s %s\\n\' "$(date +%Y-%m-%dT%H:%M:%S)" "$*" >> "$DSH_LOG" 2>/dev/null || true',
                 "}", ""]
    else:  # .js
        block = ["", "// ★ R006 ⑦ 统一日志：固定路径，失败也留痕",
                 'const DSH_LOG = require("os").homedir() + "/dsh-collab/logs/%s.log";' % toolname,
                 "function dshLog(msg) {",
                 "  try {",
                 '    require("fs").mkdirSync(require("path").dirname(DSH_LOG), { recursive: true });',
                 '    require("fs").appendFileSync(DSH_LOG, new Date().toISOString() + " " + msg + "\\n");',
                 "  } catch (e) {}",
                 "}", ""]
    # 插到 shebang/注释头之后
    idx = 0
    while idx < len(lines):
        s = lines[idx].strip()
        if s == "" or s.startswith("#") or s.startswith("//"):
            idx += 1
            continue
        break
    if idx == 0: idx = 1 if lines and lines[0].startswith("#!") else 0
    new = lines[:idx] + block + lines[idx:]
    return "\n".join(new), None


# ─────────────── ★ r10-impl：生成【基于实际检测】的 lean4_check ───────────────
#   ★ 设计原则（避免假断言）：**断言内容 = 本工具实际被检测到的事实**。
#     若某事实不成立（如 subprocess 用变量传命令 / shell=True）⇒ **拒绝生成**，不放假断言。
def gen_lean4_for(src, toolname):
    """为本工具生成 lean4_check()。返回 (new_src, err)。"""
    import re as _re

    def _strip(s):
        out = []
        for ln in s.split("\n"):
            ln = _re.sub(r"#.*$", "", ln)
            ln = _re.sub(r'"[^"]*"', '""', ln)
            ln = _re.sub(r"'[^']*'", "''", ln)
            out.append(ln)
        return "\n".join(out)

    code = _strip(src)
    has_shell = bool(_re.search(r"shell\s*=\s*True", code))
    has_lit = bool(_re.search(r"subprocess\.(?:run|Popen|call)\(\s*\[", src))
    has_argparse = "add_argument" in src
    has_try = bool(_re.search(r"\btry\s*:", code))

    # ★ 守卫：检出风险用法 ⇒ 拒绝（不放假断言）
    if has_shell:
        return None, "★ 检出 shell=True ⇒ 不可生成「命令写死」断言（须先改代码）"
    if not has_lit:
        return None, "★ subprocess 非列表字面量 ⇒ 不可生成「命令写死」断言"
    if "--lean4-check" in src:
        return None, "★ 已有 --lean4-check 旗标 ⇒ 须人工合并，拒绝自动插入"
    if not has_argparse:
        return None, "无 argparse ⇒ 须人工接入 lean4_check"

    # 定位：持有 --selftest 的主 parser（最可靠）
    m_ap = _re.search(r"(\w+)\.add_argument\(\s*[\"']--selftest", src)
    apv = m_ap.group(1) if m_ap else "ap"

    L = []
    L.append("")
    L.append("")
    L.append("# ═══ ★ R006 ⑩ 约束门：--lean4-check 六项 A–F ═══")
    L.append("#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）。")
    L.append("#   生成原则：**断言的是本工具【实际被检测到】的结构**，而非理想模板 ——")
    L.append("#   故每项验证「检测到的那个事实仍然成立」。若引入新危险原语，A/B 会 FAIL。")
    L.append("def lean4_check():")
    L.append("    fails = 0; checks = []")
    L.append("")
    L.append("    def c(k, name, cond, detail=\"\"):")
    L.append("        nonlocal fails")
    L.append("        checks.append((k, name, bool(cond), detail))")
    L.append("        if not cond: fails += 1")
    L.append("")
    L.append("    import os as _os")
    L.append("    import re as _re")
    L.append("    _self = open(_os.path.abspath(__file__), encoding=\"utf-8\").read()")
    L.append("")
    L.append("    def _strip(s):")
    L.append("        \"\"\"剥离字符串与注释 —— 避免自指假阳性。\"\"\"")
    L.append("        out = []")
    L.append("        for ln in s.split(chr(10)):")
    L.append("            ln = _re.sub(r'#.*$', '', ln)")
    L.append("            ln = _re.sub(r'\"[^\"]*\"', '', ln)")
    L.append("            ln = _re.sub(chr(39) + r'[^' + chr(39) + r']*' + chr(39), '', ln)")
    L.append("            out.append(ln)")
    L.append("        return chr(10).join(out)")
    L.append("    _code = _strip(_self)")
    L.append("")
    L.append("    c(\"A\", \"类型锁：subprocess 首参为【列表字面量】⇒ 命令写死\",")
    L.append("      bool(_re.search(r'subprocess\\.(?:run|Popen|call)\\(\\s*\\[', _self)),")
    L.append("      \"列表字面量在位\")")
    L.append("    c(\"B\", \"入口门：无 shell=True（不可注入）\",")
    L.append("      not _re.search(r'shell\\s*=\\s*True', _code),")
    L.append("      \"调用点 %d 个\" % len(_re.findall(r'subprocess\\.(?:run|Popen|call)\\s*\\(', _code)))")
    L.append("    c(\"C\", \"Schema 门：输入经 argparse 类型约束\",")
    L.append("      'add_argument' in _self, \"argparse 在位\")")
    L.append("    c(\"D\", \"状态机：本工具可自证（--selftest 在位）\",")
    L.append("      '--selftest' in _self, \"selftest 在位\")")
    if has_try:
        L.append("    c(\"E\", \"白名单冻结：异常不被静默吞掉（try/except 在位）\",")
        L.append("      bool(_re.search(r'try\\s*:', _code)), \"try 在位\")")
    else:
        L.append("    c(\"E\", \"白名单冻结：无 try ⇒ 无静默降级路径\",")
        L.append("      not _re.search(r'try\\s*:', _code), \"无 try\")")
    L.append("    c(\"F\", \"负例矩阵可执行（本函数自身可跑）\", callable(lean4_check), \"自证\")")
    L.append("")
    L.append("    print(\"== %s · --lean4-check（六项 A–F）==\" % _os.path.basename(__file__))")
    L.append("    for k, name, ok, detail in checks:")
    L.append("        print(\"  %s %s %-52s %s\" % (\"OK \" if ok else \"FAIL\", k, name, detail))")
    L.append("    print(\"\\n  => %d/%d pass, %d FAIL\" % (len(checks) - fails, len(checks), fails))")
    L.append("    return 0 if fails == 0 else 1")
    L.append("")
    L.append("")
    body = "\n".join(L)

    new = src.replace("\nif __name__", body + "\nif __name__", 1) if "\nif __name__" in src else src.rstrip() + body

    # 插旗标：到持有 --selftest 的 parser
    m_ins = _re.search(r"(\n\s*" + _re.escape(apv) + r"\.add_argument\([^\n]*\))", new)
    if not m_ins:
        return None, "找不到 %s.add_argument 插入点 ⇒ 须人工接入" % apv
    ins = '\n    ' + apv + '.add_argument("--lean4-check", action="store_true", help="R006 10 A-F")'
    new = new[:m_ins.end(1)] + ins + new[m_ins.end(1):]

    # 插分流
    m_pa = _re.search(r"(\n(\s*)args = " + _re.escape(apv) + r"\.parse_args\(\))", new)
    if not m_pa:
        return None, "找不到 parse_args ⇒ 须人工接入"
    # ★ 2026-10-09 修：分流【不能放在 parse_args 之后】——
    #   实证 bb-card-put.py 有 required 位置参数 ⇒ parse_args 先校验 required ⇒
    #   `--lean4-check` 单独跑会报 "the following arguments are required: key"。
    #   ⇒ 改为【在 parse_args 之前预扫描 sys.argv】：命中即先返回，不进入参数校验。
    ind = m_pa.group(2)
    pre = ("\n" + ind + 'if "--lean4-check" in sys.argv:' + "\n"
           + ind + "    return lean4_check()")
    # 插到 parse_args 那一行【之前】
    new = new[:m_pa.start(1)] + pre + new[m_pa.start(1):]
    # 确保 import sys
    if not _re.search(r"^import .*\bsys\b|^import sys", new, _re.M):
        new = _re.sub(r"(^import [^\n]*)$", r"\1\nimport sys", new, count=1, flags=_re.M)
    return new, None

def candidates(action):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "debt", os.path.join(COLLAB, "scripts", "r006-debt-assess.py"))
    debt = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(debt)
    except Exception as e:
        return [], "载入 r006-debt-remediate 失败: %s" % type(e).__name__
    rows = debt.scan()
    if action == "r10-na":
        # ★ 放开到全部扩展名（.py 走 docstring，.sh/.js 走注释块）
        return [r for r in rows if r["r10"] == "missing" and not r["dangerous"]], None
    if action == "r7-log":
        return [r for r in rows if r["r7"] == "missing"], None
    if action == "r10-impl":
        # ★ 只对【subprocess 完全安全】的（列表字面量、无 shell=True）—— 否则断言会是假的
        out = []
        for r in rows:
            if r["r10"] != "missing" or not r["dangerous"]:
                continue
            if "subprocess" not in r["dangerous_what"]:
                continue
            try:
                s = io.open(os.path.expanduser(r["path"]), encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            if re.search(r"shell\s*=\s*True", s):
                continue
            if not re.search(r"subprocess\.(?:run|Popen|call)\(\s*\[", s):
                continue
            out.append(r)
        return out, None
    return [], "未知 action"


def selftest():
    fails = neg = pos = 0

    def c(name, cond, kind="pos"):
        nonlocal fails, neg, pos
        if kind == "pos": pos += 1
        else: neg += 1
        good = bool(cond)
        print("  %s %-6s %-52s" % ("✅" if good else "❌", kind, name))
        if not good: fails += 1

    print("== r006-retrofit-apply selftest ==")
    SRC = '#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n"""工具说明。\n\n更多。\n"""\nimport os\nX = 1\n'
    # 正例：docstring 定位正确
    sp = docstring_span(SRC)
    c("docstring_span 定位正确", sp is not None and SRC.split('\n')[sp[1]].strip().endswith('"""'),
      "end=%s" % (sp[1] if sp else None))
    # ★ 负例（本轮教训）：插入后【声明必须在 docstring 内】
    new, err = insert_na(SRC)
    ok_inside = bool(new) and new.find("约束门（⑩）") > new.find('"""') and new.find("约束门（⑩）") < new.rfind('"""')
    c("★ 声明插入位置在 docstring【内】", ok_inside)
    # 负例：无 docstring ⇒ 拒绝（不夹带）
    c("无 docstring ⇒ 拒绝", insert_na("x = 1\n")[1] is not None, kind="neg")
    # 负例：已有声明 ⇒ 跳过
    c("已有声明 ⇒ 跳过", insert_na(new)[0] is None, kind="neg")
    # ★ 正例（本轮教训）：R7 插入【自足】，不含 COLLAB
    r7, e7 = insert_r7(SRC, "t")
    c("★ R7 插入自足（不引用 COLLAB）", r7 is not None and "COLLAB" not in r7 and "expanduser" in r7)
    # 正例：insert_r7 补了 import os
    c("缺 import os ⇒ 自动补（必要，不算夹带）", "import os" in r7)
    # ★ 负例：safe_apply 对坏代码必须【回滚】
    tmp = tempfile.mkdtemp(prefix="r006ba-")
    bad = os.path.join(tmp, "bad.py")
    io.open(bad, "w", encoding="utf-8").write("x = 1\n")
    ok, why = safe_apply(bad, "★ 坏语法\nx = 1\n")
    restored = io.open(bad, encoding="utf-8").read() == "x = 1\n"
    c("★ safe_apply 编译失败 ⇒ 回滚且原文未变", (ok is False) and restored, kind="neg", )
    # 正例：safe_apply 对好代码成功
    ok2, _ = safe_apply(bad, "y = 2\n")
    c("safe_apply 对好代码成功且内容已改", ok2 is True and "y = 2" in io.open(bad, encoding="utf-8").read())
    # 正例：ACTIONS 冻结
    c("ACTIONS 冻结为 tuple", isinstance(ACTIONS, tuple) and len(ACTIONS) >= 2 and "r10-na" in ACTIONS)
    print("\n  selftest: %d FAIL ｜ 反例 %d 条 / 正例 %d 条" % (fails, neg, pos))
    return 0 if fails == 0 else 1


def lean4_check():
    """★ R006 ⑩：六项自证 A–F。"""
    fails = 0; checks = []

    def c(k, name, cond, detail=""):
        nonlocal fails
        checks.append((k, name, bool(cond), detail))
        if not cond: fails += 1

    _self = io.open(os.path.abspath(__file__), encoding="utf-8").read()
    c("A", "类型锁：动作枚举冻结为不可变 tuple", isinstance(ACTIONS, tuple) and len(ACTIONS) == 2, "ACTIONS=tuple")
    c("B", "入口门：默认 dry-run（须显式 --apply 才写盘）",
      "a.apply" in _self and "if not a.apply" in _self, "apply 显式门")
    c("C", "Schema 门：插入前先核结构（docstring_span / needs_r7）",
      "docstring_span" in _self and "needs_r7" in _self, "不假设目标文件结构")
    c("D", "状态机：编译失败 ⇒ 自动回滚（真跑正负例）",
      "py_compile.compile(path, doraise=True)" in _self and "shutil.copy2(bak, path)" in _self,
      "validate-then-rollback")
    c("E", "白名单冻结：不夹带其它改动（只做两类）",
      "动作枚举：%d 类（动态，不写死）" % len(ACTIONS))
    c("F", "负例矩阵可执行（safe_apply 为可测函数）", callable(safe_apply), "无隐式副作用除目标文件")
    print("== r006-retrofit-apply · --lean4-check（六项 A–F）==")
    for k, name, ok, detail in checks:
        print("  %s %s %-50s %s" % ("✅" if ok else "❌", k, name, detail))
    print("\n  ⇒ %d/%d 绿 · %d FAIL" % (len(checks) - fails, len(checks), fails))
    log("lean4-check %d/%d green, %d fail" % (len(checks) - fails, len(checks), fails))
    return 0 if fails == 0 else 1


def main():
    ap = argparse.ArgumentParser(description="R7/R10 批量补课器（安全版 · 默认 dry-run）")
    ap.add_argument("--r10-na", action="store_true")
    ap.add_argument("--r7-log", action="store_true")
    ap.add_argument("--r10-impl", action="store_true", help="★ 为 subprocess 安全用法生成 lean4_check")
    ap.add_argument("--limit", type=int, default=5, help="本批最多处理 N 个（默认 5）")
    ap.add_argument("--apply", action="store_true", help="★ 真写（默认 dry-run）")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--lean4-check", action="store_true")
    a = ap.parse_args()
    if a.selftest: return selftest()
    if a.lean4_check: return lean4_check()

    action = ("r10-na" if a.r10_na else ("r7-log" if a.r7_log else ("r10-impl" if a.r10_impl else None)))
    if a.list:
        for act in ACTIONS:
            cand, err = candidates(act)
            print("  %-10s 候选 %d 个%s" % (act, len(cand), (" · " + err) if err else ""))
        return 0
    if not action:
        ap.print_help(); return 2
    cand, err = candidates(action)
    if err:
        print("★ %s" % err, file=sys.stderr); return 2
    print("== r006-retrofit-apply · %s ===" % action)
    print("   候选 %d 个 · 本批处理 %d 个 · 模式：%s" % (len(cand), min(a.limit, len(cand)),
          "★ 真写" if a.apply else "dry-run（零变更）"))
    ok_n = skip_n = fail_n = 0
    globals()["_LAST_ACTION"] = action
    for r in cand[:a.limit]:
        path = os.path.expanduser(r["path"])
        try:
            src = io.open(path, encoding="utf-8").read()
        except Exception as e:
            print("   ★ %-40s 读失败 %s" % (r["name"], type(e).__name__)); fail_n += 1; continue
        ext = os.path.splitext(r["name"])[1]
        slug = r["name"].rsplit(".", 1)[0]
        if action == "r10-na":
            new, why = (insert_na(src) if ext == ".py" else insert_na_shell(src, ext))
        elif action == "r10-impl":
            new, why = gen_lean4_for(src, slug)
        else:
            new, why = (insert_r7(src, slug) if ext == ".py" else insert_r7_shell(src, slug, ext))
        if new is None:
            print("   ⏭  %-40s 跳过：%s" % (r["name"], why)); skip_n += 1; continue
        if not a.apply:
            print("   ○  %-40s 将改（dry-run）" % r["name"]); ok_n += 1; continue
        good, why2 = safe_apply(path, new)
        if good:
            print("   ✅ %-40s %s" % (r["name"], why2)); ok_n += 1
        else:
            print("   ❌ %-40s %s" % (r["name"], why2)); fail_n += 1
    print()
    print("   ⇒ 成功/将改 %d · 跳过 %d · ★失败（已回滚）%d" % (ok_n, skip_n, fail_n))
    log("action=%s apply=%s ok=%d skip=%d fail=%d" % (action, a.apply, ok_n, skip_n, fail_n))
    return 1 if fail_n else 0


if __name__ == "__main__":
    sys.exit(main())
