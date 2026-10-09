#!/usr/bin/env python3
"""深挖修复后窗口：intent 行与结果行的配对（我上一轮预言的「有 intent 无结果」形态）
上一轮我写过：intent 行落在写入之前 ⇒ 它本身可能成为新的「部分写入」形态。
本轮统计显示 修复后 intent 行 75 / 结果行 69 ⇒ 差 6 ⇒ 核对这 6 例到底是什么。

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
    print("== intent-result-pairing-check 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 深挖修复后窗口：intent 行与结果行的配对（我上一轮预言的「有 intent 无结果」形态）")
    print("  · 上一轮我写过：intent 行落在写入之前 ⇒ 它本身可能成为新的「部分写入」形态。")
    print("  · 本轮统计显示 修复后 intent 行 75 / 结果行 69 ⇒ 差 6 ⇒ 核对这 6 例到底是什么。")
    print("  · ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: json")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/intent-result-pairing-check.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

import json, os, collections

LOG = os.path.expanduser("~/dsh-collab/logs/bb-card-send.log")
CUT = "2026-10-08T00:20:00"

rows = []
for l in open(LOG, errors="replace"):
    l = l.strip()
    if not l:
        continue
    try:
        rows.append(json.loads(l))
    except Exception:
        pass


def norm(ts):
    return (ts or "").replace(".000Z", "Z").rstrip("Z")


after = [e for e in rows if norm(e.get("at")) >= CUT]
print(f"修复后窗口条目 = {len(after)}")

ph = collections.Counter(e.get("phase") or "(无 phase 字段=结果行)" for e in after)
print("\n  phase 分布:")
for k, v in ph.most_common():
    print(f"    {k:<28} {v}")

intents = [e for e in after if e.get("phase") == "intent"]
results = [e for e in after if not e.get("phase")]
print(f"\n  intent 行 = {len(intents)}   结果行 = {len(results)}   差 = {len(intents)-len(results)}")

print("\n  结果行的 result 分布:")
print("   ", dict(collections.Counter(e.get("result") for e in results)))

# 配对：按 key 看哪些 intent 没有对应结果行
rk = collections.Counter(e.get("key") for e in results)
ik = collections.Counter(e.get("key") for e in intents)
missing = [(k, ik[k] - rk.get(k, 0)) for k in ik if ik[k] > rk.get(k, 0)]
print(f"\n  ★ 有 intent 但结果行少于 intent 的 key = {len(missing)} 个:")
for k, n in missing:
    print(f"     intent={ik[k]} 结果={rk.get(k,0)}  差{n}   {k}")

print("\n  ★ 每条这样的 intent 行的时刻:")
for k, n in missing:
    for e in intents:
        if e.get("key") == k:
            print(f"     {e.get('at')}  {k[:70]}  elapsedMs={e.get('elapsedMs')}")

print("\n  说明：差 6 可能是 ① 进程中断（intent 要捕的正是这个）② 某些路径不落结果行 ③ 日志轮转/写入竞态")
print("  ⇒ 无论哪种，都说明「有 intent 无结果」这个形态**已经出现**（不是假想）")
