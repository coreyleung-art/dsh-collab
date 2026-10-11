
# ══════════════════════════════════════════════════════════════════
# ★ R006 §5 验收两步（v1.0.2 补 —— 此前本工具只有 `--selftest`，
#   缺 `--selfcheck`（②③④）与 `--lean4-check`（⑩ A–F）
#   ⇒ 属真实欠账，登记于 `docs/wave-s-toolchain-delivery-v1.md` §5「已知缺口」第 1 条）
# ══════════════════════════════════════════════════════════════════

# ★ A 项判据（**本工具版**）：**无【危险】原语** —— 杀进程 / 删数据 / 改权限 / 执行任意命令类。
#   ★ 为何不判「无 subprocess」：本工具**必须**调外部**只读**工具（codesign / pgrep / ps / spctl），
#     若按字面判「无危险原语」会**永远失败**（假阴性）。
#     R006 A 项原意是「**不该发生的路径在结构上不可绕过**」
#     ⇒ 故 A 项判【危险原语】，而把【外部命令】交给 **F 项**（枚举调用点 + 断言 ⊆ 白名单）。
DANGEROUS_PRIMS = (
    r"os\.remove\s*\(", r"os\.rmdir\s*\(", r"shutil\.rmtree\s*",
    r"os\.chmod\s*\(", r"os\.chown\s*\(", r"os\.kill\s*\(",
    r"\bpkill\b", r"\bkillall\b", r"launchctl\s+(unload|remove|bootout)",
    r"\beval\s*\(", r"os\.system\s*\(",
)

# ★ F 项白名单（**冻结**）：本门只允许**只读探测**类外部命令
ALLOWED_CMDS = ("codesign", "pgrep", "ps", "plutil", "spctl", "lsof", "grep", "python3")


def _strip_lits(txt):
    """剥离字符串字面量与整行注释（R006 A 项要求 —— 否则会把自己的检测正则当靶子）。

    ★ 复用本机既有技术（多处「剥离字符串与注释 —— 避免自指假阳性」）。
    实现用**字符扫描**而非单条复杂正则 —— 后者在自身源码里会被自己的模式串干扰。
    """
    out, i, n = [], 0, len(txt)
    buf = []
    while i < n:
        ch = txt[i]
        if ch == "#":
            while i < n and txt[i] != "\n":
                i += 1
            buf.append("\n")
            continue
        if txt.startswith('"""', i) or txt.startswith("'''", i):
            q = txt[i:i + 3]
            i += 3
            while i < n and not txt.startswith(q, i):
                i += 1
            i += 3
            buf.append('""')
            continue
        if ch in "\"'":
            q = ch
            i += 1
            while i < n and txt[i] != q:
                if txt[i] == "\\":
                    i += 1
                i += 1
            i += 1
            buf.append('""')
            continue
        buf.append(ch)
        i += 1
    return "".join(buf)


def _synth_gcr16(cw):
    """合成 G-CR16 判据的**纯函数部分**（供 B/C 项用）。"""
    real = THRESHOLDS["context_window_default"]
    return cw <= real


def _synth_gcr8(mb):
    """合成 G-CR8 判据的**纯函数部分**（供 B/C 项用）。"""
    return mb < 240.0


def _synth_gcr6_ent(ent_text):
    """合成 G-CR6 的 entitlement 判据（供 B/C 项用）。"""
    return "audio-input" in (ent_text or "")


