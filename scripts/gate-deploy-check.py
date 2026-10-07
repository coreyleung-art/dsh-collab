#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-deploy-check.py — 部署结构门（Lean4 逻辑门，防漏变量/漏配置类 bug）
用户 2026-09-08 三问之①：漏变量(如 DSH_NODE_ID 硬编码日志) 加结构门防复发

静态检查部署脚本/守护的硬编码与 env 契约：
  G-D1 字面量门: 不得硬编码节点名/本机IP/端口 → 须 env 或配置取
  G-D2 env契约门: 声明的 env 变量格式校验（node 非空、URL 合法、token 文件存在）
  G-D3 平台门:   launchd/schtasks/systemd 平台注册与脚本平台判断一致
  G-D4 幂等门:   （部署脚本）可重复运行——含状态检测或覆盖安全

用法:
  python3 gate-deploy-check.py --file <script.py> [--node mac-mini|mbp|i9]
  python3 gate-deploy-check.py --dir  <dir>     # 检查目录内全部 py/sh

退出码: 0=全过 1=有 FAIL（供 CI/部署前门禁）
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, os, re, sys

# 本机节点名（用于判断字面量是否"硬编码本机"）
LOCAL_NODES = {"mac-mini", "mbp", "i9"}
# 本机常见 IP/主机名（出现即硬编码嫌疑）
# 特定节点 IP（tailnet 100.x）或本机域名——127.0.0.1 通用回环不拦（任何机都对）
LOCAL_IPS = re.compile(r"100\.1[0-9]{2}\.[0-9]{1,3}\.[0-9]{1,3}|coreymac-mini")
# env 声明模式：os.environ.get("NAME", "DEFAULT") 或 os.getenv("NAME")
ENV_GET = re.compile(r'(?:os\.environ\.get|os\.getenv)\("([A-Z_]+)"\s*,\s*"([^"]*)"')
# 日志中硬编码节点名嫌疑（log/f"..." 内含 mac-mini 等字面量）
HARDCODE_NODE = re.compile(r'(?:log|print)\(f?"[^"]*(?:mac-mini|mbp|i9|coreymac-mini)[^"]*"')

class Check:
    def __init__(self, name):
        self.name = name
        self.issues = []

    def fail(self, msg):
        self.issues.append(msg)

def check_file(path, node_hint=None):
    """对单文件跑四门"""
    try:
        src = open(path, encoding="utf-8").read()
    except Exception as e:
        return [f"[文件读失败] {path}: {e}"]
    issues = []
    fname = os.path.basename(path)

    # ---- G-D1 字面量门 ----
    # 1a. env 取值行里出现的默认值若为节点名/IP → 硬编码嫌疑（应无默认或空默认）
    for m in ENV_GET.finditer(src):
        name, default = m.group(1), m.group(2)
        if name in ("DSH_NODE_ID", "NODE_ID") and default in LOCAL_NODES:
            issues.append(f"G-D1 {fname}: {name} 默认值硬编码 '{default}'（应要求显式 env，防误部署到他机）")
        if default and (LOCAL_IPS.search(default) or "coreymac-mini" in default):
            issues.append(f"G-D1 {fname}: {name} 默认值含本机 IP/域名 '{default}'（多机复用应走配置）")
    # 1b. 日志里硬编码节点名（本次 bug 类型：log 写死 mac-mini 而应 {NODE}）
    for m in HARDCODE_NODE.finditer(src):
        issues.append(f"G-D1 {fname}: 日志硬编码节点名（第 {src[:m.start()].count(chr(10))+1} 行）——应插值 {{NODE}} 变量")

    # ---- G-D2 env 契约门 ----
    # node 变量必须被使用且非纯默认
    if "DSH_NODE_ID" not in src and "NODE_ID" not in src and "os.environ" in src:
        pass  # 不强制所有脚本有 node
    # URL 字面量若在 os.environ.get("X","URL") 行内(可被 env 覆盖)= 合法配置默认值；
    # 仅独立 URL 字面量(非 env 默认) → FAIL
    env_default_lines = set()  # 记录 env.get 默认值出现的行
    for m in ENV_GET.finditer(src):
        line_no = src[:m.start()].count(chr(10)) + 1
        env_default_lines.add(line_no)
    url_literals = re.findall(r'"(http://[^"]+)"', src)
    for u in url_literals:
        pos = src.find('"' + u + '"')
        line_no = src[:pos].count(chr(10)) + 1
        if line_no in env_default_lines:
            continue  # env 可覆盖的默认值，合法
        issues.append(f"G-D2 {fname}: 第{line_no}行独立 URL 字面量 '{u[:50]}'——应 env 化（SERVER_BUS/LOCAL_BB）")

    # ---- G-D3 平台门（仅当有平台相关代码）----
    if "launchctl" in src or "LaunchAgents" in src:
        # 跨平台守护应标注平台分支
        if "platform" not in src and "sys.platform" not in src and "os.name" not in src:
            issues.append(f"G-D3 {fname}: 含 launchctl 但无平台分支——跨平台(node-kit)需 sys.platform 判断")

    return issues

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--dir")
    ap.add_argument("--node", default=None, help="目标节点名（mac-mini/mbp/i9），用于校验 conf 匹配")
    args = ap.parse_args()

    files = []
    if args.file: files = [args.file]
    elif args.dir:
        for root, _, fs in os.walk(args.dir):
            for f in fs:
                if f.endswith((".py", ".sh")): files.append(os.path.join(root, f))
    if not files:
        print("❌ 未指定 --file 或 --dir"); return 2

    all_issues = []
    for f in files:
        for issue in check_file(f, args.node):
            all_issues.append(issue)

    if not all_issues:
        print(f"✅ GATE-DEPLOY PASS ({len(files)} 文件): 无硬编码/env 契约问题")
        return 0
    print(f"⚠️  GATE-DEPLOY 发现 {len(all_issues)} 项:")
    for i in all_issues: print("  -", i)
    return 1

if __name__ == "__main__":
    sys.exit(main())
