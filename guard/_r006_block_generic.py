
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
    """★ 供本工具覆盖：返回 (负例列表, 正例列表)；每项为 (名称, 实得布尔, 期望布尔)。

    ★ 缺省实现是**通用占位**（不依赖本工具判据）⇒ 工具**应当**覆盖它，
      用**本工具真实判据的纯函数部分**造输入 —— 否则 B/C 两项只验证了"布尔运算"，
      而没有验证"本门的判据能红"。★ 未覆盖时会在输出中提示。
    """
    return None


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
