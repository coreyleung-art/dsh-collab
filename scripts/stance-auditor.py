#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
立场排查器 · Stance Auditor v1.4（16 项标准）
================================
针对「不同文件 × 不同角色对象」，审查其表述逻辑是否正确（16 项标准 · 插件化）。

设计动机
--------
同一份内容，给不同人看时"该说什么、不该说什么、怎么说"完全不同。人工容易漏，也容易
过度清理（例：用「资方」做关键词清除，会误伤「出资方式」「出资方」等合法词）。
本工具把判断规则显式化为可插拔的 16 个插件，逐项给出「问题 + 位置 + 建议」。
v1.4 新增 P16「数字归属清晰性」：比例/成绩/数量类数字必须能答上「分母是什么、分子是什么、
谁做的（我方/承接/借用/行业）、什么时候做的」四个问题，答不上来标「⚠️ 归属不清」（严重度轻微，
仅作提示——这条最容易误报）。

用法
----
  python3 stance-auditor.py <文件> --audience shareholder        # 单文件审查
  python3 stance-auditor.py <文件1> <文件2> --audience investor  # 多文件
  python3 stance-auditor.py <文件> --audience all                # 所有受众各审一遍
  python3 stance-auditor.py <文件> --audience shareholder --json # 机器可读输出
  python3 stance-auditor.py --list                               # 列出 16 项标准与受众档案

受众档案（audience profiles）
----------------------------
  shareholder  股东（橙果等）      —— 要看清自己的权利义务；不该看到他方私人安排
  investor     潜在投资人          —— 要看清回报与风险；不该看到内部流程
  partner      合作方              —— 要看清合作边界；不该看到股权细节
  internal     内部团队/执行层      —— 要看清自己负责什么；可看方法论
  public       公开版/对外宣传      —— 任何人都可能看到；不得含敏感信息
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import sys, os, re, json, argparse
from collections import OrderedDict

# ============================================================
# 一、受众档案：每个角色"该看到什么 / 不该看到什么"
# ============================================================
AUDIENCES = OrderedDict([
    ("shareholder", {
        "name": "股东（橙果等）",
        "sees": "自己的出资/权利/义务、公司结构与对赌、各轮选项、退出路径",
        "not_sees": "他方（尤其是梁振宇）的私人资金安排、内部文档生产流程、内部工具代号",
        "term_level": "unknown",      # 需要术语解释
        "敏感词": ["内部备忘", "个人资产", "个人信用", "私事"],
    }),
    ("investor", {
        "name": "潜在投资人",
        "sees": "市场/单位经济/预算/里程碑/估值依据/风险；不看内部工具与方法论",
        "not_sees": "内部写作规范、模板来源名、内部格式代号、内部文件名、股东间私聊内容",
        "term_level": "unknown",
        "敏感词": ["内部工程", "元信息", "草稿", "待我确认"],
    }),
    ("partner", {
        "name": "合作方（平台/供应链/IP 方）",
        "sees": "合作边界、交付标准、结算方式、对等义务",
        "not_sees": "股权细节、各方对赌条款、内部预算明细",
        "term_level": "unknown",
        "敏感词": ["股权", "对赌", "出资额", "估值"],
    }),
    ("internal", {
        "name": "内部团队 / 执行层",
        "sees": "几乎全部（含方法论、工具代号、内部流程）",
        "not_sees": "无（但应避免把内部口径误当对外口径使用）",
        "term_level": "known",
        "敏感词": [],
    }),
    ("public", {
        "name": "公开版（任何人都可能看到）",
        "sees": "业务是什么、市场、模式、愿景",
        "not_sees": "★ 不得含：具体股权比例、对赌条款、牌照归属细节、具体金额、合作方名称",
        "term_level": "unknown",
        "敏感词": ["授权链", "对赌", "出资额", "51%", "49%", "回购", "优先清算"],
    }),
])

# ============================================================
# 二、16 项标准（插件）——每项一个函数
# ============================================================
PLUGINS = []

def plugin(pid, name, desc, applies="all"):
    """注册插件（装饰器）"""
    def deco(fn):
        PLUGINS.append({"id": pid, "name": name, "desc": desc, "applies": applies, "fn": fn})
        return fn
    return deco


def _lines(text):
    return text.split("\n")


def _find(text, pattern, flags=0, limit=20):
    """返回 [(行号, 行内容)]"""
    out = []
    for i, ln in enumerate(_lines(text)):
        if re.search(pattern, ln, flags):
            out.append((i + 1, ln.strip()[:160]))
            if len(out) >= limit:
                break
    return out


