#!/usr/bin/env python3
"""central-availability-probe.py —— 中央侧「入口轴·可达性」子项的可复现测量

背景：守灯在 data/cld-health/cross-table-empty-cell-20260911 中报过
「≈2,400 次 GET / 仅 3 例 unreachable / 可用率 >99.8%」，**但无落盘证据**
（属回忆值）⇒ 本条把它降级为可复现测量：固定路由、固定键集、固定 N、落盘。

纪律:
  · **必须用同一个读法测两副本**（黑板键名=URL 路径原样；换路由即换对象）
  · 只读（GET），不写测试数据（不污染复本）
  · 输出的可用率必须带 frame（键集/次数/时点/发起节点/路由）
  · 失败必须分类（超时 / 4xx / 5xx / 连接错），不得把 404 当成不可达
    ——404 = 语法通过但不存在，**是可达的证据**，不是失败

用法: central-availability-probe.py [N]        # N=每副本请求数上限，默认 120
输出: 控制台摘要 + 落盘 JSON（含逐次结果）
"""
import sys, json, time, urllib.request, urllib.error, os

B = "http://127.0.0.1:8792"
C = "http://106.53.214.108:8792"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 120
OUT = os.path.expanduser("~/dsh-collab/cld-health/central-availability-probe.json")

# 探测键集：混合 存在 / 不存在 / 非法 —— 三态都要打
EXIST = ["data/cld-health/blackboard-key-route-rootcause-20260911",
         "data/cld-health/item18-disk-top-consumer-20260911",
         "data/registry/hr-reply-shoudeng-quantifier-20260911"]
ABSENT = ["data/cld-health/__probe-absent__"]
BAD = ["cld-health/foo"]           # 非法键（首段非纯小写字母）⇒ 期望 400

def one(base, key, timeout=8):
    t0 = time.time()
    try:
        with urllib.request.urlopen(f"{base}/{key}", timeout=timeout) as r:
            r.read(64)
            return ("ok", r.status, round((time.time()-t0)*1000, 1), None)
    except urllib.error.HTTPError as e:
        # 4xx = 板子应答了 ⇒ 可达（可达性意义上的成功应答）
        return ("answered", e.code, round((time.time()-t0)*1000, 1), None)
    except Exception as e:
        return ("unreachable", None, round((time.time()-t0)*1000, 1), type(e).__name__)

def probe(base, name):
    rows = []
    cycle = EXIST + ABSENT + BAD
    i = 0
    while len(rows) < N:
        k = cycle[i % len(cycle)]; i += 1
        rows.append({"key": k, "result": one(base, k)})
    cls = {}
    for r in rows:
        cls[r["result"][0]] = cls.get(r["result"][0], 0) + 1
    lat = sorted(r["result"][2] for r in rows if r["result"][2] is not None)
    unreachable = [r for r in rows if r["result"][0] == "unreachable"]
    return {"replica": name, "base": base, "n": len(rows), "class": cls,
            "unreachable_examples": [r["result"][3] for r in unreachable[:5]],
            "latency_ms": {"p50": lat[len(lat)//2] if lat else None,
                           "p95": lat[int(len(lat)*0.95)] if lat else None,
                           "max": lat[-1] if lat else None,
                           "min": lat[0] if lat else None},
            "availability": round(1 - len(unreachable)/len(rows), 6),
            "rows": rows}

print(f"入口轴·可达性探测  路由=直接路径 `/<key>`（两副本同一读法）  N/副本={N}")
res = [probe(B, "local"), probe(C, "central")]
for r in res:
    print(f"  {r['replica']:8s} n={r['n']:4d} 分类={r['class']} 可用率={r['availability']:.4f} "
          f"延迟 p50={r['latency_ms']['p50']}ms p95={r['latency_ms']['p95']}ms")
    if r["unreachable_examples"]:
        print(f"           不可达样例: {r['unreachable_examples']}")

doc = {"tool": "central-availability-probe.py", "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "frame": {"keys": EXIST + ABSENT + BAD, "n_per_replica": N,
                 "route": "direct path /<key> (same read form on both replicas)",
                 "origin_node": "mac-mini (守灯)", "readonly": True},
       "limits": ["只测从本机到两副本的 GET 可达性", "不测写路径/鉴权门/schema 门",
                  "4xx 计入『可达』（板子有应答）⇒ 本指标不含鉴权语义",
                  "单节点视角，不代表其他节点"],
       "results": res}
json.dump(doc, open(OUT, "w"), ensure_ascii=False, indent=1)
print(f"落盘 → {OUT}")
