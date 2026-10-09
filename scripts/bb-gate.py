#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-gate.py — 机制前置门禁（全局规则，所有动作推进前先过）

用户指示（2026-08-23）：机制前置过程工具化/插件化/自动化/落链为底层规则——
任何工作未完成机制前置评估，先跑评估再推进。

用法：
  python3 bb-gate.py --action send --to hr --text "请评估X"       # 发消息前
  python3 bb-gate.py --action upgrade --from v0.6 --to v0.7 --script xxx  # 升级前
  python3 bb-gate.py --action absorb --node i9 --tool xxx         # 吸收前
  python3 bb-gate.py --action write --role qa --key status        # 写黑板前
  python3 bb-gate.py --action new-tool --name xxx                 # 新建工具前
  python3 bb-gate.py --list                                        # 列出全部前置规则

输出：{action, gate, status: passed|required, requirements: [...], next: "先跑..."}
  status=passed   → 已满足前置，可推进
  status=required → 未满足，先跑 next 命令再回来
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, sys, datetime, os, subprocess, urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-gate.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

BB = "http://127.0.0.1:8792"
SCRIPTS = os.path.expanduser("~/dsh-collab/scripts")

# ── 机制前置注册表（动作 → 前置评估）──
GATES = {
    "send": {
        "desc": "发消息/通信",
        "tool": "bb-channel.py",
        "run": ["python3 %s/bb-channel.py" % SCRIPTS],
        "requirement": "通道分级裁决：STATUS/ACK→blackboard(用bb-write)，仅TASK才agent_send",
        "pass_if": "channel==p2p 且 type==TASK（或已按裁决转黑板）",
    },
    "write": {
        "desc": "写黑板/STATUS",
        "tool": "bb-write.py",
        "run": ["python3 %s/bb-write.py" % SCRIPTS],
        "requirement": "用 bb-write 短名写 data/<role>/（自动带命名空间+seq）",
        "pass_if": "写入走 bb-write.py（非裸 curl 无签名）",
    },
    "upgrade": {
        "desc": "底座升级",
        "tool": "bb-upgrade.py",
        "run": ["python3 %s/bb-upgrade.py --dry-run ..." % SCRIPTS],
        "requirement": "跑升级流水线（7步：语法→测试→冒烟→切换→验证→复用评估→落链）",
        "pass_if": "dry-run 冒烟全过且复用评估完成",
    },
    "absorb": {
        "desc": "吸收节点经验",
        "tool": "bb-absorb.py",
        "run": ["python3 %s/bb-absorb.py ..." % SCRIPTS],
        "requirement": "复用评估(reusable/needs-adaptation/hub-only) + 环境自适配检查",
        "pass_if": "bb-absorb 已跑且 grade 记录在黑板 iterations/absorb-*",
    },
    "new-tool": {
        "desc": "新建工具/资产",
        "tool": "bb-reuse-check.py + 属主登记",
        "run": ["python3 %s/bb-reuse-check.py ..." % SCRIPTS],
        "requirement": "复用评估 + 属主登记（HR registry scripts 台账）",
        "pass_if": "复用分级已定 + 属主已登记",
    },
    "node-join": {
        "desc": "接入新节点",
        "tool": "黑板 /nodes + v0.6",
        "run": ["PUT /nodes/<id> (type/identity)"],
        "requirement": "节点身份注册(store_id/code/location) + 收件定向(recipient)",
        "pass_if": "nodes/ 已注册且 tasks 用 recipient 定向",
    },
}

