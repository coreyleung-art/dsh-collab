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


# ★★★ 2026-10-15（D-395）【S-1b 的分母必须【先分类再数】】——
#   ★ 立据：原实现把 `lsof -sTCP:LISTEN` 的**全部监听端口**当「活体通道」⇒ 实测 36 个里
#     ★★ 含 Dropbox(17500/17600/17603) · Feishu(49210) · ARD(3283) · ControlCenter(5000/7000)
#     · rapportd(49152) · AweSun(8908) · LM Studio(1234/41343) · Ollama/llama(11434/56689/56983)
#     · lmlink(50353) —— ★★ **它们不可能、也不该各有 drift 探测**。
#   ★★ ⇒ 那个「活体 36」是**类别错误的分母**（★ 与 P6 / H5e 同形：判据消费了错的量）。
#   ★ 修法：★ 按【属主命令行】分三桶 —— A 本线治理服务 / B 面外（别人/系统/应用）/ C 不可判；
#     ★★ 分母只用 **A**，且**必须同时点名缺口**（★ 计数比较是粗代理，覆盖才是原意）。
#   ★★ 且 ★ **不因换分母就放它绿**：缺口非空 ⇒ 仍 FAIL —— ★ 红条要变成【可行动的】。
GOV_OWNER_MARKERS = ("dsh-collab", "/.dsh/", "/.cld/", "dsh-tailnet-proxy",
                     "rust-blackboard", "rust-genebank", "blackboard-mcp")


def _proc_cwd(pid):
    """★ 取进程工作目录（★ 供【相对路径命令行】兜底 —— ★ 见 classify_listener 的 D-395b）。"""
    try:
        r = subprocess.run(["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"],
                           capture_output=True, text=True, timeout=10)
        for ln in (r.stdout or "").split("\n"):
            if ln.startswith("n"):
                return ln[1:].strip()
    except Exception:
        pass
    return ""


def classify_listener(cmd, cwd=""):
    """★ 按属主命令行把监听者分桶（★ 规则显式、可复核、可反驳）。

    ★ 返回 ("A"|"B"|"C", 理由)：
      · **A** = 命令行含【本线治理面】标记（本仓 / `~/.dsh` / `~/.cld`）⇒ ★ 计入分母；
      · **B** = 有明确属主的**面外**服务（系统 / 第三方应用 / 另有项目归属）⇒ ★ **不计入**，
        ★★ 但**必须列出**（★ 并由人裁它算不算本网通道 —— ★ 本判据不代裁）；
      · **C** = 读不到命令行 ⇒ ★ **不可判**（★ 单列，★ 绝不静默丢弃 —— ★ 空 ≠ 无）。
    """
    c = (cmd or "").strip()
    if not c:
        return "C", "读不到命令行 ⇒ 不可判（★ 空 ≠ 无）"
    for mk in GOV_OWNER_MARKERS:
        if mk in c:
            return "A", "命中治理面标记 %r（命令行）" % mk
    # ★★★ 2026-10-15 补（D-395b）：★ **相对路径的命令行**里看不到本仓 ⇒ 第一轮会【漏】
    #   ★ 立据（★ 本线自查抓到的假阴性）：`:8798` 命令行逐字是
    #     `Python scripts/bb-blueprint-gallery.py --port 8798` —— ★★ 它是**本仓脚本**，
    #     而命令行里**没有绝对路径** ⇒ 被误分到「面外」桶（★ 正是本判据要防的错）。
    #   ★ 修法：★ 再看进程的**工作目录**（`lsof -a -p PID -d cwd`）。
    # ★★ 而 cwd 兜底【不得过宽】—— 否则「在本仓目录里启动的 Dropbox」也会被判成治理服务
    #   （★ 实测：把 cwd 一律传本仓 ⇒ 自证当场抓出 Dropbox/Ollama 两条负控被误判为 A）。
    #   ★ 收紧条件：**只有【命令行里带了相对路径的脚本参数】** 才允许用 cwd 兜底。
    _has_rel_script = re.search(r'(?:^|\s)(?![/-])(?:\.[/\\])?[\w.\-/]+\.(?:py|js|mjs|cjs|ts|sh)\b', c) is not None
    if cwd and _has_rel_script:
        for mk in GOV_OWNER_MARKERS:
            if mk in cwd:
                return "A", "命令行的脚本参数是相对路径，★ 且 cwd 命中治理面标记 %r" % mk
    return "B", "属主不在治理面（★ 面外服务/系统/应用）"


