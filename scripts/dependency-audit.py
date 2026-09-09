#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dependency-audit v0.1 — 依赖全景分类 + peer 兼容矩阵 (audit 工具族·守链)
域: 软件依赖 (profiles/web)
模式: 域全景扫描 → 分类 + 兼容矩阵 → 判断输入 (Φ10 判断力)
输出:
  A. 依赖全景分类 (第三方npm/github / 本地自研link/file / 宿主)
  B. peer 兼容矩阵 (N插件 × rc声明 × 修复路径)
  C. 脆弱性快照 (github直链 / 版本失控 / 无peer / 崩过史)
用法:
  dependency-audit.py scan [--profile <path>]  # 全景扫描
  dependency-audit.py peer-matrix              # peer 兼容矩阵
  dependency-audit.py --lean4-check            # 自检 (只读无写)
  dependency-audit.py --version
"""
import json
import os
import re
import sys

VERSION = "0.1.0"
DEFAULT_PROFILE = os.path.expanduser("~/.dsh/profiles/web")

# 崩过历史 (可扩展登记)
KNOWN_FRAGILE = {"dsh-gov", "dsh-better-sidebar", "dsh-plugin-flower-cockpit",
                 "dsh-plugin-office", "@xberg-io/xberg"}


def _load_package(profile: str) -> dict:
    with open(os.path.join(profile, "package.json")) as f:
        return json.load(f)


def _load_plugin_pkg(profile: str, name: str) -> dict:
    try:
        with open(os.path.join(profile, "node_modules", name, "package.json")) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def scan(profile: str = DEFAULT_PROFILE) -> dict:
    """A+C: 依赖全景分类 + 脆弱性快照"""
    pkg = _load_package(profile)
    deps = pkg.get("dependencies", {})
    bundles = set(pkg.get("dsh", {}).get("profile", {}).get("bundles", []))
    result = {"third_party": [], "local": [], "host": [], "fragile": []}
    for name, spec in deps.items():
        entry = {"name": name, "spec": spec, "in_bundles": name in bundles}
        if spec.startswith(("link:", "file:")):
            entry["type"] = "local"
            result["local"].append(entry)
        elif name.startswith("@deepseek-ai/"):
            entry["type"] = "host"
            result["host"].append(entry)
        else:
            entry["type"] = "github" if spec.startswith("github:") else "npm"
            if name in KNOWN_FRAGILE:
                entry["fragile"] = "崩过史"
                result["fragile"].append(entry)
            result["third_party"].append(entry)
    result["stats"] = {k: len(v) for k, v in result.items()
                       if k in ("third_party", "local", "host")}
    return result


def peer_matrix(profile: str = DEFAULT_PROFILE) -> dict:
    """B: peer 兼容矩阵 (N插件 × rc声明 × 修复路径)"""
    pkg = _load_package(profile)
    bundles = pkg.get("dsh", {}).get("profile", {}).get("bundles", [])
    matrix = []
    for b in bundles:
        if b.startswith("@deepseek-ai/"):
            continue
        bp = _load_plugin_pkg(profile, b)
        if not bp:
            continue
        peers = bp.get("peerDependencies", {})
        rc_peers = {k: v for k, v in peers.items() if re.search(r"rc\.\d|\.c\.\d", v)}
        if not rc_peers:
            continue
        all_caret = all(v.startswith("^") for v in rc_peers.values())
        matrix.append({
            "plugin": b, "version": bp.get("version", "?"),
            "rc_count": len(rc_peers), "all_caret": all_caret,
            "fix": "放宽 ^0.1.1-rc.2" if all_caret else "源码/升级",
            "rc_versions": sorted(set(rc_peers.values())),
        })
    return matrix


def _lean4_check(profile: str = DEFAULT_PROFILE) -> int:
    """R006-⑩ 自检: 证明只读扫描无写路径"""
    ok = True
    out = [f"== Lean4 约束门自检 (dependency-audit v{VERSION}) =="]
    src = open(__file__).read()
    write_patterns = [r"rm\s+-rf", r"os\.remove", r"shutil\.rmtree", r"write\s*\("]
    has_write = any(re.search(p, src) for p in write_patterns)
    checks = [
        ("① 只读无破坏写", not has_write),
        ("② scan 返回结构", isinstance(scan(profile).get("stats"), dict)),
        ("③ profile 存在", os.path.isdir(profile)),
        ("④ peer_matrix 返回 list", isinstance(peer_matrix(profile), list)),
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
        print(f"dependency-audit v{VERSION}")
        raise SystemExit(0)
    if not args or args[0] == "scan":
        print(json.dumps(scan(), ensure_ascii=False, indent=2))
    elif args[0] == "peer-matrix":
        print(json.dumps(peer_matrix(), ensure_ascii=False, indent=2))
    else:
        print(f"用法: dependency-audit.py [scan|peer-matrix|--lean4-check|--version]")
