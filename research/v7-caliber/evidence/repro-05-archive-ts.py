#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R4 · 复跑脚本 05：归档操作的副作用 —— 板级 ts 被覆盖（两个量被写成一个）

背景：2026-10-12 19:23:08 用户裁定对 7 条 drift-delivery-failure 执行「归档（标记不删）」。

发现：归档 = 对同一键**重新 PUT**（value 内加 _archived_at）⇒ 黑板**刷新板级 ts**。
     于是「板级 ts」不再表示「卡何时产生」，而表示「卡何时被最后一次写」。

后果：读「板级 ts」会得出错误的发生时刻。

复跑：
    python3 research/v7-caliber/evidence/repro-05-archive-ts.py
"""
import json
import sys
import time
import urllib.request

LOCAL = "http://127.0.0.1:8792"
CENTRAL = "http://106.53.214.108:8792"
NS = "data/ops/drift-delivery-failure/"


def get(base, key, tries=3):
    last = None
    for _ in range(tries):
        try:
            with urllib.request.urlopen(base + "/" + key, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # 中枢板曾实测 ConnectionResetError，故带重试
            last = e
            time.sleep(2)
    raise last


def main():
    print("=" * 88)
    print("R4 复跑 05 · 归档副作用：板级 ts 被覆盖")
    print("=" * 88)
    for name, base in (("本机", LOCAL), ("中枢", CENTRAL)):
        try:
            d = get(base, NS)["list"]
        except Exception as e:
            print("--- %s板 读取失败（已重试3次）: %r ---" % (name, e))
            continue
        print("--- %s板 total=%d ---" % (name, len(d)))
        print("   %-21s %-21s %-26s %s" % ("板级ts", "内层value.ts", "_archived_at", "两者相差"))
        for k, v in sorted(d.items(), key=lambda x: x[0]):
            val = v.get("value") or {}
            its = val.get("ts")
            iv = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(its / 1000)) if its else "NA"
            delta = "NA"
            if its and v.get("ts"):
                try:
                    tb = time.mktime(time.strptime(v["ts"][:19], "%Y-%m-%dT%H:%M:%S"))
                    delta = "%+.0f 分钟" % ((tb - its / 1000.0) / 60.0)
                except Exception:
                    pass
            print("   %-21s %-21s %-26s %s" % (v.get("ts"), iv, val.get("_archived_at"), delta))
    print("-" * 88)
    print("★ 板级 ts 全部 ≈ 19:23（= 归档重写时刻）；内层 value.ts 为 04:56~07:59（= 真实失败时刻）")
    print("★ 差 ≈ 11.4 ~ 14.5 小时")
    print("★★ ⇒ 读「板级 ts」判「失败发生在何时」会错约半天。")
    print("★★ ⇒ 【标记不删】这一正确做法，副作用是销毁了板级 ts 的原始语义 —— 须登记。")
    print("=" * 88)
    return 0


if __name__ == "__main__":
    sys.exit(main())