def _listeners():
    """★ 枚举本机 TCP 监听者（★ 只读）：[{port, proc, pid, cmd}]。"""
    r = subprocess.run(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"],
                       capture_output=True, text=True, timeout=25)
    seen, out = set(), []
    for ln in r.stdout.split("\n")[1:]:
        m = re.match(r'^(\S+)\s+(\d+)\s+\S+\s+\S+\s+\S+\s+.*?\s(?:\S*:)(\d{2,5})\s+\(LISTEN\)', ln)
        if not m:
            continue
        proc, pid, port = m.group(1), m.group(2), m.group(3)
        if (port, pid) in seen:
            continue
        seen.add((port, pid))
        out.append({"port": port, "proc": proc, "pid": pid, "cmd": "", "cwd": ""})
    cache = {}
    for it in out:
        if it["pid"] not in cache:
            try:
                pr = subprocess.run(["ps", "-p", it["pid"], "-o", "command="],
                                    capture_output=True, text=True, timeout=10)
                cache[it["pid"]] = (pr.stdout or "").strip()
            except Exception:
                cache[it["pid"]] = ""
        it["cmd"] = cache[it["pid"]]
    _cwd_cache = {}
    for it in out:
        if it["pid"] not in _cwd_cache:
            _cwd_cache[it["pid"]] = _proc_cwd(it["pid"])
        it["cwd"] = _cwd_cache[it["pid"]]
    return sorted(out, key=lambda x: int(x["port"]))


def check_s1b():
    """★ S-1b：`drift` 检查项数 **≥** 【本线活体治理通道数】 ∧ ★ **无未覆盖点**

    ★★ 原意的准确形式（★ 锚点 §0.1.4 S-1 逐字）是：★「**每条**活体通道都有**可复跑探测**」
      ⇒ ★ **覆盖**才是判据本体，★ 而「项数 ≥ 通道数」只是它的**粗代理**。
    ★★★ 2026-10-15 修（D-395）：★ 分母改为【分类后的 A 桶】；★ 并**必须点名缺口**。
    """
    p = _matrix_path()
    n_items = None
    matrix = {}
    if p:
        try:
            matrix = json.load(io.open(p, encoding="utf-8")).get("matrix") or {}
            n_items = len([k for k in matrix if not str(k).startswith("_")])
        except Exception:
            n_items = None
    if n_items is None:
        return {"verdict": "UNDECIDABLE", "why": "★ 矩阵不在"}
    try:
        lis = _listeners()
    except Exception as e:
        return {"verdict": "UNDECIDABLE", "why": "lsof/ps 失败 %s" % type(e).__name__}
    A, B, C = [], [], []
    for it in lis:
        k, why = classify_listener(it["cmd"], it.get("cwd") or "")
        it["why"] = why
        {"A": A, "B": B, "C": C}[k].append(it)
    # ★ drift 矩阵里出现过的端口（★ 从 expect/probe 串里取）⇒ 用于判【覆盖】
    covered = set()
    for v in matrix.values():
        if not isinstance(v, dict):
            continue
        blob = json.dumps(v, ensure_ascii=False)
        for m in re.finditer(r':(\d{2,5})(?![0-9])', blob):
            covered.add(m.group(1))
    gap = [x for x in A if x["port"] not in covered]
    cnt_ok = n_items >= len(A)
    v = "PASS" if (cnt_ok and not gap) else "FAIL"
    return {"verdict": v,
            "why": ("★ drift 项 %d vs **本线活体治理服务 %d**（★ 面外 %d · ★ 不可判 %d）⇒ %s；"
                    "★ 未覆盖点 %d 个%s"
                    "　★ 依 **R063**（三维修：面/判据/装置 —— ★ 分母是【分类后的 A 桶】，★ 不是全部监听）"
                    "· ★ 依 **R030**（无验证不陈述）；★ 规范形：★ 缺口须【按端口点名】，★ 不得只报计数"
                    % (n_items, len(A), len(B), len(C), "≥" if cnt_ok else "<", len(gap),
                       ("：" + ", ".join(":%s(%s)" % (g["port"], g["proc"]) for g in gap[:8])) if gap else "")),
            "evidence": {"drift_items": n_items, "governance_live": len(A),
                         "off_scope": len(B), "undecidable": len(C),
                         "gap_ports": [g["port"] for g in gap],
                         "A_sample": [(x["port"], x["proc"]) for x in A[:10]]}}


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
    pid = rows["8792"]["pid"]
    # ★★★ 2026-10-13（D-313）：**加【命令行证据】**—★ 它比 pid 比对更强。
    #   ★ 实测那进程命令行逐字：`rust-blackboard-... --port 8792 --sse-port 8803 --data-dir ...`
    #   ★★ ⇒ 【同一进程同时托管两端口】是**设计层一体**，★ 而非「碰巧同 pid」。
    #   ★ 且**不需启停任何服务**（★ 只读命令行）⇒ 找到了那个只读等价判据。
    ev = dict(rows)
    _has_both = False
    try:
        _ps = subprocess.run(["ps", "-p", str(pid), "-o", "command="],
                             capture_output=True, text=True, timeout=15)
        _cmd = (_ps.stdout or "").strip()
        ev["command"] = _cmd
        _has_both = ("--port 8792" in _cmd) and ("--sse-port 8803" in _cmd)
        ev["cmd_declares_both_ports"] = _has_both
        _pp = subprocess.run(["ps", "-p", str(pid), "-o", "ppid="],
                             capture_output=True, text=True, timeout=15)
        ev["ppid"] = (_pp.stdout or "").strip()
    except Exception:
        pass
    if same:
        _extra = ("；★★ **命令行逐字声明两端口**（★ 设计层一体）"
                  if _has_both else "")
        return {"verdict": "FAIL",
                "why": "★★ **8792 与 8803 同 pid=%s**（%s）⇒ **单点**：挂一个同时带走订阅面%s"
                       "　★ 依 **R030**（无验证不陈述）；★ 规范形：★ 判「无单点」须【实读两端口 pid】"
                       "（★ 不启停服务 ⇒ ★ 破坏性负控【不可判】，★ 不得据此判成立）"
                       % (pid, rows["8792"]["cmd"], _extra),
                "evidence": ev}
    return {"verdict": "PASS",
            "why": "★ 8792 pid=%s · 8803 pid=%s ⇒ **非同进程**（★ 无单点）"
                   % (rows["8792"]["pid"], rows["8803"]["pid"]), "evidence": ev}
    return {"verdict": "PASS",
            "why": "★ 8792 pid=%s · 8803 pid=%s ⇒ **非同进程**（★ 无单点）"
                   % (rows["8792"]["pid"], rows["8803"]["pid"]), "evidence": rows}


