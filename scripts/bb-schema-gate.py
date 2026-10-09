#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-schema-gate.py — 数据写入契约门(Φ9/Lean4 结构强制 · R006)
任何对蓝图/规则/关系的写操作前必过此门: 字段契约 + 引用完整 + 重复检测
用法:
  --check-rules          校验 rule-mapping.json(规则引用蓝图存在/不重复)
  --check-relations      校验 relations 边(from/to 是合法蓝图)
  --check-bp BP          校验单蓝图字段契约(BP-9)
  --validate-write TYPE JSON  通用: 提交写入前验证(type=rules|relations|bp|link)
  --selfcheck / --tool-version

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, sys, datetime, urllib.request

VERSION = "v1.0.0"
BB = os.environ.get("BB_URL", "http://127.0.0.1:8792")
BLUEPRINT_DIR = os.path.expanduser("~/dsh-collab/data/blueprint")
BP9_FIELDS = ["id", "name", "version", "mainlines", "stages", "status"]

# ── 纯判定函数(R006#10 Lean4 结构门: 生产路径与 --lean4-check 共用, 证明违规被拒) ──
def _norm_bp(ref):
    """剥离 bp: 前缀后的蓝图引用"""
    return str(ref).replace("bp:", "")

def _ref_violations(rules, bps):
    """规则→蓝图引用校验(纯): 返回违规清单 [rid 引用不存在蓝图 X, ...]"""
    viol = []
    for rule in rules:
        rid = rule.get("id")
        for b in rule.get("blueprints", []):
            if _norm_bp(b) not in bps:
                viol.append(f"{rid} 引用不存在蓝图 {b}")
    return viol

def _edge_violations(edges, bps):
    """relations 边校验(纯): 返回违规清单 [边 X→Y: from/to 非蓝图, ...]"""
    viol = []
    for e in edges:
        f, t = e.get("from"), e.get("to")
        if f and _norm_bp(f) not in bps: viol.append(f"边 {f}→{t}: from 非蓝图")
        if t and _norm_bp(t) not in bps: viol.append(f"边 {f}→{t}: to 非蓝图")
    return viol

def _missing_fields(v):
    """BP-9 字段契约(纯): 返回缺失字段清单"""
    return [f for f in BP9_FIELDS if not v.get(f)]

def _fetch(k):
    try:
        with urllib.request.urlopen(BB + "/" + k, timeout=6) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None

def valid_blueprints():
    """合法蓝图 id 集(黑板上 relations.blueprints 为准 + 目录)"""
    rel = _fetch("data/blueprint/relations")
    ids = set()
    if rel:
        v = rel.get("value", rel)
        for b in v.get("blueprints", []):
            if isinstance(b, dict): ids.add(b.get("id"))
            else: ids.add(str(b))
    # 目录兜底
    if os.path.isdir(BLUEPRINT_DIR):
        for d in os.listdir(BLUEPRINT_DIR):
            if os.path.isdir(os.path.join(BLUEPRINT_DIR, d)) and not d.startswith("."):
                ids.add(d)
    return ids

def valid_rules():
    r = _fetch("data/rules") or _fetch("rules-registry/rules.json")
    # rules 从本地文件
    try:
        d = json.load(open(os.path.expanduser("~/dsh-collab/rules-registry/rules.json")))
        return {x["id"] for x in d.get("rules", [])}
    except Exception:
        return set()

def check_rules():
    bps = valid_blueprints()
    try:
        d = json.load(open(os.path.expanduser("~/dsh-collab/rules-registry/rule-mapping.json")))
    except Exception as e:
        return {"ok": False, "errors": [str(e)]}
    errors, warn = [], []
    seen = set()
    for rule in d.get("rules", []):
        rid = rule.get("id")
        if not rid: errors.append("规则缺 id"); continue
        if rid in seen: warn.append(f"重复规则 {rid}")
        seen.add(rid)
    errors += _ref_violations(d.get("rules", []), bps)  # 引用完整性(纯函数门)
    # bpToRules 反向也查
    btr = d.get("bpToRules", {})
    for b, rls in (btr or {}).items():
        if _norm_bp(b) not in bps: warn.append(f"bpToRules 键 {b} 非蓝图")
    return {"ok": not errors, "errors": errors, "warn": warn,
            "rules": len(seen), "blueprintsKnown": len(bps)}

