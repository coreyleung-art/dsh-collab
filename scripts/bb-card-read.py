#!/usr/bin/env python3
"""通用读卡工具（kebab-case，共享目录用）
用法: python3 bb-card-read.py <key> [--raw]

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
import json, sys, urllib.request, urllib.error

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-card-read.log")


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


def fetch(url, t=25):
    try:
        r = urllib.request.urlopen(url, timeout=t)
        return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return f"ERR:{type(e).__name__}", None


def show(obj, indent=0, limit=1400):
    pad = "  " * indent
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                n = len(v)
                print(f"{pad}[{k}] ({type(v).__name__}, n={n})")
                show(v, indent + 1, limit)
            else:
                s = str(v)
                print(f"{pad}{k}: {s[:limit]}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, (dict, list)):
                print(f"{pad}({i})")
                show(v, indent + 1, limit)
            else:
                print(f"{pad}({i}) {str(v)[:limit]}")
    else:
        print(f"{pad}{str(obj)[:limit]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 bb-card-read.py <key>"); sys.exit(2)
    key = sys.argv[1]
    s, d = fetch(LOCAL + key)
    if not isinstance(d, dict):
        print(f"读取失败 http={s}  key={key}"); sys.exit(1)
    print(f"KEY   = {key}")
    print(f"ts    = {d.get('ts')}   version = {d.get('version')}")
    v = d.get("value", {})
    if "--raw" in sys.argv:
        print(json.dumps(v, ensure_ascii=False, indent=1)[:8000])
    else:
        print("-" * 70)
        show(v)
