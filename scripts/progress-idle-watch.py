#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""progress-idle-watch.py — 待命信号检测 + 主线进度提醒（用户提议机制 v2）
原理：
  ① 检测黑板消息新鲜度：最近 N 分钟无新消息写入 → 系统空闲（协调者已待命）
  ② 空闲且 24h 内未提醒 → 生成进度提醒卡 data/progress/reminder-<ts>
  ③ 注入协调者上下文（写黑板 → central-inbox SSE 注入自动唤醒）
  ④ 防重复：24h 内同 key 不重复；有新活动自动取消信号
用法：launchd 每 5 分钟跑（com.dsh.progress-idle-watch）
"""
import json, os, sys, time, urllib.request

BB = "http://127.0.0.1:8792"
IDLE_MINUTES = 10      # 无新消息超时 = 空闲
REMINDER_INTERVAL = 24 * 3600  # 24h 内不重复提醒
STATE_FILE = os.path.expanduser("~/.dsh/progress-idle-state.json")

def bb_get(path):
    with urllib.request.urlopen(f"{BB}/{path}", timeout=8) as r:
        return json.loads(r.read().decode())

def bb_put(path, v):
    body = json.dumps(v).encode()
    req = urllib.request.Request(f"{BB}/{path}", data=body, method="PUT",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode())

def latest_msg_ts():
    """黑板最近消息时间戳（collab + iterations + tasks）"""
    latest = 0
    for ns in ["notes?node=collab", "data?node=iterations", "data?node=blueprint"]:
        try:
            d = bb_get(ns)
            lst = d.get("list", {})
            for k, v in lst.items():
                ts = v.get("ts", "")
                if isinstance(ts, str):
                    try:
                        t = time.mktime(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S"))
                        latest = max(latest, t)
                    except: pass
        except: pass
    return latest

def load_state():
    try:
        return json.load(open(STATE_FILE))
    except:
        return {"last_reminder": 0, "last_idle": 0}

def save_state(s):
    json.dump(s, open(STATE_FILE, "w"), indent=1)

def check_mainline():
    """检查主线停滞项（简版：最近迭代报告时间）"""
    try:
        d = bb_get("data?node=iterations")
        lst = d.get("list", {})
        reports = [k for k in lst if "fa1f9150" in k or "iteration" in k]
        return f"最近主线迭代报告 {len(reports)} 份"
    except:
        return "主线状态读取失败"

def main():
    s = load_state()
    now = time.time()
    latest = latest_msg_ts()

    # ① 空闲检测
    idle_for = now - latest if latest else 99999
    if idle_for < IDLE_MINUTES * 60:
        # 系统活跃，不提醒（待命信号取消）
        if s.get("last_idle"):
            s["last_idle"] = 0
            save_state(s)
        return

    # ② 空闲确认 → 挂待命信号
    idle_key = f"data/progress/idle-{int(now)}"
    try:
        bb_put(idle_key, {"value": {"idle_since": now, "idle_minutes": int(idle_for/60),
                                    "check": check_mainline()}, "ts": int(now)})
        s["last_idle"] = now
    except: pass

    # ③ 24h 内已提醒过则跳过
    if now - s.get("last_reminder", 0) < REMINDER_INTERVAL:
        save_state(s)
        return

    # ④ 生成进度提醒卡（写黑板 → central-inbox 注入协调者）
    reminder = {
        "value": {
            "type": "progress-reminder",
            "from": "进度监督机制",
            "title": "主线进度提醒（待命触发）",
            "check": check_mainline(),
            "idle_minutes": int(idle_for / 60),
            "suggest": [
                "① 检查蓝图 flowernet 是否有停滞 stage（data/blueprint/）",
                "② 主线排期：MCP SSE 传输模式 / Rust 工具扩展 / 特征库",
                "③ 端侧 batch2 标注如有回报可批量处理（不阻塞主线）"
            ],
            "ts": int(now)
        },
        "ts": int(now)
    }
    try:
        bb_put(f"data/progress/reminder-{int(now)}", reminder)
        s["last_reminder"] = now
        save_state(s)
        print(f"[progress-idle-watch] 空闲 {int(idle_for/60)}min → 已写提醒卡 data/progress/reminder-{int(now)}")
    except Exception as e:
        print(f"[progress-idle-watch] 提醒写入失败: {e}")

if __name__ == "__main__":
    main()
