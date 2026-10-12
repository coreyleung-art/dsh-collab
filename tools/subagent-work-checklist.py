#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""subagent-work-checklist — 派子代理工作安排检查清单（可跑的，不是文档）。

★ 立据（2026-10-12 · 20 个子代理的实战）：
  ★ 当晚 **9 调研 + 5 撰写 + 3 审查 + 3 其他**，产出约 20,000 行；★ 但同时暴露：
    · **V2 审查两次皆空**（★ 派了两次、0 篇产出）
    · **R2 首次零产出**（★ 跑了约 40 分钟、只留 evidence/）
    · **20 个代理【一个都没引用】本仓已有的 10 个 lint/gate**（★ 逐条实测 0 次）
  ★★ 而事后复盘发现：★ **这三件都有【事前的结构性预防】——就是本清单。**

★★ 用法：
  subagent-work-checklist.py --stage pre   [--module M1] [--prompt-file f.txt]
  subagent-work-checklist.py --stage mid
  subagent-work-checklist.py --stage post  [--artifacts <dir>]
  subagent-work-checklist.py --selftest

三态：`--prompt-file` 给了但读不到 ⇒ 「不可判」；未给 ⇒ 只列清单不判分。
"""
import io
import os
import re
import sys
import json
import argparse
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── 段一 · 派工前（★ 七项，缺一即风险）──
PRE = [
    ("P1", "目标从【登记了什么没做完】正推，不从【我手上有什么】反推",
     "★ 反面实证：初版大纲只盖四维+M4，而锚点实际有 91 项未完成"),
    ("P2", "提示词含【既有 lint/gate 清单】",
     "★★ 本仓已有 14 个 lint/gate，★ 而当晚 20 个代理一个都没引用 —— 逐条实测 0 次"),
    ("P3", "提示词含【你必须吸收的已确认发现】",
     "★ 防重建：★ 否则 5 个撰写代理各自重建一遍 ⇒ 两边口径打架"),
    ("P4", "提示词含【你必须自己现测的】清单",
     "★ 防照抄：★ v6.1 的读数在 28 小时内被推翻 22 处"),
    ("P5", "提示词含【自我保护】条（上游缺位时它自己替代做什么）",
     "★★ 实战有效：V2 两次皆空，而 W1/W2 各自替代核查并抓到本线 3 处错"),
    ("P6", "提示词含【硬性纪律】（原子写 / 阳性对照 / 退出码在管道前 / 不改既有件）",
     "★ 实测：写进提示词的四条【全被执行】；未写的不会被遵守"),
    ("P7", "要求文末自报【限制】+ 声明【同一主体⇒不能自证独立】",
     "★ 实测：所有代理都写了限制节；★ 而这逼它们自己划边界"),
]

# ── 段二 · 派工中 ──
MID = [
    ("M1", "失败即重派，不纠缠、不因一次失败改整个流程",
     "★ 实证：R2 首次零产出 ⇒ 重派后交付 8 篇 1592 行；V2 两次皆空 ⇒ 不再派、由 W1/W2 替代"),
    ("M2", "零产出/空目录要【如实记】，不假称完成",
     "★ 读目录核 md 篇数与行数，★ 不看它的自述"),
    ("M3", "代理的【自曝】要收下并记一笔（★ 自曝是质量的信号）",
     "★ 实测：R2 自曝 3 次探针事故 · W1 自曝 3 处自己的错 · W2 自曝落盘后复跑发现数错"),
    ("M4", "代理【推翻自己人】要收下并交叉核对（★ 这是流程在起作用）",
     "★ W1 推翻「G-CR 门有 5 条自证」· W2 推翻「11 个目录」· W5 推翻「三条件未找到」"),
]

# ── 段三 · 收工（★ 六项验收）──
POST = [
    ("V1", "每条读数【本轮现测 + 带时刻】",
     "★ 抽查：★ 核其时刻是否落在本轮窗口内"),
    ("V2", "凡断言「某机制有效」，有【它在什么输入下会红】",
     "★★ 给不出 ⇒ 标「未验」，★ 不得当作成立"),
    ("V3", "凡报「未搜到」，有【必定命中的阳性对照】",
     "★ 实证：3 个代理踩过（含本线 2 次）——★ 用本机不存在的 timeout 命令，一批「0 命中」是探针坏了"),
    ("V4", "未修改 `docs/` 既有件（★ 双 sha 核对）",
     "★ 实测：全部代理均自证未改；★ 锚点 sha 为证"),
    ("V5", "写文件用了【临时文件 + 原子替换】",
     "★ 实证：本线当天因 `open(p,\"w\")` 先截断 + 写入失败，★ 清空了 634 KB 台账"),
    ("V6", "产出可复跑（★ 抽 2–3 条命令真跑一遍，与文中原始输出逐字对）",
     "★ 这是【审查代理】的核心动作，★ 也是收工验收的最低标准"),
]


def load_prompt(path):
    if path is None:
        return None, None
    if not os.path.exists(path):
        return None, "★ 提示词文件读不到 ⇒ 不可判（★ 读不到 ≠ 不存在）"
    try:
        return io.open(path, encoding="utf-8").read(), None
    except Exception as e:
        return None, "★ 提示词读取失败 %s ⇒ 不可判" % type(e).__name__


def judge_pre(prompt_text):
    """★ 七项逐条判（★ 只在给了提示词时）。"""
    checks = {
        "P1": None,  # ★ 无法从文本自动判「正推 vs 反推」⇒ 人工项
        "P2": bool(re.search(r'lint-inventory|既有 lint|evidence-channel-guard|csx-canfail-check', prompt_text)),
        "P3": bool(re.search(r'必须吸收|已确认发现|已独立复现', prompt_text)),
        "P4": bool(re.search(r'必须.*自己现测|不得照抄', prompt_text)),
        "P5": bool(re.search(r'自我保护', prompt_text)),
        "P6": bool(re.search(r'原子替换|临时文件', prompt_text)) and bool(re.search(r'阳性对照', prompt_text)),
        "P7": bool(re.search(r'不能自证独立|同一主体|限制', prompt_text)),
    }
    return checks


def render(items, checks=None):
    L = []
    for cid, what, why in items:
        mark = ""
        if checks is not None and cid in checks:
            v = checks[cid]
            mark = "  ← ★ 自动判：%s" % ("✓ 已含" if v else ("— 人工项" if v is None else "❌ 未含"))
        L.append("  [%s] %s%s" % (cid, what, mark))
        L.append("        ★ 依据：%s" % why)
    return "\n".join(L)


def selftest():
    ok = tot = 0
    # ★ 正控：三段各有条目
    tot += 1
    if len(PRE) >= 5 and len(MID) >= 3 and len(POST) >= 5:
        ok += 1; print("  ✅ 正控：三段条目齐（pre=%d mid=%d post=%d）" % (len(PRE), len(MID), len(POST)))
    else:
        print("  ❌ 正控：三段条目不足")
    # ★ 正控：含 lint 清单的提示词 ⇒ P2 判 ✓
    tot += 1
    c = judge_pre("请先跑 python3 tools/lint-inventory.py --prompt 并粘入")
    if c["P2"] is True:
        ok += 1; print("  ✅ 正控：含 lint-inventory ⇒ P2 判 ✓")
    else:
        print("  ❌ 正控：含 lint-inventory 却未判出")
    # ★ 负控：空提示词 ⇒ P2 判 ❌（可红）
    tot += 1
    c2 = judge_pre("")
    if c2["P2"] is False:
        ok += 1; print("  ✅ 负控：空提示词 ⇒ P2 判 ❌（可红）")
    else:
        print("  ❌ 负控：空提示词竟判通过")
    # ★ 负控：不存在的提示词文件 ⇒ 不可判文案（不冒充通过）
    tot += 1
    t, err = load_prompt("/tmp/__no_such_prompt__.txt")
    if t is None and err and "不可判" in err:
        ok += 1; print("  ✅ 负控：提示词不存在 ⇒ 报「不可判」（★ 不冒充通过）")
    else:
        print("  ❌ 负控：不存在的提示词未报不可判")
    # ★ 正控：P6 需【原子替换 ∧ 阳性对照】两者皆有
    tot += 1
    c3 = judge_pre("写文件用临时文件 + 原子替换")
    if c3["P6"] is False:
        ok += 1; print("  ✅ 正控：只含「原子替换」⇒ P6 仍判 ❌（★ 需两者皆有）")
    else:
        print("  ❌ 正控：P6 判据过宽（缺阳性对照也通过）")
    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["pre", "mid", "post"], default="pre")
    ap.add_argument("--prompt-file", default=None)
    ap.add_argument("--module", default=None)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("subagent-work-checklist 1.0.0")
        return 0
    if a.selftest:
        return selftest()

    print("== subagent-work-checklist 1.0.0 · stage=%s%s =="
          % (a.stage, (" · module=%s" % a.module) if a.module else ""))
    print()
    if a.stage == "pre":
        checks = None
        if a.prompt_file is not None:
            t, err = load_prompt(a.prompt_file)
            if t is None:
                print("  " + err)
                return 2
            checks = judge_pre(t)
        print("  ── 段一 · 派工前（7 项）──")
        print(render(PRE, checks))
        if checks is not None:
            miss = [k for k, v in checks.items() if v is False]
            print()
            if miss:
                print("  ❌ 未含 %d 项：%s" % (len(miss), ",".join(miss)))
                print("     ★ 修法：`python3 tools/lint-inventory.py --prompt` 取 P2 片段；其余按上表补")
                return 1
            print("  ✅ 自动可判的 6 项全含（★ P1 为人工项）")
        return 0
    if a.stage == "mid":
        print("  ── 段二 · 派工中（4 项）──")
        print(render(MID))
        return 0
    print("  ── 段三 · 收工验收（6 项）──")
    print(render(POST))
    return 0


if __name__ == "__main__":
    sys.exit(main())
