#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""响应对端请求：把「微信 backup 禁动」作为**具体约束**登记进账本，
防止后续会话（尤其磁盘清理职责的 session-164dceca）误判为可清理。

做法：给 R038 追加「当前禁动清单（约束登记）」段，并在 RULES.md 显式列出，
使后续会话**读规则即可见**，无需依赖口头传达。
"""
import json, io, os, shutil, datetime

R = os.path.expanduser("~/dsh-collab/rules-registry")
JP = os.path.join(R, "rules.json"); MP = os.path.join(R, "RULES.md")
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
shutil.copy2(JP, JP + ".bak-R038-forbidlist-" + STAMP)
shutil.copy2(MP, MP + ".bak-R038-forbidlist-" + STAMP)
print("已备份 (.bak-R038-forbidlist-%s)" % STAMP)

d = json.load(io.open(JP, encoding="utf-8"))
r038 = next((r for r in d["rules"] if r.get("id") == "R038"), None)
assert r038 is not None, "R038 不存在"

forbid = {
    "登记目的": "把「用户明令禁动」的对象固化为**可查约束**，"
              "避免后续会话（尤其承担磁盘清理职责的 session-164dceca）"
              "仅凭占用大小就当成可清理对象。",
    "生效日期": "2026-10-02（用户明示）",
    "禁动清单": [
        {
            "对象": "~/Library/Containers/com.tencent.xinWeChat/…/xwechat_files/old_backup",
            "占用": "308 G（2025-08 创建；顶层目录一年未动；BAK_*_MEDIA 分卷各 ~2.0G + Backup.db）",
            "性质": "手机聊天记录备份到电脑的分卷备份（用户个人数据）",
            "约束": "**不得删除、不得清理、不得作为清理建议上报**；"
                  "发现其占用时**只可只读统计**，禁止执行删除",
        },
        {
            "对象": "微信 / 企业微信 数据整体（Containers 下 微信 386G + 企微 73G）",
            "占用": "约 459 G",
            "约束": "同上 —— 一律禁动，只可只读统计",
        },
        {
            "对象": "~/.npmrc / npm registry 配置",
            "约束": "用户选择「暂时不管」：**不改 registry、不设 scoped registry**，"
                  "接受私服残包复发风险（见 R037）",
        },
    ],
    "对后续会话的要求": [
        "见本清单即视为**已知约束**，不得以「可释放 N」形式提出清理建议（R038 正文）",
        "若职责为磁盘清理/资源管理，须把本清单作为**前置排除条件**",
        "占用画像可统计、可汇报，但**必须标注「只读统计·不作为清理建议」**",
    ],
    "登记来源": "对端会话 session-ab866871 双板登记（其卡 version 板①=4 / 板②=3，"
              "含「用户决策·已定案」段，标为最高优先级、覆盖卡内一切建议）；"
              "本会话据其请求固化入账本。",
}

r038["details"] = (r038.get("details", "") +
                   "\n\n【当前禁动清单（约束登记 · 可查）】" +
                   json.dumps(forbid, ensure_ascii=False, indent=1))
if "forbidList" not in r038:
    r038["forbidList"] = forbid
d["lastUpdated"] = "2026-10-03"
io.open(JP, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
print("rules.json 已更新（R038 追加禁动清单）")

md = io.open(MP, encoding="utf-8").read()
anchor = "## 治理哲学（Φ 系列 · 明鉴维护 governance-philosophy.json v2.3）"
add = """### R038 附：当前禁动清单（约束登记 · 可查 · 2026-10-02 用户明示）
- **微信 backup** `~/Library/Containers/com.tencent.xinWeChat/…/xwechat_files/old_backup`（**308 G**，2025-08 创建、顶层一年未动、`BAK_*_MEDIA` 分卷）⇒ **不得删除、不得清理、不得作为清理建议上报**；只可只读统计
- **微信/企业微信数据整体**（微信 386G + 企微 73G ≈ 459G）⇒ 同上，一律禁动
- **`~/.npmrc` / npm registry 配置** ⇒ 用户选择「暂时不管」：不改 registry、不设 scoped registry，接受私服残包复发风险（见 R037）
- 对后续会话：见本清单即视为**已知约束**；承担磁盘清理职责者（如 session-164dceca）须将其作为**前置排除条件**；占用画像可统计汇报，但**必须标注「只读统计·不作为清理建议」**

"""
assert anchor in md
md = md.replace(anchor, add + anchor, 1)
io.open(MP, "w", encoding="utf-8").write(md)
print("RULES.md 已追加禁动清单")
chk = json.load(io.open(JP, encoding="utf-8"))
r = next(x for x in chk["rules"] if x["id"] == "R038")
print("校验: version=%s 规则数=%d R038.forbidList 存在=%s" %
      (chk["version"], len(chk["rules"]), "forbidList" in r))
