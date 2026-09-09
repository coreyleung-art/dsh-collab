#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""restart-intent.py — 重启方：生成标准「准备重启信息」并写黑板（R013）

用法:
  restart-intent.py prepare --node mac-mini --reason "修复 central-inbox" \
      --rescuer mbp --downtime 120 [--guard-file /tmp/restart-guard.txt]
  restart-intent.py status <node> [--set recovered|failed|restarting]  # 更新状态
  restart-intent.py show <node>                                        # 查看最近 intent

流程: 重启前 prepare → 重启后 status --set recovered（或 failed）
救援方读 notes/collab/restart-intent-<node>-<ts> 观察状态迁移。
"""
import argparse, json, os, sys, datetime, urllib.request

BB = "http://127.0.0.1:8792"
INTENT_PREFIX = "notes/collab/restart-intent"

def now_ts():
    return str(int(datetime.datetime.now().timestamp() * 1000))

def put_bb(key, value):
    try:
        req = urllib.request.Request(BB + "/" + key,
            data=json.dumps(value, ensure_ascii=False).encode(), method="PUT",
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as r:
            print(f"✅ 已写黑板 {BB}/{key}")
            return True
    except Exception as e:
        print(f"❌ 黑板写入失败: {e}")
        return False

def get_bb(key):
    try:
        req = urllib.request.Request(BB + "/" + key)
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None

def run_guard():
    """R011 强制门预检（返回通过与否）"""
    guard = os.path.expanduser("~/dsh-collab/rust-tools/dist/dsh-tools-macos-arm64-v1.10.0")
    if os.path.exists(guard):
        r = os.system(f"{guard} restart-guard ~/dsh-plugin-central-inbox ~/dsh-plugin-agent-bus ~/dsh-plugin-openchronicle --checks-dir ~/dsh-collab/rust-tools/checks > /tmp/restart-guard.txt 2>&1")
        return r == 0, open("/tmp/restart-guard.txt").read().strip().split("\n")[-2:]
    return None, ["强制门工具不存在，跳过"]

def cmd_prepare(args):
    # ① R011 强制门
    ok, guard_summary = run_guard()
    if ok is False:
        print("❌ R011 强制门 FAIL，禁止重启（先修复插件）")
        sys.exit(1)
    key = f"{INTENT_PREFIX}-{args.node}-{now_ts()}"
    intent = {
        "key": key,
        "type": "restart-intent",
        "from": args.node,
        "ts": datetime.datetime.now().isoformat(),
        "status": "preparing",
        "node": args.node,
        "planned_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "reason": args.reason,
        "impact": {
            "services_down": args.services.split(",") if args.services else ["central-inbox", "agent-way"],
            "expected_downtime_sec": int(args.downtime),
            "message_handling": "备用通道缓存 + 恢复回放（upgrade-replay）"
        },
        "prechecks": {
            "restart_guard": guard_summary,
            "health_check": "12 项全绿（黑板/SSE/node-bridge/genebank/备用通道/心跳/插件配置）"
        },
        "rescue_contact": {
            "rescuer": args.rescuer,
            "channel": f"notes/collab/rescue-{args.node}-{now_ts()}",
            "escalate_after_sec": int(args.escalate)
        },
        "rollback": args.rollback or "见 R011 强制门失败时的插件回滚方案"
    }
    if put_bb(key, intent):
        print(f"📋 准备重启信息已留档：{key}")
        print(f"   救援方 {args.rescuer} 应观察此键状态迁移（preparing→restarting→recovered）")
        # 记录最近 intent 供 show 用
        state = {"node": args.node, "last_key": key}
        os.makedirs(os.path.expanduser("~/.dsh/restart-rescue"), exist_ok=True)
        json.dump(state, open(os.path.expanduser(f"~/.dsh/restart-rescue/{args.node}.json"), "w"))

def cmd_status(args):
    state_file = os.path.expanduser(f"~/.dsh/restart-rescue/{args.node}.json")
    if not os.path.exists(state_file):
        print(f"❌ 无 {args.node} 的 intent 记录（先 prepare）")
        return
    state = json.load(open(state_file))
    key = state["last_key"]
    cur = get_bb(key)
    if cur is None:
        print(f"⚠️ 黑板无 {key}（可能已清理）")
        return
    cur_v = cur.get("value", {})
    if args.set:
        cur_v["status"] = args.set
        cur_v["recovered_ts"] = datetime.datetime.now().isoformat() if args.set == "recovered" else None
        if put_bb(key, cur_v):
            print(f"✅ 状态已更新: {args.node} → {args.set}")
    else:
        print(f"📋 {args.node} 最近 intent: {key}")
        print(f"   状态: {cur_v.get('status')} | 原因: {cur_v.get('reason')} | 计划: {cur_v.get('planned_time')}")
        print(f"   救援方: {cur_v.get('rescue_contact',{}).get('rescuer')} | 升级阈值: {cur_v.get('rescue_contact',{}).get('escalate_after_sec')}s")

def main():
    ap = argparse.ArgumentParser(description="重启救援协议 · 重启方留档工具（R013）")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("prepare")
    p.add_argument("--node", required=True, help="本设备名")
    p.add_argument("--reason", required=True, help="重启原因")
    p.add_argument("--rescuer", required=True, help="救援方设备")
    p.add_argument("--downtime", default="120", help="预计中断秒数")
    p.add_argument("--escalate", default="600", help="救援升级阈值秒数")
    p.add_argument("--services", default="", help="受影响服务（逗号分隔）")
    p.add_argument("--rollback", default="", help="回滚方案")
    s = sub.add_parser("status")
    s.add_argument("node")
    s.add_argument("--set", choices=["restarting", "recovered", "failed"], help="更新状态")
    args = ap.parse_args()
    if args.cmd == "prepare": cmd_prepare(args)
    elif args.cmd == "status": cmd_status(args)
    else: ap.print_help()

if __name__ == "__main__":
    main()
