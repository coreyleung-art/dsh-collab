#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""i9-node-agent.py v1.0 — i9 资源节点执行器（完整版，补执行+回报）

与 node-agent.py（PoC，只 print）的区别：真正执行任务卡 + 结构化回报。
纯标准库（urllib/subprocess），Windows Python3 可直接跑。

用法（在 i9 上）:
  python i9-node-agent.py --node-id i9 --blackboard http://100.120.203.20:8792

任务卡协议（node-relationship-model）:
  中枢 PUT /tasks/i9/cmd  body={"task_id":"...","action":"shell|info|ollama|scan","cmd":"...","payload":{...}}
  节点 GET /tasks/i9/cmd → 取 value → 按 action 执行
  节点 PUT /tasks/i9/result body={"task_id":"...","ok":true,"output":"...","node":"i9"}
  节点 DELETE /tasks/i9/cmd（清卡）
"""
import argparse, json, os, sys, time, subprocess, datetime, platform
import urllib.parse, http.client

BB = "http://100.120.203.20:8792"
NODE_ID = "i9"

def _req(method, path, data=None, timeout=15):
    """用 http.client 显式发请求（Windows urllib 对 PUT body 有兼容问题，
    http.client 明确控制 body + Content-Length，跨平台稳定）"""
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
    caps = ["gpu-cuda", "ollama", "file-e-drive", "dsh", "python3", "shell"]
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
    """执行 shell 命令，返回 (rc, stdout+stderr)"""
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
    return _run_shell("systeminfo | findstr /C:\"OS\" /C:\"Memory\" & echo --- & nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>nul & echo --- & wmic logicaldisk get caption,freespace,size 2>nul")

def _ollama(payload):
    """调 i9 本地 Ollama（http://localhost:11434），零订阅本地推理。
    用 http.client（不走系统代理，避免 Windows urllib 代理拦截 localhost）"""
    model = payload.get("model", "qwen2.5:7b")
    prompt = payload.get("prompt", "")
    body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0}}).encode()
    try:
        conn = http.client.HTTPConnection("localhost", 11434, timeout=300)
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
    """扫描指定目录 → 结构化清单（数据沉淀归档）"""
    path = payload.get("path", "E:\\")
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
    """按 action 分派执行，返回 (ok, output)"""
    action = task.get("action", "shell")
    payload = task.get("payload", {}) or {}
    cmd = task.get("cmd", "")
    if action == "shell" or action == "exec" or action == "run":
        rc, out = _run_shell(cmd or payload.get("cmd", ""))
        return rc == 0, out
    elif action == "info" or action == "status":
        rc, out = _info()
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
    """轮询任务卡 → 执行 → 回报 → 清卡"""
    r = _req("GET", "/tasks/%s/cmd" % NODE_ID)
    if not r or "value" not in r or not r["value"]:
        return None  # 无任务卡
    task = r["value"]
    if not isinstance(task, dict):
        task = {"cmd": str(task)}
    task_id = task.get("task_id", "unknown")
    print("[%s] 收到任务 %s action=%s" % (_now(), task_id, task.get("action", "shell")),
          flush=True)
    ok, output = execute(task)
    result = {"task_id": task_id, "ok": ok, "output": output, "node": NODE_ID,
              "ts": _now()}
    _req("PUT", "/tasks/%s/result" % NODE_ID, result)
    _req("DELETE", "/tasks/%s/cmd" % NODE_ID)
    print("[%s] 已回报 %s ok=%s" % (_now(), task_id, ok), flush=True)
    return result

def main():
    global BB, NODE_ID
    ap = argparse.ArgumentParser()
    ap.add_argument("--node-id", default="i9")
    ap.add_argument("--blackboard", default=BB)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=15)
    ap.add_argument("--version", action="version", version="i9-node-agent v1.1.0")
    args = ap.parse_args()
    NODE_ID = args.node_id
    BB = args.blackboard.rstrip("/")
    print("i9-node-agent 启动 node=%s bb=%s" % (NODE_ID, BB), flush=True)
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
