#!/usr/bin/env python3
"""★ 验证正确模型：中央板 = 「跨设备通道（comm-central）」的子集，而非「本地板的部分同步副本」
判据：若成立 ⇒
  ① central 上存在的键**大多带通道标记**（如 `_via`）
  ② local 独有（central 没有）的键**大多不带**通道标记
  ③ notes/genebank 的键若不带通道标记，则它不同步是**设计**而非缺陷

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
    print("== bb-central-subset-model-check 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · ★ 验证正确模型：中央板 = 「跨设备通道（comm-central）」的子集，而非「本地板的部分同步副本」")
    print("  · 判据：若成立 ⇒")
    print("  · ① central 上存在的键**大多带通道标记**（如 `_via`）")
    print("  · ② local 独有（central 没有）的键**大多不带**通道标记")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: json, os, random, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/bb-central-subset-model-check.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

import json, urllib.request, urllib.error, collections

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-central-subset-model-check.log")


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


def fetch(base, url, t=30):
    try:
        r = urllib.request.urlopen(base + url, timeout=t)
        return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return f"ERR:{type(e).__name__}", None


def keys_of(base, ns):
    out = {}
    off = 0
    while True:
        s, d = fetch(base, f"{ns}/?limit=1000&offset={off}")
        if not isinstance(d, dict):
            break
        lst = d.get("list") or {}
        out.update(lst)
        if len(lst) < 1000 or len(out) >= d.get("total", 0):
            break
        off += 1000
    return out


def via_of(base, key):
    s, d = fetch(base, key)
    if not isinstance(d, dict):
        return f"HTTP{s}"
    v = d.get("value")
    if isinstance(v, dict):
        for f in ("_via", "via", "channel", "_channel"):
            if f in v:
                return f"{f}={v[f]}"
        return "(无通道字段)"
    return f"(value 非 dict: {type(v).__name__})"


print("=" * 76)
print("【A】local-only vs 共有：通道字段分布（notes/mac-mini）")
print("=" * 76)
kl = keys_of(LOCAL, "notes/mac-mini")
kc = keys_of(CENTRAL, "notes/mac-mini")
only_l = sorted(set(kl) - set(kc))
both = sorted(set(kl) & set(kc))
print(f"  local={len(kl)}  central={len(kc)}  仅 local={len(only_l)}  共有={len(both)}")

import random
random.seed(7)
for label, keys, base in (("共有键（两板都有）", random.sample(both, min(10, len(both))), LOCAL),
                          ("仅 local 的键", random.sample(only_l, min(10, len(only_l))), LOCAL)):
    c = collections.Counter(via_of(base, k) for k in keys)
    print(f"\n  {label}（抽样 {len(keys)}，读 local 板）:")
    for k, n in c.most_common():
        print(f"    {n:>3}  {k}")

print()
print("=" * 76)
print("【B】genebank 样本的通道字段分布")
print("=" * 76)
kg = keys_of(LOCAL, "notes/genebank")
gk = random.sample(sorted(kg), min(8, len(kg)))
for k in gk:
    print(f"  {via_of(LOCAL, k):<30} {k}")

print()
print("=" * 76)
print("【C】对照：中央板上有、本地板没有的键（反向残留）")
print("=" * 76)
only_c = sorted(set(kc) - set(kl))
print(f"  notes/mac-mini 仅 central = {len(only_c)}")
for k in only_c[:8]:
    print(f"  {via_of(CENTRAL, k):<30} {k}")