# ---------- P01 受众术语适配 ----------
@plugin("P01", "受众术语适配", "专业词首次出现是否解释（面向不懂行的受众）")
def p01(text, aud, meta):
    if aud["term_level"] == "known":
        return []
    terms = meta.get("terms", [])
    issues = []
    for t in terms:
        hits = [i for i, ln in enumerate(_lines(text)) if t in ln]
        if not hits:
            continue
        first = hits[0]
        window = "\n".join(_lines(text)[first:first + 3])
        has_def = any(k in window for k in ["是指", "指", "即", "也就是", "——", "（", "俗称"])
        if not has_def:
            issues.append({
                "level": "轻微", "line": first + 1,
                "msg": f"术语「{t}」首次出现未解释（面向前两类受众应加一句话解释）",
                "snippet": _lines(text)[first].strip()[:100],
            })
    return issues


# ---------- P02 内部元信息隔离 ----------
@plugin("P02", "内部元信息隔离", "是否含「文档是怎么生产出来的」类信息")
def p02(text, aud, meta):
    if aud["name"].startswith("内部"):
        return []
    patterns = [
        (r"写作纪律|撰写纪律|写作规范|本文的写法|本文件的写法", "写作规范（内部 QA 标准）"),
        (r"阅读前须知|这份文件写给|写给三类读者|写给谁看", "文档受众说明（内部元信息）"),
        (r"红杉|F君|BP-9|BP9", "内部模板/格式来源名"),
        (r"v1|v2|旧版|本版|上一版|修订|作废口径|修正记录|已被取代", "修订痕迹"),
        (r"`[A-Z][A-Z0-9_\-]{6,}\.md`|`[A-Z][A-Z0-9_\-]{6,}\.json`", "内部文件名引用"),
        (r"内部备忘|内部文件|内部命名|统一叫法", "内部口径说明"),
    ]
    issues = []
    for pat, label in patterns:
        for ln, content in _find(text, pat, re.I, limit=6):
            issues.append({
                "level": "严重" if "修订" in label or "模板" in label else "中等",
                "line": ln, "msg": f"内部元信息：{label}", "snippet": content[:100],
            })
    return issues


# ---------- P03 他方隐私边界 ----------
@plugin("P03", "他方隐私边界", "是否泄露了非本受众方的私人安排（个人对赌/资金来源/个人资产）")
def p03(text, aud, meta):
    # 「资方」作为独立词才判（避免误伤「出资方式」「出资方」——这正是本工具的由来）
    patterns = [
        (r"(?<![出投])资方", "「资方」提法（易与他方私人安排关联，建议改为「外部投资人」或直接不写）"),
        (r"钱的来源|资金来源|这笔钱从哪来|这笔钱从哪", "他方资金来源"),
        (r"个人层面的对赌|与自己资方|与资方之间的对赌|个人层面的约定", "他方个人层面约定"),
        (r"个人资产|个人信用|个人兜底", "他方个人资产/信用"),
        (r"不并入本计划书|不写进这份计划书|不并入本文件", "「此地无银」式表述（写了「不写」反而暴露其存在）"),
    ]
    issues = []
    for pat, label in patterns:
        for ln, content in _find(text, pat, limit=8):
            issues.append({
                "level": "严重",
                "line": ln, "msg": f"隐私边界：{label}", "snippet": content[:100],
            })
    return issues


# ---------- P04 立场中立性 ----------
@plugin("P04", "立场中立性", "是否单方面偏袒某方（对各方应保持对等表述）")
def p04(text, aud, meta):
    patterns = [
        (r"单方面(偏袒|有利)|偏向.{0,6}(一方|某方)|照顾.{0,4}利益", "疑似偏袒某方"),
        (r"我们要确保.{0,10}拿到最多|最大化我方(利益|收益)", "疑似单方利益最大化"),
    ]
    issues = []
    for pat, label in patterns:
        for ln, content in _find(text, pat, limit=5):
            issues.append({"level": "中等", "line": ln, "msg": f"中立性：{label}", "snippet": content[:100]})
    # 义务对称性：若提到某方的义务，是否也提到对方义务
    if "对赌" in text or "回购" in text:
        if not re.search(r"义务主体|谁来承担|公司层", text):
            issues.append({"level": "中等", "line": 0,
                           "msg": "中立性：出现对赌/回购但未写明义务主体（易被误读为某方个人兜底）", "snippet": ""})
    return issues


# ---------- P05 信息权限分级 ----------
@plugin("P05", "信息权限分级", "该受众是否有权限看到这些细节")
def p05(text, aud, meta):
    issues = []
    for kw in aud.get("敏感词", []):
        for ln, content in _find(text, re.escape(kw), limit=4):
            issues.append({
                "level": "中等" if aud["name"].startswith("公开") else "轻微",
                "line": ln, "msg": f"权限分级：受众「{aud['name']}」不宜看到「{kw}」", "snippet": content[:100],
            })
    # 公开版额外严查
    if aud["name"].startswith("公开"):
        for pat, label in [(r"\d{1,2}%", "具体股权比例"), (r"\d+ ?万元", "具体金额"),
                           (r"橙果|声通", "合作方名称"), (r"授权链|确权", "牌照敏感细节")]:
            for ln, content in _find(text, pat, limit=3):
                issues.append({"level": "严重", "line": ln,
                               "msg": f"公开版不宜含：{label}", "snippet": content[:100]})
    return issues


