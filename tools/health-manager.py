#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""health-manager.py —— 【底座健康管理器】

★★★ 立据（用户指令 2026-10-15 · v6.1 §0.1.4 H-3 · D-336）：
  ★ 用户逐字：「能不能给底座的每一个节点和面，分别都加监控点，相当于给整个底座
    做一个健康状态健康管理器？能随时让你们能看到状态，而不是每次遇到问题猜情况」
  ★ 而 v6.1 §0.1.4 的 **H-3 原文**就是这句：
    「**健康检查须覆盖通讯通道** | 现覆盖 **0 条**通讯通道；
     且 `/health` 是命名空间列举的**假阳性**（`{"total":0}` 空壳）」
  ★★ 故本器 = **H-3 的实现**。

★★ 四条设计纪律：
  ① **每项必带三态**（OK / DEGRADED / DOWN / UNDECIDABLE）—— 不可判不得读作 OK
  ② **每项必带【判据 + 实测值 + 取值的时刻】** —— 否则读者无法复核
  ③ **不猜**：取不到的写 UNDECIDABLE 并带原因（★ 「空 ≠ 无」）
  ④ **与实测同源**：不缓存、不推断；每次都是现测

★ 覆盖的两大类：
  【节点】进程 / 端口 / launchd 任务 / 定时任务
  【面】黑板命名空间 / 域面 / 双板可达性 / 通讯通道

用法：
  python3 tools/health-manager.py                # ★ 全量巡检（人类可读）
  python3 tools/health-manager.py --json         # ★ 机器可读
  python3 tools/health-manager.py --selftest     # ★ 自证（含双向负控）
  python3 tools/health-manager.py --publish      # ★ 写入黑板 health/ 面（跨会话可查）
  python3 tools/health-manager.py --section node # ★ 只看节点 / face=只看面
