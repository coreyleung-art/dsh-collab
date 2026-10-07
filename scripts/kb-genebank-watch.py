#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kb-genebank-watch.py — 语义库→基因库自动同步常驻监控（事件驱动）

用户指示（2026-08-24）：语义库更新后自动同步基因库，过程自动化。
事件驱动：订阅黑板事件桥（8803），检测语义库来源更新（论文落链/新 PDF 登记）→
自动触发 kb-genebank-sync.py（去重 + 断点续传）。

触发源：
  - data/recovery/4787d717-*（论文落链完成）
  - data/iterations/*（迭代落链）
  - 定期兜底（每 6h 全量扫描对比）

用法：
  python3 kb-genebank-watch.py                      # 常驻（事件驱动 + 6h 兜底）
  python3 kb-genebank-watch.py --log /tmp/kb-gb-watch.log
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, sys, time, datetime, subprocess, urllib.request

EVENTS_URL = "http://127.0.0.1:8803/events"
SYNC = os.path.expanduser("~/dsh-collab/scripts/kb-genebank-sync.py")
LOGF = None
LAST_FULL = 0
FULL_INTERVAL = 6 * 3600  # 6h 兜底全量

def log(msg):
    line = "[%s] %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    if LOGF:
        try:
            with open(LOGF, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

def trigger_sync(why):
    """触发一次同步（增量去重 + 断点续传）"""
    log("🔄 触发同步（%s）" % why)
    try:
        r = subprocess.run("python3 %s" % SYNC, shell=True, capture_output=True, text=True, timeout=600)
        out = (r.stdout or "") + (r.stderr or "")
        # 摘要
        for line in out.split("\n")[-5:]:
            if line.strip():
                log("  " + line.strip()[:100])
    except Exception as e:
        log("同步失败: %s" % str(e)[:100])

def is_sync_source(key):
    """判断事件是否来自语义库更新源"""
    triggers = [
        key.startswith("data/recovery/4787d717-"),   # 论文落链
        "/papers/" in key or "paper-cache" in key,    # 论文登记
        key.startswith("data/iterations/") and ("paper" in key or "yolo" in key),
        "datasets/" in key,                            # 数据集
    ]
    return any(triggers)

def main():
    global LOGF, LAST_FULL
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=None)
    args = ap.parse_args()
    LOGF = args.log
    log("语义库→基因库同步监控启动（事件驱动 %s + 6h 兜底）" % EVENTS_URL)
    while True:
        # 6h 兜底全量
        if time.time() - LAST_FULL > FULL_INTERVAL:
            LAST_FULL = time.time()
            trigger_sync("6h 定期兜底")
        try:
            req = urllib.request.Request(EVENTS_URL, headers={"Accept": "text/event-stream"})
            resp = urllib.request.urlopen(req, timeout=None)
            log("已连接事件桥，等待语义库更新...")
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
                if is_sync_source(key):
                    trigger_sync("事件: %s" % key.split("/")[-1])
        except Exception as ex:
            log("连接中断: %s（5s 后重连）" % str(ex)[:100])
            time.sleep(5)

if __name__ == "__main__":
    main()
