#!/usr/bin/env python3
"""i9 秒级轮询 v2 — 监控 tasks/i9/result + tasks/i9/cmd + notes/i9/*（i9 消息键）
v2 修复：之前只查 result/cmd，漏了 notes/i9（i9 发消息的键）——这就是『秒级还收不到』的根因

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
    print("== i9-poll-seconds 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · i9 秒级轮询 v2 — 监控 tasks/i9/result + tasks/i9/cmd + notes/i9/*（i9 消息键）")
    print("  · v2 修复：之前只查 result/cmd，漏了 notes/i9（i9 发消息的键）——这就是『秒级还收不到』的根因")
    print("  · ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。")
    print("  · 依据：r006-debt-assess.py 机械扫描未检出以下原语：")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: json, os, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/i9-poll-seconds.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, sys, time, datetime, urllib.request

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/i9-poll-seconds.log")


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
INTERVAL = 2

def get(path):
    try:
        with urllib.request.urlopen(BB + path, timeout=3) as r:
            return json.loads(r.read().decode())
    except Exception:
        return {}

def main():
    last_result = None
    seen_notes = set()
    print("[%s] i9 秒级轮询 v2 启动（result+cmd+notes/i9 三路监控）" % datetime.datetime.now().strftime("%H:%M:%S"), flush=True)
    while True:
        now = datetime.datetime.now().strftime("%H:%M:%S")
        # 1. 任务回报
        r = get("/tasks/i9/result")
        v = r.get("value") or {}
        tid, ts = v.get("task_id"), v.get("ts","")
        if tid and (tid, ts) != last_result:
            last_result = (tid, ts)
            print("[%s] 🔄 回报: %s ok=%s | %s" % (now, tid, v.get("ok"), ts[:19]), flush=True)
            out = str(v.get("output",""))[:150]
            if out: print("    ", out, flush=True)
        # 2. 任务卡
        c = get("/tasks/i9/cmd")
        if "value" in c and c["value"]:
            print("[%s] 📥 任务卡: %s" % (now, c["value"].get("task_id","?")), flush=True)
        # 3. notes/i9（i9 消息）——v2 新增
        n = get("/notes/i9/?limit=50")
        for k, item in (n.get("list") or {}).items():
            if k not in seen_notes:
                seen_notes.add(k)
                val = item.get("value", {})
                if val.get("from") == "i9":
                    print("[%s] 💬 i9消息: %s | %s" % (now, k.split("/")[-1], str(val.get("subject") or val.get("type",""))[:60]), flush=True)
                    print("    ", json.dumps(val.get("content",""), ensure_ascii=False)[:200], flush=True)
                elif val.get("from") == "coordinator":
                    pass  # 自己写的忽略
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
