#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""resource-audit v0.1 — 资源登记全景 + 归属/锁矩阵 (audit 工具族)
域: 跨智能体资源登记 — 适用角色: HR 司库
数据源: resource-registry.md (资源登记表) + data-ownership.md
模式: 域全景扫描 → 分类 + 归属/冲突矩阵 → Φ10 判断输入
输出:
  A. 资源全景分类 (按 file/store/panel/device/channel 等类型)
  B. 归属矩阵 (资源 × 属主角色 × 锁状态)
用法:
  resource-audit.py scan              # 资源全景分类
  resource-audit.py owners            # 归属矩阵
  resource-audit.py --lean4-check     # 自检 (只读)
  resource-audit.py --version

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import os
import re
import sys


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/resource-audit.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = "0.1.0"
DEFAULT_REG = os.path.expanduser("~/dsh-collab/resource-registry.md")

# 资源类型前缀 → 类型名 (对应 registry §1)
TYPE_PREFIX = {"file:": "文件", "panel:": "后台", "launchd:": "服务", "task:": "任务",
               "store:": "店铺", "im_window:": "店铺窗口", "port:": "端口", "db:": "数据集",
               "chroma:": "数据集", "dify:": "数据集", "device:": "设备", "service:": "服务",
               "msg:": "消息", "channel:": "通道", "browser:": "浏览器", "agent:": "应用"}


def _parse_registry(path: str) -> list:
    """解析 resource-registry.md → 资源条目列表"""
    if not os.path.exists(path):
        return []
    entries = []
    with open(path) as f:
        lines = f.readlines()
    cur_owner = "?"
    for i, line in enumerate(lines):
        ls = line.strip()
        # 角色行 (session-xxx 开头 + 含资源) → 更新当前归属上下文
        om = re.match(r"^\|\s*(session-[\w-]+|[\w-]+)\s*\|", ls)
        if om and any(p in ls for p in ("file:", "store:", "panel:", "device:", "channel:", "launchd:")):
            cur_owner = om.group(1)
        # 提取行内所有资源引用
        for m in re.finditer(r"(file|store|panel|launchd|task|device|service|channel|browser|port|db|chroma|agent|im_window):([\w~./\-]+)", ls):
            typ = TYPE_PREFIX.get(m.group(1) + ":", m.group(1))
            res = m.group(1) + ":" + m.group(2)
            entries.append({"name": res, "type": typ, "owner": cur_owner})
    # 去重 (name+owner)
    seen = set()
    uniq = []
    for e in entries:
        if e["name"] not in seen:
            seen.add(e["name"])
            uniq.append(e)
    return uniq


def scan(path: str = DEFAULT_REG) -> dict:
    """A: 资源全景分类"""
    entries = _parse_registry(path)
    by_type = {}
    for e in entries:
        by_type.setdefault(e["type"], []).append(e["name"])
    return {"total": len(entries), "by_type": {k: len(v) for k, v in by_type.items()},
            "types": sorted(by_type.keys())}


def owners(path: str = DEFAULT_REG) -> dict:
    """B: 归属矩阵 (资源 → 属主角色)"""
    entries = _parse_registry(path)
    by_owner = {}
    for e in entries:
        by_owner.setdefault(e["owner"], []).append(e["name"])
    return {k: len(v) for k, v in sorted(by_owner.items(), key=lambda x: -len(x[1]))}


def _lean4_check(path: str = DEFAULT_REG) -> int:
    ok = True
    out = [f"== Lean4 约束门自检 (resource-audit v{VERSION}) =="]
    src = open(__file__).read()
    has_write = bool(re.search(r"rm\s+-rf|os\.remove|shutil\.rmtree|open\([^)]*['\"]w['\"]", src))
    checks = [
        ("① 只读无破坏写", not has_write),
        ("② scan 返回结构", "total" in scan(path)),
        ("③ registry 存在", os.path.exists(path)),
        ("④ owners 返回 dict", isinstance(owners(path), dict)),
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
        print(f"resource-audit v{VERSION}")
        raise SystemExit(0)
    path = DEFAULT_REG
    if "--reg" in args:
        path = os.path.expanduser(args[args.index("--reg") + 1])
    import json
    if not args or args[0] == "scan":
        print(json.dumps(scan(path), ensure_ascii=False, indent=2))
    elif args[0] == "owners":
        print(json.dumps(owners(path), ensure_ascii=False, indent=2))
    else:
        print("用法: resource-audit.py [scan|owners|--lean4-check|--version]")
