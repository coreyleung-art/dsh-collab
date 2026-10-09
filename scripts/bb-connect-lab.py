#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-connect-lab.py — 智能体连接实验室(Φ8 工具化 · R006 合规)
孤岛探测 × 候选穷举 × 可连接性打分(5 特征) — 探索智能体网络潜在连接

用法:
  python3 bb-connect-lab.py --scan [--top N]      扫孤岛+候选+打分(默认 top 15)
  python3 bb-connect-lab.py --islands             只列孤岛
  python3 bb-connect-lab.py --json                输出 JSON(落链)
  python3 bb-connect-lab.py --out FILE            候选落盘(供 gallery 读取/确认池)
  python3 bb-connect-lab.py --selfcheck           TCC 自检
  python3 bb-connect-lab.py --tool-version        版本
数据源: ~/.dsh/agent-bus.json profiles(能力/资源/角色)
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, sys, datetime


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-connect-lab.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = "v1.2.0"
AGENTS_FILE = os.path.expanduser("~/.dsh/agent-bus.json")
OUT_DEFAULT = os.path.expanduser("~/dsh-collab/data/connect-lab/candidates.json")
CONFIRMED = os.path.expanduser("~/dsh-collab/data/connect-lab/confirmed.json")

def load_confirmed():
    if os.path.exists(CONFIRMED):
        return json.load(open(CONFIRMED, encoding="utf-8"))
    return {"version": "1.0", "links": [], "updated": ""}

def cmd_confirm(frm, to, reason="", by=""):
    d = load_confirmed()
    for l in d["links"]:
        if l["from"] == frm and l["to"] == to:
            print(f"⚠️ 已存在: {frm} ↔ {to}"); return 0
    d["links"].append({"from": frm, "to": to, "reason": reason or "连接实验室人工确认",
                       "by": by or "user", "ts": datetime.datetime.now().isoformat()})
    d["updated"] = datetime.datetime.now().isoformat()
    os.makedirs(os.path.dirname(CONFIRMED), exist_ok=True)
    json.dump(d, open(CONFIRMED, "w"), ensure_ascii=False, indent=1)
    print(f"✅ 确认连接: {frm} ↔ {to} → {CONFIRMED}")
    return 0

def cmd_list_confirmed():
    d = load_confirmed()
    print(f"已确认连接 {len(d['links'])} 条:")
    for l in d["links"]:
        print(f"  {l['from']} ↔ {l['to']}  [{l.get('reason','')}]  {l.get('ts','')[:16]}")
    return 0

# 职能域(agent_domain 同 gallery)
DOMAINS = {"运维/安全":"ops","开发/插件":"dev","数据/调研":"data","业务/运营":"biz",
           "治理/协调":"gov","洞察/规划":"plan","通讯/媒体":"comm","后备/通用":"idle"}
def agent_domain(role):
    for kw, d in DOMAINS.items():
        if kw.split("/")[0] in role or kw in role: return d
    return "other"

def _res_keys(r):
    keys=set()
    for m in re.finditer(r"(~|/|store:|port:|file:|db:)([A-Za-z0-9_./-]{2,40})", str(r)):
        keys.add(m.group(1)+m.group(2))
    return keys

def _text_sim(a,b):
    def toks(s): return set(re.findall(r'[\u4e00-\u9fff]{2,4}|[A-Za-z][A-Za-z0-9-]{1,}', s or ''))
    ta,tb=toks(a),toks(b)
    if not ta or not tb: return 0.0
    return len(ta&tb)/max(1,len(ta|tb))

# ── 向量语义通道(v1.1): Ollama bge-m3 优先, 失败退化 Jaccard ──
import urllib.request as _urlreq
import math as _math
_OLLAMA="http://127.0.0.1:11434"
_EMB_MODEL=None
def _ensure_embed():
    global _EMB_MODEL
    if _EMB_MODEL is not None: return _EMB_MODEL
    try:
        for m in ["bge-m3","nomic-embed-text"]:
            req=_urlreq.Request(f"{_OLLAMA}/api/embed",data=json.dumps({"model":m,"input":["测试"]}).encode(),
                                headers={"Content-Type":"application/json"})
            with _urlreq.urlopen(req,timeout=5) as r:
                d=json.loads(r.read())
                if d.get("embeddings"): _EMB_MODEL=m; return m
    except Exception: pass
    _EMB_MODEL=""; return None

