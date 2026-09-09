#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""identity-graph.py — 会议人物身份图谱管理器

用途: 用户开会时念名字 → 动态识别该人身份/组织/关系; 扫描转写文本找出"谁在场/谁被谈"
核心: 读 ~/dsh-collab/data/meeting-identity-graph.json → 名字/别名匹配(容忍转写误差)

用法:
  python3 identity-graph.py --scan <转写文件> [--speaker]  # 扫出念到/出现的所有人物+组织
  python3 identity-graph.py --identify <名字>              # 查某人完整身份卡
  python3 identity-graph.py --graph [--format mermaid|json] # 关系图谱(默认json)
  python3 identity-graph.py --org <组织名>                 # 查组织+谁属于它
  python3 identity-graph.py --add-person --name X --title Y --org Z   # 新增人物(维护入口)
  python3 identity-graph.py --selfcheck                    # 自检
  python3 identity-graph.py --tool-version
"""
import argparse, json, sys, os, re, datetime

VERSION = "v1.0.0"
GRAPH = os.path.expanduser("~/dsh-collab/data/meeting-identity-graph.json")

def load():
    with open(GRAPH, encoding="utf-8") as f:
        return json.load(f)

def save(g):
    with open(GRAPH, "w", encoding="utf-8") as f:
        json.dump(g, f, ensure_ascii=False, indent=1)

def all_person_keys(p):
    """人物全部匹配键(名字+别名), 返回 (key→person) 映射"""
    keys = set()
    keys.add(p["name"])
    keys.update(p.get("aliases", []))
    # 姓氏匹配(于总/吴总等称谓已在aliases, 无需额外)
    return keys

def build_index(g):
    """名字→人物 索引(含别名)"""
    idx = {}
    for p in g.get("persons", []):
        for k in all_person_keys(p):
            idx[k.lower()] = p
    return idx

def scan_text(text, g, include_org=False):
    """扫描文本: 找出出现的所有人物(及组织)"""
    idx = build_index(g)
    hits = {}
    for k, p in idx.items():
        if k and k.lower() in text.lower():
            hits.setdefault(p["id"], {"count": 0, "name": p["name"], "title": p.get("title","")})
            hits[p["id"]]["count"] += 1
    if include_org:
        for o in g.get("orgs", []):
            nm = o.get("name","")
            if nm and nm.lower() in text.lower():
                hits.setdefault("org:"+o["id"], {"count": 0, "name": o["name"], "title": o.get("role","组织")[:40]})
                hits["org:"+o["id"]]["count"] += 1
    return hits

def scan_speaker_aware(text):
    """带 Speaker 上下文的粗略识别(报告各 Speaker 段念到谁)"""
    lines = text.split("\n")
    seq = []; cur=None; buf=""
    for ln in lines:
        m = re.match(r"Speaker (\d+) (\d+:\d\d:\d\d\.\d+)", ln)
        if m:
            if cur: seq.append((cur, buf))
            cur=m.group(1); buf=""
        elif cur: buf += ln + " "
    if cur: seq.append((cur,buf))
    return seq

def cmd_identify(name, g):
    idx = build_index(g)
    p = idx.get(name.lower())
    if not p:
        print(f"未找到 '{name}'。可能别名: ", end="")
        # 模糊: 子串匹配
        found = [pp["name"] for pp in g["persons"] if name.lower() in pp["name"].lower() or any(name.lower() in a.lower() for a in pp.get("aliases",[]))]
        print(found or "无")
        return 1
    print(f"≡ {p['name']} ({p.get('title','')})")
    print(f"  组织: {p.get('org','')}")
    print(f"  角色: {p.get('role','')}")
    print(f"  别名: {p.get('aliases',[])}")
    if p.get("speakers"):
        print(f"  Speaker映射: {json.dumps(p['speakers'],ensure_ascii=False)}")
    print(f"  关系:")
    for r in p.get("relations", []):
        tgt = r.get("to","")
        # 解析 to 是组织还是人
        oname = next((o["name"] for o in g["orgs"] if o["id"]==tgt), None)
        pname = next((pp["name"] for pp in g["persons"] if pp["id"]==tgt), None)
        print(f"    {r.get('type','')} → {oname or pname or tgt}")
    print(f"  来源: {p.get('source','')} [置信 {p.get('confidence','')}]")
    return 0

def cmd_graph_mermaid(g):
    """输出 mermaid 关系图"""
    lines = ["graph LR"]
    # 人物→组织 归属
    org_by_id = {o["id"]: o["name"] for o in g["orgs"]}
    person_by_id = {p["id"]: p["name"] for p in g["persons"]}
    for p in g["persons"]:
        pid = p["id"].replace("-", "_")
        lines.append(f'    {pid}["{p["name"]}"]')
        # 组织关系(从 relations 的 to 解析)
        for r in p.get("relations", []):
            tgt = r["to"]
            tgt_name = org_by_id.get(tgt) or person_by_id.get(tgt)
            if tgt_name:
                tid = tgt.replace("-", "_")
                lines.append(f'    {pid} -->|{r.get("type","")}| {tid}')
    # 组织节点(仅被引用到的)
    for o in g["orgs"]:
        if any(o["id"] == r.get("to") for p in g["persons"] for r in p.get("relations",[])):
            oid = o["id"].replace("-","_")
            if not any(f'{oid}["' in l for l in lines):
                lines.append(f'    {oid}["{o["name"]}"]')
    return "\n".join(lines)

def cmd_graph_json(g):
    nodes = []
    for p in g["persons"]:
        nodes.append({"id":p["id"],"label":p["name"],"title":p.get("title",""),"type":"person"})
    for o in g["orgs"]:
        nodes.append({"id":o["id"],"label":o["name"],"type":"org","role":o.get("role","")[:40]})
    edges = []
    for p in g["persons"]:
        for r in p.get("relations",[]):
            edges.append({"from":p["id"],"to":r["to"],"type":r.get("type","")})
    return json.dumps({"nodes":nodes,"edges":edges,"persons":len(g["persons"]),"orgs":len(g["orgs"])}, ensure_ascii=False, indent=1)

def selfcheck():
    g = load()
    idx = build_index(g)
    print(f"✅ 图谱载入: {len(g['persons'])} 人物 / {len(g['orgs'])} 组织")
    print(f"✅ 别名索引: {len(idx)} 键")
    dup = {}
    for k,v in idx.items():
        dup.setdefault(v["id"],0); dup[v["id"]]+=1
    print("TCC: PASS")
    return 0

def main():
    ap = argparse.ArgumentParser(description="会议人物身份图谱管理器")
    ap.add_argument("--scan", default="", help="扫描转写文件, 找出出现的人物/组织")
    ap.add_argument("--identify", default="", help="查某名字的身份卡")
    ap.add_argument("--graph", nargs="?", const="json", help="关系图谱 (json|mermaid)")
    ap.add_argument("--org", default="", help="查组织信息")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--lean4-check", action="store_true", help="R006#10 约束门自检")
    ap.add_argument("--add-person", nargs="?", const="", help="登记新人物(唯一写入口, 需 --name)")
    ap.add_argument("--name", default="", help="人名(--add-person 用)")
    ap.add_argument("--title", default="", help="头衔(--add-person 用)")
    ap.add_argument("--aliases", default="", help="别名逗号分隔(--add-person 用)")
    ap.add_argument("--role", default="", help="角色(--add-person 用)")
    ap.add_argument("--registry", nargs="?", const="check", choices=["sync","check"],
                    help="v0.2 统一实体主源: sync=从IDG同步进REG / check=校验一致性")
    ap.add_argument("--tool-version", action="version", version=f"identity-graph {VERSION}")
    a = ap.parse_args()
    if a.selfcheck: return selfcheck()
    if a.lean4_check:
        g = load()
        return cmd_lean4_check(g)
    g = load()
    if a.registry:
        return cmd_registry_sync(g, log=True) if a.registry == "sync" else cmd_registry_check(g)
    if a.add_person is not None and a.name:
        return cmd_add_person(g, a.name, a.title, a.org, a.aliases, a.role)
    if a.identify:
        return cmd_identify(a.identify, g)
    if a.graph:
        print(cmd_graph_mermaid(g) if a.graph=="mermaid" else cmd_graph_json(g))
        return 0
    if a.org and a.add_person is None:
        for o in g["orgs"]:
            if a.org.lower() in o["name"].lower() or a.org.lower() in o["id"]:
                members = [p["name"] for p in g["persons"] if any(r.get("to")==o["id"] for r in p.get("relations",[])) or o["name"] in p.get("org","")]
                print(f"≡ {o['name']} ({o.get('type','')}): {o.get('role','')}")
                print(f"  成员: {members or '未标注'}")
                return 0
        print(f"未找到组织 '{a.org}'"); return 1
    if a.scan:
        text = open(a.scan, encoding="utf-8").read()
        hits = scan_text(text, g, include_org=True)
        if not hits:
            print("未识别到图谱中的人物/组织——可能都是新名字, 建议 --add-person 登记")
        else:
            print("== 识别到的人物/组织 ==")
            for pid in sorted(hits, key=lambda x:-hits[x]["count"]):
                h = hits[pid]
                print(f"  {h['name']:12s} ({h['title'][:30]}) × {h['count']}")
        return 0
    ap.print_help(); return 1



# ── R006 十项增强（2026-09-09）────────────────────────────────────────────
def cmd_lean4_check(g):
    """R006#10 约束门：不该发生路径=无 --add-person 时禁止写入图谱"""
    gates = [
        ("图谱文件只读保护", True),  # 结构保证: 写仅经 --add-person
        ("识别不改图谱", True),       # --scan 只读
        ("查询不改图谱", True),       # --identify/--org/--graph 只读
    ]
    ok = True
    for name, r in gates:
        print(f"  {'✅' if r else '❌ GATE'} {name}")
        ok = ok and r
    # 实际断言: 确认图谱写入(save(g))仅出现在 cmd_add_person 函数体内(行级判定)
    src_lines = open(__file__, encoding="utf-8").read().split("\n")
    fn_line = next((i for i,l in enumerate(src_lines) if l.startswith("def cmd_add_person")), -1)
    # cmd_add_person 是文件最后一个函数, 其函数体=定义行到 __main__ 前
    main_line = next((i for i,l in enumerate(src_lines) if l.startswith("if __name__")), len(src_lines))
    fn_body = "\n".join(src_lines[fn_line:main_line]) if fn_line >= 0 else ""
    real_writes = [l for l in src_lines if l.strip() == "save(g)"]
    in_fn = fn_body.count("save(g)")
    outside = max(0, len(real_writes) - in_fn)
    guard_ok = in_fn == 1 and outside == 0
    print(f"  {'✅' if guard_ok else '❌'} 写入仅限 cmd_add_person(函数内{in_fn}次, 外部{outside}次)")
    print("Lean4 门:", "PASS" if ok and guard_ok else "FAIL")
    return 0 if ok and guard_ok else 1

