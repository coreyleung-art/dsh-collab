#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cld-monitor — CLD 实时状态监控器（比事后翻日志更好的修理工具）
被动只读（绝不修改 CLD/dsh 任何文件），把分散的故障信号汇聚成
一份状态快照 + 主动告警，异常时推黑板 notes/mac-mini/cld-monitor-alert-*。

信号源（全部只读）：
  进程     CLD 主进程 + dsh 子进程存活          → ps
  心跳     ~/.cld/logs/heartbeat.json 新鲜度    → <90s=活
  退出态   ~/.cld/logs/exit-marker.json         → cleanExit/reason
  崩溃     crash-reason.log 增量(游标)          → 新行即告警
  内存     memory-trend.json 最新行(rss/heap)   → rss 突增/超阈告警(OOM前兆)
  web      dsh-web.log 解析最新端口 → HTTP GET  → 200=活
  doctor   doctor-state.json 数 healthy verdict  → 骤降告警
  会话     sessions 递归数 session.jsonl.zstd    → 骤降告警
  workspace workspace.json sessionIds 数         → 对照

用法：
  python3 cld-monitor.py --once            # 单次快照+告警评估(stdout + state.json)
  python3 cld-monitor.py --watch 30        # 常驻每 30s（launchd/crontab 亦可用 --once）
  python3 cld-monitor.py --once --alert-board  # 有告警时推黑板(读 ~/.dsh/.env token)
状态/告警落盘： ~/.cld/logs/cld-monitor/{state.json,alerts.jsonl,cursor.json}
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

HOME = os.path.expanduser("~")
LOG_DIR = os.path.join(HOME, ".cld", "logs")
MON_DIR = os.path.join(LOG_DIR, "cld-monitor")
STATE_FILE = os.path.join(MON_DIR, "state.json")
ALERTS_FILE = os.path.join(MON_DIR, "alerts.jsonl")
CURSOR_FILE = os.path.join(MON_DIR, "cursor.json")
SESSIONS_ROOT = os.path.join(HOME, ".dsh", "sessions")
WORKSPACE_JSON = os.path.join(HOME, ".dsh", "storages", "workspace.json")
DOCTOR_STATE = os.path.join(HOME, ".cld", "doctor-state.json")

RSS_WARN_MB = 2000        # rss 超此告警（OOM 前兆，堆上限 4001MB）
RSS_DELTA_MB = 500        # 相邻采样 rss 增量超此告警
HEARTBEAT_STALE_S = 90
HEALTHY_BASELINE = 191    # doctor healthy 基线


def read_json(fp, fallback=None):
    try:
        return json.load(open(fp))
    except Exception:
        return fallback


def read_tail(fp, n=5):
    try:
        with open(fp, "r", errors="ignore") as f:
            lines = f.readlines()
        return "".join(lines[-n:]).strip()
    except Exception:
        return ""


def pgrep(pattern):
    try:
        out = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True, timeout=5)
        return [p for p in out.stdout.split() if p]
    except Exception:
        return []


def newest_port_from_log():
    """从 dsh-web.log 提取最新 'dsh web: http://127.0.0.1:PORT'"""
    try:
        with open(os.path.join(LOG_DIR, "dsh-web.log"), "r", errors="ignore") as f:
            for line in reversed(f.readlines()):
                m = re.search(r"dsh web: http://127\.0\.0\.1:(\d+)", line)
                if m:
                    return int(m.group(1))
    except Exception:
        pass
    return None


def http_ok(port):
    if not port:
        return None
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/", method="GET")
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.status
    except Exception as e:
        return f"ERR:{type(e).__name__}"



def is_shell_main(pid_str):
    """区分壳主进程(纯 GUI)与 dsh 运行实例(带 --expose-internals)。
    只认 /Applications/CLD.app 开头的真实 CLD 二进制(排除 bash -c 等含路径文本的干扰)。"""
    try:
        out = subprocess.run(["ps", "-p", str(pid_str), "-o", "command="], capture_output=True, text=True, timeout=5).stdout or ""
        out = out.strip()
        # 真实 CLD: 命令以 /Applications/CLD.app 开头(非 bash/python 等包裹)
        if not out.startswith("/Applications/CLD.app"):
            return False
        return "--expose-internals" not in out and "bin.js" not in out
    except Exception:
        return False

