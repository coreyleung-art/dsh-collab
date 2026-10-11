def _r006_cases():
    """★ 供 B/C 两项：**用本工具真实判据造合成输入**（替换通用块的占位实现）。

    ★ 依据：`check_timevalue()` 的输出字段 ——
        · `n_bare` = **无证据支撑的确定性值个数**（如裸露的 `/tmp` 路径、指纹）
        · R048 的**时值检查三选一**要求：A 自包含 / B 标时点+复跑命令 / C 指向活体入口
      ⇒ B 项：**裸露值 ⇒ `n_bare > 0`**（判据能红）
      ⇒ C 项：**含时点 + 复跑命令 ⇒ `n_bare == 0`**（判据不误伤合法写法）
    ★ 实测值（2026-10-10 · 本机）：
        · 含裸露 /tmp 与指纹 ⇒ n_values=2 n_bare=2
        · 含时点+复跑命令    ⇒ n_values=2 n_bare=0
    """
    # ── B 负例：裸露的确定性值（易失路径 + 指纹，均无证据）⇒ 应红 ──
    _bare = ("临时文件在 /tmp/foo-12345.json，指纹 abcdef123456abcd。")
    r_bare = check_timevalue(_bare)
    # ── C 正例：标了时点 + 复跑命令（R048 的 B 式）⇒ 应无裸露值 ──
    _nl = chr(10)
    _good = ("时点：2026-10-10T03:00:00+0800" + _nl
             + "复跑命令：python3 tools/x.py --check" + _nl
             + "临时文件在 /tmp/foo.json（**命令自创建的中间文件**，非依赖）")
    r_good = check_timevalue(_good)

    b = [
        ("裸露易失路径+指纹 ⇒ 应红（n_bare=%d）" % r_bare["n_bare"], r_bare["n_bare"] > 0, True),
    ]
    c = [
        ("含时点+复跑命令 ⇒ 应无裸露值（n_bare=%d）" % r_good["n_bare"], r_good["n_bare"] == 0, True),
    ]
    return b, c
