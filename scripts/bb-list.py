#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-list.py — 黑板枚举，**永远附带搜索面**

作者: 老登 session-aa528267 (mac-mini) · 2026-09-28

存在的理由（一次真实错误）
  我报「未找到比 09:52:56 更新的卡」——而那张卡**是存在的**（10:00:36 落卡），
  只是我的列表快照（total=1503 · 最大 ts=09:52:56）**早于它诞生**。
  ⇒ ⇒ **「对象不存在」与「我的快照早于它诞生」读数是同一个**【没找到】✓
  ⇒ 这与我已经立过的那两条同族：
     · 「造不出反例」有**两种成因**（结构上不可能 / 我没想到）——读数相同、处置相反
     · 「不可达 ≠ 不存在」（今天在 binding-check 里刚修过）
     · 三档里「**未核**」不进错误率，但**必须报未核占比**
  ⇒ 本次是**时间维度的「未核」**：我把【未核（搜得太早）】报成了【已核的不存在】——
    把**我的观测装置的性质**（快照过期）说成了**对象的性质**（不存在）。

判据（本工具把判断变成读数）
  **报「未找到」时必须附【我搜到哪一刻 + 搜了多大的面】。**
  ⇒ 本工具**无论如何**都打印：前缀（面）· 快照时刻 · total · ts 区间 · 匹配数
    ⇒ 于是「没有」与「我搜得早」**不再同形** ✓

用法
  bb-list.py <前缀> [--grep 正则] [--json]
  例: bb-list.py notes/mac-mini --grep '^mingjian-' --json

退出码
  0 有匹配
  2 **无匹配**（但搜索面照印 —— 「没有」必须带着面报）
  3 黑板不可达（**≠ 不存在**）
  4 用法错 / 前缀写法非法
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, sys, urllib.error, urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-list.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = "1.0.0"
BB = os.environ.get("BB_BASE", "http://127.0.0.1:8792")


def fetch_list(prefix):
    """取前缀列举。返回 (items, error_kind)。error_kind 非空即失败。"""
    url = "%s/%s/" % (BB, prefix.strip("/"))
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            raw = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code == 400:
            return None, ("前缀写法非法", "首段须纯小写字母 [a-z]+；本前缀=%r" % prefix)
        return None, ("HTTP %s" % e.code, url)
    except urllib.error.URLError as e:
        return None, ("黑板**不可达**", "%s ⇒ 本次**取不到**，与「不存在」是两件事" % e.reason)
    try:
        d = json.loads(raw)
    except ValueError as e:
        return None, ("响应非 JSON", str(e)[:120])
    lst = d.get("list", d) if isinstance(d, dict) else d
    if not isinstance(lst, dict):
        return None, ("列举结构异常", type(lst).__name__)
    return lst, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prefix", nargs="?")
    ap.add_argument("--grep", default=None, help="对完整的键做正则过滤")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="version", version="bb-list %s" % VERSION)
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if not a.prefix:
        print(__doc__)
        return 4
    try:
        pat = re.compile(a.grep) if a.grep else None
    except re.error as e:
        print("❌ --grep 正则非法：%s" % e)
        return 4

    lst, err = fetch_list(a.prefix)
    if err:
        print("❌ %s：%s" % err)
        return 3 if "不可达" in err[0] else 4

    items = [(k, (v.get("ts", "") if isinstance(v, dict) else ""))
             for k, v in lst.items()]
    matched = [(k, ts) for k, ts in items if pat.search(k)] if pat else items
    matched.sort(key=lambda x: x[1], reverse=True)

    snap = __import__("time").strftime("%Y-%m-%dT%H:%M:%S")
    total = len(items)
    all_ts = [ts for _, ts in items if ts]
    rep = {
        "搜索面_前缀": a.prefix,
        "搜索面_快照时刻": snap,
        "搜索面_对象总数": total,
        "搜索面_ts区间": [min(all_ts), max(all_ts)] if all_ts else None,
        "过滤正则": a.grep,
        "匹配数": len(matched),
        "匹配": [{"key": k, "ts": ts} for k, ts in matched],
        "★ 报「未找到」时须连同本行的面一并报出": "否则「没有」与「我搜得早」同形",
    }
    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    else:
        print("黑板枚举 · 面=%s" % a.prefix)
        print("  **搜索面**：快照时刻 %s · 对象总数 %d · ts 区间 %s"
              % (snap, total, rep["搜索面_ts区间"]))
        if a.grep:
            print("  过滤正则: %s" % a.grep)
        if matched:
            print("  匹配 %d 条：" % len(matched))
            for k, ts in matched[:40]:
                print("    %s  %s" % (ts or "（无 ts）", k))
            if len(matched) > 40:
                print("    … 另有 %d 条未列" % (len(matched) - 40))
        else:
            # ★ 「没有」必须带着面报 —— 这正是本工具存在的理由
            print("  ⚠️ **无匹配**。但请连同上面那行【搜索面】一起引用：")
            print("     对象总数=%d · 快照止于 %s ⇒ 本结论的时效**止于该时刻**，"
                  "晚于它的写入不在本次面内。" % (total, rep["搜索面_ts区间"]))
    return 0 if matched else 2


