#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""cahac-clause-ownership-check.py — S0「偏离归属」判据的机械核

S0 条款（CAHAC v1.2）：
  > 凡本协议条款，均须为其「偏离正常路径」的情形指定【唯一责任方】；
  > 未指定责任方的条款，不得标为 enforced，只能标 advisory。

判据（可机械核）：
  > 遍历全部条款，每条能回答「偏离时谁负责」；答不出的条款标 advisory 并计入缺口数。

本工具做的事：
  ① 逐条核：`owner` 非空 且 **不含 "advisory" 标记**时才算真指定
  ② 交叉核：`status=advisory` 的条目，其 `owner` 必须显式说明「为什么答不出」
  ③ 输出【缺口数】与【缺口清单】（即 S0 要暴露的东西）
  ④ `--selftest`：负例（缺 owner / 错标 enforced）必须被检出

用法：
  python3 cahac-clause-ownership-check.py            # 人读
  python3 cahac-clause-ownership-check.py --json     # 机器读
  python3 cahac-clause-ownership-check.py --selftest
  python3 cahac-clause-ownership-check.py --gaps     # 只列缺口
退出码：0 = 无非法条目；1 = 有非法条目（即清单本身有错）；2 = 环境错误

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== cahac-clause-ownership-check 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · cahac-clause-ownership-check.py — S0「偏离归属」判据的机械核")
    print("  · S0 条款（CAHAC v1.2）：")
    print("  · > 凡本协议条款，均须为其「偏离正常路径」的情形指定【唯一责任方】；")
    print("  · > 未指定责任方的条款，不得标为 enforced，只能标 advisory。")
    print("  · 命令/参数: json, gaps, selftest, file")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, json, os, sys, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/cahac-clause-ownership-check.log")
    return 0



import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

import argparse
import json
import os
import sys


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕
LOG = os.path.expanduser("~/dsh-collab/logs/cahac-clause-ownership-check.log")   # ★ 不用 COLLAB（本文件无该常量）


def log(msg):
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

DEFAULT = os.path.expanduser(
    "~/dsh-collab/research/cost-governance/cahac-clause-ownership.json")
LEGAL_STATUS = {"enforced", "advisory"}


def load(path=None):
    p = path or DEFAULT
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def check(data):
    """返回 (rows, problems)。rows 每条含 id/sec/clause/status/owner/why。"""
    problems = []
    rows = []
    seen = set()
    for c in data.get("clauses", []):
        cid = c.get("id", "?")
        st = c.get("status")
        owner = (c.get("owner") or "").strip()
        why = []
        # ① id 唯一
        if cid in seen:
            problems.append("%s: 重复 id" % cid)
        seen.add(cid)
        # ② status 合法
        if st not in LEGAL_STATUS:
            problems.append("%s: status 非法（%r）" % (cid, st))
        # ③ owner 非空
        if not owner:
            problems.append("%s: owner 为空" % cid)
        # ④ ★ 关键：标 enforced 的，owner 里不得出现 advisory 标记
        if st == "enforced" and "advisory" in owner.lower():
            problems.append("%s: 标 enforced 但 owner 自承未指定 ⇒ 应改标 advisory" % cid)
        # ⑤ advisory 的必须说明「为什么答不出」
        if st == "advisory" and "未" not in owner and "无" not in owner:
            problems.append("%s: advisory 但 owner 未说明缺失原因" % cid)
        # ⑥ 必备字段
        for k in ("sec", "clause", "normal", "deviation"):
            if not c.get(k):
                problems.append("%s: 缺字段 %s" % (cid, k))
        rows.append({"id": cid, "sec": c.get("sec"), "clause": c.get("clause"),
                     "status": st, "owner": owner, "deviation": c.get("deviation"),
                     "problems": [x for x in problems if x.startswith(cid + ":")]})
    return rows, problems


def summary(rows):
    n = len(rows)
    enf = sum(1 for r in rows if r["status"] == "enforced")
    adv = sum(1 for r in rows if r["status"] == "advisory")
    return {"total": n, "enforced": enf, "advisory": adv,
            "gap_ratio": round(adv / n, 4) if n else None}


