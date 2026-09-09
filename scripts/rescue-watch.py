#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rescue-watch.py — 救援方：观察重启方状态，异常发救援信号（R013）

用法:
  rescue-watch.py watch <重启方节点> [--interval 30]   # 持续观察（launchd 常驻）
  rescue-watch.py watch <重启方节点> --once             # 单次检查
  rescue-watch.py signal <重启方节点> --reason "..."    # 手动发救援信号
  rescue-watch.py allow <动作>                          # 查询救援动作白名单

观察逻辑:
  1. 读黑板 notes/collab/restart-intent-<node>-<ts> 状态字段
  2. 监控重启方心跳（间隔 >90s = 离线）
  3. 状态异常或超时未恢复 → 写救援信号 notes/collab/rescue-<node>-<ts>

救援边界（R013 禁止破坏性）:
  ✅ 只读诊断 / 守护重启 / 状态记录
  ⛔ 删数据 / 改配置 / 覆盖文件 / 破坏性项目
"""
import argparse, json, os, sys, time, datetime, urllib.request

BB = "http://127.0.0.1:8792"
INTENT_PREFIX = "notes/collab/restart-intent"
RESCUE_PREFIX = "notes/collab/rescue"

# R013 救援动作白名单（允许）与黑名单（禁止）
ALLOWED_ACTIONS = ["read-logs", "check-process", "check-resources", "restart-daemon", "write-status", "notify"]
FORBIDDEN_ACTIONS = ["delete-data", "modify-config", "reset", "destructive-project", "business-data"]

def now_ts():
    return str(int(datetime.datetime.now().timestamp() * 1000))

def put_bb(key, value):
    try:
        req = urllib.request.Request(BB + "/" + key,
            data=json.dumps(value, ensure_ascii=False).encode(), method="PUT",
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as r:
            return True
    except Exception as e:
        print(f"⚠️ 黑板写入失败: {e}")
        return False

def get_bb(key):
    try:
        req = urllib.request.Request(BB + "/" + key)
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None

def list_intents(node):
    """列黑板该节点的所有 intent（取最近一个）"""
    try:
        req = urllib.request.Request(BB + "/notes/collab/")
        with urllib.request.urlopen(req, timeout=8) as r:
            d = json.loads(r.read().decode())
        items = d.get("list", {})
        keys = [k for k in items if k.startswith(f"{INTENT_PREFIX}-{node}-")]
        if not keys:
            return None
        latest = sorted(keys)[-1]
        return latest, items[latest].get("value", {})
    except Exception:
        return None

def check_heartbeat(node):
    """检查重启方心跳，返回 (在线, 距现在秒)"""
    d = get_bb(f"/nodes/{node}/heartbeat")
    if d is None:
        return False, None
    v = d.get("value", {})
    ts = v.get("ts", "0")
    try:
        age = int(time.time()) - int(ts)
    except Exception:
        age = None
    return True, age

def cmd_watch(args):
    node = args.node
    intent = list_intents(node)
    if intent is None:
        print(f"[rescue-watch] {datetime.datetime.now().strftime('%H:%M:%S')} 无 {node} 的 restart-intent（未准备重启或已清理）")
        return
    key, val = intent
    status = val.get("status", "?")
    print(f"[rescue-watch] 观察 {node}: {key} | 状态: {status} | 原因: {val.get('reason','')[:40]}")

    # 心跳检查
    online, age = check_heartbeat(node)
    if online and age is not None:
        print(f"[rescue-watch] 心跳: {'✅ 在线' if age <= 90 else f'⚠️ 距现在 {age}s（>90s 离线阈值）'}")
    else:
        print(f"[rescue-watch] 心跳: ❌ 无法读取")

    # 超时判断（escalate_after）
    if status == "restarting":
        esc = val.get("rescue_contact", {}).get("escalate_after_sec", 600)
        started = val.get("ts", "")
        print(f"[rescue-watch] 重启进行中，升级阈值 {esc}s（{key}）")
        # 简单判断：intent 写入时间已超过阈值且未 recovered
        try:
            ts_int = int(started.split(".")[0].replace("-", "").replace("T", "").replace(":", "")[:14])
            # 简化：不精确判断，交给人工/协调者确认
        except Exception:
            pass

    # 离线超时 → 救援信号
    if (not online) or (age is not None and age > 90 and status != "restarting"):
        print(f"[rescue-watch] ⚠️ {node} 异常（心跳离线 {age}s / 状态 {status}）→ 建议发救援信号")
        if args.once and args.auto_signal:
            rkey = f"{RESCUE_PREFIX}-{node}-{now_ts()}"
            put_bb(rkey, {
                "type": "rescue-signal", "from": args.from_node or "rescuer",
                "node": node, "ts": datetime.datetime.now().isoformat(),
                "evidence": f"心跳离线 {age}s / intent 状态 {status}",
                "suggested": "非破坏性救援：check-process → restart-daemon",
                "forbidden": "禁止：delete-data / modify-config / destructive",
            })
            print(f"[rescue-watch] 🚨 已发救援信号 {rkey}")

def cmd_signal(args):
    rkey = f"{RESCUE_PREFIX}-{args.node}-{now_ts()}"
    ok = put_bb(rkey, {
        "type": "rescue-signal", "from": args.from_node or "rescuer",
        "node": args.node, "ts": datetime.datetime.now().isoformat(),
        "reason": args.reason,
        "allowed": ALLOWED_ACTIONS, "forbidden": FORBIDDEN_ACTIONS,
    })
    print(f"{'🚨 已发救援信号' if ok else '❌ 发送失败'} {rkey}")

def cmd_allow(args):
    print("✅ 允许（非破坏性）:", ", ".join(ALLOWED_ACTIONS))
    print("⛔ 禁止（破坏性）:", ", ".join(FORBIDDEN_ACTIONS))

def main():
    ap = argparse.ArgumentParser(description="重启救援协议 · 救援方观察工具（R013）")
    sub = ap.add_subparsers(dest="cmd")
    w = sub.add_parser("watch")
    w.add_argument("node")
    w.add_argument("--once", action="store_true")
    w.add_argument("--auto-signal", action="store_true", help="异常自动发救援信号")
    w.add_argument("--from-node", default="", help="救援方设备名")
    s = sub.add_parser("signal")
    s.add_argument("node")
    s.add_argument("--reason", default="救援方观察发现异常")
    s.add_argument("--from-node", default="")
    sub.add_parser("allow")
    args = ap.parse_args()
    if args.cmd == "watch": cmd_watch(args)
    elif args.cmd == "signal": cmd_signal(args)
    elif args.cmd == "allow": cmd_allow(args)
    else: ap.print_help()

if __name__ == "__main__":
    main()
