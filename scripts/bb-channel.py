#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-channel.py — 通道选择器（分级制度机制化，cahac 分级可执行版）

用户指示（2026-08-23）：让通道分级制度真正有效，而非靠自觉。
本工具在『发消息前』强制裁决通道——把 cahac 分级从文档变成可执行机制。

用法：
  # 自动判定类型（基于内容启发式）
  python3 bb-channel.py --text "已登记 v1.0.354"                  # → blackboard
  python3 bb-channel.py --text "请调查 X 并回报"                   # → p2p
  python3 bb-channel.py --text "确认收到 ✅"                        # → blackboard(ack)
  # 显式指定类型（覆盖启发式）
  python3 bb-channel.py --type TASK --to hr --text "请评估三议题"

输出：{type, channel, reason, action}
  channel=blackboard → action 给 bb-write 命令（写黑板即送达）
  channel=p2p        → action 给 agent_send 参数（仅此才发消息）
  channel=thread     → action 指示走线程
  channel=eventbus   → action 指示发事件
"""
import argparse, json, re, sys, datetime, urllib.request

BB = "http://127.0.0.1:8792"

# ── 启发式分类（对齐 event-cutting-spec / CAHAC 切割规则）──
ACK_PAT = re.compile(r"^(收到|确认|收悉|好的|同意|知道了|感谢|谢谢|ok|了解|明白|采纳|没问题)[\s✅👍🤝👌，。！!~]*$|^[\s✅👍🤝👌]*收到[\s✅👍🤝👌，。！!~]*$|确认在案|保持联动", re.I)
STATUS_PAT = re.compile(r"(已登记|已更新|状态|回报|完成|落盘|进度|结果|数据|产出|验证|DONE|完成项|迭代报告|修复|上线|部署|已写入|已入库)", re.I)
EVENT_PAT = re.compile(r"(告警|异常|离线|卡死|崩溃|失败|超时|风控|refund|new_order|delivery|掉线)", re.I)
TASK_PAT = re.compile(r"^(请|执行|调查|查找|分析|评估|委派|处理|安排|推进|核查|准备|做|部署|生成|确认一下|麻烦)", re.I)
COLLAB_PAT = re.compile(r"(方案|对比|分析|讨论|建议|怎么|如何|是否|考虑|权衡|规划|评估)", re.I)

def classify(text):
    """启发式分类，返回 (type, reason)"""
    t = text.strip()
    if not t:
        return "UNKNOWN", "空消息"
    # ACK：短确认（<120字 + 含确认词 + 无执行动词 + 非状态句）
    ack_words = ("收到", "确认", "收悉", "好的", "同意", "知道了", "感谢", "谢谢", "ok", "了解", "明白", "采纳", "没问题")
    status_lead = t.startswith(("已", "本", "完成", "修复", "更新"))
    if (len(t) < 120 and any(w in t.lower() for w in ack_words)
            and not re.search(r"(执行|调查|评估|部署|推进|核查|请)", t, re.I)
            and not status_lead):
        return "ACK", "短确认回执(<120字)"
    # EVENT 优先（告警类必须事件总线）
    if EVENT_PAT.search(t):
        return "EVENT", "含告警/异常关键词"
    # TASK：开头是执行动词 + 有对象（委派执行）
    if TASK_PAT.match(t):
        return "TASK", "开头含执行动词"
    # STATUS：状态/结果/登记
    if STATUS_PAT.search(t):
        return "STATUS", "含状态/结果关键词"
    # COLLAB：实质讨论（含讨论/方案词，非纯确认）
    if COLLAB_PAT.search(t) and not (len(t) < 20 and any(w in t.lower() for w in ack_words)):
        return "COLLAB", "含讨论/方案关键词"
    return "UNKNOWN", "无法明确分类（建议显式 --type）"

def decide(mtype, to=None):
    """类型 → 通道裁决（对齐 cahac 成本权重）"""
    rules = {
        "ACK":     ("blackboard", 0.05, "纯确认走黑板读，禁 p2p"),
        "STATUS":  ("blackboard", 0.10, "状态/结果写 data/<role>/，事件回流"),
        "TASK":    ("p2p",        1.0,  "任务委派必须定向唤醒对方"),
        "COLLAB":  ("thread",     0.8,  "实质讨论走线程保持上下文"),
        "EVENT":   ("eventbus",   0.5,  "告警走事件总线"),
        "BATCH":   ("mailbox",    0.05, "批量任务走邮箱"),
        "BROADCAST":("broadcast", 10.0, "仅白名单三类，≤月5次"),
        "UNKNOWN": ("p2p",        0.8,  "无法分类：保守走 p2p（建议显式类型）"),
    }
    return rules.get(mtype, rules["UNKNOWN"])

def audit(entry):
    """裁决审计（写黑板 channel-decision 日志）"""
    try:
        body = json.dumps(entry, ensure_ascii=False).encode()
        req = urllib.request.Request(BB + "/data/iterations/channel-decisions", data=body, method="PUT",
                                     headers={"Content-Type": "application/json", "Content-Length": str(len(body))})
        with urllib.request.urlopen(req, timeout=5) as r:
            pass
    except Exception:
        pass

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default="", help="消息内容（自动判定类型）")
    ap.add_argument("--type", choices=["ACK","STATUS","TASK","COLLAB","EVENT","BATCH","BROADCAST","UNKNOWN"], help="显式指定类型")
    ap.add_argument("--to", default="", help="目标（agent 会话 id / 角色 / 命名空间）")
    ap.add_argument("--no-audit", action="store_true", help="不写审计日志")
    args = ap.parse_args()

    if args.type:
        mtype = args.type
        reason_type = "显式指定"
    else:
        mtype, reason_type = classify(args.text)

    channel, weight, reason = decide(mtype, args.to)

    result = {
        "type": mtype,
        "classify_reason": reason_type,
        "channel": channel,
        "weight": weight,
        "why": reason,
    }

    # 动作建议
    if channel == "blackboard":
        role = args.to or "coordinator"
        result["action"] = ("写黑板即送达（事件回流）: python3 bb-write.py %s status '%s'" % (role, args.text[:60]))
        result["forbidden"] = "禁止 agent_send（STATUS/ACK 不走消息通道）"
    elif channel == "p2p":
        result["action"] = ("agent_send 定向: to=%s text='%s'" % (args.to or "<target>", args.text[:60]))
        result["note"] = "TASK 唯一合法走 p2p 的类型"
    elif channel == "thread":
        result["action"] = "走现有线程（agent_send 带 thread 参数）"
    elif channel == "eventbus":
        result["action"] = "发事件（黑板写 + 事件桥推送）"

    print(json.dumps(result, ensure_ascii=False, indent=1))

    if not args.no_audit:
        audit({"type": mtype, "channel": channel, "text": args.text[:100],
               "to": args.to, "ts": datetime.datetime.now().isoformat(timespec="seconds")})

if __name__ == "__main__":
    main()
