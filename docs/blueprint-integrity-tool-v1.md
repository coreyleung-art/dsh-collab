# 蓝图完整度检查器 bb-blueprint-integrity.py v1.0(R006 九标准)

## 用途
按 BP-9 九字段契约 + 关系 + 可渲染性给蓝图完整度评分(0-100), 定位数据缺口。

## 维度(加权)
identity 10 · mainlines 18 · stages 20 · works 12 · gate 12 · status 6 · relations 10 · render 8 · ts 4

## R006
1 独立脚本 · 2 --selfcheck · 3 黑板/服务可配 · 4 --tool-version · 5 本文档 · 6 版本台账
7 --report 生成 md · 8 结果落黑板(由调用方) · 9 --scan/--check/--report/--regress/--json

## 用法
python3 bb-blueprint-integrity.py --scan           # 全扫评分
python3 bb-blueprint-integrity.py --check mtm      # 单蓝图+缺失维度
python3 bb-blueprint-integrity.py --report         # 生成完整度报告 md
python3 bb-blueprint-integrity.py --regress 60     # 低于60列出

## 配套
- bb-blueprint-content-check.py: 空呈现检查(数据能否渲染)
- 建议纳入发布前检查(与 bb-gallery-gate 并列)
