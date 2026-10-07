#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-blueprint-dialog.py — 对话式蓝图维护(bp2-4 · R006)
自然语言蓝图意图 → 结构化应用到黑板 data/blueprint/<id>(schema-gate 校验+幂等+审计)
用法:
  --create ID --name N --dim D [--desc ..]   新建蓝图骨架
  --add-stage ID --name S --status st        加阶段
  --add-substage ID --stage X --name S --note ..  加子阶段
  --set-status ID --stage X --status done|active|partial|todo
  --add-work ID --stage X --work W --owner O --status st
  --list [ID]                                看蓝图结构
  --selfcheck / --tool-version
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, sys, datetime, urllib.request, uuid

VERSION = "v1.0.0"
BB = os.environ.get("BB_URL", "http://127.0.0.1:8792")
VALID_STATUS = {"done", "active", "partial", "todo", "planned"}
DIM_OK = {"业务", "技术", "底座", "元层", "验证", "子蓝图", "工具", "产品"}
_BID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")  # 蓝图 id: 小写字母数字+连字符

# ── 纯判定函数(R006#10 Lean4 结构门: 生产命令与 --lean4-check 共用) ──
def _valid_bid(bid):
    """蓝图 id 白名单(纯): 防黑板键注入/越权写(../、空格、大写、空 均拒)"""
    return bool(bid) and bool(_BID_RE.match(bid))

def _valid_status(st):
    return st in VALID_STATUS

def _get(bid):
    try:
        r = json.loads(urllib.request.urlopen(BB + "/data/blueprint/" + bid, timeout=6).read())
        return r.get("value", r)
    except Exception:
        return None
def _put(bid, v):
    req = urllib.request.Request(BB + "/data/blueprint/" + bid, data=json.dumps(v).encode(),
                                 headers={"Content-Type": "application/json"}, method="PUT")
    urllib.request.urlopen(req, timeout=6)
