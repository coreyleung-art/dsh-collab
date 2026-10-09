#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
红队编排器 · Red Team Orchestrator v1.0
=====================================
把「手工派 3 个不同视角红队子代理做对抗审查」这件事工具化：

  1) prep   生成多视角红队的【提示词任务包】（每视角一个 .md，直接派发给子代理）
  2) merge  把各视角回报的结果（md / json）合并成一份汇总，按问题去重 + 标注视角冲突
  3) list   列出现有视角模板

设计要点（来自本项目已验证有效的实战纪律）
--------------------------------------------
* 每个视角有独立角色设定与审查重点（对方视角 / 数据算术 / 表达可信度 / 法律合规 / 数据来源）
* 提示词内含 7 条铁律：
    1 必须具体（引用原文原句，不说「这里不清楚」）
    2 必须可执行（给出可直接粘贴替换的句子，不是「建议改写」）
    3 必须区分「必须改」与「明确不要改」（防过度修改）
    4 必须回报 units_reviewed 总数（证明全文读过，不是抽样）
    5 必须站在对方立场挑刺（不替被审方辩护）
    6 不编造（无法核实就写无法核实，全部结论必须有原文出处）
    7 结果写到指定文件 + 最后一段话回报
* 任务包会写入「审查单元基准数」，merge 据此核对 units_reviewed 是否真有通读
* merge 的合并键：位置行号 → 原文片段 → 标题；近似位置/近似原文自动并组
* merge 对同一处出现不同判定档位 → 单列「视角冲突」