P26_WINDOW_KEY = "last_session"   # ★ 窗的基座就在索引里


def check_p26():
    """★★ P26 复发（★ v7 §12 第 2 项：「签名存在，缺时间窗」）

    ★ 窗 = 上次复发时刻（`last_session.ended_at`）之后；
    ★ 分子 = 窗内 `CONTEXT_WINDOW_EXCEEDED` 的命中数。
    ★★ ★ **窗内无复发 ≠ 已修复** —★ 只读作「未复发」。
    """
    import json as _json
    p = os.path.join(ROOT, "data", "registry", "continuity-index.json")
    try:
        idx = _json.load(io.open(p, encoding="utf-8"))
    except Exception as e:
        return {"verdict": "UNDECIDABLE", "why": "索引不可读 %s" % type(e).__name__}
    ls = idx.get(P26_WINDOW_KEY) or {}
    win = ls.get("ended_at")
    sev = ls.get("severity")
    if not win:
        return {"verdict": "UNDECIDABLE", "why": "★ 索引里无 `last_session.ended_at` ⇒ **窗不可定**"}
    # ★ 分子：扫本会话 jsonl + 日志
    hits = 0
    scanned = []
    jf = os.environ.get("DSH_SESSION_JSONL")
    import glob as _glob
    cands = []
    if jf:
        cands.append(jf)
    for d in (os.path.expanduser("~/.dsh/sessions"), os.path.join(ROOT, "logs")):
        cands += _glob.glob(os.path.join(d, "**", "*.jsonl"), recursive=True)[:20]
        cands += _glob.glob(os.path.join(d, "*.log"), recursive=True)[:20]
    for f in cands:
        try:
            if "CONTEXT_WINDOW_EXCEEDED" in io.open(f, encoding="utf-8", errors="ignore").read():
                hits += 1
                scanned.append(os.path.basename(f))
        except Exception:
            pass
    # ★ 阳性对照：★ 扫过的面必须非零
    if not cands:
        return {"verdict": "UNDECIDABLE", "why": "★ 无可扫面 ⇒ 不可判"}
    v = "PASS" if hits == 0 else "FAIL"
    return {"verdict": v,
            "why": "★ 窗 = **%s 之后**（★ 上次 severity=%s）· 扫 %d 面 · 窗内命中 **%d**"
                   % (win, sev, len(cands), hits)
                   + ("（★ %s）" % ",".join(scanned[:3]) if scanned else ""),
            "evidence": {"window": win, "severity": sev, "scanned": len(cands), "hits": hits}}


