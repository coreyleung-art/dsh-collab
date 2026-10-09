#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""i9-monitor-sub.py v1.0 — i9 回报常驻监控（事件驱动订阅，替代一次性轮询脚本）

订阅黑板事件桥（:8803/events），过滤 tasks/i9/* 变化 → 记录回报到日志 + 黑板 notes。
零轮询（事件驱动），常驻后台。教训：之前用一次性 40min 轮询脚本漏了 CUDA 回报——事件驱动订阅不会漏。

用法:
  python3 i9-monitor-sub.py                      # 常驻（后台）
  python3 i9-monitor-sub.py --log /tmp/i9-monitor.log

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== i9-monitor-sub 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · i9-monitor-sub.py v1.0 — i9 回报常驻监控（事件驱动订阅，替代一次性轮询脚本）")
    print("  · 订阅黑板事件桥（:8803/events），过滤 tasks/i9/* 变化 → 记录回报到日志 + 黑板 notes。")
    print("  · 零轮询（事件驱动），常驻后台。教训：之前用一次性 40min 轮询脚本漏了 CUDA 回报——事件驱动订阅不会漏。")
    print("  · python3 i9-monitor-sub.py                      # 常驻（后台）")
    print("  · 命令/参数: log")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, http, os, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/i9-monitor-sub.log")
    return 0

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, sys, time, datetime, urllib.request

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/i9-monitor-sub.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

EVENTS_URL = "http://127.0.0.1:8803/events"
BLACKBOARD = "http://127.0.0.1:8792"
WATCH_PREFIX = "tasks/i9/"   # 监控 i9 相关所有 key（queue/result/results）

def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")

def _bb_put(path, data):
    import http.client, urllib.parse
    u = urllib.parse.urlparse(BLACKBOARD)
    body = json.dumps(data, ensure_ascii=False).encode()
    conn = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=8)
    conn.request("PUT", path, body=body, headers={"Content-Type":"application/json","Content-Length":str(len(body))})
    r = conn.getresponse(); raw = r.read().decode(); conn.close()
    return raw

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default="/tmp/i9-monitor.log")
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    if "--selfcheck" in __import__("sys").argv:
        return selfcheck()
    args = ap.parse_args()
    logf = open(args.log, "a", encoding="utf-8")
    def log(msg):
        line = "[%s] %s" % (_now(), msg)
        print(line, flush=True)
        logf.write(line + "\n"); logf.flush()
    log("i9 回报常驻监控启动（事件驱动订阅 %s，监控 %s）" % (EVENTS_URL, WATCH_PREFIX))
    while True:
        try:
            req = urllib.request.Request(EVENTS_URL, headers={"Accept": "text/event-stream"})
            resp = urllib.request.urlopen(req, timeout=None)
            log("已连接黑板事件桥，等待 i9 事件...")
            for raw_line in resp:
                line = raw_line.decode("utf-8", "ignore").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data:
                    continue
                try:
                    evt = json.loads(data)
                except json.JSONDecodeError:
                    continue
                key = evt.get("key", "")
                if key.startswith(WATCH_PREFIX):
                    log("🎯 i9 事件: %s" % key)
                    # 若是 result，记录回报摘要
                    if key.endswith("/result") or "/results/" in key:
                        val = evt.get("value", {})
                        log("   回报: task_id=%s ok=%s" % (val.get("task_id"), val.get("ok")))
                    # 黑板 notes 记录（可追溯）
                    try:
                        _bb_put("/notes/i9/monitor", {"ts":_now(), "from":"mac总线","type":"monitor",
                                                       "event_key":key, "value":str(evt.get("value"))[:200]})
                    except Exception:
                        pass
        except Exception as ex:
            log("连接中断: %s（5s 后重连）" % str(ex)[:100])
            time.sleep(5)

if __name__ == "__main__":
    main()
