#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""blackboard-server v0.6 (coordinator) — 黑板进化版（:8792 兼容升级）

v0.5 → v0.6 变更（2026-08-23 · 协调者，用户指示：门店规模化前补齐归属机制）：
  1. 【写者签名】PUT/DELETE 支持 X-Writer 头，audit 记录 writer（无签名记 anonymous）
  2. 【收件定向】任务卡支持 recipient 字段 + GET /tasks?node=<id> 过滤（取卡校验）
  3. 【门店身份】PUT /nodes/<id> 支持 store 类型（store_id/code/location/type）+ GET /stores 列出
  4. 【兼容】v0.1-v0.5 API 全不变（无新字段的旧客户端照常工作）

用法：BLACKBOARD_TOKEN=xxx python3 blackboard-server-v0.6.py --port 8792
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）


import argparse, json, os, re, threading, urllib.request, datetime, gzip, shutil
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DATA_DIR = os.path.expanduser("~/dsh-collab/token-monitor/blackboard")
TOKEN = os.environ.get("BLACKBOARD_TOKEN", "")
NS_RE = re.compile(r"^([a-z]+)/([\w\-./]+)$")
QUEUE_RE = re.compile(r"^tasks/([\w\-]+)/result$")       # tasks/<node>/result → 镜像
MIRROR_NS = "results"                                     # tasks/<node>/results/<seq>

# v0.5：职责命名空间注册表（推广确认汇总，GET /ns-registry 返回）
ROLE_NS = {
    "6ed4daf2": ("恢复自查", "data/recovery/"),
    "a3bc8cba": ("学习", "data/learning/"),
    "aa528267": ("运营", "data/ops/"),
    "45f89009": ("运营", "data/ops/"),
    "4787d717": ("数据调查", "data/investigate/"),
    "0e84e65c": ("供应链", "data/supply-chain/"),
    "ffb7c3ab": ("QA", "data/qa/"),
    "54e809ed": ("媒体", "data/media/"),
    "55d4d1bd": ("摄取", "data/ingest/"),
    "2a15e6b1": ("HR", "data/registry/"),
    "b193c782": ("客服", "data/customer-service/"),
    "coordinator": ("协调者", "data/iterations/"),
}

# v0.4 配置：轮转阈值 / 归档保留数
AUDIT_ROTATE_BYTES = 5 * 1024 * 1024    # audit.jsonl 超过 5MB 触发轮转
SNAPSHOT_FILE = "snapshot.json"
SUBS_FILE = "subs.json"
ARCHIVE_KEEP = 10                       # 保留最近 10 个归档（旧的 gzip + 清理）

# 内存状态
state = {}          # key -> {version, value, ts}
subs = {}           # (topic, callback) -> {topic, callback, ts}  去重
_notify_pool = ThreadPoolExecutor(max_workers=8)
_io_lock = threading.Lock()             # audit/快照/归档 的写锁（防并发轮转撕裂）

# ── v0.3 全局时钟（唯一时间戳）──
_clock_lock = threading.Lock()
_last_seq = 0            # 已分配的最大全局 seq（持久化恢复）
_last_seq_snapshot = 0   # 持久化恢复基准（防呆用，HR P1-①）
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
        # 防呆（HR P1-① 裁决）：seq 必须严格单调递增，杜绝物理进位回退/复用
        if _last_seq <= _last_seq_snapshot:
            _last_seq = _last_seq_snapshot + 1
        return _last_seq

def _timeline_append(seq, op, key, version):
    _timeline.append({"seq": seq, "op": op, "key": key, "ts": _now_ts(), "version": version})
    if len(_timeline) > TIMELINE_MAX:
        del _timeline[: len(_timeline) - TIMELINE_MAX]

# ── v0.4 订阅持久化 ──
def _save_subs():
    """原子写 subs.json（临时文件 + rename）"""
    try:
        tmp = os.path.join(DATA_DIR, SUBS_FILE + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"subs": [{"topic": s["topic"], "callback": s["callback"], "ts": s["ts"]}
                                for s in subs.values()]}, f, ensure_ascii=False)
        os.replace(tmp, os.path.join(DATA_DIR, SUBS_FILE))
    except Exception:
        pass

def _load_subs():
    """重启恢复订阅（v0.4）"""
    try:
        p = os.path.join(DATA_DIR, SUBS_FILE)
        if os.path.exists(p):
            d = json.load(open(p, encoding="utf-8"))
            for s in d.get("subs", []):
                subs[(s["topic"], s["callback"])] = {"topic": s["topic"],
                                                     "callback": s["callback"],
                                                     "ts": s.get("ts", _now_ts())}
    except Exception:
        pass

