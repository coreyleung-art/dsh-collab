#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""channel-gate-weekly.py — 通道变更留痕周审（com.dsh.cron.channel-gate-weekly）

读 ~/dsh-collab/logs/channel-changes.jsonl → 统计：每通道变更数/漂移修复数、
熔断拒绝记录、缺字段单 → 写周报卡 data/ops/channel-gate-weekly/<ts>（双板）。
判据：留痕行必须有 id/channel/evidence/rollback（缺=门被绕过=FAIL 记录）。
2026-10-02 星桥 · 架构三期治理常态化 ①

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, os, time, urllib.request

LOG = os.path.expanduser("~/dsh-collab/logs/channel-changes.jsonl")
BB = "http://127.0.0.1:8792"


def main():
    rows = []
    try:
        with open(LOG) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    except FileNotFoundError:
        rows = []
    if not rows:
        print("[cg-weekly] 无留痕记录，跳过")
        return 0
    by_channel, meltdowns, incomplete = {}, 0, 0
    for r in rows:
        ch = r.get("channel") or "unknown"
        kind = "drift-fix" if str(r.get("action", "")).startswith("drift-fix:") else "change"
        by_channel.setdefault(ch, {"change": 0, "drift-fix": 0})
        by_channel[ch][kind] += 1
        if r.get("meltRisk") == "next-freezes":
            meltdowns += 1
        for field in ("id", "channel", "evidence", "rollback"):
            if not r.get(field):
                incomplete += 1
                break
    ts = int(time.time() * 1000)
    key = f"data/ops/channel-gate-weekly/{ts}"
    val = {
        "type": "channel-gate-weekly", "from": "channel-gate-weekly",
        "ts": ts, "period": "自留痕启用（2026-10-02）至今",
        "total_records": len(rows), "by_channel": by_channel,
        "meltdown_risk_records": meltdowns, "incomplete_records": incomplete,
        "gate_integrity": "OK" if incomplete == 0 else f"FAIL（{incomplete} 条缺必填字段=疑似绕门）",
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
        print(f"[cg-weekly] {name} PUT {st}", flush=True)
    assert readbacks["local"]["value"] == readbacks["central"]["value"]
    print(f"[cg-weekly] 周报：{len(rows)} 条留痕 · 熔断风险 {meltdowns} · 缺字段 {incomplete} · {key}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
