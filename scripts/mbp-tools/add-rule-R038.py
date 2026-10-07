#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""入账 R038：未获批处置项不得以「可释放 N」形式外传。
来源：2026-10-02 两个会话各自独立犯同一错（会话 ab866871 与 20b800d4）。"""
import json, io, os, shutil, datetime

R = os.path.expanduser("~/dsh-collab/rules-registry")
JP = os.path.join(R, "rules.json"); MP = os.path.join(R, "RULES.md")
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
shutil.copy2(JP, JP + ".bak-R038-" + STAMP)
shutil.copy2(MP, MP + ".bak-R038-" + STAMP)
print("已备份 (.bak-R038-%s)" % STAMP)

d = json.load(io.open(JP, encoding="utf-8"))
rules = d["rules"]
assert "R038" not in {r.get("id") for r in rules}, "R038 已存在"
TODAY = "2026-10-03"

r038 = {
    "id": "R038",
    "name": "未获批处置项不得以「可释放 N」形式外传（授权边界纪律）",
    "category": "治理",
    "scope": "all-bus-devices",
    "status": "enforced",
    "version": "1.0",
    "source": "2026-10-02 同一天内两个会话**各自独立**犯同一错："
              "会话 session-ab866871 与本会话 session-20b800d4，"
              "分别把「待用户拍板」的 308G 微信备份清理写成"
              "「若确认可释放 308G / 磁盘可降到约 63%」。用户随即明令："
              "**「不允许动微信 backup」**。",
    "summary": "**未获用户/授权人批准的清理、删除、迁移、变更项，不得以"
               "「可释放 N GB」「可降到 X%」「可节省 N」等可量化收益形式对外表达**"
               "（含写黑板卡、发消息、出报告）。"
               "这类表述会被下游读成「**建议动作**」甚至「**默认动作**」，"
               "从而把「未授权」变成「事实授权」。",
    "detail": "事故：某会话统计出 `/System/Volumes/Data` 96%（余 43Gi），"
              "定位大头为微信 `old_backup` **308G**（2025-08 手机聊天记录分卷备份、"
              "顶层一年未动），随即在/向外表述「若用户确认清理，可从 96% 降到约 63%」。"
              "用户随后明确指示**不得动微信 backup**。⇒ 该表述属**口径越界**："
              "把「仅属统计事实」与「处置建议」混为一体，且给出**诱导性收益数字**。"
              "★ 两个会话在同一天**各自独立**犯此错 ⇒ 说明这是**结构性倾向**，非个人疏忽。",
    "enforcedBy": "① 未获批项**只能以「待批事项」形式上报给决策人本人**，"
                  "且**不给可量化收益**（避免诱导批准）；"
                  "② 若必须披露数据，须与处置建议**显式分离**，并标注"
                  "「**只读统计·仅供知情，不作为清理建议**」；"
                  "③ 已获批的**禁止项**必须标为**最高优先级**并声明"
                  "「**覆盖本卡内一切建议**」；"
                  "④ 下游会话见到「禁动」标记时**只可只读统计，禁止执行删除/清理**；"
                  "⑤ 报告他人决策时，**不得把「待拍板」的假设写成可选方案**",
    "added": TODAY,
    "approvedBy": "用户明令（不允许动微信 backup）触发；对端会话提出口径失误自省",
    "approvedAt": TODAY,
    "details": "与 R034(静默失败必须可见) 互为反面：R034 防「做了却没人知道」，"
               "本条防「**没批准却被当已批准**」。"
               "亦与 R032(跨设备受控停机须先获同意) 同族 —— 同属**授权边界**规则："
               "凡涉及他人资源/数据的不可逆动作，**未获明示同意即不得动手，"
               "亦不得以诱导性收益推动其被批准**。",
}

rules.append(r038)
d["rules"] = rules; d["version"] = "2.14.5"; d["lastUpdated"] = TODAY
io.open(JP, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
print("rules.json → version=%s 规则数=%d" % (d["version"], len(rules)))

md = io.open(MP, encoding="utf-8").read()
md = md.replace("> v2.14.4 | 81 条 | 所有总线设备必须服从",
                "> v2.14.5 | 82 条 | 所有总线设备必须服从", 1)
block = """## R038 ✅ 未获批处置项不得以「可释放 N」形式外传（授权边界纪律）
- 分类: 治理 | 范围: all-bus-devices | 状态: enforced
- 摘要: **未获用户/授权人批准的清理、删除、迁移、变更项，不得以「可释放 N GB」「可降到 X%」等可量化收益形式对外表达**。这类表述会被下游读成「建议动作」甚至「默认动作」，把「未授权」变成「事实授权」
- 实证(2026-10-02): 定位到磁盘 96% 的大头为微信 `old_backup` **308G**（2025-08 手机聊天记录分卷备份），**两个会话在同一天各自独立**把它写成「若用户确认清理可释放 308G / 降到约 63%」⇒ 用户随即明令「**不允许动微信 backup**」。★ 两处独立犯同一错 ⇒ 属**结构性倾向**，非个人疏忽
- 强制: ①未获批项**只以「待批事项」上报决策人本人，且不给可量化收益**（避免诱导批准）②必须披露数据时与处置建议**显式分离**，标注「**只读统计·仅供知情，不作为清理建议**」③已获批**禁止项**标为**最高优先级**并声明「**覆盖本卡内一切建议**」④下游见「禁动」标记**只可只读统计，禁止执行**⑤**不得把「待拍板」的假设写成可选方案**
- 关系: R034 的反面（R034 防「做了没人知道」，本条防「**没批准却被当已批准**」）；与 R032 同族，均属**授权边界**

"""
md = md.replace("## 治理哲学（Φ 系列 · 明鉴维护 governance-philosophy.json v2.3）",
                block + "## 治理哲学（Φ 系列 · 明鉴维护 governance-philosophy.json v2.3）", 1)
io.open(MP, "w", encoding="utf-8").write(md)
print("RULES.md 已同步")
chk = json.load(io.open(JP, encoding="utf-8"))
print("校验: version=%s 规则数=%d 末条=%s" % (chk["version"], len(chk["rules"]), chk["rules"][-1]["id"]))
