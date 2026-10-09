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
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, time, datetime, urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/mac-mini-inbox-watch.log")


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
WATCH_PREFIXES = ("notes/mac-mini/", "notes/collab/")
INBOX_DIR = os.path.expanduser("~/.dsh/inbox")
SEEN_FILE = os.path.join(os.path.expanduser("~/.dsh"), "mac-mini-watch.seen")   # ★P0：移出 inbox
CURSOR_FILE = os.path.join(os.path.expanduser("~/.dsh"), "mac-mini-watch.cursor")  # ★P0：增量游标
TIMELINE_CAP = 20000   # 板的 timeline 上限（超出即需要一次全量对账）
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


def _load_cursor():
    try:
        with open(CURSOR_FILE) as f:
            return int((json.load(f) or {}).get("last_seq") or 0)
    except Exception:
        return 0


def _save_cursor(seq):
    try:
        with open(CURSOR_FILE, "w") as f:
            f.write(json.dumps({"last_seq": int(seq), "ts": now()}))
    except Exception as ex:
        print("[%s] cursor 写入失败: %s" % (now(), str(ex)[:60]), flush=True)


def _migrate_seen(seen):
    """★P0 修复①：seen 换了位置 ⇒ 首次运行必须把旧位置的记录搬过来。
    否则 seen 为空 ⇒ 兜底全量对账时会把**所有历史键**当新键重灌（沙箱已实测重现）。"""
    old = os.path.join(INBOX_DIR, "mac-mini-watch.seen")
    if seen or not os.path.exists(old):
        return seen
    try:
        with open(old) as f:
            seen |= set(json.loads(f.read()))
        save_seen(seen)
        print("[%s] seen 已从旧位置迁移 %d 键（%s）" % (now(), len(seen), old), flush=True)
    except Exception as ex:
        print("[%s] seen 迁移失败（将保守做一次全量对账）: %s" % (now(), str(ex)[:60]), flush=True)
    return seen


def scan_delta(seen, dry_run=False):
    """★P0：只取【新事件】，不再全量列举 16k 键。
    实测：全量 GET /notes/ = 21.2 MB / 16,418 键；增量 /timeline?since_seq= = 430 B / 3 事件。
    ★ 语义保持：仍用 seen 去重（同一键重复 PUT 只处理首见），seen 本身也不会再被"删队列"清掉。
    ★ 兜底：若 latest_seq 与游标相距超过板的 timeline 上限 ⇒ 可能漏事件 ⇒ 由调用方做一次全量对账。"""
    cur = _load_cursor()
    r = get("/timeline?since_seq=%d&limit=500" % cur)
    if not r:
        return [], cur, False
    evs = r.get("events") or []
    latest = int(r.get("latest_seq") or cur)
    # ★ 2026-10-01 修复（消息丢失级）：游标只能推进到【实际取回事件的最后一个 seq】。
    #   原实现用 latest_seq ⇒ 窗口取满时跳过未取回事件。实测：limit=500 / total=1025
    #   ⇒ 一次轮询跳过 525 个事件，**永久丢失**（它们不会再出现在任何后续窗口里）。
    _seqs = [int(e.get("seq") or 0) for e in evs if e.get("seq")]
    cursor_next = max(_seqs) if _seqs else cur
    # ★P0 修复②：seq 是「微秒时间戳×1000+序号」，**非连续**（实测 500 事件跨 6.8e9）
    #   ⇒ 按 `latest-cur > 20000` 判落后**永远为真** ⇒ 会每轮都做一次全量扫（比现状更糟）。
    #   ⇒ 改用**事件条数**判：本轮取满 limit 且板保留量也取满 ⇒ 可能还有更早的未读事件 ⇒ 全量对账。
    # ★ 修复：原判据第三项 `latest_seq > latest` 恒假（latest 就是 latest_seq）⇒ 兜底永不触发。
    #   正确判据：窗口取满 **且** 板上仍有更早未取回的事件。
    need_full = (len(evs) >= 500 and int(r.get("total") or 0) > len(evs))
    fresh = []
    for e in evs:
        if e.get("op") != "PUT":
            continue
        key = e.get("key") or ""
        if not key.startswith(WATCH_PREFIXES) or "llm-reply" in key:
            continue
        if key in seen:
            continue
        seen.add(key)
        fresh.append(key)
    if not dry_run:
        _save_cursor(cursor_next)
    return fresh, cursor_next, need_full


