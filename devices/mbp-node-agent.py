#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mbp-node-agent.py v1.0 — MBP 资源节点执行器（黑板任务卡协议，同 i9）

与 i9-node-agent.py 同协议（node-relationship-model），动作适配 macOS：
- shell：bash（非 cmd）
- info：system_profiler/uname/df（macOS）
- dsh：调用 MBP 上的 CLD/dsh CLI（bash 或 node bin.js）
- scan：os.walk 扫描目录
- ollama：若 MBP 有本地 Ollama（默认 127.0.0.1:11434）

用法（在 MBP 上）:
  python3 mbp-node-agent.py --node-id mbp --blackboard http://100.120.203.20:8792

任务卡协议:
  中枢 PUT /tasks/mbp/cmd  body={"task_id":"...","action":"shell|info|dsh|ollama|scan","cmd":"...","payload":{...}}
  节点 GET /tasks/mbp/cmd → 执行 → PUT /tasks/mbp/result → DELETE 清卡
"""
import argparse, json, os, sys, time, subprocess, datetime, platform
import urllib.parse, http.client

BB = "http://100.120.203.20:8792"
NODE_ID = "mbp"

# MBP CLD/dsh CLI（预设里记录的路径，探测兜底）
DSH_CLI = "/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh/lib/bin.js"

def _req(method, path, data=None, timeout=15):
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
        return json.loads(raw) if raw else {}
    except Exception as ex:
        return {"error": str(ex)[:100]}

def register():
    caps = ["m3", "dsh", "python3", "bash", "macos", "files"]
    return _req("PUT", "/nodes/%s" % NODE_ID,
                {"status": "online", "capabilities": caps,
                 "registered": True, "os": platform.system(),
                 "hostname": platform.node(), "ts": _now()})

def heartbeat():
    return _req("PUT", "/nodes/%s/heartbeat" % NODE_ID,
                {"ts": _now(), "health": "ok", "os": platform.system(),
                 "hostname": platform.node()})

def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")

def _run_shell(cmd, timeout=120):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="ignore")
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode, out.strip()
    except subprocess.TimeoutExpired:
        return 124, "__TIMEOUT__"
    except Exception as ex:
        return 1, "exec error: %s" % str(ex)[:100]

def _info():
    return _run_shell("echo ===HOST=== & hostname & uname -a & echo ===CPU/MEM=== & sysctl -n machdep.cpu.brand_string 2>/dev/null; sysctl -n hw.memsize 2>/dev/null & echo ===DISK=== & df -h / | tail -1 & echo ===LOAD=== & uptime")

def _dsh(payload):
    """调用 MBP 上的 CLD/dsh CLI"""
    cmd = payload.get("cmd", "")
    use_bash = payload.get("bash", False)
    if use_bash:
        return _run_shell(cmd, timeout=180)
    if os.path.exists(DSH_CLI):
        return _run_shell("node '%s' %s" % (DSH_CLI, cmd), timeout=180)
    return _run_shell("which dsh && dsh %s" % cmd, timeout=180)

def _ollama(payload):
    model = payload.get("model", "qwen2.5:7b")
    prompt = payload.get("prompt", "")
    body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0}}).encode()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", 11434, timeout=300)
        conn.request("POST", "/api/generate", body=body,
                     headers={"Content-Type": "application/json",
                              "Content-Length": str(len(body))})
        resp = conn.getresponse()
        raw = resp.read().decode("utf-8", "ignore")
        conn.close()
        d = json.loads(raw)
        return 0, (d.get("response") or "").strip()
    except Exception as ex:
        return 1, "ollama error: %s" % str(ex)[:100]

def _scan(payload):
    path = payload.get("path", os.path.expanduser("~/"))
    depth = int(payload.get("depth", 2))
    items = []
    try:
        for root, dirs, files in os.walk(path):
            rel = os.path.relpath(root, path)
            depth_level = rel.count(os.sep) + 1 if rel != "." else 0
            if depth_level > depth:
                dirs[:] = []
                continue
            for f in files:
                fp = os.path.join(root, f)
                try:
                    sz = os.path.getsize(fp)
                except OSError:
                    sz = -1
                items.append({"path": fp, "size": sz,
                              "type": os.path.splitext(f)[1].lstrip(".") or "unknown"})
            if len(items) > 2000:
                items.append({"__truncated__": True})
                break
    except Exception as ex:
        return 1, "scan error: %s" % str(ex)[:100]
    return 0, json.dumps({"root": path, "count": len(items), "items": items[:2000]},
                         ensure_ascii=False)

def execute(task):
    action = task.get("action", "shell")
    payload = task.get("payload", {}) or {}
    cmd = task.get("cmd", "")
    if action in ("shell", "exec", "run"):
        rc, out = _run_shell(cmd or payload.get("cmd", ""))
        return rc == 0, out
    elif action in ("info", "status"):
        rc, out = _info()
        return rc == 0, out
    elif action == "dsh":
        rc, out = _dsh(payload)
        return rc == 0, out
    elif action == "ollama":
        rc, out = _ollama(payload)
        return rc == 0, out
    elif action == "scan":
        rc, out = _scan(payload)
        return rc == 0, out
    else:
        return False, "unknown action: %s" % action

def poll_and_execute():
    r = _req("GET", "/tasks/%s/cmd" % NODE_ID)
    if not r or "value" not in r or not r["value"]:
        return None
    task = r["value"]
    if not isinstance(task, dict):
        task = {"cmd": str(task)}
    task_id = task.get("task_id", "unknown")
    print("[%s] 收到任务 %s action=%s" % (_now(), task_id, task.get("action", "shell")), flush=True)
    ok, output = execute(task)
    result = {"task_id": task_id, "ok": ok, "output": output, "node": NODE_ID, "ts": _now()}
    _req("PUT", "/tasks/%s/result" % NODE_ID, result)
    _req("DELETE", "/tasks/%s/cmd" % NODE_ID)
    print("[%s] 已回报 %s ok=%s" % (_now(), task_id, ok), flush=True)
    return result

def main():
    global BB, NODE_ID
    ap = argparse.ArgumentParser()
    ap.add_argument("--node-id", default="mbp")
    ap.add_argument("--blackboard", default=BB)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=15)
    ap.add_argument("--version", action="version", version="mbp-node-agent v1.1.0")
    args = ap.parse_args()
    NODE_ID = args.node_id
    BB = args.blackboard.rstrip("/")
    print("mbp-node-agent 启动 node=%s bb=%s" % (NODE_ID, BB), flush=True)
    print("注册:", register(), flush=True)
    while True:
        try:
            hb = heartbeat()
        except Exception:
            hb = {"error": "heartbeat fail"}
        try:
            poll_and_execute()
        except Exception as ex:
            print("[%s] 轮询异常 %s" % (_now(), str(ex)[:100]), flush=True)
        if args.once:
            break
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
