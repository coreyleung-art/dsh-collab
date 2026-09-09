#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""send-repair-report.py — 修复评估报告自动投递（跨设备运维 SOP）

用途：每次完成 Mac mini（或任意节点）的修复/故障处理后，自动生成一份
      修复评估报告并投递到目标节点黑板 notes/<node>/repair-report-* 通道，
      central-inbox 会监听到该前缀并注入中枢会话（等价「发到那台 Mac」），
      同时在目标节点 ~/dsh-collab/repair-reports/ 归档留底。

用法：
  python3 send-repair-report.py <node> <title> '<json报告体>'
  python3 send-repair-report.py mac-mini "修复 central-inbox 崩溃" '{"root_cause":"...","fix":"...","verify":"..."}'

参数：
  node   目标节点名（黑板 notes/<node>/ 前缀，如 mac-mini）
  title  报告标题（会作为 key 与时间戳组合）
  body   JSON 字符串报告体（必须可 json.loads）

行为：
  1. PUT http://<BB>/notes/<node>/repair-report-<ts>-<slug>（X-Writer 签名）
  2. 归档 JSON 到目标节点 ~/dsh-collab/repair-reports/<ts>-<slug>.json
     （若本机即目标节点则直接写；否则提示通过 SSH 归档）
  3. 输出黑板 key + seq 供确认

环境变量：
  BB               黑板地址（默认 http://127.0.0.1:8792，跨机时传目标节点地址）
  BLACKBOARD_TOKEN 黑板 token（如启用则自动带 X-Blackboard-Token）
  SSH_TARGET       目标节点 ssh 别名/IP（用于归档，如 coreyleung@192.168.1.28）
"""
import json
import os
import re
import sys
import time
import urllib.request

BB = os.environ.get("BB", "http://127.0.0.1:8792")
TOKEN = os.environ.get("BLACKBOARD_TOKEN", "")
SSH_TARGET = os.environ.get("SSH_TARGET", "")


def slugify(s):
    # 黑板 key 仅支持 ASCII（服务器端不解析百分号编码）：中文/符号一律剔除
    s = re.sub(r"[^\x00-\x7f]", "", s)          # 去非 ASCII
    s = re.sub(r"[^\w-]", "-", s).strip("-")    # 其余非单词字符 → -
    return s[:48] or "repair"


def put(key, value):
    headers = {
        "Content-Type": "application/json",
        "X-Writer": "mbp-ops",
    }
    if TOKEN:
        headers["X-Blackboard-Token"] = TOKEN
    body = json.dumps(value, ensure_ascii=False).encode()
    headers["Content-Length"] = str(len(body))
    req = urllib.request.Request(BB + "/" + key, data=body, method="PUT", headers=headers)
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode())


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    node, title, body_raw = sys.argv[1], sys.argv[2], sys.argv[3]
    try:
        value = json.loads(body_raw)
    except json.JSONDecodeError:
        print("❌ body 必须是 JSON 字符串（用单引号包）")
        sys.exit(1)

    ts = time.strftime("%Y%m%d-%H%M%S")
    key = "notes/%s/repair-report-%s-%s" % (node, ts, slugify(title))
    value.setdefault("title", title)
    value.setdefault("node", node)
    value.setdefault("ts", ts)
    value.setdefault("from", "mbp-ops")

    try:
        resp = put(key, value)
        print("✅ 已投递 %s → %s (seq=%s version=%s)" % (node, key, resp.get("seq"), resp.get("version")))
    except Exception as ex:
        print("❌ 黑板投递失败: %s" % str(ex)[:160])
        sys.exit(1)

    # 归档（本机直接写；跨机提示走 SSH）
    fname = "%s-%s.json" % (ts, slugify(title))
    local_archive = os.path.expanduser("~/dsh-collab/repair-reports/" + fname)
    try:
        os.makedirs(os.path.dirname(local_archive), exist_ok=True)
        with open(local_archive, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=1)
        print("📦 已归档: %s" % local_archive)
    except Exception:
        pass
    if SSH_TARGET:
        print("🔗 提示: 目标节点归档可用 ssh %s 'mkdir -p ~/dsh-collab/repair-reports'" % SSH_TARGET)


if __name__ == "__main__":
    main()