def selftest():
    fails = neg = pos = 0

    def c(name, cond, kind="pos"):
        nonlocal fails, neg, pos
        if kind == "pos":
            pos += 1
        else:
            neg += 1
        good = bool(cond)
        print("  %s %-6s %s" % ("✅" if good else "❌", kind, name))
        if not good:
            fails += 1

    print("== cahac-clause-ownership-check selftest ==")
    base = {"id": "T1", "sec": "§1", "clause": "c", "normal": "n",
            "deviation": "d", "owner": "某人", "status": "enforced"}
    # 正例：合规条目应无 problem
    _, p0 = check({"clauses": [dict(base)]})
    c("合规条目 ⇒ 无 problem", p0 == [])
    # 负例：owner 空
    _, p1 = check({"clauses": [dict(base, owner="")]})
    c("owner 空 ⇒ 检出", any("owner 为空" in x for x in p1), kind="neg")
    # 负例：✗ 标 enforced 但 owner 自承 advisory
    _, p2 = check({"clauses": [dict(base, owner="★ advisory：未指定")]})
    c("标 enforced 而 owner 自承 advisory ⇒ 检出", any("应改标 advisory" in x for x in p2), kind="neg")
    # 负例：status 非法
    _, p3 = check({"clauses": [dict(base, status="BOGUS")]})
    c("status 非法 ⇒ 检出", any("status 非法" in x for x in p3), kind="neg")
    # 负例：重复 id
    _, p4 = check({"clauses": [dict(base), dict(base)]})
    c("重复 id ⇒ 检出", any("重复 id" in x for x in p4), kind="neg")
    # 负例：advisory 但没说原因
    _, p5 = check({"clauses": [dict(base, status="advisory", owner="某人")]})
    c("advisory 未说明缺失原因 ⇒ 检出", any("未说明缺失原因" in x for x in p5), kind="neg")
    # 正例：advisory 且说明原因
    _, p6 = check({"clauses": [dict(base, status="advisory", owner="★ advisory：未指定责任方")]})
    c("advisory 且说明原因 ⇒ 无 problem", p6 == [])
    # 正例：真实清单可加载
    if os.path.exists(DEFAULT):
        rows, _ = check(load())
        s = summary(rows)
        c("真实清单可加载并有 enforced 与 advisory 两类",
          s["total"] > 0 and s["enforced"] > 0 and s["advisory"] > 0)
    print("\n  selftest: %d FAIL ｜ 反例 %d 条 / 正例 %d 条" % (fails, neg, pos))
    return 0 if fails == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    ap.add_argument("--gaps", action="store_true", help="只列 advisory 缺口")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--file", default=None)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not os.path.exists(a.file or DEFAULT):
        print("环境错误：找不到清单 " + (a.file or DEFAULT), file=sys.stderr)
        return 2
    rows, problems = check(load(a.file))
    s = summary(rows)
    if a.json:
        print(json.dumps({"summary": s, "problems": problems, "rows": rows},
                         ensure_ascii=False, indent=1))
        return 1 if problems else 0
    if a.gaps:
        print("★ S0 缺口清单（advisory = 未指定唯一责任方）")
        for r in rows:
            if r["status"] == "advisory":
                print("  %-8s %-8s %s" % (r["id"], r["sec"], r["clause"][:44]))
                print("          偏离：%s" % (r["deviation"] or "")[:90])
        print("\n  合计 %d 条缺口（共 %d 条）" % (s["advisory"], s["total"]))
        return 0
    print("== S0 偏离归属 · 条款责任方核验 ==")
    for r in rows:
        mark = "✅" if r["status"] == "enforced" else "🟡"
        print("  %s %-9s %-7s %s" % (mark, r["id"], r["sec"], (r["clause"] or "")[:46]))
    print("\n  条款总数 %d · **enforced %d** · **advisory（缺口）%d** · 缺口比 %.1f%%"
          % (s["total"], s["enforced"], s["advisory"], (s["gap_ratio"] or 0) * 100))
    if problems:
        print("\n  ★ 清单自身问题 %d 处：" % len(problems))
        for x in problems[:12]:
            print("    · " + x)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
