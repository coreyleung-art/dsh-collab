#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""node-executor.py — 通用节点值守执行器（吸收 i9-executor 设计，底座泛化）

i9 的 i9-executor.py 证明了「秒级全天候零 token 值守」：纯 HTTP 轮询（不耗 LLM token），
取到任务卡才执行（才可能调模型）。本文件将其泛化为底座通用件，供：
  · mac-mini 本地角色（轻量值守/定时巡检/事件监听兜底）
  · 未来门店节点（蓝图 3.0：每节点一个执行器，零 token 值守）
  · 任意分布式节点（MBP/门店…）

设计要点（吸收 i9 经验）：
  1. 纯标准库（http.client），跨平台（Windows/macOS/Linux）
  2. 轮询 = HTTP GET，零 token；取到卡才执行
  3. 黑板写入显式 Content-Length（i9 踩坑：Windows urllib PUT body 丢失）
  4. 单执行器原则（避免双执行器抢卡）
  5. 心跳/轮询分离（心跳保活 + 轮询取卡）
  6. 任务卡协议 v1.2+（队列：tasks/<node>/queue/<seq>，recipient 定向 v0.6）
  7. 回报自动镜像（黑板 v0.2：results/<seq> 历史可追溯）

用法（任意节点）：
  python3 node-executor.py --node-id store-01 --blackboard http://100.120.203.20:8792 --interval 15
  python3 node-executor.py --node-id local-watcher --blackboard http://127.0.0.1:8792 --interval 10 --once

动作白名单（可扩展）：shell/info/status/ollama/scan/自定义
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, sys, time, subprocess, datetime, platform
import urllib.parse, http.client
from concurrent.futures import ThreadPoolExecutor

DEFAULT_BB = "http://100.120.203.20:8792"
NODE = "node"
CONFIG = {"poll_interval_s": 15, "timeout_s": 300, "max_concurrent": 2}
KNOWN = {"shell", "exec", "run", "info", "status", "ollama", "scan", "数据沉淀"}
LOG = None

# ── 环境自适配层（吸收 i9 踩坑：Windows GBK / 路径分隔 / shell 差异）──
import platform as _plat
_OS = _plat.system().lower()          # windows / darwin / linux
IS_WINDOWS = _OS == "windows"
IS_MAC = _OS == "darwin"

# 1. 编码自适配：Windows 中文环境 GBK，macOS/Linux UTF-8（i9 坑 5）
def _pick_encoding():
    if IS_WINDOWS:
        try:
            import locale
            enc = locale.getpreferredencoding(False)
            if enc and enc.lower() not in ("utf-8", "utf8"):
                return enc                    # 如 cp936/GBK
        except Exception:
            pass
        return "gbk"                          # Windows 兜底 GBK
    return "utf-8"

ENCODING = _pick_encoding()

# 2. 路径自适配：Windows 反斜杠 / macOS-Linux 正斜杠
def _adapt_path(p):
    if IS_WINDOWS:
        return p.replace("/", "\\")
    return p.replace("\\", "/")

# 3. shell 风格自适配：Windows cmd / POSIX sh（命令由派卡方提供，节点按平台执行）

# 4. 输出转码：统一 UTF-8 回报（避免 GBK 乱码进黑板）
def _decode_out(b):
    """字节 → 字符串，按平台编码解码，失败回退 UTF-8"""
    if isinstance(b, bytes):
        for enc in (ENCODING, "utf-8", "latin-1"):
            try:
                return b.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return b.decode("utf-8", errors="replace")
    return str(b)

def env_report():
    """回报环境自适配信息（派卡方可见节点差异）"""
    return {"os": _OS, "encoding": ENCODING, "python": sys.version.split()[0],
            "path_style": "\\" if IS_WINDOWS else "/"}

def log(msg):
    line = "[%s] %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    if LOG:
        try:
            with open(LOG, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

def _req(method, path, data=None, timeout=15):
    """http.client 显式 Content-Length（跨平台稳定，i9 踩坑经验）"""
    u = urllib.parse.urlparse(BB)
    body = json.dumps(data, ensure_ascii=False).encode() if data is not None else None
    headers = {"Content-Type": "application/json"}
    if body is not None:
        headers["Content-Length"] = str(len(body))
    try:
        conn = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=timeout)
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        raw = resp.read().decode("utf-8", "ignore")
        conn.close()
        try:
            return resp.status, json.loads(raw)
        except Exception:
            return resp.status, {"raw": raw}
    except Exception as ex:
        return 0, {"error": str(ex)[:100]}

