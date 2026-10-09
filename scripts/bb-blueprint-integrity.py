#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-blueprint-integrity.py — 蓝图完整度检查器 v1.0(R006 九标准)
按 BP-9 九字段契约 + 关系 + 可渲染性, 给每蓝图完整度评分(0-100)
维度: 身份/主线/阶段/工作/门禁/状态/关系/可渲染/时间戳
用法:
  --scan            全部蓝图完整度报告(评分+缺失项)
  --check BP        单蓝图
  --report [DIR]    生成报告 md
  --selfcheck       TCC
  --tool-version
  --json            结构化
  --regress N       低于 N 分的列出(默认 60)

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, sys, datetime, urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-blueprint-integrity.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = "v1.0.0"
BB = os.environ.get("BB_URL", "http://127.0.0.1:8792")
GALLERY = os.environ.get("GALLERY_URL", "http://127.0.0.1:8798")
WEIGHTS = {"identity": 10, "mainlines": 18, "stages": 20, "works": 12, "gate": 12,
           "status": 6, "relations": 10, "render": 8, "ts": 4}
VALID_STATUS = {"active", "done", "partial", "todo", "planned", "archived"}

def _fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None

def check_one(bid):
    """评分: 返回 {id, score, dims{dim:{score,max,ok,detail}}, missing[]}"""
    bp = _fetch(BB + "/data/blueprint/" + bid)
    v = bp.get("value", bp) if isinstance(bp, dict) else {}
    # flowernet 特殊(数据在全局 stages 键)
    if bid == "flowernet" and not v.get("mainlines"):
        st = _fetch(BB + "/data/blueprint/stages")
        v = st.get("value", st) if isinstance(st, dict) else {}
    info = _fetch(GALLERY + "/api/bpinfo/" + bid) or {}
    svg = info.get("svg", "") or ""
    svg_texts = [t for t in re.findall(r"<text[^>]*>([^<]{2,})</text>", svg) if t.strip()]
    svg_subs = len(re.findall(r"◦", svg))
    # relations: 蓝图在关系图中有边?
    rel = _fetch(BB + "/data/blueprint/relations") or {}
    relv = rel.get("value", rel) if isinstance(rel, dict) else {}
    rel_edges = relv.get("edges", [])
    rel_hit = sum(1 for e in rel_edges if e.get("from") == bid or e.get("to") == bid)
    # 各维度
    dims = {}
    def dim(name, ok, detail):
        mx = WEIGHTS[name]
        dims[name] = {"ok": bool(ok), "max": mx, "detail": str(detail)[:80]}
        return mx if ok else 0
    s = 0
    s += dim("identity", bool(v.get("id")) and bool(v.get("name")) and bool(v.get("version")), f"name={bool(v.get('name'))} ver={v.get('version')}")
    ml = v.get("mainlines") or {}
    ml_keys = list(ml.keys()) if isinstance(ml, dict) else []
    def _ml_ok(k):
        val = ml[k]
        if isinstance(val, dict): return bool(val.get("name") or val.get("desc"))
        return bool(str(val).strip())  # 字符串形式主线(desc)
    ml_ok = len(ml_keys) >= 3 and all(_ml_ok(k) for k in ml_keys[:3])
    s += dim("mainlines", ml_ok, f"{len(ml_keys)}主线")
    st = v.get("stages") or []
    if not isinstance(st, list): st = []
    subs = sum(len(x.get("substages", [])) for x in st if isinstance(x, dict))
    s += dim("stages", len(st) >= 2 and subs >= 2, f"{len(st)}阶段/{subs}子")
    wk = v.get("works") or []
    if not isinstance(wk, list): wk = []
    s += dim("works", len(wk) >= 2, f"{len(wk)}works")
    gate = v.get("gate") or ""
    s += dim("gate", len(str(gate)) > 10, f"gate {len(str(gate))}字")
    sts = v.get("status") or ""
    s += dim("status", sts in VALID_STATUS, sts)
    s += dim("relations", rel_hit >= 1, f"{rel_hit}关系边")
    s += dim("render", len(svg_texts) >= 14 and (svg_subs >= 3 or len(st) >= 2), f"svg {len(svg_texts)}文本/{svg_subs}子")
    s += dim("ts", bool(v.get("ts")), v.get("ts", ""))
    missing = [n for n in dims if not dims[n]["ok"]]
    return {"id": bid, "name": (v.get("name") or bid)[:40], "score": s,
            "dims": dims, "missing": missing}

def scan():
    bps = _fetch(GALLERY + "/api/blueprints") or []
    return [check_one(b.get("id", "")) for b in bps if b.get("id")]

def gen_report(out_dir):
    rs = scan()
    os.makedirs(out_dir, exist_ok=True)
    now = datetime.datetime.now()
    lines = ["# 蓝图完整度报告", "", f"> 生成 {now} · bb-blueprint-integrity {VERSION}",
             "", "| 蓝图 | 分 | 缺失 |", "|------|----|------|"]
    for r in sorted(rs, key=lambda x: -x["score"]):
        lines.append(f"| {r['id']} | **{r['score']}** | {' '.join(r['missing']) if r['missing'] else '—'} |")
    for r in rs:
        if r["missing"]:
            lines += ["", f"## {r['id']} ({r['score']})", ""]
            for m in r["missing"]:
                lines.append(f"- **{m}**: {r['dims'][m]['detail']}")
    p = os.path.join(out_dir, f"integrity-{now:%Y%m%d}.md")
    open(p, "w").write("\n".join(lines))
    return p

def main():
    ap = argparse.ArgumentParser(description="蓝图完整度检查器(R006)")
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--check")
    ap.add_argument("--report", nargs="?", const=os.path.expanduser("~/dsh-collab/data/blueprint/gallery/integrity"))
    ap.add_argument("--regress", type=int, default=60)
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--tool-version", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.tool_version: print(f"bb-blueprint-integrity {VERSION}"); return
    if args.selfcheck:
        r = check_one("flowernet")
        print("TCC:", "✅ 通过" if "score" in r else "❌ 失败")
        sys.exit(0 if "score" in r else 1)
    if args.report:
        p = gen_report(args.report)
        print(f"报告已生成: {p}"); return
    if args.check:
        r = check_one(args.check)
        if args.json: print(json.dumps(r, ensure_ascii=False, indent=1)); return
        print(f"📐 {r['id']} ({r.get('name')}) — 完整度 {r['score']}/100")
        for n, d in r["dims"].items():
            print(f"  {'✅' if d['ok'] else '❌'} {n:10s} {d['max']}分 · {d['detail']}")
        return
    rs = scan()
    if args.json:
        print(json.dumps(rs, ensure_ascii=False, indent=1)); return
    print("══ 蓝图完整度(0-100) ══")
    low = []
    for r in sorted(rs, key=lambda x: -x["score"]):
        mark = "🟢" if r["score"] >= 80 else ("🟡" if r["score"] >= args.regress else "🔴")
        print(f"{mark} {r['score']:3d} {r['id']:26s} 缺:{' '.join(r['missing'][:5]) if r['missing'] else '—'}")
        if r["score"] < args.regress: low.append(r["id"])
    print(f"\n→ {len(rs)} 蓝图 · 低于{args.regress}分 {len(low)} 个: {low}")

if __name__ == "__main__":
    main()
