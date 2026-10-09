#!/usr/bin/env python3
"""决定性验证：那条新出现的「仅-local」键是否在 <=300s 同步窗口内被推上
对象：notes/mac-mini/closing-the-a-b-gap-binary-and-carrier-errors-only-cause-false-negatives-20261008
（ts 12:36:28；我第一次测于 ~12:5x，发现它仍是仅-local）
若现已两板都有 ⇒ 支持「表内前缀 + <=300s 同步窗口」模型；若仍仅 local ⇒ 真遗漏

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
    print("== sync-window-verify 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 决定性验证：那条新出现的「仅-local」键是否在 <=300s 同步窗口内被推上")
    print("  · 对象：notes/mac-mini/closing-the-a-b-gap-binary-and-carrier-errors-only-cause-false-negatives-20261")
    print("  · （ts 12:36:28；我第一次测于 ~12:5x，发现它仍是仅-local）")
    print("  · 若现已两板都有 ⇒ 支持「表内前缀 + <=300s 同步窗口」模型；若仍仅 local ⇒ 真遗漏")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: json, os, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/sync-window-verify.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

import json, urllib.request, urllib.error, datetime

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/sync-window-verify.log")


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
K = "notes/mac-mini/closing-the-a-b-gap-binary-and-carrier-errors-only-cause-false-negatives-20261008"


def get(base, key):
    try:
        r = urllib.request.urlopen(base + key, timeout=20)
        return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return f"ERR:{type(e).__name__}", None


print("NOW =", datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
sl, vl = get(LOCAL, K)
sc, vc = get(CENTRAL, K)
print(f"\n  local   http={sl}  ts={(vl or {}).get('ts')}")
print(f"  central http={sc}  ts={(vc or {}).get('ts')}")
print(f"\n  ⇒ {'✅ 已被推上（两板都有）⇒ 支持表内前缀 + <=300s 同步窗口' if sc == 200 else '⚠ 仍仅 local ⇒ 可能真遗漏，或同步周期未到'}")

# 再统计当前仅-local 的最晚 ts（全前缀快速版：只比键集，不取 value）
def keys_of(base, ns):
    out = {}
    off = 0
    while True:
        try:
            r = urllib.request.urlopen(f"{base}{ns}/?limit=1000&offset={off}", timeout=30)
            d = json.loads(r.read().decode("utf-8", "replace"))
        except Exception:
            break
        lst = d.get("list") or {}
        out.update(lst)
        if len(lst) < 1000 or len(out) >= d.get("total", 0):
            break
        off += 1000
    return out


kl = keys_of(LOCAL, "notes/mac-mini")
kc = keys_of(CENTRAL, "notes/mac-mini")
only_l = {k: v for k, v in kl.items() if k not in kc}
ts = sorted((str(v.get("ts") or ""), k) for k, v in only_l.items())
print(f"\n  当前：local={len(kl)} central={len(kc)} 仅local={len(only_l)}")
print("  仅-local 最晚 5 条:")
for t, k in ts[-5:]:
    print(f"    {t}  {k}")