def dsh_rss_mb():
    """采样 dsh 进程 RSS(消除盲区: 现只监控壳 162MB, dsh 3.6GB 看不到)"""
    try:
        pids = pgrep(r"dsh/lib/bin\.js web")
        if not pids:
            return None
        out = subprocess.run(["ps", "-o", "rss=", "-p", pids[0]], capture_output=True, text=True, timeout=5)
        val = int(out.stdout.strip())
        return val // 1024
    except Exception:
        return None


def count_sessions():
    total = 0
    try:
        for ws in os.listdir(SESSIONS_ROOT):
            if ws.startswith("."):
                continue
            wdir = os.path.join(SESSIONS_ROOT, ws)
            if not os.path.isdir(wdir):
                continue
            for sess in os.listdir(wdir):
                if os.path.isfile(os.path.join(wdir, sess, "session.jsonl.zstd")):
                    total += 1
    except Exception:
        pass
    return total


def shade_count():
    """C7: profile @deepseek-ai 真目录遮蔽 runtime 的包数（>0 即告警）"""
    import json as _j
    PROF = os.path.expanduser("~/.dsh/profiles/web/node_modules/@deepseek-ai")
    RUNT = "/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai"
    n = 0
    try:
        for name in os.listdir(PROF):
            if ".bak" in name or ".pnpmcopy" in name:
                continue
            pdir = os.path.join(PROF, name)
            if not os.path.isdir(pdir) or os.path.islink(pdir):
                continue
            try:
                pv = _j.load(open(os.path.join(pdir, "package.json"))).get("version")
            except Exception:
                continue
            rdir = os.path.join(RUNT, name)
            rv = None
            if os.path.exists(os.path.join(rdir, "package.json")):
                try:
                    rv = _j.load(open(os.path.join(rdir, "package.json"))).get("version")
                except Exception:
                    pass
            if rv is None or pv != rv:
                n += 1
    except Exception:
        pass
    return n


def doctor_healthy():
    d = read_json(DOCTOR_STATE, {})
    if not isinstance(d, dict):
        return None
    n = 0
    for k, v in d.items():
        if isinstance(v, dict) and v.get("verdict") == "healthy":
            n += 1
    return n


def workspace_session_ids():
    d = read_json(WORKSPACE_JSON, {})
    try:
        n = 0
        for wid, w in d.get("tables", {}).get("workspaces", {}).items():
            n += len(w.get("sessionIds", []))
        return n
    except Exception:
        return None


def crash_reason_new(cursor):
    """crash-reason.log 增量：返回自游标以来的新行列表。
    首次运行(游标缺 baseline 标记)时只设基线不告警，避免把历史当新崩溃。"""
    try:
        with open(os.path.join(LOG_DIR, "crash-reason.log"), "r", errors="ignore") as f:
            lines = f.read().splitlines()
    except Exception:
        return [], cursor
    if "baselined" not in cursor:
        cursor["baselined"] = True
        cursor["crash_reason_len"] = len(lines)
        return [], cursor
    prev_len = cursor.get("crash_reason_len", len(lines))
    new = lines[prev_len:] if len(lines) >= prev_len else lines
    cursor["crash_reason_len"] = len(lines)
    return new, cursor


