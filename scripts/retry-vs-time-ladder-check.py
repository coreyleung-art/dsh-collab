#!/usr/bin/env python3
"""决定性检验：那张未归因 6832ms 的卡（04:06:25）到底有没有走重试？
判据：修复后（Z 轴 00:20:00 之后）的卡，若真走了重试 ⇒
      ① calls[] 里应有 `(retry N)` 步（core.js:160 已把重试 GET 接进 timed()）
      ② retryCount 应 > 0（core.js:176/193/202 三处均已改 retryRounds）
⇒ 若两者都为「无」而时间却像重试 ⇒ 那么「用时间梯重建重试」这一步需要重新审视

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
import json, os

LOG = os.path.expanduser("~/dsh-collab/logs/bb-card-send.log")
rows = []
for l in open(LOG, errors="replace"):
    l = l.strip()
    if not l:
        continue
    try:
        rows.append(json.loads(l))
    except Exception:
        pass

res = [e for e in rows if e.get("result")]
print(f"结果行 = {len(res)}")

# 找未归因大的
cand = []
for e in res:
    calls = e.get("calls") or []
    if not isinstance(calls, list) or not calls:
        continue
    s = sum(c.get("ms") or 0 for c in calls)
    el = e.get("elapsedMs") or 0
    un = el - s
    cand.append((un, el, s, e))
cand.sort(reverse=True, key=lambda x: x[0])

print("\n=== 未归因最大的 5 张（含 calls[] 明细）===")
for un, el, s, e in cand[:5]:
    calls = e.get("calls") or []
    steps = [c.get("step") for c in calls]
    has_retry_step = any("retry" in str(x) for x in steps)
    print(f"\n  at={e.get('at')}  key={str(e.get('key'))[:60]}")
    print(f"    sum(calls)={s}ms  elapsedMs={el}ms  **未归因={un}ms**")
    print(f"    **仪表 retryCount = {e.get('retryCount')}**")
    print(f"    calls 步数 = {len(calls)}   含 (retry 步? **{has_retry_step}**")
    print(f"    steps = {steps}")

print("\n=== 判据 ===")
print("  若某张卡的未归因很大、但 calls[] 里【没有】(retry 步 且 retryCount=0")
print("  ⇒ 那么「用时间梯把这 6832ms 重建为 1 轮重试」这个推断可能不成立（该耗时另有来源）")
print("  反之若含 (retry 步、却仍报 retryCount=0 ⇒ 修复不完整（另一条路径仍在写死 0）")