def _embed(texts):
    m=_ensure_embed()
    if not m: return None
    try:
        req=_urlreq.Request(f"{_OLLAMA}/api/embed",data=json.dumps({"model":m,"input":texts}).encode(),
                            headers={"Content-Type":"application/json"})
        with _urlreq.urlopen(req,timeout=30) as r:
            return json.loads(r.read()).get("embeddings")
    except Exception: return None

def _cos(a,b):
    d=sum(x*y for x,y in zip(a,b)); na=_math.sqrt(sum(x*x for x in a)); nb=_math.sqrt(sum(y*y for y in b))
    return d/(na*nb) if na and nb else 0.0

def _sem_sim(a,b):
    """语义相似: 向量可用用余弦, 否则 Jaccard"""
    e=_embed([a,b])
    if e and len(e)==2: return _cos(e[0],e[1])
    return _text_sim(a,b)

def load_agents():
    d=json.load(open(AGENTS_FILE,encoding="utf-8"))
    return [p for p in d.get("profiles",[])
            if str(p.get("agentId","")).startswith("session-")
            and "已交接" not in p.get("role","") and "前任" not in p.get("role","")]

def scan(top=15, all_cands=False):
    agents=[{"id":a.get("agentId"),"role":a.get("role",""),"domain":agent_domain(a.get("role","")),
             "abilities":a.get("abilities",[]),"resources":a.get("resources",[])} for a in load_agents()]
    res={n["id"]:_res_keys(" ".join(n["resources"])) for n in agents}
    # 预计算文本向量(批量一次嵌入, 避免逐对调 API)
    _vec={}; _embed_model_ok=_ensure_embed()
    if _embed_model_ok:
        _texts=[" ".join(n["abilities"])+" "+" ".join(n["resources"]) for n in agents]
        _embs=_embed(_texts)
        if _embs: _vec={n["id"]:v for n,v in zip(agents,_embs)}
    def _sim_vec(a,b):
        if a in _vec and b in _vec: return _cos(_vec[a],_vec[b])
        return _text_sim(" ".join(next(n["abilities"] for n in agents if n["id"]==a))+" "+" ".join(next(n["resources"] for n in agents if n["id"]==a)),
                         " ".join(next(n["abilities"] for n in agents if n["id"]==b))+" "+" ".join(next(n["resources"] for n in agents if n["id"]==b)))
    # 共享资源边(<8 主的私有键)
    cnt={}
    for rks in res.values():
        for k in rks: cnt[k]=cnt.get(k,0)+1
    priv={k for k,n in cnt.items() if n<8}
    linked=set()
    for aid,rks in res.items():
        for k in rks&priv:
            owners=[nid for nid,rr in res.items() if k in rr]
            if len(owners)>1: linked.update(owners)
    islands=[n for n in agents if n["id"] not in linked]
    # 穷举打分
    cands=[]
    for iso in islands:
        for tgt in agents:
            if iso["id"]==tgt["id"]: continue
            f1=0.28 if iso["domain"]==tgt["domain"] else 0.05
            f2=0.36*_sim_vec(iso["id"], tgt["id"])
            share=len(res[iso["id"]]&res[tgt["id"]])
            f3=0.20*min(1.0,share/3)
            f4=0.15*_sim_vec(iso["id"], tgt["id"])  # 互补近似(全文本向量, 免逐对嵌入)
            f5=0.04
            score=round(f1+f2+f3+f4+f5,3)
            _why = _explain_value(iso, tgt, f2, share, iso["domain"]==tgt["domain"], score)
            _why += _explain_action(iso, tgt, share, iso["domain"]==tgt["domain"])
            cands.append({"from":iso["id"],"from_role":iso["role"][:60],"to":tgt["id"],"to_role":tgt["role"][:60],
                          "score":score,"feats":{"f1_dom":round(f1,2),"f2_sem":round(f2,3),"f3_share":round(f3,2),"f4_comp":round(f4,2)},
                          "band":"high" if score>=0.5 else ("mid" if score>=0.38 else "weak"),
                          "reason":"；".join(_why) if _why else "弱信号(待向量深查)"})
    cands.sort(key=lambda x:-x["score"])
    # 去重反向
    seen=set(); dedup=[]
    # 已确认连接排除(不可重复建议)
    confirmed_set=set()
    try:
        import os as _o
        _cf2=_o.path.expanduser("~/dsh-collab/data/connect-lab/confirmed.json")
        if _o.path.exists(_cf2):
            for _l in json.load(open(_cf2)).get("links",[]):
                confirmed_set.add(tuple(sorted([_l.get("from"),_l.get("to")])))
    except Exception: pass
    for c in cands:
        k=tuple(sorted([c["from"],c["to"]]))
        if k in seen: continue
        if k in confirmed_set: continue  # 已确认/已建边 → 不再建议
        seen.add(k); dedup.append(c)
    return {"mode":"connectlab","islandCount":len(islands),"candidateCount":len(dedup),
            "bands":{"high":sum(1 for c in dedup if c["band"]=="high"),
                     "mid":sum(1 for c in dedup if c["band"]=="mid"),
                     "weak":sum(1 for c in dedup if c["band"]=="weak")},
            "islands":[{"id":n["id"],"role":n["role"][:60]} for n in islands],
            "candidates":dedup[:top] if not all_cands else dedup,
            "ts":datetime.datetime.now().isoformat()}


