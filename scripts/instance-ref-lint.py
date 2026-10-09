#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""instance-ref-lint.py — 扫卡片里的「相对指称」实例引用（只读 · 不改任何卡）

为什么需要它（2026-09-13，明鉴与星桥各自自陈）：
  · 明鉴发现自己一直在写「本机 200 / 中央 200」；**「本机」是相对指称** ——
    在 mac-mini 上写就指 mac-mini，而 i9 上的 agent 读到时，指的是**他们那台**。
  · 星桥同一晚也在用「本地/中央」简写；而 `/Users/...` 这类**绝对路径**、以及 `127.0.0.1:8792`
    这类 **loopback**，同样只是「**相对于某个本机的绝对**」——一样缺作用域。
  · 共同结构：**作用域没进标识**。一个伪装成绝对，一个伪装成通用词。
  · 而这类缺陷**只在跨作用域时才显形**，同机读写不会自曝 —— 靠自觉一定会漏。

判据（写死以免自欺）：
  允许：规范实例标识 —— 主机名（mac-mini / mbp / i9 / …）或 `IP:port`
  标红：1) 相对指称词作为实例标签（本机 / 本地 / 中央 / 这台 / local / localhost / central）
        2) 裸绝对路径且同句未给主机名（/Users/... 指哪台机器的 /Users？）
  例外：出现在「规范标识附近」的相对词（同段落 80 字内已有主机名或 IP:port）→ 视为已限定，不标红

用法：
  instance-ref-lint.py <key> [<key> ...]        # 检查指定黑板卡
  instance-ref-lint.py --ns notes/mac-mini --limit 30
  instance-ref-lint.py --file <path> [...]      # 检查本地文件
  instance-ref-lint.py --selftest               # 正反例自证（必须先跑它）

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json
import os
import re
import sys
import urllib.request

BB = os.environ.get("BLACKBOARD_LOCAL", "http://127.0.0.1:8792")

REL_STRICT = ["本机", "这台", "同一台", "localhost", "local instance", "central"]
# ★ 自纠（2026-09-13，读了输出才发现，自证没覆盖）：初版把「该机」放进列表 →
#   命中「该**机制**」的「该机」= **子串误判**（与明鉴 15,396 假阳性同型）。
#   且「本地」可为**修饰语**（本地校验 / 本地代理 / 本地文件），未必是实例引用。
#   现分两级：明确实例引用 = error；疑似修饰语 = soft（提示，不判错）。
REL_CTX = re.compile(r"(本机|本地|中央)\s*(实例|黑板|服务|回读|写入|读取|200|HTTP|端|侧|那台|这台)")
REL_SOFT = re.compile(r"本机|本地|中央")
CANON_HOST = ["mac-mini", "mbp", "i9", "macmini", "VM-0-14-ubuntu"]
CANON_IP = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}:\d{2,5}\b")
ABS_PATH = re.compile(r"(?<![\w:/])(/Users/[\w./-]+|/opt/[\w./-]+|/var/[\w./-]+)")
WINDOW = 80  # 判定"附近已限定"的字符窗口


def has_canonical_near(text, pos):
    lo, hi = max(0, pos - WINDOW), min(len(text), pos + WINDOW)
    seg = text[lo:hi]
    if CANON_IP.search(seg):
        return True
    return any(h in seg for h in CANON_HOST)


def scan_text(name, text):
    """返回 [(level, kind, snippet, pos)] —— level ∈ {error, soft}"""
    hits = []
    seen = []

    def add(level, kind, pos):
        if has_canonical_near(text, pos):
            return
        if pos in seen:          # ★ 只按**同一位置**去重（同一词被 strict/ctx/soft 各匹配一次）；
            return               #   初版写成"邻近 6 字符内即去重" → 把相邻的「本地…中央…」当成一处吞掉（自证抓到）
        seen.append(pos)
        hits.append((level, kind, text[max(0, pos - 30):pos + 30], pos))

    for w in REL_STRICT:
        for m in re.finditer(re.escape(w), text, re.I):
            add("error", "relative-label", m.start())
    for m in REL_CTX.finditer(text):              # 「本地实例 / 本机 200」等明确用法
        add("error", "relative-label", m.start())
    for m in REL_SOFT.finditer(text):             # 其余疑似修饰语
        add("soft", "maybe-modifier", m.start())
    for m in ABS_PATH.finditer(text):
        add("error", "bare-abs-path", m.start())
    return hits
    return hits


