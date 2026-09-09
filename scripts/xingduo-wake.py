#!/usr/bin/env python3
"""星舵进度监督员·每 15 分钟唤醒（v4：agent-bus 端口动态探测）
v3 缺陷（2026-09-05 重启后自检发现）：写死 61698 端口，CLD 重启后 GUI 端口漂移（61698→62124），
   send API Connection refused，投递唤醒静默失效数日（黑板留痕仍在，真投递断）
v4 修复：动态探测 agent-bus webServer 端口（CLD 监听端口列表中找 /agent-bus/api/state 响应者）"""
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

def bb_put(path, v):
    body = json.dumps(v).encode()
    req = urllib.request.Request(f"{BB}/{path}", data=body, method="PUT", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode())

ts = int(time.time())
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

# ② 真·投递唤醒（动态端口）
port = find_agent_bus_port()
if port is None:
    print(f"[xingduo-wake] {time.strftime('%Y-%m-%d %H:%M:%S')} agent-bus 端口未找到，投递跳过（黑板留痕仍完成）", flush=True)
else:
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
