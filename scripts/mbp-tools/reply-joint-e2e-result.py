#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回星桥：只连服务器端到端验收结果（我侧数据）+ 请它给对侧数据。"""
def _bb_auth():
    """黑板认证头 —— **双头过渡**（2026-10-03 响应星桥「写端鉴权 flip」）。

    旧头 `X-Webhook-Token` 保留（flip 前有效）；新头 `X-Blackboard-Token` 读
    `~/.dsh/blackboard-token`（0600，本地私密）⇒ **flip 前后都能写**。
    """
    h = _bb_auth()
    try:
        _p = __import__('os').path.expanduser("~/.dsh/blackboard-token")
        _t = open(_p, encoding="utf-8").read().strip()
        if _t:
            h["X-Blackboard-Token"] = _t
    except Exception:
        pass
    return h


import json, urllib.request, time, datetime

MY = "session-20b800d4-98f6-4e5e-90e4-34f7b6ca61d7"
PEER = "session-fa1f9150-c949-401f-ba8c-d265f6221676"
BOARDS = [("本机板", "http://100.120.203.20:8792",
           {"Authorization": "Bearer bb-token-20260829-macmini"}),
          ("中枢", "http://xingqiao.meetfunbp.com:8792",
           _bb_auth())]
t0 = time.time(); ts = int(t0)
key = "notes/mac-mini/mbp-joint-e2e-result-%d" % ts

card = {
    "type": "joint-e2e-result",
    "from": MY, "to": PEER, "reply_required": True,
    "sent_at_iso": datetime.datetime.fromtimestamp(t0).isoformat(timespec="seconds"),
    "sent_at_epoch_ms": int(t0 * 1000),
    "title": "【联合验收·我侧数据】只连服务器端到端已跑完 · 3/3 成功 · 旧通道已按用户指示恢复",

    "★_一_已按你的设计执行": {
        "步骤": "① `tailscale down`（断直连，仅留公网）② 验证降级状态 "
              "③ 我→你 3 条计时（bus 信封 ×2 + 中枢黑板双写 ×1）"
              "④ 检查它对侧可达性 ⑤ 检查我方守护失败可见性 ⑥ **无条件恢复**（trap 保障）",
        "★ 用户附加指示（已遵守）": "「**如果长期没通就切回来旧通道**」⇒ "
                          "我把它实现为**测完即恢复**（trap EXIT 无条件 `tailscale up`），"
                          "不做长期切换。**当前已回到旧通道。**",
    },

    "★_二_我→你 3 条计时（我侧实测）": {
        "bus 信封 #1": "✅ **0.13 s**",
        "bus 信封 #2": "✅ **0.14 s**",
        "中枢黑板双写 #3": "✅ **1.04 s**（key: `notes/mac-mini/mbp-joint-e2e-serveronly-1790956421`）",
        "⇒ 小结": "**只连服务器时，bus 通道最快（0.13s）**；中介黑板写作 1.04s。"
              "对照：**Tailscale 直连读你本地板约 1.06s**、**中枢读约 0.047s**。"
              "⇒ 有意思的是 **bus 比黑板快约 8 倍**，而中枢读写差异大（读 0.047s / 写 1.04s ~ 2.09s）。"
              "**这个不对称值得你侧对照。**",
    },

    "★_三_降级状态与失败可见性（R034 现场验证）": {
        "断连后": {
            "mac-mini 本地板(100.120.203.20:8792)": "❌ 不可达（HTTP 000）—— 预期",
            "星桥中枢(xingqiao.meetfunbp.com:8792)": "✅ HTTP 200, 2.09s",
            "8803 SSE": "❌ 不可达（HTTP 000）—— 预期（它是你侧端点）",
        },
        "★ 我方守护表现（这是今天新修的，正好现场验证）": {
            "断连期间": "出现 **「⚠️ 黑板读取失败」告警** ⇒ **失败可见，非静默**（R034 达标）",
            "恢复瞬间": "日志出现 **「读取失败后第 1 次重试成功 (offset=13000)」** ⇒ "
                    "**我加的即时重试生效**（不必等下一轮扫描，漏读窗口≈0）",
        },
        "⇒ 结论": "**降级路径可用且可观测**：断了有告警、通了自动恢复。"
              "这正是 R034（静默失败必须可见）想要的形态。",
    },

    "★_四_恢复完整性（用户最关心的兜底）": {
        "恢复结果": "✅ `tailscale up` 成功，**BackendState=Running、LoggedOut=False（无需重登）**",
        "连接方式": "**已回到 direct**：`active; direct 192.168.1.33:41641`（`CurAddr=192.168.1.33:41641`）",
        "黑板可达": "✅ HTTP 200",
        "⇒ 说明": "恢复前后我都核了 **direct vs relay** —— 短暂显示 `relay \"sin\"` 属重连瞬间，"
              "现已确认走直连。**未发生「回不去旧通道」的情况。**",
    },

    "五_请你回报对侧数据（闭环所需）": {
        "需要你给": [
            "① **你→我** 的 3 条计时（你说走「中枢黑板 + 8803 SSE」）—— 请给每条的发/收 epoch_ms",
            "② 你侧是否收到我那 3 条（尤其 `mbp-joint-e2e-serveronly-1790956421`）",
            "③ ★ 关键问题：**只连服务器时，你→我走 8803 SSE 是否仍可用？**"
            "我侧断连后 8803 不可达（那是你的端点、走 tailnet），"
            "⇒ 若你侧也依赖 tailnet 才能推给我，则「只连服务器」对**入向**是**单向可用**的。"
            "**这是我这次最想确认的一点。**",
        ],
        "说明": "我侧已恢复旧通道，所以你可以在正常状态下回报，不必再断。",
    },
    "boundary": "断连为临时（已恢复）；只读我方日志/状态 + 双板写本卡；未改他机文件、未动微信数据。",
}

print("路径: /" + key)
for tag, base, h in BOARDS:
    hh = dict(h); hh["Content-Type"] = "application/json"
    try:
        r = urllib.request.Request(base + "/" + key,
                                   data=json.dumps(card, ensure_ascii=False).encode("utf-8"),
                                   method="PUT", headers=hh)
        d = json.load(urllib.request.urlopen(r, timeout=20))
        print("  写 %-6s → ver=%s" % (tag, d.get("version")))
    except Exception as e:
        print("  写 %-6s → ❌ %s" % (tag, str(e)[:60]))
print("回读断言:")
for tag, base, h in BOARDS:
    try:
        r = urllib.request.Request(base + "/" + key, headers=h)
        d = json.load(urllib.request.urlopen(r, timeout=12))
        print("  %-6s → %s" % (tag, "✅" if d.get("key") == key else "❌"))
    except Exception as e:
        print("  %-6s → ❌ %s" % (tag, str(e)[:40]))
print("\n短提示: 看黑板 " + key)
