#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-handshake.py — 黑板消息握手协议（可靠性：不漏发、漏了能补）

用户指示（2026-08-23）：黑板中间应加握手逻辑链条——每条信息单独生成密钥，
确保没有漏发、漏了还能补上。

设计（衔接 v0.3 全局 seq + v0.6 recipient 定向）：
  1. 消息唯一 ID：msg_id = "<sender>-<seq>"（seq 为黑板全局唯一序）
  2. 消息密钥：msg_key = sha256(msg_id + recipient)[:16]（每条独立，可校验）
  3. 发送：PUT notes/<recipient>/handshake/<msg_id> {msg_key, sender, seq, payload}
  4. ACK：接收方处理完 PUT data/handshake/acks/<msg_id> {status, msg_key, ts}
  5. 水位：接收方记 data/handshake/watermark/<recipient> {last_seq}
  6. 补漏：--check 比对 水位 vs 黑板时间轴 since_seq → 找缺口消息

用法：
  发送: python3 bb-handshake.py --send --to <recipient> --msg '<内容>'
  确认: python3 bb-handshake.py --ack --msg-id <msg_id> --by <recipient>
  查水位: python3 bb-handshake.py --watermark --for <recipient>
  补漏检查: python3 bb-handshake.py --check --for <recipient>
"""
import argparse, json, hashlib, sys, datetime, urllib.request

BB = "http://127.0.0.1:8792"
SENDER = "coordinator"

def fetch(path):
    try:
        with urllib.request.urlopen(BB + path, timeout=6) as r:
            return json.loads(r.read().decode())
    except Exception:
        return {}

def put(path, obj):
    body = json.dumps(obj, ensure_ascii=False).encode()
    req = urllib.request.Request(BB + path, data=body, method="PUT",
                                 headers={"Content-Type": "application/json", "Content-Length": str(len(body))})
    with urllib.request.urlopen(req, timeout=6) as r:
        return json.loads(r.read().decode())

def msg_key(msg_id, recipient):
    """每条消息独立密钥（哈希，可校验）"""
    return hashlib.sha256(("%s|%s" % (msg_id, recipient)).encode()).hexdigest()[:16]

def send(to, msg):
    """发送握手消息（拿全局 seq 做 msg_id）"""
    clock = fetch("/clock")
    seq = clock.get("seq", 0)
    msg_id = "%s-%s" % (SENDER, seq)
    key = msg_key(msg_id, to)
    entry = {"msg_id": msg_id, "msg_key": key, "sender": SENDER,
             "recipient": to, "seq": seq, "payload": msg,
             "ts": datetime.datetime.now().isoformat(timespec="seconds")}
    r = put("/notes/%s/handshake/%s" % (to, msg_id), entry)
    print("✅ 已发送 %s → %s | msg_id=%s | key=%s | seq=%s" % (SENDER, to, msg_id, key, seq))
    return entry

def ack(msg_id, by):
    """接收方确认处理"""
    r = put("/data/handshake/acks/%s" % msg_id,
            {"msg_id": msg_id, "status": "processed", "by": by,
             "ts": datetime.datetime.now().isoformat(timespec="seconds")})
    print("✅ 已确认 %s (by %s)" % (msg_id, by))
    return r

def watermark(recipient):
    """记录/读取水位（接收方已处理到的 seq）"""
    d = fetch("/data/handshake/watermark/%s" % recipient)
    return d.get("value", {}).get("last_seq", 0)

def set_watermark(recipient, last_seq):
    put("/data/handshake/watermark/%s" % recipient, {"last_seq": last_seq, "by": recipient,
        "ts": datetime.datetime.now().isoformat(timespec="seconds")})

def check(recipient, prefix=None):
    """补漏检查（泛化）：水位 vs 黑板时间轴 → 找消费方域内漏处理的写入
    prefix: 关注的命名空间前缀（如 data/i9/、notes/i9/、tasks/i9/）——缺省=定向握手消息
    """
    wm = watermark(recipient)
    tl = fetch("/timeline?since_seq=%s&limit=200" % wm)
    latest = tl.get("latest_seq", wm)
    events = tl.get("events", [])
    if prefix:
        # 泛化：检查该前缀下所有 PUT（消费方域的写入）
        relevant = [e for e in events if e.get("op") == "PUT"
                    and e.get("key", "").startswith(prefix)]
    else:
        # 缺省：定向握手消息
        relevant = [e for e in events if e.get("op") == "PUT"
                    and e.get("key", "").startswith("notes/%s/handshake/" % recipient)]
    # 查这些写入是否已确认（data/handshake/acks/<seq> 通用确认）
    unacked = []
    for e in relevant:
        key = e.get("key", "")
        msg_id = key.rsplit("/", 1)[-1]
        a = fetch("/data/handshake/acks/%s" % msg_id)
        if "msg_id" not in a:
            unacked.append({"msg_id": msg_id, "seq": e.get("seq"), "key": key})
        # 也支持按 seq 通用确认（data/handshake/acks/<seq>）
        a2 = fetch("/data/handshake/acks/seq-%s" % e.get("seq"))
        if "msg_id" not in a and "msg_id" not in a2:
            unacked.append({"msg_id": msg_id, "seq": e.get("seq"), "key": key})
    # 去重
    seen, dedup = set(), []
    for u in unacked:
        if u["key"] not in seen:
            seen.add(u["key"]); dedup.append(u)
    print("== 补漏检查 for %s%s ==" % (recipient, (" [%s]" % prefix) if prefix else ""))
    print("  水位 last_seq: %s | 黑板 latest: %s" % (wm, latest))
    print("  相关写入: %d 条 | 未确认: %d 条" % (len(relevant), len(dedup)))
    unacked = dedup
    if unacked:
        print("  ⚠️ 未确认消息（需补处理/重发）:")
        for u in unacked[:10]:
            print("    - %s (seq=%s)" % (u["msg_id"], u["seq"]))
    else:
        print("  ✅ 无缺口，全部已确认")
    return unacked

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true")
    ap.add_argument("--ack", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--watermark", action="store_true")
    ap.add_argument("--to", default="")
    ap.add_argument("--msg", default="")
    ap.add_argument("--msg-id", default="")
    ap.add_argument("--by", default="")
    ap.add_argument("--for", dest="recipient", default="")
    ap.add_argument("--prefix", default="", help="补漏检查的命名空间前缀（泛化：任意消费方域）")
    args = ap.parse_args()

    if args.send:
        if not args.to or not args.msg:
            print("--send 需 --to 和 --msg"); sys.exit(1)
        send(args.to, args.msg)
    elif args.ack:
        if not args.msg_id or not args.by:
            print("--ack 需 --msg-id 和 --by"); sys.exit(1)
        ack(args.msg_id, args.by)
    elif args.check:
        if not args.recipient:
            print("--check 需 --for <recipient>"); sys.exit(1)
        check(args.recipient, prefix=args.prefix or None)
    elif args.watermark:
        if not args.recipient:
            print("--watermark 需 --for <recipient>"); sys.exit(1)
        wm = watermark(args.recipient)
        print("水位(last_seq) for %s: %s" % (args.recipient, wm))
    else:
        print(ap.format_help())

if __name__ == "__main__":
    main()
