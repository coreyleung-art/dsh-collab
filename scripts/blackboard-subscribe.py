#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""blackboard-subscribe v0.1 (HR) — S6 A 级 PoC：黑板订阅检测

监听黑板载体（registry/pending-work-plan/approval-ledger）变更 → 解析 topic/key → 匹配订阅表 → 写唤醒队列（agent 侧定向发送）。
零 LLM 成本。
用法：python3 blackboard-subscribe.py [--dry-run]
输出：wakeup-queue/YYYY-MM-DD.jsonl（应唤醒项）+ blackboard-subscribe-state.json（上次 hash 快照）
验收目标：无广播；每变更每订阅者 ≤1 条；唤醒延迟 <5min（launchd 每 5 分钟）；成本 ≈0.05×读。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, hashlib, datetime


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/blackboard-subscribe.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

COLLAB = os.path.expanduser("~/dsh-collab")
STATE = os.path.join(COLLAB, "token-monitor", "blackboard-subscribe-state.json")
QUEUE_DIR = os.path.join(COLLAB, "token-monitor", "wakeup-queue")
SUB = os.path.join(COLLAB, "subscriptions.json")
BOARDS = [
    ("registry", os.path.join(COLLAB, "resource-registry.md")),
    ("ledger", os.path.join(COLLAB, "approval-ledger.md")),
    ("workplan", os.path.join(COLLAB, "pending-work-plan.md")),
]

def sha(p):
    try: return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
    except Exception: return ""

def load_state():
    try: return json.load(open(STATE, encoding="utf-8"))
    except Exception: return {}

def save_state(s):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(s, open(STATE, "w", encoding="utf-8"))

def load_subs():
    try: return json.load(open(SUB, encoding="utf-8")).get("subscriptions", [])
    except Exception: return []

def diff_text(p, old_sha):
    """返回变更摘要：从文件尾部提取新增行（简化：取前 N 行变更提示）"""
    try:
        lines = open(p, encoding="utf-8", errors="ignore").read().splitlines()
        return "changed: %d lines total" % len(lines)
    except Exception:
        return ""

def detect(board, path, state):
    """检测单黑板变更：hash 差分 + 增量行提取"""
    prev = state.get(board, {}).get("sha", "")
    cur = sha(path)
    if cur == prev or cur == "":
        return None
    # 内容 diff（方向无关）：新行 = 新内容不在旧内容中的行
    try:
        lines = open(path, encoding="utf-8", errors="ignore").read().splitlines()
        prev_set = set(state.get(board, {}).get("prev", []))
        new_lines = [l for l in lines if l not in prev_set]
    except Exception:
        new_lines = []
    return {"board": board, "path": path, "sha": cur, "new_lines": new_lines[:10], "ts": datetime.datetime.now().isoformat(timespec="seconds")}

def match_subscribers(change, subs):
    """按 topic 关键词匹配订阅者"""
    text = "\n".join(change.get("new_lines", [])) + " " + change.get("board", "")
    hits = []
    for s in subs:
        for pat in s.get("topics", []):
            if pat.lower() in text.lower():
                hits.append({"agent": s.get("agent"), "topic": pat})
                break
    return hits

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    state = load_state()
    subs = load_subs()
    os.makedirs(QUEUE_DIR, exist_ok=True)
    queue_file = os.path.join(QUEUE_DIR, datetime.date.today().isoformat() + ".jsonl")
    changes = []
    for board, path in BOARDS:
        ch = detect(board, path, state)
        if ch:
            changes.append(ch)
            state[board] = {"sha": ch["sha"], "lines": ch.get("lines", 0)}
    added = 0
    for ch in changes:
        for hit in match_subscribers(ch, subs):
            entry = {"ts": ch["ts"], "board": ch["board"], "topic": hit["topic"], "agent": hit["agent"],
                     "summary": ch["new_lines"][-1] if ch["new_lines"] else "board updated", "sent": False}
            with open(queue_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            added += 1
            print("WAKE:", hit["agent"], "<-", ch["board"], "/", hit["topic"], "|", entry["summary"][:60])
    # 更新 prev 全文快照
    for board, path in BOARDS:
        try:
            state[board]["prev"] = open(path, encoding="utf-8", errors="ignore").read().splitlines()
        except Exception:
            pass
    save_state(state)
    print("subscribe scan: boards=%d changes=%d wakeups=%d (queue=%s)" % (len(BOARDS), len(changes), added, queue_file))

if __name__ == "__main__":
    main()