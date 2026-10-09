#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tier-gate-test v1.0 (HR) — 接入分级 PoC：本机模拟网关分级逻辑

认证(token)→角色(role/tenant)→网关过滤(工具白名单/数据边界/写权限/审批)→PASS/FAIL。
零 LLM。用法：python3 tier-gate-test.py

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== tier-gate-test 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · tier-gate-test v1.0 (HR) — 接入分级 PoC：本机模拟网关分级逻辑")
    print("  · 认证(token)→角色(role/tenant)→网关过滤(工具白名单/数据边界/写权限/审批)→PASS/FAIL。")
    print("  · 零 LLM。用法：python3 tier-gate-test.py")
    print("  · ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: json, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/tier-gate-test.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, os


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/tier-gate-test.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

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
