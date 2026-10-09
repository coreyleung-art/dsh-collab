#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成招商版 PPT（嘉腾版）——基于内容大纲 招商PPT内容大纲-嘉腾版.md

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
纯 python-pptx，无图片依赖。莫兰迪配色：粉/白/绿。"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== gen-zhaoshang-ppt 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 生成招商版 PPT（嘉腾版）——基于内容大纲 招商PPT内容大纲-嘉腾版.md")
    print("  · ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。")
    print("  · 依据：r006-debt-assess.py 机械扫描未检出以下原语：")
    print("  · os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: os, time")
    print("  · ★ 第三方: pptx ⇒ 缺失时行为须明确（拒绝或降级），不得抛栈")
    print("  · 固定日志: ~/dsh-collab/logs/gen-zhaoshang-ppt.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

# 莫兰迪配色
import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/gen-zhaoshang-ppt.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

PINK = RGBColor(0xD8, 0xA7, 0x9A)    # 莫兰迪粉
DEEP = RGBColor(0x6B, 0x4F, 0x4A)    # 深棕粉（标题）
GREEN = RGBColor(0x8A, 0x9A, 0x7B)   # 莫兰迪绿
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT = RGBColor(0xF7, 0xF1, 0xEA)   # 米白底
GRAY = RGBColor(0x6B, 0x6B, 0x6B)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]

