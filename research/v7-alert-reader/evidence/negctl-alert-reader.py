#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""negctl-alert-reader.py — 给「告警卡有读者（M4①d/M4③②）」这条判据造负控

★ 为什么需要：本项目纪律「一个断言若从未红过，它就不是判据」。
  `beacon-check.py --selftest` 现测覆盖 10 条逻辑判据 + 心跳 4 条负控，
  **但「告警卡有读者」这一条在 selftest 里没有 case**（见 07 篇原始输出）。

★ 本脚本只读【本地假板】，绝不 PUT/POST 真板；真板仅只读 GET。
四态：
  ① 假板非空（无 _archived_at） ⇒ n>0  ⇒ 该条应【红】
  ② 假板为空                   ⇒ n=0  ⇒ 该条应【绿】
  ③ 假板非空但全带 _archived_at ⇒ n=0  ⇒ ★【归档即转绿】（本次要证的关键）
  ④ 端口不可达                 ⇒ None ⇒ 【不可判】（不冒充绿）
另附：真板 7 条归档卡的「带过滤/不带过滤」对照读数。
"""
import http.server, json, socketserver, threading, importlib.util, os, sys

BC = "/Users/coreyleung/dsh-collab/tools/beacon-check.py"
BOARD = os.environ.get("DSH_BB_URL", "http://127.0.0.1:8792")
TOKEN_F = os.path.expanduser("~/.dsh/board-token")

spec = importlib.util.spec_from_file_location("bc", BC)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

CARD = {"ts": "2026-10-12T19:23:12", "version": 1,
        "value": {"type": "drift-delivery-failure", "from": "drift-scan-cron",
                  "failedLegs": ["central"], "note": "★ 假板负控卡（不落真板）"}}
ARCHIVED = {"ts": "2026-10-12T19:23:12", "version": 2,
            "value": {"type": "drift-delivery-failure", "failedLegs": ["central"],
                      "_archived_at": "2026-10-12T19:23:08+08:00",
                      "_archived_note": "假板归档卡"}}

def serve(payload_list):
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            b = json.dumps({"list": payload_list, "total": len(payload_list),
                            "offset": 0, "limit": None}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b))); self.end_headers()
            self.wfile.write(b)
        def log_message(self, *a): pass
    srv = socketserver.TCPServer(("127.0.0.1", 0), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True); t.start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]

def judge(reads):
    """复刻 beacon-check 的判决分支（机械抄自源码 468-490 行）"""
    unread = [d for d, v in reads.items() if v is None]
    hot = [(d, v[0], v[1]) for d, v in reads.items() if v and v[0] > 0]
    if len(unread) == len(reads): return ("SKIP", "都读不到 ⇒ 不可判")
    if hot: return ("FAIL(红)", "未处理告警 %d 条" % sum(n for _, n, _ in hot))
    ok = [d for d, v in reads.items() if v is not None]
    return ("PASS(绿)", "已读 %d 目录、均空" % len(ok))

print("=== 负控①：假板【非空】⇒ 期望 红 ===")
srv, url = serve({"data/ops/drift-delivery-failure/1791752163821": CARD})
r = m.read_alert_cards(board_url=url); srv.shutdown()
print("  read_alert_cards =", r); print("  判决 =", judge(r)[0], "|", judge(r)[1])

print("=== 负控②：假板【空】⇒ 期望 绿 ===")
srv, url = serve({})
r = m.read_alert_cards(board_url=url); srv.shutdown()
print("  read_alert_cards =", r); print("  判决 =", judge(r)[0], "|", judge(r)[1])

print("=== 负控③：假板【非空但全归档】⇒ 期望 绿（★ 归档即转绿）===")
srv, url = serve({"data/ops/drift-delivery-failure/1791752163821": ARCHIVED})
r = m.read_alert_cards(board_url=url); srv.shutdown()
print("  read_alert_cards =", r); print("  判决 =", judge(r)[0], "|", judge(r)[1])

print("=== 负控④：端口不可达 ⇒ 期望 不可判 ===")
r = m.read_alert_cards(board_url="http://127.0.0.1:1")
print("  read_alert_cards =", r); print("  判决 =", judge(r)[0], "|", judge(r)[1])

print("=== 真板对照（只读 GET）：带 _archived_at 过滤 vs 不带 ===")
import urllib.request
def raw(d, tok=None):
    req = urllib.request.Request(BOARD.rstrip("/") + "/" + d + "/")
    if tok: req.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(req, timeout=8) as r: return json.loads(r.read())["list"]
tok = open(TOKEN_F).read().strip() if os.path.exists(TOKEN_F) else None
for d in m.ALERT_DIRS:
    try:
        L = raw(d, tok)
        n_all = len(L)
        n_live = len([k for k, v in L.items() if not ((v or {}).get("value") or {}).get("_archived_at")])
        j_all = "绿" if n_all == 0 else "红"
        j_live = "绿" if n_live == 0 else "红"
        print(f"  {d}: 不带过滤 n={n_all} ⇒ 判决={j_all} ; 带过滤 n={n_live} ⇒ 判决={j_live}")
    except Exception as e:
        print(f"  {d}: 读失败 {type(e).__name__}: {e} ⇒ 不可判")
