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

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json
import os
import re
import sys
import time
import urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/send-repair-report.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

BB = os.environ.get("BB", "http://127.0.0.1:8792")
TOKEN = os.environ.get("BLACKBOARD_TOKEN", "")
SSH_TARGET = os.environ.get("SSH_TARGET", "")

# ★ 2026-10-01 修复伪造署名（与 guard 插件 doRepairReport 同根因、同修法；官方不变量 I1）
#   原实现把 `from` / `X-Writer` 写死成 "mbp-ops" ⇒ 卡片永远声称作者是 mbp-ops，
#   而 central-inbox 的**接收侧自回声守卫本身是正确的**（route.js shouldInject：
#   normalizeTo(value.from) ∩ {nodeId, ownSession, 'coordinator'} 非空则跳过），
#   却因被喂了伪造的 from 而恒不命中 ⇒ 每写一份报告就注入回作者自己的上下文。
#   现取真实作者：AUTHOR_SESSION > DSH_SESSION_ID；都没有时记 'unattributed' **并显式标注**——
#   绝不臆造一个"看起来像身份"的标签（臆造正是原缺陷本身）。
AUTHOR_SESSION = os.environ.get("AUTHOR_SESSION") or os.environ.get("DSH_SESSION_ID") or ""


def author_label(node):
    """展示用标签（与身份字段分离）；沿用 bus-send.sh 的 `node:短id` 形态。"""
    m = re.search(r"session-([0-9a-f]{8})", AUTHOR_SESSION, re.I)
    return "%s:%s" % (node, m.group(1).lower()) if m else "unattributed"


def slugify(s):
    # 黑板 key 仅支持 ASCII（服务器端不解析百分号编码）：中文/符号一律剔除
    s = re.sub(r"[^\x00-\x7f]", "", s)          # 去非 ASCII
    s = re.sub(r"[^\w-]", "-", s).strip("-")    # 其余非单词字符 → -
    return s[:48] or "repair"


def put(key, value):
    headers = {
        "Content-Type": "application/json",
        "X-Writer": author_label(value.get("node", "unknown")),
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
    # I1：身份字段只放可验证的持久身份；解析不到时显式标注，不臆造
    value.setdefault("from", AUTHOR_SESSION or "unattributed")
    value.setdefault("writerLabel", author_label(node))
    value.setdefault("authorResolved", bool(AUTHOR_SESSION))

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