def collect():
    snap = {"ts": time.time(), "iso": time.strftime("%Y-%m-%d %H:%M:%S")}
    # 进程
    snap["proc_cld"] = pgrep(r"CLD\.app/Contents/MacOS/CLD( |$)")
    snap["proc_dsh"] = pgrep(r"dsh/lib/bin\.js web")
    snap["cld_alive"] = len(snap["proc_cld"]) > 0
    snap["dsh_alive"] = len(snap["proc_dsh"]) > 0
    snap["dsh_rss_mb"] = dsh_rss_mb()
    # 心跳
    hb = read_json(os.path.join(LOG_DIR, "heartbeat.json"))
    if hb and hb.get("ts"):
        snap["heartbeat_age_s"] = round(time.time() * 1000 - hb["ts"]) // 1000
    else:
        snap["heartbeat_age_s"] = None
    # 退出态（运行中 marker 为 cleanExit:false + note:boot，非崩溃）
    em = read_json(os.path.join(LOG_DIR, "exit-marker.json"))
    snap["exit_clean"] = em.get("cleanExit") if em else None
    snap["exit_reason"] = em.get("reason") if em else None
    snap["exit_ended"] = em.get("endedAt") if em else None
    # 内存趋势最新行（NDJSON：每行一个对象，取最后一行）
    mt = None
    try:
        with open(os.path.join(LOG_DIR, "memory-trend.json"), "r", errors="ignore") as f:
            lines = [l for l in f.read().splitlines() if l.strip()]
        if lines:
            mt = json.loads(lines[-1])
    except Exception:
        pass
    snap["mem"] = mt
    # web
    port = newest_port_from_log()
    snap["web_port"] = port
    snap["web_http"] = http_ok(port) if port else None
    # doctor / 会话 / 遮蔽(C7: 27遮蔽事故后必查)
    snap["doctor_healthy"] = doctor_healthy()
    snap["shade_count"] = shade_count()
    snap["sessions_disk"] = count_sessions()
    snap["workspace_session_ids"] = workspace_session_ids()
    # crash-reason 增量
    cursor = read_json(CURSOR_FILE, {})
    new_crash, cursor = crash_reason_new(cursor)
    snap["crash_new_lines"] = new_crash
    save_cursor(cursor)
    # 日志错误模式尾扫：只扫最近一次 "CLD boot" 之后的段（历史崩溃段不算当前告警）
    try:
        with open(os.path.join(LOG_DIR, "dsh-web.log"), "r", errors="ignore") as f:
            log_text = f.read()
        idx = log_text.rfind("===== CLD boot")
        current_seg = log_text[idx:] if idx >= 0 else log_text[-20000:]
        tail = current_seg[-20000:]
    except Exception:
        tail = ""
    fatal_pats = ["plugin tree failed", "failed to load", "Fatal process", "SIGABRT", "ERR_MODULE_NOT_FOUND", "Cannot read properties", "dsh-crash"]
    snap["log_fatal_hits"] = [p for p in fatal_pats if p.lower() in tail.lower()]
    return snap


def save_cursor(cursor):
    try:
        os.makedirs(MON_DIR, exist_ok=True)
        json.dump(cursor, open(CURSOR_FILE, "w"))
    except Exception:
        pass


def evaluate(snap, prev):
    """返回告警列表。prev = 上一次快照(内存趋势比较用)。"""
    alerts = []
    if not snap.get("cld_alive"):
        alerts.append({"sev": "critical", "msg": "CLD 主进程不在!"})
    if not snap.get("dsh_alive"):
        alerts.append({"sev": "critical", "msg": "dsh 子进程不在!"})
    ha = snap.get("heartbeat_age_s")
    if ha is not None and ha > HEARTBEAT_STALE_S:
        alerts.append({"sev": "warn", "msg": f"heartbeat 过期 {ha}s (> {HEARTBEAT_STALE_S}s) — 可能卡死/崩溃"})
    if snap.get("web_port") and snap.get("web_http") != 200:
        alerts.append({"sev": "warn", "msg": f"web :{snap['web_port']} HTTP={snap['web_http']}"})
    # 退出非 clean：仅当有明确崩溃 reason（且已 endedAt）才算异常；运行中(note:boot/无endedAt)不算
    if snap.get("exit_clean") is False and snap.get("exit_reason") and snap.get("exit_ended"):
        alerts.append({"sev": "warn", "msg": f"上次退出非 clean: reason={snap.get('exit_reason')}"})
    for line in snap.get("crash_new_lines") or []:
        up = line.upper()
        if "CRASH" in up or "DID NOT EXIT CLEANLY" in up or "UNCAUGHTEXCEPTION" in up or "DSH-CRASH" in up:
            alerts.append({"sev": "critical", "msg": f"崩溃记录: {line[:150]}"})
    m = snap.get("mem")
    if m and m.get("rss_mb") is not None:
        if m["rss_mb"] > RSS_WARN_MB:
            alerts.append({"sev": "warn", "msg": f"rss {m['rss_mb']}MB > {RSS_WARN_MB}MB (OOM 前兆)"})
        pm = (prev or {}).get("mem")
        if pm and pm.get("rss_mb") and m["rss_mb"] - pm["rss_mb"] > RSS_DELTA_MB:
            alerts.append({"sev": "warn", "msg": f"rss 突增 +{m['rss_mb'] - pm['rss_mb']}MB (上一采样 {pm['rss_mb']}MB)"})
        if m.get("used_heap_mb") is None:
            alerts.append({"sev": "info", "msg": "heap 字段为 null（壳版本旧，需 S5fix: node:v8）"})
    # dsh RSS 监控(2026-09-06: 消除盲区; cage 4GB 硬顶, 3GB 以上逼近)
    dsh_rss = snap.get("dsh_rss_mb")
    if dsh_rss is not None and dsh_rss > 3000:
        alerts.append({"sev": "warn", "msg": f"dsh RSS {dsh_rss}MB > 3GB (cage 4GB 的 75%+, 建议 GC/重启)"})
    elif dsh_rss is not None and dsh_rss > 3500:
        alerts.append({"sev": "critical", "msg": f"dsh RSS {dsh_rss}MB > 3.5GB (cage 硬顶危险区!)"})
    # 多实例守护(2026-09-06: 孤儿 81555 与 7460 并存 → 端口冲突+弹浏览器事故)
    # 只统计"壳主进程"(纯 GUI 壳, 无 --expose-internals; dsh 子进程 CLD --expose... 不算)
    cld_procs = snap.get("proc_cld") or []
    shell_procs = [p2 for p2 in cld_procs if p2 and is_shell_main(p2)]
    if len(shell_procs) > 1:
        alerts.append({"sev": "critical", "msg": f"CLD 多实例 {len(shell_procs)} 个: {shell_procs}（端口冲突/弹浏览器根因, 保留最新 pid 杀其余）"})
    sc = snap.get("shade_count")
    if sc and sc > 0:
        alerts.append({"sev": "critical", "msg": f"profile 遮蔽 runtime {sc} 个包(rc.6/7 vs rc.2)! 核心包遮蔽=会话空根因, 立即 guard-check-deps 清理"})
    dh = snap.get("doctor_healthy")
    if dh is not None and dh < HEALTHY_BASELINE:
        alerts.append({"sev": "warn", "msg": f"doctor healthy {dh} < 基线 {HEALTHY_BASELINE}"})
    sd = snap.get("sessions_disk")
    if sd is not None and 0 < sd < 100:  # 骤降(但 0=可能空库不告警)
        alerts.append({"sev": "warn", "msg": f"会话骤降: 磁盘仅 {sd}（基线≈{HEALTHY_BASELINE}）"})
    if snap.get("log_fatal_hits"):
        alerts.append({"sev": "warn", "msg": f"日志致命串: {snap['log_fatal_hits']}"})
    return alerts


