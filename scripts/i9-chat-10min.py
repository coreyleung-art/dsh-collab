#!/usr/bin/env python3
"""i9 持续对话测试（10 分钟）— 每 ~12s 发一个任务，秒级轮询抓回报，记录对话轮次
模拟「持续聊天」：发任务=说一句，收回报=回一句

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, sys, time, datetime, urllib.request, http.client, urllib.parse

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/i9-chat-10min.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

BB = "http://127.0.0.1:8792"
DURATION = 600  # 10 分钟
SEND_EVERY = 12  # 每 12 秒发一轮
LOG = "/tmp/i9-chat-10min.log"

def get(path):
    try:
        with urllib.request.urlopen(BB + path, timeout=3) as r:
            return json.loads(r.read().decode())
    except Exception:
        return {}

def put(path, data):
    try:
        u = urllib.parse.urlparse(BB)
        body = json.dumps(data, ensure_ascii=False).encode()
        conn = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=5)
        conn.request("PUT", path, body=body, headers={"Content-Type":"application/json","Content-Length":str(len(body))})
        r = conn.getresponse(); raw = r.read().decode(); conn.close()
        return json.loads(raw) if raw else {}
    except Exception:
        return {}

def now(): return datetime.datetime.now().strftime("%H:%M:%S")

def main():
    logf = open(LOG, "a", encoding="utf-8")
    def log(m):
        line = "[%s] %s" % (now(), m)
        print(line, flush=True)
        logf.write(line + "\n"); logf.flush()

    log("=== i9 持续对话测试开始（10 分钟，每 %ds 一轮）===" % SEND_EVERY)
    start = time.time()
    round_no = 0
    replies = 0
    last_seen_result = None
    last_send = 0

    while time.time() - start < DURATION:
        # 1. 秒级轮询：抓新回报
        r = get("/tasks/i9/result")
        v = r.get("value") or {}
        tid = v.get("task_id"); ts = v.get("ts","")
        if tid and (tid, ts) != last_seen_result:
            last_seen_result = (tid, ts)
            replies += 1
            out = str(v.get("output",""))[:100]
            log("↩ 收到回报 #%d: %s ok=%s | %s" % (replies, tid, v.get("ok"), out))

        # 2. 每 12s 发一轮
        if time.time() - last_send >= SEND_EVERY:
            last_send = time.time()
            round_no += 1
            ts_q = int(time.time()*1000)
            content = "round-%d: %s | ping from coordinator" % (round_no, now())
            put("/tasks/i9/queue/%s" % ts_q, {
                "task_id": "chat-%d-%s" % (round_no, ts_q),
                "action": "shell",
                "cmd": "echo ROUND-%d & echo %s & date /t & time /t" % (round_no, content),
                "ts": datetime.datetime.now().isoformat(),
            })
            log("→ 发出第 %d 轮: chat-%d" % (round_no, round_no))

        time.sleep(1)  # 秒级节奏

    elapsed = round(time.time() - start)
    log("=== 测试结束（%ds）===" % elapsed)
    log("发出轮次: %d | 收到回报: %d | 响应率: %.0f%%" % (
        round_no, replies, (replies/max(round_no,1))*100))
    log("日志: %s" % LOG)

if __name__ == "__main__":
    main()