def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")

def register():
    caps = ["python3", "shell", "dsh"]
    return _req("PUT", "/nodes/%s" % NODE,
                {"status": "online", "capabilities": caps, "registered": True,
                 "os": platform.system(), "hostname": platform.node(), "ts": _now()})

def heartbeat():
    return _req("PUT", "/nodes/%s/heartbeat" % NODE,
                {"ts": _now(), "health": "ok", "os": platform.system(),
                 "hostname": platform.node()})

def list_queue():
    """取卡：GET /tasks?node=<id>（v0.6 收件定向）→ 按 seq 升序"""
    st, j = _req("GET", "/tasks?node=%s" % NODE)
    if st != 200 or not isinstance(j, dict):
        return []
    lst = j.get("list", {}) or {}
    entries = []
    for k, v in lst.items():
        if not (v and v.get("value")):
            continue
        seq_s = k.rsplit("/", 1)[-1]
        try:
            sortkey = int(seq_s)
        except ValueError:
            sortkey = 10 ** 18
        entries.append((sortkey, k, v["value"]))
    entries.sort(key=lambda x: x[0])
    return entries

def execute(task):
    """按 action 执行（环境自适配：编码/路径/shell）"""
    action = task.get("action", "shell")
    payload = task.get("payload", {}) or {}
    cmd = task.get("cmd") or payload.get("cmd", "")
    if action in ("shell", "exec", "run"):
        try:
            # 环境自适配：按平台编码执行，输出统一转 UTF-8 回报
            p = subprocess.run(cmd, shell=True, capture_output=True,
                               timeout=CONFIG.get("timeout_s", 300))
            out = _decode_out((p.stdout or b"")) + _decode_out((p.stderr or b""))
            return p.returncode == 0, out.strip()
        except subprocess.TimeoutExpired:
            return False, "__TIMEOUT__"
        except Exception as ex:
            return False, "exec error: %s" % str(ex)[:100]
    elif action in ("info", "status"):
        import json as _json
        return 0, _json.dumps(env_report(), ensure_ascii=False)
    elif action == "ollama":
        return 0, "ollama local (zero-subscription) node=%s" % NODE
    elif action == "scan":
        return 0, "scan stub node=%s" % NODE
    else:
        return False, "unknown action: %s" % action

def handle_task(key, task):
    tid = task.get("task_id", key.rsplit("/", 1)[-1])
    ok, output = execute(task)
    _req("PUT", "/tasks/%s/result" % NODE,
         {"task_id": tid, "ok": ok, "output": output, "node": NODE, "ts": _now()})
    _req("DELETE", "/%s" % key)
    log("DONE %s action=%s ok=%s" % (tid, task.get("action", "shell"), ok))
    return ok

def main():
    global BB, NODE, LOG
    ap = argparse.ArgumentParser()
    ap.add_argument("--node-id", default=NODE)
    ap.add_argument("--blackboard", default=DEFAULT_BB)
    ap.add_argument("--interval", type=int, default=0)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--log", default=None)
    a = ap.parse_args()
    NODE = a.node_id
    BB = a.blackboard.rstrip("/")
    LOG = a.log
    interval = a.interval or CONFIG.get("poll_interval_s", 15)
    log("node-executor start node=%s bb=%s interval=%ss（纯 HTTP 轮询，零 token）" % (NODE, BB, interval))
    st, raw = register()
    log("注册: %s" % str(raw)[:80])
    while True:
        try:
            heartbeat()
        except Exception as ex:
            log("heartbeat fail: %s" % str(ex)[:60])
        try:
            entries = list_queue()
            if entries:
                batch = entries[:CONFIG.get("max_concurrent", 2)]
                log("QUEUE %d cards, take %d" % (len(entries), len(batch)))
                with ThreadPoolExecutor(max_workers=len(batch)) as ex:
                    [ex.submit(handle_task, k, t) for _, k, t in batch]
        except Exception as ex:
            log("poll error: %s" % str(ex)[:100])
        if a.once:
            log("once done")
            break
        time.sleep(interval)

if __name__ == "__main__":
    main()
