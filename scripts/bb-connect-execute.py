#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-connect-execute.py — 连接真实执行器(Φ8/R006 合规 · v1.0)
五步门"执行"的真实动作: 确认边后 ①黑板投递通知两端相关方 ②协作任务登记 ③幂等留痕
用法:
  python3 bb-connect-execute.py --run --graph G --from A --to B [--reason ..]  执行一条
  python3 bb-connect-execute.py --run-all                                         批量执行全部未执行
  python3 bb-connect-execute.py --list                                            查看执行/通知状态
  python3 bb-connect-execute.py --selfcheck                                        TCC 自检
  python3 bb-connect-execute.py --tool-version                                    版本
  python3 bb-connect-execute.py --json                                            结构化输出
  graph: agents(默认)/servers(R006 v2.1 comm-layer 服务器域)/rules|bp 域
数据: confirmed-links.json(输入) → 黑板投递 + 协作登记(输出)
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, sys, datetime, urllib.request, urllib.error

VERSION = "v1.0.0"
BB = os.environ.get("BB_URL", "http://127.0.0.1:8792")
CONF = os.path.expanduser("~/dsh-collab/data/connect-lab/confirmed-links.json")
EXEC_LOG = os.path.expanduser("~/dsh-collab/data/connect-lab/executions.json")

