#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""add-summary-drift-check.py —— 给一致性门加「逐条摘要文本漂移」检查（对端 ④-B 建议的落地）

【背景】对端 `session-ab866871` 旧卡 ④ 指出：根因**不只是硬编码**，而是
  **同一段文本在两载体各存一份、且无一致性断言** ⇒ 改一处必漂移。
  它给了 A（单一真相源）/ B（加一致性断言）二选一。
  ⇒ 我早已选 B 并建了 `check-rules-consistency.py`；但它列的判据里有一条我**没做**：
    **逐条 name/摘要 的文本指纹比对**。

【实测（决定判据严格度，不靠拍脑袋）】
  在真实账本上跑规范化比对（54 条）：
    完全相同 44 ／ 前缀关系 2 ／ **不一致 7** ／ md 无摘要 1
  逐条看差异：大多是**「md 是精简摘要」**（R037/R038 等，json 更全）——**属正常**；
  但 **R006 相似度 0.74**（md 写「用户批准·十项」、json 仍写 `(v2.1 范围:含服务器化comm-layer…)`）
  与 **R034 0.97**（json「定标准」vs md「据」）**是真正的分叉**。
  ⇒ **判据不能要求逐字相等**（md 本就是人读摘要），改为**低相似度告警**。

【设计】⚠️ **警告级（不判死）**：规范化后 `difflib` 相似度 < 0.90 即报，
  列出 id / 相似度 / 差异片段；≥0.90 视为"摘要精简"，不报。
  理由：与 R34/R31 同源 —— **判据的价值 = 判别力 ÷ 噪声**；要求逐字相等会 7/54 误报、必被忽略。
"""
import io
import os

p = os.path.expanduser("~/dsh-collab/tools/check-rules-consistency.py")
s = io.open(p, encoding="utf-8").read()

# ① 新函数（放在 A2 分类校验之后）
anchor = "# ---------- B. md -> json（v2 新增：真正读 md 侧） ----------"
func = '''# ---------- A3. 逐条摘要文本漂移（对端 ④-B 建议 · ⚠️ 警告级） ----------
#   实测：54 条里 44 完全相同、2 前缀关系、7 不一致；其中大多是「md 是精简摘要」（正常），
#   但 R006(0.74)、R034(0.97) 是真分叉。⇒ **不要求逐字相等**，只对低相似度告警。
_SUMMARY_WARN = []
try:
    import difflib as _dl

    def _norm_summary(x):
        return re.sub(r"[*`#\\s]+", "", str(x or ""))

    _md_sum = {}
    for _m in re.finditer(r"(?m)^##\\s+([A-Za-z]*\\d+)\\b(.*)$", md):
        _rid = _m.group(1)
        _seg = md[_m.end():_m.end() + 1500]
        _sm = re.search(r"-\\s*摘要:\\s*(.+)", _seg)
        if _sm:
            _md_sum.setdefault(_rid, _sm.group(1).strip())
    for _r in d["rules"]:
        _rid = _r.get("id")
        _js = _norm_summary(_r.get("summary"))
        _ms = _md_sum.get(_rid)
        if not _js or _ms is None:
            continue
        _msn = _norm_summary(_ms)
        if _js == _msn:
            continue
        _ratio = _dl.SequenceMatcher(None, _js, _msn).ratio()
        if _ratio < 0.90:
            _SUMMARY_WARN.append((_rid, round(_ratio, 2), _js, _msn))
except Exception as _e:
    _SUMMARY_WARN.append(("?", 0.0, "摘要漂移检查异常: %s" % str(_e)[:60], ""))

'''
assert anchor in s, "A3 锚点未命中"
s = s.replace(anchor, func + anchor, 1)

# ② 输出：把告警打出来（不判死）
old = '''if fails:
    print("  ❌ 漂移 %d 处:" % len(fails))'''
new = '''if _SUMMARY_WARN:
    print("  ⚠️ 摘要文本漂移 %d 处（**警告级，不判死** —— md 本是精简摘要；相似度 <0.90 才报）："
          % len(_SUMMARY_WARN))
    for _rid, _rt, _a, _b in _SUMMARY_WARN[:8]:
        if _rid == "?":
            print("     - %s" % _a); continue
        print("     - %s 相似度 %.2f ｜ json:%s… ／ md:%s…" % (_rid, _rt, _a[:34], _b[:34]))
if fails:
    print("  ❌ 漂移 %d 处:" % len(fails))'''
assert old in s, "输出锚点未命中"
s = s.replace(old, new, 1)

# ③ 自证：加一条正样本（md 摘要被改到低相似度 ⇒ 必须进 _SUMMARY_WARN）
old2 = '''    case("★ md 侧超前日期（对端注入B）⇒ 必须报漂移", m_md_future, True)'''
new2 = '''    case("★ md 侧超前日期（对端注入B）⇒ 必须报漂移", m_md_future, True)

    # ★ 摘要文本漂移（对端 ④-B）：把 md 的 - 摘要: 整句换成无关文本 ⇒ 必须进 _SUMMARY_WARN
    def m_summary_drift(d2):
        import subprocess as _sp, json as _js, sys as _sys, os as _os
        p3 = _os.path.join(d2, "RULES.md")
        t = _io.open(p3, encoding="utf-8").read()
        t = re.sub(r"-\\s*摘要:\\s*.+", "- 摘要: 完全无关的另一段文本用于制造低相似度", t, count=1)
        _io.open(p3, "w", encoding="utf-8").write(t)
        return "把 md 首条摘要改成无关文本"

    def pos_summary_drift(d2):
        r = _run_gate(d2)
        if "摘要文本漂移" in r:
            return True
        raise AssertionError("未报摘要漂移: %s" % r[-200:])

    case("★ 摘要文本漂移 ⇒ 必须告警（对端 ④-B）", lambda d2: (m_summary_drift(d2), pos_summary_drift(d2)), False)'''
if old2 in s and "_run_gate" in s:
    s = s.replace(old2, new2, 1)
    print("✅ 自证已加摘要漂移用例")
else:
    print("ℹ️ 自证未加（缺 _run_gate 辅助）—— 改由真实账本输出验证")

io.open(p, "w", encoding="utf-8").write(s)
print("✅ 已加 A3 摘要漂移检查（⚠️ 警告级，阈值 0.90）")
