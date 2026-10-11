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