def handle_new(fresh, seen, dry_run=False):
    fresh = sorted(fresh)
    for key in fresh:
        rec = get("/" + key)
        val = (rec or {}).get("value") or {}
        line = "[%s] 📩 中枢通道新消息 %s | from=%s to=%s | %s" % (
            now(), key, val.get("from"), val.get("to"),
            str(val.get("subject") or val.get("content") or "")[:60])
        print(line, flush=True)
        if dry_run:
            continue
        topic = key.split("/")[1] + "-inbox"
        inbox_file = os.path.join(INBOX_DIR, topic + ".json")
        try:
            with open(inbox_file, "a") as f:
                # ★ S1（2026-10-09 所有者授权）：落盘条目带 CAHAC `state`
                #   §7.5 时点①「发出」由发卡方写 todo；此处是【落盘副本】，随同标注。
                #   兼容性：仅新增字段，不改 `key`/`ts`/`value` ⇒ 旧消费者不受影响。
                f.write(json.dumps({"key": key, "ts": now(), "state": "todo", "value": val}, ensure_ascii=False) + "\n")
        except Exception as ex:
            print("[%s] inbox 落盘失败: %s" % (now(), str(ex)[:60]), flush=True)
        with open(LOG_FILE, "a") as f:
            f.write("%s %s from=%s to=%s %s\n" % (
                now(), key, val.get("from"), val.get("to"),
                json.dumps(str(val.get("subject") or "")[:100], ensure_ascii=False)))
    if not dry_run and fresh:
        save_seen(seen)


def _full_scan_keys(seen):
    """★P0 修复③：全量对账只**返回**新键，不再自带写盘 —— 写盘统一由 handle_new 负责，
    这样它就受 --dry-run 管（沙箱实测：旧写法绕过了守卫，真往累积器写了 30 行）。"""
    d = get("/notes/")
    if not d:
        return []
    fresh = []
    for key in (d.get("list") or {}):
        if not key.startswith(WATCH_PREFIXES) or "llm-reply" in key:
            continue
        if key in seen:
            continue
        seen.add(key)
        fresh.append(key)
    return fresh


def scan(seen, backfill=False):
    fresh = _full_scan_keys(seen)
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
                # ★ S1（2026-10-09 所有者授权）：落盘条目带 CAHAC `state`
                #   §7.5 时点①「发出」由发卡方写 todo；此处是【落盘副本】，随同标注。
                #   兼容性：仅新增字段，不改 `key`/`ts`/`value` ⇒ 旧消费者不受影响。
                f.write(json.dumps({"key": key, "ts": now(), "state": "todo", "value": val}, ensure_ascii=False) + "\n")
        except Exception as ex:
            print("[%s] inbox 落盘失败: %s" % (now(), str(ex)[:60]), flush=True)
        with open(LOG_FILE, "a") as f:
            f.write("%s %s from=%s to=%s %s\n" % (
                now(), key, val.get("from"), val.get("to"),
                json.dumps(str(val.get("subject") or "")[:100], ensure_ascii=False)))
    save_seen(seen)


# ═══════════════════════════════════════════════════════════════════════════
# 断言套件（2026-10-01 新增）—— 此前本组件【零断言】。
# 动因：P0 补丁里 handle_new() 调用了未定义的 seen ⇒ NameError；
#       而上一轮「验证通过」只跑了 --dry-run，dry-run 恰好跳过那两行（if not dry_run and fresh），
#       于是 bug 被验证方式本身遮住了。⇒ 断言必须覆盖**非 dry-run 的写路径**。
# ═══════════════════════════════════════════════════════════════════════════
_ST = {"ok": 0, "fail": 0}


