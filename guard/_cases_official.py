def _r006_cases():
    """★ 供 B/C 两项：**用本工具真实判据造合成输入**（替换通用块的占位实现）。

    ★ 依据：`age_hours()` / `FRESH_HOURS` 与三栏判据 —— 它们正是 `selftest()` 里已有的
      合成负例，本函数把它们**抽出来给 R006 B/C 复用**（同一判据，不另起一套）。
    ★ 实测（2026-10-10）：留证 1h 前 ⇒ 新鲜（GO）；48h 前 ⇒ 过期（NO-GO）。
    """
    _now = time.time()
    _fresh = {"ts_epoch": _now - 3600, "target": "x"}
    _stale = {"ts_epoch": _now - 48 * 3600, "target": "x"}

    b = [
        ("留证 48h 前 ⇒ 应过期（age=%.1fh > %.1fh）" % (age_hours(_stale) or -1, FRESH_HOURS),
         (age_hours(_stale) or 0) > FRESH_HOURS, True),
    ]
    c = [
        ("留证 1h 前 ⇒ 应新鲜（age=%.1fh ≤ %.1fh）" % (age_hours(_fresh) or -1, FRESH_HOURS),
         (age_hours(_fresh) or 0) <= FRESH_HOURS, True),
    ]
    return b, c
