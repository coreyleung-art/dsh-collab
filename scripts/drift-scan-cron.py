#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""drift-scan-cron.py — 通道漂移周期巡检 wrapper（com.dsh.cron.drift-scan 调用）

运行 drift-scan（node 工具）→ driftCount>0 时写黑板告警卡 data/ops/drift-alert/<ts>。
正常时静默（只写统一日志）。零漂移零写入黑板（防噪音）。
2026-10-02 星桥 · 架构三期治理常态化 ①
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, subprocess, sys, time, urllib.request, os


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/drift-scan-cron.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

TOOL = "/opt/homebrew/bin/node"
CLI = os.path.expanduser("~/dsh-plugin-drift-scan/cli.js")
BB = "http://127.0.0.1:8792"


def main():
    r = subprocess.run([TOOL, CLI, "--json"], capture_output=True, text=True, timeout=120)
    if r.returncode not in (0, 1):
        print(f"[drift-cron] 工具异常 exit={r.returncode}: {r.stderr[:120]}", flush=True)
        return 1
    try:
        d = json.loads(r.stdout)
    except Exception as e:
        print(f"[drift-cron] 输出解析失败: {e}", flush=True)
        return 1
    if d.get("driftCount", 0) == 0:
        return 0  # 零漂移：静默
    # 漂移 → 写黑板告警卡（本机+中枢双写+回读断言）
    ts = int(time.time() * 1000)
    key = f"data/ops/drift-alert/{ts}"
    val = {
        "type": "drift-alert", "from": "drift-scan-cron",
        "ts": ts, "driftCount": d.get("driftCount"),
        "drifts": [{"check": row.get("check"), "actual": str(row.get("actual"))[:80]}
                   for row in d.get("rows", []) if row.get("drift")],
        "note": "通道漂移巡检告警（自动）：修复路径=经 channel-gate 登记（portal §3）",
    }
    body = json.dumps(val).encode()
    readbacks = {}
    for name, base in (("local", BB), ("central", "http://xingqiao.meetfunbp.com:8792")):
        req = urllib.request.Request(base + "/" + key, data=body, method="PUT",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=6) as r:
            st = r.status
        with urllib.request.urlopen(base + "/" + key, timeout=6) as r:
            readbacks[name] = json.loads(r.read())
        print(f"[drift-cron] 告警卡 {name} PUT {st}", flush=True)
    assert readbacks["local"]["value"] == readbacks["central"]["value"], "两板不一致"
    print(f"[drift-cron] 漂移 {d.get('driftCount')} 项 → 告警卡 {key} 双写一致", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
