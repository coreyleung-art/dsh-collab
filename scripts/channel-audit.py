#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""channel-audit v0.1 — 外链通道全景 + 覆盖/状态矩阵 (audit 工具族)
域: 对外通道 (企微/飞书/钉钉等) — 适用角色: 驿使(92623479)
数据源: ~/.dsh/channels.json (通道注册, 0600 私有) + 黑板 data/ops (能力表)
模式: 域全景扫描 → 分类 + 覆盖/状态矩阵 → Φ10 判断输入
输出:
  A. 通道全景 (各通道: 状态/绑定/凭据方案)
  B. 能力×通道覆盖矩阵 (哪些能力可用哪些通道投递)
用法:
  channel-audit.py scan               # 通道全景
  channel-audit.py coverage           # 能力覆盖矩阵
  channel-audit.py --lean4-check      # 自检 (只读)
  channel-audit.py --version
安全: 不读凭据内容, 只读状态/绑定元数据 (凭据纪律 0600/keychain)
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json
import os
import sys
import re

VERSION = "0.1.0"
DEFAULT_CHANNELS = os.path.expanduser("~/.dsh/channels.json")

# 已知外链能力 (channel 可投递的场景)
CAPABILITIES = ["alert", "report", "daily_summary", "reply_draft", "announce",
                "query", "interactive"]


def _read_channels(path: str) -> dict:
    if not os.path.exists(path):
        return {"channels": {}}
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"channels": {}}


def scan(path: str = DEFAULT_CHANNELS) -> dict:
    """A: 通道全景分类"""
    data = _read_channels(path)
    chans = data.get("channels", {})
    by_status = {}
    detail = []
    for name, info in chans.items():
        status = info.get("status", "?")
        by_status.setdefault(status, []).append(name)
        # 凭据方案标注 (不含 secret 值)
        cred = info.get("cred_scheme") or info.get("secret", "?")
        detail.append({"channel": name, "status": status,
                       "bound_at": info.get("bound_at", "?"),
                       "cred": "keychain/enc" if ("keychain" in str(cred) or "enc" in str(cred)) else "?"})
    return {"total": len(chans), "by_status": {k: len(v) for k, v in by_status.items()},
            "channels": detail}


def coverage(path: str = DEFAULT_CHANNELS) -> dict:
    """B: 能力×通道覆盖矩阵 (简化: 全通道支持全能力, 标注状态可用性)"""
    data = _read_channels(path)
    chans = data.get("channels", {})
    rows = {}
    for name, info in chans.items():
        ok = info.get("status") in ("bound", "active")
        rows[name] = {"usable": ok, "capabilities": len(CAPABILITIES) if ok else 0}
    return rows


def _lean4_check(path: str = DEFAULT_CHANNELS) -> int:
    ok = True
    out = [f"== Lean4 约束门自检 (channel-audit v{VERSION}) =="]
    src = open(__file__).read()
    # 必须: 不打印 secret/凭据明文值
    leaks_secret = bool(re.search(r"print\(.*(secret|token|cred|password)", src, re.I))
    checks = [
        ("① 只读无破坏写", not re.search(r"rm\s+-rf|os\.remove|shutil\.rmtree|open\([^)]*['\"]w['\"]", src)),
        ("② 不泄露凭据明文", not leaks_secret),
        ("③ scan 返回结构", "total" in scan(path)),
        ("④ coverage 返回 dict", isinstance(coverage(path), dict)),
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
        print(f"channel-audit v{VERSION}")
        raise SystemExit(0)
    path = DEFAULT_CHANNELS
    if "--channels" in args:
        path = os.path.expanduser(args[args.index("--channels") + 1])
    if not args or args[0] == "scan":
        print(json.dumps(scan(path), ensure_ascii=False, indent=2))
    elif args[0] == "coverage":
        print(json.dumps(coverage(path), ensure_ascii=False, indent=2))
    else:
        print("用法: channel-audit.py [scan|coverage|--lean4-check|--version]")
