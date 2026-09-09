#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-write.py — 黑板统一写入工具（v0.5 配套）

用途：任何角色一行命令写 STATUS/结果到自己的职责命名空间（事件桥自动回流）。
用法：
  python3 bb-write.py <role> <key> '<json>'        # role 用短名或会话 id
  python3 bb-write.py 6ed4daf2 status '{"status":"idle"}'
  python3 bb-write.py recovery check '{"ok":true}' # 或用命名空间前缀名
示例：
  # 按注册表写入：短名 -> 自动补全 data/<ns>/
  python3 bb-write.py ops daily '{"date":"2026-08-23","orders":100}'
"""
import sys, json, urllib.request, urllib.parse

BB = "http://127.0.0.1:8792"

# 短名 -> 命名空间（与黑板 /ns-registry 的 role_ns 对齐）
ALIAS = {
    # 角色短名
    "6ed4daf2": "recovery", "recovery": "recovery", "自查": "recovery",
    "a3bc8cba": "learning", "learning": "learning", "学习": "learning",
    "aa528267": "ops", "45f89009": "ops", "ops": "ops", "运营": "ops",
    "4787d717": "investigate", "investigate": "investigate", "调查": "investigate",
    "0e84e65c": "supply-chain", "supply": "supply-chain", "供应链": "supply-chain",
    "ffb7c3ab": "qa", "qa": "qa",
    "54e809ed": "media", "media": "media", "媒体": "media",
    "55d4d1bd": "ingest", "ingest": "ingest", "摄取": "ingest",
    "2a15e6b1": "registry", "hr": "registry", "registry": "registry",
    "b193c782": "customer-service", "客服": "customer-service", "cs": "customer-service",
    "coordinator": "iterations", "iterations": "iterations", "协调": "iterations",
}

def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    role = sys.argv[1]
    key = sys.argv[2]
    try:
        value = json.loads(sys.argv[3])
    except json.JSONDecodeError:
        print("value 必须是 JSON（用单引号包：'{\"status\":\"ok\"}'）")
        sys.exit(1)
    ns = ALIAS.get(role)
    if not ns:
        print("未知角色: %s（可用: %s）" % (role, ", ".join(sorted(set(ALIAS.values())))))
        sys.exit(1)
    path = "/data/%s/%s" % (ns, key)
    body = json.dumps(value, ensure_ascii=False).encode()
    req = urllib.request.Request(BB + path, data=body, method="PUT",
                                 headers={"Content-Type": "application/json",
                                          "Content-Length": str(len(body))})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            resp = json.loads(r.read().decode())
            print("✅ 已写入 %s → %s (version=%s seq=%s)" % (path, key,
                  resp.get("version"), resp.get("seq")))
    except Exception as ex:
        print("❌ 写入失败: %s" % str(ex)[:150])
        sys.exit(1)

if __name__ == "__main__":
    main()
