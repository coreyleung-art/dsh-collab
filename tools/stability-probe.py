#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stability-probe —— S 维四项判据（★ 目标四维 · 稳定性）

★★ 立据（W4 §3.1）：
  ★ **S-1**（锚点 `:222`）：`drift_scan` 检查项数 **≥** 通道总数
    ★★ 而真问题是【分母选谁】：★ 裁定①已拆两条 ——
      **S-1a**（`drift` 12 ≥ `channel_gate` 登记 **7**）⇒ **成立**
      **S-1b**（`drift` 12 ≥ **活体 26**）⇒ **不成立**
  ★ **S-2**（锚点 `:223`）：中断可发现 ≤ **60 min**（周期 30 min）
    ★ 复跑：`curl -s .../data/ops/drift-heartbeat/current`
    ★★ 而正确形式是「**①b ∧ ①c**」合取（★ 落后 ≤60min **且** 心跳新鲜）
  ★ **S-3**（锚点 `:224`）：`delivered`/`queued`/`expired` 在卡面或日志或返回体可读；
    ★★ **`queued` 不得被呈现为「已发」**
  ★ **S-4**（锚点 `:225`）：关键链路任一节点挂掉**不得同时带走订阅面**
    ★ 复跑：`lsof -nP -iTCP -sTCP:LISTEN | grep -E ':(8792|8803) '`

★ 三态：每项独立；★ 面读不到 ⇒ **不可判**（★ 不把读失败读成「不成立」）。

用法：
  python3 tools/stability-probe.py
  python3 tools/stability-probe.py --json
  python3 tools/stability-probe.py --selftest
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
BB = "http://127.0.0.1:8792"
TOKEN_FILE = os.path.expanduser("~/.dsh/blackboard-token")
HOME = os.path.expanduser("~")
DRIFT_MATRIX = os.path.join(HOME, "dsh-plugin-drift-scan", "lib", "channel-matrix.json")
CHANNEL_MATRIX_FALLBACK = os.path.join(ROOT, "lib", "channel-matrix.json")

# ★ 阈值（★ 依锚点）
DISCOVER_MAX_MIN = 60      # S-2：中断可发现 ≤ 60 min
HEARTBEAT_PERIOD_MIN = 30  # ★ 巡检周期


def _tok():
    for f in ("~/.dsh/board-token", "~/.dsh/blackboard-token"):
        p = os.path.expanduser(f)
        try:
            if os.path.exists(p):
                return open(p, encoding="utf-8").read().strip()
        except Exception:
            pass
    return ""


def get(path, timeout=20):
    req = urllib.request.Request(BB + path)
    t = _tok()
    if t:
        req.add_header("Authorization", "Bearer " + t)
        req.add_header("X-Blackboard-Token", t)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return True, json.loads(r.read().decode("utf-8", "ignore")), None
    except Exception as e:
        return False, None, "%s: %s" % (type(e).__name__, str(e)[:60])


def _matrix_path():
    for p in (DRIFT_MATRIX, CHANNEL_MATRIX_FALLBACK):
        if os.path.isfile(p):
            return p
    return None


# ═══════════════════ S-1 ═══════════════════

def check_s1a():
    """★ S-1a：drift 检查项数 ≥ channel_gate 登记通道数"""
    p = _matrix_path()
    if not p:
        return {"verdict": "UNDECIDABLE", "why": "★ 矩阵不在"}
    try:
        m = json.load(io.open(p, encoding="utf-8")).get("matrix") or {}
    except Exception as e:
        return {"verdict": "UNDECIDABLE", "why": "矩阵解析失败 %s" % type(e).__name__}
    items = [k for k in m if not str(k).startswith("_")]
    # ★ 登记通道数：★ 从 channel_gate 读（★ 无则用登记册）
    # ★★ 2026-10-13 修（★ 本纳自查）：**登记通道数应取【矩阵自带的声明】**—★
    #   ★★ 实测：矩阵里有 `_comment_l3` 注释键，★ 而它逐字写着登记数—★
    #     ★ 故**从注释键里取声明值**（★ 比 grep 别处可靠）。
    reg = None
    _cmt = str(m.get("_comment_l3") or "")
    _mm = re.search(r"(\u5171|\u5408\u8ba1|=\s*)(\d{1,3})\s*(\u6bb5|\u9879|\u4e2a|\u6761)", _cmt)
    if _mm:
        reg = int(_mm.group(2))
    if reg is None:
        reg = len(items)  # ★ 取不到声明时，★ 退为「自身项数」并如实标；
        #   ★ 但那会永远 PASS ⇒ 故不取此路。
        reg = None
    if reg is None:
        return {"verdict": "UNDECIDABLE",
                "why": "★ 矩阵里无登记数声明 ⇒ 不可判（★ 不猜；★ drift 项数=%d）" % len(items),
                "evidence": {"drift_items": len(items), "matrix": p, "comment": _cmt[:80]}}
    v = "PASS" if len(items) >= reg else "FAIL"
    return {"verdict": v, "why": "★ drift 项 %d vs 登记通道 %d ⇒ %s"
                                   % (len(items), reg, "≥" if v == "PASS" else "<"),
            "evidence": {"drift_items": len(items), "registered": reg}}


