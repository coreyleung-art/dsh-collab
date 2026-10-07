#!/usr/bin/env python3
"""board-publish.py —— 黑板发布/核验（守灯 2026-09-11，根因教训固化）

为什么需要它（实测根因，见卡 data/cld-health/blackboard-key-route-rootcause-20260911）：
  黑板**键名 = URL 路径原样（含前缀）**。写 `/api/v1/kv/<KEY>` 实存的键是
  `api/v1/kv/<KEY>`，**不是** `<KEY>`；而用同一路径回读**永远 200、完全自洽**
  ⇒ 「PUT 200 + 回读成功」**不构成对端可见性证据**。
  本工具强制：① 写**规范键**（绝不用 api 前缀）② 写**双副本**
  ③ 回读**用对端的读法**（规范键 × 两副本）④ 比对两副本内容哈希。

用法:
  board-publish.py put  <key> <payload.json>   # 发布（规范键 × 双副本）+ 核验
  board-publish.py check <key>                 # 只核验既有卡（本机+中央）
  board-publish.py list  <prefix>              # 列某前缀下的键（规范读法）
退出码: 0=全部通过 1=核验失败 2=用法/输入错误

硬约束（防止重犯）:
  · 拒绝含 'api/' 前缀的键（写入即会落到错误的键名空间）
  · 要求键首段为纯小写字母命名空间（`data`/`notes`/`tasks`…），否则黑板返回 400
"""
import sys, json, hashlib, urllib.request, urllib.error

REPLICAS = [("local", "http://127.0.0.1:8792"),
            ("central", "http://106.53.214.108:8792")]


def _get(base, key, timeout=15):
    try:
        with urllib.request.urlopen(f"{base}/{key}", timeout=timeout) as r:
            return json.load(r).get("value")
    except urllib.error.HTTPError as e:
        return {"__http__": e.code}
    except Exception as e:
        return {"__err__": str(e)}


def _put(base, key, value, timeout=20):
    body = json.dumps(value, ensure_ascii=False).encode()
    req = urllib.request.Request(f"{base}/{key}", data=body, method="PUT",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return f"ERR {e}"


def key_guard(key):
    if "api/" in key or key.startswith("api"):
        return "键含 'api/' 前缀 —— 会落到错误键名空间（黑板键名=URL路径原样）。去掉该前缀。"
    first = key.split("/")[0]
    if not first.isalpha() or not first.islower():
        return f"首段命名空间 '{first}' 非纯小写字母（黑板将返回 400 bad key）。"
    if "/" not in key:
        return "单段键不是有效存储键（会被当作命名空间列举）。"
    return None


def canon(fp):
    v = fp.get("value", fp) if isinstance(fp, dict) else fp
    return hashlib.md5(json.dumps(v, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]


def nf(v):
    return len(v) if isinstance(v, dict) else (f"list({len(v)})" if isinstance(v, list) else "?")


def cmd_put(key, path):
    err = key_guard(key)
    if err:
        print(f"⛔ 拒绝: {err}")
        return 2
    try:
        payload = json.load(open(path))
    except Exception as e:
        print(f"⛔ 载荷不是合法 JSON: {e}")
        return 2
    print(f"发布 `{key}`（规范键 × 双副本）")
    for name, base in REPLICAS:
        st = _put(base, key, payload)
        print(f"  PUT {name:8s} -> {st}")
    return cmd_check(key)


def cmd_check(key):
    err = key_guard(key)
    if err:
        print(f"⛔ 拒绝: {err}")
        return 2
    print(f"核验 `{key}`（**用对端的读法：规范键 × 两副本**）")
    hashes, ok = {}, True
    for name, base in REPLICAS:
        v = _get(base, key)
        if isinstance(v, dict) and ("__http__" in v or "__err__" in v):
            print(f"  ❌ {name:8s} 不可达: {v}")
            ok = False
            continue
        h = canon(v)
        hashes[name] = h
        print(f"  {'✅' if True else ' '} {name:8s} 字段={nf(v):<8} hash={h}")
    if len(hashes) == 2 and len(set(hashes.values())) != 1:
        print("  ⚠ 两副本内容**不一致**（副本分叉）—— 按四态纪律记 divergent，不得记为 consistent")
        ok = False
    print("结果:", "✅ 规范键双副本可达且内容一致" if ok else "❌ 核验失败（对端读不到或不一致）")
    return 0 if ok else 1


def cmd_list(prefix):
    for name, base in REPLICAS:
        v = _get(base, prefix)
        if isinstance(v, dict) and ("__http__" in v or "__err__" in v):
            print(f"  ❌ {name:8s} {v}")
            continue
        L = v.get("list") if isinstance(v, dict) else v
        ks = [str(x.get("key") if isinstance(x, dict) else x) for x in (L or [])]
        print(f"  {name:8s} 键数={len(ks)}  样例={ks[:3]}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    c = sys.argv[1]
    if c == "put" and len(sys.argv) == 4:
        sys.exit(cmd_put(sys.argv[2], sys.argv[3]))
    if c == "check" and len(sys.argv) == 3:
        sys.exit(cmd_check(sys.argv[2]))
    if c == "list" and len(sys.argv) == 3:
        sys.exit(cmd_list(sys.argv[2]))
    print(__doc__)
    sys.exit(2)