def grab_evidence(alerts):
    """异常时自动抓 UI 证据(/dom 文本 + /shot 截图)供后续分析"""
    sev = [a.get("sev") for a in alerts]
    if not any(s in ("critical", "warn") for s in sev):
        return None
    ev_dir = os.path.join(MON_DIR, "evidence")
    os.makedirs(ev_dir, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    out = {"ts": ts, "alerts": alerts}
    try:
        import subprocess as _s
        dom = _s.run(["curl", "-s", "-m", "6", "http://127.0.0.1:31888/dom"],
                     capture_output=True, text=True, timeout=10)
        if dom.returncode == 0:
            try:
                out["ui_text"] = json.loads(dom.stdout).get("text", "")[:2000]
            except Exception:
                out["ui_text"] = dom.stdout[:2000]
    except Exception:
        pass
    try:
        png = os.path.join(ev_dir, f"evidence-{ts}.png")
        r = _s.run(["curl", "-s", "-m", "8", "-o", png, "http://127.0.0.1:31888/shot"],
                   capture_output=True, text=True, timeout=12)
        if os.path.exists(png) and os.path.getsize(png) > 1000:
            out["shot"] = png
    except Exception:
        pass
    with open(os.path.join(ev_dir, f"evidence-{ts}.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return out


def llm_diag_evidence(alerts, snap):
    """告警时调 guard-llm 诊断副驾：产出根因假设存 evidence（monitor×llm 联动）"""
    try:
        import subprocess as _s
        # 组诊断上下文: 关键状态 + 告警
        ctx_lines = []
        for k in ("cld_alive", "dsh_alive", "heartbeat_age_s", "web_http", "doctor_healthy", "sessions_disk", "shade_count", "exit_reason"):
            if k in snap:
                ctx_lines.append(f"{k}={snap.get(k)}")
        ui = ""
        try:
            dom = _s.run(["curl", "-s", "-m", "5", "http://127.0.0.1:31888/dom"],
                         capture_output=True, text=True, timeout=8)
            if dom.returncode == 0:
                try:
                    ui = json.loads(dom.stdout).get("text", "")[:1200]
                except Exception:
                    ui = dom.stdout[:1200]
        except Exception:
            pass
        prompt = ("CLD 监控告警，请诊断根因:\n告警: " + json.dumps(alerts, ensure_ascii=False) +
                  "\n状态: " + " ".join(ctx_lines) + "\nUI文本: " + ui +
                  "\n输出: 1)根因假设(最可能优先, 含遮蔽/服务/竞态等分类) 2)验证步骤 3)处置建议 4)还需什么证据")
        r = _s.run(["/usr/bin/python3", os.path.expanduser("~/dsh-collab/guard/tools/guard-llm"),
                    "ask", prompt, "--model", "MiniMax-M2.5-highspeed"],
                   capture_output=True, text=True, timeout=90)
        out = r.stdout[-2500:] if r.stdout else ""
        # 去掉 '=== guard-llm...===' 头
        if "===" in out:
            out = out.split("===")[-1].strip()
        ev_dir = os.path.join(MON_DIR, "evidence")
        os.makedirs(ev_dir, exist_ok=True)
        with open(os.path.join(ev_dir, "llm-diag.txt"), "a") as f:
            f.write(f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n" + out + "\n")
        return out
    except Exception as e:
        return f"llm_diag 失败: {str(e)[:150]}"


def push_board(alerts, snap):
    try:
        token = ""
        try:
            raw = open(os.path.join(HOME, ".dsh", ".env")).read()
            m = re.search(r"^BLACKBOARD_TOKEN=(.*)$", raw, re.M)
            if m:
                token = m.group(1).strip().strip('"').strip("'")
        except Exception:
            pass
        ts = time.strftime("%Y%m%d-%H%M%S")
        key = f"notes/mac-mini/cld-monitor-alert-{ts}"
        body = json.dumps({"alerts": alerts, "snap": {k: snap[k] for k in ("iso", "cld_alive", "dsh_alive", "heartbeat_age_s", "web_port", "web_http", "rss_mb" if "rss_mb" in snap else "mem", "doctor_healthy", "sessions_disk") if k in snap}, "from": "cld-monitor"}, ensure_ascii=False).encode()
        headers = {"Content-Type": "application/json", "X-Writer": "cld-monitor"}
        if token:
            headers["X-Blackboard-Token"] = token
        req = urllib.request.Request(f"http://127.0.0.1:8792/{key}", data=body, method="PUT", headers=headers)
        with urllib.request.urlopen(req, timeout=6) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)[:150]}


def run_once(board=False, prev=None):
    os.makedirs(MON_DIR, exist_ok=True)
    if prev is None:
        prev = read_json(STATE_FILE) or {}
    snap = collect()
    alerts = evaluate(snap, prev)
    snap["alerts"] = alerts
    try:
        json.dump(snap, open(STATE_FILE, "w"), indent=1)
    except Exception:
        pass
    if alerts:
        try:
            with open(ALERTS_FILE, "a") as f:
                f.write(json.dumps({"ts": snap["iso"], "alerts": alerts}) + "\n")
        except Exception:
            pass
        grab_evidence(alerts)  # 异常自动抓 UI 证据
        if os.environ.get("MONITOR_LLM_DIAG") == "1":
            diag = llm_diag_evidence(alerts, snap)
            if diag and not diag.startswith("llm_diag 失败"):
                print(f"\n🧠 [llm-diag] 诊断副驾产出:\n{diag[:1500]}")
    keys = ("iso", "cld_alive", "dsh_alive", "heartbeat_age_s", "exit_clean", "exit_reason",
            "web_port", "web_http", "mem", "doctor_healthy", "sessions_disk",
            "workspace_session_ids", "shade_count", "crash_new_lines", "log_fatal_hits", "alerts")
    print(json.dumps({k: snap.get(k) for k in keys}, ensure_ascii=False, indent=1))
    if alerts:
        print(f"\n🚨 告警 {len(alerts)} 条:")
        for a in alerts:
            print(f"  [{a['sev']}] {a['msg']}")
        if board:
            r = push_board(alerts, snap)
            print("黑板推送:", r)
    return snap


def main():
    args = sys.argv[1:]
    watch = None
    if "--watch" in args:
        try:
            watch = int(args[args.index("--watch") + 1])
        except Exception:
            watch = 30
    board = "--alert-board" in args

    if watch:
        # 常驻循环：直接内联 sleep 循环，避免递归
        prev = None
        while True:
            prev = run_once(board=board, prev=prev)
            time.sleep(watch)
    else:
        run_once(board=board)
    return 0


if __name__ == "__main__":
    sys.exit(main())