# ---------- P06 承诺与义务边界 ----------
@plugin("P06", "承诺与义务边界", "是否给出超出该受众应得的承诺/义务")
def p06(text, aud, meta):
    # 排除语境：「保底」若出现在授权/许可/采购/分成等业务语境，不是"给投资人的承诺"
    EXEMPT = re.compile(r"授权|许可|采购|分成|包材|供应|IP |销量|毛利|议价|争取")
    GUARANTEE = re.compile(r"(保证|承诺)[^。]{0,12}(收益|回报|回本|盈利|分红|退出)")
    ABSOLUTE = re.compile(r"(永远不会|绝对不会|100% ?(可靠|安全|成功|保证))")
    BAODI = re.compile(r"保底")
    issues = []
    for ln, content in _find(text, GUARANTEE.pattern, limit=6):
        issues.append({"level": "严重", "line": ln, "msg": "承诺边界：疑似对收益/回报作保证",
                       "snippet": content[:100]})
    for ln, content in _find(text, ABSOLUTE.pattern, limit=6):
        issues.append({"level": "中等", "line": ln, "msg": "承诺边界：绝对化表述",
                       "snippet": content[:100]})
    for ln, content in _find(text, BAODI.pattern, limit=8):
        if EXEMPT.search(content):      # ★ 业务语境豁免
            continue
        issues.append({"level": "严重", "line": ln, "msg": "承诺边界：出现「保底」（若非业务语境的授权/采购，即属对回报作保证）",
                       "snippet": content[:100]})
    return issues


# ---------- P07 风险披露完整性 ----------
@plugin("P07", "风险披露完整性", "该受众关心的风险是否讲全")
def p07(text, aud, meta):
    need = meta.get("required_risks", [])
    issues = []
    for kw, label in need:
        if not re.search(kw, text):
            issues.append({"level": "严重", "line": 0,
                           "msg": f"风险披露缺失：未提及「{label}」", "snippet": ""})
    return issues


# ---------- P08 口径一致性 ----------
@plugin("P08", "口径一致性", "同一事实是否只有一个说法")
def p08(text, aud, meta):
    issues = []
    for a, b, label in meta.get("conflict_pairs", []):
        na, nb = len(re.findall(a, text)), len(re.findall(b, text))
        if na and nb:
            issues.append({"level": "严重", "line": 0,
                           "msg": f"口径冲突：「{a}」({na}次) 与 「{b}」({nb}次) 并存 —— {label}",
                           "snippet": ""})
    return issues


# ---------- P09 数字标注规范 ----------
@plugin("P09", "数字标注规范", "实测/测算/公开数据是否分类标注")
def p09(text, aud, meta):
    issues = []
    nums = re.findall(r"\d[\d,\.]*\s*(?:万元|亿元|万|亿|%|家|人|店)", text)
    marks = len(re.findall(r"实测|测算|公开数据|平台政策口径", text))
    if len(nums) > 30 and marks < 5:
        issues.append({"level": "中等", "line": 0,
                       "msg": f"数字标注偏少：发现 {len(nums)} 处数字，但「实测/测算」标注仅 {marks} 处",
                       "snippet": ""})
    # 要求：出现"测算"必须与"实测"区分
    if "测算" not in text and re.search(r"万元|亿元", text):
        issues.append({"level": "严重", "line": 0,
                       "msg": "含金额但全文未出现「测算」标注（金额未经审计应标测算）", "snippet": ""})
    return issues


