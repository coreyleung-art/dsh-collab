#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""citation-anchor-scan.py — 跨卡引用锚点扫描（只读）
守灯 2026-09-11 · 起因：一张「关于来源不可信」的卡自身缺来源锚点 ⇒ 规则只是纪律、无机械校验
用途：扫描黑板卡，找出**引用了他卡/他人结论但未记依据锚点**的卡 ⇒ 产出候选清单（**筛候选非定论**）
判据（两条，机器可判）：
  A. `提及他卡键`（data/… 或 notes/…）却**未记录该键的 version** ⇒ 锚点不全（无法判断依据是否被改版）
  B. `归因型数值`（如「（守灯计数）」「据 HR 实测」「明鉴核过」等）**无对应依据键** ⇒ 来源不可追溯
只读保证：仅 GET，不写任一复本
输出：候选清单（含命中项与判据编号）+ 框声明；**"缺锚点"是候选，需人核**（同 gate-auditor 口径）
"""
import json, re, sys, urllib.request, datetime, argparse

BB = "http://127.0.0.1:8792"
KEY_RE = re.compile(r'\b((?:data|notes|tasks)/[A-Za-z0-9][\w./-]{5,})')
# 归因标记：括号内计数/据某人/某人实测/核过 等
ATTR_RE = re.compile(r'(（[^）]{0,12}(计数|统计|实测|核过|提供|确认)[^）]{0,12}）|据\s*(HR|守灯|明鉴|星桥|罗盘|守链|文汇)[^\s，。]{0,8}(实测|统计|计数|核)|(HR|守灯|明鉴|星桥)[^\s，。]{0,6}(已核|核实|实测过))')
VER_RE = re.compile(r'(version|版本|v\s*\d+|@\s*\d{4}-)')
# ★ v0.2 收紧：把「提及他卡键」与「就该卡下了结论」分开
#   首版判据 A = 只要提到他卡键且无 version ⇒ 候选 ⇒ **6000 卡里 1229 候选（20%）**，过宽无用。
#   原因：**「提到路径」是常见的指针行为，不等于「引用其结论」**。
#   收紧后 A′ 仅在**同时**满足时才成立：① 提及他卡键 ② 卡内含归因/结论型标记
#   （计数/实测/核过/结论/依据/据…）③ 无 version/版本锚点。
CLAIM_RE = re.compile(r'(计数|统计|实测|核过|核实|结论|依据|据\s*(HR|守灯|明鉴|星桥|罗盘|守链)|已核|提供)')
# 遥测/机器卡（非「做结论的卡」）——**仅作 triage 过滤并显式声明**，不作用语义判决
AUTO_KEY_RE = re.compile(r'/(v-\d+$|w\d+-\d+$|\d+-\d+$|status-\d+$|current$|heartbeat$|latest$|latest-[a-z]+$)')

def get(path):
    try:
        with urllib.request.urlopen(BB + "/" + path, timeout=60) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception as e:
        return {"_err": str(e)[:80]}

def adjacency_compare(a):
    """v0.6 · 实测「邻接判据 vs 全局出现判据」的效应量（只读，确定性抽样）

    动机（守灯 2026-09-11）：判据 A′ 原用 `VER_RE.search(整卡)` = **全局出现**——
    「卡里出现 version 字样」就认为锚点在。而**正确的锚点必须与所引键相邻**
    （出现 ≠ 附着）。本函数在同一语料上同时算两种判据，报出差额：
      · N_global   = 全局判据下**未**报的卡数（即全局认为「有锚点」）
      · N_adjacent = 邻接判据下**未**报的卡数
      · 差额 = 全局判据的**假阴性来源被反过来读**：差额越大 ⇒ 邻接判据抓出的漏检越多
    并单独计数已知假阳性机制：**匹配到卡自己的 ts**（非引用锚点）。
    """
    W = 200
    ns_list = list(dict.fromkeys(a.ns or ["data"]))   # 去重（--ns 默认与显式传参会叠加）
    rows = []
    for ns in ns_list:
        d = get(ns + "/")
        if "_err" in d:
            print(f"⛔ 无法列举 {ns}/ : {d['_err']}"); return 2
        items = list((d.get("list") or {}).items())
        if a.sample:
            items = sorted(items, key=lambda kv: str(kv[0]))[:a.sample]
        for key, meta in items:
            v = (meta or {}).get("value")
            if not isinstance(v, dict):
                continue
            s = json.dumps(v, ensure_ascii=False)
            refs = [m.group(1) for m in re.finditer(KEY_RE, s) if m.group(1) != key]
            if not refs:
                continue
            if not CLAIM_RE.search(s):
                continue
            own_ts = str((meta or {}).get("ts") or "")
            # ① 全局出现判据（现状）
            global_has_anchor = bool(VER_RE.search(s))
            # ② 邻接判据：锚点须落在某个「所引键」±W 邻域内，且不得是卡自己的 ts
            adjacent_has_anchor = False
            for k in set(refs):
                start = 0
                while True:
                    i = s.find(k, start)
                    if i < 0:
                        break
                    win = s[max(0, i - W): i + len(k) + W]
                    for m in VER_RE.finditer(win):
                        tok = m.group(0)
                        if own_ts and (tok == own_ts or tok in own_ts or own_ts in tok):
                            continue          # 卡自己的 ts ⇒ 非引用锚点（已知假阳性机制）
                        adjacent_has_anchor = True
                        break
                    if adjacent_has_anchor:
                        break
                    start = i + 1
                if adjacent_has_anchor:
                    break
            # ③ 单独计数：全局判据的锚点是不是**只**由自己的 ts 造成的
            own_ts_only = False
            if global_has_anchor and own_ts:
                toks = [m.group(0) for m in VER_RE.finditer(s)]
                if toks and all((t == own_ts or t in own_ts or own_ts in t) for t in toks):
                    own_ts_only = True
            rows.append({"key": key, "global": global_has_anchor,
                         "adjacent": adjacent_has_anchor, "own_ts_only": own_ts_only})
    n = len(rows)
    if n == 0:
        print("样本内无可判卡"); return 0
    ng = sum(1 for r in rows if r["global"])
    na = sum(1 for r in rows if r["adjacent"])
    no = sum(1 for r in rows if r["own_ts_only"])
    only_global = [r["key"] for r in rows if r["global"] and not r["adjacent"]]
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print("── 邻接判据效应量实测（v0.6 · 只读）──")
    print("框: 命名空间=%s ｜ 确定性抽样=%s ｜ 窗口=±%d 字符 ｜ 时点=%s ｜ 谁在测=守灯"
          % (",".join(ns_list), a.sample or "全部", W, ts))
    print("样本内「提及他卡键且含结论型断言」的卡数 N=%d" % n)
    print("  ① **全局出现判据**认为『有锚点』的卡: %d（%.1f%%）" % (ng, 100*ng/n))
    print("  ② **邻接判据**认为『有锚点』的卡: %d（%.1f%%）" % (na, 100*na/n))
    print("  ③ 差额（①多认的）= **邻接判据能抓出而全局判据漏掉的**: %d 张（%.1f%%）"
          % (ng-na, 100*(ng-na)/n))
    print("  ④ 其中**仅由卡自身 ts 充数**的: %d 张（占差额 %.0f%%）"
          % (no, 100*no/max(1, ng-na)))
    step = 1.0/max(1, n)                       # 分母粒度：最小可辨步长
    delta = (ng-na)/n
    print("\n⇒ 效应量判读：全局出现判据把『锚点存在率』**高估** %.1f 个百分点；"
          % (100*delta))
    # ★ 自检（用守灯今日提给 HR 的巧合第四机制「小分母粗粒度」检查本测量自己）
    if abs(delta) < step:
        print("   ⚠ **自检不过**：|Δ|=%.1fpp < 1/N=%.1fpp（分母粒度）⇒ 该接近不足以支持结论"
              % (100*abs(delta), 100*step))
    else:
        print("   ✅ 自检通过：|Δ|=%.1fpp **>** 1/N=%.1fpp（分母粒度）⇒ **不是小分母粗粒度**"
              % (100*abs(delta), 100*step))
    print("   即**『卡里出现过 version 字样』≠『所引键的版本被记录』**（出现 ≠ 附着）。")
    print("\n── 本实测的边界 ──")
    print("   ① 只测 **判据 A′**（引用锚点），不测 B（第三方归因）")
    print("   ② 邻接窗口 ±%d 字符是**约定**，非实测最优；窗口越宽越接近全局判据" % W)
    print("   ③ **单主体、单次**：这是**效应量证据**，不是**独立性证据**（后者需未持有该原则的主体独立复现）")
    print("   ④ 仍为启发式正则，两个方向都有误差；差额**不可读作『精确漏检数』**")
    print("\n样本中差额样例（前 5）:")
    for k in only_global[:5]:
        print("   •", k)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ns", action="append", default=["data", "notes"])
    ap.add_argument("--limit", type=int, default=0, help="每命名空间最多扫 n 卡（0=全部）")
    ap.add_argument("--sample", type=int, default=0,
                    help="确定性抽样：按键名排序后取前 n 张（可复现；0=不抽样）")
    ap.add_argument("--adjacency-compare", action="store_true",
                    help="v0.6：实测『邻接判据』相对『全局出现判据』的效应量（只读）")
    a = ap.parse_args()
    if a.adjacency_compare:
        return adjacency_compare(a)

    frame = {"时点": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "命名空间": a.ns, "限制": a.limit or "全部"}
    candidates = []; scanned = 0; scanned_keys = set()
    for ns in a.ns:
        d = get(ns + "/")
        if "_err" in d:
            print(f"⛔ 无法列举 {ns}/ : {d['_err']}"); return 2
        items = list((d.get("list") or {}).items())
        if a.limit: items = items[:a.limit]
        for key, meta in items:
            if key in scanned_keys: continue
            scanned_keys.add(key)
            v = (meta or {}).get("value")
            try:
                s = json.dumps(v, ensure_ascii=False)
            except Exception:
                continue
            if not isinstance(s, str): continue
            scanned += 1
            auto_card = bool(AUTO_KEY_RE.search(key))
            # 只关心「提及他卡」或「有归因型数值」的卡
            refs = [m.group(1) for m in KEY_RE.finditer(s) if m.group(1) != key]
            attrs = ATTR_RE.findall(s)
            if not refs and not attrs: continue
            if auto_card and not attrs: continue          # triage 过滤：遥测卡无归因 ⇒ 跳过（显式声明）
            hits = []
            has_claim = bool(CLAIM_RE.search(s))
            if refs and has_claim and not VER_RE.search(s):
                hits.append("A′:提及他卡键**且含结论/计数型断言**，但未见 version/版本锚点")
            # ★ v0.3 收紧 B：仅查**第三方**归因
            #   自我适用时发现：我的卡因自陈自己的测量（「实测/统计」）被 B 扫出 14/41 ⇒ **自引不需依据键**
            #   （该卡本身就是来源）⇒ B 只在「被归因方 ≠ 本卡作者」时成立。
            #   局限：`from` 可能缺失或被工具盖章（今晚已知）⇒ from 缺失时**保守仍标**，并注明无法判自/他。
            if attrs and not refs:
                frm = str((v or {}).get("from") or "") if isinstance(v, dict) else ""
                self_names = [p for p in re.split(r'[^A-Za-z0-9\u4e00-\u9fff]+', frm) if len(p) >= 2]
                third_party = (not frm) or (not any(n in s for n in self_names) )
                if third_party:
                    hits.append("B:第三方归因型数值但无可追溯的依据键"
                                + ("（from 缺失，无法判自/他）" if not frm else ""))
            if hits:
                candidates.append({"key": key, "判据": hits,
                                   "提及他卡数": len(set(refs)),
                                   "归因标记数": len(attrs),
                                   "遥测卡": auto_card,
                                   "字节": len(s)})

    print("── 跨卡引用锚点扫描（只读）──")
    print("框声明: 时点=%s ｜ 命名空间=%s ｜ 扫描卡数=%d ｜ 候选=%d"
          % (frame["时点"], ",".join(a.ns), scanned, len(candidates)))
    print("\n[候选清单]（**缺锚点是候选，需人核** —— 同 gate-auditor『筛候选非定论』口径）")
    shown = 0
    for c in candidates:
        if c["遥测卡"]: continue          # 遥测卡单独计数，不占展示位（人工可按需展开）
        shown += 1
        print("   • %s" % c["key"])
        print("     判据=%s ｜ 提及他卡%d ｜ 归因标记%d"
              % ("; ".join(c["判据"]), c["提及他卡数"], c["归因标记数"]))
        if shown >= 20: break
    n_auto = sum(1 for c in candidates if c["遥测卡"])
    if len(candidates) > shown:
        print("   … 共 %d 条（其中遥测/机器卡 %d 条，可按需展开）" % (len(candidates), n_auto))
    print("\n说明：① 判据为**启发式**（正则），必然有误报/漏报 ⇒ 只作候选；"
          "② 修正逐卡需属主同意（HR 立场：扫描属测量、改卡属属主）；③ 只读，未写任何复本")
    # ★ v0.4：把「不可用条件」写进输出（HR 2026-09-11 要求：元层不在扫描范围时，
    #   正确处置不是改代码，而是在输出里声明）——同「判据输出应含其不可用条件」。
    print("\n── 本工具**不覆盖**（不可用条件，逐条如实声明）──")
    print("   ① **自身输出（元层）**：本工具的交付卡若也用缩写引用他卡，**本工具报不出它自己**")
    print("      （自指检查实测：它未命中 `data/cld-health/citation-anchor-scanner-delivery-20260911`）")
    print("   ② **缩写/短名引用**：只识别含 `data/`、`notes/`、`tasks/` 前缀的**全键**；")
    print("      形如「见 dualwrite-population-census」的**短名引用会被漏检**（上一条的成因即此）")
    print("   ③ **version 识别有宽窄两向误差**：窄判据实测**过报 19%**（174 vs 141 候选）；")
    print("      放宽后又会把**键名内嵌版本**误当锚点 ⇒ **两向误差叠加，本清单不可作定论**")
    print("   ④ **遥测/机器卡按 triage 过滤**（键形判据，属便宜特征代理 —— 已声明为 triage 非判决）")
    print("   ⑤ **通道类缺口扫不到**：如 bb-write 删除通道缺口（HR 已裁定归**服务端侧**）")
    print("      这类问题**不在本工具的判据面内**，本工具既不报它、也不能证明它不存在")
    print("   ⑥ **不检查判据本身**：本工具不校验『引用锚点』这一规则是否完备（它只是规则的执行体）")
    # ★ v0.5：把「误差界」写进输出（HR 2026-09-11 推进：不只『不可用条件』(定性)，
    #   还要『误差界』(定量) —— 定性只能防误用，定量才能让人【估价】）。
    print("\n── 误差界（定量 · 含框与时点；**未测的标未测，不推算**）──")
    print("   过报率：**约 19%**（框：data/ 非遥测卡，窄判据 174 vs 宽判据 141 候选；时点 2026-09-11T07:3xZ）")
    print("           —— 成因：只认 `version|版本|v\\d`，把『版本写法不同』也算缺锚点")
    print("   漏报率：**人写类 ≈ 0.00%** ｜ **机器类 ≈ 0.62%**")
    print("           （框：抽样 `data/` 4000 张，seed=7，时点 2026-09-11T07:5xZ；判据=『够长的末段名(≥14字符)』缩写引用）")
    print("           机制：正则只认含 `data/`/`notes/`/`tasks/` 前缀的**全键** ⇒ 缩写引用会被漏；")
    print("           实测漏检**全为机器卡**（`data/ops/queue-condense/*` 自动压缩摘要，25/25），**人写卡 0 例**")
    print("           剩余局限：`notes/` 未抽样（**时点 2026-09-11T07:5xZ ｜ 谁在测=守灯**）；只计 ≥14 字符的末段名 ⇒ 上述为**下界估计**")
    print("   ⇒ 使用指引：本清单**可用于筛候选与估价**，**不可作定论**；据清单改卡前须逐卡人工/属主确认")
    return 0

if __name__ == "__main__":
    sys.exit(main())
