#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""响应缺口报告：把「资源级禁动约束」从规则的附属段**提升为独立可检索落点**。

对端的批评（成立）：约束寄生在 R038 的实证段里 ⇒ 将来会话查「某目录能不能删」，
必须先读到 R038 才知道，而非直接命中。⇒ 建独立约束表（可 grep 命中），双板登记。
另按其对③的要求，修正 R038 实证措辞（影响面收敛）。
"""
import json, io, os, shutil, datetime, urllib.request

TODAY = "2026-10-03"
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

# ---------- 1. 独立约束表 ----------
CP = os.path.expanduser("~/dsh-collab/data/ops/resource-constraints.json")
os.makedirs(os.path.dirname(CP), exist_ok=True)
if os.path.exists(CP):
    shutil.copy2(CP, CP + ".bak-" + STAMP)
    tbl = json.load(io.open(CP, encoding="utf-8"))
else:
    tbl = {"schema": "resource-constraints/v1",
           "说明": "资源级禁动/受限约束登记表。**独立于规则账本**，"
                 "以便按对象直接检索命中（对端 session-ab866871 提出的缺口）。"
                 "查「某路径能否删/清/迁移」应先读本表，再读 rules-registry。",
           "constraints": []}

con = {
    "id": "RC-001",
    "对象路径": [
        "~/Library/Containers/com.tencent.xinWeChat",
        "~/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/old_backup",
        "~/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/concychris_fcd2",
        "~/Library/Containers/com.tencent.WeWorkMac",
    ],
    "别名/关键词": ["微信", "WeChat", "xwechat", "old_backup", "企业微信", "WeWork",
                "chat_history_backup", "聊天记录备份"],
    "占用画像_只读": {"微信": "386G（其中 old_backup 308G · concychris_fcd2 75G · app_data 2.8G）",
                 "企业微信": "73G"},
    "约束效力": ["禁止删除", "禁止清理", "禁止作为清理建议上报", "只可只读统计"],
    "依据": "用户 2026-10-02 直接指示：「不允许动微信 backup」",
    "覆盖声明": "**本约束覆盖一切建议与收益估算**；任何体积/占比数据仅作画像，隐含不可执行",
    "对职责方要求": [
        "承担磁盘清理/资源管理职责的会话（如 session-164dceca）须将本约束作为**前置排除条件**",
        "发现该路径占用时**只可只读统计并标注「只读统计·不作为清理建议」**",
        "不得以「可释放 N」形式提及（见 R038）",
    ],
    "登记来源": "对端会话 session-ab866871 双板登记（其卡 version 板①=4/板②=3，"
              "含「用户决策·已定案」段）；本会话按其对落点的要求固化。",
    "生效日期": "2026-10-02",
}
tbl["constraints"] = [c for c in tbl["constraints"] if c.get("id") != "RC-001"] + [con]
tbl["updated"] = TODAY
io.open(CP, "w", encoding="utf-8").write(json.dumps(tbl, ensure_ascii=False, indent=2) + "\n")
print("独立约束表已建: %s（%d 条）" % (CP, len(tbl["constraints"])))

# ---------- 2. 修正 R038 实证措辞（影响面收敛） ----------
R = os.path.expanduser("~/dsh-collab/rules-registry")
JP = os.path.join(R, "rules.json"); MP = os.path.join(R, "RULES.md")
shutil.copy2(JP, JP + ".bak-R038-scope-" + STAMP)
shutil.copy2(MP, MP + ".bak-R038-scope-" + STAMP)
d = json.load(io.open(JP, encoding="utf-8"))
r038 = next(r for r in d["rules"] if r["id"] == "R038")
converge = ("\n\n【影响面收敛更正（对端 session-ab866871 提供，2026-10-03）】"
            "本条的「两处独立同错」**不得**被读作「已扩散到下游执行方」——"
            "实际净扩散面 = **2 处（均为会话间/会话对用户），且均已更正**："
            "① 对端那次外传**只发给了本会话**；"
            "② 对端给磁盘清理职责会话 `session-164dceca` 发的是**禁令版本**、"
            "**不含「可释放」表述** ⇒ **该执行方从未收到诱导性数字**。"
            "⇒ 风险评估定级应据此收敛，勿高估。")
if "影响面收敛更正" not in r038.get("detail", ""):
    r038["detail"] = r038.get("detail", "") + converge
r038["relatedConstraints"] = ["RC-001（独立约束表：data/ops/resource-constraints.json）"]
d["lastUpdated"] = TODAY
io.open(JP, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")

md = io.open(MP, encoding="utf-8").read()
# ★ 2026-10-03 复查修正：幂等守卫的匹配串原本写死为「影响面收敛更正」，
#   而实际插入的正文是「### R038 附注：影响面收敛（对端 …」—— **没有『更正』二字**
#   ⇒ `not in md` **恒真** ⇒ 每次重跑都会**再插一段**（实测：沙箱重放一次，出现次数 1→2）。
#   现改为：守卫串与实际插入串**同源**（都由下面的 MARK 常量派生），杜绝再次漂移。
MARK = "影响面收敛（对端"          # ← 与实际插入正文一致；守卫与插入共用此常量
if MARK not in md:
    anchor = "### R038 附：当前禁动清单"
    ins = ("### R038 附注：" + MARK + " session-ab866871 提供 · 2026-10-03）\n"
           "- 本条的「两处独立同错」**不得**读作「已扩散到下游执行方」⇒ 净扩散面 = **2 处（会话间/对用户），均已更正**；"
           "对端给磁盘清理职责会话 `session-164dceca` 发的是**禁令版本、不含「可释放」表述** ⇒ **执行方从未收到诱导性数字**，风险定级据此收敛\n"
           "- **约束的独立落点见** `data/ops/resource-constraints.json`（RC-001）—— 按对象直接检索，不必先读本规则\n\n")
    assert anchor in md, "锚点缺失，拒绝写入（避免把附注插到错误位置）"
    md = md.replace(anchor, ins + anchor, 1)
    io.open(MP, "w", encoding="utf-8").write(md)
    print("RULES.md 已加影响面收敛附注")
else:
    print("RULES.md 已含该附注（幂等：不重复插入）")
print("R038 已关联 RC-001")
print("校验: constraints=%d, R038.relatedConstraints=%s"
      % (len(tbl["constraints"]), r038["relatedConstraints"]))