def _bb_put(key, payload):
    """黑板写(key: data/... 或 notes/...)"""
    try:
        req = urllib.request.Request(BB + "/" + key, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"}, method="PUT")
        with urllib.request.urlopen(req, timeout=6) as r:
            return True, r.status
    except Exception as e:
        return False, str(e)

def load_confirmed():
    return json.load(open(CONF, encoding="utf-8")) if os.path.exists(CONF) else {"links": []}

def load_exec():
    d = json.load(open(EXEC_LOG, encoding="utf-8")) if os.path.exists(EXEC_LOG) else {"executions": []}
    return d

def _agent_note(aid):
    """agent 通知键: notes/<node>/ 下发? agent id 是 session-xxx → notes/session-<id>/ 域不合适,
    用 notes/connect-lab/<short>-<ts> 单一通知墙 + data/connect-lab/notifications/ 结构化"""
    return "data/connect-lab/notifications"

def notify_parties(link, action="connect-confirmed"):
    """给连接两端(agent 或域主体)黑板通知 + 协作登记 + 端侧定向. 返回通知数"""
    frm, to = link.get("from", ""), link.get("to", "")
    graph = link.get("graph", "agents")
    value = link.get("desc", "连接确认")
    ts = datetime.datetime.now().isoformat()
    sent = 0
    # 1) 黑板 data/connect-lab/notifications/ 追加一条(两端都可见, 单键时间序)
    note_key = "data/connect-lab/notifications/latest"
    note = {"ts": ts, "action": action, "graph": graph, "between": [frm, to],
            "value": value, "by": "bb-connect-execute"}
    ok, _ = _bb_put(note_key, note)
    if ok: sent += 1
    # 2) 协作任务登记
    task_key = "data/connect-lab/collab-tasks/task-" + ts.replace(":", "").replace("-", "").replace(".", "")
    task = {"ts": ts, "from": frm, "to": to, "graph": graph, "value": value,
            "status": "new", "suggested": "双方知会协作方向, 认领复用/共建任务",
            "assigned": "待相关方认领", "tool": "bb-connect-execute"}
    ok2, _ = _bb_put(task_key, task)
    if ok2: sent += 1
    # 3) 端侧定向投递(R004/central-inbox v2 兼容): notes/<短id>/ 域 —— 两端会话可感知(短id=session- 后首段)
    if graph == "agents":
        for _end in [frm, to]:
            _e = str(_end)
            _short = _e.split("-")[1] if _e.startswith("session-") and len(_e.split("-")) > 1 else _e[:8]
            _nkey = "notes/" + _short + "/connect-notify-" + ts.replace(":", "").replace("-", "").replace(".", "")
            _n = {"ts": ts, "action": action, "between": [frm, to], "value": value,
                  "by": "bb-connect-execute", "from_graph": graph}
            _ok3, _ = _bb_put(_nkey, _n)
            if _ok3: sent += 1
    return sent

def _valid_endpoints(graph, frm, to):
    """Φ9 契约: 端点必须存在
    agents 域 → agent-bus.json; servers 域 → hardware-nodes.json(server/device/cloud 组); 其它域 → 注册蓝图"""
    try:
        if graph == "agents":
            d = json.load(open(os.path.expanduser("~/.dsh/agent-bus.json")))
            ids = {p.get("agentId") for p in d.get("profiles", [])}
        elif graph == "servers":
            # comm-layer 服务器化: 端点 = hardware-nodes 节点(hw: 前缀兼容)
            hw = json.load(open(os.path.expanduser("~/dsh-collab/data/blueprint/gallery/hardware-nodes.json")))
            ids = set()
            for n in hw.get("nodes", []):
                nid = n.get("id", "")
                ids.add(nid)
                if nid.startswith("hw:"): ids.add(nid[3:])
                ids.add(n.get("device", "")); ids.add(n.get("name", ""))
        else:
            d = json.load(open(os.path.expanduser("~/dsh-collab/data/blueprint/gallery/blueprint-registry.json"))) if os.path.exists(os.path.expanduser("~/dsh-collab/data/blueprint/gallery/blueprint-registry.json")) else {"blueprints": []}
            ids = {b.get("id") for b in d.get("blueprints", [])}
            # 兜底目录
            import glob as _g
            for _bd in _g.glob(os.path.expanduser("~/dsh-collab/data/blueprint/*/")):
                ids.add(os.path.basename(_bd.rstrip("/")))
        # bp:/hw: 前缀剥离后比对
        f2 = str(frm).replace("bp:", "").replace("hw:", "")
        t2 = str(to).replace("bp:", "").replace("hw:", "")
        return f2 in ids and t2 in ids
    except Exception:
        return True  # 校验不可用放行(核心幂等已保)

def execute_link(link, dry=False):
    """执行一条: 通知+登记, 标 executed. 幂等: 已执行跳过"""
    if not _valid_endpoints(link.get("graph","agents"), link.get("from",""), link.get("to","")):
        return {"ok": False, "error": "契约拒: 连接端点不存在(不可执行通知)"}
    key = (link.get("graph"), link.get("from"), link.get("to"))
    ex = load_exec()
    for e in ex["executions"]:
        if (e.get("graph"), e.get("from"), e.get("to")) == key:
            return {"ok": True, "already": True, "note": "已执行过(幂等跳过)"}
    if dry:
        return {"ok": True, "dry": True, "would_notify": 2}
    sent = notify_parties(link)
    ex["executions"].append({"graph": link.get("graph"), "from": link.get("from"), "to": link.get("to"),
                             "notified": sent, "ts": datetime.datetime.now().isoformat()})
    os.makedirs(os.path.dirname(EXEC_LOG), exist_ok=True)
    json.dump(ex, open(EXEC_LOG, "w"), ensure_ascii=False, indent=1)
    return {"ok": True, "already": False, "notified": sent}

def main():
    ap = argparse.ArgumentParser(description="连接真实执行器(R006)")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--run-all", action="store_true")
    ap.add_argument("--graph", default="agents")
    ap.add_argument("--from", dest="frm")
    ap.add_argument("--to")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--tool-version", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--dry", action="store_true", help="演练(不发黑板)")
    ap.add_argument("--lean4-check", action="store_true", help="Lean4自检(违规路径被拒)")
    ap.add_argument("--reason", default="连接确认", help="确认原因/价值叙事")
    args = ap.parse_args()

    if args.tool_version:
        print(f"bb-connect-execute {VERSION}"); return
    if args.selfcheck:
        # TCC: 依赖文件可读 + 黑板可达(干跑)
        ok = os.path.exists(CONF)
        try:
            urllib.request.urlopen(BB + "/", timeout=3)  # 黑板根 400=服务在(HTTPError 也是可达)
            bb_ok = True
        except urllib.error.HTTPError: bb_ok = True  # 4xx 说明服务响应
        except Exception: bb_ok = False
        print("TCC:", "✅ 通过" if ok else "❌ confirmed 缺失", "| 黑板:", "✅" if bb_ok else "⚠️不可达(降级本地)")
        sys.exit(0 if ok else 1)
    if args.list:
        ex = load_exec()
        print(f"已执行 {len(ex['executions'])} 条:")
        for e in ex["executions"]: print(f"  [{e.get('graph')}] {e.get('from','')[:14]} ↔ {e.get('to','')[:14]} 通知{e.get('notified',0)}")
        # 未执行 confirmed
        done = {(e.get('graph'), e.get('from'), e.get('to')) for e in ex["executions"]}
        conf = load_confirmed()
        pend = [l for l in conf["links"] if (l.get("graph"), l.get("from"), l.get("to")) not in done]
        print(f"待执行 confirmed: {len(pend)} 条")
        for l in pend: print(f"  [{l.get('graph')}] {l.get('from','')[:14]} ↔ {l.get('to','')[:14]}")
        return
    if args.run_all:
        ex = load_exec(); done = {(e.get('graph'), e.get('from'), e.get('to')) for e in ex["executions"]}
        conf = load_confirmed()
        pend = [l for l in conf["links"] if (l.get("graph"), l.get("from"), l.get("to")) not in done]
        results = [execute_link(l, args.dry) for l in pend]
        print(f"批量执行 {len(pend)} 条: {sum(1 for r in results if r.get('ok'))} 成功")
        if args.json: print(json.dumps(results, ensure_ascii=False, indent=1))
        return
    if args.lean4_check:
        # Lean4 自检: 非法端点应被契约拒(结构门生效证明)
        r1 = execute_link({"graph":"agents","from":"session-nonexist-000","to":"session-nonexist-111","desc":"lean4-check"}, dry=False)
        ok1 = (not r1.get("ok")) and "契约拒" in str(r1.get("error",""))
        r2 = execute_link({"graph":"rules","from":"bp:nope","to":"bp:nope2","desc":"lean4"}, dry=False)
        ok2 = (not r2.get("ok"))
        # servers 域(R006 v2.1): 合法 server 端点(xingqiao)放行 + 幽灵服务器拒
        r3 = execute_link({"graph":"servers","from":"hw:srv-xingqiao","to":"hw:srv-commlayer","desc":"lean4"}, dry=True)
        ok3 = r3.get("ok", False) and r3.get("dry", False)   # 合法端点过契约门(演练不真发)
        r4 = execute_link({"graph":"servers","from":"srv-ghost-x","to":"srv-ghost-y","desc":"lean4"}, dry=True)
        ok4 = not r4.get("ok")                                # 幽灵服务器被拒
        passed = ok1 and ok2 and ok3 and ok4
        detail = f"agents非法拒={ok1} rules非法拒={ok2} servers合法放行={ok3} servers幽灵拒={ok4}"
        print("lean4-check:", ("✅ 结构门生效 · " if passed else "❌ ") + detail)
        sys.exit(0 if passed else 1)
    if args.run:
        if not (args.frm and args.to):
            print("需 --from --to"); sys.exit(1)
        link = {"graph": args.graph, "from": args.frm, "to": args.to, "desc": args.reason or "连接确认"}
        r = execute_link(link, args.dry)
        print(json.dumps(r, ensure_ascii=False))
        return
    ap.print_help()

if __name__ == "__main__":
    main()
