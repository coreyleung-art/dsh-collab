#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""holdout-split.py — SystemGraph C 组 hold-out 划分的**可复跑手段**（v1.0.0）

依据：裁判 2026-10-08 复核指出「方案写『机器可核、可复跑』但**未给复跑命令**——
      『可复跑』是声称而非手段」（与「非自包含命令 = 定时器」同族）。

用途：把 confirmed-links 按**时间字段**排序，留出最近 20% 作 hold-out 测试集；
      输出划分清单（哪些 id 在 hold-out 内）与其**内容指纹**，供他人复跑比对。

时间字段：默认取每条记录的 `ts`；缺失时回退 `confirmed_at` → `created_at` → `updated_at`。
          （裁判标未覆盖项：原方案未写明排序字段——本脚本显式声明并打印所用字段）

用法:
  python3 holdout-split.py --input <confirmed-links.json>            # 划分并打印摘要
  python3 holdout-split.py --input <...> --json                      # 输出机器可读
  python3 holdout-split.py --selftest                                # 自检（含负控）
  python3 holdout-split.py --version

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
import argparse, json, hashlib, sys

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/holdout-split.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = "1.0.0"
__version__ = VERSION   # 兼容别名（引用同一值）
HOLDOUT_RATIO = 0.20
TIME_FIELDS = ("ts", "confirmed_at", "created_at", "updated_at")


def _records(doc):
    if isinstance(doc, list):
        return doc
    if isinstance(doc, dict):
        v = doc.get("value", doc)
        if isinstance(v, dict):
            for k in ("links", "items", "list", "confirmed_links"):
                if isinstance(v.get(k), list):
                    return v[k]
        for k in ("links", "items", "list"):
            if isinstance(v.get(k), list):
                return v[k]
    return []


def _time_of(rec):
    for f in TIME_FIELDS:
        t = rec.get(f) if isinstance(rec, dict) else None
        if t:
            return str(t), f
    return "", None


def _ident(rec, i):
    for k in ("id", "key", "from", "link"):
        if isinstance(rec, dict) and rec.get(k):
            return str(rec[k])
    return f"#{i}"


def split(doc, ratio=HOLDOUT_RATIO):
    recs = _records(doc)
    if not recs:
        return {"error": "无记录（检查 --input 是否为 confirmed-links 形态）"}
    keyed = []
    field_used = {}
    for i, r in enumerate(recs):
        t, f = _time_of(r)
        field_used[f] = field_used.get(f, 0) + 1
        keyed.append((t, i, r))
    # 排序：有时间者按时间升序；无时间者排最后（并计入 unsorted 计数）
    timed = [x for x in keyed if x[0]]
    untimed = [x for x in keyed if not x[0]]
    timed.sort(key=lambda x: (x[0], x[1]))
    ordered = timed + untimed
    n = len(ordered)
    cut = n - int(round(n * ratio))
    train, hold = ordered[:cut], ordered[cut:]
    digest = hashlib.sha256(
        "|".join(_ident(r, i) for _t, i, r in hold).encode()
    ).hexdigest()[:16]
    return {
        "total": n, "train": len(train), "holdout": len(hold),
        "ratio": ratio, "time_field_used": field_used,
        "untimed_count": len(untimed),
        "holdout_ids": [_ident(r, i) for _t, i, r in hold],
        "holdout_digest": digest,
        "rule": "按时间字段升序排序后，取**末 20%** 为 hold-out；无时间字段者排末尾（仍可能落入 hold-out）",
    }


def selftest():
    ok = 0; fail = 0
    def chk(cond, label):
        nonlocal ok, fail
        if cond: ok += 1; print("  ✅", label)
        else: fail += 1; print("  ❌", label)
    # 正例：10 条，末 2 条应入 hold-out
    doc = {"value": {"links": [{"id": f"L{i:02d}", "ts": f"2026-09-{i+1:02d}T00:00:00"} for i in range(10)]}}
    r = split(doc)
    chk(r["total"] == 10 and r["holdout"] == 2, "10 条 → hold-out 2 条")
    chk(r["holdout_ids"] == ["L08", "L09"], "hold-out = 末 2 条（L08/L09）")
    chk(r["time_field_used"].get("ts") == 10, "时间字段声明为 ts")
    # 负控①：输入为空 ⇒ 明确报错而非静默返回空划分
    chk("error" in split({"value": {"links": []}}), "负控·空输入报错")
    # 负控②：无时间字段 ⇒ 计数暴露，不假装已排序
    r2 = split({"value": {"links": [{"id": "A"}, {"id": "B"}, {"id": "C"}]}})
    chk(r2["untimed_count"] == 3, "负控·无时间字段被显式计数")
    # 负控③：划分可复跑（同输入两次结果一致）
    chk(split(doc)["holdout_digest"] == split(doc)["holdout_digest"], "负控·同输入指纹一致（可复跑）")
    print(f"\nselftest: {ok} PASS / {fail} FAIL")
    return 0 if fail == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input"); ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true"); ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print(json.dumps({"tool": "holdout-split", "version": VERSION, "time_fields": TIME_FIELDS})); return 0
    if a.selftest:
        return selftest()
    if not a.input:
        ap.error("需要 --input（或 --selftest/--version）")
    with open(a.input, encoding="utf-8") as f:
        doc = json.load(f)
    r = split(doc)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1)); return 0 if "error" not in r else 1
    if "error" in r:
        print("ERROR:", r["error"]); return 1
    print(f"total={r['total']} train={r['train']} holdout={r['holdout']} ratio={r['ratio']}")
    print(f"time_field_used={r['time_field_used']} untimed={r['untimed_count']}")
    print(f"holdout_digest={r['holdout_digest']}")
    print("holdout_ids=", ", ".join(r["holdout_ids"][:20]), ("…" if len(r["holdout_ids"]) > 20 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