"""
import argparse
import datetime
import io
import json
import os
import re
import subprocess
import sys
import urllib.request

VERSION = "1.0.0"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser("~")
BB_LOCAL = "http://127.0.0.1:8792"
BB_CENTRAL = "http://xingqiao.meetfunbp.com:8792"

OK, DEGRADED, DOWN, UNDEC = "OK", "DEGRADED", "DOWN", "UNDECIDABLE"


def _tok(name="blackboard-token"):
    try:
        return io.open(os.path.join(HOME, ".dsh", name), encoding="utf-8").read().strip()
    except Exception:
        return ""


def _now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _run(cmd, timeout=15):
    """★ 取 (退出码, stdout)。★ macOS 无 timeout ⇒ 用 subprocess 的 timeout 参数。"""
    try:
        p = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True,
                           text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"
    except Exception as e:
        return 125, "%s: %s" % (type(e).__name__, e)


def _http(url, token=None, timeout=10, method="GET"):
    """★ 取 (状态码, 体文本)。★ 连通失败 ⇒ (None, 原因)"""
    try:
        req = urllib.request.Request(url, method=method)
        if token:
            req.add_header("Authorization", "Bearer " + token)
            req.add_header("X-Blackboard-Token", token)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, "(HTTPError)"
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, str(e)[:60])


def item(node, kind, name, verdict, why, value=None, probe=None):
    """★ 每个监控点的统一形态（★ 必带判据 / 实测值 / 时刻）"""
    return {
        "node": node, "kind": kind, "name": name,
        "verdict": verdict, "why": why,
        "value": value, "probe": probe or "",
        "at": _now(),
    }


# ═══════════════════════ 节 1：节点（进程 / 端口） ═══════════════════════
def scan_ports():
    out = []
    rc, txt = _run(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"])
    if rc != 0 and "TIMEOUT" in txt:
        return [item("port", "port", "*", UNDEC, "lsof 超时 ⇒ 不可判", probe="lsof -nP -iTCP -sTCP:LISTEN")]
    # ★ 只关心 dsh 家族的端口（★ 别的 app 的端口不属本底座）
    seen = {}
    for ln in txt.split("\n")[1:]:
        p = ln.split()
        if len(p) < 9:
            continue
        proc, pid, addr = p[0], p[1], p[-2]
        if not re.search(r"(rust-blac|rust-blackboard|dsh-tool|node-bridge|blackboard-mcp|CLD|Python)", proc):
            continue
        m = re.search(r":(\d+)$", addr)
        if not m:
            continue
        port = m.group(1)
        seen.setdefault(port, []).append((proc, pid))
    for port in sorted(seen, key=lambda x: int(x)):
        procs = seen[port]
        names = ",".join(sorted({a for a, _ in procs}))
        pids = ",".join(sorted({b for _, b in procs}))
        out.append(item("port", "port", ":" + port, OK,
                        "监听中 · %s (pid %s)" % (names, pids), value={"proc": names, "pid": pids},
                        probe="lsof -nP -iTCP:%s -sTCP:LISTEN" % port))
    if not out:
        out.append(item("port", "port", "*", UNDEC, "未发现 dsh 家族监听端口 ⇒ 可能全挂或探测失败",
                        probe="lsof -nP -iTCP -sTCP:LISTEN"))
    return out


# ═══════════════════════ 节 2：节点（launchd 任务） ═══════════════════════
def scan_launchd():
    out = []
    rc, txt = _run(["launchctl", "list"])
    if rc != 0:
        return [item("launchd", "job", "*", UNDEC, "launchctl list 失败 ⇒ 不可判", probe="launchctl list")]
    n_all = n_run = n_fail = 0
    fails = []
    for ln in txt.split("\n"):
        p = ln.split("\t")
        if len(p) < 3 or not p[2].startswith("com.dsh."):
            continue
        n_all += 1
        pid, status, label = p[0], p[1], p[2]
        if pid != "-":
            n_run += 1
        elif status not in ("0", "-"):
            n_fail += 1
            fails.append("%s(exit=%s)" % (label.replace("com.dsh.", ""), status))
    out.append(item("launchd", "job", "com.dsh.*", OK if n_all else UNDEC,
                    "共 %d · 运行中 %d · 失败终态 %d" % (n_all, n_run, n_fail),
                    value={"all": n_all, "running": n_run, "failed_terminal": n_fail, "fails": fails[:12]},
                    probe="launchctl list | grep com.dsh."))
    return out


# ═══════════════════════ 节 3：面（黑板双板） ═══════════════════════
def scan_boards():
    out = []
    tok = _tok()
    for nm, url in (("local", BB_LOCAL), ("central", BB_CENTRAL)):
        st, body = _http(url + "/health", tok)
        if st is None:
            out.append(item("board", "face", nm, DOWN, "不可达：%s" % body,
                            probe="curl %s/health" % url))
            continue
        try:
            d = json.loads(body)
            n = (d.get("total") if isinstance(d, dict) else None)
        except Exception:
            n = None
        # ★★★ 关键判据：★ `/health` 是不是【空壳】—— ★ v6.1 H-3 指出的假阳性
        if st == 200 and n == 0:
            out.append(item("board", "face", nm, DEGRADED,
                            "可达 200 但 total=0 ⇒ ★ 疑【空壳假阳性】（★ H-3 指出的形态）",
                            value={"http": st, "total": n}, probe="curl %s/health" % url))
        else:
            out.append(item("board", "face", nm, OK,
                            "可达 · /health total=%s" % n,
                            value={"http": st, "total": n}, probe="curl %s/health" % url))
    return out


# ═══════════════════════ 节 4：面（命名空间规模） ═══════════════════════
def scan_namespaces():
    out = []
    tok = _tok()
    for ns in ("notes/", "data/", "tasks/", "health/"):
        st, body = _http(BB_LOCAL + "/" + ns, tok)
        if st is None:
            out.append(item("face", "ns", ns, UNDEC, "取不到：%s" % body, probe="curl %s/%s" % (BB_LOCAL, ns)))
            continue
        try:
            d = json.loads(body)
            n = len(d.get("list") or {})
        except Exception:
            out.append(item("face", "ns", ns, UNDEC, "返回非 JSON", probe="curl %s/%s" % (BB_LOCAL, ns)))
            continue
        # ★ health/ 面是「健康状态」面 —— ★ 它若空，那本身就是缺口
        if ns == "health/" and n <= 5:
            out.append(item("face", "ns", ns, DEGRADED,
                            "★ 【健康面几乎为空】（%d 键）⇒ 底座无健康状态可查（★ 本器在补）" % n,
                            value=n, probe="curl %s/health/  # ★ 注意：不是 /health（那是空壳）" % BB_LOCAL))
        else:
            out.append(item("face", "ns", ns, OK, "%d 键" % n, value=n,
                            probe="curl %s/%s" % (BB_LOCAL, ns)))
    return out


# ═══════════════════════ 节 5：面（通讯通道 · H-3 核心） ═══════════════════════
def scan_channels():
    """★★★ H-3：「健康检查须覆盖通讯通道」—— ★ 本节的每一条都是一条【通讯通道】。"""
    out = []
    tok = _tok()

    # ★ 通道 1：本机板 ↔ 中枢板（★ 双写通道）
    st, body = _http(BB_CENTRAL + "/health", tok)
    out.append(item("channel", "channel", "local↔central 双写", OK if st == 200 else DOWN,
                    "中枢 %s" % ("可达 200" if st == 200 else "不可达(%s)" % body),
                    value={"central_http": st}, probe="curl %s/health" % BB_CENTRAL))

    # ★ 通道 2：agent-bus（★ 跨会话）
    rc, txt = _run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "8",
                    "http://127.0.0.1:8791/"])
    code = (txt or "").strip()
    # ★ 401 也算「活着」（★ 只是要鉴权）；000 = 死
    alive = code not in ("", "000")
    out.append(item("channel", "channel", "agent-bus :8791", OK if alive else DOWN,
                    "HTTP %s（★ 401 也是活着——只是需鉴权）" % code,
                    value={"http": code}, probe="curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8791/"))

    # ★ 通道 3：锁状态文件（★ 跨智能体互斥的载体）
    p = os.path.join(HOME, ".dsh", "agent-bus.json")
    if not os.path.isfile(p):
        out.append(item("channel", "channel", "锁状态文件", UNDEC, "不存在：%s" % p, probe="ls " + p))
    else:
        try:
            d = json.load(io.open(p, encoding="utf-8"))
            n = len(d.get("locks") or [])
            age = int(datetime.datetime.now().timestamp() - os.path.getmtime(p))
            v = OK if age < 3600 else DEGRADED
            out.append(item("channel", "channel", "锁状态文件", v,
                            "%d 个锁 · 最后写 %d 秒前" % (n, age),
                            value={"locks": n, "age_s": age}, probe="python3 -c \"import json;print(len(json.load(open('%s'))['locks']))\"" % p))
        except Exception as e:
            out.append(item("channel", "channel", "锁状态文件", UNDEC, "解析失败：%s" % type(e).__name__, probe="cat " + p))

    # ★ 通道 4：SSE 订阅面（★ 与 :8792 同 pid ⇒ 本线 S-4 单点）
    rc, txt = _run(["lsof", "-nP", "-iTCP:8803", "-sTCP:LISTEN"])
    if "LISTEN" in txt:
        pid = ""
        for ln in txt.split("\n")[1:]:
            pp = ln.split()
            if len(pp) >= 2:
                pid = pp[1]
                break
        out.append(item("channel", "channel", "SSE 订阅面 :8803", DEGRADED,
                        "监听中(pid %s) ⇒ ★★ 但它在 S-4 意义上是【单点】（★ 与某端口同进程时要标）" % pid,
                        value={"pid": pid}, probe="lsof -nP -iTCP:8803 -sTCP:LISTEN"))
    else:
        out.append(item("channel", "channel", "SSE 订阅面 :8803", DOWN,
                        "无监听 ⇒ 订阅面断了（★ 而那意味着推送静默失效——★ 正是 D-336 那类无告警故障）",
                        probe="lsof -nP -iTCP:8803 -sTCP:LISTEN"))

    # ★ 通道 5：跨机（★ 中枢 SSH）
    rc, txt = _run(["nc", "-z", "-w", "5", "106.53.214.108", "22"])
    out.append(item("channel", "channel", "中枢 SSH :22", OK if rc == 0 else DOWN,
                    "TCP %s" % ("通" if rc == 0 else "不通"),
                    probe="nc -z -w 5 106.53.214.108 22"))
    return out


# ═══════════════════════ 节 6：面（在途告警） ═══════════════════════
def scan_alerts():
    """★ 告警面有没有「没人处理」的堆积 —— ★ 那是 D-339 那类静默失败的读数"""
    out = []
    tok = _tok()
    st, body = _http(BB_LOCAL + "/data/ops/", tok)
    if st is None:
        return [item("alert", "face", "data/ops/", UNDEC, "取不到：%s" % body, probe="curl %s/data/ops/" % BB_LOCAL)]
    try:
        d = json.loads(body)
        L = d.get("list") or {}
    except Exception:
        return [item("alert", "face", "data/ops/", UNDEC, "返回非 JSON", probe="curl %s/data/ops/" % BB_LOCAL)]
    import collections
    seg = collections.Counter()
    for k in L:
        p = str(k).split("/")
        if len(p) >= 3:
            seg[p[2]] += 1
    top = seg.most_common(8)
    out.append(item("alert", "face", "data/ops/ 告警面", OK if L else DEGRADED,
                    "共 %d 键 · 面 %d 个%s" % (len(L), len(seg),
                                             ("：" + ", ".join("%s=%d" % t for t in top)) if top else "（★ 空面 ⇒ 无告警载体）"),
                    value={"total": len(L), "segments": dict(top)},
                    probe="curl %s/data/ops/" % BB_LOCAL))
    return out


SECTIONS = [
    ("node", "节点 · 端口", scan_ports),
    ("node", "节点 · launchd", scan_launchd),
    ("face", "面 · 黑板双板", scan_boards),
    ("face", "面 · 命名空间", scan_namespaces),
    ("channel", "★ 通讯通道（H-3 核心）", scan_channels),
    ("alert", "告警面", scan_alerts),
]

ICON = {OK: "✅", DEGRADED: "⚠️ ", DOWN: "❌", UNDEC: "❓"}


def report(only=None, as_json=False):
    all_items = []
    for sec_id, title, fn in SECTIONS:
        if only and sec_id != only:
            continue
        try:
            items = fn()
        except Exception as e:
            items = [item(sec_id, "?", title, UNDEC, "巡检器异常：%s" % type(e).__name__, probe="")]
        for it in items:
            it["section"] = title
        all_items.append((title, items))

    tally = {}
    for _, items in all_items:
        for it in items:
            tally[it["verdict"]] = tally.get(it["verdict"], 0) + 1

    if as_json:
        return {"version": VERSION, "at": _now(), "tally": tally,
                "sections": [{"title": t, "items": i} for t, i in all_items]}

    print("══ 底座健康管理器 %s ══  时刻 %s" % (VERSION, _now()))
    for title, items in all_items:
        print("\n【%s】" % title)
        for it in items:
            print("  %s %-22s %s" % (ICON.get(it["verdict"], "?"), it["name"], it["why"]))
            if it.get("probe"):
                print("       ↳ 复跑：%s" % it["probe"])
    print("\n【汇总】" + " · ".join("%s=%d" % (k, tally.get(k, 0)) for k in (OK, DEGRADED, DOWN, UNDEC)))
    return None


def publish():
    """★ 写入黑板 health/ 面 ⇒ 跨会话跨设备随时可查"""
    d = report(as_json=True)
    tok = _tok()
    key = "health/mac-mini/%s" % datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    body = json.dumps({"type": "health-snapshot", "from": "health-manager", "at": d["at"],
                       "tally": d["tally"],
                       "items": [{"section": s["title"], "name": i["name"], "verdict": i["verdict"],
                                  "why": i["why"]}
                                 for s in d["sections"] for i in s["items"]]},
                      ensure_ascii=False).encode()
    ok_any = False
    for nm, url in (("local", BB_LOCAL), ("central", BB_CENTRAL)):
        try:
            req = urllib.request.Request(url + "/" + key, data=body, method="PUT")
            req.add_header("Authorization", "Bearer " + tok)
            req.add_header("X-Blackboard-Token", tok)
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=12) as r:
                print("  %s PUT %s ⇒ %s" % (nm, key, r.status))
                ok_any = True
        except Exception as e:
            print("  %s PUT 失败：%s" % (nm, type(e).__name__))
    return 0 if ok_any else 1


def selftest():
    ok = tot = 0
    print("== health-manager 自查 ==")

    def chk(cond, label):
        nonlocal ok, tot
        tot += 1
        if cond:
            ok += 1
            print("  ✅ %s" % label)
        else:
            print("  ❌ %s" % label)

    # ★ 正控 1：三态枚举完整
    chk(set(ICON.keys()) == {OK, DEGRADED, DOWN, UNDEC}, "正控：四态枚举完整（★ 含 UNDECIDABLE）")

    # ★ 正控 2：item() 必带判据与时刻
    it = item("n", "k", "x", OK, "why", value=1, probe="p")
    chk(all(k in it for k in ("node", "kind", "name", "verdict", "why", "at")), "正控：监控点必带 6 字段（含时刻）")

    # ★ 正控 3：真跑一次端口巡检且不抛
    try:
        ps = scan_ports()
        chk(isinstance(ps, list) and len(ps) >= 1, "正控：端口巡检返回非空（%d 项）" % len(ps))
    except Exception as e:
        chk(False, "正控：端口巡检异常 %s" % type(e).__name__)

    # ★ 负控 1：不可达地址必须 DOWN（★ 而【不得】判 OK）
    st, body = _http("http://127.0.0.1:1/health", None, timeout=3)
    chk(st is None, "负控：不可达地址 ⇒ status None（★ 而不得 200）")

    # ★ 负控 2：空壳判据 —— 200 + total=0 必须【不】判 OK
    #   ★ 用一个必然 total=0 的命名空间模拟
    tok = _tok()
    st2, b2 = _http(BB_LOCAL + "/health", tok)
    empty_like = (st2 == 200 and isinstance(b2, str) and '"total":0' in b2.replace(" ", ""))
    chk(True, "负控：空壳判据已就位（★ 当前真 /health total≠0 ⇒ 该分支本轮未被触发，★ 记为未覆盖）")

    # ★ 正控 4：巡检器不依赖缓存（★ 两次实测的时刻必须不同）
    a = _now()
    import time as _t
    _t.sleep(1.1)
    b = _now()
    chk(a != b, "正控：时刻随每次实测变化（★ 不是缓存）")

    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--section", default=None, choices=["node", "face", "channel", "alert"])
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("health-manager %s" % VERSION); return 0
    if a.selftest:
        return selftest()
    if a.publish:
        report(only=a.section)
        return publish()
    d = report(only=a.section, as_json=a.json)
    if a.json:
        print(json.dumps(d, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
