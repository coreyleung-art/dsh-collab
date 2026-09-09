#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tier-gate-test v1.0 (HR) — 接入分级 PoC：本机模拟网关分级逻辑

认证(token)→角色(role/tenant)→网关过滤(工具白名单/数据边界/写权限/审批)→PASS/FAIL。
零 LLM。用法：python3 tier-gate-test.py
"""
import json, os

CFG = os.path.expanduser("~/dsh-collab/token-monitor/role-config.json")

def load():
    return json.load(open(CFG, encoding="utf-8"))

def check(cfg, token, tool, target=None):
    """模拟网关：认证→角色→过滤。返回 (allow, reason)"""
    auth = cfg["auth"].get(token)
    if not auth:
        return (False, "401 unauthorized")
    role = auth["role"]
    tenant = auth["tenant"]
    r = cfg["roles"].get(role, {})
    # 数据边界
    if target:
        boundary = r.get("data_boundary", "").replace("<tenant>", tenant)
        if not target.startswith(boundary):
            return (False, "403 tenant boundary: %s not in %s" % (target, boundary))
    # 工具白名单
    wl = r.get("tool_whitelist", [])
    if "*" not in wl and tool not in wl:
        return (False, "403 tool not whitelisted: %s" % tool)
    # 审批要求
    if tool in r.get("approval_required", []):
        return (True, "approval_required (L3 escalate)")
    # 写权限
    if tool not in r.get("writes", []) and tool not in ("ops.status", "report.read", "knowledge.search", "ops.alerts", "waimai.review-stats", "waimai.state"):
        return (True, "read-only allow")
    return (True, "allow")

def run():
    cfg = load()
    cases = [
        # (name, token, tool, target, expect_allow, expect_hint)
        ("门店A-本店评价", "store-token-A", "waimai.review-stats", "data/store-A/review", True, ""),
        ("门店A-跨店隔离", "store-token-A", "waimai.review-stats", "data/store-B/review", False, "403"),
        ("门店A-改价审批", "store-token-A", "price.change", "data/store-A/", True, "approval_required"),
        ("门店A-回复草稿", "store-token-A", "reply.draft", "data/store-A/", True, "allow"),
        ("门店A-访问监察", "store-token-A", "ops.status", None, False, "403 tool not whitelisted"),
        ("订阅-读报告", "sub-key-1", "report.read", "data/sub-1/", True, "allow"),
        ("订阅-写回复", "sub-key-1", "reply.draft", "data/sub-1/", False, "403 tool not whitelisted"),
        ("订阅-访问门店", "sub-key-1", "report.read", "data/store-A/", False, "403 tenant boundary"),
        ("无token", "fake", "ops.status", None, False, "401"),
    ]
    passed = 0
    for name, token, tool, target, expect, hint in cases:
        allow, reason = check(cfg, token, tool, target)
        ok = (allow == expect)
        passed += ok
        print("%s %-4s | %-18s %-10s | %s" % ("PASS" if ok else "FAIL", name, token, tool, reason))
    print("\n== %d/%d PASS ==" % (passed, len(cases)))
    return passed == len(cases)

if __name__ == "__main__":
    run()