用法
----
  # 1) 生成任务包（每视角一个 .md + results/ 目录 + 包清单 json）
  python3 red-team.py prep 材料.md --perspectives platform,math,expression --out /tmp/redteam/

  # 2) 合并各视角回报
  python3 red-team.py merge /tmp/redteam/results/*.md --out FINDINGS.md

  # 3) 列出现有视角
  python3 red-team.py list

零外部依赖 · Python 3.9+ · 中文输出

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== red-team 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 红队编排器 · Red Team Orchestrator v1.0")
    print("  · 把「手工派 3 个不同视角红队子代理做对抗审查」这件事工具化：")
    print("  · 1) prep   生成多视角红队的【提示词任务包】（每视角一个 .md，直接派发给子代理）")
    print("  · 2) merge  把各视角回报的结果（md / json）合并成一份汇总，按问题去重 + 标注视角冲突")
    print("  · 命令/参数: prep, merge, list, version, perspectives, out, embed, max-embed-chars")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, collections, difflib, glob, hashlib, json, os, re, sys, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/red-team.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse
import difflib
import glob as _glob
import hashlib
import json
import os
import re
import sys
import time
from collections import OrderedDict


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/red-team.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = "1.0"

# ============================================================
# 一、视角模板（写在脚本里，可 --perspectives 选）
# ============================================================
PERSPECTIVES = OrderedDict([
    ("platform", {
        "name": "对方视角",
        "focus": "这份材料给不给我信心？我会问什么尖锐问题？",
        "output_req": "8-12 个必问问题 + 每个问题「材料里能否回答」",
        "role": (
            "你现在是**坐在桌子对面的那一方**的审查员。桌对面是供应商 / 合作方 / 出资方 / "
            "客户的立场——你不是这份材料的作者，你是被这份材料说服（或说服不了）的人。"
        ),
        "mission": [
            "我逐字读完这份材料，愿不愿意签字 / 给钱 / 给位置？为什么？",
            "哪些地方让我起疑：让我觉得对方在藏东西、在吹、在自我表扬？",
            "哪些结论**被材料自己的数据 / 排期表 / 附录推翻**？（交叉推翻最致命："
            "正文说「我们已具备 X」，后面的排期表却把 X 排在三个月之后）",
            "哪些是「承诺姿态」而不是可验证的承诺？（读了让人感动，但落不到条款上）",
            "我接下来会拿什么去问它的律师 / 财务 / 技术负责人？",
        ],
        "extra_output": (
            "## 我的必问问题\n\n"
            "（8-12 条，每条写成你**逐字会怎么问**的一句话，例：「你说 2025 年 3 月已经跑通 120 家门店，"
            "请问这 120 家里有几家是直营、几家是挂靠？」；每条后面标注 `能否回答：能 / 部分能 / 不能`，"
            "`不能` 的再补一句「这代表什么风险：…」）"
        ),
        "verdict_hint": (
            "判定档位：会让对方**不签字/不给钱**的问题 → `必须改`；会让我多问一句但不影响决策 → `可选优化`；"
            "我检查过、认为**不要改**的地方（写清为什么它其实是对的）→ `明确不要改`。"
        ),
    }),
    ("math", {
        "name": "数据算术",
        "focus": "每处数字实算 + 口径交叉核对",
        "output_req": "【算错】/【假设不同】/【无法核实】三分类，算错必须给完整计算过程",
        "role": "你现在是**数据算术审查员**。你只认数字：算式、分母、口径、单位、时间跨度。",
        "mission": [
            "把材料里**每一个**数字抄出来单独重算一遍（不要因为「看起来合理」跳过）。",
            "表格必查：行列合计、同比/环比、增长率、占比之和是否为 100%、单位是否混用"
            "（万元 / 元、家 / 店）、年份跨度与总量是否自洽。",
            "比例必查：**分母是什么、分子是什么**——报「34%」而不给分母的一律记一笔。",
            "同一指标在不同章节 / 不同表格是否说法一致（此处最常出「少算 / 多算」）。",
            "口径交叉核对：实测 vs 测算 vs 公开数据是否被混用；抽样数 × 单店值 是否等于总量。",
        ],
        "extra_output": (
            "## 三分类统计\n\n"
            "| 分类 | 条数 | 说明 |\n|---|---|---|\n"
            "| 【算错】 | N | 逐条对应上方 F-xx |\n"
            "| 【假设不同】 | N | |\n"
            "| 【无法核实】 | N | 缺来源/缺口径，无法判定 |\n\n"
            "## 算式明细\n\n"
            "（每条【算错】都写全：算式 → 代入的数字 → 我的结果 → 原文结果 → 差值。"
            "例：`24303 - 22580 = 1723`，即长期档少算 1723 家）"
        ),
        "verdict_hint": (
            "★ 每条发现必须**同时**给出两套标注：\n"
            "  ① 数学分类：`【算错】` / `【假设不同】` / `【无法核实】`（写在「数学分类」字段）\n"
            "  ② 判定档位：`【算错】` → `必须改`；`【假设不同】` → `可选优化`"
            "（若该假设会改变结论，则升为 `必须改`）；`【无法核实】` → `可选优化`。\n"
            "【算错】的「依据」字段必须给**完整计算过程**（不是「算错了」三个字）。"
        ),
    }),
    ("expression", {
        "name": "表达与可信度",
        "focus": "元话语 / 此地无银 / 承诺姿态 / 空话",
        "output_req": "三档判定：必须改 / 可选优化 / 明确不要改",
        "role": "你现在是**表达与可信度审查员**。你判断的不是数字对不对，而是**这些话读起来像不像真的**。",
        "mission": [
            "元话语：文档在谈自己（本计划书/本文/本节/我的写法）、在评价自己（诚实/没藏/不美化）。",
            "此地无银：写了「不写进来」「不并入本文件」「不在这份材料里讨论」——写了「不写」反而暴露它存在。",
            "承诺姿态：读起来像承诺、实际没有责任主体的句子（「我们会全力以赴」「确保万无一失」）。",
            "空话：无主语、无数字、无动词的口号（「赋能」「闭环」「生态化反」）。",
            "**改稿史 / 写作规范 / 版本痕迹外泄**：内部怎么改稿、上一版怎么错、模板从哪来——逐处列出。",
            "**极有价值的句子**：材料里那种「读了让人相信他」的实话（例：敢把「我做不好就退」写进材料），"
            "必须专门列出并标 `明确不要改`，防止下游统一口径时把它改掉。",
        ],
        "extra_output": (
            "## 明确不要改清单（防过度修改）\n\n"
            "（逐条列出你**检查过但认为不能动**的句子，并写清为什么不能动。这一档至少占你全部发现的 20%，"
            "包括：正当的诚实披露、必要的前提说明、对读者有帮助的引导语、以及「看起来像问题其实是对的」的句子）"
        ),
        "verdict_hint": (
            "三档判定：\n"
            "  `必须改` —— 会让读者怀疑真实性 / 暴露内部改稿史 / 此地无银。\n"
            "  `可选优化` —— 能更利落，但不改也不伤。\n"
            "  `明确不要改` —— ★ 这一档必须写。防的是下游「统一文风」把有血有肉的实话一起清掉。"
        ),
    }),
    ("legal", {
        "name": "法律与合规",
        "focus": "授权链 / 责任归属 / 条款风险",
        "output_req": "条款级建议 + 责任方（谁承担什么）",
        "role": "你现在是**法律与合规审查员**。你只关心：出了问题谁负责、授权链是否闭合、这句话签下去意味着什么。",
        "mission": [
            "授权链：材料里用到的资质 / 牌照 / 数据 / 品牌 / 供应链，**谁授权给谁**、链条是否闭合、缺哪一环。",
            "责任归属：每一个承诺 / 对赌 / 回购 / 保底，**责任主体是谁**（公司？创始人个人？某方单独兜底？）。",
            "条款风险：写进合同会产生什么后果；是否有歧义可被对方反向解释。",
            "合规：个人信息、数据来源合法性、平台规则、行业准入。",
            "明确区分三类风险：**法律风险**（会被追责）/ **商业风险**（会亏钱）/ **表述风险**（会被误解）。",
        ],
        "extra_output": (
            "## 条款级建议\n\n"
            "| # | 条款/位置 | 风险类型 | 现状写法的问题 | 建议写法 | 责任方 |\n|---|---|---|---|---|---|\n\n"
            "（责任方栏必须写具体主体：某公司 / 创始人个人 / 各方按比例 / 未明确 ← 「未明确」本身就是最严重的发现）"
        ),
        "verdict_hint": (
            "判定档位：会造成实质责任敞口或授权链断裂 → `必须改`；建议加固但现状不违规 → `可选优化`；"
            "对本受众而言**不构成风险、不必改**的（写清为什么）→ `明确不要改`。"
        ),
    }),
    ("data", {
        "name": "数据来源",
        "focus": "每个数字的来源与性质",
        "output_req": "来源表 + 无法核实项清单",
        "role": "你现在是**数据来源审查员**。数字对不对不是你的活，**这个数字是从哪来的、是什么性质**才是。",
        "mission": [
            "把材料里每一个数字登记一遍，逐项标注来源与性质。",
            "性质分类：`实测` / `测算` / `公开数据` / `客户口述` / `行业报告` / `平台政策口径` / `未知`。",
            "**「谁做的」**：这个成绩是我们做的，还是承接的 / 借用的 / 行业的？（「承接」最容易把别人的数字写在自己名下）",
            "**「什么时候做的」**：截至哪个时点？是历史数据还是目标？",
            "无法核实的单独成清单——它们是这份材料最脆弱的地方，也是对方最先攻击的地方。",
        ],
        "extra_output": (
            "## 来源表\n\n"
            "| # | 数字/指标 | 位置 | 来源（谁给的） | 性质 | 谁做的 | 时点 | 可否核实 |\n|---|---|---|---|---|---|---|---|\n\n"
            "## 无法核实项清单\n\n"
            "（逐条：数字 → 缺什么 → 该向谁要 → 若要不到会发生什么）"
        ),
        "verdict_hint": (
            "判定档位：无来源却当作事实陈述（会被对方一击击穿）→ `必须改`；"
            "有来源但性质标注不清 → `可选优化`；来源充分、标注清楚的 → 不必出现在发现里。"
        ),
    }),
])

DEFAULT_PERSPECTIVES = ["platform", "math", "expression"]

# ============================================================
# 二、7 条铁律（写进每个任务包）
# ============================================================
IRON_RULES = [
    ("必须具体", "不许说「这里不清楚」「表述模糊」。要写：**这句「…（逐字引用原文）」没告诉我…**。"
                 "每条发现必须含逐字原文引用，不许转述。"),
    ("必须可执行", "不许说「建议改写」。要给出**可直接粘贴回原文的替换句**"
                   "（字段「直接替换为」），长度和位置与原句匹配，读者能一键替换。"),
    ("必须区分「必须改」与「不要改」", "只报问题是不够的。你必须同时列出**检查过、但认为明确不要改**的地方，"
                                        "并写清为什么不能改。这是为了防止下游把材料改得没有灵魂。"),
    ("必须回报 units_reviewed", "报告末尾给出你**实际逐字读过**的审查单元总数（非空行 / 段落 / 表格行）。"
                                 "任务包给了基准数，你报的数要能对上——这是你「全文读过，不是抽样」的唯一证明。"
                                 "没读完就如实报小的数，虚报比漏读更糟。"),
    ("必须站在对方立场挑刺", "你是对方的枪，不是被审方的辩护律师。不许替被审方解释动机、不许替它补逻辑漏洞、"
                              "不许写「不过考虑到…也可以理解」。发现「大概能解释过去」的地方，照样写出来让它自己解释。"),
    ("不编造，无法核实就写无法核实", "所有结论必须有原文出处。不确定的性质写 `无法核实`，不许猜、不许用常识补齐。"
                                     "宁可少报一条，不可编一条。"),
    ("输出写到指定文件 + 最后一段话回报", "结果写进任务包指定的结果文件（不要改被审文件本身）；"
                                            "并在你的最后回复里给一段话回报（照抄任务包里的「逐字回报」模板）。"),
]

# ============================================================
# 三、工具函数
# ============================================================
PUNCT_RE = re.compile(r"[\s\u3000·、，,。．\.：:；;！!？?「」『』\"'“”‘’（）()\[\]【】*_`>#\-—…/\\|]+")
NUM_RE = re.compile(r"\d[\d,]*\.?\d*")


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _norm(s):
    """归一化：去标点空白、转小写——用于去重比对"""
    return PUNCT_RE.sub("", s or "").lower()


def _fence_for(text):
    """给内容选一个安全的代码围栏长度"""
    runs = re.findall(r"`+", text or "")
    longest = max([len(r) for r in runs] or [0])
    return "`" * max(3, longest + 1)


def _read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def count_units(text):
    """统计审查单元：非空行（排除表格分隔行）/ 表格数 / 数字个数"""
    lines = text.split("\n")
    units = 0
    tables = 0
    in_table = False
    for ln in lines:
        s = ln.strip()
        if not s:
            in_table = False
            continue
        if re.match(r"^\|[\s:|-]+\|$", s):          # 表格分隔行不计
            continue
        units += 1
        if s.startswith("|"):
            if not in_table:
                tables += 1
                in_table = True
        else:
            in_table = False
    return {
        "chars": len(text),
        "lines_total": len(lines),
        "units": units,
        "tables": tables,
        "numbers": len(NUM_RE.findall(text)),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
    }


# ============================================================
# 四、prep：生成提示词任务包
# ============================================================
RESULT_TEMPLATE = """# 红队报告 · {pname}

- perspective: {key}
- target: {target_name}
- units_reviewed: 0
- score: 0
- summary: 一句话总评（写在上一行的 score 后面这一行）

## 总评

（3-8 句，站在本视角：这份材料给不给我信心？最致命的一条是什么？如果只能改一处，改哪里？）

## 发现

### F-01 [必须改] 一句话标题（≤40 字，直接说事，不要「表述问题」这种空标题）
- 位置：L42-L58（第 3 张表）          ← 行号 + 定位描述，line 0 用「全文」
- 原文：「逐字引用原文，≤120 字，不许转述」
- 问题：这句「…」没告诉我…（写清：缺什么 / 错在哪 / 会让读者怎么想）
- 直接替换为：「可以直接粘贴回原文的句子」
- 依据：数字 / 规则 / 出处（math 视角此处必填完整算式与差值）
- 数学分类：【算错】/【假设不同】/【无法核实】     ← 仅 math 视角需要
- 责任方：某公司 / 创始人个人 / 各方按比例 / 未明确   ← 仅 legal 视角需要

### F-02 [可选优化] 一句话标题
- 位置：…
- 原文：「…」
- 问题：…
- 直接替换为：「…」
- 依据：…

### F-03 [明确不要改] 一句话标题（★ 这一档必须写，写清为什么不能改）
- 位置：…
- 原文：「…」
- 问题：看起来像问题，其实是……（写清为什么它是对的、动了会损失什么）
- 直接替换为：（无 —— 保持原样）
- 依据：…

{extra_output}

## 逐字回报

（把下面这段话原样发回给派你的人，不要改格式：）

红队回报 · {pname}（{key}）· target={target_name}
units_reviewed={units}；必须改 N 条 / 可选优化 N 条 / 明确不要改 N 条
最致命的一条：F-xx …（一句话）
我认为被审方**最该保留**的一句：……
我无法核实的：……（若有）
结果文件：{result_path}
"""


def build_prompt(key, p, target_path, target_text, stats, out_dir, embed=True):
    result_path = os.path.join(out_dir, "results", "%s.md" % key)
    target_name = os.path.basename(target_path)

    L = []
    L.append("# 红队任务包 · %s（%s）" % (p["name"], key))
    L.append("")
    L.append("> 由 `red-team.py v%s` 生成于 %s · 目标文件：`%s`（sha256:%s）"
             % (VERSION, _now(), target_path, stats["sha256"]))
    L.append("> 本文件是**派发给子代理的完整提示词**：整段发给它即可，不要删减其中的铁律与输出格式。")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 0. 角色设定")
    L.append("")
    L.append(p["role"])
    L.append("")
    L.append("本视角的审查重点：**%s**。" % p["focus"])
    L.append("")
    L.append("## 1. 审查目标")
    L.append("")
    L.append("- 被审文件：`%s`" % target_path)
    L.append("- 被审文件规模：%d 字符 / %d 行 / %d 个非空审查单元 / %d 张表 / %d 个数字"
             % (stats["chars"], stats["lines_total"], stats["units"], stats["tables"], stats["numbers"]))
    L.append("- **审查单元基准数：%d**（你回报的 `units_reviewed` 必须能对上这个数；少于它的 90%% 视为抽样，"
             "会被合并环节标红）" % stats["units"])
    L.append("- 你**不要修改被审文件**，只写你自己的结果文件。")
    L.append("")
    if embed:
        fence = _fence_for(target_text)
        L.append("### 被审文件全文（自包含，无需再去找文件）")
        L.append("")
        L.append(fence)
        L.append(target_text.rstrip("\n"))
        L.append(fence)
    else:
        L.append("### 被审文件全文")
        L.append("")
        L.append("（文件较大，未内联；请自行逐行读取 `%s`）" % target_path)
    L.append("")
    L.append("## 2. 七条铁律（违反任何一条，本次审查作废）")
    L.append("")
    for i, (t, d) in enumerate(IRON_RULES, 1):
        L.append("%d. **%s** —— %s" % (i, t, d))
    L.append("")
    L.append("## 3. 你的任务（%s）" % p["name"])
    L.append("")
    for m in p["mission"]:
        L.append("- %s" % m)
    L.append("")
    L.append("**本视角输出要求：%s**" % p["output_req"])
    L.append("")
    L.append(p["verdict_hint"])
    L.append("")
    L.append("## 4. 输出格式（严格照抄；合并环节要机读，格式错会被当成解析失败）")
    L.append("")
    L.append("```markdown")
    L.append(RESULT_TEMPLATE.format(
        pname=p["name"], key=key, target_name=target_name, units=stats["units"],
        result_path=result_path, extra_output=p["extra_output"]).rstrip("\n"))
    L.append("```")
    L.append("")
    L.append("格式硬要求：")
    L.append("")
    L.append("- 每条发现的标题行必须是 `### F-<两位数字> [必须改|可选优化|明确不要改] 标题`，方括号里的档位只有这三个词。")
    L.append("- 每个字段写一行（`- 位置：` / `- 原文：` / `- 问题：` / `- 直接替换为：` / `- 依据：`），字段内容不要换行。")
    L.append("- 原文引用用 `「」` 包裹，不要用换行分割引文。")
    L.append("- 发现少于 5 条也要老实写——不要为了凑数把可改可不改的写成「必须改」。")
    L.append("")
    L.append("## 5. 输出位置与回报")
    L.append("")
    L.append("- 结果文件（**必须写**）：`%s`" % result_path)
    L.append("- 最后回复里给一段话回报（照抄上面模板里的「逐字回报」段落）。")
    L.append("")
    return "\n".join(L)


def cmd_prep(args):
    target = args.target_file
    if not os.path.exists(target):
        print("⚠️ 目标文件不存在：%s" % target)
        return 2
    if os.path.isdir(target):
        print("⚠️ 目标是目录，请给具体文件：%s" % target)
        return 2

    keys = _resolve_keys(args.perspectives)
    if keys is None:
        return 2

    out_dir = os.path.abspath(args.out)
    results_dir = os.path.join(out_dir, "results")
    prompt_dir = out_dir
    try:
        os.makedirs(results_dir, exist_ok=True)
    except OSError as e:
        print("⚠️ 无法创建输出目录 %s：%s" % (out_dir, e))
        return 2

    text = _read(target)
    stats = count_units(text)
    embed = True
    if args.embed == "never":
        embed = False
    elif args.embed == "auto" and stats["chars"] > args.max_embed_chars:
        embed = False

    extra = ""
    if args.append:
        extra = _read(args.append) if os.path.exists(args.append) else args.append
        extra = extra.strip()

    written = []
    for k in keys:
        p = PERSPECTIVES[k]
        body = build_prompt(k, p, os.path.abspath(target), text, stats, out_dir, embed=embed)
        if extra:
            body += "\n## 6. 本次追加要求（派发者补充，优先级最高）\n\n%s\n" % extra
        fn = os.path.join(prompt_dir, "%s.md" % k)
        with open(fn, "w", encoding="utf-8") as f:
            f.write(body)
        written.append({
            "perspective": k, "name": p["name"], "prompt": fn,
            "result": os.path.join(results_dir, "%s.md" % k),
            "units_expected": stats["units"],
        })

    pack = {
        "tool": "red-team.py", "version": VERSION, "generated_at": _now(),
        "target": os.path.abspath(target), "target_name": os.path.basename(target),
        "stats": stats, "embed": embed, "perspectives": written,
        "merge_cmd": "python3 %s merge %s/*.md --out FINDINGS.md"
                     % (os.path.abspath(__file__), results_dir),
    }
    pack_fn = os.path.join(out_dir, "redteam-pack.json")
    with open(pack_fn, "w", encoding="utf-8") as f:
        json.dump(pack, f, ensure_ascii=False, indent=2)

    print("=" * 76)
    print("  红队任务包已生成 · %s" % _now())
    print("=" * 76)
    print("  目标文件：%s" % os.path.abspath(target))
    print("  规模：%d 字符 / %d 行 / %d 审查单元 / %d 张表 / %d 个数字（sha256:%s）%s"
          % (stats["chars"], stats["lines_total"], stats["units"], stats["tables"],
             stats["numbers"], stats["sha256"], "" if embed else "  ← 未内联全文"))
    print("  输出目录：%s" % out_dir)
    print("")
    print("  生成的提示词（每行一个，直接把整份文件内容作为子代理 prompt 派发）：")
    for w in written:
        size = os.path.getsize(w["prompt"])
        print("    [%-10s] %-16s %s  (%d 字节)" % (w["perspective"], w["name"], w["prompt"], size))
    print("")
    print("  各视角结果请让子代理写到：")
    for w in written:
        print("    %s" % w["result"])
    print("")
    print("  合并命令：")
    print("    %s" % pack["merge_cmd"])
    print("  包清单：%s" % pack_fn)
    print("=" * 76)
    return 0


def _resolve_keys(spec):
    if not spec:
        return list(DEFAULT_PERSPECTIVES)
    raw = [s.strip() for s in re.split(r"[,\s]+", spec) if s.strip()]
    if not raw or raw == ["all"]:
        return list(PERSPECTIVES.keys())
    bad = [k for k in raw if k not in PERSPECTIVES]
    if bad:
        print("⚠️ 未知视角：%s" % ", ".join(bad))
        print("   可选：%s / all" % ", ".join(PERSPECTIVES.keys()))
        return None
    # 去重保序
    out = []
    for k in raw:
        if k not in out:
            out.append(k)
    return out


# ============================================================
# 五、merge：合并各视角回报
# ============================================================
VERDICT_ALIAS = {
    "必须改": "必须改",
    "可选优化": "可选优化",
    "明确不要改": "明确不要改",
    "不要改": "明确不要改",
    "明确不改": "明确不要改",
}
VERDICT_ORDER = ["必须改", "可选优化", "明确不要改"]

HEAD_RE = re.compile(r"^#{2,4}\s*F[-_]?(\d+)\s*[\[【]\s*([^\]】]+?)\s*[\]】]\s*(.*)$")
FIELD_RE = re.compile(r"^\s*[-*]?\s*\*{0,2}(位置|原文|问题|直接替换为|建议改为|依据|数学分类|责任方|"
                      r"来源|时点|能否回答|风险)\*{0,2}\s*[:：]\s*(.*)$")
LOC_RE = re.compile(r"[Ll]?(\d+)")


class Finding(object):
    __slots__ = ("fid", "verdict", "title", "loc", "raw_loc", "quote", "problem",
                 "replacement", "evidence", "extra", "perspective", "pname", "src")

    def __init__(self, perspective="", pname="", src=""):
        self.fid = ""
        self.verdict = "可选优化"
        self.title = ""
        self.loc = ""            # 归一化行号 "42-58"
        self.raw_loc = ""        # 原样
        self.quote = ""
        self.problem = ""
        self.replacement = ""
        self.evidence = ""
        self.extra = OrderedDict()
        self.perspective = perspective
        self.pname = pname
        self.src = src

    def key(self):
        nums = LOC_RE.findall(self.raw_loc or "")
        if nums:
            return ("loc", nums[0], nums[-1])
        nq = _norm(self.quote)
        if len(nq) >= 6:
            return ("quote", nq[:32])
        return ("title", _norm(self.title)[:32])

    def sort_loc(self):
        nums = LOC_RE.findall(self.raw_loc or "")
        try:
            return (0, int(nums[0])) if nums else (1, 10 ** 9)
        except ValueError:
            return (1, 10 ** 9)


class Report(object):
    def __init__(self, path):
        self.path = path
        self.perspective = ""
        self.pname = ""
        self.target = ""
        self.units = None
        self.score = None
        self.summary = ""
        self.overall = ""
        self.extra = ""
        self.findings = []
        self.warnings = []


def parse_md_report(path):
    text = _read(path)
    rep = Report(path)
    base = os.path.basename(path)
    rep.perspective = os.path.splitext(base)[0]

    m = re.search(r"^\s*[-*]?\s*perspective\s*[:：]\s*(\S+)", text, re.M)
    if m:
        rep.perspective = m.group(1).strip().strip("`")
    m = re.search(r"^\s*[-*]?\s*target\s*[:：]\s*(.+)$", text, re.M)
    if m:
        rep.target = m.group(1).strip().strip("`")
    m = re.search(r"units_reviewed\s*[:：]\s*(\d+)", text)
    if m:
        rep.units = int(m.group(1))
    m = re.search(r"^\s*[-*]?\s*score\s*[:：]\s*(-?\d+)", text, re.M)
    if m:
        rep.score = int(m.group(1))
    m = re.search(r"^\s*[-*]?\s*summary\s*[:：]\s*(.+)$", text, re.M)
    if m:
        rep.summary = m.group(1).strip()

    # ## 总评 段落
    m = re.search(r"^##+\s*总评\s*$(.*?)(?=^##+\s|\Z)", text, re.M | re.S)
    if m:
        rep.overall = m.group(1).strip()
    # 视角专属输出 / 其余 2 级小节（整段保留）
    m = re.search(r"^##+\s*(视角专属输出.*?|专属输出.*?)$(.*?)(?=\Z)", text, re.M | re.S)
    if m:
        rep.extra = (m.group(1) + m.group(2)).strip()

    # 若视角名已知但未标 key，用名称反查
    if rep.perspective not in PERSPECTIVES:
        for k, p in PERSPECTIVES.items():
            if rep.perspective == p["name"] or p["name"] in rep.perspective:
                rep.perspective = k
                break
    rep.pname = PERSPECTIVES.get(rep.perspective, {}).get("name", rep.perspective or base)

    # ---- 解析发现 ----
    lines = text.split("\n")
    cur = None
    for idx, ln in enumerate(lines):
        hm = HEAD_RE.match(ln)
        if hm:
            if cur:
                rep.findings.append(cur)
            v = VERDICT_ALIAS.get(hm.group(2).strip())
            cur = Finding(rep.perspective, rep.pname, base)
            if v is None:                     # 非常规档位（如 math 的【算错】）→ 归可选优化并留证
                cur.extra["原始档位"] = hm.group(2).strip()
                v = "可选优化"
            cur.fid = "F-%s" % hm.group(1)
            cur.verdict = v
            cur.title = hm.group(3).strip() or "(无标题)"
            continue
        if cur is None:
            continue
        if re.match(r"^#{1,4}\s", ln):        # 下一个非发现小节 → 结束
            rep.findings.append(cur)
            cur = None
            continue
        fm = FIELD_RE.match(ln)
        if fm:
            k, v = fm.group(1), fm.group(2).strip()
            if k == "位置":
                cur.raw_loc = v
                nums = LOC_RE.findall(v)
                cur.loc = ("%s-%s" % (nums[0], nums[-1])) if nums else v
            elif k == "原文":
                cur.quote = v.strip("「」\"' ")
            elif k == "问题":
                cur.problem = v
            elif k in ("直接替换为", "建议改为"):
                cur.replacement = v.strip("「」\"' ")
            elif k == "依据":
                cur.evidence = v
            else:
                cur.extra[k] = v
            continue
        s = ln.strip()
        if s and not s.startswith("|") and cur.problem is not None and len(s) < 300:
            # 续行：接到最后一个已知字段
            if cur.evidence:
                cur.evidence += " " + s
            elif cur.problem:
                cur.problem += " " + s
    if cur:
        rep.findings.append(cur)

    # 过滤空壳发现
    rep.findings = [f for f in rep.findings if f.title and (f.problem or f.quote or f.extra)]
    if not rep.findings:
        rep.warnings.append("%s：未解析出任何 `### F-xx [档位] 标题` 形式的发现" % base)
    return rep


def parse_json_report(path):
    data = json.loads(_read(path))
    if isinstance(data, list):
        reps = []
        for item in data:
            reps.append(_json_to_report(path, item))
        return reps
    return [_json_to_report(path, data)]


def _json_to_report(path, data):
    rep = Report(path)
    base = os.path.basename(path)
    rep.perspective = str(data.get("perspective") or os.path.splitext(base)[0])
    rep.pname = PERSPECTIVES.get(rep.perspective, {}).get("name", rep.perspective)
    rep.target = str(data.get("target", ""))
    if isinstance(data.get("units_reviewed"), int):
        rep.units = data["units_reviewed"]
    if isinstance(data.get("score"), int):
        rep.score = data["score"]
    rep.summary = str(data.get("summary", ""))
    rep.overall = str(data.get("overall") or data.get("总评") or "")
    rep.extra = str(data.get("extra", ""))
    for i, fd in enumerate(data.get("findings", []) or [], 1):
        f = Finding(rep.perspective, rep.pname, base)
        f.fid = str(fd.get("id") or ("F-%02d" % i))
        v = VERDICT_ALIAS.get(str(fd.get("verdict", "")).strip())
        if v is None:
            f.extra["原始档位"] = str(fd.get("verdict", ""))
            v = "可选优化"
        f.verdict = v
        f.title = str(fd.get("title", "")) or "(无标题)"
        f.raw_loc = str(fd.get("location", ""))
        nums = LOC_RE.findall(f.raw_loc)
        f.loc = ("%s-%s" % (nums[0], nums[-1])) if nums else f.raw_loc
        f.quote = str(fd.get("quote", "")).strip("「」\"' ")
        f.problem = str(fd.get("problem", ""))
        f.replacement = str(fd.get("replacement", "")).strip("「」\"' ")
        f.evidence = str(fd.get("evidence", ""))
        for k in ("数学分类", "责任方", "来源", "时点", "风险"):
            if fd.get(k):
                f.extra[k] = str(fd[k])
        rep.findings.append(f)
    if not rep.findings:
        rep.warnings.append("%s：JSON 内无 findings" % base)
    return rep


def load_reports(patterns):
    paths = []
    for pat in patterns:
        if os.path.isdir(pat):
            pat = os.path.join(pat, "*.md")
        hit = sorted(_glob.glob(pat)) if any(c in pat for c in "*?[") else [pat]
        for h in hit:
            if h not in paths and os.path.isfile(h):
                paths.append(h)
    reports = []
    for p in paths:
        try:
            if p.lower().endswith(".json"):
                reports.extend(parse_json_report(p))
            else:
                reports.append(parse_md_report(p))
        except Exception as e:
            r = Report(p)
            r.warnings.append("解析失败：%s" % e)
            reports.append(r)
    return paths, reports


def _loc_overlap(a, b):
    """位置是否指向同一处：起点相同，或一方是单点且落在另一方区间内"""
    na, nb = LOC_RE.findall(a.raw_loc or ""), LOC_RE.findall(b.raw_loc or "")
    if not na or not nb:
        return False
    a1, a2 = int(na[0]), int(na[-1])
    b1, b2 = int(nb[0]), int(nb[-1])
    if a1 == b1:
        return True
    if a1 == a2 and b1 <= a1 <= b2:
        return True
    if b1 == b2 and a1 <= b1 <= a2:
        return True
    return False


def _topic_sim(a, b):
    """话题相似度：优先比原文引用，其次比标题（0~1）"""
    qa, qb = _norm(a.quote), _norm(b.quote)
    if len(qa) >= 8 and len(qb) >= 8:
        if qa in qb or qb in qa:
            return max(0.9, difflib.SequenceMatcher(None, qa, qb).ratio())
        return difflib.SequenceMatcher(None, qa, qb).ratio()
    ta, tb = _norm(a.title), _norm(b.title)
    if len(ta) >= 6 and len(tb) >= 6:
        return difflib.SequenceMatcher(None, ta, tb).ratio()
    return 0.0


def _similar(a, b):
    """是否算「同一个问题」：
       ① 位置指向同一处 且 话题相关（引用同一句 / 标题相近）→ 并组
       ② 话题高度相似（引用同一句）→ 即使位置标注不同也并组
       ③ 位置指向同一处 但有一方缺引用 → 并组
       ★ 只靠「位置相同」不足以并组：同一行上可能压着两个不同问题，
         此时不并组，改为互相交叉引用（渲染时标注「同位置另有问题」）。"""
    same_loc = a.key() == b.key()
    sim = _topic_sim(a, b)
    if same_loc and sim >= 0.35:
        return True
    if sim >= 0.70:
        return True
    if _loc_overlap(a, b) and sim >= 0.5:
        return True
    if same_loc and (not _norm(a.quote) or not _norm(b.quote)):
        return True
    return False


def group_findings(reports):
    """按「问题」去重：位置 → 原文 → 标题；近似位置/近似原文自动并组"""
    groups = []          # [{"members":[Finding], "key":k}]
    index = {}           # key -> [group 下标]（同一 key 可以对应多个组：同一行上可能压着不同问题）
    for rep in reports:
        for f in rep.findings:
            k = f.key()
            gi = None
            # ① 先在同 key 的组里找话题相关的（位置相同但话题无关 → 不并）
            for cand in index.get(k, []):
                if any(_similar(f, m) for m in groups[cand]["members"]):
                    gi = cand
                    break
            # ② 再全局找话题高度相似的（位置标注不同，但引用的是同一句）
            if gi is None:
                for i, g in enumerate(groups):
                    if any(_similar(f, m) for m in g["members"]):
                        gi = i
                        break
            if gi is None:
                groups.append({"members": [f], "key": k})
                gi = len(groups) - 1
            else:
                groups[gi]["members"].append(f)
            index.setdefault(k, [])
            if gi not in index[k]:
                index[k].append(gi)
    return groups


def _merge_verdict(members):
    """合并档位：取最严（必须改 > 可选优化 > 明确不要改）"""
    ranks = {v: i for i, v in enumerate(VERDICT_ORDER)}
    return sorted(set(m.verdict for m in members), key=lambda v: ranks.get(v, 9))[0]


def _persp_label(members):
    seen = []
    for m in members:
        tag = "%s（%s）" % (m.perspective, m.pname) if m.pname and m.pname != m.perspective else m.perspective
        if tag not in seen:
            seen.append(tag)
    return "、".join(seen)


def _group_title(members, join_distinct=False):
    """组标题：默认取首条；join_distinct=True 时把明显不同的标题并列（用于视角冲突）"""
    if not join_distinct:
        return members[0].title
    kept = []
    for m in members:
        t = m.title
        if not t:
            continue
        nt = _norm(t)
        if any(difflib.SequenceMatcher(None, nt, _norm(x)).ratio() >= 0.6 for x in kept):
            continue
        kept.append(t)
        if len(kept) >= 3:
            break
    return " ｜ ".join(kept) or members[0].title


def _bullets(m, out):
    out.append("- **位置**：%s" % (m.raw_loc or "全文"))
    if m.quote:
        out.append("- **原文**：「%s」" % m.quote)
    if m.problem:
        out.append("- **问题**：%s" % m.problem)
    if m.replacement:
        out.append("- **直接替换为**：「%s」" % m.replacement)
    if m.evidence:
        out.append("- **依据**：%s" % m.evidence)
    for k, v in m.extra.items():
        out.append("- **%s**：%s" % (k, v))


def _is_conflict(g):
    """视角冲突：≥2 个**不同视角**对同一处给出不同档位。
       （同一视角在同一处给了两个档位 → 不算视角冲突，按各自档位分节，另加交叉引用）"""
    ms = g["members"]
    if len(set(m.perspective for m in ms)) < 2:
        return False
    return len(set(m.verdict for m in ms)) > 1


def _demote_headings(text, by=2):
    """把嵌入的原文标题降级（合并报告只有 5 个 H2 章节，嵌入内容不得再出现 H2）"""
    out = []
    for ln in (text or "").split("\n"):
        m = re.match(r"^(#{1,6})\s", ln)
        if m:
            ln = "#" * min(6, len(m.group(1)) + by) + ln[len(m.group(1)):]
        out.append(ln)
    return "\n".join(out)


def render_merge(reports, groups, paths, pack=None):
    out = []
    all_findings = [f for r in reports for f in r.findings]
    by_verdict = {v: [] for v in VERDICT_ORDER}
    conflicts = []
    for g in groups:
        if _is_conflict(g):
            conflicts.append(g)
        else:
            by_verdict[_merge_verdict(g["members"])].append(g)

    for v in VERDICT_ORDER:
        by_verdict[v].sort(key=lambda g: g["members"][0].sort_loc())

    # 同一位置压着多个不同问题 → 交叉引用
    loc_index = {}
    for g in groups:
        k = g["members"][0].key()
        if k[0] == "loc":
            loc_index.setdefault(k, []).append(g)

    # 先分配展示编号（供交叉引用）
    display = {}
    tag_of = {"必须改": "M", "可选优化": "O", "明确不要改": "D"}
    for v in VERDICT_ORDER:
        for i, g in enumerate(by_verdict[v], 1):
            display[id(g)] = "%s-%02d" % (tag_of[v], i)
    for i, g in enumerate(conflicts, 1):
        display[id(g)] = "C-%02d" % i

    def _xref(g):
        sibs = [display[id(o)] for o in loc_index.get(g["members"][0].key(), []) if o is not g]
        if not sibs:
            return None
        return "- **同位置另有问题**：%s（同一行上压着 %d 条不同问题，改这一处时一并看）" % (
            "、".join(sibs), len(sibs))

    target = ""
    for r in reports:
        if r.target:
            target = r.target
            break

    out.append("# 红队合并报告%s" % (" · %s" % target if target else ""))
    out.append("")
    out.append("- 生成时间：%s · 工具：red-team.py v%s" % (_now(), VERSION))
    out.append("- 输入：%d 个结果文件" % len(paths))
    for p in paths:
        out.append("  - `%s`" % p)
    out.append("- 参与视角：%s" % ("、".join(
        "%s（%s）" % (r.perspective, r.pname) for r in reports) or "（无）"))
    out.append("- 发现：合计 %d 条 → 去重合并为 %d 处（必须改 %d / 可选优化 %d / 明确不要改 %d）+ 视角冲突 %d 处"
               % (len(all_findings), len(groups), len(by_verdict["必须改"]),
                  len(by_verdict["可选优化"]), len(by_verdict["明确不要改"]), len(conflicts)))
    # units_reviewed 通读核验
    checks = []
    for r in reports:
        exp = (pack or {}).get("units_expected", {}).get(r.perspective)
        if exp is None:
            exp = (pack or {}).get("stats", {}).get("units")
        if r.units is None:
            checks.append("%s：未回报 units_reviewed ⚠️" % r.perspective)
        elif exp:
            ratio = r.units / float(exp)
            flag = "✅" if ratio >= 0.9 else ("⚠️ 疑似抽样" if ratio >= 0.5 else "❌ 明显未通读")
            checks.append("%s：%d / 基准 %d（%.0f%%）%s" % (r.perspective, r.units, exp, ratio * 100, flag))
        else:
            checks.append("%s：%d（无基准）" % (r.perspective, r.units))
    out.append("- 通读核验（units_reviewed）：%s" % ("；".join(checks) or "（无）"))
    warns = [w for r in reports for w in r.warnings]
    if warns:
        out.append("- ⚠️ 解析告警：")
        for w in warns:
            out.append("  - %s" % w)
    out.append("")

    # ---- 必须改 ----
    for v in VERDICT_ORDER:
        title = {"必须改": "## 必须改", "可选优化": "## 可选优化", "明确不要改": "## 明确不要改"}[v]
        out.append(title)
        out.append("")
        lst = by_verdict[v]
        if not lst:
            out.append("（无）")
            out.append("")
            continue
        for i, g in enumerate(lst, 1):
            ms = g["members"]
            tag = {"必须改": "M", "可选优化": "O", "明确不要改": "D"}[v]
            out.append("### %s-%02d %s" % (tag, i, ms[0].title))
            out.append("")
            out.append("- **提到方**：%s%s" % (
                _persp_label(ms), "  ← 多视角独立命中" if len(set(m.perspective for m in ms)) > 1 else ""))
            out.append("- **原始编号**：%s" % "、".join("%s/%s" % (m.perspective, m.fid) for m in ms))
            x = _xref(g)
            if x:
                out.append(x)
            out.append("")
            for m in ms:
                if len(ms) > 1:
                    out.append("#### 视角 %s · %s" % (m.perspective, m.pname))
                    out.append("")
                _bullets(m, out)
                out.append("")

    # ---- 视角冲突 ----
    out.append("## 视角冲突")
    out.append("")
    if not conflicts:
        out.append("（无：各视角对同一处的判定档位一致）")
        out.append("")
    else:
        out.append("> 多个视角对**同一处**判断不同（档位分歧）。单列在此，不进上面的分节，避免被单方判断覆盖。")
        out.append("")
        for i, g in enumerate(conflicts, 1):
            ms = g["members"]
            out.append("### C-%02d %s" % (i, _group_title(ms, join_distinct=True)))
            out.append("")
            out.append("- **位置**：%s" % (ms[0].raw_loc or "全文"))
            out.append("- **分歧档位**：%s" % " vs ".join(sorted(set(m.verdict for m in ms))))
            out.append("- **建议**：按较严的一方处理（`%s`），或先向分歧双方核实事实再定"
                       % _merge_verdict(ms))
            x = _xref(g)
            if x:
                out.append(x)
            out.append("")
            for m in ms:
                out.append("#### 视角 %s · %s —— `%s`" % (m.perspective, m.pname, m.verdict))
                out.append("")
                _bullets(m, out)
                out.append("")

    # ---- 各视角总评与评分 ----
    out.append("## 各视角总评与评分（如有）")
    out.append("")
    if not reports:
        out.append("（无）")
    for r in reports:
        head = "### %s · %s" % (r.perspective, r.pname)
        meta = []
        if r.score is not None:
            meta.append("评分 %d/100" % r.score)
        if r.units is not None:
            meta.append("units_reviewed %d" % r.units)
        meta.append("发现 %d 条" % len(r.findings))
        out.append(head + "　—　" + " · ".join(meta))
        out.append("")
        if r.summary:
            out.append("**一句话总评**：%s" % r.summary)
            out.append("")
        if r.overall:
            out.append(r.overall)
            out.append("")
        if r.extra:
            out.append("#### 视角专属输出")
            out.append("")
            out.append(_demote_headings(r.extra, 2))
            out.append("")
        if not (r.summary or r.overall or r.extra):
            out.append("（该视角未给总评）")
            out.append("")
    out.append("---")
    out.append("")
    out.append("由 red-team.py 合并 %d 个视角报告 · 去重键：位置行号 → 原文片段 → 标题" % len(reports))
    return "\n".join(out) + "\n"


def cmd_merge(args):
    paths, reports = load_reports(args.inputs)
    if not paths:
        print("⚠️ 没有匹配到任何结果文件：%s" % " ".join(args.inputs))
        return 2

    pack = None
    pack_path = args.pack
    if not pack_path:
        for cand in [os.path.join(os.path.dirname(os.path.abspath(paths[0])), "..", "redteam-pack.json"),
                     os.path.join(os.path.dirname(os.path.abspath(paths[0])), "redteam-pack.json")]:
            cand = os.path.normpath(cand)
            if os.path.exists(cand):
                pack_path = cand
                break
    if pack_path and os.path.exists(pack_path):
        try:
            pack = json.loads(_read(pack_path))
            if pack.get("stats"):
                pack["units_expected"] = {w["perspective"]: w["units_expected"]
                                          for w in pack.get("perspectives", [])}
        except Exception as e:
            print("⚠️ 包清单读取失败（忽略）：%s" % e)

    groups = group_findings(reports)
    doc = render_merge(reports, groups, paths, pack)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(doc)
        n_conf = sum(1 for g in groups if len(set(m.verdict for m in g["members"])) > 1)
        print("=" * 76)
        print("  合并完成 · %s" % _now())
        print("=" * 76)
        print("  输入：%d 个文件 / %d 个视角" % (len(paths), len(reports)))
        print("  发现：%d 条 → %d 处（合并去重）" % (
            sum(len(r.findings) for r in reports), len(groups)))
        print("  视角冲突：%d 处" % n_conf)
        for r in reports:
            print("  [%-11s] %-14s 发现 %2d 条 · units_reviewed %s · 评分 %s"
                  % (r.perspective, r.pname, len(r.findings),
                     r.units if r.units is not None else "未报",
                     r.score if r.score is not None else "未报"))
        for r in reports:
            for w in r.warnings:
                print("  ⚠️ %s" % w)
        print("  输出：%s" % os.path.abspath(args.out))
        print("=" * 76)
    else:
        sys.stdout.write(doc)

    if args.json_out:
        payload = {"generated_at": _now(), "target": next((r.target for r in reports if r.target), ""),
                   "inputs": paths,
                   "perspectives": [{"perspective": r.perspective, "name": r.pname,
                                     "units_reviewed": r.units, "score": r.score,
                                     "summary": r.summary, "findings": len(r.findings)}
                                    for r in reports],
                   "groups": [{"verdict": _merge_verdict(g["members"]),
                               "title": g["members"][0].title,
                               "perspectives": sorted(set(m.perspective for m in g["members"])),
                               "conflict": len(set(m.verdict for m in g["members"])) > 1,
                               "members": [{"perspective": m.perspective, "id": m.fid,
                                            "verdict": m.verdict, "location": m.raw_loc,
                                            "quote": m.quote, "problem": m.problem,
                                            "replacement": m.replacement, "evidence": m.evidence}
                                           for m in g["members"]]}
                              for g in groups]}
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print("  JSON：%s" % os.path.abspath(args.json_out))
    return 0


# ============================================================
# 六、list
# ============================================================
def cmd_list(args):
    print("=" * 76)
    print("  红队视角模板 · red-team.py v%s" % VERSION)
    print("=" * 76)
    for k, p in PERSPECTIVES.items():
        print("  %-11s %s" % (k, p["name"]))
        print("      审查重点：%s" % p["focus"])
        print("      输出要求：%s" % p["output_req"])
        print("      角色：%s" % p["role"].replace("**", ""))
        print("      任务：")
        for m in p["mission"]:
            print("        · %s" % (m if len(m) <= 88 else m[:88] + "…"))
        print("      专属输出块：%s" % p["extra_output"].split("\n")[0])
        print("")
    print("  派发时每个视角一份提示词文件，内含统一七条铁律：")
    for i, (t, d) in enumerate(IRON_RULES, 1):
        print("    %d. %s" % (i, t))
    print("")
    print("  用法：")
    print("    python3 red-team.py prep <目标文件> --perspectives %s --out DIR"
          % ",".join(DEFAULT_PERSPECTIVES))
    print("    python3 red-team.py merge DIR/results/*.md --out FINDINGS.md")
    print("=" * 76)
    return 0


# ============================================================
# 七、入口
# ============================================================
def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="red-team.py",
        description="红队编排器 v%s：生成多视角红队提示词任务包 + 合并各视角回报（零依赖 / Python 3.9+）"
                    % VERSION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="视角：%s\n"
               "例：\n"
               "  red-team.py prep 材料.md --perspectives platform,math,expression --out /tmp/redteam/\n"
               "  red-team.py merge /tmp/redteam/results/*.md --out FINDINGS.md\n"
               "  red-team.py list\n" % ", ".join(PERSPECTIVES.keys()))
    ap.add_argument("--version", action="version", version="red-team.py v%s" % VERSION)
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    sub = ap.add_subparsers(dest="cmd")

    p1 = sub.add_parser("prep", help="生成多视角红队提示词任务包")
    p1.add_argument("target_file", help="被审材料（md/txt/html 等纯文本）")
    p1.add_argument("--perspectives", "-p", default=",".join(DEFAULT_PERSPECTIVES),
                    help="逗号分隔：%s / all" % ",".join(PERSPECTIVES.keys()))
    p1.add_argument("--out", "-o", default="./redteam-pack", help="任务包输出目录")
    p1.add_argument("--embed", choices=["auto", "always", "never"], default="auto",
                    help="是否把目标文件全文内联进提示词（默认 auto：≤8 万字符则内联）")
    p1.add_argument("--max-embed-chars", type=int, default=80000, help="auto 模式的内联上限")
    p1.add_argument("--append", default=None, help="追加到每个提示词的补充要求（文本或文件路径）")

    p2 = sub.add_parser("merge", help="合并各视角回报（md / json）")
    p2.add_argument("inputs", nargs="+", help="结果文件（支持通配符与目录）")
    p2.add_argument("--out", "-o", default=None, help="汇总输出文件（省略则打印到 stdout）")
    p2.add_argument("--pack", default=None, help="任务包清单 redteam-pack.json（用于 units_reviewed 核验）")
    p2.add_argument("--json-out", default=None, help="同时输出机器可读 json")

    p3 = sub.add_parser("list", help="列出现有视角模板")
    p3.set_defaults(cmd="list")

    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help()
        return 1
    if args.cmd == "prep":
        return cmd_prep(args)
    if args.cmd == "merge":
        return cmd_merge(args)
    if args.cmd == "list":
        return cmd_list(args)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