# ── v0.4 audit 轮转（快照 + 归档）──
def _write_snapshot():
    """写 state 快照（当前全量 state + last_seq + timeline 尾部）"""
    snap = {"state": state, "last_seq": _last_seq,
            "timeline": _timeline[-TIMELINE_MAX:],
            "ts": _now_ts(), "v": "0.4-snapshot"}
    tmp = os.path.join(DATA_DIR, SNAPSHOT_FILE + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False)
    os.replace(tmp, os.path.join(DATA_DIR, SNAPSHOT_FILE))

def _rotate_audit():
    """audit 超阈值 → 快照 + 归档 + 新 audit（加锁防撕裂）"""
    with _io_lock:
        ap = os.path.join(DATA_DIR, "audit.jsonl")
        try:
            if os.path.exists(ap) and os.path.getsize(ap) > AUDIT_ROTATE_BYTES:
                _write_snapshot()
                ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                arch = os.path.join(DATA_DIR, "audit-%s.jsonl" % ts)
                shutil.move(ap, arch)
                # 归档压缩 + 清理超龄
                try:
                    with open(arch, "rb") as fi, gzip.open(arch + ".gz", "wb") as fo:
                        shutil.copyfileobj(fi, fo)
                    os.remove(arch)
                    arch = arch + ".gz"
                except Exception:
                    pass
                audits = sorted([f for f in os.listdir(DATA_DIR)
                                 if f.startswith("audit-") and f.endswith(".jsonl.gz")])
                for old in audits[:-ARCHIVE_KEEP]:
                    try:
                        os.remove(os.path.join(DATA_DIR, old))
                    except Exception:
                        pass
                print("audit rotated -> %s (state snapshot saved)" % os.path.basename(arch))
        except Exception as ex:
            print("rotate failed: %s" % str(ex)[:100])