# ---------- P10 文本完整性 ----------
@plugin("P10", "文本完整性", "结构层：表格列数/孤立行/破损标记/引用完整性")
def p10(text, aud, meta):
    issues = []
    lines = _lines(text)
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            ncol = lines[i].count("|")
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                if lines[j].count("|") != ncol:
                    issues.append({"level": "轻微", "line": j + 1,
                                   "msg": f"表格列数不齐（表头 {ncol} 条竖线，本行 {lines[j].count('|')} 条）",
                                   "snippet": lines[j].strip()[:100]})
                j += 1
            i = j
        else:
            if re.match(r"^\s*\|", lines[i]) and not lines[i].strip().endswith("|"):
                issues.append({"level": "中等", "line": i + 1,
                               "msg": "表格残缺行（无结尾竖线，渲染会串列）", "snippet": lines[i].strip()[:100]})
            i += 1
    # 破损标记
    # 粗体：同一行内 ** 出现奇数次 → 未闭合
    for i, ln in enumerate(lines):
        if ln.count("**") % 2 == 1:
            issues.append({"level": "轻微", "line": i + 1,
                           "msg": "文本完整性：粗体标记未闭合（** 出现奇数次）",
                           "snippet": ln.strip()[:100]})
    # 表格断裂残留：整行竖线数 > 表头列数×2（真·行合并），而非合法的小计行
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            ncol = lines[i].count("|")
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                if lines[j].count("|") > ncol + 1:
                    issues.append({"level": "中等", "line": j + 1,
                                   "msg": f"文本完整性：疑似表格行合并残留（本行 {lines[j].count('|')} 条竖线，表头仅 {ncol} 条）",
                                   "snippet": lines[j].strip()[:110]})
                j += 1
            i = j
        else:
            i += 1
    return issues


# ---------- P11 载体一致性 ----------
@plugin("P11", "载体一致性", "同一内容的多份载体（md/HTML/单文件）是否口径一致/是否残留已作废口径")
def p11(text, aud, meta):
    """自包含：内置「已作废/应清理」清单，逐条查本载体是否残留。
       另可用 --peers 传入同族载体做交叉比对（词频差异过大即提示）。"""
    OBSOLETE = [
        (r"双层有限合伙", "已作废的旧结构（资方做 LP）"),
        (r"上层\s*GP|上层\s*LP", "已作废的旧结构（上层合伙）"),
        (r"资方\s*LP|LP\s*持下层", "已作废的旧结构（资方 LP）"),
        (r"种子轮融资", "已作废的旧口径（种子轮=融资轮）"),
        (r"投后估值\s*6000|出让\s*15-20%|出让\s*15%-20%", "已作废的旧口径（种子轮估值/出让）"),
        (r"(?<!文件)元信息", "内部格式代号「元信息」"),
        (r"写作纪律|撰写纪律|写作规范|撰写规范", "内部写作规范"),
        (r"写作纪律|撰写纪律", "内部写作规范"),
        (r"BP-?9", "内部格式代号「BP-9」"),
        (r"红杉|F君", "内部模板来源名"),
        (r"`[A-Z][A-Z0-9_\-]{8,}\.(md|json)`", "内部文件名引用"),
        (r"不并入本计划书|不写进这份计划书", "「此地无银」式表述"),
        (r"(?<![出投])资方", "「资方」提法（应与「出资」区分）"),
        (r"财务资方|背后出资方|\(你|（你", "旧结构/非正式人称混用"),
    ]
    issues = []
    for pat, label in OBSOLETE:
        for ln, content in _find(text, pat, limit=3):
            issues.append({"level": "严重", "line": ln,
                           "msg": f"载体残留：{label}", "snippet": content[:110]})
    # 交叉比对（可选）
    peers = meta.get("peers") or []
    for pf, ptext in peers:
        for kw in ["双层有限合伙", "种子轮融资", "写作纪律", "BP-9"]:
            a, b = len(re.findall(kw, text)), len(re.findall(kw, ptext))
            if (a > 0) != (b > 0):
                issues.append({"level": "中等", "line": 0,
                               "msg": f"载体不一致：本载体「{kw}」{a} 次，同族载体 {os.path.basename(pf)} {b} 次",
                               "snippet": ""})
    return issues


# ---------- P12 人称适配 ----------
@plugin("P12", "人称适配", "对外载体是否误用非正式人称（你/我/咱们）")
def p12(text, aud, meta):
    if aud["name"].startswith("内部"):
        return []
    issues = []
    # 排除引号内引用、示例
    # ★ 分两类：
    #   A) 「你」指代公司/创始人 → 违规（应改为 本公司/梁振宇及其实控主体公司）
    #   B) 「你」用于 FAQ 引导语（如"如果你只关心结论"）→ 允许
    FAQ_OK = re.compile(r"(如果|若)你|告诉你|给你看|你可以|你想知道|你只关心|你觉得|你希望|你是否")
    PERSON_AS_COMPANY = re.compile(r"([^\w]|^)你(?=[^\w])")
    for i, ln in enumerate(_lines(text)):
        if not PERSON_AS_COMPANY.search(ln):
            continue
        st = ln.strip()
        if re.search(r'["\'「」]', st) or st.startswith((">", "```")):
            continue
        if FAQ_OK.search(st):        # B 类：FAQ 引导语 → 放行
            continue
        issues.append({"level": "中等", "line": i + 1,
                       "msg": "人称适配：第二人称「你」指代公司/一方（对外应改为「本公司 / 各方 / 梁振宇及其实控主体公司」）",
                       "snippet": st[:100]})
    for ln, content in _find(text, r"咱们|哥们|咱(?![\w])", limit=4):
        issues.append({"level": "中等", "line": ln, "msg": "人称适配：口语人称", "snippet": content[:100]})
    return issues


