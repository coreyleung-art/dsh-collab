#!/usr/bin/env python3
"""核验级别检测：找「已落盘 / 已修复 / 已同步」这类声称，看它有没有声明核到哪一级。

由来（HR 2026-09-14 排序：第 1 位）：
  可机械检查 ✓ · 后果最重 —— 虚假的「已落盘」会让下游在错误前提上行动。
  今晚多起事故都源于此：HR 报「写入成功两次」· 我报「已落盘成功」，而两层都不是真的。
  执行理由：这条防的是【下游在错误前提上行动】（不可逆）；裸数那条防的是【可比性失真】（可重算）。
  ⇒ 不可逆的优先于可重算的。

三级（明鉴 2026-09-14 的核验边界 v2）：
  存在级 —— 键在、非空（GET 得到）
  结构级 —— 层级与字段形态符合约定（字段数 / 键集合 / 单层）
  内容级 —— 值与声称相符（指纹 / 复算）

它做什么：扫卡的内容，找【完成态声称】，检查同一段里有没有级别词。
  有声称 + 无级别词 ⇒ 报出（该声称的强度上限不明）
  有声称 + 有级别词 ⇒ 通过

用法：
  python3 verification-level-lint.py [--ns data/registry/] [--limit N]
退出码：0 = 未发现无级别的完成态声称；1 = 有
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, sys, re, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

# ★ 2026-09-28 加：未知参数必须【有声拒绝】，不能静默跑默认动作。
#   实测（08:47 工具族盘点，探针 = `python3 <工具> --selftest`）：本工具**没有 --selftest 入口**，
#   而它当时**静默忽略了 --selftest、照常跑了默认扫描**，产出 825 键的 A/B/S 报告并 exit=1。
#   ⇒ 危险在于：**它回答的是另一个问题，而读数看起来像答案** ——
#     若那次默认扫描恰好 exit 0，调用者会把「它跑了别的任务」记成「自测通过」。
#   ⇒ 样板：bb-put-both.py 的做法（不认识就干净打用法、exit 2），本段照抄其精神。
_KNOWN = {"--ns", "--limit", "--all", "--version", "-h", "--help"}
_unknown = [a for a in sys.argv[1:] if a.startswith("-") and a not in _KNOWN]
if _unknown:
    sys.exit(f"❌ 不认识的参数: {' '.join(_unknown)}\n"
             f"   本工具接受的参数: {' '.join(sorted(_KNOWN))}\n"
             f"   ★ 本工具【没有】--selftest 入口（明鉴已知未结项，2026-09-28 盘点时发现）——\n"
             f"     这里明确说出来，而不是静默跑默认扫描（那会给你另一个问题的答案）。")

BB = "127.0.0.1:8792"

# ★ 收紧（第一版只抓「词的出现」，实测假阳性极高）：
#   第一版正则 CLAIM = 已落盘|已写入|已修复|已修|... ⇒ 120 键报 28 处 17 张，
#   而看样例：v2.2.0：…已修（历史记录）· 是否已修好（待查问题）·
#   「不是报告已修」（否定式）· 已修好的 20 张（被指对象）—— 三种都不是【声称】。
#   根因与我在 inplace-pointer-audit 第一版犯的同一个错：测的是【词的出现】，
#   要测的是【声称本身】。
# 收紧为：只认【第一人称的完成态声称】——
#   形态 = 「已X」后紧跟【冒号 或 具体对象】，且其前 12 字内没有
#   是否 / 不是 / 未 / 被 / 的 / 版本号 / 引号内的转述标记
CLAIM = re.compile(r"已(?:落盘|写入|修复|同步|完成|投递|部署|上线|合并|推送)")
NEG = re.compile(r"是否|不是|并非|未|被|已在|待|若|如|已修好的|报告已|声称")
VER = re.compile(r"v\d+\.\d+|VERSION|版本")
# 级别词（声明核到哪一级）
LEVEL = re.compile(r"存在级|结构级|内容级|已核|非空|字段数|键集合|指纹|sha256|复算|回读|GET\s*\d|双侧|ver=|\d+\s*B\b|字节")


def enum(ns):
    d = json.loads(urllib.request.urlopen(f"http://{BB}/{ns}", timeout=90).read())
    l = d.get("list", {})
    return list(l.keys()) if isinstance(l, dict) else list(l)


def get(k):
    try:
        with urllib.request.urlopen(f"http://{BB}/{k}", timeout=15) as r:
            return json.loads(r.read())
    except Exception:
        return None


def leaves(v):
    """只取叶子【字符串】，不把子键名当内容。
    修 2026-09-14 实测缺陷①：原实现 json.dumps(val) 把子键名也写进待检文本，
    实例 failure-state-vs-read-the-body-laodeng 命中的是子键名
    「★_全4店失败_即零采集却记为已完成」而非正文。属「对象≠制品」同族。"""
    out = []
    if isinstance(v, str):
        out.append(v)
    elif isinstance(v, list):
        for x in v:
            out.extend(leaves(x))
    elif isinstance(v, dict):
        for _k, val in v.items():
            out.extend(leaves(val))
    return out


SUSPECT_QUOTED = re.compile("[「『“”" + chr(34) + "']$")
SUSPECT_ATTR = re.compile(r"^\s*[的项卡文件版本份条]")
HOMONYM = [("已合并", re.compile(r"版本|VERSION|v\d+\.\d+|[为成]\s?1\s?份|成一条|定义"))]
EVIDENCE = re.compile(r"md5|[0-9a-f]{7,}|回读|复验|回归|重训|一致|哈希|指纹|字节")


def scan(k):
    """返回 (key, fields)；fields = [(字段名, [(词, suspect, evidence, ctx), ...])]
    粒度已改：同字段多次匹配合并为一条 ⇒ 新版「处」= 字段（旧版「处」= 匹配次数）。"""
    env = get(k)
    if not env:
        return None
    v = env.get("value", {})
    if not isinstance(v, dict):
        return None
    fields = []
    for fld, val in v.items():
        hits = []
        for s in leaves(val):
            for m in CLAIM.finditer(s):
                after = s[m.end(): m.end() + 10]
                if not re.match(r"\s*[:：]", after) and not re.search(r"[0-9A-Za-z_\-/]", after):
                    continue
                before = s[max(0, m.start() - 12): m.start()]
                if NEG.search(before) or VER.search(before):
                    continue
                ctx = s[max(0, m.start() - 60): m.end() + 60]
                if LEVEL.search(ctx):
                    continue
                kind = ""
                if SUSPECT_QUOTED.search(s[max(0, m.start() - 1): m.start()]):
                    kind = "quoted"
                elif SUSPECT_ATTR.match(after):
                    kind = "attributive"
                else:
                    for w, pat in HOMONYM:
                        if m.group(0) == w and pat.search(ctx):
                            kind = "homonym"
                            break
                hits.append((m.group(0), kind, bool(EVIDENCE.search(ctx)), ctx.strip()[:90]))
        if hits:
            fields.append((fld, hits))
    return (k, fields) if fields else None


VERSION = "2.0.0"   # 2.0.0 = 2026-09-14 修两处实现缺陷 + 加分档（判据段未改）


def main():
    if "--version" in sys.argv:
        import hashlib
        h = hashlib.sha256(open(__file__, "rb").read()).hexdigest()[:16]
        print("verification-level-lint " + VERSION + " | file_sha256[:16]=" + h
              + " | 判据 CLAIM/NEG/VER/LEVEL 自 v1 起未改")
        return 0
    ns = "data/registry/"
    limit = 0
    if "--ns" in sys.argv:
        ns = sys.argv[sys.argv.index("--ns") + 1]
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    keys = enum(ns)
    if limit:
        keys = keys[:limit]
    print("扫描 " + ns + " · " + str(len(keys)) + " 键 · 判据段未改动（本次仅修实现 + 加分档）")
    with ThreadPoolExecutor(max_workers=24) as ex:
        res = [r for r in ex.map(scan, keys) if r]

    A, B, S = [], [], []
    for k, fields in res:
        for fld, hits in fields:
            if any(h[1] for h in hits):
                S.append((k, fld, hits))
            elif any(h[2] for h in hits):
                B.append((k, fld, hits))
            else:
                A.append((k, fld, hits))
    print("★ 命中字段合计 " + str(len(A) + len(B) + len(S)) + " 个（" + str(len(res)) + " 张卡）—— 新版「处」= 字段，旧版「处」= 匹配次数，不可直接比")
    print("  A 真缺陷（无级别词且无证据）    : " + str(len(A)))
    print("  B 待定  （无级别词但有验证证据）: " + str(len(B)))
    print("  S 疑似  （元讨论/异义/被指对象）: " + str(len(S)) + "   ← 候选非判决，须人工")
    print()

    def show(rows, tag, cap):
        if not rows:
            print("  【" + tag + "】无")
            print()
            return
        print("  【" + tag + "】")
        for k, fld, hits in rows[:cap]:
            ws = "/".join(sorted({h[0] for h in hits}))
            kinds = "/".join(sorted({h[1] for h in hits if h[1]})) or "-"
            print("    " + k.split("/")[-1][:50] + " | " + fld[:24] + " | [" + ws + "] kind=" + kinds)
            print("        …" + hits[0][3][:80] + "…")
        if len(rows) > cap:
            print("    …另有 " + str(len(rows) - cap) + " 个字段")
        print()

    # ★ 2026-09-14 加 --all：HR 标了「未逐张复核 A37 名单」，而原实现只打印前 12 个
    #   ⇒ 那是我的工具缺口，不是 HR 的核对缺口。判据不变，只改打印上限。
    cap = 10 ** 9 if "--all" in sys.argv else 12
    show(A, "A 真缺陷", cap)
    show(B, "B 待定（有证据未命名级别）", 8)
    show(S, "S 疑似（元讨论/异义/被指对象）—— 必须打印，不得静默吞掉", 10)
    print("★ 判读：A/B/S 三档都是【候选而非判决】——")
    print("  A：一段里没有级别词，也可能是它在别处声明了。")
    print("  B：给了哈希/回读/复验等证据但没命名级别 ⇒ 比「已修复」强，仍需读者自判证据强度。")
    print("  S：suspect 由结构判据给出（引号相邻/量词相邻/已知异义表）⇒ 会误判，须人工收口。")
    return 1 if A else 0


if __name__ == "__main__":
    sys.exit(main())