def selftest():
    """自测：码 0/2/3/4 各一 must_reject，且 must_pass 反向用例必备。"""
    import http.server, threading, tempfile
    class _Stub(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/bad"):
                self.send_response(400)
            elif self.path.startswith("/empty"):
                self.send_response(200)
            else:
                self.send_response(200)
            body = json.dumps({"list": {"notes/x/a": {"ts": "2026-01-01T00:00:00"}}}).encode() \
                if not self.path.startswith("/empty") else json.dumps({"list": {}}).encode()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.path.startswith("/bad"):
                return
            self.wfile.write(body)
        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Stub)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % srv.server_address[1]
    me = os.path.abspath(__file__)
    import subprocess
    def run(args, b):
        env = dict(os.environ); env["BB_BASE"] = b
        return subprocess.run([sys.executable, me] + args, capture_output=True,
                              text=True, env=env)
    cases = [
        ("must_pass·有匹配 ⇒ 码 0", ["notes/x"], base, 0, "匹配 1 条"),
        ("must_reject·前缀无人 ⇒ 码 2（且须印出搜索面）", ["notes/x", "--grep", "zzz"], base, 2, "搜索面"),
        ("must_reject·黑板不可达 ⇒ 码 3（≠ 不存在）", ["notes/x"], "http://127.0.0.1:9", 3, "不可达"),
        ("must_reject·前缀写法非法(400) ⇒ 码 4", ["bad/x"], base, 4, "写法非法"),
        ("must_reject·--grep 正则非法 ⇒ 码 4", ["notes/x", "--grep", "("], base, 4, "正则非法"),
        ("must_reject·无参数 ⇒ 码 4", [], base, 4, "用法"),
    ]
    detail, ok = [], 0
    for name, args, b, exp, must in cases:
        p = run(args, b)
        good = (p.returncode == exp) and (must in p.stdout)
        ok += good
        detail.append((name, good, p.returncode, exp))
    # ★★ 差分断言：码 2（无匹配）与码 3（不可达）必须**既不同码也不同文**
    p2 = run(["notes/x", "--grep", "zzz"], base)
    p3 = run(["notes/x"], "http://127.0.0.1:9")
    diff_ok = (p2.returncode != p3.returncode) and ("搜索面" in p2.stdout) \
        and ("不可达" in p3.stdout) and ("搜索面" not in p3.stdout)
    detail.append(("★★ 码2（没有）与码3（取不到）可区分，且码3**不得**冒充搜索面",
                   diff_ok, "%s/%s" % (p2.returncode, p3.returncode), "不同"))
    srv.shutdown()
    ok += diff_ok
    for name, good, got, exp in detail:
        print("  %s %s  期望 %s / 实得 %s" % ("✅" if good else "❌", name, exp, got))
    n_rej = [d for d in detail if "must_reject" in d[0]]
    n_pas = [d for d in detail if "must_pass" in d[0]]
    print("\nselftest %d/%d" % (ok, len(detail)))
    print("覆盖形态: must_reject %d/%d · must_pass %d/%d"
          % (sum(1 for d in n_rej if d[1]), len(n_rej),
             sum(1 for d in n_pas if d[1]), len(n_pas)))
    return 0 if ok == len(detail) else 2


if __name__ == "__main__":
    sys.exit(main())
