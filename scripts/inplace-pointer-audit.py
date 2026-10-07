#!/usr/bin/env python3
"""扫全库：找「有更正卡指向 X，而 X 本身无更正指针」的卡。

由来（2026-09-14，HR 采纳的机制性补法）：
  「就地标注」若靠人记得回原位，它只是一条规则；把它变成原位卡的【必填字段】
  （更正指针 + 截至时刻），它才成为一个步骤 —— 因为字段的有无是可机械检查的，
  而这个查询不需要读任何人的记忆。

启发式（★ 两处都是启发式，所以本报告是【下界/上界】而非精确值，见下）：
  更正卡 = 卡名或正文含 更正/撤回/修正/correct/retract/fix 等记号，
           且其 reply_to 指向另一张卡（或正文提到另一张卡的键）
  原位指针 = 被指的那张卡里出现【更正卡的键名】或「更正/已更正」等字样
  未回原位 = 更正卡存在，但原位卡里找不到对它的引用

判读（★ 必须连同这两条一起读）：
  · 本报告的「未回原位」是【上界】：启发式会把一些非更正性质的引用算进来。
  · 反过来它也是【下界】：正文里用别的措辞指代更正、或更正指向的不是单张卡时，
    真实漏标会比这里报的多。
  · 所以它只能用于【发现问题】，不能用于宣布「已经都标了」。

用法：python3 inplace-pointer-audit.py [--ns data/registry/] [--limit N] [--verbose]
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, sys, re, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

# ★ 2026-09-28 加：未知参数必须【有声拒绝】—— 与本日 verification-level-lint.py 同一处改动同因。
#   实测（08:47 探针 `python3 inplace-pointer-audit.py --selftest`）：它静默忽略 --selftest、
#   照常跑默认扫描（825 键）⇒ **回答了另一个问题，而读数看起来像答案**。
_KNOWN = {"--ns", "--limit", "--verbose", "--version", "-h", "--help"}
_unknown = [a for a in sys.argv[1:] if a.startswith("-") and a not in _KNOWN]
if _unknown:
    sys.exit(f"❌ 不认识的参数: {' '.join(_unknown)}\n"
             f"   本工具接受的参数: {' '.join(sorted(_KNOWN))}\n"
             f"   ★ 本工具【没有】--selftest 入口（明鉴已知未结项，2026-09-28 盘点时发现）。")

BB = "127.0.0.1:8792"
MARK = re.compile(r"更正|撤回|修正|纠正|correct|retract|\bfix\b|supersede", re.I)
POINTER = re.compile(r"更正指针|已更正|见更正|就地更新|supersede|已撤回|retracted")


def enum(ns):
    d = json.loads(urllib.request.urlopen(f"http://{BB}/{ns}", timeout=60).read())
    l = d.get("list", {})
    return list(l.keys()) if isinstance(l, dict) else list(l)


def get(k):
    try:
        with urllib.request.urlopen(f"http://{BB}/{k}", timeout=15) as r:
            return json.loads(r.read())
    except Exception:
        return None


VERSION = "2.0.0"   # 2.0.0 = 2026-09-14 加「弱指针」三态（启发式未改）


def main():
    if "--version" in sys.argv:
        import hashlib
        h = hashlib.sha256(open(__file__, "rb").read()).hexdigest()[:16]
        print("inplace-pointer-audit " + VERSION + " | file_sha256[:16]=" + h
              + " | 启发式 MARK/POINTER 自 v1 起未改")
        return 0
    ns = "data/registry/"
    limit = 0
    verbose = "--verbose" in sys.argv
    if "--ns" in sys.argv:
        ns = sys.argv[sys.argv.index("--ns") + 1]
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    keys = enum(ns)
    if limit:
        keys = keys[:limit]
    print(f"扫描 {ns} · {len(keys)} 键")
    with ThreadPoolExecutor(max_workers=24) as ex:
        cards = {k: get(k) for k in keys}
    cards = {k: v for k, v in cards.items() if v}
    allkeys = set(cards.keys())

    corrections = []      # (更正卡, 它指向的对象集合)
    for k, env in cards.items():
        v = env.get("value", {})
        if not isinstance(v, dict):
            continue
        s = json.dumps(v, ensure_ascii=False)
        if not MARK.search(k) and not MARK.search(s):
            continue
        # ★ 收紧（第一版过宽，实测假阳性极高）：
        #   第一版把「正文里出现的任何卡键」都当作被更正对象 ⇒ 于是任何引用都被算成更正，
        #   报出 67 对里绝大多数无关（如 backup-triple-defect ← absence-lint-approval-review）。
        #   根因是【对象错】：我要测的是「更正」，实际测的是「引用」。
        #   收紧为两条：① 卡名本身带更正记号 ② 正文里有【紧邻指向】的更正表述
        name_is_correction = bool(re.search(r"correct|retract|fix|supersede|更正|撤回|修正", k, re.I))
        targets = set()
        if name_is_correction:
            for m in re.finditer(r"(?:data|notes)/[A-Za-z0-9_\-/]+", s):
                if m.group(0) in allkeys and m.group(0) != k:
                    targets.add(m.group(0))
            rt = v.get("reply_to")
            if isinstance(rt, str):
                for m in re.finditer(r"(?:data|notes)/[A-Za-z0-9_\-/]+", rt):
                    if m.group(0) in allkeys:
                        targets.add(m.group(0))
        else:
            # 紧邻指向：更正/撤回/已更正 + 紧跟其后的卡键（同一小段内）
            for m in re.finditer(r"(?:更正|撤回|已更正|correct(?:ed|ion)?|retract(?:ed|ion)?)[^。\n]{0,20}?((?:data|notes)/[A-Za-z0-9_\-/]+)", s, re.I):
                if m.group(1) in allkeys and m.group(1) != k:
                    targets.add(m.group(1))
        if targets:
            corrections.append((k, targets))

    print(f"识别为「更正性质」且指向具体卡的：{len(corrections)} 张")
    # ★ 三态（2026-09-14 加）：原实现把「含更正卡键名」与「只命中通用词」合并成 has，
    #   而 【只命中通用词】这一支会被【讨论该规则的卡】满足（卡里写着「更正指针」这四个字）
    #   ⇒ 讨论越多，越容易被判成「已回原位」⇒ **漏报，且静默**。
    #   这是「元讨论污染」在【过严方向】的实例（另一个工具 verification-level-lint 是过宽方向）。
    bad, weak = [], []
    for ck, targets in corrections:
        base = ck.split("/")[-1]
        for t in targets:
            sv = json.dumps(cards[t].get("value", {}), ensure_ascii=False)
            named = (ck in sv) or (base in sv)
            ptr = bool(POINTER.search(sv))
            if named:
                continue                      # 强证据：原位卡点了更正卡的名
            if ptr:
                weak.append((ck, t))          # 弱证据：只命中通用词 ⇒ 可能只是它在讨论这条规则
            else:
                bad.append((ck, t))
    print(f"★ 未回原位（更正卡存在，原位无指针）        ：{len(bad)} 对")
    print(f"☆ 弱指针（原位只出现通用词、未点更正卡名）  ：{len(weak)} 对  ← 不计入上面，但必须打印")
    print(f"   （旧版把这两支合并 ⇒ 旧版的「未回原位」= {len(bad) + len(weak)} 对，其中 {len(weak)} 对可能被讨论污染掩盖）")
    for ck, t in bad[:20]:
        print(f"    {t.split('/')[-1][:52]}")
        print(f"      ← 被 {ck.split('/')[-1][:52]} 更正，但原位无指针")
    if len(bad) > 20:
        print(f"    …另有 {len(bad)-20} 对")
    for ck, t in weak[:12]:
        print(f"    [弱] {t.split('/')[-1][:52]}")
        print(f"          ← 被 {ck.split('/')[-1][:52]} 更正，原位只有通用词、无卡名")
    if len(weak) > 12:
        print(f"    …另有 {len(weak)-12} 对弱指针")
    if weak:
        print()
    if verbose:
        for ck, targets in corrections[:10]:
            print(f"  [verbose] 更正卡 {ck.split('/')[-1][:50]} → {len(targets)} 个目标")
    print()
    print("★ 判读：本报告是【上界】也是【下界】（见文件头），只能用于发现问题，不能用于宣布已标全。")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
