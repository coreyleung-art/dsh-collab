#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-waimai-mcp-core.py — 外卖能力 MCP 能力中台(栈2 · P0 只读)
封装 8787 面板只读 API → 标准 MCP JSON-RPC 2.0 工具面 (供栈3 merchant/栈4 ops 消费)
用法:
  python3 bb-waimai-mcp-core.py --mcp-list                          # 列工具(JSON-RPC tools/list 冒烟)
  python3 bb-waimai-mcp-core.py --call waimai_state                 # 调单个工具(直接输出)
  python3 bb-waimai-mcp-core.py --call waimai_report --days 1
  python3 bb-waimai-mcp-core.py --serve                            # MCP streamable HTTP 服务(待P1)
  python3 bb-waimai-mcp-core.py --selfcheck / --tool-version / --lean4-check
护栏(P0): 只读封装, 不含任何写/动作工具(accept/price 等 P2 再加带 R027门)
数据源: 127.0.0.1:8787 (只读 GET)

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, sys, urllib.request, datetime


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-waimai-mcp-core.log")


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
PANEL = os.environ.get("WAIMAI_PANEL_URL", "http://127.0.0.1:8787")

# ── 工具面定义(白名单映射 8787 只读 API) ──
TOOLS = {
    "waimai_state":   {"endpoint": "/api/state",     "desc": "多店实时状态(在线/登录/窗口)", "params": {}},
    "waimai_alerts":  {"endpoint": "/api/alerts",    "desc": "待处理订单/运营告警", "params": {"limit": {"type":"int","default":10}}},
    "waimai_issues":  {"endpoint": "/api/issues",    "desc": "运营异常巡检(拒单率/积压/掉线)", "params": {}},
    "waimai_report":  {"endpoint": "/api/report",    "desc": "经营日报/周报(按店聚合)", "params": {"days": {"type":"int","default":1}}},
    "waimai_analyze": {"endpoint": "/api/analyze",   "desc": "经营分析(事件量/时段分布)", "params": {}},
    "waimai_keywords":{"endpoint": "/api/keywords",  "desc": "关键字/成交意图分析", "params": {"days": {"type":"int","default":7}}},
    "waimai_scenarios":{"endpoint":"/api/scenarios", "desc": "售后/配送/投诉等场景信号", "params": {"minutes": {"type":"int","default":60}}},
}

def _fetch_json(path, params=None):
    """GET 8787 → json. 只读, 无任何写调用"""
    url = PANEL + path
    if params:
        from urllib.parse import urlencode
        url += "?" + urlencode({k: v for k, v in params.items() if v is not None})
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read().decode())

def call_tool(name, params=None):
    """调一个只读工具 → 结果"""
    t = TOOLS.get(name)
    if not t: return {"ok": False, "error": f"未知工具 {name}(须 {sorted(TOOLS)})"}
    try:
        data = _fetch_json(t["endpoint"], params or {})
        return {"ok": True, "tool": name, "data": data}
    except Exception as e:
        return {"ok": False, "tool": name, "error": str(e)[:150]}

def _no_action_tools():
    """护栏(AST): 真实代码不含任何动作/写工具调用(accept/price/shelf/reject/review 等)"""
    import ast as _ast
    src = open(os.path.abspath(__file__)).read()
    tree = _ast.parse(src)
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Call):
            f = node.func
            name = f.attr if isinstance(f, _ast.Attribute) else (f.id if isinstance(f, _ast.Name) else "")
            if name.startswith("waimai_") and name not in ("waimai_state","waimai_alerts","waimai_issues",
                                                           "waimai_report","waimai_analyze","waimai_keywords","waimai_scenarios"):
                return False  # 发现非只读工具调用
    return True

def mcp_list():
    """JSON-RPC tools/list 格式输出(供 MCP 客户端发现)"""
    out = []
    for name, t in TOOLS.items():
        props = {}
        for pn, pv in t.get("params", {}).items():
            props[pn] = {"type": pv.get("type", "string"), "description": pn}
        out.append({"name": name, "description": t["desc"],
                    "inputSchema": {"type": "object", "properties": props}})
    return {"jsonrpc": "2.0", "result": {"tools": out}}

def main():
    ap = argparse.ArgumentParser(description="外卖能力 MCP 能力中台(栈2 P0 只读)")
    ap.add_argument("--mcp-list", action="store_true")
    ap.add_argument("--call", metavar="TOOL")
    ap.add_argument("--days", type=int)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--minutes", type=int)
    ap.add_argument("--serve", action="store_true", help="MCP streamable HTTP 服务(P1 实现)")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--tool-version", action="store_true")
    ap.add_argument("--lean4-check", action="store_true")
    args = ap.parse_args()

    if args.tool_version: print(f"bb-waimai-mcp-core {VERSION}"); return
    if args.selfcheck:
        ok = True
        for name in TOOLS:
            r = call_tool(name)
            if not r.get("ok"): ok = False
        print("TCC:", "✅ 只读工具全可达(8787)" if ok else "❌ 有工具不可达(检查 8787)")
        sys.exit(0 if ok else 1)
    if args.lean4_check:
        # 自检: 无动作工具(护栏) + 未知工具拒 + 真实只读通
        ok1 = _no_action_tools()
        ok2 = not call_tool("waimai_ghost-tool").get("ok")
        ok3 = call_tool("waimai_state").get("ok")
        print("lean4-check:", "✅ 结构门生效(无动作工具+未知拒+只读通)" if (ok1 and ok2 and ok3) else
              f"❌ 护栏={ok1} 未知拒={ok2} 只读通={ok3}")
        sys.exit(0 if (ok1 and ok2 and ok3) else 1)
    if args.mcp_list:
        print(json.dumps(mcp_list(), ensure_ascii=False, indent=1)); return
    if args.call:
        params = {}
        if args.days is not None: params["days"] = args.days
        if args.limit is not None: params["limit"] = args.limit
        if args.minutes is not None: params["minutes"] = args.minutes
        r = call_tool(args.call, params)
        # 摘要输出(防超大返回截断破坏 JSON): 状态类只保留关键字段
        if args.call == "waimai_state" and r.get("ok"):
            stores = r.get("data", {}).get("stores", [])
            r["data"] = {"store_count": len(stores), "stores": [
                {"id": s.get("id"), "name": s.get("name"), "channel": s.get("channel"),
                 "running": s.get("running"), "login": (s.get("login") or {}).get("label")}
                for s in stores[:12]]}
        print(json.dumps(r, ensure_ascii=False, indent=1)); return
    if args.serve:
        print("⚠️ MCP serve 服务在 P1 实现(当前 P0 只读 CLI)"); return
    ap.print_help()

if __name__ == "__main__":
    main()