# ── 价值叙事: 把机器依据转成"为什么+价值"人话(v1.2) ──
_DOM_VAL = {"ops": "运维安全域", "dev": "开发插件域", "data": "数据调研域", "biz": "业务运营域",
            "gov": "治理协调域", "plan": "洞察规划域", "comm": "通讯媒体域", "idle": "通用域", "other": "其他域"}
def _explain_value(a, b, f2, share, same_dom, score):
    import re as _re
    parts = []
    abi_a = set(a.get("abilities", [])); abi_b = set(b.get("abilities", []))
    inter = [x for x in abi_a if x in abi_b][:2]
    if inter:
        parts.append("共同能力: " + " / ".join(x[:22] for x in inter))
    def kw(s): return set(_re.findall(r"[\u4e00-\u9fff]{2,4}|[A-Za-z][A-Za-z0-9-]{1,}", s))
    ka = kw(" ".join(abi_a)); kb = kw(" ".join(abi_b))
    overlap = list(ka & kb)[:3]
    if overlap and not inter:
        parts.append("能力关键词重合: " + "、".join(overlap))
    if share > 0:
        parts.append("已有 %d 类资源共享(协作基础)" % share)
    da = _DOM_VAL.get(a.get("domain", ""), "本域"); db = _DOM_VAL.get(b.get("domain", ""), "本域")
    if same_dom:
        parts.append("价值: 同属%s, 连接可共享方法论与资产, 减少重复建设" % da)
    else:
        parts.append("价值: 以%s(%s)能力服务%s场景, 补对方空白, 形成跨域协作" % (a.get("role","A")[:10], da, db))
    if score >= 0.5:
        parts.append("语义匹配 %.0f%%, 是强信号连接" % (score*100))
    return parts

def _resource_topic(r):
    """从资源串提取主题词(文件/端口/存储名)"""
    import re as _re
    # 去路径前缀取核心名: file:~/dsh-collab/cld-health → cld-health
    m = _re.findall(r"(?:file:|~|/|port:|db:|store:|kb:|chroma:)[^\s\\/]*(?:[\\/]([A-Za-z0-9._-]{3,}))?|([A-Za-z][A-Za-z0-9._-]{3,30})", r)
    out = set()
    for mm in m:
        for g in mm:
            if g and not g.startswith((".", "~")) and len(g) >= 3:
                out.add(g.split(".")[0].lower())
    return out

