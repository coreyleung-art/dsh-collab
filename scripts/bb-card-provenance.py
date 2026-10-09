#!/usr/bin/env python3
"""追查 card-1791011480 的来源与两版差异（只读，不改）
目的：能否识别产生者，以便把发现通报给正确的人（审查员只上报、不代改）。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
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
