#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-write-verify.py — 黑板写入的**独立回读校验**（目标要求「比 payload sha」的可执行实现）。

★ 为什么不能直接比原始字节（2026-10-10 实测）：
  黑板**会重新排列键序** —— 写入 `{z_last_key:…, a_first_key:…}`，读回变成字母序
  `{a_first_key:…, z_last_key:…}`。
  而**内容逐字节保真**：两边**规范化（sort_keys）后 sha256 完全相等**。
  ⇒ 因此判据必须是「**规范化后比 sha**」：
    · 比原始字节 ⇒ **恒假红**（键序必然不同）
    · 只比字段   ⇒ 若板子日后引入类型强转，字段检查照样通过 ⇒ **假绿**
    · 规范化 sha ⇒ 两种错都拦得住 ✅

★ 为什么必须"独立回读"而不是信写入端自报：
  目标明写「不信 `bb_dualwrite` 的 `values_equal`」—— 它比的是**板对板**，
  不比**我发出去的 payload**，故它有假绿缺陷。本工具比的是
  **「我发出去的规范化 payload」⨯「我独立读回来的规范化 payload」**，两端都是我自己取的。

用法：
  python3 bb-write-verify.py --key notes/mac-mini/xxx --file card.json          # 从文件写
  python3 bb-write-verify.py --key notes/mac-mini/xxx --stdin < card.json       # 从 stdin 写
  python3 bb-write-verify.py --key notes/mac-mini/xxx --verify-only             # 只校验现有值
  python3 bb-write-verify.py --key notes/mac-mini/xxx --verify-only --expect-file card.json

退出码：0 = 规范化 sha 相等 · 1 = 不等（列差异）· 2 = 用法/环境错误
"""
import argparse
import hashlib
import json
import sys
import urllib.request

BB = "http://127.0.0.1:8792"


def canon(obj) -> str:
    """规范化：排序键 + 紧凑分隔符 + 不转义非 ASCII。**这是判据的统一口径。**"""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha_of(obj) -> str:
    return hashlib.sha256(canon(obj).encode("utf-8")).hexdigest()


def put(key: str, obj) -> int:
    body = json.dumps(obj, ensure_ascii=False).encode()
    req = urllib.request.Request(
        f"{BB}/{key}", data=body, method="PUT",
        headers={"Content-Type": "application/json", "Content-Length": str(len(body))})
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status


def read_value(key: str):
    """★ 只取信封的 value 层（板子包 {key,ts,value,version}；读错层是历史翻车点）。"""
    with urllib.request.urlopen(f"{BB}/{key}", timeout=10) as r:
        env = json.loads(r.read().decode())
    if not isinstance(env, dict) or "value" not in env:
        raise ValueError(f"信封结构异常：顶层键 = {list(env.keys()) if isinstance(env, dict) else type(env)}")
    return env["value"]


def diff_summary(a, b, limit=12):
    """顶层键与逐键差异（只用于**人读**；判据是 sha，不是这个）。"""
    out = []
    ka, kb = set(a.keys()), set(b.keys())
    if ka - kb:
        out.append(f"  只在我方有：{sorted(ka - kb)}")
    if kb - ka:
        out.append(f"  只在板上有：{sorted(kb - ka)}")
    for k in sorted(ka & kb):
        if canon(a[k]) != canon(b[k]):
            out.append(f"  值不同 [{k}]：我={canon(a[k])[:60]} 板={canon(b[k])[:60]}")
            if len(out) >= limit:
                out.append("  …（截断）")
                break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--file")
    ap.add_argument("--stdin", action="store_true")
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("--expect-file", help="verify-only 时用来比对的期望 payload")
    a = ap.parse_args()

    if a.file and a.stdin:
        print("用法错误：--file 与 --stdin 只能给一个", file=sys.stderr)
        return 2

    mine = None
    if a.expect_file:
        with open(a.expect_file, encoding="utf-8") as f:
            mine = json.load(f)

    if not a.verify_only:
        try:
            if a.stdin:
                mine = json.loads(sys.stdin.read())
            elif a.file:
                with open(a.file, encoding="utf-8") as f:
                    mine = json.load(f)
        except Exception as e:
            print(f"用法错误：载荷读不进来（{e}）", file=sys.stderr)
            return 2
        if mine is None:
            print("用法错误：未给 --file/--stdin，也不是 --verify-only", file=sys.stderr)
            return 2
        try:
            st = put(a.key, mine)
        except Exception as e:
            print(f"环境错误：写盘失败（{e}）", file=sys.stderr)
            return 2
        print(f"PUT {a.key} → {st}")

    try:
        got = read_value(a.key)
    except Exception as e:
        print(f"环境错误：回读失败（{e}）", file=sys.stderr)
        return 2

    if mine is None:
        print(f"（verify-only 且未给 --expect-file ⇒ 只回报现状）")
        print(f"  key={a.key}  规范化 sha={sha_of(got)[:16]}  顶层键={len(got)}")
        return 0

    sm, sg = sha_of(mine), sha_of(got)
    print(f"规范化 sha（我发的）  {sm}")
    print(f"规范化 sha（读回的）  {sg}")
    if sm == sg:
        print("  ✅ 逐字节等价（规范化后）—— 写入与读回语义完全一致")
        return 0
    print("  ❌ 不等 —— 差异如下（★ 这才是真的漂，不是键序问题）：")
    for line in diff_summary(mine, got):
        print(line)
    return 1


if __name__ == "__main__":
    sys.exit(main())