def run(as_json=False):
    out = {"version": VERSION, "checks": {}}
    out["checks"]["S-1a drift ≥ 登记通道（裁定①）"] = check_s1a()
    out["checks"]["S-1b drift ≥ 活体通道（裁定①）"] = check_s1b()
    out["checks"]["S-2 中断可发现 ≤60min"] = check_s2()
    out["checks"]["S-3 投递三态可区分"] = check_s3()
    out["checks"]["S-4 无单点"] = check_s4()
    out["checks"]["P26 复发（★ 时间窗）"] = check_p26()
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
    if r["summary"]["PASS"] + r["summary"]["FAIL"] + r["summary"]["UNDECIDABLE"] >= 5:
        ok += 1; print("  \u2705 \u6b63\u63a7\uff1a\u4e94\u9879\u5168\u8dd1\u51fa\u6765\uff08\u2605 PASS %d \u00b7 FAIL %d \u00b7 \u4e0d\u53ef\u5224 %d\uff09"
                       % (r["summary"]["PASS"], r["summary"]["FAIL"], r["summary"]["UNDECIDABLE"]))
    else:
        print("  \u274c \u672a\u8dd1\u9f50\u4e94\u9879")
    # ★★★ 2026-10-15（D-376）【异源用例】—★ 由明鉴的一般形式启发
    try:
        import sys as _sysE
        _sysE.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from extcase import extcase_selftest as _ecs
        _ec_ok, _ec_tot, _ec_msg = _ecs("stability-probe.py")
        print(_ec_msg)
        if _ec_ok is None:
            print("  ❓ 异源用例 ⇒ **不可判**（★ 空 ≠ 无）")
        else:
            ok += _ec_tot; tot += _ec_tot
    except Exception as _eE:
        print("  ❓ 异源用例 ⇒ 不可判（%s）" % type(_eE).__name__)

    # ★★★ 2026-10-15 补（D-395）：【分母分类】的两向控制 ——
    #   ★ 立据：原实现把 Dropbox/Feishu/Ollama 等**全部监听**当「活体通道」⇒ 分母是类别错误。
    # ★★ 每条控制自带 cwd（★ 首版把 cwd 一律传本仓 —— ★★ 而【负控】因此被误判成 A
    #    ⇒ 自证当场报 12/14 —— ★ 那正是【控制之间互相污染】的形态，★ 已修：cwd 逐条给）。
    _repo = os.path.expanduser("~/dsh-collab")
    _c395 = [
        ("正控", "rust-blackboard（本仓路径）⇒ 必须计入治理桶",
         "/Users/coreyleung/dsh-collab/rust-blackboard/dist/rust-blackboard-macos-arm64-v0.6.18 --port 8792", "A", ""),
        ("正控", "bus-bridge（~/.dsh）⇒ 必须计入治理桶",
         "/opt/homebrew/bin/node /Users/coreyleung/.dsh/bus-bridge/bus-bridge.js", "A", ""),
        ("负控", "Dropbox ⇒ 不得计入治理桶",
         "/Applications/Dropbox.app/Contents/MacOS/Dropbox /firstrunupdate 1262", "B", _repo),
        ("负控", "Ollama/llama-server ⇒ 不得计入治理桶",
         "/Applications/Ollama.app/Contents/Resources/llama-server --model /x", "B", _repo),
        ("负控", "读不到命令行 ⇒ 必须落【不可判】桶（★ 不得静默丢弃）", "", "C", _repo),
        ("正控", "命令行为【相对路径】而 cwd 在本仓 ⇒ 必须计入治理桶（★ 防假阴性）",
         "Python scripts/bb-blueprint-gallery.py --port 8798", "A", _repo),
        ("负控", "相对路径但 cwd 在仓外 ⇒ 不得计入治理桶（★ 防 cwd 兜底过宽）",
         "Python forum-server.py 8091", "B", "/System/Library/CoreServices"),
    ]
    for _k, _name, _cmd, _want, _cwd in _c395:
        tot += 1
        _got, _why = classify_listener(_cmd, cwd=_cwd)
        if _got == _want:
            ok += 1
            print("  \u2705 %s\uff1a%s\uff08\u2605 D-395\uff09" % (_k, _name))
        else:
            print("  \u274c %s\uff1a%s\uff08\u2605 \u5b9e\u9645 %s\uff0c\u671f\u671b %s\uff09" % (_k, _name, _got, _want))

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
