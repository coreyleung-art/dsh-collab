#!/usr/bin/env python3
"""星舵进度监督员·每 15 分钟唤醒（v5：目标会话退役/不在线时跳过本轮）
v3 缺陷（2026-09-05 重启后自检发现）：写死 61698 端口，CLD 重启后 GUI 端口漂移（61698→62124），
   send API Connection refused，投递唤醒静默失效数日（黑板留痕仍在，真投递断）
v4 修复：动态探测 agent-bus webServer 端口（CLD 监听端口列表中找 /agent-bus/api/state 响应者）
v5 修复（2026-10-03 全架构审查实测）：XINGDUO_SESSION（8c2494e0）已于 8/30 退役，
   本脚本仍每 15min 向死会话投递 ⇒ 累计 383 条 queued + 每天 96 张黑板卡（实测语料）。
   修复：投递前查 /agent-bus/api/state，目标不在线 ⇒ 跳过本轮（不写卡不投递）。
   判据：state.agents[] 含 XINGDUO_SESSION 才继续；查询失败保守跳过（宁漏一轮不刷死会话）。"""
import json, re, subprocess, time, urllib.request

XINGDUO_SESSION = "session-8c2494e0-3772-4a62-9789-b7adc3123ccc"
BB = "http://127.0.0.1:8792"

def find_agent_bus_port():
    """从 CLD 进程监听端口找 agent-bus webServer（/agent-bus/api/state 返回 ok）"""
    try:
        r = subprocess.run(["/usr/sbin/lsof", "-nP", "-iTCP", "-sTCP:LISTEN"], capture_output=True, text=True, timeout=10)
        ports = set()
        for line in r.stdout.splitlines():
            m = re.search(r'CLD.*?127\.0\.0\.1:(\d+)', line)
            if m: ports.add(int(m.group(1)))
            m2 = re.search(r'CLD.*?\[::1\]:(\d+)', line)
            if m2: ports.add(int(m2.group(1)))
        for port in sorted(ports):
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{port}/agent-bus/api/state", method="GET")
                with urllib.request.urlopen(req, timeout=3) as resp:
                    if resp.status == 200:
                        resp.read(64)
                        return port
            except Exception:
                continue
    except Exception as e:
        print(f"[xingduo-wake] 端口探测异常: {e}", flush=True)
    return None

def target_live(port):
    """v5：目标会话是否仍在活跃会话列表；查询失败保守返回 False"""
    if port is None:
        return False
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/agent-bus/api/state", method="GET")
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())
        agents = data.get("agents") or []
        return any(a.get("id") == XINGDUO_SESSION for a in agents)
    except Exception as e:
        print(f"[xingduo-wake] 状态查询失败（保守跳过本轮）: {e}", flush=True)
        return False

def bb_put(path, v):
    body = json.dumps(v).encode()
    req = urllib.request.Request(f"{BB}/{path}", data=body, method="PUT", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode())

ts = int(time.time())
port = find_agent_bus_port()
# ★ v5 活性门：目标退役/不在线 ⇒ 本轮静默跳过（不再向死会话写卡/投递）
if not target_live(port):
    print(f"[xingduo-wake] {time.strftime('%Y-%m-%d %H:%M:%S')} 星舵会话已退役/不在线，本轮跳过（不写卡不投递）", flush=True)
    raise SystemExit(0)

# ① 黑板留审计痕
try:
    bb_put(f"notes/8c2494e0/xingduo-wake-{ts}", {
        "value": {"from": "coordinator", "to": XINGDUO_SESSION, "type": "wake",
                  "body": "星舵，定时巡检时间到：扫 data/blueprint/ + data/iterations/ + data/progress/ → 有停滞写提醒卡 + 短提示协调者。24h 同项不重复。",
                  "ts": ts},
        "ts": ts
    })
except Exception as e:
    print(f"[xingduo-wake] bb_put 失败: {e}", flush=True)

# ② 真·投递唤醒（port 已由活性门保证非 None）
try:
    body = json.dumps({
        "to": XINGDUO_SESSION,
        "text": "【星舵·15min 定时巡检】扫黑板 data/blueprint/ + data/iterations/ + data/progress/，判断主线与 active 阶段是否停滞；有停滞写提醒卡并短提示协调者（24h 同项不重复）；无停滞静默。",
    }).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/agent-bus/api/send", data=body, method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as r:
        resp = json.loads(r.read().decode())
    print(f"[xingduo-wake] {time.strftime('%Y-%m-%d %H:%M:%S')} 投递唤醒(port {port}): {resp.get('status')}", flush=True)
except Exception as e:
    print(f"[xingduo-wake] send API 失败: {e}", flush=True)
