#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修 R037 与禁动清单第3条（npm registry）的**未声明冲突**。

对端 session-ab866871 指出（成立）：
  · R037 处置优先序「scoped registry（结构门，推荐）」与禁动清单第3条
    「不改 registry、不设 scoped registry」直接冲突；
  · **冲突必须写在可能被误执行的那一条上**（即 R037 本体），
    只在禁动清单反向写注记 = 把拦截责任推给读者的阅读顺序；
  · 下游若先读 R037 会按「推荐」执行 ⇒ 违反禁动清单。

修法：在 R037 处置优先序前加**前置声明**（fail-closed 式）：
  若目标配置已被禁动清单登记 ⇒ 本条建议不适用，降级为只读告警 + 上报用户。
"""
import json, io, os, shutil, datetime

R = os.path.expanduser("~/dsh-collab/rules-registry")
JP = os.path.join(R, "rules.json"); MP = os.path.join(R, "RULES.md")
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
shutil.copy2(JP, JP + ".bak-R037-precedence-" + STAMP)
shutil.copy2(MP, MP + ".bak-R037-precedence-" + STAMP)
print("已备份 (.bak-R037-precedence-%s)" % STAMP)

PRECEDENCE = (
    "★★ 前置声明（2026-10-03 补 · 对端 session-ab866871 指出冲突）★★\n"
    "本条的「scoped registry（结构门，推荐）」建议**受禁动清单约束**：\n"
    "**若目标 registry 配置已被「R038 附：当前禁动清单」或独立约束表 "
    "`data/ops/resource-constraints.json` 登记为禁动 ⇒ 本条该建议【不适用】。**\n"
    "此时处置**降级为：只读告警 + 上报用户**，**不得修改任何 registry 配置**。\n"
    "⇒ 即：**约束表 > 本条建议**（fail-closed：宁可不动，不可误改）。\n"
    "★ 冲突写在可能被误执行的那一条上 —— 只在禁动清单反向写注记，"
    "等于把拦截责任推给读者的阅读顺序。"
)

d = json.load(io.open(JP, encoding="utf-8"))
r037 = next(r for r in d["rules"] if r["id"] == "R037")
if "前置声明（2026-10-03 补" not in r037.get("enforcedBy", ""):
    r037["enforcedBy"] = PRECEDENCE + "\n\n" + r037.get("enforcedBy", "")
r037["precedence"] = {
    "约束表优先": "registry 配置若被禁动清单/约束表登记 ⇒ 本条 scoped registry 建议不适用",
    "降级处置": "只读告警 + 上报用户；不得修改 registry 配置",
    "原则": "fail-closed：宁可不动，不可误改",
    "冲突落点": "写在本条（可能被误执行处），而非只在禁动清单反向写注记",
}
d["lastUpdated"] = "2026-10-03"
io.open(JP, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
print("rules.json: R037 已加前置声明 + precedence 字段")

md = io.open(MP, encoding="utf-8").read()
anchor = "## R038 ✅ 未获批处置项不得以「可释放 N」形式外传（授权边界纪律）"
ins = """### ★★ R037 前置声明（2026-10-03 补 · 对端 session-ab866871 指出冲突）★★
**R037 的「scoped registry（结构门，推荐）」建议受禁动清单约束**：
若目标 registry 配置已被「R038 附：当前禁动清单」或独立约束表 `data/ops/resource-constraints.json` 登记为禁动
⇒ **本条该建议不适用**，处置**降级为：只读告警 + 上报用户**，**不得修改任何 registry 配置**。
⇒ **约束表 > 本条建议**（fail-closed：宁可不动，不可误改）。
★ 冲突写在**可能被误执行的那一条上** —— 只在禁动清单反向写注记，等于把拦截责任推给读者的阅读顺序。

"""
assert anchor in md, "锚点未找到"
assert "R037 前置声明" not in md, "已存在，勿重复"
md = md.replace(anchor, ins + anchor, 1)
io.open(MP, "w", encoding="utf-8").write(md)
print("RULES.md: 已插入 R037 前置声明")
chk = json.load(io.open(JP, encoding="utf-8"))
r = next(x for x in chk["rules"] if x["id"] == "R037")
print("校验: precedence=%s" % ("已设" if r.get("precedence") else "缺失"))
