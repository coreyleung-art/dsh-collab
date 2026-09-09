#!/usr/bin/env python3
"""comm-server 心跳镜像转发器（本机 → 中枢）
把本机黑板 nodes/mbp/heartbeat + nodes/i9/heartbeat 转发到中枢（双写：本机保留+中枢镜像）
目的：跨设备心跳走中枢（统一裁决）但保留本机旧通道（降级备灾，永续通讯）
触发：launchd 常驻，每 30s 转发（只转最新心跳）
"""
import json, os, sys, time, urllib.request

LOCAL_BB = os.environ.get("LOCAL_BB", "http://127.0.0.1:8792")
CENTRAL_BB = os.environ.get("CENTRAL_BB", "http://xingqiao.meetfunbp.com:8792")
FORWARD_NODES = ("mbp", "i9")
INTERVAL = int(os.environ.get("INTERVAL", "30"))

def log(m):
    print(f"[hb-fwd] {time.strftime('%H:%M:%S')} {m}", flush=True)

def fwd_once():
    for node in FORWARD_NODES:
        try:
            with urllib.request.urlopen(LOCAL_BB + f"/nodes/{node}/heartbeat", timeout=5) as r:
                d = json.loads(r.read())
            val = d.get("value", {})
            if not val: continue
            # 加双写标记
            val2 = dict(val)
            val2["_mirror"] = "mac-mini-fwd"
            body = json.dumps(val2).encode()
            req = urllib.request.Request(CENTRAL_BB + f"/nodes/{node}/heartbeat",
                data=body, method="PUT", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as r:
                log(f"转发 {node} 心跳 → 中枢 (HTTP {r.status})")
        except Exception as e:
            log(f"{node} 转发失败: {str(e)[:60]}")
    # 转发中枢本机心跳（中枢知道 mac-mini 活着）
    try:
        with urllib.request.urlopen(LOCAL_BB + "/nodes/mac-mini/heartbeat", timeout=5) as r:
            d = json.loads(r.read())
        val = dict(d.get("value", {}))
        val["_mirror"] = "mac-mini-fwd"
        body = json.dumps(val).encode()
        req = urllib.request.Request(CENTRAL_BB + "/nodes/mac-mini/heartbeat",
            data=body, method="PUT", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            log(f"转发 mac-mini 心跳 → 中枢")
    except Exception as e:
        log(f"mac-mini 转发失败: {str(e)[:60]}")


# ═══════════ E2 全局注册表（发现层 · data/discovery/agents/）═══════════
# mac-mini 设备级注册：device + 核心会话（会话全量由端侧自注册器扩展）
# schema v1：心跳驱动活性（读侧 G5：mac-mini 心跳<90s = online）
REGISTRY_SESSIONS = [
    {"session_id": "session-fa1f9150-c949-401f-ba8c-d265f6221676", "role": "星桥(协调者)"},
    {"session_id": "session-a190c54c-ca73-4845-9a65-9dc002d45044", "role": "明鉴(SystemGraph架构)"},
    {"session_id": "session-2a15e6b1-32a9-48b3-a167-8fe0a28e8d82", "role": "HR司库"},
]


def registry_register():
    """E2: 心跳时同注册各设备到服务器发现层 data/discovery/agents/<dev>
    mac-mini 自注册(核心会话); mbp 设备级兜底注册(MBP 自注册可覆盖, PUT 幂等)"""
    now = int(time.time())
    regs = [
        ("mac-mini", REGISTRY_SESSIONS),
        # mbp 兜底: 端侧(164dceca)自注册后可覆盖此设备级
        ("mbp", [{"session_id": "session-164dceca-c0c1-4370-a1f5-f99f22a72e17", "role": "MBP资源中枢"}]),
    ]
    for dev, sessions in regs:
        try:
            val = {
                "device": dev, "schema": "v1", "status": "online",
                "sessions": sessions,
                "heartbeat_ref": f"nodes/{dev}/heartbeat",
                "via": "hb-fwd-mac-mini" if dev != "mac-mini" else "self",
                "ts": now,
            }
            body = json.dumps(val).encode()
            req = urllib.request.Request(CENTRAL_BB + f"/data/discovery/agents/{dev}",
                data=body, method="PUT", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as r:
                log(f"E2注册 {dev} → 发现层 (HTTP {r.status})")
        except Exception as e:
            log(f"E2注册 {dev} 失败: {str(e)[:60]}")

if __name__ == "__main__":
    if "--once" in sys.argv:
        fwd_once()
        registry_register()
    else:
        log(f"常驻启动: 每 {INTERVAL}s 转发心跳 + E2 注册到中枢")
        while True:
            fwd_once()
            registry_register()
            time.sleep(INTERVAL)