# ---------- P13 元话语·自我评价（表扬/辩护/自证可信） ----------
@plugin("P13", "元话语·自我评价", "文档在评价自己（诚实/没藏/不美化）或预先反驳质疑——主语是「文档」不是「生意」")
def p13(text, aud, meta):
    PATS = [
        (r"一份可信的(计划书|文件)|价值不在于|诚实地(告诉|说)", "自我表扬：强调文档可信"),
        (r"没有藏|不美化|不回避|没有回避|如实写(出|明)了", "自我表扬：强调没藏风险"),
        (r"我们(把它)?标(出来|注)了|两类数字.{0,6}从不混用|一项都没有说成", "自我表扬：强调标注规范"),
        (r"最想让人记住|最后一句实话|这里必须诚实地说|必须诚实地说一句", "自我表扬：以「诚实」开场"),
        (r"不是方法的失败|方法正常运转|并非失败|不是自欺|怎么知道我们没在自欺", "自我辩护：预先反驳质疑"),
        (r"这是(最|唯一)(需要讲清|重要)的|这正是.{0,14}的原因", "自我辩护：为设计/结论预先辩解"),
        (r"难能可贵|值得?(称道|骄傲)|实事求是地说", "自我表扬"),
    ]
    EXEMPT = re.compile(r"标「实测」|标「测算」|可核验|含义：|前提")
    issues = []
    for pat, label in PATS:
        for ln, content in _find(text, pat, limit=4):
            if EXEMPT.search(content): continue
            issues.append({"level": "中等", "line": ln, "msg": f"元话语（自我评价）：{label}",
                           "snippet": content[:110]})
    return issues


# ---------- P14 元话语·对读者的指令（教人怎么读） ----------
@plugin("P14", "元话语·对读者指令", "文档在指挥读者怎么读（务必/必须说清/请逐字）——是作者视角，不是内容")
def p14(text, aud, meta):
    PATS = [
        (r"务必(先)?看|必须先看|请逐字|请仔细看|不得读错", "指令读者阅读方式"),
        (r"必须(说清|写明|点明|讲清|强调)|需要(特别)?说明的是|要说明的是", "指令读者注意要点"),
        (r"这一(节|条|点)必须|下面(请)?注意|请注意", "指令读者"),
        (r"（必须(先)?讲清）|（这是最需要讲清的）|（必须先看）", "括注式指令"),
    ]
    issues = []
    for pat, label in PATS:
        for ln, content in _find(text, pat, limit=4):
            issues.append({"level": "中等", "line": ln, "msg": f"元话语（对读者指令）：{label}",
                           "snippet": content[:110]})
    return issues


# ---------- P15 元话语·自我指涉（文档谈自己 + 内部口径管理） ----------
@plugin("P15", "元话语·自我指涉", "文档在谈论自己（本计划书/本文/本节）或暴露「内外两套口径」")
def p15(text, aud, meta):
    PATS = [
        (r"本计划书(里|中|不|统一|采用|的主角)", "自我指涉：文档谈自己"),
        (r"本文(里|中)?(从|不|里)", "自我指涉"),
        (r"本节(全部|内容|说明)|这一节(说|讲)|本文件(把|的写法|不)", "自我指涉"),
        (r"以下内容为正式口径|本部分的读者|与对外部分的区别|对内回答|对外回答", "暴露内外两层"),
        (r"内部(融资)?口径|对外文件不写|不写(内部|进).{0,6}来源|内部会议", "内部口径管理（暴露双轨）"),
        (r"为什么要?(写|说)(这次|这).{0,6}(修正|区别|在这里)", "自我指涉：解释写作动机"),
    ]
    # ★ 豁免清单：这些是正当的诚实披露/方法说明，不是元话语
    EXEMPT = re.compile(
        r"没有可靠信源|来源不明|待考证|需补信源|前提|依据|对应|"
        r"标「实测」|标「测算」|可核验|术语表|双方约定|未达标时触发"
    )
    issues = []
    for pat, label in PATS:
        for ln, content in _find(text, pat, limit=4):
            if EXEMPT.search(content):      # 正当披露 → 放行
                continue
            issues.append({"level": "中等", "line": ln, "msg": f"元话语（自我指涉）：{label}",
                           "snippet": content[:110]})
    return issues


