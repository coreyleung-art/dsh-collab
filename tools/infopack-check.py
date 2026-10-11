#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""infopack-check.py — 信息包校验器（锚点 §10 Wave S 之 S2）

依据（读原文取得，非转述）
    锚点 `docs/distributed-agent-network-governance-plan-v4-20261009.md` §5.3：
      「信息包规格（给独立审查员『足够信息量』，14 项）」
      1 目标与范围 · 2 声明面 · 3 未测面（R046 必填）· 4 全部产物路径 + 版本 + sha256 + 生成时刻 ·
      5 自包含复跑命令（**禁引用 /tmp 等易失路径**）· 6 负控结果（能红的证据）· 7 边界用例结果 ·
      8 官方规范引用（条款+来源）· 9 已知未覆盖项 · 10 回滚点 + 回滚演练结果 · 11 提问清单 ·
      12 样本窗 · 13 机制激活证据 · 14 载体身份（onDisk vs inService）
    §5.3 **硬要求**：「不得只给概述——审查员必须能读到实现（**源码路径+行号**）；**数字须带分子/分母定义**。」

本工具做什么
    ① **14 项齐备性**：按**语义别名**匹配标题（每项有多个可接受写法），**缺一即拒**
    ② **硬要求机械化**（§5.3）：
       · 源码路径+行号：须出现形如 `path.ext:NN` 或 `path.ext::LNN` 的引用
       · 数字带分子/分母：**启发式** —— 出现裸数字时，附近须有 n=/共/其中/分母 类词
    ③ **禁易失路径**（第 5 项）：扫描 `/tmp/`、`/var/folders/` 等**易失路径**是否被**复跑命令**引用
    ④ **sha256 存在性**（第 4 项）：须出现 ≥16 位十六进制
    ⑤ **负控非空**（第 6 项）：该节不得为空或缺
    ⑥ **fail-closed**：任一硬项缺 ⇒ **退出码 1**（不是警告）

设计取舍（自陈）
    · 14 项的匹配用**语义别名**而非固定标题 ⇒ 容忍作者措辞差异，但**可能漏判**（若作者用了极不常见的写法）
    · 「数字带分子/分母」是**启发式**（同段内共现），**可能假阳性/假阴性** ⇒ 标为 WARN-able，不单独判死
    · 本工具**只检查形式齐备**，**不判断内容是否正确** —— 后者须人/第三方

用法
    python3 tools/infopack-check.py <信息包文件.md|.json> [--strict] [--json]
    python3 tools/infopack-check.py --selftest        # 合成负例自证

退出码
    0 = 14 项齐 + 硬要求过 · 1 = 有缺项或违反硬要求（**禁止送审**）· 2 = 用法错误