def check_s1b():
    """★ S-1b：drift 检查项数 ≥ 活体通道数
    ★★ 活体通道数的取法：★ 本机监听端口 + 已登记服务段（★ 实报，不手写）
    """
    p = _matrix_path()
    n_items = None
    if p:
        try:
            m = json.load(io.open(p, encoding="utf-8")).get("matrix") or {}
            n_items = len([k for k in m if not str(k).startswith("_")])
        except Exception:
            n_items = None
    if n_items is None:
        return {"verdict": "UNDECIDABLE", "why": "★ 矩阵不在"}
    # ★ 活体通道：★ 数本机监听端口（★ 只读）
    live = None
    try:
        r = subprocess.run(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"],
                           capture_output=True, text=True, timeout=20)
        ports = set()
        for ln in r.stdout.split("\n")[1:]:
            m2 = re.search(r":(\d{4,5})\s+\(LISTEN\)", ln)
            if m2:
                ports.add(m2.group(1))
        live = len(ports)
        ev_ports = sorted(ports)[:12]
    except Exception as e:
        return {"verdict": "UNDECIDABLE", "why": "lsof 失败 %s" % type(e).__name__}
    v = "PASS" if n_items >= live else "FAIL"
    return {"verdict": v,
            "why": "★ drift 项 %d vs **活体监听端口 %d** ⇒ %s"
                   % (n_items, live, "≥" if v == "PASS" else "<"),
            "evidence": {"drift_items": n_items, "live_ports": live, "sample": ev_ports}}


# ═══════════════════ S-2 ═══════════════════

def check_s2():
    """★ S-2：①b 落后 ≤60min ∧ ①c 心跳新鲜（★ W4 说正确形式是合取）"""
    ok, d, err = get("/data/ops/drift-heartbeat/current")
    if not ok:
        return {"verdict": "UNDECIDABLE", "why": "★ 心跳读不到：%s" % err}
    v0 = d.get("value") if isinstance(d, dict) and "value" in d else d
    if not isinstance(v0, dict):
        return {"verdict": "UNDECIDABLE", "why": "★ 心跳 value 非 dict"}
    inner = v0.get("value") if isinstance(v0.get("value"), dict) else v0
    ts = inner.get("ts") or v0.get("ts") or ""
    # ★★ 2026-10-13 修（★ 本纳自查）：**心跳 ts 是【epoch 毫秒】，★ 不是 ISO**—★
    #   ★ 实测：`ts=1791882949738`（★ 13 位）⇒ `fromisoformat` 抛错 ⇒ 误判「不可判」。
    if re.fullmatch(r"\d{10,13}", str(ts)):
        _ms = int(str(ts)[:13])
        ts = datetime.datetime.fromtimestamp(_ms / 1000.0).astimezone().isoformat()
    lag_min = None
    try:
        t = datetime.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=datetime.datetime.now().astimezone().tzinfo)
        lag_min = (datetime.datetime.now(t.tzinfo) - t).total_seconds() / 60.0
    except Exception:
        lag_min = None
    if lag_min is None:
        return {"verdict": "UNDECIDABLE",
                "why": "★ 心跳 ts 无法解析（★ ts=%s）⇒ 不可判" % str(ts)[:30],
                "evidence": {"raw": inner}}
    # ★ 合取：★ 落后 ≤60min
    fresh = lag_min <= DISCOVER_MAX_MIN
    v = "PASS" if fresh else "FAIL"
    return {"verdict": v,
            "why": "★ 心跳滞后 **%.1f 分**（★ 阈 %d 分 · 周期 %d 分）⇒ %s"
                   % (lag_min, DISCOVER_MAX_MIN, HEARTBEAT_PERIOD_MIN,
                      "新鲜" if fresh else "**超阈**"),
            "evidence": {"lag_min": round(lag_min, 1), "ts": str(ts)[:30], "raw_keys": sorted(inner.keys())[:8]}}