# ---------- P16 数字归属清晰性 ----------
# 规则（v1.4 新增）：文中比例 / 成绩 / 数量类的数字，必须能回答四个问题，答不上来标「归属不清」：
#   ① 分母是什么（比例类） ② 分子是什么（比例类）
#   ③ 谁做的（成绩类）—— 是我们做的，还是承接的 / 借用的 / 行业的？
#   ④ 什么时候做的（时效类）
# ★ 严重度固定为「轻微」：这条最容易误报（表格、口径常在邻近行），只作提示，不阻断交付。
P16_PCT = re.compile(
    r"(?<![\d.])(\d[\d,]*(?:\.\d+)?(?:\s*[-–—~至]\s*\d[\d,]*(?:\.\d+)?)?)\s*%")
P16_CN = re.compile(
    r"(?:约|近|超过|逾|不足|至少|最多|达到?)\s*([一二两三四五六七八九十百千零]+)\s*"
    r"(万元|亿元|家|个|人|名|店|万|亿)")
P16_NUM = re.compile(
    r"(?<![\dA-Za-z_.])(\d[\d,]*(?:\.\d+)?)\s*"
    r"(万元|亿元|百分点|万|亿|元|家|个|人|名|店|台|次|单|条|款|倍|户|份|场|笔)")

# 归属标注词（任一命中即视为该问题「答得上来」）
# ★ 分母只认**显式**标注（分母/口径/样本/全量…）或动词式「占 34%」；
#   「占比 34%」「市场占有率 34%」不算答上——它没说基数是什么。
P16_DENOM = re.compile(
    r"分母|口径|样本|基数|基准|全量|总[数单量额]|合计|平均|覆盖|抽样|对照|相比|同比|环比|"
    r"较去年|较上年|其中|占\s*\d|占[^\u4e00-\u9fff]")
P16_SOURCE = re.compile(
    r"来源|依据|据[^\w]|实测|测算|估算|预估|预算|公开数据|平台|后台|系统导出|台账|报表|调研|"
    r"报告|客户(提供|反馈)|内部数据|自报|导出|统计|性质|标注|注明|引用|引自|审计|"
    r"未审计|待核对|待考证|待确认|未核实|无法核实|存疑|暂估|口径未知|来源不明")
P16_WHO = re.compile(
    r"我方|我们|本[公店司团]|公司|企业|集团|商家|团队|门店|客户|顾客|平台|供应商|合作方|"
    r"总部|第三方|行业|竞品|对手|承接|借用|引用|自营|加盟|直营|"
    r"由[^，。；]{0,8}(提供|统计|测算|核算|执行|完成)")
# 比例前的计数（如「95 个待回复会话 100% 超时」——「95 个」就是分母）
P16_COUNT_BASE = re.compile(r"\d[\d,\.]*\s*(?:个|家|人|名|单|次|份|笔|台|户|条|店|万单|单)")
# 同一行里出现「分母：/来源：/口径：」这类**显式标注** → 视为作者已在标注归属，本行不再判
P16_EXPLICIT = re.compile(
    r"(分母|分子|来源|数据来源|口径|依据|时点|样本量|统计口径)\s*[:：]")
P16_WHEN = re.compile(
    r"截至|截止|时点|当期|期末|本月|当月|上月|去年|今年|同比|环比|累计|至今|以来|实时|"
    r"期间|季度|年度|近\s*\d|近[一二三四五六七八九十]|Q\s*[1-4]|[1-4]\s*季度|"
    r"\d{4}\s*年|\d{1,2}\s*月|\d{1,2}\s*日|(?<![\d])(?:19|20)\d{2}(?![\d])")
P16_ACHIEVE = re.compile(
    r"增长|提升|下降|增速|达成|完成|排名|领先|第一|冠军|翻倍|突破|超越|扭亏|盈利|降幅")
# 表格行标签含这些字 → 该行数字按「比例」审（同一列的裸数字也算比例）
P16_RATIO_LABEL = re.compile(r"率|占比|比例|增速|增长|降幅|损耗|转化|渗透")


def _p16_units(lines):
    """切审查单元：连续非空行算一个块（整张表格算一块），块外前后各带 1 行作为邻近上下文"""
    blocks = []
    i = 0
    while i < len(lines):
        if lines[i].strip():
            j = i
            while j < len(lines) and lines[j].strip():
                j += 1
            blocks.append((i, j - 1))
            i = j
        else:
            i += 1
    unit_of = {}
    for a, b in blocks:
        ctx = "\n".join(lines[max(0, a - 1):min(len(lines), b + 2)])
        for k in range(a, b + 1):
            unit_of[k] = ctx
    return unit_of