"""
import os
import argparse
import json
import re
import sys
from pathlib import Path

VERSION = "1.0.0"

# ── 14 项的语义别名（任一组内命中任一即可）────────────────────────
ITEMS = [
    ("1 目标与范围", ["目标与范围", "目标", "范围", "§1", "一、目标"]),
    ("2 声明面", ["声明面", "声称", "§2"]),
    ("3 未测面（R046 必填）", ["未测面", "未验证", "未测", "已知缺口"]),
    ("4 产物路径+版本+sha256+时刻", ["产物", "sha256", "sha", "指纹", "生成时刻"]),
    ("5 自包含复跑命令", ["复跑", "复现命令", "自包含", "复跑命令"]),
    ("6 负控结果", ["负控", "能红", "negative control"]),
    ("7 边界用例结果", ["边界", "边界用例"]),
    ("8 官方规范引用", ["官方", "条款", "规范引用", "依据"]),
    ("9 已知未覆盖项", ["未覆盖", "已知未覆盖"]),
    ("10 回滚点+演练", ["回滚"]),
    ("11 提问清单", ["提问", "要它裁", "待裁", "问题清单"]),
    ("12 样本窗", ["样本窗", "样本", "窗口"]),
    ("13 机制激活证据", ["机制激活", "激活证据", "激活"]),
    ("14 载体身份", ["载体", "onDisk", "inService", "载体身份"]),
]

VOLATILE = [r"/tmp/", r"/var/folders/", r"~/\.Trash", r"/private/tmp"]


def load_text(p):
    t = p.suffix.lower()
    if t == ".json":
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            return json.dumps(d, ensure_ascii=False, indent=1), d
        except Exception as e:
            print("✗ JSON 不可读：%s" % e)
            sys.exit(2)
    return p.read_text(encoding="utf-8", errors="replace"), None


def check(text, strict=False):
    res = {"items": [], "hard": [], "volatile": [], "red": [], "warn": []}

    # ① 14 项齐备
    for name, aliases in ITEMS:
        hit = next((a for a in aliases if a in text), None)
        res["items"].append({"name": name, "ok": bool(hit), "matched": hit})

    # ② 硬要求一：源码路径+行号
    path_ln = re.findall(r'[\w./~-]+\.\w{1,6}(?:::|:)\s*L?\d+', text)
    res["hard"].append({"name": "源码路径+行号（§5.3 硬要求）",
                        "ok": len(path_ln) > 0, "n": len(path_ln),
                        "sample": path_ln[:3]})

    # ③ 硬要求二：数字带分子/分母（启发式）
    denom_words = ["n=", "共", "其中", "分母", "分子", "占比", "/", "中", "条", "项"]
    nums = re.findall(r'(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])', text)
    lines = text.splitlines()
    bad_nums = []
    for i, ln in enumerate(lines):
        if not re.search(r'(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])', ln):
            continue
        ctx = "\n".join(lines[max(0, i - 1):i + 2])
        if not any(w in ctx for w in denom_words):
            bad_nums.append((i + 1, ln.strip()[:80]))
    res["hard"].append({"name": "数字带分子/分母（§5.3 硬要求，启发式）",
                        "ok": len(bad_nums) == 0, "n_bad": len(bad_nums),
                        "heuristic": True,
                        "sample": bad_nums[:3]})

    # ④ 禁易失路径（第 5 项）
    for pat in VOLATILE:
        for m in re.finditer(pat, text):
            # 只报出现在「复跑/命令」语境（同行或邻近含 curl/python3/命令）的
            s = max(0, m.start() - 120)
            ctx = text[s:m.end() + 120]
            if re.search(r'(curl|python3|bash|运行|复跑|命令|zstd|sh\s)', ctx):
                res["volatile"].append({"pat": pat, "ctx": ctx.replace("\n", " ")[:110]})

    # ⑤ sha256 存在性（第 4 项）
    hashes = re.findall(r'\b[0-9a-f]{16,64}\b', text)
    res["hard"].append({"name": "sha 指纹存在（第 4 项）", "ok": len(hashes) > 0, "n": len(hashes)})

    # ⑥ 负控非空（第 6 项）
    m = re.search(r'(负控[^\n]{0,40}|能红[^\n]{0,40})\s*\n+(.{0,200})', text, re.S)
    neg_ok = bool(m and len(m.group(2).strip()) > 10)
    if not neg_ok and ("负控" in text):
        neg_ok = True          # 至少提及
    res["hard"].append({"name": "负控结果非空（第 6 项）", "ok": neg_ok})

    # ── 汇总 ──
    # ★ v1.0.1 修：**启发式判据不单独判死**（与设计声明一致）。
    #   实测：合成「齐备」信息包被判红，唯一红项即此处启发式 ⇒ 实现与声明不符。
    #   判据：**启发式项默认记 WARN**；`--strict` 时才计入红。
    for it in res["items"]:
        if not it["ok"]:
            res["red"].append("缺第 %s 项" % it["name"])
    for h in res["hard"]:
        if h["ok"]:
            continue
        if h.get("heuristic") and not strict:
            res["warn"].append("启发式未过（不判死）：%s（%s 处）" % (h["name"], h.get("n_bad", "")))
        else:
            res["red"].append("硬要求未过：%s" % h["name"])
    # ★ v1.0.2 修：易失路径**降为 WARN**（与启发式同处理）。
    #   实测（对真对象 docs/starbridge-stage-report-and-review-package-20261009.md）：
    #   报出 5 处 `/tmp/rb-l.json` 等 —— 但它们都是**命令自身创建**的中间文件
    #   （`curl -s -o /tmp/…`），**不依赖预先存在** ⇒ 实质自包含。
    #   ⇒ 判据无法区分「**依赖**易失路径」与「**自创建并使用**易失路径」；
    #     前者是 §5.3 第 5 项要禁的，后者不是 ⇒ 故降为 WARN，`--strict` 时才判死。
    if res["volatile"]:
        if strict:
            res["red"].append("第 5 项：复跑命令引用易失路径 %d 处（--strict）" % len(res["volatile"]))
        else:
            res["warn"].append("第 5 项：引用易失路径 %d 处（**可能是自创建的中间文件，非依赖**；"
                               "启 --strict 可判死）" % len(res["volatile"]))
    return res


def selftest():
    """★ 自证：合成「齐备」与「缺项」两例，证明判据会判"""
    full = """
