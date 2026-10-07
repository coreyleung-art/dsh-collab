#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix-restart-audit-verdict-single-source.py —— 让 --json 与人读分支共用同一判定

【缺陷】（2026-10-03 重启前审查查出，**重启后会立刻暴露**）
  `restart-audit.py` 有**两套判定**：
    · 人读分支：`stub-limited` 且**有自查证据** ⇒ 降级为 ⚠️、**不阻断** ⇒ exit 0（"可以重启"）
    · `--json` 分支：`smoke == "stub-limited"` ⇒ **直接算阻断** ⇒ exit 1
  而插件工具判通过与否**只看退出码**：
    `const ok = r.code === 0;` ⇒ `verdict: ok ? 'pass' : 'blocked'`
  ⇒ **重启后调用 `restart_audit` 工具会报 `⛔ 审查未通过（exit=1）`，而手跑脚本说"✅ 可以重启"**
  ⇒ 同一条判据两个分支结论相反 —— 正是今天一直在打的那一类。

【修法】把"阻断项计算"抽成**单一真相源** `compute_blockers()`，两个分支共用；
  `--json` 沿用**同一逻辑**决定退出码（并在 JSON 里附 `_verdict` 字段，便于调用方直接读，不必猜退出码）。
"""
import io
import os

p = os.path.expanduser("~/dsh-collab/tools/restart-audit.py")
s = io.open(p, encoding="utf-8").read()

# ── ① 抽出入参化的阻断判定（放在 main 之前）──────────────────────────
anchor = "def main():"
func = '''def compute_blockers(rep, sandbox_ok):
    """★ 单一真相源（2026-10-03 修「两分支判定相反」缺陷）。

    背景：`--json` 分支原先把 `smoke == "stub-limited"` 一律当阻断（exit 1），
    而人读分支对**有自查证据**的 stub-limited **降级为 ⚠️ 不阻断**（exit 0）
    ⇒ 插件工具只看退出码 ⇒ **工具报"未通过"、手跑脚本报"可以重启"**（同一份数据两个结论）。
    ⇒ 抽到这里，两分支共用，杜绝再次分叉。
    """
    blockers = []
    for r in rep:
        if (r["syntax_fail"] or r["deps_missing"] or r["bare_syms"]
                or r.get("self_recursion") or r.get("settle") is False
                or r.get("patch") is False or r["smoke"] is False):
            blockers.append(r["name"])
        elif (r["smoke"] == "stub-limited"
              and "来自 config.*" not in str(r["smoke_msg"])
              and not _selfcheck_passed(r["name"])):
            blockers.append(r["name"] + "(apply 需人工确认)")
    if sandbox_ok is False:
        blockers.append("boot-sandbox")
    return blockers


def main():'''
assert anchor in s, "main 锚点未命中"
s = s.replace(anchor, func, 1)

# ── ② --json 分支改用同一逻辑 + 附 _verdict ────────────────────────────
old_json = '''    as_json = "--json" in sys.argv
    if as_json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0 if not any(r["syntax_fail"] or r["deps_missing"] or r["bare_syms"]
                            or r.get("self_recursion") or r.get("settle") is False
                            or r["smoke"] is False or r["smoke"] == "stub-limited"
                            for r in rep) else 1'''
new_json = '''    as_json = "--json" in sys.argv
    if as_json:
        # ★ 与人读分支**同一判定**（compute_blockers）；顺带把结论写进 JSON，
        #   调用方不必再从退出码反推（退出码语义保留：0=通过 / 1=有阻断）。
        _blk = compute_blockers(rep, sandbox_ok)
        print(json.dumps({"_verdict": "blocked" if _blk else "pass",
                          "_blockers": _blk,
                          "_sandbox_ok": sandbox_ok,
                          "_deps_ok": deps_ok,
                          "plugins": rep}, ensure_ascii=False, indent=2))
        return 1 if _blk else 0'''
assert old_json in s, "json 分支锚点未命中"
s = s.replace(old_json, new_json, 1)

# ── ③ 人读分支复用（把内联的 blockers 组装替换为调用）────────────────
old_blk = '''    blockers = []
    for r in rep:'''
new_blk = '''    blockers = compute_blockers(rep, sandbox_ok)   # ★ 单一真相源（原内联逻辑已抽走）
    for r in rep:'''
assert old_blk in s, "blockers 锚点未命中"
s = s.replace(old_blk, new_blk, 1)

# 人读分支里原来会把 sandbox 失败/ stub-limited 再 append 一次 ⇒ 去掉重复追加
s = s.replace('''    if sandbox_ok is False:
        blockers.append("boot-sandbox")
''', '', 1)
old_tail = '''        if (r["syntax_fail"] or r["deps_missing"] or r["bare_syms"]
                or r.get("self_recursion") or r.get("settle") is False
                or r.get("patch") is False or r["smoke"] is False):
            blockers.append(r["name"])
        elif (r["smoke"] == "stub-limited" and "来自 config.*" not in str(r["smoke_msg"])
              and not _selfcheck_passed(r["name"])):
            blockers.append(r["name"] + "(apply 需人工确认)")
'''
assert old_tail in s, "尾部重复 append 锚点未命中"
s = s.replace(old_tail, "", 1)

io.open(p, "w", encoding="utf-8").write(s)
print("✅ 已改为单一真相源：compute_blockers() 两分支共用；--json 附 _verdict/_blockers")