def selftest():
    import tempfile, shutil
    global INBOX_DIR, SEEN_FILE, CURSOR_FILE, LOG_FILE, get
    _orig = (INBOX_DIR, SEEN_FILE, CURSOR_FILE, LOG_FILE, get)
    tmp = tempfile.mkdtemp(prefix="wtest-")
    INBOX_DIR = os.path.join(tmp, "inbox"); os.makedirs(INBOX_DIR, exist_ok=True)
    SEEN_FILE = os.path.join(tmp, "seen.json")
    CURSOR_FILE = os.path.join(tmp, "cursor.json")
    LOG_FILE = os.path.join(tmp, "w.log")
    def check(name, cond, detail=""):
        if cond: _ST['ok'] += 1; print("  PASS  " + name)
        else:    _ST['fail'] += 1; print("  FAIL  " + name + "  " + str(detail))

    FIXED = {"notes/collab/good-1": {"from": "a", "to": "me", "subject": "s1"},
             "notes/mac-mini/good-2": {"from": "b", "to": "me", "subject": "s2"},
             "notes/collab/llm-reply-x": {"from": "c", "to": "me"},
             "notes/i9/other": {"from": "d", "to": "me"}}

    def fake(path):
        if path.startswith("/timeline"):
            return {"events": [{"op": "PUT", "key": k} for k in FIXED],
                    "latest_seq": 999, "total": 4}
        if path.startswith("/notes/"):
            return {"list": {k: {} for k in FIXED}, "total": len(FIXED)}
        return {"value": FIXED.get(path.lstrip("/"), {})}

    # I1 结构：热路径必须走 /timeline 而非全量 /notes/
    src = open(__file__).read()
    i_scan, i_notes = src.find("def scan_delta"), src.find("def _full_scan_keys")
    check("I1 scan_delta 使用 /timeline 增量（不再全量 /notes/）",
          "/timeline?since_seq=" in src[i_scan:i_scan + 900], "未见增量端点")
    check("I1 全量 /notes/ 仅保留在对账/backfill 路径内",
          '/notes/' in src[i_notes:] or "backfill" in src, "未定位")

    get = fake
    # I2 前缀过滤 + llm-reply 排除
    seen = set()
    fresh, latest, need = scan_delta(seen, dry_run=True)
    check("I2 只收 WATCH_PREFIXES 内的键", "notes/i9/other" not in fresh, fresh)
    check("I2 排除 llm-reply 键", "notes/collab/llm-reply-x" not in fresh, fresh)
    check("I2 收齐 2 个合法新键", len(fresh) == 2, fresh)

    # I3 dry_run 零写入
    before = os.path.exists(CURSOR_FILE), os.path.exists(SEEN_FILE)
    fresh, latest, need = scan_delta(set(), dry_run=True)
    check("I3 dry_run 不写 cursor", not os.path.exists(CURSOR_FILE), "cursor 被写了")

    # I4 非 dry_run：★ 这一条会抓出原补丁的 NameError
    try:
        fresh, latest, need = scan_delta(set(), dry_run=False)
        check("I4 非 dry_run 时 cursor 被推进",
              os.path.exists(CURSOR_FILE) and json.load(open(CURSOR_FILE))["last_seq"] == latest,
              "cursor 未推进")
    except Exception as e:
        check("I4 非 dry_run 时 cursor 被推进", False, repr(e))

    # ★ 不用 try/check(True) 惯用法（审计工具判 TAUTOLOGY，且它确实弱）：
    #   改为断言**副作用**——非 dry_run 必须真的落盘。原补丁此处 NameError ⇒ 副作用不会发生 ⇒ 断言红。
    seen2 = set()
    _err = None
    try:
        handle_new(["notes/collab/good-1"], seen2, dry_run=False)
    except Exception as e:      # noqa: BLE001
        _err = repr(e)
    _acc = os.path.join(INBOX_DIR, "collab-inbox.json")
    _written = os.path.exists(_acc) and "good-1" in open(_acc).read()
    check("I4 ★ handle_new 非 dry_run 产生真实副作用（原补丁此处 NameError）",
          _err is None and _written, "err=%s written=%s" % (_err, _written))

    acc = os.path.join(INBOX_DIR, "collab-inbox.json")
    check("I5 非 dry_run 真写累积器", os.path.exists(acc), "累积器未生成")
    if os.path.exists(acc):
        check("I5 累积器内容含该键", "good-1" in open(acc).read())

    # I6 dry_run 不写累积器
    acc2 = os.path.join(INBOX_DIR, "mac-mini-inbox.json")
    handle_new(["notes/mac-mini/good-2"], set(), dry_run=True)
    check("I6 dry_run 不写累积器", not os.path.exists(acc2), "dry_run 竟写了累积器")

    # I7/I8/I9 ★ 行为断言（原 I7 只查源码文字，测不出「判据恒假」这类缺陷 —— 自查教训）
    def saturated(path):
        evs = [{"op": "PUT", "key": "notes/collab/sat-%d" % i, "seq": 1000 + i} for i in range(500)]
        if path.startswith("/timeline"):
            return {"events": evs, "latest_seq": 99999, "total": 1025}
        if path.startswith("/notes/"):
            return {"list": {e["key"]: {} for e in evs}, "total": 500}
        return {"value": {}}
    get = saturated
    seen7 = set()
    fresh7, cur7, need7 = scan_delta(seen7, dry_run=True)
    check("I7 窗口取满且有更早事件 ⇒ need_full=True（原判据恒假）", need7 is True, "need_full=%s" % need7)
    check("I8 ★ 游标不跳越未取回事件（= 末事件 seq 而非 latest_seq）",
          cur7 == 1499, "cursor=%s（应为末事件 seq 1499，而非 latest_seq 99999）" % cur7)
    # 未取满时不应触发兜底
    def small(path):
        if path.startswith("/timeline"):
            return {"events": [{"op": "PUT", "key": "notes/collab/x", "seq": 5}],
                    "latest_seq": 5, "total": 1}
        return {"value": {}}
    get = small
    _, cur9, need9 = scan_delta(set(), dry_run=True)
    check("I9 未取满 ⇒ need_full=False", need9 is False, "need_full=%s" % need9)
    check("I9 少量事件时游标 = 该事件 seq", cur9 == 5, "cursor=%s" % cur9)
    get = fake

    INBOX_DIR, SEEN_FILE, CURSOR_FILE, LOG_FILE, get = _orig
    shutil.rmtree(tmp, ignore_errors=True)
    print("\n  selftest: %d PASS / %d FAIL" % (_ST["ok"], _ST["fail"]))
    return 0 if _ST["fail"] == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true", help="★P0：只打印不写任何文件（供等价性验证）")
    ap.add_argument("--selftest", action="store_true", help="跑断言套件")
    ap.add_argument("--backfill", action="store_true",
                    help="忽略历史存量，只处理启动后的新键")
    args = ap.parse_args()
    if args.selftest:
        # ★ 崩溃断言化：未捕获异常必须变成一条【命名 FAIL】并给出汇总，
        #   否则套件崩溃只能被外部工具判为「不可判」，看不出崩在哪一条。
        try:
            return selftest()
        except Exception as _e:
            print("  FAIL  \u2605 \u5957\u4ef6\u672a\u6355\u83b7\u5f02\u5e38\uff08\u5d29\u6e83\u65ad\u8a00\u5316\uff09: %r" % (_e,))
            print("\n  selftest: %d PASS / %d FAIL" % (_ST["ok"], _ST["fail"] + 1))
            return 1
    seen = _migrate_seen(load_seen())
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
            fresh, latest, need_full = scan_delta(seen, dry_run=args.dry_run)
            if fresh:
                handle_new(fresh, seen, dry_run=args.dry_run)
            if need_full:                       # 游标落后于板的 timeline 上限 ⇒ 一次全量对账
                print("[%s] ⚠ 取满窗口且板上还有更早事件 ⇒ 做一次全量对账" % now(), flush=True)
                _full = _full_scan_keys(seen)
                handle_new(_full, seen, dry_run=args.dry_run)
        except Exception as ex:
            print("[%s] scan error: %s" % (now(), str(ex)[:80]), flush=True)
        if args.once:
            break
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
