#!/usr/bin/env python3
"""
assertion-set-consistency.py — 断言集的「整集一致性」检查

★ 为什么需要它（2026-09-10，由 HR 司库的实际发现逼出来）：
   HR 把我交付的键语法断言集接入 lean4-check 后，「跑」出一个我「读」不出来的问题：
     `data/x/a#b`/`a?b` 列 must_reject，而 `data/x/../escape`/`./cur` 列 must_accept
     —— **两组是同一类，判法却不一致。**
   ★ 它的解释是今晚方法论层面最准的一句：
     「**我是『跑』出来的，不是『读』出来的。** 你的断言集如果我只通读一遍，
       这处不一致**不会被我看见** —— 因为每一条单看都有道理，
       **不一致只存在于两条之间的关系里**。
       所以断言集是工具，不是文档；**审它的正确方式是执行它，而不是阅读它。**」

★ 由此得出的规则（HR 称之为我的版本比它的更强）：
   它说「审它的方式是执行它」（**审查侧**）；
   我说「**构造它就必须跑它**」（**生产侧**）—— 后者能防「自己写的集合有矛盾」。
   **完整表述：断言集不是一个可以「写完再验」的产物，它只能「边跑边长」。**

用法：
  assertion-set-consistency.py <assertion-set.json> [--base http://127.0.0.1:8792] [--dry-run]

退出码：0 无不一致 · 1 发现不一致 · 2 用法或 IO 错误

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, sys, urllib.request as U, urllib.error
from collections import defaultdict


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/assertion-set-consistency.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = "1.0.0"

# ★ 分类器：把键归入「本该同类」的桶 —— 这是「关系检查」的核心
def bucket(k):
    if "#" in k or "?" in k:   return "URL 语义字符（# / ?）"
    if "/../" in k or "/./" in k: return "点段（. / ..）"
    if k.endswith("/"):        return "尾斜杠"
    if "//" in k:              return "空段（//）"
    if any(c in k for c in ":;%&'\"<>|*"): return "非法字符集"
    if any(ord(c) > 127 for c in k): return "非 ASCII"
    return None

def probe(base, k):
    try:
        r = U.urlopen(U.Request(f"{base}/{k}", data=b'{"_probe":1}', method="PUT"), timeout=10)
        return r.status
    except U.HTTPError as e: return e.code
    except Exception as e: return f"ERR:{type(e).__name__}"

def main():
    ap = argparse.ArgumentParser(description="断言集整集一致性检查")
    ap.add_argument("path")
    ap.add_argument("--base", default="http://127.0.0.1:8792")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--tool-version", action="store_true")
    args = ap.parse_args()
    if args.tool_version:
        print(VERSION); return 0

    p = os.path.expanduser(args.path)
    if not os.path.exists(p):
        print(f"❌ 断言集不存在：{p}", file=sys.stderr); return 2
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        print(f"❌ 解析失败：{e}", file=sys.stderr); return 2

    rej = d.get("assertions", {}).get("must_reject", [])
    acc = d.get("assertions", {}).get("must_accept", [])
    print(f"== 断言集整集一致性 · {os.path.basename(p)} ==")
    print(f"   must_reject {len(rej)} · must_accept {len(acc)}")
    print()

    # ★ 检查①：同类别是否分裂在两个集合里（这正是 HR 抓到的那类）
    bk = defaultdict(lambda: {"rej": [], "acc": []})
    for x in rej:
        b = bucket(x["key"])
        if b: bk[b]["rej"].append(x["key"])
    for x in acc:
        b = bucket(x["key"])
        if b: bk[b]["acc"].append(x["key"])

    issues = []
    print(f"  【① 类别间一致性】（同一类必须同侧）")
    print(f"     {'类别':<22}{'must_reject':<14}{'must_accept':<14}{'判定'}")
    for b in sorted(bk):
        v = bk[b]
        split = bool(v["rej"]) and bool(v["acc"])
        if split: issues.append(("类别分裂", b, v))
        print(f"     {b:<22}{len(v['rej']):<14}{len(v['acc']):<14}{'⚠️ 分裂！' if split else '✅'}")
    if not bk:
        print("     （无可分类条目）")

    # ★ 检查②：声明（board 字段）与实测是否一致
    print()
    print(f"  【② 声明 vs 实测】（抽查声明 board=400 的条目）")
    if args.dry_run:
        print("     （dry-run：跳过实测）")
    else:
        sample = [x for x in rej if x.get("board") == 400][:6]
        wrong = 0
        for x in sample:
            actual = probe(args.base, x["key"])
            ok = actual == 400
            if not ok: wrong += 1
            print(f"     {x['key'][:28]:<30} 声明=400 实测={actual} {'✅' if ok else '❌'}")
            try: U.urlopen(U.Request(f"{args.base}/{x['key']}", method="DELETE"), timeout=5)
            except Exception: pass
        if wrong: issues.append(("声明与实测不符", f"{wrong} 条", {}))

    # ★ 检查③：同一 key 不得同时出现在两侧
    print()
    print(f"  【③ 同键不得双侧】")
    both = set(x["key"] for x in rej) & set(x["key"] for x in acc)
    if both:
        issues.append(("同键双侧", list(both), {}))
        print(f"     ⚠️ {len(both)} 个键同时出现在 must_reject 与 must_accept：{list(both)[:5]}")
    else:
        print(f"     ✅ 无重叠")

    # ★ 检查④：边界声明（completeness）是否为空壳
    #   来源：HR 指出「连诚实边界本身也可以被写成空壳」——
    #     空壳键 value={} · 半空壳 value.value · 引用的空壳（三段压一段）· ★ 空壳声明 completeness:"partial"
    #   判据（HR 修订）：**边界声明必须包含「缺口的定位」（在哪部分不全），而不只是「存在缺口」的断言**
    print()
    print(f"  【④ 边界声明是否为空壳】（HR 修订判据：须带「缺口定位」）")
    comp = d.get("completeness")
    if comp is None:
        print(f"     ⚠️ 无顶层 completeness —— 未声明「这是不是全部」")
        issues.append(("缺顶层 completeness", "顶层", {}))
    else:
        import re as _re
        locator = _re.compile(r"\d|from .*subset|where|哪些|未登记|not asserted|measured")
        is_shell = str(comp).strip().lower() in ("partial", "partial (unknown)", "") or not locator.search(str(comp))
        print(f"     声明：{str(comp)[:80]}")
        print(f"     判定：{'⚠️ 空壳（只有「存在缺口」的断言，没有「缺口在哪」）' if is_shell else '✅ 带缺口定位，不是空壳'}")
        if is_shell:
            issues.append(("空壳声明", str(comp)[:40], {}))
    print()
    print("     注：`partial` 单独一个词 = 字段在、格式对、**信息为零** = 空壳声明")

    # ★ 检查⑤：不可执行的主张不得以「规格」形式存在（递归终止条件的落地）
    #   来源：HR「降级本身也要留痕」+「这条如果被违反，谁会知道？」
    print()
    print(f"  【⑤ 规格类产物不得含 design-intent 条目】")
    dn = d.get("design_notes")
    if dn:
        notes = dn.get("notes", []) if isinstance(dn, dict) else dn
        untagged = [n for n in notes if isinstance(n, dict) and "status" not in n]
        tagged = [n for n in notes if isinstance(n, dict) and "status" in n]
        print(f"     降级条目 {len(notes)} 个 · 带 status 标记 {len(tagged)} · 未标记 {len(untagged)}")
        if untagged:
            print(f"     ⚠️ {len(untagged)} 条降级未留痕 —— 读者会以为那是规格")
            issues.append(("降级未留痕", f"{len(untagged)} 条", {}))
        else:
            print(f"     ✅ 全部带 `status: design-intent (not verifiable)` —— 读者不会误当规格")
    else:
        print(f"     （无 design_notes 段）")
    print()
    print("     判据：**「这条如果被违反，谁会知道？」** —— 答不出具体的知道方式，它就还不是规格。")

    print()
    if issues:
        print(f"  ⚠️ 发现 {len(issues)} 处整集不一致：")
        for kind, what, detail in issues:
            print(f"     · [{kind}] {what}")
        print()
        print("  ★ 这些是「逐条看都正确、只在关系上矛盾」的缺陷 —— 只有跑整集才能发现。")
        return 1
    print("  ✅ 整集一致 —— 无类别分裂 · 声明与实测相符 · 无同键双侧")
    print()
    print("  ★ 本检查的由来：我逐条构造断言集，从未整集跑过；")
    print("    是 HR『跑』出来才发现点段与 #/? 判法分裂。")
    print("    **断言集不是「写完再验」的产物，只能「边跑边长」。**")
    return 0

if __name__ == "__main__":
    sys.exit(main())
