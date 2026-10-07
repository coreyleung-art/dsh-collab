#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify-watch.py — 跨设备重启验证守护 v3.2

v1 缺陷：心跳 ts 每 60s 更新是常态，用 ts 比较每 60s 误触发。
v2 修复：改为心跳间隔 >90s 才触发（检测 node-bridge 离线/重启）。
v3 追加：存活探针机制（CLD 重启 ≠ node-bridge 重启）。
v3.1 优化：探针只在【离线恢复】或【显式重启通知】时发，平时静默只检查 ack+心跳，不刷屏。
v3.2（2026-08-28）：探针改为【不写黑板】——双向注入链路已验证通（SSE 广播修复），
   探针消息再写黑板会被 central-inbox 注入业务会话造成排队刷屏；改为仅记录状态，需要时看日志。

策略（v3.2 最终）：
  1. 每轮检查 ack（verify-<node>-ack）→ 有 = 注入链路确认通过（最终信号）
  2. 每轮检查心跳 → 间隔>90s = node-bridge 离线/重启 → 恢复时记录（不再写黑板探针）
  3. 探针写入 notes/<node>/verify-recovery-<ts>（仅在离线恢复时）
  4. 已验证的节点停发探针（去重）

用法:
  python3 verify-watch.py --once           # 单次检查（launchd 每 5 分钟）
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, time, datetime, urllib.request

BB = "http://127.0.0.1:8792"
STATE_FILE = os.path.expanduser("~/.dsh/inbox/verify-watch.json")
NODES = ["mbp", "i9"]
OFFLINE_THRESHOLD = 90   # 心跳间隔超过此值 = node-bridge 离线/重启
ACK_KEY = "notes/collab/verify-{node}-ack"

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def bb_get(key):
    try:
        with urllib.request.urlopen(f"{BB}/{key}", timeout=5) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None

def bb_put(key, value):
    try:
        req = urllib.request.Request(
            f"{BB}/{key}", data=json.dumps(value).encode(),
            headers={"Content-Type": "application/json"}, method="PUT")
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"  ⚠️ 写 {key} 失败: {e}")
        return None

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"last_ts": {}, "verified": {}, "recovery_probe": {}}

def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="单次检查（launchd 模式）")
    args = ap.parse_args()

    state = load_state()
    ts_ms = int(time.time() * 1000)

    for node in NODES:
        # ── ① ack 检测（最终信号）──
        # 真实 ack 必须带 payload.confirm == true（防止测试/噪音 ack 误判）
        ack = bb_get(ACK_KEY.format(node=node))
        is_real_ack = False
        if ack and "value" in ack:
            ack_val = ack.get("value", {})
            if isinstance(ack_val, dict):
                pl = ack_val.get("payload", {})
                is_real_ack = pl.get("confirm") is True or ack_val.get("confirm") is True
        if is_real_ack:
            if state["verified"].get(node) != "yes":
                state["verified"][node] = "yes"
                print(f"[{now()}] 🎉 {node} 验证 ack 已收到——注入链路确认通过！")
            else:
                print(f"[{now()}] {node} 已验证（ack 持续）")
            save_state(state)
            continue

        # ── ② 心跳检测（node-bridge 离线/重启）──
        hb = bb_get(f"nodes/{node}/heartbeat")
        if not hb or "value" not in hb:
            print(f"[{now()}] {node}: 心跳不可读（node-bridge 离线？）")
            continue
        hb_ts = hb["value"].get("ts", "")
        try:
            hb_epoch = int(hb_ts) if hb_ts.isdigit() else int(
                datetime.datetime.fromisoformat(hb_ts.replace("Z", "+00:00")).timestamp())
        except Exception:
            hb_epoch = 0

        prev_ts = state["last_ts"].get(node)
        gap = 0
        if prev_ts:
            try:
                prev_epoch = int(prev_ts) if prev_ts.isdigit() else int(
                    datetime.datetime.fromisoformat(prev_ts.replace("Z", "+00:00")).timestamp())
                gap = hb_epoch - prev_epoch
            except Exception:
                gap = 0
        state["last_ts"][node] = hb_ts

        if gap > OFFLINE_THRESHOLD:
            # node-bridge 离线后恢复 → 发恢复探针（此时可能 CLD 也重启了）
            # 2026-08-28 改动：链路已验证通（双向注入 OK），探针不再写黑板（避免
            # central-inbox 注入刷屏；需要时手动看日志）。保留状态记录。
            if state["recovery_probe"].get(node) != hb_ts:
                probe_key = f"notes/{node}/verify-recovery-{ts_ms}"
                probe = {
                    "type": "verify-recovery",
                    "node": "mac-mini",
                    "ts": ts_ms,
                    "target": node,
                    "subject": f"恢复探针（{node} 离线 {gap}s 后恢复）",
                    "body": f"检测到 {node} node-bridge 离线 {gap}s 后恢复。若 CLD 已重启且 central-inbox 生效，此消息应注入本地会话。请回报黑板 {ACK_KEY.format(node=node)}。",
                }
                # 探针不再写入黑板（链路已通，注入刷屏风险 > 验证价值）
                print(f"  📡 {node} 恢复探针（已停发黑板写入，仅记录）: {probe_key} gap={gap}s")
                state["recovery_probe"][node] = hb_ts
            else:
                print(f"  ↻ {node} 恢复探针已发过")
        elif gap > 0:
            print(f"[{now()}] {node}: 心跳正常（间隔 {gap}s）")
        else:
            print(f"[{now()}] {node}: 心跳记录 {hb_ts}")

    save_state(state)
    print(f"[{now()}] 完成。")

if __name__ == "__main__":
    main()
