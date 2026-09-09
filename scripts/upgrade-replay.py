#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""upgrade-replay.py — 升级后消息回放（备用通道保持机制 · 保障 3）

CLD 重启/升级期间，CLD 内插件（central-inbox/agent-way）失联，但守护层
（bb-sub → coordinator.jsonl 缓存 + central-wake → wake-trigger）全程在线，
消息不丢失。本工具在 CLD 恢复后执行「恢复回放」：

  1. 读 bb-sub 落盘缓存 ~/.dsh/inbox/bb/coordinator.jsonl（append-only JSONL）
  2. 按水位（coordinator.seen last_key）过滤未处理消息
  3. 逐条归档到黑板 data/central/replay-<ts>/ 子键（防丢 + 可审计）
  4. 更新水位 seen → 下次不再重复

用法:
  python3 upgrade-replay.py            # 回放未处理消息
  python3 upgrade-replay.py --dry-run  # 只预览不归档
  python3 upgrade-replay.py --since <ts>  # 从指定时间戳回放

依赖:
  · bb-sub.coordinator 落盘缓存（~/.dsh/inbox/bb/coordinator.jsonl）
  · 黑板 127.0.0.1:8792（归档 PUT）
  · 与 central-wake.py 共享 seen 水位（避免重复处理）

产出:
  · 黑板 data/central/replay-<batch_ts>/<n> 归档每条未处理消息
  · 打印回放清单（key/ts/from），供中枢会话逐条登记
"""
import argparse, json, os, sys, time, datetime, urllib.request

BB = "http://127.0.0.1:8792"
COORD_INBOX = os.path.expanduser("~/.dsh/inbox/bb/coordinator.jsonl")
SEEN_FILE = os.path.expanduser("~/.dsh/inbox/bb/coordinator.seen")
ARCHIVE_PREFIX = "data/central/replay"

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def now_ts():
    return str(int(time.time() * 1000))

def load_seen():
    try:
        return json.load(open(SEEN_FILE))
    except Exception:
        return {"count": 0, "last_key": ""}

def save_seen(s):
    json.dump(s, open(SEEN_FILE, "w"))

def put_bb(path, value):
    try:
        req = urllib.request.Request(BB + "/" + path.lstrip("/"),
            data=json.dumps(value, ensure_ascii=False).encode(), method="PUT")
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"[upgrade-replay] ❌ 黑板写入失败 {path}: {str(e)[:60]}", flush=True)
        return None

def read_cache():
    """读 bb-sub 缓存（JSONL），返回消息列表"""
    if not os.path.exists(COORD_INBOX):
        return []
    out = []
    with open(COORD_INBOX, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue  # 跳过坏行（JSONL 追加，极端情况可能截断）
    return out

def filter_new(messages, seen):
    """按水位过滤未处理消息（seen.last_key 格式: ts|key）"""
    if not messages:
        return []
    last_sig = seen.get("last_key", "")
    if not last_sig:
        return messages  # 无水位 → 全部视为新（首次运行）
    # 找到水位所在索引，其后均为未处理
    idx = -1
    for i, m in enumerate(messages):
        sig = f"{m.get('ts')}|{m.get('key')}"
        if sig == last_sig:
            idx = i
    if idx < 0:
        # 水位不在缓存（可能缓存轮转）→ 保守：返回最后 50 条供人工确认
        return messages[-50:]
    return messages[idx + 1:]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只预览不归档")
    ap.add_argument("--since", type=str, default="", help="从指定时间戳回放（可选）")
    args = ap.parse_args()

    seen = load_seen()
    messages = read_cache()
    if not messages:
        print(f"[upgrade-replay] {now()} 缓存为空（{COORD_INBOX} 不存在或无内容）")
        return

    new = filter_new(messages, seen)
    if args.since:
        new = [m for m in new if str(m.get('ts', '')) >= args.since]

    print(f"[upgrade-replay] {now()} 缓存 {len(messages)} 条 | 水位 {seen.get('last_key', '(无)')} | 未处理 {len(new)} 条")
    if not new:
        print("[upgrade-replay] ✅ 无未处理消息，无需回放")
        return

    batch_ts = now_ts()
    processed = 0
    for i, m in enumerate(new):
        key = m.get("key", "?")
        ts = m.get("ts", "?")
        val = m.get("value", {})
        frm = val.get("from", "?") if isinstance(val, dict) else "?"
        preview = str(val)[:120] if isinstance(val, dict) else str(m)[:120]
        print(f"  [{i+1}/{len(new)}] {ts} | {key} | from={frm}\n      {preview}", flush=True)
        if not args.dry_run:
            put_bb(f"{ARCHIVE_PREFIX}/{batch_ts}/{i}", {
                "key": key, "ts": ts, "value": val,
                "replayed_at": now(), "from": frm,
            })
            processed += 1

    if not args.dry_run and processed > 0:
        # 更新水位到最后一条
        last = new[-1]
        seen["last_key"] = f"{last.get('ts')}|{last.get('key')}"
        seen["count"] = len(messages)
        save_seen(seen)
        print(f"[upgrade-replay] {now()} ✅ 归档 {processed} 条 → 黑板 {ARCHIVE_PREFIX}/{batch_ts}/ | 水位已更新")
        print(f"[upgrade-replay] 请中枢会话逐条处理：read 黑板 {ARCHIVE_PREFIX}/{batch_ts}/ 清单")
    elif args.dry_run:
        print(f"[upgrade-replay] (dry-run) 将归档 {len(new)} 条")

if __name__ == "__main__":
    main()