def check_send(args):
    """发消息前置：跑 bb-channel 裁决（支持显式 --type 覆盖自动分类）"""
    cmd = "python3 %s/bb-channel.py --text \"%s\"" % (SCRIPTS, (args.text or "")[:80])
    if args.type:
        cmd += " --type %s" % args.type
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        out = r.stdout or ""
        import re
        ch = re.search(r'"channel": "(\w+)"', out)
        ty = re.search(r'"type": "(\w+)"', out)
        channel = ch.group(1) if ch else "?"
        mtype = ty.group(1) if ty else "?"
        if mtype in ("STATUS", "ACK") or channel == "blackboard":
            return "required", ["STATUS/ACK 走黑板，禁止 agent_send",
                                 "改用: python3 bb-write.py <role> status '<text>'"]
        if channel == "p2p" and mtype == "TASK":
            return "passed", ["TASK→p2p 合法，可 agent_send"]
        return "required", ["通道裁决: %s/%s，按 bb-channel 建议执行" % (mtype, channel)]
    except Exception as e:
        return "required", ["bb-channel 运行失败: %s" % str(e)[:60]]

def check_write(args):
    return "passed", ["bb-write.py 短名写入（命名空间+seq 自动）"]

def check_upgrade(args):
    return "passed" if args.dry_run_done else "required", [
        "先跑: python3 %s/bb-upgrade.py --from %s --to %s --dry-run" % (SCRIPTS, args.vfrom, args.vto)]

def check_absorb(args):
    # 检查黑板是否已有吸收记录
    try:
        with urllib.request.urlopen(BB + "/data/iterations/absorb-%s-%s" % (args.node, args.tool.replace(".","-")), timeout=5) as r:
            return "passed", ["absorb 记录已存在（黑板 iterations/absorb-*）"]
    except Exception:
        return "required", ["先跑: python3 %s/bb-absorb.py --node %s --tool %s" % (SCRIPTS, args.node, args.tool)]

def check_new_tool(args):
    return "required", ["先跑复用评估: python3 %s/bb-reuse-check.py --capability \"%s\"" % (SCRIPTS, args.name),
                        "再登记属主（HR registry scripts 台账）"]

def check_node_join(args):
    return "required", ["注册: PUT /nodes/<id> {type:store,...}",
                        "任务卡用 recipient 定向"]

CHECKERS = {
    "send": check_send, "write": check_write, "upgrade": check_upgrade,
    "absorb": check_absorb, "new-tool": check_new_tool, "node-join": check_node_join,
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--action", choices=list(GATES.keys()))
    ap.add_argument("--list", action="store_true")
    # send
    ap.add_argument("--text", default="")
    ap.add_argument("--to", default="")
    ap.add_argument("--type", choices=["ACK","STATUS","TASK","COLLAB","EVENT","BATCH","BROADCAST","UNKNOWN"], default="",
                    help="显式消息类型（覆盖自动分类，供人类语义兜底）")
    # upgrade
    ap.add_argument("--from", dest="vfrom", default="")
    ap.add_argument("--vto", default="")
    ap.add_argument("--dry-run-done", action="store_true")
    # absorb
    ap.add_argument("--node", default="")
    ap.add_argument("--tool", default="")
    # new-tool
    ap.add_argument("--name", default="")
    # write
    ap.add_argument("--role", default="")
    ap.add_argument("--key", default="")
    args = ap.parse_args()

    if args.list:
        print("== 机制前置规则表 ==")
        for k, g in GATES.items():
            print("  %s: %s → %s" % (k, g["desc"], g["requirement"][:50]))
        sys.exit(0)

    if not args.action:
        print("需 --action（--list 查看全部）"); sys.exit(1)

    gate = GATES[args.action]
    checker = CHECKERS[args.action]
    status, msgs = checker(args)

    result = {
        "action": args.action,
        "gate": gate["desc"],
        "tool": gate["tool"],
        "status": status,
        "messages": msgs,
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    print(json.dumps(result, ensure_ascii=False, indent=1))
    # 审计
    try:
        body = json.dumps({"action": args.action, "status": status,
                           "ts": result["ts"]}).encode()
        req = urllib.request.Request(BB + "/data/iterations/gate-decisions", data=body, method="PUT",
                                     headers={"Content-Type": "application/json", "Content-Length": str(len(body))})
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass
    sys.exit(0 if status == "passed" else 2)

if __name__ == "__main__":
    main()