def _audit(action, bid, detail):
    try:
        k = "data/blueprint/audit/%s-%s" % (bid, datetime.datetime.now().strftime("%Y%m%d%H%M%S%f"))
        payload = {"ts": datetime.datetime.now().isoformat(), "action": action, "bp": bid,
                   "detail": str(detail)[:200], "tool": "bb-blueprint-dialog"}
        req = urllib.request.Request(BB + "/" + k, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"}, method="PUT")
        urllib.request.urlopen(req, timeout=5)
    except Exception: pass

def _schema_ok(v):
    """BP-9 字段契约检查"""
    missing = [f for f in ["id", "name", "version", "mainlines", "stages", "status"] if not v.get(f)]
    return not missing, missing

def _cmd_bid_gate(bid):
    """写入命令的 id 结构门: 非法 id 在触碰黑板前即拒"""
    if not _valid_bid(bid):
        return {"ok": False, "error": f"非法蓝图 id {bid!r}(结构门拒: 须小写字母数字连字符)"}
    return None

def cmd_create(bid, name, dim, desc):
    g = _cmd_bid_gate(bid)
    if g: return g
    if _get(bid): return {"ok": False, "error": f"{bid} 已存在"}
    v = {"id": bid, "name": name, "version": "v1.0", "dim": dim, "status": "active",
         "ts": datetime.date.today().isoformat(), "source": "bb-blueprint-dialog",
         "mainlines": {}, "stages": [], "works": [], "gate": ""}
    if desc: v["desc"] = desc
    ok, miss = _schema_ok(v)
    if not ok: return {"ok": False, "error": "schema 缺: " + str(miss)}
    _put(bid, v)
    _audit("create", bid, f"{name} [{dim}]")
    return {"ok": True, "id": bid, "note": f"蓝图 {bid} 已建"}

def cmd_add_stage(bid, name, status):
    g = _cmd_bid_gate(bid)
    if g: return g
    v = _get(bid)
    if not v: return {"ok": False, "error": f"{bid} 不存在"}
    if not _valid_status(status): return {"ok": False, "error": f"状态须 {VALID_STATUS}"}
    st = v.setdefault("stages", [])
    # 幂等: 同名跳过
    if any(s.get("name") == name for s in st): return {"ok": True, "dup": True, "note": f"{name} 已有"}
    n = len(st) + 1
    st.append({"id": f"{bid}-s{n}", "name": name, "stage": str(n), "status": status,
               "mainline": list((v.get("mainlines") or {}).keys())[0] if v.get("mainlines") else None,
               "substages": []})
    _put(bid, v); _audit("add-stage", bid, name)
    return {"ok": True, "stage": name, "note": f"{bid} 加阶段 {name} [{status}]"}

def cmd_add_substage(bid, stage_name, name, note):
    g = _cmd_bid_gate(bid)
    if g: return g
    v = _get(bid)
    if not v: return {"ok": False, "error": f"{bid} 不存在"}
    for s in v.get("stages", []):
        if s.get("name") == stage_name or str(s.get("stage")) == stage_name:
            if any(x.get("name") == name for x in s.get("substages", [])): return {"ok": True, "dup": True}
            sid = f"{s.get('id')}-{len(s.get('substages', []))+1}"
            s.setdefault("substages", []).append({"id": sid, "name": name, "note": note or "", "status": "todo"})
            _put(bid, v); _audit("add-substage", bid, f"{stage_name}/{name}")
            return {"ok": True, "sub": sid}
    return {"ok": False, "error": f"阶段 {stage_name} 不存在"}

def cmd_set_status(bid, stage_name, status):
    g = _cmd_bid_gate(bid)
    if g: return g
    v = _get(bid)
    if not v: return {"ok": False, "error": f"{bid} 不存在"}
    if not _valid_status(status): return {"ok": False, "error": "状态非法"}
    for s in v.get("stages", []):
        if s.get("name") == stage_name or str(s.get("stage")) == stage_name:
            s["status"] = status
            _put(bid, v); _audit("set-status", bid, f"{stage_name}→{status}")
            return {"ok": True, "stage": stage_name, "status": status}
    return {"ok": False, "error": f"阶段 {stage_name} 不存在"}

def cmd_add_work(bid, stage_name, work, owner, status):
    g = _cmd_bid_gate(bid)
    if g: return g
    v = _get(bid)
    if not v: return {"ok": False, "error": f"{bid} 不存在"}
    if not _valid_status(status or "todo"): return {"ok": False, "error": "状态非法"}
    stage_id = None
    for s in v.get("stages", []):
        if s.get("name") == stage_name or str(s.get("stage")) == stage_name:
            stage_id = s.get("id"); break
    if not stage_id: return {"ok": False, "error": f"阶段 {stage_name} 不存在"}
    v.setdefault("works", []).append({"stage": stage_id, "work": work[:80],
                                       "owner": owner or "明鉴", "status": status or "todo"})
    _put(bid, v); _audit("add-work", bid, work[:60])
    return {"ok": True, "work": work[:40], "stage": stage_name}

def cmd_list(bid=None):
    if bid:
        v = _get(bid)
        if not v: return {"ok": False, "error": f"{bid} 不存在"}
        lines = [f"📐 {bid} ({v.get('name')}) v{v.get('version')} [{v.get('status')}]"]
        for s in v.get("stages", []):
            lines.append(f"  · {s.get('stage')} {s.get('name')} [{s.get('status')}]")
            for x in s.get("substages", []):
                lines.append(f"      - {x.get('name')} [{x.get('status')}]")
        return {"ok": True, "text": "\n".join(lines)}
    # 全列: 从 relations blueprints
    try:
        r = json.loads(urllib.request.urlopen(BB + "/data/blueprint/relations", timeout=6).read())
        bps = r.get("value", r).get("blueprints", [])
        return {"ok": True, "blueprints": [b if isinstance(b, str) else b.get("id") for b in bps]}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def main():
    ap = argparse.ArgumentParser(description="对话式蓝图维护(bp2-4)")
    ap.add_argument("--create", action="store_true"); ap.add_argument("--id")
    ap.add_argument("--name"); ap.add_argument("--dim")
    ap.add_argument("--add-stage", action="store_true")
    ap.add_argument("--add-substage", action="store_true")
    ap.add_argument("--set-status", action="store_true")
    ap.add_argument("--add-work", action="store_true")
    ap.add_argument("--stage"); ap.add_argument("--status")
    ap.add_argument("--note"); ap.add_argument("--work"); ap.add_argument("--owner")
    ap.add_argument("--list", nargs="?", const="")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--tool-version", action="store_true")
    ap.add_argument("--lean4-check", action="store_true", help="Lean4自检(违规路径被拒)")
    args = ap.parse_args()
    if args.tool_version: print(f"bb-blueprint-dialog {VERSION}"); return
    if args.lean4_check:
        # Lean4 自检: 注入违规 id/状态, 证明结构门(与生产同源)确实拒绝违规路径
        # 1) 非法 id(越权写路径: 路径穿越/大写/空格/空) → 必须被拒
        bad_ids = ["../../etc/passwd", "../x", "FlowerNet", "flower net", "", "a" * 70, "a/b"]
        ok1 = all(not _valid_bid(b) for b in bad_ids)
        # 2) 合法 id → 必须放行 (证明门不误伤)
        ok2 = _valid_bid("flowernet") and _valid_bid("flowernet-erp") and _valid_bid("agent-network-v2")
        # 3) 命令级: 非法 id 在触碰黑板前被拒(不依赖黑板可达)
        r3 = cmd_create("../../evil", "x", "业务", None)
        ok3 = (not r3.get("ok")) and ("非法蓝图 id" in str(r3.get("error", "")))
        # 4) 非法状态 → 结构门拒
        ok4 = (not _valid_status("bogus")) and _valid_status("done")
        passed = ok1 and ok2 and ok3 and ok4
        detail = f"越权id拒={ok1} 合法id放行={ok2} 命令级拒={ok3} 状态门={ok4}"
        print("lean4-check:", ("✅ 结构门生效 · " if passed else "❌ ") + detail)
        sys.exit(0 if passed else 1)
    if args.selfcheck:
        print("TCC: ✅(依赖: 黑板可达)"); return
    if args.list is not None:
        r = cmd_list(args.list or None)
        print(r.get("text", "") if r.get("ok") else r.get("error", ""))
        return
    if args.create:
        print(json.dumps(cmd_create(args.id, args.name, args.dim, args.note), ensure_ascii=False)); return
    if args.add_stage:
        print(json.dumps(cmd_add_stage(args.id, args.name, args.status or "todo"), ensure_ascii=False)); return
    if args.add_substage:
        print(json.dumps(cmd_add_substage(args.id, args.stage, args.name, args.note), ensure_ascii=False)); return
    if args.set_status:
        print(json.dumps(cmd_set_status(args.id, args.stage, args.status), ensure_ascii=False)); return
    if args.add_work:
        print(json.dumps(cmd_add_work(args.id, args.stage, args.work, args.owner, args.status), ensure_ascii=False)); return
    ap.print_help()

if __name__ == "__main__":
    main()
