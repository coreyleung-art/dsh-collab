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
        return v if isinstance(v, dict) else (d if isinstance(d, dict) else None)
    except Exception:
        return None


def measure(namespaces, since=None):
    # ★★ 2026-10-13【时间窗】（★ I-1 分层）—★
    #   ★ 立据：分母是【历史全量 642 张】⇒ ★★ **改工具不会让读数立刻变**。
    #   ★ 故加 `--since <时刻缓存串>`（★ 如 `2026-10-13`）⇒ 只算时间窗内的卡。
    since = (since or "").strip() or None
    seen = collections.Counter()          # 字段出现次数
    scanned = 0                           # ★ 真扫过的卡数（分母）
    with_payload = 0
    envelope_ok = 0
    per_ns = {}
    errs = []
    for ns in namespaces:
        keys, ts_map, err = list_ns(ns)
        # ★ 2026-10-13（I-1 分层）：用【外层 ts】过窗（★ ISO 格式，★ 可直接比）
        if since:
            keys = [k for k in keys if str(ts_map.get(k) or '') >= since]
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
            if all(f in v for f in req):
                envelope_ok += 1
    return dict(seen=seen, scanned=scanned, with_payload=with_payload,
                envelope_ok=envelope_ok, per_ns=per_ns, errs=errs)


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
    ap.add_argument("--ns", nargs="*", default=["notes/collab"])
    ap.add_argument("--since", default=None, help="★ 时间窗（如 2026-10-13）：只算该时刻之后的卡")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--lean4-check", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version: print(VERSION); return 0
    if a.selfcheck: return selfcheck()
    if a.lean4_check: return lean4_check()
    r = report(a.ns, as_json=a.json, since=a.since)
    return 0 if r["verdict"] in ("MEASURED", "UNDECIDABLE") else 1


if __name__ == "__main__":
    sys.exit(main())