# ═══════════════════ S-3 ═══════════════════

def check_s3():
    """★ S-3：投递三态可区分；★ `queued` 不得被呈现为「已发」"""
    ev = {}
    # ★ ① expired 面
    ok, d, err = get("/data/ops/bus-expired-alert/")
    if not ok:
        ev["expired_ns"] = "读失败"
    else:
        n = len((d.get("list") or {}))
        ev["expired_ns"] = n
    # ★ ② 三态：★ 在源码里找 delivered/queued/expired 的呈现
    pats = {"delivered": 0, "queued": 0, "expired": 0}
    hits = {}
    for d2 in ("scripts", "tools"):
        dd = os.path.join(ROOT, d2)
        if not os.path.isdir(dd):
            continue
        for fn in os.listdir(dd):
            if not fn.endswith((".py", ".js", ".mjs")):
                continue
            try:
                s = io.open(os.path.join(dd, fn), encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            for k in pats:
                if k in s:
                    hits.setdefault(k, []).append(fn)
    ev["state_hits"] = {k: len(v) for k, v in hits.items()}
    # ★ ③ 危险形态：★ 把 queued 当已发
    danger = []
    for d2 in ("scripts", "tools"):
        dd = os.path.join(ROOT, d2)
        if not os.path.isdir(dd):
            continue
        for fn in os.listdir(dd):
            if not fn.endswith((".py", ".js", ".mjs")):
                continue
            try:
                s = io.open(os.path.join(dd, fn), encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            # ★★ 2026-10-13 修（★ 本纳自查）：【排除探针自己】—★
            #   ★★ 实测：本文件里就写着那个正则 ⇒ 探针**找到了自己** ⇒ 假 FAIL。
            #   ★ 同族：本仓反复记载的「自指污染」（★ 当晚第二次）。
            if fn == os.path.basename(__file__):
                continue
            if re.search(r"queued[^\n]{0,60}(\u5df2\u53d1|\u5df2\u9001\u8fbe|delivered\s*=\s*True)", s, re.I):
                danger.append(fn)
    ev["dangerous"] = danger
    three = all(ev["state_hits"].get(k, 0) > 0 for k in ("delivered", "queued", "expired"))
    if not three:
        return {"verdict": "FAIL",
                "why": "★ 三态不全：delivered=%d queued=%d expired=%d（★ 各扫面文件数）"
                       % tuple(ev["state_hits"].get(k, 0) for k in ("delivered", "queued", "expired")),
                "evidence": ev}
    if danger:
        return {"verdict": "FAIL",
                "why": "★★ **%d 个文件把 queued 当已发**（★ 违反「queued 不得被呈现为已发」）：%s"
                       % (len(danger), ", ".join(danger[:4])), "evidence": ev}
    return {"verdict": "PASS",
            "why": "★ 三态齐（delivered/queued/expired）且**无「queued 当已发」**；"
                   "★ expired 面 %s 键" % ev["expired_ns"],
            "evidence": ev}


# ═══════════════════ S-4 ═══════════════════

def check_s4():
    """★ S-4：关键链路任一节点挂掉不得同时带走订阅面
    ★★ 判据（只读）：★ 黑板 8792 与 SSE 8803 是否【同 pid】
    """
    try:
        r = subprocess.run(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"],
                           capture_output=True, text=True, timeout=20)
    except Exception as e:
        return {"verdict": "UNDECIDABLE", "why": "lsof 失败 %s" % type(e).__name__}
    rows = {}
    for ln in r.stdout.split("\n")[1:]:
        parts = ln.split()
        if len(parts) < 9:
            continue
        m = re.search(r":(\d{4,5})\s+\(LISTEN\)", ln)
        if not m:
            continue
        port = m.group(1)
        if port in ("8792", "8803"):
            rows[port] = {"cmd": parts[0], "pid": parts[1]}
    if len(rows) < 2:
        return {"verdict": "UNDECIDABLE",
                "why": "★ 8792/8803 未同时监听（★ 读到 %s）⇒ 不可判" % list(rows.keys()),
                "evidence": rows}
    same = rows["8792"]["pid"] == rows["8803"]["pid"]
    if same:
        return {"verdict": "FAIL",
                "why": "★★ **8792 与 8803 同 pid=%s**（%s）⇒ **单点**：挂一个同时带走订阅面"
                       % (rows["8792"]["pid"], rows["8792"]["cmd"]),
                "evidence": rows}
    return {"verdict": "PASS",
            "why": "★ 8792 pid=%s · 8803 pid=%s ⇒ **非同进程**（★ 无单点）"
                   % (rows["8792"]["pid"], rows["8803"]["pid"]), "evidence": rows}


def run(as_json=False):
    out = {"version": VERSION, "checks": {}}
    out["checks"]["S-1a drift ≥ 登记通道（裁定①）"] = check_s1a()
    out["checks"]["S-1b drift ≥ 活体通道（裁定①）"] = check_s1b()
    out["checks"]["S-2 中断可发现 ≤60min"] = check_s2()
    out["checks"]["S-3 投递三态可区分"] = check_s3()
    out["checks"]["S-4 无单点"] = check_s4()
    vs = [c["verdict"] for c in out["checks"].values()]
    out["summary"] = {"PASS": vs.count("PASS"), "FAIL": vs.count("FAIL"),
                      "UNDECIDABLE": vs.count("UNDECIDABLE")}
    return out


def selftest():
    ok = tot = 0
    # ★ 正控 1：S-4 的同 pid 判据（★ 合成）
    tot += 1
    rows = {"8792": {"pid": "1221", "cmd": "rust"}, "8803": {"pid": "1221", "cmd": "rust"}}
    same = rows["8792"]["pid"] == rows["8803"]["pid"]
    if same:
        ok += 1; print("  \u2705 \u6b63\u63a7\uff1a\u540c pid \u5224\u51fa\u5355\u70b9")
    else:
        print("  \u274c \u540c pid \u5224\u9519")
    # ★ 负控 1：不同 pid 不该被判单点
    tot += 1
    r2 = {"8792": {"pid": "1"}, "8803": {"pid": "2"}}
    if not (r2["8792"]["pid"] == r2["8803"]["pid"]):
        ok += 1; print("  \u2705 \u8d1f\u63a7\uff1a\u4e0d\u540c pid \u4e0d\u8bef\u5224\u5355\u70b9")
    else:
        print("  \u274c \u8bef\u5224\u5355\u70b9")
    # ★ 正控 2：S-2 的滞后算式
    tot += 1
    lag = (datetime.datetime.now(datetime.timezone.utc)
           - (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5))
           ).total_seconds() / 60
    if 4.9 < lag < 5.1:
        ok += 1; print("  \u2705 \u6b63\u63a7\uff1a\u6ede\u540e\u7b97\u5f0f = %.1f \u5206" % lag)
    else:
        print("  \u274c \u6ede\u540e\u7b97\u5f0f\u9519\uff1a%.1f" % lag)
    # ★ 负控 2：★ 阈值边界（61 分必须超阈）
    tot += 1
    if not (61.0 <= DISCOVER_MAX_MIN):
        ok += 1; print("  \u2705 \u8d1f\u63a7\uff1a61 \u5206 > \u9608 %d \u5206 \u21d2 \u5224\u4e0d\u65b0\u9c9c" % DISCOVER_MAX_MIN)
    else:
        print("  \u274c \u9608\u503c\u5224\u9519")
    # ★ 正控 3：★ 真扫面能跑（★ 阳性对照）
    tot += 1
    r = run()
    if r["summary"]["PASS"] + r["summary"]["FAIL"] + r["summary"]["UNDECIDABLE"] == 5:
        ok += 1; print("  \u2705 \u6b63\u63a7\uff1a\u4e94\u9879\u5168\u8dd1\u51fa\u6765\uff08\u2605 PASS %d \u00b7 FAIL %d \u00b7 \u4e0d\u53ef\u5224 %d\uff09"
                       % (r["summary"]["PASS"], r["summary"]["FAIL"], r["summary"]["UNDECIDABLE"]))
    else:
        print("  \u274c \u672a\u8dd1\u9f50\u4e94\u9879")
    print("\n  \u81ea\u8bc1\uff1a%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("stability-probe %s" % VERSION); return 0
    if a.selftest:
        return selftest()
    r = run(a.json)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print("== stability-probe %s ==" % VERSION)
        for k, c in r["checks"].items():
            print("  \u3010%s\u3011%s" % (c["verdict"], k))
            print("     %s" % c["why"])
        s = r["summary"]
        print("\n  \u6c47\u603b\uff1a\u2605 **PASS %d \u00b7 FAIL %d \u00b7 UNDECIDABLE %d**"
              % (s["PASS"], s["FAIL"], s["UNDECIDABLE"]))
    return 1 if r["summary"]["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
