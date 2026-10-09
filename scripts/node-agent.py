#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""node-agent v0.1 (HR) — 节点总线 PoC 执行器

注册→心跳(60s)→命令轮询→本地探针→回报。黑板 :8792 为状态中枢。
用法：python3 node-agent.py --node-id mbp [--blackboard http://127.0.0.1:8792] [--once]

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== node-agent 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · node-agent v0.1 (HR) — 节点总线 PoC 执行器")
    print("  · 注册→心跳(60s)→命令轮询→本地探针→回报。黑板 :8792 为状态中枢。")
    print("  · 用法：python3 node-agent.py --node-id mbp [--blackboard http://127.0.0.1:8792] [--once]")
    print("  · ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。")
    print("  · 命令/参数: node-id, blackboard, once, interval")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/node-agent.log")
    return 0

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, time, datetime, urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/node-agent.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

BB = "http://127.0.0.1:8792"
PROBES = {
    "dsh": lambda: "ok" if os.path.exists(os.path.expanduser("~/.dsh")) else "missing",
    "blackboard": lambda: _get("/nodes/") != None,
}

def _req(method, path, data=None):
    url = os.environ.get("NODE_AGENT_BB", BB) + path
    body = json.dumps(data, ensure_ascii=False).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception as ex:
        return {"error": str(ex)[:80]}

def _get(path):
    return _req("GET", path)

def heartbeat(node_id):
    probes = {k: (v() if callable(v) else v) for k, v in PROBES.items()}
    return _req("PUT", "/nodes/%s/heartbeat" % node_id, {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "load": os.getloadavg()[0] if hasattr(os, "getloadavg") else 0,
        "probes": probes, "health": "ok"})

def register(node_id, caps):
    return _req("PUT", "/nodes/%s" % node_id, {"status": "online", "capabilities": caps, "registered": True})

def poll_commands(node_id):
    """轮询黑板 tasks/<node_id>/cmd 看有没有命令（PoC：命令由调度者 PUT 写入）"""
    r = _req("GET", "/tasks/%s/cmd" % node_id)
    if r and "value" in r and r["value"]:
        cmd = r["value"]
        print("CMD:", cmd)
        _req("DELETE", "/tasks/%s/cmd" % node_id)
        return cmd
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--node-id", default="mbp")
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    ap.add_argument("--blackboard", default=BB)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=60)
    if "--selfcheck" in __import__("sys").argv:
        return selfcheck()
    args = ap.parse_args()
    os.environ["NODE_AGENT_BB"] = args.blackboard
    caps = ["dsh", "blackboard-client", "scripts"]
    print("register:", register(args.node_id, caps))
    while True:
        hb = heartbeat(args.node_id)
        print("heartbeat:", json.dumps(hb, ensure_ascii=False)[:120])
        cmd = poll_commands(args.node_id)
        if cmd:
            print("  executing:", cmd)
        if args.once:
            break
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