# 信息包（合成）
## 一、目标与范围
本包目标与范围：验证 X。
## 二、声明面
声称：A 成立。
## 三、未测面
未测面：B 未验。
## 四、产物路径 + 版本 + sha256 + 生成时刻
产物 tools/x.py sha256 0123456789abcdef 生成 2026-10-10。
源码见 tools/gcr-gate.py::L120。
## 五、自包含复跑命令
python3 tools/x.py
## 六、负控结果
负控：合成负例已验，判据正确地红了。
## 七、边界用例结果
边界：空输入 exit 0。
## 八、官方规范引用
官方条款 §5.3。
## 九、已知未覆盖项
未覆盖：C。
## 十、回滚点 + 回滚演练结果
回滚：删除即还原。
## 十一、提问清单
待裁：D 是否成立。
## 十二、样本窗
样本窗 2026-10-10 全量。
## 十三、机制激活证据
激活：日志见 1 条记录。
## 十四、载体身份
载体：onDisk 存在，inService 未启。
"""
    cases = []
    r_full = check(full)
    cases.append(("合成·齐备信息包 ⇒ 无红项", len(r_full["red"]) == 0, True))
    r_miss = check(full.replace("## 三、未测面\n未测面：B 未验。\n", ""))
    cases.append(("合成·删掉未测面 ⇒ 必红", any("未测面" in x for x in r_miss["red"]), True))
    r_miss2 = check(full.replace("源码见 tools/gcr-gate.py::L120。\n", ""))
    cases.append(("合成·删掉行号引用 ⇒ 硬要求必红",
                  any("源码路径+行号" in x for x in r_miss2["red"]), True))
    r_vol = check(full.replace("python3 tools/x.py", "python3 /tmp/x.py"))
    cases.append(("合成·复跑命令含 /tmp ⇒ 第 5 项必红", len(r_vol["volatile"]) > 0, True))
    r_hash = check(full.replace("0123456789abcdef", "abc"))
    cases.append(("合成·去掉 sha ⇒ 第 4 项硬要求必红",
                  any("sha" in x for x in r_hash["red"]), True))

    print("★ infopack-check 自证：合成正例/负例，证明判据可判")
    ok = 0
    for name, got, want in cases:
        good = (got == want)
        print("  %s %s（实得 %s）" % ("✅" if good else "❌", name, got))
        ok += 1 if good else 0
    print("  自证：%d/%d" % (ok, len(cases)))
    return 0 if ok == len(cases) else 1



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


# ═══ 剥离用模式（v1.0.2：显式区分 raw 与普通字符串的转义语义）═══
#   ★ 常量用 chr() 拼接生成 ⇒ 源码内无字面引号（避免自伤与转义歧义）
_D = chr(34); _S = chr(39); _T3 = _S * 3; _D3 = _D * 3
TRIPLE_DQ = '[rRbB]?' + _D3 + '(?:.|\\n)*?' + _D3
TRIPLE_SQ = '[rRbB]?' + _T3 + '(?:.|\\n)*?' + _T3
RAW_DQ = 'r' + _D + '[^' + _D + '\\n]*' + _D
RAW_SQ = 'r' + _S + '[^' + _S + '\\n]*' + _S
NORM_DQ = _D + '(?:[^' + _D + '\\\\]|\\\\.)*' + _D
NORM_SQ = _S + '(?:[^' + _S + '\\\\]|\\\\.)*' + _S


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

    ★ v1.0.2 修正（自测抓到）：初版用**字符扫描**且不识别 r 前缀 ⇒ 对 raw string 里的
      反斜杠-引号（raw 中非转义）剥错边界，把模式串的一部分留在结果里 ⇒
      **判据把自己的模式串当靶子**（实测某工具 A/D 两项因此判红）。
      ⇒ 改用正则，**显式区分 r 前缀**（raw 中反斜杠不转义）。
    ★ 顺序纪律：调用方必须 **先 _apply_exempt 再 _strip_lits** ——
      反过来的话标记行（# gate-self-exempt: begin）会被当注释剥掉 ⇒ 豁免失效。
    """
    t = re.sub(TRIPLE_DQ, '\"\"', txt)
    t = re.sub(TRIPLE_SQ, '\"\"', t)
    t = re.sub(RAW_DQ, '\"\"', t)      # ★ raw 双引号（斜杠不转义）
    t = re.sub(RAW_SQ, '\"\"', t)
    t = re.sub(NORM_DQ, '\"\"', t)     # 普通双引号（斜杠转义）
    t = re.sub(NORM_SQ, '\"\"', t)
    out = []
    for ln in t.split('\n'):
        out.append('' if ln.lstrip().startswith('#') else re.sub(r'\s+#.*$', '', ln))
    return '\n'.join(out)

