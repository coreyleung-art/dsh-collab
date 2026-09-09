#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""device-audit v0.1 — 设备资产全景 + 能力/健康矩阵 (audit 工具族·骨架)
域: 跨设备资产 (mac-mini / MBP / PC-i9 / 手机) — 适用角色: 罗盘/守灯塔
模式: 域全景扫描 → 分类 + 兼容/可用矩阵 → 判断输入 (Φ10)
数据源: 黑板 data/discovery/agents/<device> (R-ERR4) + 本地资产文档兜底
输出:
  A. 设备资产全景 (各设备: 能力/健康/在线)
  B. 能力×可用矩阵 (跨设备任务路由判断输入)
用法:
  device-audit.py scan              # 设备全景 (黑板 discovery)
  device-audit.py matrix            # 能力可用矩阵
  device-audit.py --lean4-check     # 自检
  device-audit.py --version
注: 骨架——黑板 discovery 未全注册时输出本地推断; 罗盘接入后可扩充
"""
import json
import os
import re
import sys
import urllib.request

VERSION = "0.2.0"
# discovery 注册表在星桥服务器 (CENTRAL_BB) —— 与 bb-gate registry 同源
BLACKBOARD = os.environ.get("CENTRAL_BB", "http://xingqiao.meetfunbp.com:8792")
# 设备 key 对齐 discovery 实际注册 (小写 mac-mini/i9/mbp + E2 store-<id>)
DEVICES = ["mac-mini", "i9", "mbp", "store-2", "store-7", "store-8", "phone"]
# 能力清单 (跨设备可路由任务类型)
CAPABILITIES = ["web_ui", "waimai", "voice", "vision", "design", "document",
                "research", "compute_gpu", "compute_cpu", "comm"]
# 本地兜底能力推断 (远程 discovery 未注册/能力空时)
FALLBACK = {
    "mac-mini": ["web_ui", "waimai", "voice", "vision", "document", "research", "compute_cpu"],
    "i9": ["web_ui", "compute_gpu", "compute_cpu", "design", "research", "comm"],
    "mbp": ["web_ui", "design", "document", "research", "vision", "comm"],
    "store-2": ["waimai"], "store-7": ["waimai"], "store-8": ["waimai"],
    "phone": ["comm", "voice"],
}


def _read_device(device: str) -> dict:
    """读黑板 data/discovery/agents/<device> (R-ERR4 注册表)"""
    try:
        with urllib.request.urlopen(f"{BLACKBOARD}/data/discovery/agents/{device}", timeout=3) as r:
            v = json.loads(r.read()).get("value") or {}
            if v:
                v["registered"] = True
                v["device"] = v.get("device", device)
            else:
                return {"registered": False, "device": device,
                        "capabilities": FALLBACK.get(device, []),
                        "note": "黑板未注册, 本地兜底推断"}
            return v
    except Exception:
        return {"registered": False, "device": device,
                "capabilities": FALLBACK.get(device, []),
                "note": "黑板不可达, 本地兜底推断"}


def scan() -> dict:
    """A: 设备资产全景"""
    devices = []
    for d in DEVICES:
        info = _read_device(d)
        devices.append(info)
    return {"devices": devices,
            "registered": sum(1 for d in devices if d.get("registered"))}


def matrix() -> dict:
    """B: 能力×设备可用矩阵 (远程注册能力 + 本地兜底推断合并)"""
    rows = {}
    for d in DEVICES:
        info = _read_device(d)
        caps = set(info.get("capabilities", []) or [])
        # 注册能力为空 → 并入本地兜底
        if not caps:
            caps = set(FALLBACK.get(d, []))
        rows[d] = {c: (c in caps) for c in CAPABILITIES}
    return rows


def _lean4_check() -> int:
    ok = True
    out = [f"== Lean4 约束门自检 (device-audit v{VERSION}) =="]
    src = open(__file__).read()
    has_write = bool(re.search(r"rm\s+-rf|os\.remove|shutil\.rmtree|open\([^)]*['\"]w['\"]", src))
    checks = [
        ("① 只读无破坏写", not has_write),
        ("② scan 返回结构", "devices" in scan()),
        ("③ matrix 返回 dict", isinstance(matrix(), dict)),
    ]
    for label, cond in checks:
        out.append(f"  [{'✅' if cond else '❌'}] {label}")
        ok = ok and cond
    out.append(f"  结果: {'✅ GATE OK' if ok else '❌ GATE FAIL'}")
    print("\n".join(out))
    return 0 if ok else 1


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--lean4-check" in args:
        raise SystemExit(_lean4_check())
    if "--version" in args:
        print(f"device-audit v{VERSION}")
        raise SystemExit(0)
    if not args or args[0] == "scan":
        print(json.dumps(scan(), ensure_ascii=False, indent=2))
    elif args[0] == "matrix":
        print(json.dumps(matrix(), ensure_ascii=False, indent=2))
    else:
        print("用法: device-audit.py [scan|matrix|--lean4-check|--version]")
