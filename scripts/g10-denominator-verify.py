#!/usr/bin/env python3
"""独立复核 G10 验收分母（星桥称：修复后 12 写 / 0 假红；修复前 343 / 26）
分窗点：修复落盘时刻 2026-10-08T00:20:00Z（他声明的窗口字段 = 日志 at）
★ 我不采信他的计数，自己数一遍

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
import json, os, re, datetime

LOG = os.path.expanduser("~/dsh-collab/logs/bb-card-send.log")
CUT = "2026-10-08T00:20:00"

print(f"日志 = {LOG}")
print(f"exists={os.path.isfile(LOG)}  size={os.path.getsize(LOG) if os.path.isfile(LOG) else '-'}")
print(f"分窗点（他声明的）= {CUT}Z\n")

lines = open(LOG, errors="replace").read().splitlines()
print(f"总行数 = {len(lines)}")
print("前 2 行样例:")
for l in lines[:2]:
    print("  ", l[:200])

# 自适应：先试 JSONL，失败则按 at=… 正则
parsed = []
bad = 0
for l in lines:
    l = l.strip()
    if not l:
        continue
    try:
        e = json.loads(l)
        parsed.append(e)
        continue
    except Exception:
        pass
    m = re.search(r"at=([0-9T:\-\.]+Z)", l)
    if m:
        parsed.append({"at": m.group(1), "_raw": l})
    else:
        bad += 1

print(f"\n解析成功 = {len(parsed)}  无法解析 = {bad}")
if parsed:
    print("样例解析对象键:", sorted(parsed[0].keys())[:14])


def norm(ts):
    return (ts or "").replace(".000Z", "Z").rstrip("Z")


before = [e for e in parsed if norm(e.get("at")) < CUT]
after = [e for e in parsed if norm(e.get("at")) >= CUT]

print()
print("=" * 74)
print("【分窗统计（按 at 字段；result 取 OK / OK-WITH-TIMEOUT / FAIL）】")
print("=" * 74)
for label, rows in (("修复前 (<%s)" % CUT, before), ("修复后 (>=%s)" % CUT, after)):
    res = {}
    for e in rows:
        r = e.get("result") or e.get("action") or "?"
        res[r] = res.get(r, 0) + 1
    ok = res.get("OK", 0)
    okt = res.get("OK-WITH-TIMEOUT", 0)
    fail = res.get("FAIL", 0)
    writes = ok + okt + fail
    print(f"  {label}")
    print(f"    总条目 = {len(rows)}   写入(OK+OKWT+FAIL) = {writes}")
    print(f"    OK = {ok} · OK-WITH-TIMEOUT = {okt} · **FAIL = {fail}**")
    print(f"    其他 result 分布 = { {k: v for k, v in res.items() if k not in ('OK','OK-WITH-TIMEOUT','FAIL')} }")
    print()

print("=" * 74)
print("【与他的声称对比】")
print("=" * 74)
print("  他称：修复前 343 写 / 26 假红；修复后 12 写 / 0 假红")
print("  ⇒ 请对照上方实测。差异可能来源：窗口字段口径 / result 分类口径（他能把假红单列）")
print("  ⇒ 注意：我在分窗内的 FAIL 计数是否能对应他的“假红”需先看 result 取值全集")
allres = {}
for e in parsed:
    r = e.get("result") or "?"
    allres[r] = allres.get(r, 0) + 1
print(f"\n  全量 result 分布: {allres}")