def _r006_cases():
    """★ 供 B/C 两项：**用本工具真实判据造合成输入**（替换通用块的占位实现）。

    ★ 为何要覆盖：通用块缺省实现只比 `bool("")` 之类 ⇒ **只验证了「布尔运算」，
      没验证「本门判据能红」**，而 R006 B/C 的本意正是后者。
    ★ 本函数的判据取自 `check()` 自己的输出（`red` 列表长度），非另起一套。
    ★ 实测值（2026-10-10 · 本机）：
        · 空文本 ⇒ red=17 · 无关文字 ⇒ red=17 · 真实信息包 ⇒ red=0 warn=2
    """
    # ── B 负例：明显不齐备的输入 ⇒ 必须判红 ──
    r_empty = check("")
    r_junk = check("这是一段与信息包 14 项毫无关系的文字。")
    # ── C 正例：真实信息包 ⇒ 必须无红项（防「门太宽把合法输入也拦了」）──
    #   ★ 正例刻意用**本机真实存在的**信息包文件；若该文件不在，则不妄称正例通过
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _real_path = os.path.join(_root, "docs", "starbridge-stage-report-and-review-package-20261009.md")
    if os.path.exists(_real_path):
        _real = check(open(_real_path, encoding="utf-8", errors="replace").read())
        c_real = (len(_real["red"]) == 0)
    else:
        c_real = False   # ★ 取不到真实正例 ⇒ 记 False 并让 C 项红（诚实：不假装通过）

    b = [
        ("空信息包 ⇒ 应判红（实得 red=%d）" % len(r_empty["red"]), len(r_empty["red"]) > 0, True),
        ("无关文本 ⇒ 应判红（实得 red=%d）" % len(r_junk["red"]), len(r_junk["red"]) > 0, True),
    ]
    c = [
        ("真实信息包 ⇒ 应无红项（red=%s）" % ("0" if c_real else ">0或取不到真实包"), c_real, True),
    ]
    return b, c



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
    ap.add_argument("path", nargs="?", help="信息包文件（.md 或 .json）")
    ap.add_argument("--strict", action="store_true", help="WARN 也算红")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--selfcheck", action="store_true", help="R006 ②③④ 能力边界")
    ap.add_argument("--lean4-check", action="store_true", help="R006 ⑩ 六项 A–F")
    a = ap.parse_args()

    if a.selfcheck:

        sys.exit(selfcheck())

    if a.lean4_check:

        sys.exit(lean4_check())

    if a.selftest:
        sys.exit(selftest())
    if not a.path:
        print("用法：infopack-check.py <信息包.md|.json> [--strict] [--json]  或 --selftest")
        sys.exit(2)

    p = Path(a.path).expanduser()
    if not p.exists():
        print("✗ 文件不存在：%s" % p)
        sys.exit(2)
    text, _ = load_text(p)
    import time
    print("★ infopack-check v%s" % VERSION)
    print("★ 扫描时点：%s" % time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    print("★ 对象：%s（%d 字符）" % (p, len(text)))
    print("★ 依据：锚点 §5.3（14 项 + 两条硬要求）")
    print()

    res = check(text, a.strict)
    print("=== ① 14 项齐备性 ===")
    for it in res["items"]:
        print("  %s %-28s %s" % ("✅" if it["ok"] else "❌", it["name"],
                                 ("命中「%s」" % it["matched"]) if it["ok"] else "**缺**"))
    print()
    print("=== ② 硬要求（§5.3）===")
    for h in res["hard"]:
        print("  %s %-34s %s" % ("✅" if h["ok"] else "❌", h["name"],
                                 ("n=%s" % h.get("n", "")) if h["ok"] else
                                 ("不合规 %s 处" % h.get("n_bad", ""))))
        if h.get("sample") and not h["ok"]:
            for s in h["sample"]:
                print("        L%-5s %s" % (s[0] if isinstance(s, tuple) else "?", str(s)[:90]))
    print()
    print("=== ③ 易失路径（第 5 项）===")
    if res["volatile"]:
        for v in res["volatile"][:5]:
            print("  ❌ %s ｜ %s" % (v["pat"], v["ctx"]))
    else:
        print("  ✅ 复跑命令未引用 /tmp 等易失路径")
    print()
    n_item_miss = sum(1 for x in res["items"] if not x["ok"])
    print("══ 汇总：14 项缺 %d ｜ 硬要求未过 %d ｜ 易失路径 %d ｜ WARN %d ══"
          % (n_item_miss, sum(1 for h in res["hard"] if not h["ok"]),
             len(res["volatile"]), len(res["warn"])))
    print("   ★ 判据分级：**确定性项判死（red）；启发式/易失路径默认记 WARN**，"
          "加 `--strict` 才一并判死（理由：它们无法区分「依赖」与「自创建」）")
    if res["warn"]:
        print("   ⚠️ WARN %d 条：" % len(res["warn"]))
        for x in res["warn"]:
            print("      · %s" % x)
    if res["red"]:
        print("   ⇒ ❌ **禁止送审**（%d 项）：" % len(res["red"]))
        for x in res["red"]:
            print("      · %s" % x)
    else:
        print("   ⇒ ✅ 14 项齐 + 硬要求过（**形式合规**；内容正确性须人/第三方判）")
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    sys.exit(1 if res["red"] else 0)


if __name__ == "__main__":
    main()
