#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""blackboard-server v0.3 (coordinator) — 黑板进化版（:8792 兼容升级）

v0.2 → v0.3 变更（2026-08-23 · 协调者，用户指示：时间轴管理 + 唯一时间戳对齐基线）：
  1. 【唯一时间戳】全局单调 seq（HLC 风格）：
     - 每次 PUT/DELETE 分配全局唯一递增 seq（黑板服务器时间为物理时钟基准）
     - seq = 秒级物理时间戳 * 10^6 + 同秒逻辑计数 → 跨设备全局唯一可排序
     - 持久化：seq 随 audit.jsonl 落盘，重启从 audit 恢复最大值（不丢序）
     - PUT 响应新增 seq 字段；订阅通知 payload 新增 seq
  2. 【时间轴】增量基线查询：
     - GET /timeline?since_seq=N&limit=M → N 之后的事件按 seq 全局序返回
     - 设备记住 latest_seq → 重启后 since_seq 增量补漏 → 对齐基线
  3. 【对时】GET /clock → 当前全局 seq + 黑板服务器权威时间
  4. 【兼容】v0.1/v0.2 API 全不变；旧 audit 记录加载时按序补 seq（不回写）

用法：BLACKBOARD_TOKEN=xxx python3 blackboard-server-v0.3.py --port 8792
"""
import argparse, json, os, re, threading, urllib.request, datetime
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DATA_DIR = os.path.expanduser("~/dsh-collab/token-monitor/blackboard")
TOKEN = os.environ.get("BLACKBOARD_TOKEN", "")
NS_RE = re.compile(r"^([a-z]+)/([\w\-./]+)$")
QUEUE_RE = re.compile(r"^tasks/([\w\-]+)/result$")       # tasks/<node>/result → 镜像
MIRROR_NS = "results"                                     # tasks/<node>/results/<seq>

# 内存状态
state = {}          # key -> {version, value, ts}
subs = {}           # (topic, callback) -> {topic, callback, ts}  去重
_notify_pool = ThreadPoolExecutor(max_workers=8)

# ── v0.3 全局时钟（唯一时间戳）──
_clock_lock = threading.Lock()
_last_seq = 0            # 已分配的最大全局 seq（持久化恢复）
_last_phys = 0           # 上次分配时的物理时间（秒）
_timeline = []           # [{seq, op, key, ts, version}] 内存时间轴（重启重建）
TIMELINE_MAX = 20000     # 时间轴内存上限（audit.jsonl 是完整持久层）

def _now_ts():
    return datetime.datetime.now().isoformat(timespec="seconds")

def _next_seq():
    """分配全局唯一单调 seq（HLC 风格：物理时间 + 同秒逻辑计数）"""
    global _last_seq, _last_phys
    with _clock_lock:
        phys = int(datetime.datetime.now().timestamp())
        if phys == _last_phys:
            _last_seq += 1                     # 同秒：逻辑计数递增
        elif phys > _last_phys:
            _last_seq = phys * 10**6 + 1       # 新秒：物理时间进位
            _last_phys = phys
        else:
            _last_seq += 1                     # 时钟回拨兜底：继续递增
        return _last_seq

def _timeline_append(seq, op, key, version):
    _timeline.append({"seq": seq, "op": op, "key": key, "ts": _now_ts(), "version": version})
    if len(_timeline) > TIMELINE_MAX:
        del _timeline[: len(_timeline) - TIMELINE_MAX]

def _load():
    global _last_seq, _last_phys
    os.makedirs(DATA_DIR, exist_ok=True)
    max_seq = 0
    for f in sorted(os.listdir(DATA_DIR)):
        if f.endswith(".jsonl"):
            for line in open(os.path.join(DATA_DIR, f), encoding="utf-8", errors="ignore"):
                line = line.strip()
                if line:
                    try:
                        e = json.loads(line)
                        if e["op"] == "PUT":
                            state[e["key"]] = {"version": e["version"], "value": e["value"], "ts": e["ts"]}
                        seq = e.get("seq", 0)
                        if seq > 0:
                            # v0.3：重建时间轴（仅带 seq 的记录；旧记录无 seq 跳过，仍可单 key/LIST 访问）
                            _timeline_append(seq, e["op"], e["key"], e.get("version", 0))
                            if seq > max_seq:
                                max_seq = seq
                    except Exception:
                        pass
    if max_seq > 0:
        _last_seq = max_seq
        _last_phys = max_seq // 10**6
        print("clock restored: last_seq=%d timeline=%d" % (max_seq, len(_timeline)))

def _audit(op, key, value, seq):
    os.makedirs(DATA_DIR, exist_ok=True)
    entry = {"op": op, "key": key, "version": state.get(key, {}).get("version", 1), "value": value,
             "ts": _now_ts(), "seq": seq}
    with open(os.path.join(DATA_DIR, "audit.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry

def _notify_one(s, key, seq):
    """单个订阅者回调（在后台线程执行，失败静默）"""
    try:
        data = json.dumps({"key": key, "value": state.get(key, {}).get("value"),
                           "version": state.get(key, {}).get("version"), "seq": seq}).encode()
        req = urllib.request.Request(s["callback"], data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

def _notify(key, seq):
    """异步通知：全部订阅者回调进线程池，不阻塞 PUT 返回（v0.2 变更 3）"""
    for s in list(subs.values()):
        if key.startswith(s["topic"]):
            _notify_pool.submit(_notify_one, s, key, seq)

def _mirror_result(key, seq):
    """v0.2 变更 1：tasks/<node>/result 自动镜像到 tasks/<node>/results/<seq>"""
    m = QUEUE_RE.match(key)
    if not m:
        return
    node = m.group(1)
    val = state.get(key, {}).get("value")
    if not isinstance(val, dict):
        return
    seq_s = str(seq)[-10:]
    mirror_key = "tasks/%s/%s/%s" % (node, MIRROR_NS, seq_s)
    cur = state.get(mirror_key, {})
    state[mirror_key] = {"version": cur.get("version", 0) + 1,
                         "value": val, "ts": _now_ts()}
    _audit("PUT", mirror_key, val, seq)
    # 镜像不触发 notify（避免重复通知原订阅者）

class H(BaseHTTPRequestHandler):
    def _ok(self, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def _err(self, code, msg):
        body = json.dumps({"error": msg}, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def _auth(self):
        if TOKEN and self.headers.get("X-Blackboard-Token") != TOKEN:
            self._err(401, "unauthorized")
            return False
        return True
    def do_GET(self):
        if not self._auth(): return
        path = self.path.lstrip("/")
        # 分页参数（v0.2 变更 4）
        limit, offset = None, 0
        since_seq = None
        op_filter = None
        if "?" in path:
            path, qs = path.split("?", 1)
            for kv in qs.split("&"):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    if k == "limit" and v.isdigit(): limit = int(v)
                    elif k == "offset" and v.isdigit(): offset = int(v)
                    elif k == "since_seq" and v.isdigit(): since_seq = int(v)
                    elif k == "op": op_filter = v
        # v0.3：GET /clock — 对时（全局 seq + 黑板权威时间）
        if path == "clock":
            self._ok({"seq": _last_seq, "ts": _now_ts(),
                      "server": "blackboard", "host": os.uname().nodename if hasattr(os, "uname") else "?"})
            return
        # v0.3：GET /timeline — 增量时间轴（since_seq 后的事件，按 seq 全局序）
        if path == "timeline":
            events = [e for e in _timeline
                      if (since_seq is None or e["seq"] > since_seq)
                      and (op_filter is None or e["op"] == op_filter)]
            total = len(events)
            if limit is not None:
                events = events[offset:offset + limit]
            self._ok({"events": events, "latest_seq": _last_seq,
                      "since_seq": since_seq, "op": op_filter,
                      "total": total, "limit": limit, "offset": offset})
            return
        # GET /subs — 订阅者列表（v0.2 变更 2）
        if path == "subs":
            self._ok({"subscribed": len(subs),
                      "subs": [{"topic": s["topic"], "callback": s["callback"], "ts": s["ts"]}
                               for s in subs.values()]})
            return
        if path.startswith("audit"):
            self._ok({"audit": True}); return
        if "/" not in path or path.endswith("/"):
            ns = path.rstrip("/").split("/")[0]
            prefix = ns + "/"
            items = {k: v for k, v in state.items() if k.startswith(prefix)}
            total = len(items)
            if limit is not None:  # 显式分页
                keys = sorted(items.keys())
                page = keys[offset:offset + limit]
                items = {k: items[k] for k in page}
            self._ok({"list": items, "total": total,
                      "limit": limit, "offset": offset})
            return
        m = NS_RE.match(path)
        if not m:
            self._err(400, "bad key"); return
        ns, key = m.group(1), m.group(2)
        if ns + "/" + key in state:
            self._ok({"key": ns + "/" + key, **state[ns + "/" + key]})
        else:
            self._err(404, "not found")
    def do_PUT(self):
        if not self._auth(): return
        try:
            n = int(self.headers.get("Content-Length", 0))
            value = json.loads(self.rfile.read(n).decode("utf-8", "ignore")) if n else {}
        except Exception:
            value = {}
        m = NS_RE.match(self.path.lstrip("/"))
        if not m:
            self._err(400, "bad key"); return
        ns, key = m.group(1), m.group(2)
        full = ns + "/" + key
        cur = state.get(full, {})
        ver = cur.get("version", 0) + 1
        seq = _next_seq()                              # v0.3：分配全局唯一 seq
        state[full] = {"version": ver, "value": value, "ts": _now_ts()}
        _audit("PUT", full, value, seq)
        _timeline_append(seq, "PUT", full, ver)        # v0.3：记时间轴
        _mirror_result(full, seq)                      # v0.2 变更 1
        _notify(full, seq)                             # v0.2 变更 3（异步，带 seq）
        self._ok({"key": full, "version": ver, "seq": seq})   # v0.3：响应带 seq
    def do_DELETE(self):
        if not self._auth(): return
        m = NS_RE.match(self.path.lstrip("/"))
        if m:
            full = m.group(1) + "/" + m.group(2)
            if full in state:
                seq = _next_seq()                      # v0.3：DELETE 也占全局序
                del state[full]
                _audit("DELETE", full, None, seq)
                _timeline_append(seq, "DELETE", full, 0)
                _notify(full, seq)
        self._ok({"deleted": True})
    def do_POST(self):
        if not self._auth(): return
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n).decode("utf-8", "ignore")) if n else {}
        except Exception:
            body = {}
        if self.path.rstrip("/").endswith("subscribe"):
            topic = body.get("topic", "")
            callback = body.get("callback", "")
            unsub = body.get("unsub", False)
            if unsub:  # v0.2 变更 2：退订
                removed = [k for k, s in subs.items() if s["topic"] == topic and s["callback"] == callback]
                for k in removed:
                    del subs[k]
                self._ok({"unsubscribed": len(removed), "subscribed": len(subs)})
                return
            key = (topic, callback)
            if key not in subs:  # v0.2 变更 2：去重
                subs[key] = {"topic": topic, "callback": callback,
                             "ts": datetime.datetime.now().isoformat(timespec="seconds")}
            self._ok({"subscribed": len(subs)})
        else:
            self._err(400, "use /subscribe")
    def log_message(self, *a):
        pass

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8792)
    ap.add_argument("--data-dir", default=None, help="数据目录（默认 ~/dsh-collab/token-monitor/blackboard，测试用独立目录隔离）")
    args = ap.parse_args()
    if args.data_dir:
        DATA_DIR = args.data_dir
    _load()
    srv = ThreadingHTTPServer(("0.0.0.0", args.port), H)
    print("blackboard-server v0.3 on :%d (token=%s) data=%s subs=%d clock_seq=%d timeline=%d"
          % (args.port, "on" if TOKEN else "off", DATA_DIR, len(subs), _last_seq, len(_timeline)))
    srv.serve_forever()
