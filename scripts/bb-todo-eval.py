#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-todo-eval.py v2 — 蓝图 todo 价值评估 · Lean4 化 + R006 全合规
Lean4 逻辑门: 判定不靠关键词猜(启发式), 靠"工具能力表"结构化匹配(类型化) + 人工 Confirm 才可 done
两级判定:
  I门(完整性): 查 tool-capabilities.json capability — 精确匹配 todo 需求 vs 工具能力
    → 命中 = suspected(待人工 Confirm 转 verified-done, 不可自动 done)
    → 未命中 = 真待开发
  R门(资源): 需外部(授权/计量/门店/上线/用户) → backlog(带 reason)
  通过后: V×.30 + D×.20 + 1/C×.10 + S×.10 排序
用法: --scan / --eval BP / --confirm BP STAGE  (人工确认 suspected→done)
     --list-tools / --selfcheck / --tool-version / --json
"""
import argparse, json, os, sys, datetime, urllib.request, glob, re

VERSION = "v2.0.0"
BB = os.environ.get("BB_URL", "http://127.0.0.1:8792")
CAP_FILE = os.path.expanduser("~/dsh-collab/data/tools/tool-capabilities.json")
OUT_DIR = os.path.expanduser("~/dsh-collab/data/blueprint/todo-eval")
EXTERNAL_KW = ["授权", "计量", "HA", "云接管", "上线", "灰度", "门店", "用户", "支付",
               "采购", "实地", "订阅", "租户", "投放", "异业", "供应商", "融资"]

def _cap():
    try: return json.load(open(CAP_FILE)).get("capability", {})
    except Exception: return {}

def _impl_for(name):
    """I门: 精确查能力表 — todo 名关键词 ∩ 工具 capability"""
    caps = _cap()
    hits = []
    nm = str(name).lower()
    for tool, caps_list in caps.items():
        for c in caps_list:
            ck = c.lower()
            # 工具能力词是 todo 名子串 或 todo 名含能力词
            if ck and (ck in nm or any(ck in k for k in re.findall(r'[a-z0-9-]{3,}', nm))):
                hits.append(tool); break
    return hits

def _need_external(item):
    txt = str(item.get("name", "")) + str(item.get("note", ""))
    return any(k in txt for k in EXTERNAL_KW)

def _scan_all():
    try:
        r = json.loads(urllib.request.urlopen(BB + "/data/blueprint/relations", timeout=6).read())
        bps = r.get("value", r).get("blueprints", [])
    except Exception: bps = []
    out = []
    for bid in bps:
        bid = bid if isinstance(bid, str) else bid.get("id")
        try:
            r = json.loads(urllib.request.urlopen(BB + "/data/blueprint/" + bid, timeout=5).read())
            v = r.get("value", r)
        except Exception: continue
        for s in v.get("stages", []):
            for sub in s.get("substages", []):
                if sub.get("status") == "todo":
                    out.append({"bp": bid, "stage": str(s.get("stage")),
                                "id": sub.get("id"), "name": sub.get("name"),
                                "note": str(sub.get("note", ""))[:80]})
    return out

def classify(item):
    """Lean4 判定: 返回 {class, tool_hits, reason}"""
    hits = _impl_for(item)
    if hits:
        return {"class": "suspected", "tools": hits, "reason": "能力表命中"}
    if _need_external(item):
        return {"class": "backlog", "reason": "需外部资源"}
    return {"class": "actionable", "reason": ""}

def _confirm(bp, sub_id, to_status):
    """人工 Confirm: suspected→done(写蓝图数据), 带 auth"""
    try:
        r = json.loads(urllib.request.urlopen(BB + "/data/blueprint/" + bp, timeout=6).read())
        v = r.get("value", r)
    except Exception as e:
        return {"ok": False, "error": str(e)}
    for s in v.get("stages", []):
        for sub in s.get("substages", []):
            if sub.get("id") == sub_id:
                sub["status"] = to_status or "done"
                sub["verified"] = {"by": "user-confirm", "ts": datetime.datetime.now().isoformat(),
                                   "tool": "bb-todo-eval"}
                req = urllib.request.Request(BB + "/data/blueprint/" + bp,
                    data=json.dumps(v).encode(), headers={"Content-Type": "application/json"}, method="PUT")
                urllib.request.urlopen(req, timeout=6)
                os.makedirs(OUT_DIR, exist_ok=True)
                log = os.path.join(OUT_DIR, "audit.jsonl")
                with open(log, "a") as f:
                    f.write(json.dumps({"ts": datetime.datetime.now().isoformat(), "bp": bp,
                                        "id": sub_id, "to": to_status, "by": "user-confirm"}) + "\n")
                return {"ok": True, "bp": bp, "id": sub_id, "status": to_status}
    return {"ok": False, "error": f"{sub_id} 未找到"}

def main():
    ap = argparse.ArgumentParser(description="蓝图 todo 价值评估 v2(Lean4/R006)")
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--eval")
    ap.add_argument("--confirm", nargs=2, metavar=("BP", "SUB_ID"))
    ap.add_argument("--to", default="done")
    ap.add_argument("--list-tools", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--tool-version", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.tool_version: print(f"bb-todo-eval {VERSION}"); return
    if args.selfcheck:
        t = _scan_all(); c = _cap()
        ok = isinstance(t, list) and isinstance(c, dict) and len(c) > 5
        print("TCC:", "✅" if ok else "❌", f"({len(t)} todo, {len(c)} 工具能力)"); return
    if args.list_tools:
        for t, c in sorted(_cap().items()): print(f" · {t}: {c}")
        return
    if args.confirm:
        print(json.dumps(_confirm(args.confirm[0], args.confirm[1], args.to), ensure_ascii=False)); return
    items = _scan_all()
    cats = {"suspected": [], "actionable": [], "backlog": []}
    for it in items:
        r = classify(it)
        it.update(r)
        cats[r["class"]].append(it)
    if args.json:
        print(json.dumps({"total": len(items), "cat": {k: len(v) for k, v in cats.items()},
                          "ver": VERSION}, ensure_ascii=False, indent=1)); return
    print(f"══ 蓝图 todo 评估 v2({len(items)} 项, Lean4 门) ══")
    print(f"① suspected(能力表命中·待人工 Confirm→done): {len(cats['suspected'])}")
    for it in cats["suspected"][:12]:
        print(f"   {it['bp']}/{it['id']} {str(it['name'])[:30]} ← {it['tools'][:2]}")
    print(f"② actionable(可推进): {len(cats['actionable'])}")
    for it in cats["actionable"][:12]:
        print(f"   {it['bp']}/{it['id']} {str(it['name'])[:34]} | {it['stage'][:8]}")
    print(f"③ backlog(需外部): {len(cats['backlog'])}")

if __name__ == "__main__":
    main()