def _p16_tokens(ln, s):
    """抽出本行需要审的数字：[(显示文本, 类别 ratio|num, 类别名, 本行偏移)]"""
    toks = []
    for m in P16_PCT.finditer(ln):
        toks.append((m.group(1).strip() + "%", "ratio", "比例", m.start()))
    for m in P16_CN.finditer(ln):
        toks.append(("约" + m.group(1) + m.group(2), "num", "数量/金额", m.start()))
    for m in P16_NUM.finditer(ln):
        pre = ln[max(0, m.start() - 2):m.start()]
        if "第" in pre:                       # 「第 3 条 / 第 5 款」是结构编号，不是数据
            continue
        toks.append((m.group(1) + " " + m.group(2), "num", "数量/金额", m.start()))
    if s.startswith("|"):                     # 表格：行标签含「率/占比/…」时，裸数字按比例审
        cells = [c.strip() for c in s.strip().strip("|").split("|")]
        if cells and P16_RATIO_LABEL.search(cells[0]):
            for c in cells[1:]:
                if re.match(r"^-?\d[\d,]*(?:\.\d+)?$", c):
                    off = ln.find(c)
                    toks.append((c + "（%s）" % cells[0].strip(), "ratio", "比例",
                                 off if off >= 0 else 0))
    return toks


def _p16_base_before(ln, pos):
    """比例前若已出现「95 个 / 1180 家 / 12 万单」这类**计数**，该计数就是分母 → 分母算答得上来"""
    return bool(P16_COUNT_BASE.search(ln[:pos]))


@plugin("P16", "数字归属清晰性", "比例/成绩/数量类数字能否答上「分母·分子·谁做的·何时做的」四个问题")
def p16(text, aud, meta):
    lines = _lines(text)
    unit_of = _p16_units(lines)
    per_line = OrderedDict()
    dim_count = {"分母": 0, "来源/口径": 0, "来源": 0, "时点": 0, "谁做的": 0}
    in_fence = False
    max_lines = 12
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not s:
            continue
        if re.match(r"^\|[\s:|-]+$", s):        # 表格分隔行
            continue
        if re.search(r"https?://", s):          # 含链接的行（数字多是 URL 的一部分）
            continue
        if re.match(r"^\s*#{1,6}\s*\d+[\.、\)]?\s*$", s):   # 纯编号标题
            continue
        if P16_EXPLICIT.search(s):      # 本行已显式标注分母/来源/口径 → 放行
            continue
        unit = unit_of.get(i, s)
        for raw, kind, kindlabel, off in _p16_tokens(ln, s):
            need = []
            if kind == "ratio":
                if not P16_DENOM.search(unit) and not _p16_base_before(ln, off):
                    need.append("分母")
            else:
                if not P16_SOURCE.search(unit):
                    need.append("来源")
                if not P16_WHEN.search(unit):
                    need.append("时点")
            if P16_ACHIEVE.search(unit):        # 成绩类（增长/达成/排名…）才要求答「谁做的」
                if not P16_WHO.search(unit):
                    need.append("谁做的")
            if need:
                per_line.setdefault(i + 1, []).append((raw, kindlabel, need))
                for d in need:
                    dim_count[d] = dim_count.get(d, 0) + 1

    issues = []
    for lnno, items in list(per_line.items())[:max_lines]:
        shown = "；".join(
            "%s「%s」缺 %s" % (k, raw, "、".join("「%s」" % d for d in need))
            for raw, k, need in items[:3])
        extra = "（本行另有 %d 处未列）" % (len(items) - 3) if len(items) > 3 else ""
        issues.append({
            "level": "轻微", "line": lnno,
            "msg": "⚠️ 归属不清：" + shown + extra + "（四个问题：分母/分子/谁做的/什么时候做的）",
            "snippet": lines[lnno - 1].strip()[:110],
        })
    if len(per_line) > max_lines:
        issues.append({"level": "轻微", "line": 0,
                       "msg": "归属不清：另有 %d 行数字未逐行列示（只报了前 %d 行）"
                              % (len(per_line) - max_lines, max_lines), "snippet": ""})
    if len(per_line) >= 3:      # 全文级提示：本项误报率较高，给出缺项分布便于人工判断
        hist = " / ".join("%s %d 处" % (k, v) for k, v in
                          sorted(dim_count.items(), key=lambda kv: -kv[1]) if v)
        issues.append({"level": "轻微", "line": 0,
                       "msg": "归属不清汇总：%d 行数字存在归属缺失（%s）——本项为提示性质，需人工判断"
                              % (len(per_line), hist), "snippet": ""})
    return issues


# ============================================================
# 三、受众档案：各受众的"必知风险"
# ============================================================
REQUIRED_RISKS = {
    "shareholder": [
        (r"未注册|尚未注册", "公司注册状态"),
        (r"测算", "金额为测算而非已验证"),
        (r"授权|确权", "牌照/资源的授权链风险"),
        (r"待各方协议确认|待确认", "条款尚待协议确认"),
    ],
    "investor": [
        (r"测算", "金额为测算"),
        (r"风险", "风险披露"),
        (r"未注册|尚未注册", "公司注册状态"),
    ],
    "partner": [(r"待各方协议确认|待确认", "条款待确认")],
    "internal": [],
    "public": [(r"测算|预估|以实际为准", "数据免责说明")],
}