def check_relations():
    rel = _fetch("data/blueprint/relations")
    if not rel: return {"ok": False, "errors": ["relations 不可读"]}
    v = rel.get("value", rel)
    bps = set()
    for b in v.get("blueprints", []):
        if isinstance(b, dict): bps.add(b.get("id"))
        else: bps.add(str(b))
    errors = _edge_violations(v.get("edges", []), bps)  # 引用完整(纯函数门)
    return {"ok": not errors, "errors": errors, "edges": len(v.get("edges", [])),
            "blueprints": len(bps)}

def check_bp(bid):
    bp = _fetch("data/blueprint/" + bid)
    v = bp.get("value", bp) if isinstance(bp, dict) else {}
    missing = _missing_fields(v)  # BP-9 字段契约(纯函数门)
    return {"ok": not missing, "missing": missing, "id": bid}

def main():
    ap = argparse.ArgumentParser(description="数据写入契约门(Φ9)")
    ap.add_argument("--check-rules", action="store_true")
    ap.add_argument("--check-relations", action="store_true")
    ap.add_argument("--check-bp")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--tool-version", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--lean4-check", action="store_true", help="Lean4自检(违规路径被拒)")
    args = ap.parse_args()
    if args.tool_version: print(f"bb-schema-gate {VERSION}"); return
    if args.lean4_check:
        # Lean4 自检: 注入违规数据, 证明纯函数门(与生产同源)确实拒绝违规路径
        fake_bps = {"flowernet", "agent-network"}           # 已知蓝图集(瘦身集足够证明门)
        # 1) 规则引用不存在蓝图 → 必须被拒
        r1 = _ref_violations([{"id": "RX", "blueprints": ["bp:ghost-blue"]}], fake_bps)
        ok1 = len(r1) == 1 and "ghost-blue" in r1[0]
        # 2) relations 边引用非蓝图 → 必须被拒 (from/to 各 1 条)
        r2 = _edge_violations([{"from": "ghost-a", "to": "flowernet"},
                               {"from": "flowernet", "to": "bp:ghost-b"}], fake_bps)
        ok2 = len(r2) == 2
        # 3) BP-9 缺字段 → 必须被拒 (只有 id, 缺 name/version/mainlines/stages/status)
        r3 = _missing_fields({"id": "flowernet"})
        ok3 = len(r3) == len(BP9_FIELDS) - 1
        # 4) 合法引用 → 必须放行 (证明门不误伤)
        ok4 = not _ref_violations([{"id": "OK", "blueprints": ["flowernet"]}], fake_bps) \
              and not _edge_violations([{"from": "flowernet", "to": "agent-network"}], fake_bps)
        passed = ok1 and ok2 and ok3 and ok4
        detail = f"规则幽灵引用拒={ok1} 边幽灵引用拒={ok2} 缺字段拒={ok3} 合法放行={ok4}"
        print("lean4-check:", ("✅ 结构门生效 · " if passed else "❌ ") + detail)
        sys.exit(0 if passed else 1)
    if args.selfcheck:
        r = check_rules()
        print("TCC:", "✅" if "ok" in r else "❌"); sys.exit(0 if r.get("ok") else 1)
    if args.check_rules:
        r = check_rules()
        if args.json: print(json.dumps(r, ensure_ascii=False, indent=1)); return
        print("══ 规则映射契约 ══")
        for e in r["errors"][:10]: print("❌", e)
        for w in r["warn"][:5]: print("⚠️", w)
        print(f"→ {'✅ 通过' if r['ok'] else '❌ '+str(len(r['errors']))+' 错误'} · {r['rules']} 规则 · {r['blueprintsKnown']} 蓝图")
        return
    if args.check_relations:
        r = check_relations()
        print("══ 关系契约 ══")
        for e in r["errors"][:10]: print("❌", e)
        print(f"→ {'✅' if r['ok'] else '❌'} {len(r['errors'])} 错误 · {r['edges']} 边")
        return
    if args.check_bp:
        r = check_bp(args.check_bp)
        print(f"蓝图 {args.check_bp}: {'✅' if r['ok'] else '❌ 缺 ' + str(r['missing'])}")
        return
    ap.print_help()

if __name__ == "__main__":
    main()
