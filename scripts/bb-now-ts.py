#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-now-ts.py — 输出标准时刻串（卡 ts 用）v1.0.0

★★ 为什么需要它（2026-10-14 本会话自查）：
  灯塔发出的 56 张卡里 49 张的 payload.ts 是【手写递增】的，最大偏差 +12h53m。
  根因：在可取证的地方用了推理（时刻一条命令就能读）。
  ⇒ 此后 ts 一律走本工具，不手写。

用法: bb-now-ts.py          # 2026-10-14T01:25+0800
      bb-now-ts.py --iso    # 2026-10-14T01:25:30+08:00
"""
import sys, datetime
now = datetime.datetime.now().astimezone()
if "--iso" in sys.argv:
    print(now.strftime("%Y-%m-%dT%H:%M:%S%z")[:-2] + ":" + now.strftime("%z")[-2:])
else:
    print(now.strftime("%Y-%m-%dT%H:%M%z"))
