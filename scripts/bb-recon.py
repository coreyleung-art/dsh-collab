#!/usr/bin/env python3
"""探索一个系统时的第一步：读它的自我声明。

由来（2026-09-14，HR 采纳并认领同一次）：
  我今晚探测了 7 个 HTTP 方法、读了根路径、读了 /api 与 /methods，就是没读 /help ——
  而 /help 一直在那里，它列出 11 个端点与 4 个方法。
  HR 也认领同一次，并且更重：它今晚【判断过黑板的能力边界】（如「无 keys-only 端点 ⇒
  枚举必返回全部值」），而那个判断若有 /help 佐证会更硬、更便宜。
⇒ 所以判据：凡断言一个系统的能力边界，须先读该系统的自我声明。
   有自我声明 ⇒ 读它（事实）；无自我声明 ⇒ 才需要论证（推理）。
⇒ 而这条判据本身也要变成一个步骤：本脚本就是那一步。

它做什么：按顺序尝试一个系统的自我声明入口，打印能力清单；并明确报告哪一层没有声明。
用法：python3 bb-recon.py [host:port]        默认 127.0.0.1:8792
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, sys, urllib.request, urllib.error

CANDIDATES = ["/help", "/", "/api", "/openapi.json", "/swagger.json", "/version", "/health"]


def probe(host, path):
    try:
        with urllib.request.urlopen(f"http://{host}{path}", timeout=10) as r:
            body = r.read()
            try:
                return (r.status, json.loads(body))
            except Exception:
                return (r.status, body[:200].decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return (e.code, None)
    except Exception as e:
        return (-1, type(e).__name__)


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:8792"
    print(f"=== 探索 {host} 的自我声明 ===\n")
    declared = False
    for path in CANDIDATES:
        st, data = probe(host, path)
        if st == 200 and isinstance(data, dict) and "endpoints" in data:
            declared = True
            eps = data["endpoints"]
            print(f"★ {path} —— 系统自己列出了能力（{len(eps)} 个端点）")
            methods = sorted({e.get("method") for e in eps})
            print(f"  方法集合：{methods}")
            for e in eps:
                print(f"    {e.get('method','?'):7} {e.get('path','?'):30} {e.get('desc','')[:60]}")
            for k, v in data.items():
                if k in ("endpoints",):
                    continue
                if isinstance(v, dict) and len(v) > 1:
                    print(f"\n  附加注册表 {k}：{len(v)} 项（前 3）")
                    for kk, vv in list(v.items())[:3]:
                        print(f"    {kk} → {json.dumps(vv, ensure_ascii=False)[:80]}")
                elif v:
                    print(f"\n  附加字段 {k}：{json.dumps(v, ensure_ascii=False)[:120]}")
            break
        else:
            print(f"  {path:16} ⇒ {st}" + ("（非能力清单）" if st == 200 else ""))
    print()
    if declared:
        print("⇒ 结论：该系统【自证了能力边界】。凡关于它能力的断言，引这份清单即可，不必论证。")
    else:
        print("⇒ 结论：未找到自证入口。此时关于它能力的断言【只能靠推理】—— 须显式声明这一点。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
