#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mac-mini-inbox-watch.py — 中枢(mac-mini)通道消费常驻监听
监听黑板 notes/mac-mini/*（其他节点发给中枢的通道）与 notes/collab/*（协作通道），
新键出现即打印 + 写日志 + 落盘 inbox（中枢会话可感知，解决"MBP 发了消息中枢不知道"）。

用法:
  python3 mac-mini-inbox-watch.py              # 常驻监听（默认 5s 轮询）
  python3 mac-mini-inbox-watch.py --once       # 单次检查
  python3 mac-mini-inbox-watch.py --backfill   # 只看本次之后的新键（忽略历史存量）

状态: ~/.dsh/inbox/mac-mini-watch.seen 记录已处理键
"""
import argparse, json, os, time, datetime, urllib.request

BB = "http://127.0.0.1:8792"
WATCH_PREFIXES = ("notes/mac-mini/", "notes/collab/")
INBOX_DIR = os.path.expanduser("~/.dsh/inbox")
SEEN_FILE = os.path.join(INBOX_DIR, "mac-mini-watch.seen")
LOG_FILE = "/tmp/mac-mini-inbox-watch.log"

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.loads(f.read()))
    return set()

def save_seen(seen):
    os.makedirs(INBOX_DIR, exist_ok=True)
    with open(SEEN_FILE, "w") as f:
        f.write(json.dumps(sorted(seen)))

def get(path):
    try:
        req = urllib.request.Request(BB + path)
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode())
    except Exception as ex:
        print("[%s] GET %s error: %s" % (now(), path, str(ex)[:80]), flush=True)
        return None

def scan(seen, backfill=False):
    d = get("/notes/")
    if not d:
        return
    lst = d.get("list", d)
    fresh = []
    for key in lst:
        if not key.startswith(WATCH_PREFIXES):
            continue
        # 跳过历史事故残留（llm-reply 循环产物）与纯测试键
        if "llm-reply" in key:
            continue
        if key not in seen:
            fresh.append(key)
            seen.add(key)
    if not fresh:
        return
    fresh.sort()
    for key in fresh:
        rec = get("/" + key)
        val = (rec or {}).get("value") or {}
        line = "[%s] 📩 中枢通道新消息 %s | from=%s to=%s | %s" % (
            now(), key, val.get("from"), val.get("to"),
            str(val.get("subject") or val.get("content") or "")[:60])
        print(line, flush=True)
        # 落盘 inbox：topic = 去前缀后的第一个段
        topic = key.split("/")[1] + "-inbox"
        inbox_file = os.path.join(INBOX_DIR, topic + ".json")
        try:
            with open(inbox_file, "a") as f:
                f.write(json.dumps({"key": key, "ts": now(), "value": val}, ensure_ascii=False) + "\n")
        except Exception as ex:
            print("[%s] inbox 落盘失败: %s" % (now(), str(ex)[:60]), flush=True)
        with open(LOG_FILE, "a") as f:
            f.write("%s %s from=%s to=%s %s\n" % (
                now(), key, val.get("from"), val.get("to"),
                json.dumps(str(val.get("subject") or "")[:100], ensure_ascii=False)))
    save_seen(seen)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=5)
    ap.add_argument("--backfill", action="store_true",
                    help="忽略历史存量，只处理启动后的新键")
    args = ap.parse_args()
    seen = load_seen()
    if args.backfill:
        # 预填当前所有已存在键，只处理之后新出现的
        d = get("/notes/")
        if d:
            lst = d.get("list", d)
            for key in lst:
                if key.startswith(WATCH_PREFIXES) and "llm-reply" not in key:
                    seen.add(key)
        save_seen(seen)
        print("[%s] backfill 完成，已预填 %d 键，之后只处理新消息" % (now(), len(seen)), flush=True)
        return
    print("[%s] mac-mini-inbox-watch 启动（监听 %s，%ss 轮询）" % (
        now(), ",".join(WATCH_PREFIXES), args.interval), flush=True)
    while True:
        try:
            scan(seen)
        except Exception as ex:
            print("[%s] scan error: %s" % (now(), str(ex)[:80]), flush=True)
        if args.once:
            break
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