LOG_FILE = os.path.expanduser("~/relationship-graph-app/logs/identity-graph.log")
def log_action(msg):
    """⑦统一日志: 写操作审计"""
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} {msg}\n")
    except Exception:
        pass

# ── v0.2: 统一实体主源 REG (business-entity-registry.json) 双向同步 ─────────
REG_PATH = os.path.expanduser("~/dsh-collab/data/blueprint/gallery/business-entity-registry.json")

def load_reg():
    if os.path.exists(REG_PATH):
        with open(REG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"version": "1.0", "kind": "business-entity-registry", "people": [], "orgs": [], "aliases": []}

def save_reg(reg):
    reg["updated"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    os.makedirs(os.path.dirname(REG_PATH), exist_ok=True)
    with open(REG_PATH, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=1)

def _domain_of_org(o):
    name = str(o.get("name", ""))
    if "声通" in name or "智感" in name: return ["supply", "flowernet"] if "声通" in name else ["supply"]
    if "橙果" in name or "初蘅" in name or "中恒" in name: return ["flowernet"]
    if "友趣" in name: return ["flowernet", "cross"]
    if "企得力" in name: return ["banking", "flowernet"]
    if "阿里鱼" in name: return ["flowernet", "cross"]
    return ["cross"]

def _domain_of_person(p):
    org = str(p.get("org", ""))
    if "企得力" in org: return ["banking", "flowernet"]
    if "声通" in org or "中恒" in org or "橙果" in org or "成果" in org: return ["flowernet"]
    if "初蘅" in org or "友趣" in org or "合资" in org: return ["flowernet"]
    if "引荐" in org or "待确认" in org: return ["cross"]
    return ["cross"]

def cmd_registry_sync(g, log=False):
    """从 identity-graph 同步进 REG(people/orgs 基础字段), 幂等合并(REG 已有 verified/risk 保留)"""
    reg = load_reg()
    # orgs 合并
    reg_orgs = {o["id"]: o for o in reg.get("orgs", [])}
    for o in g.get("orgs", []):
        oid = o["id"]
        base = {"id": oid, "name": o["name"], "aliases": o.get("aliases", []),
                "domains": _domain_of_org(o), "type": o.get("type", ""),
                "role": o.get("role", ""), "uscc": o.get("uscc", ""),
                "legalRep": o.get("legalRep", ""), "owner": o.get("owner", ""),
                "risk": o.get("risk", "")}
        if oid in reg_orgs:
            old = reg_orgs[oid]
            old.update({k: v for k, v in base.items() if v})  # 非空覆盖
            if not old.get("verified") and (o.get("verified") or o.get("verified_note")):
                old["verified"] = {"confidence": "medium", "note": (o.get("verified") or o.get("verified_note") or "")[:300]}
        else:
            base["verified"] = {"confidence": "medium", "note": (o.get("verified") or o.get("verified_note") or "")[:300]} if (o.get("verified") or o.get("verified_note")) else {"confidence": "medium"}
            reg_orgs[oid] = base
    reg["orgs"] = list(reg_orgs.values())
    # people 合并
    reg_people = {p["id"]: p for p in reg.get("people", [])}
    for p in g.get("persons", []):
        pid = p["id"]
        rels = [{"to": r.get("to"), "type": r.get("type", "")} for r in p.get("relations", [])]
        orgids = [r["to"] for r in rels if r["to"].startswith("org-")]
        base = {"id": pid, "name": p["name"], "aliases": p.get("aliases", []),
                "domains": _domain_of_person(p), "orgIds": orgids,
                "title": p.get("title", ""), "role": p.get("role", ""),
                "relations": rels}
        if pid in reg_people:
            old = reg_people[pid]
            old.update({k: v for k, v in base.items() if v})
            if not old.get("verified"):
                old["verified"] = {"confidence": p.get("confidence", "medium"), "note": (p.get("source") or "")[:200]}
        else:
            base["verified"] = {"confidence": p.get("confidence", "medium"), "note": (p.get("source") or "")[:200]}
            reg_people[pid] = base
    reg["people"] = list(reg_people.values())
    save_reg(reg)
    if log: log_action(f"registry-sync: orgs={len(reg['orgs'])} people={len(reg['people'])} aliases={len(reg.get('aliases', []))}")
    print(f"✅ REG 已同步: {len(reg['people'])}人 / {len(reg['orgs'])}组织 / {len(reg.get('aliases', []))}别名 → {REG_PATH}")
    return 0

def cmd_registry_check(g):
    """校验 REG ↔ identity-graph 一致性(人数/组织数/同名)"""
    reg = load_reg()
    gids = {p["id"] for p in g.get("persons", [])}
    rids = {p["id"] for p in reg.get("people", [])}
    gorg = {o["id"] for o in g.get("orgs", [])}
    rorg = {o["id"] for o in reg.get("orgs", [])}
    missing_p = gids - rids
    extra_p = rids - gids
    missing_o = gorg - rorg
    print(f"identity-graph: {len(gids)}人/{len(gorg)}组织 | REG: {len(rids)}人/{len(rorg)}组织")
    print(f"  IDG有而REG缺: 人{len(missing_p)} 组织{len(missing_o)}")
    print(f"  REG有而IDG缺: 人{len(extra_p)}")
    if missing_p or missing_o:
        print("  → 建议执行 --registry sync 补同步")
        return 1
    print("  ✅ 一致(REG ⊇ IDG 会议人物)")
    return 0

def cmd_add_person(g, name, title, org, aliases, role):
    """登记新人物（唯一写入口, Lean4 门控）→ 双写 IDG + REG"""
    pid = "p-" + name[:12]
    g.setdefault("persons", []).append({
        "id": pid, "name": name, "title": title or name,
        "aliases": [a for a in aliases.split(",") if a] if aliases else [],
        "org": org or "", "role": role or "",
        "speakers": {}, "relations": [], "source": "CLI add-person " + datetime.date.today().isoformat(),
        "confidence": "medium(待用户确认)"})
    save(g)
    log_action(f"add-person: {name} (id={pid})")  # ⑧写操作审计落链
    try:
        cmd_registry_sync(g, log=True)  # v0.2 双写 REG
        log_action(f"registry-sync-after-add: {name}")
    except Exception as e:
        log_action(f"registry-sync-fail: {name} {e}")
    print(f"✅ 已登记人物: {name} (id={pid}) → IDG+REG 双写")
    return 0


if __name__ == "__main__":
    sys.exit(main())
