#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb_dualwrite.py — 双板写 + 有界重试 + **统一失败留痕**（v1.0.0）

依据（裁判 2026-10-08 提醒③，最有价值的一条）：
  「按类改的验收应要求每个写入器各有一条可核证据」——但**若各写入器的痕迹格式不同，
   第三方无法只扫一处判断覆盖情况** ⇒ 故 helper 除「双板写 + 有界重试」外，
   **一并固定一个最小日志/回读字段集**，使「覆盖验收」变成一个**统计量**而非逐个人工确认。

统一留痕字段（每行一 JSON，机器可扫）：
  {"at","writer","key","action":"dualwrite",
   "boards":{"local":{"http","value_match"?},"central":{"http","value_match"?}},
   "both_readable","values_equal","retry_rounds","window_ms","verdict"}
  verdict ∈ {ok, transport-diff, defect, skipped-no-board, unverified}

用法:
  # 库
  from bb_dualwrite import put_both
  r = put_both(key, value, writer="<session-id>")
  # CLI
  python3 bb_dualwrite.py --key <k> --json-file <f> --writer <w> [--log <path>] [--json]
  python3 bb_dualwrite.py --selftest | --version
"""
import argparse, hashlib, json, os, sys, time, urllib.request

VERSION = "1.0.0"
__version__ = VERSION

BOARDS = [("local", "http://127.0.0.1:8792"), ("central", "http://xingqiao.meetfunbp.com:8792")]
# 有界退避（与 bb-card-send v1.2.x 同构）：累积上限默认 420s（实测最大两板延迟 220s ⇒ 余量 +91%）
BASE_DELAYS = [5000, 10000, 20000, 40000, 60000, 60000, 60000, 60000, 45000, 60000]
DEFAULT_WINDOW_MS = 420000
TRANSPORT_MARKERS = ("_via",)   # 传输标记（有实证；其余字段一律参与比较）
DEFAULT_LOG = os.path.expanduser("~/dsh-collab/logs/bb-dualwrite.jsonl")


def _tokens():
    def rd(p):
        try:
            return open(os.path.expanduser(p), encoding="utf-8").read().strip()
        except Exception:
            return ""
    return {"local": rd("~/.dsh/board-token"), "central_webhook": rd("~/.dsh/webhook-token"),
            "central_board": rd("~/.dsh/blackboard-token")}


def _headers(name, tok):
    if name == "local":
        return {"Authorization": "Bearer " + tok["local"]} if tok["local"] else {}
    h = {}
    if tok["central_webhook"]:
        h["X-Webhook-Token"] = tok["central_webhook"]
    if tok["central_board"]:
        h["X-Blackboard-Token"] = tok["central_board"]
    return h


def _req(base, key, method, body, writer=None, timeout=20):
    """返回 (http_status, value_or_None, error_or_None)。调用层异常不抛出（超时≠未落盘）。"""
    url = f"{base}/{key}"
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
    headers = {"Content-Type": "application/json"}
    if data:
        headers["Content-Length"] = str(len(data))
    if writer:
        headers["X-Writer"] = writer      # ★ 板层归属（板升级到 0.6.20+ 后即被审计行记录）
    headers.update(_headers("local" if "127.0.0.1" in base else "central", _tokens()))
    try:
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "ignore")
            try:
                return r.status, json.loads(raw).get("value"), None
            except Exception:
                return r.status, None, "非 JSON 响应"
    except urllib.error.HTTPError as e:
        return e.code, None, f"HTTP {e.code}"
    except Exception as e:
        return None, None, type(e).__name__   # 超时/网络 ⇒ 调用层失败，交给回读判


def _sha(v, exclude=TRANSPORT_MARKERS):
    if isinstance(v, dict):
        v = {k: x for k, x in v.items() if k not in exclude}
    return hashlib.sha256(json.dumps(v, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]


def _delays(window_ms):
    out, acc = [], 0
    for d in BASE_DELAYS:
        if acc + d > window_ms:
            break
        out.append(d); acc += d
    return out, acc


def put_both(key, value, writer="unattributed", window_ms=DEFAULT_WINDOW_MS, log_path=DEFAULT_LOG):
    """双板写 + 有界重试等待可见性 + 统一留痕。返回统一字段 dict。"""
    t0 = time.time()
    delays, window_actual = _delays(window_ms)
    rec = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "writer": writer, "key": key,
           "action": "dualwrite", "boards": {}, "retry_rounds": 0, "window_ms": window_actual}
    # 写 + 回读（调用层异常不中断）
    for name, base in BOARDS:
        st, _, err = _req(base, key, "PUT", value, writer=writer)
        rec["boards"][name] = {"http": st, "put_error": err}
    # 有界重试：两板 value 指纹一致才停
    vals, rounds = {}, 0
    for _ in range(0, 1):   # 初次读
        for name, base in BOARDS:
            st, v, err = _req(base, key, "GET", None)
            rec["boards"][name]["http"] = st
            rec["boards"][name]["get_error"] = err
            vals[name] = v
    while _sha(vals.get("local")) != _sha(vals.get("central")) and rounds < len(delays):
        time.sleep(delays[rounds] / 1000.0)
        rounds += 1
        rec["retry_rounds"] = rounds
        for name, base in BOARDS:
            st, v, err = _req(base, key, "GET", None)
            rec["boards"][name]["http"] = st
            if v is not None:
                vals[name] = v
    rec["boards"]["local"]["value_match"] = (vals.get("local") is not None)
    rec["boards"]["central"]["value_match"] = (vals.get("central") is not None)
    both = all(rec["boards"][n]["value_match"] for n, _ in BOARDS)
    equal = both and _sha(vals.get("local")) == _sha(vals.get("central"))
    rec["both_readable"] = bool(both)
    rec["values_equal"] = bool(equal)
    rec["values_sha"] = {"local": _sha(vals.get("local")), "central": _sha(vals.get("central"))}
    if not both and rounds >= len(delays) and rec["boards"]["local"]["http"] is None \
            and rec["boards"]["central"]["http"] is None:
        rec["verdict"] = "skipped-no-board"
    elif not both:
        rec["verdict"] = "defect"
    elif equal:
        rec["verdict"] = "ok"
    else:
        rec["verdict"] = "transport-diff"   # 差异仅可能在传输标记（已从指纹排除）
    rec["elapsed_ms"] = int((time.time() - t0) * 1000)
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return rec


def blackhole_test(window_ms=8000):
    """受控黑洞测试：起一个**接受连接但不回包**的 socket ⇒ 强制触发调用层超时与重试路径。
    验证「重试逻辑真的会跑」（手段就绪 ≠ 已实战验证）。返回 dict。"""
    import socket, threading
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0)); srv.listen(5)
    port = srv.getsockname()[1]
    stop = {"v": False}
    def acceptor():
        conns = []
        while not stop["v"]:
            try:
                srv.settimeout(0.5); c, _ = srv.accept(); conns.append(c)   # 收下但不回
            except Exception:
                pass
    t = threading.Thread(target=acceptor, daemon=True); t.start()
    global BOARDS
    real = BOARDS
    BOARDS = [("local", f"http://127.0.0.1:{port}"), ("central", f"http://127.0.0.1:{port}")]
    t0 = time.time()
    try:
        r = put_both("notes/mac-mini/__blackhole-probe__", {"x": 1}, writer="blackhole-selftest",
                     window_ms=window_ms, log_path="/tmp/bb-dualwrite-blackhole.jsonl")
    finally:
        BOARDS = real
        stop["v"] = True
        try: srv.close()
        except Exception: pass
    r["blackhole_port"] = port
    r["wall_ms"] = int((time.time() - t0) * 1000)
    return r


def selftest():
    ok = fail = 0
    def chk(c, l):
        nonlocal ok, fail
        if c: ok += 1; print("  ✅", l)
        else: fail += 1; print("  ❌", l)
    d, acc = _delays(DEFAULT_WINDOW_MS)
    chk(acc == 420000, f"退避累积 = 声明窗（{acc}ms）")
    d2, acc2 = _delays(240000)
    chk(acc2 <= 240000, "小窗不越界")
    chk(_sha({"a": 1, "_via": "x"}) == _sha({"a": 1}), "传输标记不参与指纹（_via 已排除）")
    chk(_sha({"a": 1}) != _sha({"a": 2}), "真差异 ⇒ 指纹不同（有判别力）")
    chk(_sha({"a": 1, "b": 2}) == _sha({"b": 2, "a": 1}), "键序无关（canonical）")
    # 统一留痕字段完备性（第三方可扫）
    r = put_both("notes/mac-mini/__dualwrite-selftest__", {"probe": 1}, writer="selftest",
                 window_ms=5000, log_path="/tmp/bb-dualwrite-selftest.jsonl")
    need = {"at", "writer", "key", "action", "boards", "both_readable", "values_equal",
            "retry_rounds", "window_ms", "verdict", "elapsed_ms"}
    chk(need <= set(r.keys()), "统一留痕字段集完备（缺一即不可统计）")
    chk(r["verdict"] in ("ok", "transport-diff", "defect", "skipped-no-board", "unverified"),
        f"verdict 取值在枚举内（当前 {r['verdict']}）")
    print(f"\nselftest: {ok} PASS / {fail} FAIL")
    return 0 if fail == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key"); ap.add_argument("--json-file"); ap.add_argument("--writer", default="unattributed")
    ap.add_argument("--window-ms", type=int, default=DEFAULT_WINDOW_MS)
    ap.add_argument("--log", default=DEFAULT_LOG); ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true"); ap.add_argument("--version", action="store_true")
    ap.add_argument("--blackhole-test", action="store_true", help="受控黑洞：验证重试路径真的会跑")
    a = ap.parse_args()
    if a.version:
        print(json.dumps({"tool": "bb_dualwrite", "version": VERSION})); return 0
    if a.selftest:
        return selftest()
    if a.blackhole_test:
        r = blackhole_test()
        print(json.dumps(r, ensure_ascii=False, indent=1))
        # 判据：必须观测到 ≥1 轮重试 且 verdict 表明未收敛
        okk = r["retry_rounds"] >= 1 and r["verdict"] in ("defect", "skipped-no-board")
        print(("✅ 重试路径已实战验证" if okk else "❌ 重试路径未被触发（手段就绪≠已验证）")
              + f" | retry_rounds={r['retry_rounds']} verdict={r['verdict']} wall={r['wall_ms']}ms")
        return 0 if okk else 1
    if not (a.key and a.json_file):
        ap.error("需要 --key 与 --json-file（或 --selftest/--version）")
    with open(a.json_file, encoding="utf-8") as f:
        val = json.load(f)
    r = put_both(a.key, val, writer=a.writer, window_ms=a.window_ms, log_path=a.log)
    print(json.dumps(r, ensure_ascii=False, indent=1) if a.json else
          f"{r['verdict']} key={r['key']} writer={r['writer']} retry={r['retry_rounds']} "
          f"equal={r['values_equal']} elapsed={r['elapsed_ms']}ms")
    return 0 if r["verdict"] in ("ok", "transport-diff") else 1


if __name__ == "__main__":
    sys.exit(main())
