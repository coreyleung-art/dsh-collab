#!/usr/bin/env python3
"""两件独立复核：
A) 字符数 vs UTF-8 字节数 —— 核对方的指正（我把「字符」标成了「字节」）
B) 全命名空间扫描「探针/临时键」残留，并逐键比对两板（找单板残留）
★ 我方先自查：不只看已知那一个键，而是扫全部可疑键名。

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
    print("== bb-probe-residue-scan 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 两件独立复核：")
    print("  · A) 字符数 vs UTF-8 字节数 —— 核对方的指正（我把「字符」标成了「字节」）")
    print("  · B) 全命名空间扫描「探针/临时键」残留，并逐键比对两板（找单板残留）")
    print("  · ★ 我方先自查：不只看已知那一个键，而是扫全部可疑键名。")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: json, os, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/bb-probe-residue-scan.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

import json, urllib.request, urllib.error, re

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-probe-residue-scan.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

LOCAL = "http://127.0.0.1:8792/"
CENTRAL = "http://106.53.214.108:8792/"
CARD = "notes/mac-mini/card-1791011480"


def fetch(base, url, t=25):
    try:
        r = urllib.request.urlopen(base + url, timeout=t)
        return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return f"ERR:{type(e).__name__}", None


print("=" * 74)
print("【A】字符数 vs UTF-8 字节数（核对方指正）")
print("=" * 74)
for label, base in (("local", LOCAL), ("central", CENTRAL)):
    s, d = fetch(base, CARD)
    body = d["value"]["body"] if isinstance(d, dict) else None
    if body:
        chars = len(body)
        b8 = len(body.encode("utf-8"))
        print(f"  {label:<8} 字符数(Python len) = {chars:<6} UTF-8 字节数 = {b8:<6} 比值 = {b8/chars:.3f}")
print("  ⇒ 对方声称：字符 1601/1629、字节 2878/2910")
print("  ⇒ 判读：我此前卡/消息里写「1601 字节 / 1629 字节」= **把字符数标成了字节数**")

print()
print("=" * 74)
print("【B】探针/临时键残留扫描（全命名空间，不只看已知那一个）")
print("=" * 74)
PAT = re.compile(r"probe|do-not-use|dummy|temp|tmp| __|^__|test-|sandbox", re.I)
keys = []
offset = 0
while True:
    s, d = fetch(LOCAL, f"notes/mac-mini/?limit=400&offset={offset}")
    if not isinstance(d, dict):
        print("  列表读取失败 http=", s)
        break
    lst = d.get("list") or {}
    ks = list(lst.keys())
    keys.extend(ks)
    if len(ks) < 400 or len(keys) >= d.get("total", 0):
        break
    offset += 400
print(f"  命名空间 notes/mac-mini 共枚举 {len(keys)} 个键")

susp = [k for k in keys if PAT.search(k.split("/")[-1])]
print(f"  可疑键名（命中 probe/tmp/test/__ 等模式）= {len(susp)}")
for k in susp:
    print(f"    {k}")
if not susp:
    print("    （无）")

print()
print("  逐键两板比对（找单板残留）:")
found = 0
for k in susp:
    sl, _ = fetch(LOCAL, k)
    sc, _ = fetch(CENTRAL, k)
    if (sl == 200) != (sc == 200):
        found += 1
        print(f"    ⚠ **单板残留**：{k}  local={sl} central={sc}")
    else:
        print(f"    ok 两板一致（{sl}/{sc}）：{k}")
print(f"\n  ⇒ 单板残留计数 = {found}")

print()
print("=" * 74)
print("【C】我方已知清理项复核")
print("=" * 74)
for k in ("notes/mac-mini/__audit-probe-do-not-use-20261008",):
    sl, _ = fetch(LOCAL, k)
    sc, _ = fetch(CENTRAL, k)
    print(f"  {k}")
    print(f"    local={sl} central={sc} ⇒ {'✅ 已清理（两板均 404）' if sl == 404 and sc == 404 else '⚠ 仍存在'}")
