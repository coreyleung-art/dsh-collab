#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-hazards-consistency.py —— hazards 档案**内部自洽门**（2026-10-03 建立）

【为什么必须存在】
  我在同一天**四次**把档案里的"规则区间声明"改漏：
    `rules.md` 标题停在 R1–R24（实际已 R29）／`INDEX.md` §4 停在 R1–R28／R1–R30／R1–R35。
  每次都是"我改了内容、忘了改那句摘要"。这与账本侧 `category` 漂移**同型** ——
  **声明与实际不一致，而没有任何判据盯着它**。
  ⇒ 账本有 `check-rules-consistency.py`；**档案也该有对应的一道门**（本文件）。
  （上文「R1–R24 / R29」为**改名前旧称**：2026-10-04 起 hazards 自有规则统一 `H*`。）

【校验的不变量（每条对应一种真实发生过的漂移）】
  I1  `rules.md` 标题的区间上界 == 表内最大 H 编号
  I2  `INDEX.md` §4 标题的区间上界 == 同上（★ 这条今天就错了）
  I3  `INDEX.md` 声称的事故数 == `incidents/` 实际文件数
  I4  类别总表行数 == 类别展开段数
  I5  INDEX 引用的每个 `incidents/#*.md` 都存在；且没有孤儿 incident
  I6  档案内引用的 hazards 自有规则编号都存在（账本三位数 `R0xx` 属另一命名空间，排除）
★ 命名空间（2026-10-04，G6）：hazards 自有规则 `R1–R43` → **`H1–H43`**（星桥已采纳「命名空间隔离」）；
  本工具**自身**不变量编号改用 **`I1–I6`** —— 否则「H2」既是规则又是检查项，等于制造新的同名不同义。

【用法】
  python3 check-hazards-consistency.py            # exit 0/1
  python3 check-hazards-consistency.py --selftest # 正负样本自证