def add_slide(title, subtitle=None):
    slide = prs.slides.add_slide(BLANK)
    # 背景
    bg = slide.shapes.add_shape(1, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = LIGHT
    bg.line.fill.background()
    # 标题条
    bar = slide.shapes.add_shape(1, 0, 0, prs.slide_width, Inches(1.0))
    bar.fill.solid()
    bar.fill.fore_color.rgb = DEEP
    bar.line.fill.background()
    tf = bar.text_frame
    tf.margin_left = Inches(0.5)
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = WHITE
    if subtitle:
        p2 = tf.add_paragraph()
        p2.text = subtitle
        p2.font.size = Pt(14)
        p2.font.color.rgb = PINK
    return slide

def add_body(slide, items, top=1.3, left=0.7, width=12.0, height=5.8, size=16):
    """items: list of (text, level, bold)"""
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame
    tf.word_wrap = True
    first = True
    for text, level, bold in items:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.text = text
        p.level = level
        p.font.size = Pt(size - level * 2)
        p.font.bold = bold
        p.font.color.rgb = DEEP if bold else GRAY
        p.space_after = Pt(8)

def add_table(slide, headers, rows, top=1.4, left=0.7, width=12.0, height=None):
    n_rows = len(rows) + 1
    n_cols = len(headers)
    h = height or Inches(0.5 * n_rows + 0.3)
    table_shape = slide.shapes.add_table(n_rows, n_cols, Inches(left), Inches(top), Inches(width), h)
    table = table_shape.table
    # 表头
    for j, hd in enumerate(headers):
        cell = table.cell(0, j)
        cell.text = hd
        cell.text_frame.paragraphs[0].font.bold = True
        cell.text_frame.paragraphs[0].font.size = Pt(14)
        cell.text_frame.paragraphs[0].font.color.rgb = WHITE
        cell.fill.solid()
        cell.fill.fore_color.rgb = GREEN
    # 数据行
    for i, row in enumerate(rows, start=1):
        for j, val in enumerate(row):
            cell = table.cell(i, j)
            cell.text = str(val)
            cell.text_frame.paragraphs[0].font.size = Pt(13)
            cell.text_frame.paragraphs[0].font.color.rgb = DEEP
            if i % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor(0xEF, 0xE6, 0xDD)
    return table

# ── P1 封面 ──
s = add_slide("初蘅 · 鲜花品类「双霸权」供应链重构者")
add_body(s, [
    ("与嘉腾的招商合作方案", 0, False),
    ("", 0, False),
    ("「守护初心，映现生机」——卖「表达」，不卖花", 0, True),
    ("2026-08-26 · 初蘅品牌", 0, False),
], top=2.5)

# ── P2 一句话认知 ──
s = add_slide("一句话认知", "30 秒版")
add_body(s, [
    ("不是一家花店连锁——是解决「42 万家夫妻店一个人做 8 件事活不下去」的答案", 0, True),
    ("", 0, False),
    ("蜜雪有供应链霸权，麦当劳有运营霸权，初蘅做鲜花品类的双霸权", 0, True),
    ("", 0, False),
    ("核心数字：鲜花零售 2200 亿 / 连锁化率 <5% / 42 万家店 26% 在死", 1, False),
], top=2.0)

# ── P3 三叠窗口 ──
s = add_slide("三叠窗口", "为什么是现在")
add_table(s, ["窗口", "内容", "数据"], [
    ("天时", "AI 成熟——第一次能标准化鲜花", "视觉 99.75% / 预测 98% / 减损 30-50%"),
    ("地利", "即时零售爆发", "闪购鲜花 +15.7% / 七夕 2700 万单"),
    ("人和", "42 万家夫妻店存量整合", "26% 在死 / 60% 业务量下降"),
    ("结构", "连锁化率对比", "鲜花 <5% vs 茶饮 49%"),
])

# ── P4 供应链霸权 ──
s = add_slide("供应链霸权", "蜜雪式变体")
add_body(s, [
    ("四级采购 + 冷链 + 期货锁价", 0, True),
    ("→ 损耗 30%+ 压到 10% = 利润", 1, False),
    ("", 0, False),
    ("供应链差价 8-22%", 0, True),
    ("对标：蜜雪 97.6% 收入来自供货，加盟费仅 2.4%", 1, False),
    ("", 0, False),
    ("「谁解决损耗谁赢——损耗是生死线也是壁垒」", 0, True),
])

# ── P5 运营霸权 ──
s = add_slide("运营霸权", "麦当劳式 AI 版")
add_body(s, [
    ("8787 面板：10 店实时数据", 0, True),
    ("通岗 SOP（3-5 天上岗）+ 期货 SOP", 1, False),
    ("", 0, False),
    ("视觉模型 flower-yolo 99.75% + 传感器 + AI 运营助手", 0, True),
    ("", 0, False),
    ("任何人按系统都能开出一致的好花店", 0, True),
])

# ── P6 双霸权飞轮 ──
s = add_slide("双霸权协同飞轮")
add_body(s, [
    ("供应链霸权（成本低）→ 运营霸权（效率高）→ 数据飞轮（模型更准）", 0, True),
    ("→ 损耗更低 → 成本更低 → 门店更赚 → 更多门店", 0, True),
    ("", 0, False),
    ("飞轮自我强化：每多一家店，数据更多，模型更准，成本更低", 1, False),
], top=2.2)

# ── P7 品牌线 ──
s = add_slide("品牌线", "情感资产")
add_body(s, [
    ("「守护初心，映现生机」——卖「表达」不卖花", 0, True),
    ("", 0, False),
    ("四大产品线：初见 / 蘅长 / 伴旅 / 守白", 0, True),
    ("IP 联名溢价 80%", 1, False),
])

# ── P8 运营线 ──
s = add_slide("运营线", "效率引擎")
add_body(s, [
    ("AI + 双蓝图替夫妻店做 8 件专业事", 0, True),
    ("（采购/制作/上架/客服/营销/售后/财务/损耗）", 1, False),
    ("", 0, False),
    ("蓝图时间表：2027 AI 运营助手 → 2028 单店复制 → 2029-30 自动化工厂", 0, True),
    ("", 0, False),
    ("自家数据：天河 5 月营收 13.7 万 / 净利 15K", 1, False),
    ("七夕 2026-08-19：4 店 ¥76,895（自运营 3 个月打出）", 1, True),
    ("完整年轮：去年七夕零单（代运营）→ 今年 ¥76,895（自运营）", 1, True),
])

# ── P9 供应链线 ──
s = add_slide("供应链线", "成本护城河")
add_body(s, [
    ("四级采购 + 冷链 + 期货锁价", 0, True),
    ("", 0, False),
    ("实证：佛山签约店 10 万投资 / 80% 权益（2026-06 落地）", 0, True),
])

# ── P10 三层合作框架 ⭐核心 ──
s = add_slide("三层合作框架", "与嘉腾 · 核心")
add_body(s, [
    ("上层：区域代理网络（嘉腾牵头区域招商）", 0, True),
    ("中层：招商服务（嘉腾做招商服务商，不直接签二级）", 0, True),
    ("下层：门店投资人（投资人直接签初蘅）", 0, True),
    ("", 0, False),
    ("⭐ 「二级直接签初蘅，嘉腾转渠道服务商」——保护双方", 0, True),
], top=1.8)

# ── P11 合规保护 ──
s = add_slide("为什么这样设计", "合规保护")
add_body(s, [
    ("传销红线：30 人 + 3 级 + 拉人头 = 刑事风险", 0, True),
    ("健康模式 = 赚供应链钱，不赚人头费", 0, True),
    ("", 0, False),
    ("话术：这是保护嘉腾，不是限制嘉腾", 0, True),
], top=2.0)

# ── P12 嘉腾收益算账 ⭐ ──
s = add_slide("嘉腾的收益算账", "谈判筹码")
add_table(s, ["收入项", "基准", "弹性"], [
    ("招商佣金", "授权费 30%（促成+首批进货结算）", "20-40%"),
    ("区域抽成", "辖区流水 0.4%", "0.3-0.5%"),
    ("首期试点", "广州/佛山 3-5 家", "可谈"),
    ("模拟测算", "年收益 3.2 万 → 17.6 万", "随开店数增长"),
])

# ── P13 单店模型 ──
s = add_slide("单店模型", "投资人视角")
add_table(s, ["参数", "基准", "弹性"], [
    ("门店分级", "社区 10 万 / 标准 15 万 / 旗舰 20 万（带冷库）", "按店型"),
    ("品牌授权费", "3-5 万/店（一次性）", "按区域"),
    ("运营服务费", "月净利 30%（盈利 6 月起收）", "可谈"),
    ("参投分红", "品牌占股 20-30% 不控股", "按出资"),
])

# ── P14 区域合伙人参数 ──
s = add_slide("区域合伙人参数", "嘉腾视角")
add_table(s, ["参数", "基准", "弹性"], [
    ("招商佣金", "授权费 30%", "20-40%"),
    ("区域抽成", "辖区流水 0.4%", "0.3-0.5%"),
    ("考核", "年开店数 + 12 月存活率 ≥85%", "按区域"),
])

# ── P15 合规红线 ──
s = add_slide("合规红线", "无商量")
add_body(s, [
    ("❌ 不做回购/保本承诺（欺诈+非法集资+广告法三重风险）", 0, True),
    ("❌ 二级不经手资格费（直接签初蘅，防传销）", 0, True),
    ("❌ 不承诺收益/回本（话术统一管控）", 0, True),
    ("", 0, False),
    ("✅ 替代安全感：真实数据 + 区域保护 + 退出机制", 0, True),
], top=1.8)

# ── P16 资本化双路径 ──
s = add_slide("资本化双路径")
add_table(s, ["路径", "逻辑", "时间"], [
    ("A 独立上市", "蜜雪式供应链 + 遇见小面式标准化", "5-8 年"),
    ("B 被整合", "做厚供应链/密度/数据/会员", "2027-28 窗口"),
    ("估值坐标", "0.3-0.5x PS", "对齐朴朴 0.36x"),
])

# ── P17 源文件弹药 ⭐ ──
s = add_slide("源文件弹药", "港交所可复验")
add_body(s, [
    ("蜜雪 2025 年报：收入 335.6 亿 / 净利 59.27 亿 / 59,823 店", 0, True),
    ("加盟费仅 2.4% / 闭店率 4.2%——供应链收入是主引擎", 1, False),
    ("", 0, False),
    ("遇见小面 2026 中期：同店 -4.2% / 客单价 31.3→27.7", 0, True),
    ("以价换量铁证——标准化才能守住定价", 1, False),
    ("", 0, False),
    ("源文件 PDF 在 ipofiles/ 可现场展示", 1, False),
])

# ── P18 蜜雪供应链叙事 ──
s = add_slide("为什么这个模式能成")
add_body(s, [
    ("蜜雪 97.6% 收入来自供货，加盟费仅 2.4%", 0, True),
    ("初蘅对标：供应链差价 8-22% = 可持续收入", 0, True),
    ("", 0, False),
    ("「加盟商赚到钱，品牌才赚到钱」的飞轮", 0, True),
], top=2.0)

# ── P19 蓝图时间表 ──
s = add_slide("蓝图时间表", "兑现路径")
add_table(s, ["时间", "里程碑", "状态"], [
    ("今天", "8787/通岗/冷链/期货 SOP/视觉 99.75%", "✅ 已兑现"),
    ("2026 H2", "外卖→ERP 打通/数据聚合", "🎯 目标"),
    ("2027", "AI 运营助手上线/传感器铺开", "🎯 目标"),
    ("2028", "无人值守单环节/单店复制", "🎯 目标"),
    ("2029-30", "自动化工厂（融资触发）", "🔭 条件"),
])

# ── P20 蓝图愿景 40% 兑现 ──
s = add_slide("蓝图愿景 40% 已兑现")
add_body(s, [
    ("五重优势：数据透明 / 标准化 / 损耗 / AI / 供应链", 0, True),
    ("", 0, False),
    ("「合伙人加入的不是花店，是智能网络节点」", 0, True),
], top=2.0)

# ── P21 行动号召 ──
s = add_slide("行动号召")
add_body(s, [
    ("首期试点：广州/佛山 3-5 家（双方确认区域）", 0, True),
    ("下一步：授权费分佣比例最终确认 → 试点落地 → 下次会议定框架", 0, True),
    ("双周一例会机制", 0, True),
], top=2.0)

# ── P22 结束 ──
s = add_slide("初蘅 = 鲜花品类的双霸权重构者")
add_body(s, [
    ("守护初心，映现生机", 0, True),
    ("", 0, False),
    ("感谢聆听 · 期待与嘉腾共创", 0, False),
    ("", 0, False),
    ("2026-08-26", 0, False),
], top=2.5)

OUT = "/Users/coreyleung/dsh-collab/research/zhaoshang-ppt-2026-08-25/初蘅招商合作方案-嘉腾版.pptx"
prs.save(OUT)
print(f"PPT 已生成: {OUT}")
print(f"页数: {len(prs.slides.__iter__.__self__._sldIdLst)}")
