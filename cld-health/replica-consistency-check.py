#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""replica-consistency-check.py — 跨副本内容一致性检查（两级）
判据由 HR 提出并登记（三条件：①≥2 副本 ②存在未触达全部副本的写入路径 ③该单侧写入非幂等）；
本工具为该判据的执行体，不新增判据。实现：守灯（健康巡检域）· 设计经 HR 审阅（2026-09-11）

两级结构：
  一级 version 探针 —— 只标记，不判 RED（避免假失败）
  二级 内容哈希判据 —— 不一致即分叉（真 FAIL）
第三态 unknown —— 任一侧不可达/非200/无法哈希 ⇒ 独立成项，**绝不并入一致**

关键实现要点（均来自实测教训）：
  · 哈希只作用于 value 载荷（version/seq 是信封元数据，每次必变）
  · **先解包裹再取哈希**：value.body 若为可解析 JSON 字符串 ⇒ 解包后按语义比较
    （否则同一语义内容的序列化差异会造出假分叉 —— HR 2026-09-11 亲历 10 例假警报）
  · 框必须声明：未传 --prefix 时**拒绝运行**（禁静默全量）
  · 只读：仅 GET，不写任一复本、不写黑板
退出码：0=无分叉且判定完成 ｜ 1=检测到分叉（**优先于 3**）｜ 3=存在无法判定项 ｜ 2=自身错误
用法：
  replica-consistency-check.py --prefix data/registry/ [--prefix notes/]
  replica-consistency-check.py --key <key> [--key <key>]
  replica-consistency-check.py --selfcheck      # 真实正反控（正控=两张真分叉卡；反控=registry 真幂等重写）