★ 退出码语义（H37）：0=通过 ／ 1=不变量不满足 ／ 2=环境错 ／ **3=守卫主动拒绝**
"""
import argparse
import glob
import io
import os
import re
import shutil
import sys
import tempfile

H = os.environ.get("HAZARDS_DIR") or os.path.expanduser("~/dsh-collab/hazards")


def checks(hdir):
    """返回 [(码, 说明)]；空列表 = 全通过。纯函数，便于在临时副本上做正负样本。"""
    out = []
    idxp = os.path.join(hdir, "INDEX.md")
    rulp = os.path.join(hdir, "rules.md")
    patp = os.path.join(hdir, "patterns", "00-总表.md")
    for p in (idxp, rulp, patp):
        if not os.path.isfile(p):
            return [("I0", "缺文件: %s" % p)]
    idx = io.open(idxp, encoding="utf-8").read()
    rul = io.open(rulp, encoding="utf-8").read()
    pat = io.open(patp, encoding="utf-8").read()

    # 实际最大 H 编号（hazards 自有命名空间：H1–H99；账本 R0xx 三位数不计）
    nums = [int(m) for m in re.findall(r"(?m)^\|\s*H(\d{1,2})\s*\|", rul)]
    if not nums:
        out.append(("I1", "rules.md 里找不到规则表行（`| H<数字> |`）"))
        return out
    mx = max(nums)

    def declared(doc, where):
        m = re.search(r"H1[–\-]H(\d{1,3})", doc)
        return (int(m.group(1)) if m else None), where

    for doc, where, code in ((rul, "rules.md 标题", "I1"), (idx, "INDEX.md §4 标题", "I2")):
        d, _ = declared(doc, where)
        if d is None:
            out.append((code, "%s 找不到 `H1–H<n>` 区间声明" % where))
        elif d != mx:
            out.append((code, "%s 声明 H1–H%d，实际最大 H%d ⇒ **声明陈旧**" % (where, d, mx)))

    # I3 事故数
    inc = sorted(glob.glob(os.path.join(hdir, "incidents", "#*.md")))
    m = re.search(r"事故索引（(\d+)\s*起", idx)
    if not m:
        out.append(("I3", "INDEX 找不到 `事故索引（N 起` 声明"))
    elif int(m.group(1)) != len(inc):
        out.append(("I3", "INDEX 声称 %s 起，实际 %d 个文件 ⇒ **声明陈旧**" % (m.group(1), len(inc))))

    # I4 类别表 vs 展开段
    rows = len(re.findall(r"(?m)^\|\s*\*\*[A-F]\*\*\s*\|", pat))
    secs = len(re.findall(r"(?m)^###\s*[A-F]\s*·", pat))
    if rows != secs:
        out.append(("I4", "类别表行数 %d ≠ 展开段数 %d" % (rows, secs)))

    # I5 引用可达 + 无孤儿
    refs = re.findall(r"incidents/(#[0-9]+-[A-Za-z0-9\-]+\.md)", idx)
    miss = [r for r in refs if not os.path.isfile(os.path.join(hdir, "incidents", r))]
    if miss:
        out.append(("I5", "INDEX 引用的 incident 不存在: %s" % ", ".join(miss[:5])))
    names = [os.path.basename(f) for f in inc]
    orphan = [n for n in names if n not in refs]
    if orphan:
        out.append(("I5", "孤儿 incident（无索引引用）: %s" % ", ".join(orphan[:5])))

    # I6 档案内自有规则引用无悬空（H 两位数；账本 R 三位数属另一命名空间，排除）
    own = set("H%d" % n for n in nums)
    pat_r = re.compile(r"\bH(\d{1,2})\b(?!\d)")
    cited = set("H" + m2 for m2 in pat_r.findall(idx + pat + rul))
    # 排除明显属于账本的引用（R025/R034/R036/R039 等带前导 0 的写法）
    cited = set(c for c in cited if not re.search(r"H0\d", c))
    dang = sorted(cited - own, key=lambda x: int(x[1:]))
    if dang:
        out.append(("I6", "档案内引用悬空（自有命名空间）: %s" % ", ".join(dang[:8])))
    return out


def _selftest():
    print("hazards 自洽门 · 自证（正负样本）")
    ok = True
    real = H
    tmp = tempfile.mkdtemp(prefix="hz-selftest-")

    def mk():
        d = tempfile.mkdtemp(dir=tmp)
        shutil.copytree(real, d, dirs_exist_ok=True)
        return d

    def case(name, mutate, expect_codes):
        nonlocal ok
        d = mk()
        try:
            mutate(d)
            got = [c for c, _ in checks(d)]
            good = (got == expect_codes) if not expect_codes else all(c in got for c in expect_codes)
            ok = ok and good
            print("  %s %-44s 期望%-14s 实际 %s" % (
                "✅" if good else "❌", name,
                "OK" if not expect_codes else ",".join(expect_codes), ",".join(got) or "OK"))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def m_none(_d):
        pass

    def m_stale_idx(d):
        p = os.path.join(d, "INDEX.md")
        s = io.open(p, encoding="utf-8").read()
        s = re.sub(r"H1[–\-]H\d{1,3}", "H1–H9", s, count=1)
        io.open(p, "w", encoding="utf-8").write(s)

    def m_stale_rul(d):
        p = os.path.join(d, "rules.md")
        s = io.open(p, encoding="utf-8").read()
        s = re.sub(r"H1[–\-]H\d{1,3}", "H1–H3", s, count=1)
        io.open(p, "w", encoding="utf-8").write(s)

    def m_inc_count(d):
        p = os.path.join(d, "INDEX.md")
        s = io.open(p, encoding="utf-8").read()
        s = re.sub(r"事故索引（\d+\s*起", "事故索引（99 起", s, count=1)
        io.open(p, "w", encoding="utf-8").write(s)

    def m_orphan(d):
        io.open(os.path.join(d, "incidents", "#99-orphan.md"), "w", encoding="utf-8").write("# x\n")

    case("未改动副本（负样本，防过杀）", m_none, [])
    case("★ INDEX 标题区间陈旧（今天真实发生）", m_stale_idx, ["I2"])
    case("rules.md 标题区间陈旧（曾真实发生）", m_stale_rul, ["I1"])
    case("事故数声明与实际不符", m_inc_count, ["I3"])
    case("孤儿 incident（无索引引用）", m_orphan, ["I5"])
    shutil.rmtree(tmp, ignore_errors=True)
    print()
    print("  ⇒ %s" % ("全部通过" if ok else "存在失败项"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dir", default=H)
    a = ap.parse_args()
    if a.selftest:
        return _selftest()
    if not os.path.isdir(a.dir):
        print("环境错：目录不存在 %s" % a.dir)
        return 2
    rows = checks(a.dir)
    if not rows:
        print("hazards 自洽门 · ✅ 全部不变量通过（%s）" % a.dir)
        return 0
    print("hazards 自洽门 · ❌ %d 项不满足：" % len(rows))
    for c, m in rows:
        print("  [%s] %s" % (c, m))
    return 1


if __name__ == "__main__":
    sys.exit(main())
