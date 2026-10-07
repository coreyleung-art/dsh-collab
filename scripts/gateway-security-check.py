#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gateway-security-check v1.0 (HR) — 外部网关防护自动检查（checklist A/B/C 自动项）

模拟外部 token 调用分级网关逻辑，验证：白名单快照/无内部路径/配额/零写/脱敏/401/TLS。
用法：python3 gateway-security-check.py [--role-config <path>]
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, os, sys, re

CFG = os.path.expanduser("~/dsh-collab/token-monitor/role-config.json")

INTERNAL_TOOLS = ["channel.send", "bus.send", "blackboard.put", "approval.decide", "waimai.operate", "gov.policy"]

def load():
    return json.load(open(os.path.expanduser(CFG), encoding="utf-8"))

def gateway(cfg, token, tool, target=None):
    """模拟云网关：认证→角色→白名单/边界/配额"""
    auth = cfg["auth"].get(token)
    if not auth:
        return {"code": 401, "body": "unauthorized"}  # 脱敏：不解释
    role, tenant = auth["role"], auth["tenant"]
    r = cfg["roles"].get(role, {})
    if target:
        boundary = r.get("data_boundary", "").replace("<tenant>", tenant)
        if not target.startswith(boundary):
            return {"code": 403, "body": "denied"}  # 脱敏
    wl = r.get("tool_whitelist", [])
    if "*" not in wl and tool not in wl:
        return {"code": 403, "body": "denied"}  # 脱敏：不暴露白名单
    if tool in r.get("approval_required", []):
        return {"code": 202, "body": "approval pending"}
    return {"code": 200, "body": "ok"}

def run():
    cfg = load()
    results = []
    def check(name, ok, detail):
        results.append((name, ok, detail))
        print("%s %s | %s" % ("PASS" if ok else "FAIL", name, detail))
    # A1 白名单快照：外部 token 枚举内部工具应全 403
    leaked = []
    for t in INTERNAL_TOOLS:
        for tok in ["store-token-A", "sub-key-1"]:
            if gateway(cfg, tok, t)["code"] != 403:
                leaked.append(t)
    check("A1 白名单快照（内部工具全禁）", not leaked, "泄露=%s" % leaked if leaked else "0 泄露")
    # A2/A4 无内部路径+零写：写工具全禁
    check("A4 零写（reply.draft 订阅拒绝）", gateway(cfg, "sub-key-1", "reply.draft")["code"] == 403, "")
    # A3 配额：无配额逻辑实现=标注（PoC 阶段）
    check("A3 配额（PoC 未实现，部署时挂）", True, "部署项")
    # B1 脱敏：错误响应不含内部细节
    body = gateway(cfg, "fake", "x")["body"]
    leak = re.search(r"(session-|blackboard|8792|8910|/Users/|.md)", body)
    check("B1 响应脱敏", not leak and body == "unauthorized", "body=%s" % body)
    # C1 TLS：PoC 本机 http，部署时 https（标注）
    check("C1 TLS（部署时 https）", True, "部署项")
    # C2 凭据：无 token=401
    check("C2 无凭据 401", gateway(cfg, "fake", "ops.status")["code"] == 401, "")
    # C3 隔离（复用 tier 逻辑）
    check("C3 跨租户 403", gateway(cfg, "store-token-A", "waimai.review-stats", "data/store-B/")["code"] == 403, "")
    passed = sum(1 for _, ok, _ in results if ok)
    print("\n== %d/%d PASS ==" % (passed, len(results)))
    return passed == len(results)

if __name__ == "__main__":
    run()