def _explain_action(a, b, share, same_dom=False):
    """场景化行动建议: A 的能力/资源 ↔ B 的能力/资源 具体能一起做什么"""
    import re as _re
    acts = []
    ra = set(a.get("resources", [])); rb = set(b.get("resources", []))
    abi_a = " ".join(a.get("abilities", [])); abi_b = " ".join(b.get("abilities", []))
    # 主题词(资源文件名 → 对方能力是否提到)
    def topics(reslist):
        return set(x.split("/")[-1].split(":")[-1].strip(" ~/\"'").replace(".md","").replace(".json","").replace(".db","")
                   for x in reslist if "/" in x or ":" in x)
    ta, tb = topics(a.get("resources", [])), topics(b.get("resources", []))
    # 场景1: A 的资源主题出现在 B 能力里 → A 可提供该资源给 B 用
    for t in list(ta)[:2]:
        if t and t.lower() in abi_b.lower():
            acts.append(f"行动: {a.get('role','A')[:10]} 的 {t} 资产可供给 {b.get('role','B')[:10]} 的 {abi_b[:30]}… 场景直接消费")
    for t in list(tb)[:2]:
        if t and t.lower() in abi_a.lower():
            acts.append(f"行动: {b.get('role','B')[:10]} 的 {t} 资产可供 {a.get('role','A')[:10]} 复用, 免重复采集/登记")
    # 场景2: 协调/管理者角色 → 登记/授权(仅一个方向, 防双写)
    ra_l = a.get("role", "").lower(); rb_l = b.get("role", "").lower()
    MGR = ["资源管理", "协调", "星桥", "总线", "司库", "中枢"]
    if any(k in ra_l for k in MGR):
        acts.append(f"行动: {a.get('role','A')[:14]} 可将 {b.get('role','B')[:12]} 纳入登记/调度, 明确其可复用资产边界")
    elif any(k in rb_l for k in MGR):
        acts.append(f"行动: 建议 {a.get('role','A')[:10]} 向 {b.get('role','B')[:14]} 登记资源/申请通道")
    # 场景3: 共享资源深化
    if share > 0:
        acts.append(f"行动: 已有 {share} 类资源共享 → 确认后深化为协作, 联合维护走同一黑板通道")
    if not acts and same_dom:
        # 同域无管理角色: 共同能力可合并做事(联合排查/共建/复用)
        comm = set(a.get("abilities", [])) & set(b.get("abilities", []))
        focus = " / ".join(x[:16] for x in list(comm)[:1]) if comm else (a.get("domain","") + "域协同")
        acts.append(f"行动: 同域协作 — 可在「{focus}」上联合排查/共建/交叉验收, 避免各自为战重复造轮子")
    if not acts:
        acts.append(f"行动: 建议先互相知晓职责边界, 建轻量协作(互挂黑板通知), 再视实效深化")
    return acts

def main():
    ap=argparse.ArgumentParser(description="智能体连接实验室(Φ8/R006)")
    ap.add_argument("--scan",action="store_true")
    ap.add_argument("--islands",action="store_true")
    ap.add_argument("--top",type=int,default=15)
    ap.add_argument("--json",action="store_true")
    ap.add_argument("--out",default=OUT_DEFAULT)
    ap.add_argument("--confirm",nargs=2,metavar=("FROM","TO"),help="确认一条候选连接(写 confirmed.json)")
    ap.add_argument("--list-confirmed",action="store_true")
    ap.add_argument("--reason",default="",help="确认原因")
    ap.add_argument("--selfcheck",action="store_true")
    ap.add_argument("--tool-version",action="store_true")
    args=ap.parse_args()
    if args.tool_version: print(f"bb-connect-lab {VERSION}"); return
    if args.confirm: return cmd_confirm(args.confirm[0],args.confirm[1],reason=args.reason)
    if args.list_confirmed: return cmd_list_confirmed()
    if args.selfcheck:
        r=scan(top=5)
        ok=isinstance(r,dict) and r["islandCount"]>0 and isinstance(r["candidates"],list)
        print("TCC:", "✅ 通过" if ok else "❌ 失败")
        sys.exit(0 if ok else 1)
    r=scan(top=args.top)
    if args.islands:
        print(f"孤岛 {r['islandCount']}:")
        for i in r["islands"]: print(" ·",i["role"])
        return
    if args.json:
        print(json.dumps(r,ensure_ascii=False,indent=1)); return
    if args.out:
        os.makedirs(os.path.dirname(args.out),exist_ok=True)
        json.dump(r,open(args.out,"w"),ensure_ascii=False,indent=1)
        print(f"已落盘 → {args.out}"); return
    print(f"══ 连接实验室 ══ 孤岛 {r['islandCount']} · 候选 {r['candidateCount']} · {r['bands']}")
    for c in r["candidates"][:args.top]:
        if c["band"]=="weak": continue
        print(f"  {c['score']} [{c['band']}] {c['from_role'][:22]} ↔ {c['to_role'][:22]}")
        print(f"      💡 {c['reason']}")

if __name__=="__main__":
    main()