def get_card(key):
    with urllib.request.urlopen(f"{BB}/{key.lstrip('/')}", timeout=10) as r:
        d = json.load(r)
    v = d.get("value")
    return json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v


def fetch_ns(ns, limit):
    with urllib.request.urlopen(f"{BB}/{ns.strip('/')}/?limit={limit}", timeout=60) as r:
        d = json.load(r)
    lst = d.get("list") or {}
    return list(lst.keys())[:limit]


def selftest():
    """正反例自证：只自证自己，不自证别人（今晚反复验证：门必须先证明自己可信）"""
    cases = [
        # (文本, 期望 error 数, 期望 soft 数)
        ("回读：本机 200 / 中央 200", 2, 0),                              # 明确实例引用
        ("回读：mac-mini 实例 (127.0.0.1:8792) 200", 0, 0),                # 规范：主机名 + IP:port
        ("验证：本地实例与中央实例各写一次", 2, 0),
        ("主机 mac-mini 上的本机回环即 127.0.0.1:8792", 0, 0),             # 近旁已有规范标识 → 不算歧义
        ("脚本位于 /Users/coreyleung/meituan-multi/scripts/（未标节点）", 1, 0),  # 裸绝对路径
        ("脚本位于 mac-mini 的 /Users/coreyleung/x.py", 0, 0),              # 已限定
        ("该机制是否仍在的探测", 0, 0),                                     # ★ 新增：防「该机」子串误判（该机制）
        ("本地校验是远端合法性的代理", 0, 1),                               # ★ 新增：修饰语 → soft 而非 error
    ]
    ok = 0
    for text, e_err, e_soft in cases:
        hits = scan_text("selftest", text)
        got_err = sum(1 for h in hits if h[0] == "error")
        got_soft = sum(1 for h in hits if h[0] == "soft")
        flag = "✅" if (got_err == e_err and got_soft == e_soft) else "❌"
        if flag == "✅":
            ok += 1
        print(f"  {flag} 期望 error={e_err} soft={e_soft} 实得 error={got_err} soft={got_soft}  ← {text[:46]}")
    print(f"  自证: {ok}/{len(cases)} {'通过' if ok == len(cases) else '未通过 —— 检查器不可信，先修它'}")
    return ok == len(cases)


def main():
    args = sys.argv[1:]
    if "--selftest" in args or not args:
        return 0 if selftest() else 1

    targets = []  # (label, text)
    if "--ns" in args:
        ns = args[args.index("--ns") + 1]
        lim = int(args[args.index("--limit") + 1]) if "--limit" in args else 30
        for k in fetch_ns(ns, lim):
            try:
                targets.append((k, get_card(k)))
            except Exception as e:
                targets.append((k, ""))  # 读不到不算通过
    if "--file" in args:
        for p in args[args.index("--file") + 1:]:
            if p.startswith("-"):
                break
            targets.append((p, open(os.path.expanduser(p), encoding="utf-8").read()))
    keys = [a for a in args if not a.startswith("-") and a not in locals().get("_skip", [])]
    if "--ns" in args or "--file" in args:
        keys = []
    for k in keys:
        targets.append((k, get_card(k)))

    total = 0
    soft_total = 0
    for label, text in targets:
        hits = scan_text(label, text)
        if not hits:
            continue
        errs = [h for h in hits if h[0] == "error"]
        softs = [h for h in hits if h[0] == "soft"]
        total += len(errs); soft_total += len(softs)
        print(f"  {'❌' if errs else '·'} {label}  (error={len(errs)} soft={len(softs)})")
        seen = set()
        for lvl, kind, snip, pos in hits:
            s = snip.replace("\n", " ")
            if s in seen:
                continue
            seen.add(s)
            print(f"       [{'🔴' if lvl == 'error' else '🟡'} {kind}] …{s}…")
    print(f"\n  受检对象 {len(targets)} 个 · 🔴 error {total} 处 · 🟡 soft {soft_total} 处")
    if total:
        print("  → 建议改写为规范标识：<主机名> 实例 (<IP:port>)，例如 mac-mini 实例 (127.0.0.1:8792)")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