def _load():
    global _last_seq, _last_phys
    os.makedirs(DATA_DIR, exist_ok=True)
    max_seq = 0
    # v0.4：优先从快照恢复（启动快，不重放历史全量）
    sp = os.path.join(DATA_DIR, SNAPSHOT_FILE)
    if os.path.exists(sp):
        try:
            snap = json.load(open(sp, encoding="utf-8"))
            for k, v in snap.get("state", {}).items():
                state[k] = v
            max_seq = snap.get("last_seq", 0)
            # v0.4：快照恢复 timeline（轮转后 audit 已归档，timeline 从快照还原）
            _timeline[:] = snap.get("timeline", [])
            print("snapshot restored: keys=%d last_seq=%d timeline=%d" % (len(state), max_seq, len(_timeline)))
        except Exception as ex:
            print("snapshot load failed (fallback full replay): %s" % str(ex)[:80])
    # 重放当前 audit.jsonl（快照之后的增量；无快照则全量）
    ap = os.path.join(DATA_DIR, "audit.jsonl")
    if os.path.exists(ap):
        for line in open(ap, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if line:
                try:
                    e = json.loads(line)
                    if e["op"] == "PUT":
                        state[e["key"]] = {"version": e["version"], "value": e["value"], "ts": e["ts"]}
                    seq = e.get("seq", 0)
                    if seq > 0:
                        _timeline_append(seq, e["op"], e["key"], e.get("version", 0))
                        if seq > max_seq:
                            max_seq = seq
                except Exception:
                    pass
    if max_seq > 0:
        _last_seq = max_seq
        _last_seq_snapshot = max_seq   # 防呆基准（HR P1-①）
        _last_phys = max_seq // 10**6
        print("clock restored: last_seq=%d timeline=%d" % (max_seq, len(_timeline)))
    _load_subs()   # v0.4：恢复订阅
    if subs:
        print("subs restored: %d" % len(subs))

def _audit(op, key, value, seq, writer=None):
    os.makedirs(DATA_DIR, exist_ok=True)
    entry = {"op": op, "key": key, "version": state.get(key, {}).get("version", 1), "value": value,
             "ts": _now_ts(), "seq": seq}
    if writer:  # v0.6：写者签名
        entry["writer"] = writer
    with _io_lock:
        with open(os.path.join(DATA_DIR, "audit.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        # v0.4：写后检查轮转阈值
        try:
            if os.path.getsize(os.path.join(DATA_DIR, "audit.jsonl")) > AUDIT_ROTATE_BYTES:
                pass  # 轮转在 PUT 完成后由 _maybe_rotate 统一触发，避免写中轮转
        except Exception:
            pass
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
        # 分页参数（v0.2 变更 4）+ v0.6 node 过滤
        limit, offset = None, 0
        since_seq = None
        op_filter = None
        node_filter = None
        if "?" in path:
            path, qs = path.split("?", 1)
            for kv in qs.split("&"):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    if k == "limit" and v.isdigit(): limit = int(v)
                    elif k == "offset" and v.isdigit(): offset = int(v)
                    elif k == "since_seq" and v.isdigit(): since_seq = int(v)
                    elif k == "op": op_filter = v
                    elif k == "node": node_filter = v  # v0.6：任务卡收件定向过滤
        # v0.5：GET /help — API 自描述
        if path == "help":
            self._ok({
                "server": "blackboard v0.6",
                "endpoints": [
                    {"method": "PUT", "path": "/<ns>/<key>", "desc": "写 KV（X-Writer 签名，响应带 seq）"},
                    {"method": "GET", "path": "/<ns>/<key>", "desc": "读单个 KV"},
                    {"method": "GET", "path": "/<ns>/", "desc": "列命名空间（?limit=&offset= 分页）"},
                    {"method": "DELETE", "path": "/<ns>/<key>", "desc": "删 KV（占全局 seq）"},
                    {"method": "POST", "path": "/subscribe", "desc": "订阅 topic→callback（unsub=true 退订；GET /subs 列表）"},
                    {"method": "GET", "path": "/clock", "desc": "对时：当前全局 seq + 黑板权威时间"},
                    {"method": "GET", "path": "/timeline?since_seq=N&limit=M&op=PUT|DELETE", "desc": "增量事件时间轴（基线对齐）"},
                    {"method": "GET", "path": "/ns-registry", "desc": "角色→职责命名空间注册表"},
                    {"method": "GET", "path": "/tasks?node=<id>", "desc": "任务卡列表（?node= 收件定向过滤，v0.6）"},
                    {"method": "GET", "path": "/stores", "desc": "门店类型节点列表（v0.6）"},
                    {"method": "GET", "path": "/help", "desc": "本帮助"},
                ],
                "write_example": "curl -X PUT http://127.0.0.1:8792/data/<role>/<key> -d '{\"status\":\"...\"}' -H 'Content-Type: application/json' -H 'X-Writer: <agent-id>'",
                "role_ns": {k: {"role": v[0], "ns": v[1]} for k, v in ROLE_NS.items()},
            })
            return
        # v0.6：GET /stores — 门店类型节点
        if path == "stores":
            stores = {}
            for k, v in state.items():
                if k.startswith("nodes/") and "/heartbeat" not in k and "/" not in k[6:]:
                    val = v.get("value") or {}
                    if isinstance(val, dict) and val.get("type") == "store":
                        stores[k.replace("nodes/", "")] = val
            self._ok({"stores": stores, "count": len(stores), "ts": _now_ts()})
            return
        # v0.5：GET /ns-registry — 职责命名空间注册表
        if path == "ns-registry":
            self._ok({
                "registry": {k: {"role": v[0], "ns": v[1]} for k, v in ROLE_NS.items()},
                "note": "各角色 STATUS/结果写自己的 ns，事件桥 data/ 前缀订阅自动回流（零 ACK）",
                "ts": _now_ts(),
            })
            return
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
            # v0.6：任务卡收件定向过滤（?node=<id> 只返回 recipient==id 或该节点前缀的卡）
            if node_filter and ns == "tasks":
                filtered = {}
                for k, v in items.items():
                    val = v.get("value")
                    recv = val.get("recipient") if isinstance(val, dict) else None
                    if recv == node_filter:
                        filtered[k] = v
                    elif recv is None and k.startswith("tasks/%s/" % node_filter):
                        filtered[k] = v
                items = filtered
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
        writer = self.headers.get("X-Writer", "") or None   # v0.6：写者签名
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
        _audit("PUT", full, value, seq, writer=writer)
        _timeline_append(seq, "PUT", full, ver)        # v0.3：记时间轴
        _mirror_result(full, seq)                      # v0.2 变更 1
        _notify(full, seq)                             # v0.2 变更 3（异步，带 seq）
        _rotate_audit()                                # v0.4：写后检查轮转
        resp = {"key": full, "version": ver, "seq": seq}   # v0.3：响应带 seq
        if writer: resp["writer"] = writer             # v0.6：回显写者
        self._ok(resp)
    def do_DELETE(self):
        if not self._auth(): return
        writer = self.headers.get("X-Writer", "") or None   # v0.6：写者签名
        m = NS_RE.match(self.path.lstrip("/"))
        if m:
            full = m.group(1) + "/" + m.group(2)
            if full in state:
                seq = _next_seq()                      # v0.3：DELETE 也占全局序
                del state[full]
                _audit("DELETE", full, None, seq, writer=writer)
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
                _save_subs()   # v0.4：退订持久化
                self._ok({"unsubscribed": len(removed), "subscribed": len(subs)})
                return
            key = (topic, callback)
            if key not in subs:  # v0.2 变更 2：去重
                subs[key] = {"topic": topic, "callback": callback,
                             "ts": datetime.datetime.now().isoformat(timespec="seconds")}
                _save_subs()   # v0.4：注册持久化
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
    print("blackboard-server v0.6 on :%d (token=%s) data=%s subs=%d clock_seq=%d timeline=%d"
          % (args.port, "on" if TOKEN else "off", DATA_DIR, len(subs), _last_seq, len(_timeline)))
    srv.serve_forever()