"""
import argparse, hashlib, json, sys, urllib.request, datetime

REPLICAS = [("A-local", "127.0.0.1:8792"), ("B-central", "106.53.214.108:8792")]
TIMEOUT = 6

def get(host, key):
    try:
        with urllib.request.urlopen("http://%s/%s" % (host, key), timeout=TIMEOUT) as r:
            return r.status, json.loads(r.read().decode("utf-8", "ignore"))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return None, {"_err": str(e)[:60]}

def unwrap(o, _depth=0):
    """先解包裹：可解析为 JSON 的字符串按其语义内容参与比较。

    v0.2（守灯自测发现并修复）：v0.1 只解 `{` / `[` 开头的字符串 ⇒ **双重编码**的
    字符串（外层是 JSON 引号包裹，如 '"{\\"x\\":1}"'，首字符是引号）不会被解包 ⇒
    同一语义内容被判为分叉（我的单元用例『嵌套 body 字符串』即此失败）。
    现改为：任何 json.loads 可解析的字符串都递归解包（含引号包裹、数字、布尔），
    并以 _depth 上限防止构造性无限递归；解析不成功则原样返回（普通文本不受影响）。
    """
    if _depth > 5:
        return o
    if isinstance(o, dict):
        return {k: unwrap(v, _depth + 1) for k, v in o.items()}
    if isinstance(o, list):
        return [unwrap(x, _depth + 1) for x in o]
    if isinstance(o, str):
        s = o.strip()
        if not s:
            return o
        try:
            p = json.loads(s)
        except Exception:
            return o
        if isinstance(p, str) and p == o:
            return o                      # 防自反
        return unwrap(p, _depth + 1)
    return o

def canon(payload):
    return json.dumps(unwrap(payload), sort_keys=True, ensure_ascii=False, separators=(",", ":"))

def h(payload):
    return hashlib.md5(canon(payload).encode("utf-8")).hexdigest()

def compare(key):
    """返回状态与两侧身份信息。

    v0.3（守灯跑真实数据时发现并修复）：v0.2 把『仅单侧存在』也归入 unknown，
    实测 25 个 registry 采样里 21 例被误标『无法判定』——其实它们是**单侧写入**
    （中央 404），属**已知状态**而非不可判定。二者混同会：① 虚增 unknown 桶；
    ② 掩盖单写覆盖信号（而单写正是双写条文待决的核心量）。
    现四态分开：consistent / divergent / single-side / unjudgeable。
      注：单侧存在**不构成分叉**（不满足判据条件①『≥2 副本』），故不判 FAIL，
          仅作覆盖类信息输出（对双写决策有用）。
    """
    out = {"key": key, "A": None, "B": None, "verA": None, "verB": None,
           "hashA": None, "hashB": None, "diff_fields": [], "state": "unjudgeable",
           "why": "", "side": None}
    for label, host in REPLICAS:
        st, body = get(host, key)
        if st == 404:
            continue                     # 该复本无此键（不是错误）
        if st != 200 or not isinstance(body, dict) or "value" not in body:
            out["why"] = "%s: %s" % (label, ("HTTP %s" % st) if st else "unreachable")
            return out                   # 真·不可判定
        out[label[0]] = body
        out["ver" + label[0]] = body.get("version")
        out["hash" + label[0]] = h(body.get("value"))

    if out["A"] is None and out["B"] is None:
        out["state"] = "unjudgeable"; out["why"] = "两复本均无此键"
        return out
    if out["A"] is None or out["B"] is None:
        out["state"] = "single-side"
        out["side"] = "A-local-only" if out["B"] is None else "B-central-only"
        return out
    if out["hashA"] != out["hashB"]:
        out["state"] = "divergent"
        va, vb = unwrap(out["A"].get("value")), unwrap(out["B"].get("value"))
        if isinstance(va, dict) and isinstance(vb, dict):
            out["diff_fields"] = sorted(set(va) ^ set(vb)) or [
                k for k in set(va) & set(vb) if canon(va[k]) != canon(vb[k])]
        return out
    out["state"] = "consistent"
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", action="append", default=[])
    ap.add_argument("--key", action="append", default=[])
    ap.add_argument("--limit", type=int, default=0, help="有界采样：只查排序后前 N 键（0=不限，框内声明）")
    ap.add_argument("--concurrency", type=int, default=6, help="并发请求数（默认 6，避免压垮复本）")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.selfcheck:
        return selfcheck()

    if not a.prefix and not a.key:
        print("⛔ 拒绝运行：未声明范围。请传 --prefix <命名空间前缀>（可多次）或 --key <键>。")
        print("   原因：本工具遵守『框必须声明』——不预设范围、不静默全量。")
        return 2

    keys = list(a.key)
    if a.prefix:
        # v0.4（守灯端到端实测发现的 bug）: v0.3 只从 /data/ 取键 ⇒ notes/* 范围恒为 0。
        # 黑板各命名空间有独立列举端点（/data/ /notes/ /tasks/ …）⇒ 按前缀首段分组列举。
        segs = {}
        for p in a.prefix:
            segs.setdefault(p.split("/")[0], []).append(p)
        for seg, ps in segs.items():
            st, body = get("127.0.0.1:8792", seg + "/")
            if st != 200 or not isinstance(body, dict) or "list" not in body:
                print("⛔ 无法列举命名空间 %s/ ⇒ **框不完整，判定未完成**（不得静默按空范围报『一致』）" % seg)
                return 2
            keys += [k for k in (body.get("list") or {}) if any(k.startswith(x) for x in ps)]
        keys = sorted(set(keys))

    frame = {
        "取何时点": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "复本": [h for _, h in REPLICAS],
        "范围前缀": a.prefix or "(按 --key 指定)",
        "框内键数": len(keys),
        "采样": ("全量" if not a.limit or a.limit >= len(keys) else "前 %d 键（有界采样）" % a.limit),
        "并发": a.concurrency,
    }
    if a.limit and a.limit < len(keys):
        keys = keys[: a.limit]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max(1, a.concurrency)) as ex:
        rows = list(ex.map(compare, keys))
    div = [r for r in rows if r["state"] == "divergent"]
    unk = [r for r in rows if r["state"] == "unjudgeable"]
    ok = [r for r in rows if r["state"] == "consistent"]
    sng = [r for r in rows if r["state"] == "single-side"]
    probe = [r for r in rows if r["state"] == "consistent" and r["verA"] != r["verB"]]

    print("── 跨副本一致性检查 ──")
    print("框声明: 时点=%s ｜ 复本=%s ｜ 范围=%s ｜ 框内键数=%d ｜ 采样=%s ｜ 并发=%d"
          % (frame["取何时点"], " / ".join(frame["复本"]), frame["范围前缀"],
             frame["框内键数"], frame["采样"], frame["并发"]))
    if probe:
        print("\n[一级·version 探针] 只标记不 FAIL（提示存在单侧写入，可能是幂等重写）:")
        for r in probe[:20]:
            print("   ~ %s  vA=%s vB=%s（哈希相同）" % (r["key"], r["verA"], r["verB"]))
        print("   探针命中 %d 项" % len(probe))
    if div:
        print("\n[二级·内容哈希判据] **分叉**（非幂等单侧写入）:")
        for r in div:
            print("   ✗ %s  vA=%s/%s vB=%s/%s 差异字段=%s"
                  % (r["key"], r["verA"], (r["hashA"] or "")[:8], r["verB"], (r["hashB"] or "")[:8],
                     ",".join(r["diff_fields"][:6])))
    if sng:
        print("\n[单侧写入] 仅一个复本存在（**不构成分叉**——不满足判据①『≥2 副本』；覆盖类信息）:")
        for r in sng[:20]:
            print("   ○ %s  (%s)" % (r["key"], r["side"]))
        if len(sng) > 20:
            print("   … 共 %d 项" % len(sng))
    if unk:
        print("\n[第三态·无法判定] **不得并入一致**:")
        for r in unk[:20]:
            print("   ? %s  %s" % (r["key"], r["why"]))
    print("\n汇总: 一致=%d ｜ 分叉=%d ｜ 单侧写入=%d ｜ 无法判定=%d ｜ 探针标记=%d"
          % (len(ok), len(div), len(sng), len(unk), len(probe)))

    if div:
        return 1
    if unk:
        return 3
    return 0

def selfcheck(limit=25):
    """真实正反控（依据：真实负例比构造负例更有价值 —— HR 与守灯共同要求）

    v0.2：反控扫描改为**有界采样并声明框**（v0.1 枚举全部 registry 键 = 400+ 请求，
    曾整轮超时）。全量普查可用 limit=None。
    """
    print("── 自检：真实正反控 ──")
    pass_ = fail = 0
    # 正控：两张真分叉卡（notes/）
    pos = ["notes/mac-mini/resource-audit-report-20260911",
           "notes/mac-mini/subagent-burst-deepdive-20260911"]
    for k in pos:
        r = compare(k)
        good = (r["state"] == "divergent")
        print("   正控 %s → %s %s" % (k, r["state"], "OK" if good else "FAIL"))
        pass_, fail = (pass_ + 1, fail) if good else (pass_, fail + 1)
    # 反控：registry 真实幂等重写（version 不等、哈希应相同 ⇒ 不得判分叉）
    st, body = get("127.0.0.1:8792", "data/")
    allk = sorted(k for k in (body.get("list") or {}) if k.startswith("data/registry/")) if isinstance(body, dict) else []
    sample = allk if limit is None else allk[:limit]
    print("   反控框: registry 键共 %d，本次采样 %d（前 %s 个，有界采样）"
          % (len(allk), len(sample), limit if limit is not None else "全部"))
    idem = 0; falsepos = 0; unknown = 0
    for k in sample:
        r = compare(k)
        if r["state"] == "unjudgeable":
            unknown += 1; continue
        if r["verA"] != r["verB"] and r["state"] == "consistent":
            idem += 1
        if r["state"] == "divergent":
            falsepos += 1
    print("   反控结果 → 幂等重写 %d 例 ｜ 假分叉 %d 例 ｜ 无法判定 %d 例" % (idem, falsepos, unknown))
    if falsepos == 0:
        print("   反控 PASS：采样内无假分叉"); pass_ += 1
    else:
        print("   反控 FAIL：出现 %d 个分叉（若为序列化差异即假分叉）" % falsepos); fail += 1
    if idem > 0:
        pass_ += 1
    else:
        print("      ⚠️ 采样内未观察到幂等重写样本（反控未获证）")
    print("\n自检结果: %s（pass=%d fail=%d）" % ("PASS" if fail == 0 else "FAIL", pass_, fail))
    return 0 if fail == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
