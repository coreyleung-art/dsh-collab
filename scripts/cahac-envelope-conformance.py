#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cahac-envelope-conformance.py — CAHAC §3 统一信封【字段级符合度】测量（W8.1 建尺）

用法:
  python3 scripts/cahac-envelope-conformance.py                 # 默认扫 notes/collab
  python3 scripts/cahac-envelope-conformance.py --ns notes/collab data/registry
  python3 scripts/cahac-envelope-conformance.py --selfcheck     # 负控矩阵
  python3 scripts/cahac-envelope-conformance.py --lean4-check   # 约束门 A–F

★ 设计要点（★ 来自 2026-10-12 台账 D-116/D-117/D-119 的教训）：
  ★★ 三态纪律 —— 分母为 0 ⇒ 判 **UNDECIDABLE**，**不得报 0%**（0% 与「不可判」语义不同）
  ★★ 空分母护栏必须在【判据侧】，不在现象侧
  ★★ 报「0 条」必须连【扫过的面】一起打印
"""
import sys, json, os, argparse, urllib.request, collections

VERSION = "1.0.0"
BB = os.environ.get("DSH_BB_URL", "http://127.0.0.1:8792")

# ★ CAHAC §3 的 14 字段（★ 源：research/cost-governance/cahac-protocol-v1.2.md:128-145）
FIELDS = ["cahac","id","type","channel","sender","recipient","thread",
          "priority","cost_cap","dedup_key","ts","expires","payload","signature"]

# ★ 必填（★ 依 §3 字段规则：signature v1.0【可选】· expires【可选】）
OPTIONAL = {"signature","expires"}

# ★★ 2026-10-13（D-331）：规格的【规范值】（★ `cahac-protocol-v1.2.md:130` 逐字 `"cahac": "1.2"`）
CANON_VERSION = "1.2"


def fetch_json(url, timeout=12):
    req = urllib.request.Request(url)
    tok = os.path.expanduser("~/.dsh/blackboard-token")
    if os.path.exists(tok):
        try:
            req.add_header("Authorization", open(tok).read().strip())
        except Exception:
            pass
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def list_ns(ns):
    """列命名空间的键（★ 返回 (keys, ts_map, err)）

    ★★ 2026-10-13 修（★ 实测）：**换成返回外层 ts** —★
      ★ 立据：卡自带的 `value.ts` 是 **epoch 数字**（★ 实测 `1788093978`）—★
        ★★ 而【外层 ts】是 **ISO 格式**（★ `2026-10-13T06:24:11`）⇒ 可直接比。
      ★ 且 list 本就带 ts ⇒ **不多一次请求**。
    """
    try:
        d = fetch_json("%s/%s/" % (BB, ns))
        lst = d.get("list") or {}
        ts_map = {}
        for k, v in lst.items():
            if isinstance(v, dict):
                ts_map[str(k)] = str(v.get("ts") or "")
        return sorted(lst.keys()), ts_map, None
    except Exception as e:
        return [], {}, "%s: %s" % (type(e).__name__, str(e)[:80])


def card_value(ns, key):
    try:
        d = fetch_json("%s/%s" % (BB, key))
        v = d.get("value")
        # ★ 修正措辞：下面打印的是【真卡】不是「实际取到信封对象」
        # ★★★ 2026-10-13 修（D-331）：**不得回退返回外层响应**—★
        #   ★ 立据：实测有 **69 条** value 非 dict，★ 而原写法
        #     ★ `return v if isinstance(v, dict) else (d if isinstance(d, dict) else None)`—★
        #     ★★ 会把外层响应 `d`（★ 仍是 dict）当卡计入分母。
        #   ★ 修法：**value 非 dict ⇒ 返回 None**（★ 不计入）。
        return v if isinstance(v, dict) else None
    except Exception:
        return None


WINDOW_STATS = {}          # ★ D-431：最近一次过窗的三态计数（★ 供 `--window-stats` 读取，★ 不改 JSON 主输出形状）


def _window_admit(inner_ts, outer_ts, since):
    """★★★ 2026-10-15（D-431）【时间窗判据：★ 必须读【内层 value.ts】，★ 不能只读板级 ts】——

    ★ 立据（★ 本线实测的因果链，★ 不是推演）：★ 本线回填 28 张 `manager-actions` 旧卡的署名声明
      （★ 内容原样保留、★ 只加两格）⇒ ★★ **板级 ts 被这次重写顶到当天**
      ⇒ ★ 本判据按【外层 ts】过窗 ⇒ 那 28 张**旧卡**被算进「今日窗」
      ⇒ ★ 本机侧分母 **37 → 65**、符合度 **73% → 41.5%** ⇒ ★★ **跌破 50% 阈 ⇒ 判据由 SKIP 转 FAIL**
      （★ 一条红被我【合法但无关】的动作带出来了）。
    ★★ 而本仓对此**早有纪律**：★ **R062②** 逐字 —— ★「板级 `ts` 会被归档覆盖 ⇒ 凡按板级 ts
      计龄/排序的读者**必须同时读内层 `value.ts` 并报两者之差**」。★ 本判据当时**没照做**。
    ★ 故本函数给出【三态】判读（★ 纯函数 ⇒ 可单测）：
      · `inner` ≥ since ⇒ **in**（★ 真·窗内卡）；
      · `inner` 缺失 ⇒ 回退外层 ⇒ **in_outer_fallback**（★ 如实标注口径）；
      · 外层 ≥ since **而** 内层 < since ⇒ **bumped_out**（★ **被重写顶进窗口的旧卡** ⇒ ★ 不计入）；
      · 其余 ⇒ **out**。
    ★★ 声明的面限度：★ 本函数只在【外层已过窗】的候选上做内层精判 ⇒ ★ **外层旧、内层新**的卡
      不会被捞回（★ 那是另一种形态，★ 本条未覆盖 —— 见 `D-431`）。
    """
    i = (inner_ts or "").strip()
    o = (outer_ts or "").strip()
    if i and i >= since:
        return "in", "内层 value.ts 在窗内"
    if i and i < since and o >= since:
        return "bumped_out", "★ 外层 ts 在窗内而内层不在 ⇒ 疑为重写顶入的旧卡"
    if not i and o >= since:
        return "in_outer_fallback", "★ 无内层 ts ⇒ 回退外层（★ 口径如实标注）"
    return "out", "不在窗内"


def measure(namespaces, since=None):
    # ★★ 2026-10-13【时间窗】（★ I-1 分层）—★
    #   ★ 立据：分母是【历史全量 642 张】⇒ ★★ **改工具不会让读数立刻变**。
    #   ★ 故加 `--since <时刻缓存串>`（★ 如 `2026-10-13`）⇒ 只算时间窗内的卡。
    since = (since or "").strip() or None
    seen = collections.Counter()          # 字段出现次数
    window_stats = {}                     # ★ D-431：过窗三态计数（in / in_outer_fallback / bumped_out）
    scanned = 0                           # ★ 真扫过的卡数（分母）
    with_payload = 0
    envelope_ok = 0
    per_ns = {}
    errs = []
    for ns in namespaces:
        keys, ts_map, err = list_ns(ns)
        # ★ 2026-10-13（I-1 分层）：用【外层 ts】过窗 —— ★★ 2026-10-15（D-431）**改为内层优先**：
        #   ★ 外层只作【候选初筛】，★ 命中的候选再读**内层 `value.ts`** 精判（★ 依 R062②）。
        if since:
            keys = [k for k in keys if str(ts_map.get(k) or '') >= since]
            _kept = []
            for k in keys:
                _v = card_value(ns, k)
                _iv = None
                _vv = _v
                for _ in range(3):                    # ★ 兼收双层包裹的卡形
                    if isinstance(_vv, dict) and isinstance(_vv.get("ts"), str):
                        _iv = _vv["ts"]; break
                    _vv = _vv.get("value") if isinstance(_vv, dict) else None
                _adm, _whyw = _window_admit(_iv, str(ts_map.get(k) or ""), since)
                window_stats[_adm] = window_stats.get(_adm, 0) + 1
                if _adm in ("in", "in_outer_fallback"):
                    _kept.append(k)
            keys = _kept
        if err:
            errs.append(err); per_ns[ns] = "ERR"; continue
        per_ns[ns] = len(keys)
        for k in keys:
            # ★ 只取卡（★ value 是 dict 且有 type/sender 之类信封迹象，或任意 dict）
            v = card_value(ns, k)
            if not isinstance(v, dict):
                continue
            scanned += 1
            hit = [f for f in FIELDS if f in v]
            for f in hit:
                seen[f] += 1
            if "payload" in v:
                with_payload += 1
            # ★ envelope_ok = 全部【必填】字段齐（★ 可选字段不计）
            req = [f for f in FIELDS if f not in OPTIONAL]
            # ★★★ 2026-10-13 修（D-331）：**不只查存在性，★ 还查 `cahac` 的值**—★
            #   ★ 立据：规格 `:130` 规范值是 **`"1.2"`**，
            #     ★★ 而实测在库分布 `{"v1.2": 38, "1.0": 11}` ⇒ **`"1.2"` 出现 0 次**。
            #   ★ 故旧判据【只查存在性】⇒ 同类偏差永远测不出来。
            _cahac_val = v.get("cahac")
            _val_ok = (_cahac_val in (None, CANON_VERSION))
            if all(f in v for f in req) and _val_ok:
                envelope_ok += 1
    return dict(seen=seen, scanned=scanned, with_payload=with_payload,
                envelope_ok=envelope_ok, per_ns=per_ns, errs=errs,
                window_stats=window_stats)          # ★ D-431：把口径与「顶入」计数报出来


def report(namespaces, as_json=False, since=None):
    m = measure(namespaces, since=since)
    scanned = m["scanned"]
    out = {"version": VERSION, "namespaces": namespaces,
           "scanned": scanned, "per_namespace": m["per_ns"], "errors": m["errs"],
           "fields": {f: m["seen"][f] for f in FIELDS}}
    # ★★ 三态判定（★ 空分母护栏）
    if scanned == 0:
        out["verdict"] = "UNDECIDABLE"
        out["reason"] = ("★ 分母为 0：扫过 %d 个命名空间但【没有取到任何信封对象】"
                         " ⇒ 本项【不可判】，★ 不得读作 0%% 或通过" % len(namespaces))
        out["envelope_ok_rate"] = None
    else:
        out["verdict"] = "MEASURED"
        out["envelope_ok"] = m["envelope_ok"]
        out["envelope_ok_rate"] = round(m["envelope_ok"] / scanned, 6)
        out["reason"] = None
    if as_json:
        print(json.dumps(out, ensure_ascii=False, indent=1)); return out
    print("== cahac-envelope-conformance %s ==" % VERSION)
    print()
    # ★★★ 2026-10-13 补（D-327）：**时间窗必须与【面】同级打印**—★
    #   ★ 立据：本纳 D-324 的表里并列了两个**不同的时间窗**（★ 带窗 0/338 与不带窗 24/18826）
    #     ★★ 而未申报 ⇒ 同表两行口径不同（★ 差 2.1 倍）。
    print("【时间窗（★ 与【面】同级；★ 换窗即换口径）】")
    print("    since = %s" % (since if since else "（无 ⇒ 全时段）"))
    print()
    print("【扫过的面（★ 每个数字必须跟它一起报）】")
    for ns, n in m["per_ns"].items():
        print("  %-24s %s" % (ns, n if n != "ERR" else "★ 读取失败"))
    for e in m["errs"]:
        print("  ★ 错误: %s" % e)
    print("  ⇒ 实际取到信封对象（★ 分母）: %d" % scanned)
    print()
    print("【逐字段出现率】")
    for f in FIELDS:
        c = m["seen"][f]
        opt = "（★ 可选）" if f in OPTIONAL else ""
        pct = ("%.1f%%" % (100.0 * c / scanned)) if scanned else "★ 不可判"
        print("  %-12s %6d / %-6d %s%s" % (f, c, scanned, pct, opt))
    print()
    print("【判定（★ 三态）】")
    # ★★★ 2026-10-15（D-348）【分层：本机侧 vs 跨设备中继侧】—★
    #   ★ 立据（D-347）：合成 0.9% 会掩盖「本机侧已 100% 达标」这个事实—★
    #     ★ 而让人误以为【本机有缺陷】。
    try:
        print()
        print("【分层（★ 本机可修 vs 外设备需接入）】")
        _sep = split_tiers(since)
        for _name, _a, _b in _sep:
            _r = (100.0 * _a / _b) if _b else None
            print("    %-38s %5d/%-5d  %s" % (_name, _a, _b,
                  ("%6.2f%%" % _r) if _r is not None else "不可判"))
    except Exception as _e:
        print("    ★ 分层计算失败：%s ⇒ 不可判" % (repr(_e)[:120]))

    if scanned == 0:
        print("  ★★ UNDECIDABLE —— %s" % out["reason"])
    else:
        print("  MEASURED —— envelope_ok = %d / %d = %.4f%%"
              % (m["envelope_ok"], scanned, 100.0 * out["envelope_ok_rate"]))
        print("  （★ envelope_ok = 全部【必填】字段齐；signature/expires 为可选，不计）")
    return out


def selfcheck():
    """负控矩阵：每条判据必须能红"""
    print("== 负控矩阵（★ 判据必须能红）==")
    ok = 0; tot = 0
    # ① 空分母必须报 UNDECIDABLE（★ 不得报 0%）
    tot += 1
    r = report(["data/__nonexistent_ns__"], as_json=True)
    a = (r["verdict"] == "UNDECIDABLE" and r["envelope_ok_rate"] is None)
    print("  %s ① 空分母 ⇒ UNDECIDABLE 且 rate=None  %s" % ("OK " if a else "★ 不成立", r["verdict"]))
    ok += a
    # ② 字段表必须恰 14 项
    tot += 1; a = (len(FIELDS) == 14)
    print("  %s ② CAHAC §3 字段数恰为 14（实测 %d）" % ("OK " if a else "★ 不成立", len(FIELDS))); ok += a
    # ③ 可选字段不得计入 envelope_ok 必填
    tot += 1; a = ("signature" in OPTIONAL and "expires" in OPTIONAL and "payload" not in OPTIONAL)
    print("  %s ③ signature/expires 为可选，payload 为必填" % ("OK " if a else "★ 不成立")); ok += a
    # ④ 报 0 必须附面（★ 检查输出含「扫过的面」）
    tot += 1
    import io as _io, contextlib
    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf):
        report(["data/__nonexistent_ns__"])
    a = "扫过的面" in buf.getvalue()
    print("  %s ④ 报 0 时输出含【扫过的面】" % ("OK " if a else "★ 不成立")); ok += a
    # ⑤ 必需字段集恰 12（14 − 2 可选）
    tot += 1; a = (len([f for f in FIELDS if f not in OPTIONAL]) == 12)
    print("  %s ⑤ 必填字段恰 12（14 − 2 可选）" % ("OK " if a else "★ 不成立")); ok += a
    # ★★★ 2026-10-15（D-378）【异源用例】—★ 四维判据相关工具补齐
    try:
        import sys as _sysE
        _sysE.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/tools")
        from extcase import extcase_selftest as _ecs
        _ec_ok, _ec_tot, _ec_msg = _ecs("cahac-envelope-conformance.py")
        print(_ec_msg)
        if _ec_ok is None:
            print("  ❓ 异源用例 ⇒ **不可判**")
        else:
            ok += _ec_tot; tot += _ec_tot
    except Exception as _eE:
        print("  ❓ 异源用例 ⇒ 不可判（%s）" % type(_eE).__name__)

    print("\n== 负控 %d/%d ==" % (ok, tot))
    return 0 if ok == tot else 1


def lean4_check():
    """约束门 A–F（★ 与 W7 提案同型）"""
    import re
    src = open(__file__, encoding="utf-8").read()
    print("== --lean4-check（A–F）==")
    res = []
    def chk(name, cond, why):
        res.append((name, bool(cond), why))
    code = re.sub(r'"""(?:.|\n)*?"""', "", src)          # 剥 docstring
    code = re.sub(r"(?m)^\s*#.*$", "", code)             # 剥注释
    # ★★★ 致命一步：判据的面必须【排除判据自身】
    #   ★ 本函数体内含 "rmtree" / "FIELDS =" 等字面串
    #   ★ 不剔除 ⇒ 自指污染 ⇒ A/E/F 三项误判（★ 2026-10-12 实测）
    _i = code.find("def lean4_check")
    if _i > 0:
        code = code[:_i]
    chk("A 无删除原语", not re.search(r"\b(rmtree|os\.remove|os\.unlink|shutil\.rmtree)\b", code), "只读测量器")
    chk("B 无写盘", not re.search(r"\bopen\([^)]*['\"][wa]", code), "不落盘")
    chk("C 无危险原语", not re.search(r"\b(eval|exec|__import__)\s*\(", code), "无动态执行")
    chk("D 空分母有护栏", "UNDECIDABLE" in code and "scanned == 0" in code, "三态")
    chk("E 字段表单一来源", code.count("FIELDS =") == 1, "无重复定义")
    chk("F 版本单一来源", code.count("VERSION =") == 1, "无重复定义")
    ok = sum(1 for _, c, _ in res if c)
    for n, c, w in res:
        print("  %s %-22s（%s）" % ("OK " if c else "★ 不成立", n, w))
    print("\n== lean4 %d/%d ==" % (ok, len(res)))
    return 0 if ok == len(res) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiers", action="store_true")   # ★★ 2026-10-15（D-349）只输出分层
    ap.add_argument("--window-stats", action="store_true")  # ★ D-431：只报过窗口径（in/回退/顶入被排除）
    # ★★★ 2026-10-13 修（D-324）：**默认改为扫【全部 `notes/`】**—★
    #   ★ 立据：原默认只扫 `notes/collab`（★ 653 锠），
    #     ★★ 而 `notes/` 共 **18825** 锠 ⇒ **`collab` 只占 3.5%**—★
    #     ★ 故只扫它必然失真（★ 实测：collab 0/338，★ 而全域 **23/18825**）。
    #   ★ 保留 `--ns` 供显式指定；★只改默认。
    ap.add_argument("--ns", nargs="*", default=["notes/"])
    ap.add_argument("--since", default=None, help="★ 时间窗（如 2026-10-13）：只算该时刻之后的卡")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--lean4-check", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if getattr(a, "window_stats", False):
        split_tiers(a.since)
        print(json.dumps({"window_stats": WINDOW_STATS, "since": a.since,
                          "★ 判据": "in=内层 ts 在窗内 · in_outer_fallback=无内层 ts 故回退外层 · "
                                  "bumped_out=外层在窗内而内层不在（★ 疑为重写顶入的旧卡，★ 已排除）· out=初筛出局"},
                         ensure_ascii=False, indent=1))
        return 0
    if getattr(a, "tiers", False):
        import json as _j
        _out = split_tiers(a.since)
        print(_j.dumps([{"name": x, "ok": y, "total": z} for x, y, z in _out], ensure_ascii=False))
        return 0
    if a.version: print(VERSION); return 0
    if a.selfcheck: return selfcheck()
    if a.lean4_check: return lean4_check()
    r = report(a.ns, as_json=a.json, since=a.since)
    return 0 if r["verdict"] in ("MEASURED", "UNDECIDABLE") else 1


def split_tiers(since=None):
    """★★★ 2026-10-15（D-348）【分层】—★ 本机可修侧 vs 跨设备中继侧。

    ★ 立据（D-347）：
      ★ 本机 `notes/mac-mini` 面 = **3/3 = 100%**（★ 本线通道已达标）；
      ★ 而那 **317 张全部带 `_via=comm-central`**（★ 中继写入的传输标记）—★
        ★★ 而本机【无写点】（★ 全盘搜索只命中文档说明）⇒ 写在外设备侧。
    ★ 故拆两层，★ **不得合成一个数**（★ 否则会掩盖「本机已达标」）。
    """
    keys = []
    _tsmap = {}
    for ns in ("notes/", "data/", "tasks/"):
        ks, tm, err = list_ns(ns)
        if not err:
            keys += ks
            if isinstance(tm, dict):
                _tsmap.update(tm)
    # ★★ 2026-10-15（D-348）：**必须带窗**（★ 否则分层与上方总数口径不同）—★
    # ★★★ 2026-10-15（D-431）：★ **本函数原先【只读板级 ts】** ⇒ ★★ 而板级 ts 会被【重写】顶到当天
    #   ⇒ ★ 本线回填 28 张旧卡后，它们被算进「今日窗」⇒ 本机侧分母 37 → 65、符合度 73% → 41.5%
    #   ⇒ **跌破 50% 阈 ⇒ 判据 SKIP → FAIL**（★ 一条红被【合法但无关】的动作带出）。
    #   ★★ 依 **R062②**：★「板级 `ts` 会被归档覆盖 ⇒ 凡按板级 ts 计龄/排序者**必须同时读内层
    #     `value.ts`** 并报两者之差」⇒ ★ 本函数**当时没照做**。★ 现改为【外层初筛 + 内层精判】，
    #     ★ 并把三态计数落到模块级 `WINDOW_STATS`（★ 不改进本函数的返回形状 —— ★ 它是 beacon 解析的 JSON）。
    global WINDOW_STATS
    _wstats = {}
    if since:
        _s10 = str(since)[:10]
        _kept = []
        for k in keys:
            _o = str(_tsmap.get(str(k)) or "")[:10]
            if _o < _s10:
                _wstats["out"] = _wstats.get("out", 0) + 1
                continue
            _v0 = card_value("/".join(str(k).split("/")[:2]) + "/", k)
            _iv, _vv = None, _v0
            for _ in range(3):
                if isinstance(_vv, dict) and isinstance(_vv.get("ts"), str):
                    _iv = _vv["ts"][:10]; break
                _vv = _vv.get("value") if isinstance(_vv, dict) else None
            _adm, _why = _window_admit(_iv, _o, _s10)
            _wstats[_adm] = _wstats.get(_adm, 0) + 1
            if _adm in ("in", "in_outer_fallback"):
                _kept.append(k)
        keys = _kept
    WINDOW_STATS = _wstats
    a_loc = b_loc = a_rel = b_rel = 0
    for k in keys:
        ns = "/".join(str(k).split("/")[:2]) + "/"
        try:
            v = card_value(ns, k)
        except Exception:
            v = None
        if not isinstance(v, dict):
            continue
        # ★★ 2026-10-15（D-348）修：**必须用【必填】而非全字段**—★
        #   ★ 立据：`FIELDS` 含 `expires`/`signature`，★ 而它们是 `OPTIONAL`—★
        #     ★★ 故用 `FIELDS` 判会让每张卡都“缺 2 项” ⇒ **永远 0%**（★ 实测误报 0/3）。
        _need = [f for f in FIELDS if f not in OPTIONAL]
        ok = all((f in v) and (f == "thread" or v.get(f) not in (None, "")) for f in _need)
        p = str(k).split("/")
        seg1 = p[1] if len(p) >= 2 else ""
        if seg1 == "mac-mini":
            b_loc += 1
            if ok:
                a_loc += 1
        elif v.get("_via") == "comm-central" or seg1 == "i9":
            b_rel += 1
            if ok:
                a_rel += 1
    return [("① 本机侧（notes/mac-mini）★ 本线可修", a_loc, b_loc),
            ("② 跨设备中继侧（_via=comm-central / i9）", a_rel, b_rel)]



if __name__ == "__main__":
    sys.exit(main())

