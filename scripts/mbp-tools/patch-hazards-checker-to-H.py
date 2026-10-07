#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 check-hazards-consistency.py 切到 H 命名空间：
   ① rules 命名空间 R1–R99 → H1–H99
   ② 工具自身不变量编号 H1–H6 → I1–I6（避免与规则 H 号撞名 = 新的同名不同义）

R41 纪律：每处替换断言「恰好命中 1 次」，命中数不符即失败（不盲替）。
"""
import io, sys, os

P = os.path.expanduser("~/dsh-collab/tools/check-hazards-consistency.py")
s0 = io.open(P, encoding="utf-8").read()
s = s0
fails = []

PAIRS = [
    # ── docstring：不变量编号 H→I，并记命名空间变更 ──
    ("  H1  `rules.md` 标题的区间上界 == 表内最大 R 编号",
     "  I1  `rules.md` 标题的区间上界 == 表内最大 H 编号"),
    ("  H2  `INDEX.md` §4 标题的区间上界 == 同上（★ 这条今天就错了）",
     "  I2  `INDEX.md` §4 标题的区间上界 == 同上（★ 这条今天就错了）"),
    ("  H3  `INDEX.md` 声称的事故数 == `incidents/` 实际文件数",
     "  I3  `INDEX.md` 声称的事故数 == `incidents/` 实际文件数"),
    ("  H4  类别总表行数 == 类别展开段数",
     "  I4  类别总表行数 == 类别展开段数"),
    ("  H5  INDEX 引用的每个 `incidents/#*.md` 都存在；且没有孤儿 incident",
     "  I5  INDEX 引用的每个 `incidents/#*.md` 都存在；且没有孤儿 incident"),
    ("  H6  档案内引用的 hazards 自有规则编号都存在（账本三位数 `R0xx` 属另一命名空间，排除）",
     "  I6  档案内引用的 hazards 自有规则编号都存在（账本三位数 `R0xx` 属另一命名空间，排除）\n"
     "★ 命名空间（2026-10-04，G6）：hazards 自有规则 `R1–R43` → **`H1–H43`**（星桥已采纳「命名空间隔离」）；\n"
     "  本工具**自身**不变量编号改用 **`I1–I6`** —— 否则「H2」既是规则又是检查项，等于制造新的同名不同义。"),
    ("  ⇒ 账本有 `check-rules-consistency.py`；**档案也该有对应的一道门**（本文件）。",
     "  ⇒ 账本有 `check-rules-consistency.py`；**档案也该有对应的一道门**（本文件）。\n"
     "  （上文「R1–R24 / R29」为**改名前旧称**：2026-10-04 起 hazards 自有规则统一 `H*`。）"),
    ("★ 退出码语义（R37）：", "★ 退出码语义（H37）："),
    # ── 代码：不变量码 ──
    ('return [("H0", "缺文件: %s" % p)]', 'return [("I0", "缺文件: %s" % p)]'),
    ('out.append(("H1", "rules.md 里找不到规则表行（`| R<数字> |`）"))',
     'out.append(("I1", "rules.md 里找不到规则表行（`| H<数字> |`）"))'),
    ('for doc, where, code in ((rul, "rules.md 标题", "H1"), (idx, "INDEX.md §4 标题", "H2")):',
     'for doc, where, code in ((rul, "rules.md 标题", "I1"), (idx, "INDEX.md §4 标题", "I2")):'),
    ('out.append((code, "%s 找不到 `R1–R<n>` 区间声明" % where))',
     'out.append((code, "%s 找不到 `H1–H<n>` 区间声明" % where))'),
    ('out.append((code, "%s 声明 R1–R%d，实际最大 R%d ⇒ **声明陈旧**" % (where, d, mx)))',
     'out.append((code, "%s 声明 H1–H%d，实际最大 H%d ⇒ **声明陈旧**" % (where, d, mx)))'),
    ('    # H3 事故数', '    # I3 事故数'),
    ('out.append(("H3", "INDEX 找不到 `事故索引（N 起` 声明"))',
     'out.append(("I3", "INDEX 找不到 `事故索引（N 起` 声明"))'),
    ('out.append(("H3", "INDEX 声称 %s 起，实际 %d 个文件 ⇒ **声明陈旧**" % (m.group(1), len(inc))))',
     'out.append(("I3", "INDEX 声称 %s 起，实际 %d 个文件 ⇒ **声明陈旧**" % (m.group(1), len(inc))))'),
    ('    # H4 类别表 vs 展开段', '    # I4 类别表 vs 展开段'),
    ('out.append(("H4", "类别表行数 %d ≠ 展开段数 %d" % (rows, secs)))',
     'out.append(("I4", "类别表行数 %d ≠ 展开段数 %d" % (rows, secs)))'),
    ('    # H5 引用可达 + 无孤儿', '    # I5 引用可达 + 无孤儿'),
    ('out.append(("H5", "INDEX 引用的 incident 不存在: %s" % ", ".join(miss[:5])))',
     'out.append(("I5", "INDEX 引用的 incident 不存在: %s" % ", ".join(miss[:5])))'),
    ('out.append(("H5", "孤儿 incident（无索引引用）: %s" % ", ".join(orphan[:5])))',
     'out.append(("I5", "孤儿 incident（无索引引用）: %s" % ", ".join(orphan[:5])))'),
    ('    # H6 档案内自有规则引用无悬空（两位数；三位数属账本命名空间，排除）',
     '    # I6 档案内自有规则引用无悬空（H 两位数；账本 R 三位数属另一命名空间，排除）'),
    ('out.append(("H6", "档案内引用悬空（自有命名空间）: %s" % ", ".join(dang[:8])))',
     'out.append(("I6", "档案内引用悬空（自有命名空间）: %s" % ", ".join(dang[:8])))'),
    # ── 代码：规则命名空间 R→H ──
    ('    # 实际最大 R 编号（hazards 自有命名空间：R1–R99；账本 R0xx 三位数不计）\n'
     '    nums = [int(m) for m in re.findall(r"(?m)^\\|\\s*R(\\d{1,2})\\s*\\|", rul)]',
     '    # 实际最大 H 编号（hazards 自有命名空间：H1–H99；账本 R0xx 三位数不计）\n'
     '    nums = [int(m) for m in re.findall(r"(?m)^\\|\\s*H(\\d{1,2})\\s*\\|", rul)]'),
    ('        m = re.search(r"R1[–\\-]R(\\d{1,3})", doc)',
     '        m = re.search(r"H1[–\\-]H(\\d{1,3})", doc)'),
    ('    own = set("R%d" % n for n in nums)', '    own = set("H%d" % n for n in nums)'),
    ('    pat_r = re.compile(r"\\bR(\\d{1,2})\\b(?!\\d)")',
     '    pat_r = re.compile(r"\\bH(\\d{1,2})\\b(?!\\d)")'),
    ('    cited = set("R" + m2 for m2 in pat_r.findall(idx + pat + rul))',
     '    cited = set("H" + m2 for m2 in pat_r.findall(idx + pat + rul))'),
    ('    cited = set(c for c in cited if not re.search(r"R0\\d", c))',
     '    cited = set(c for c in cited if not re.search(r"H0\\d", c))'),
    # ── 自证样本：变异体与期望码 ──
    ('        s = re.sub(r"R1[–\\-]R\\d{1,3}", "R1–R9", s, count=1)',
     '        s = re.sub(r"H1[–\\-]H\\d{1,3}", "H1–H9", s, count=1)'),
    ('        s = re.sub(r"R1[–\\-]R\\d{1,3}", "R1–R3", s, count=1)',
     '        s = re.sub(r"H1[–\\-]H\\d{1,3}", "H1–H3", s, count=1)'),
    ('case("★ INDEX 标题区间陈旧（今天真实发生）", m_stale_idx, ["H2"])',
     'case("★ INDEX 标题区间陈旧（今天真实发生）", m_stale_idx, ["I2"])'),
    ('case("rules.md 标题区间陈旧（曾真实发生）", m_stale_rul, ["H1"])',
     'case("rules.md 标题区间陈旧（曾真实发生）", m_stale_rul, ["I1"])'),
    ('case("事故数声明与实际不符", m_inc_count, ["H3"])',
     'case("事故数声明与实际不符", m_inc_count, ["I3"])'),
    ('case("孤儿 incident（无索引引用）", m_orphan, ["H5"])',
     'case("孤儿 incident（无索引引用）", m_orphan, ["I5"])'),
]

for old, new in PAIRS:
    n = s.count(old)
    if n != 1:
        fails.append((n, old[:70]))
        continue
    s = s.replace(old, new, 1)

if fails:
    print("❌ 有 %d 处未恰好命中 1 次（不落盘）:" % len(fails))
    for n, o in fails:
        print("  命中 %d 次: %s" % (n, o))
    sys.exit(1)

io.open(P, "w", encoding="utf-8").write(s)
print("✅ %d 处全部恰好命中并替换" % len(PAIRS))

# 读回断言
back = io.open(P, encoding="utf-8").read()
import re
stale = re.findall(r'(?<![0-9A-Za-z_])"H[1-6]"', back)
print("读回：残留旧不变量码 H1–H6 =", stale or "无 ✅")
print("读回：H 命名空间行数 =", len(re.findall(r"\bH\d{1,2}\b", back)))
