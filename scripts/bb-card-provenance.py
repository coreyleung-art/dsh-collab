#!/usr/bin/env python3
"""追查 card-1791011480 的来源与两版差异（只读，不改）
目的：能否识别产生者，以便把发现通报给正确的人（审查员只上报、不代改）。

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
    print("== bb-card-provenance 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 追查 card-1791011480 的来源与两版差异（只读，不改）")
    print("  · 目的：能否识别产生者，以便把发现通报给正确的人（审查员只上报、不代改）。")
    print("  · ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。")
    print("  · 依据：r006-debt-assess.py 机械扫描未检出以下原语：")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: json, os, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/bb-card-provenance.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

import json, urllib.request, urllib.error

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-card-provenance.log")


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
KEY = "notes/mac-mini/card-1791011480"


def fetch(base, key, t=25):
    try:
        r = urllib.request.urlopen(base + key, timeout=t)
        return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return f"ERR:{type(e).__name__}", None


sl, vl = fetch(LOCAL, KEY)
sc, vc = fetch(CENTRAL, KEY)
print("local  ", sl, "version=", vl.get("version"), "ts=", vl.get("ts"))
print("central", sc, "version=", vc.get("version"), "ts=", vc.get("ts"))
a, b = vl.get("value"), vc.get("value")
print("\n--- local value keys ---")
print(list(a.keys()) if isinstance(a, dict) else type(a))
print("--- central value keys ---")
print(list(b.keys()) if isinstance(b, dict) else type(b))

for tag, v in (("LOCAL", a), ("CENTRAL", b)):
    print(f"\n===== {tag} =====")
    if isinstance(v, dict):
        for k, val in v.items():
            s = json.dumps(val, ensure_ascii=False) if not isinstance(val, str) else val
            print(f"  {k}: {s[:300]}")
    else:
        print(" ", str(v)[:500])
