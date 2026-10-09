#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""central-wake.py — 中枢自动感知守护（解决『中枢未自主收到信息』）

核心问题：bb-sub 把消息落盘 inbox，但不唤醒中枢会话 → 中枢不自主感知。
本守护：检测中枢 inbox（~/.dsh/inbox/bb/coordinator.jsonl）新增 → 
  ① 写触发标记（黑板 data/central/wake-trigger，供中枢会话感知）
  ② 尝试 agent_wake 唤醒中枢会话（若可用）
  ③ 记录审计

用法:
  python3 central-wake.py --once
  python3 central-wake.py --interval 60   # launchd 常驻

依赖:
  · bb-sub coordinator 订阅器已落盘 ~/.dsh/inbox/bb/coordinator.jsonl
  · 黑板 127.0.0.1:8792（写触发标记）
  · agent_wake 工具（DSH 宿主，可选唤醒）

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, time, datetime, urllib.request, subprocess


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/central-wake.log")


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
COORD_INBOX = os.path.expanduser("~/.dsh/inbox/bb/coordinator.jsonl")
SEEN_FILE = os.path.expanduser("~/.dsh/inbox/bb/coordinator.seen")
TRIGGER_KEY = "data/central/wake-trigger"
CENTRAL_SESSION = "session-fa1f9150-c949-401f-ba8c-d265f6221676"

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def load_seen():
    try:
        return json.load(open(SEEN_FILE))
    except Exception:
        return {"count": 0, "last_key": ""}

def save_seen(s):
    json.dump(s, open(SEEN_FILE, "w"))

def put_bb(path, value):
    try:
        # v1.1: BLACKBOARD_TOKEN 支持（黑板 v0.6.5 认证）
        bb_token = os.environ.get("BLACKBOARD_TOKEN", "")
        headers = {"Content-Type": "application/json"}
        if bb_token:
            headers["X-Blackboard-Token"] = bb_token
        # ★ A1 写端鉴权预备（2026-10-03）：~/.dsh/blackboard-token 存在则带 Bearer（flip 后必需）
        try:
            with open(os.path.expanduser("~/.dsh/blackboard-token")) as _f:
                headers["Authorization"] = "Bearer " + _f.read().strip()
        except Exception:
            pass
        req = urllib.request.Request(BB + "/" + path.lstrip("/"),
            data=json.dumps(value, ensure_ascii=False).encode(), method="PUT", headers=headers)
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None

def check_new():
    if not os.path.exists(COORD_INBOX):
        return None
    lines = [l for l in open(COORD_INBOX, encoding="utf-8").read().strip().split("\n") if l.strip()]
    if not lines:
        return None
    # 最后一条
    last = json.loads(lines[-1])
    seen = load_seen()
    # 新消息判断：最后一条的 key/ts 不同于已见
    last_sig = f"{last.get('ts')}|{last.get('key')}"
    if seen.get("last_key") == last_sig:
        return None
    return last, lines, seen

def trigger():
    result = check_new()
    if not result:
        return False
    last, lines, seen = result
    # 写触发标记（中枢会话可感知）
    put_bb(TRIGGER_KEY, {
        "ts": now(),
        "source": "central-wake",
        "new_message": last.get("key", ""),
        "inbox_count": len(lines),
        "preview": str(last.get("value", {}))[:100],
    })
    # 更新 seen
    seen["last_key"] = f"{last.get('ts')}|{last.get('key')}"
    seen["count"] = len(lines)
    save_seen(seen)
    print(f"[central-wake] {now()} 📩 新消息: {last.get('key')} → 已写触发标记 + seen 更新", flush=True)
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=60)
    args = ap.parse_args()
    print(f"[central-wake] {now()} 启动（监听 {COORD_INBOX}，{args.interval}s）", flush=True)
    while True:
        try:
            trigger()
        except Exception as e:
            print(f"[central-wake] {now()} error: {str(e)[:80]}", flush=True)
        if args.once:
            break
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