CONFLICT_PAIRS = [
    (r"股东出资", r"种子轮融资", "1000 万的性质（股东出资 ≠ 融资轮）"),
    (r"51%", r"双层有限合伙", "控制权实现方式"),
    (r"只对橙果", r"对各股东均设对赌", "对赌范围"),
]

TERMS = ["即时零售", "平台服务商", "GMV", "抽成", "数据底座", "FDE", "对赌",
         "清单式否决", "AB 股", "作价", "PS", "PE", "授权链"]


# ============================================================
# 四、主流程
# ============================================================
def read_text(path):
    """读文件；HTML 先剥标签转纯文本"""
    raw = open(path, encoding="utf-8").read()
    if path.lower().endswith((".html", ".htm")):
        t = re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=re.S | re.I)
        t = re.sub(r"<style[^>]*>.*?</style>", " ", t, flags=re.S | re.I)
        t = re.sub(r"<[^>]+>", "\n", t)          # 标签→换行
        t = t.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
        t = re.sub(r"\n{3,}", "\n\n", t)
        return t.strip()
    return raw


def audit(path, aud_key):
    aud = AUDIENCES[aud_key]
    text = read_text(path)
    meta = {
        "terms": TERMS,
        "required_risks": REQUIRED_RISKS.get(aud_key, []),
        "conflict_pairs": CONFLICT_PAIRS,
    }
    results = []
    for p in PLUGINS:
        if p["applies"] != "all" and aud_key not in p["applies"]:
            continue
        try:
            issues = p["fn"](text, aud, meta) or []
        except Exception as e:
            issues = [{"level": "工具错误", "line": 0, "msg": f"{p['id']} 执行异常: {e}", "snippet": ""}]
        results.append({"id": p["id"], "name": p["name"], "issues": issues})
    return {"file": os.path.basename(path), "audience": aud_key,
            "audience_name": aud["name"], "results": results}


def render(report, verbose=True):
    total = sum(len(r["issues"]) for r in report["results"])
    severe = sum(1 for r in report["results"] for i in r["issues"] if i["level"] == "严重")
    print(f"\n{'='*76}")
    print(f"  文件：{report['file']}    受众：{report['audience_name']}")
    print(f"{'='*76}")
    if total == 0:
        print("  ✅ %d 项标准全部通过" % len(report["results"]))
        return
    print(f"  共 {total} 项问题（严重 {severe}）\n")
    for r in report["results"]:
        if not r["issues"]:
            if verbose:
                print(f"  ✅ {r['id']} {r['name']}")
            continue
        print(f"  ❌ {r['id']} {r['name']}  （{len(r['issues'])} 项）")
        for i in r["issues"]:
            loc = f"L{i['line']}" if i["line"] else "全文"
            print(f"       [{i['level']}] {loc} {i['msg']}")
            if i["snippet"]:
                print(f"                 └ {i['snippet']}")


def main():
    ap = argparse.ArgumentParser(description="立场排查器 · Stance Auditor v1.4（16 项标准）")
    ap.add_argument("files", nargs="*", help="待审文件")
    ap.add_argument("--audience", "-a", default="shareholder",
                    help="受众：" + " / ".join(AUDIENCES.keys()) + " / all")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--list", action="store_true", help="列出 16 项标准与受众档案")
    ap.add_argument("--peers", nargs="*", default=None, help="同族载体（用于 P11 交叉比对）")
    args = ap.parse_args()

    if args.list:
        print("【%d 项标准 · 插件】" % len(PLUGINS))
        for p in PLUGINS:
            print(f"  {p['id']}  {p['name']:<12} {p['desc']}")
        print("\n【受众档案】")
        for k, v in AUDIENCES.items():
            print(f"  {k:<12} {v['name']}")
            print(f"              该看到：{v['sees']}")
            print(f"              不该看：{v['not_sees']}")
        return

    if not args.files:
        ap.print_help(); return

    keys = list(AUDIENCES.keys()) if args.audience == "all" else [args.audience]
    all_rep = []
    for f in args.files:
        if not os.path.exists(f):
            print(f"⚠️ 不存在: {f}"); continue
        for k in keys:
            rep = audit(f, k)
            all_rep.append(rep)
            if not args.json:
                render(rep)
    if args.json:
        print(json.dumps(all_rep, ensure_ascii=False, indent=1))
    else:
        tot = sum(len(i["issues"]) for r in all_rep for i in r["results"])
        print(f"\n{'='*76}\n  合计：{len(all_rep)} 份报告 / {tot} 项问题\n{'='*76}")


if __name__ == "__main__":
    main()