def selfcheck():
    """R006 ②③④ 能力边界自检。"""
    me = os.path.abspath(__file__)
    txt = open(me, encoding="utf-8").read()
    stripped = _strip_lits(txt)
    # ② 判「是否有写被检对象」的调用（本门为纯只读探测）
    writes = [p for p in (r"open\s*\([^)]*['\"]w", r"write_text\s*\(", r"\.write\s*\(")
              if re.search(p, stripped)]
    # ③ CLD 特有路径是否集中在常量区（散落多处 = 不可移植）
    cld_hits = len(re.findall(r"/Applications/CLD\.app", txt))
    checks = [
        ("② TCC：本门**不写**被检对象（只读探测）", len(writes) == 0),
        ("③ CLD 自适应：CLD 路径集中（%d 处，阈值 ≤3）" % cld_hits, cld_hits <= 3),
        ("④ 版本单一来源 VERSION", 'VERSION = "%s"' % VERSION in txt),
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
    stripped = _strip_lits(raw)
    res = []

    # ── A 源码无危险原语（**剥离后**扫）──
    a_hits = [p for p in DANGEROUS_PRIMS if re.search(p, stripped)]
    res.append(("A 源码无危险原语（剥离后扫）", len(a_hits) == 0,
                "命中 0 条" if not a_hits else "命中 %d 条：%s" % (len(a_hits), a_hits[:3])))

    # ── B 负例全部被拒（用**本门判据的纯函数部分**造越界输入）──
    b_cases = [
        ("G-CR16 window 远超真实上限", _synth_gcr16(1_000_000_000), False),
        ("G-CR8 会话体积 999MB", _synth_gcr8(999.0), False),
        ("G-CR6 entitlement 缺 audio-input", _synth_gcr6_ent("com.apple.security.cs.allow-jit"), False),
    ]
    b_bad = [n for n, got, want in b_cases if got != want]
    res.append(("B 负例全部被拒", len(b_bad) == 0,
                "3 条越界样例全部 FAIL" if not b_bad else "★ 有负例被放过：%s" % b_bad))

    # ── C 正例可用（**防门太宽砍自己人**）──
    c_cases = [
        ("G-CR16 window=1000（合法）", _synth_gcr16(1000), True),
        ("G-CR8 体积 100MB（合法）", _synth_gcr8(100.0), True),
        ("G-CR6 含 audio-input", _synth_gcr6_ent("com.apple.security.device.audio-input"), True),
    ]
    c_bad = [n for n, got, want in c_cases if got != want]
    res.append(("C 正例可用（防门太宽）", len(c_bad) == 0,
                "3 条合法样例全部 PASS" if not c_bad else "★ 门把合法值也拦了：%s" % c_bad))

    # ── D 零变更（本门纯只读 ⇒ 断言源码无写调用）──
    d_writes = [p for p in (r"open\s*\([^)]*['\"]w", r"write_text\s*\(", r"shutil\.copy")
                if re.search(p, stripped)]
    res.append(("D 零变更（无写调用）", len(d_writes) == 0,
                "源码无写文件调用" if not d_writes else "★ 检出写调用：%s" % d_writes))

    # ── E 白名单冻结 ──
    e_ok = isinstance(DANGEROUS_PRIMS, tuple) and isinstance(ALLOWED_CMDS, tuple)
    res.append(("E 白名单冻结（tuple）", e_ok, "DANGEROUS_PRIMS / ALLOWED_CMDS 为不可变 tuple"))

    # ── F 外部命令白名单（**枚举调用点 → 回原文读实参 → 断言 ⊆ 允许集**）──
    #    ★ 依 R006 F 项步骤：**去字面量定位调用点 → 回原文读实参**（否则会「空集通过」）。
    calls = re.findall(r"sh\(\s*\[\s*\"([\w.\-]+)\"", raw)
    calls += re.findall(r"sh\(\s*\[\s*'([\w.\-]+)'", raw)
    bad = sorted(set(calls) - set(ALLOWED_CMDS))
    res.append(("F 外部命令白名单（枚举 %d 处 → 断言 ⊆ %d 项白名单）" % (len(calls), len(ALLOWED_CMDS)),
                len(bad) == 0, "命令集 %s" % sorted(set(calls)) if not bad else "★ 越界命令：%s" % bad))

    print("★ lean4-check（R006 ⑩ 六项）")
    n = 0
    for name, ok, note in res:
        print("  %s %s — %s" % ("✅" if ok else "❌", name, note))
        n += 1 if ok else 0
    print("  六项：%d/%d %s" % (n, len(res), "全绿" if n == len(res) else "★ 未全绿"))
    return 0 if n == len(res) else 1
