#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-absorb-watch.py — 吸收循环常驻监控（事件驱动，零轮询零 token）

订阅黑板事件桥（:8803/events），监控 data/<node>/tools/ 命名空间——
节点登记新工具时自动触发 bb-absorb.py 评估 + 落链。

设计（吸收循环自动化）：
  · 事件驱动：订阅 8803 SSE（零轮询，只有工具登记才动作）
  · 自动评估：新工具出现 → 跑 bb-absorb.py（复用评估 + 落链建议）
  · 去重：已评估过的工具（data/iterations/absorb-* 有记录）跳过
  · 常驻：launchd 托管（或 nohup 后台）

用法：
  python3 bb-absorb-watch.py                    # 常驻
  python3 bb-absorb-watch.py --log /tmp/bb-absorb-watch.log
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, sys, time, datetime, subprocess, urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-absorb-watch.log")


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
BB = "http://127.0.0.1:8792"
WATCH_PREFIX = "/tools/"          # 监控 data/<node>/tools/ 登记
ABSORB = os.path.expanduser("~/dsh-collab/scripts/bb-absorb.py")
LOGF = None
SEEN = set()                      # 已处理工具去重

def log(msg):
    line = "[%s] %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    if LOGF:
        try:
            with open(LOGF, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

def bb_get(path):
    try:
        with urllib.request.urlopen(BB + path, timeout=5) as r:
            return json.loads(r.read().decode())
    except Exception:
        return {"error": "fetch_failed"}  # 404/网络错误 → 标记为未获取（未吸收）

def already_absorbed(node, tool):
    key = "data/iterations/absorb-%s-%s" % (node, tool.replace(".", "-"))
    d = bb_get("/" + key)
    # 只有真存在（有 absorbed_from 字段）才算已吸收；404/空/错误都算未吸收
    return isinstance(d, dict) and "absorbed_from" in d

def trigger_absorb(node, tool, desc_hint=""):
    """触发吸收评估（复用 bb-absorb.py）"""
    if tool in SEEN:
        return
    SEEN.add(tool)
    if already_absorbed(node, tool):
        log("⏭ 已吸收过: %s/%s（跳过）" % (node, tool))
        return
    log("🎯 检测到新工具: %s/%s → 触发吸收评估" % (node, tool))
    cmd = "python3 %s --node %s --tool %s --desc \"%s\" --deps \"标准库\" --hub-dep \"黑板HTTP\" --node-side \"纯标准库\" --env-notes \"需核查：编码GBK/UTF8、路径分隔、shell风格跨平台自适配\"" % (
        ABSORB, node, tool, desc_hint or ("%s 节点工具" % node))
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        out = (r.stdout or "") + (r.stderr or "")
        log("吸收评估完成:\n%s" % out[-300:])
    except Exception as ex:
        log("吸收评估失败: %s" % str(ex)[:100])

def main():
    global LOGF
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=None)
    args = ap.parse_args()
    LOGF = args.log
    log("吸收循环监控启动（事件驱动订阅 %s，监控 %s）" % (EVENTS_URL, WATCH_PREFIX))
    while True:
        try:
            req = urllib.request.Request(EVENTS_URL, headers={"Accept": "text/event-stream"})
            resp = urllib.request.urlopen(req, timeout=None)
            log("已连接事件桥，等待节点工具登记...")
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
                # 匹配 data/<node>/tools/<tool>
                if key.startswith("data/") and WATCH_PREFIX in key:
                    parts = key.split("/")
                    if len(parts) >= 4 and parts[2] == "tools":
                        node = parts[1]
                        tool = parts[3]
                        trigger_absorb(node, tool)
        except Exception as ex:
            log("连接中断: %s（5s 后重连）" % str(ex)[:100])
            time.sleep(5)

if __name__ == "__main__":
    main()
