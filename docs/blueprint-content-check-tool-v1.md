# 蓝图空呈现检查修复器 bb-blueprint-content-check.py v1(R006 合规)

> 作者: 明鉴 v2 · 2026-09-05 · 用户提出(刚修完 svg 空框架, 要求工具化防复发)
> 问题类型: 蓝图详情/图谱呈现为空(或只框架), 因数据层字段契约不匹配/数据缺失:
> - 子蓝图 stages 无 mainline 字段 → svg 空壳(已修生成器)
> - 蓝图数据缺 stages/works → 真无内容
> - svg 元素全深色/文字稀疏 → 视觉空

## 一、检查维度(每蓝图跑)
| # | 检查 | 判定空 |
|---|------|--------|
| C1 | mainlines 存在且有值 | 无 mainline 或无 name |
| C2 | stages 存在且每 stage 有 mainline 或(子蓝图)有内容 | stages 空 |
| C3 | works 有内容 | works 空(可接受) |
| C4 | svg 渲染: 文本行数/子阶段数/内容字符 | svg 文字 <10 或 无子阶段+仅主线名 |
| C5 | svg 字段契约: stages 缺 mainline(子蓝图允许, 记录提示) | 契约断裂 |

## 二、修复器(幂等)
- R1 缺 mainline 的 stages → 生成器已柔性归属(无需改数据)
- R2 数据缺 stages/works → 从蓝图 md 文档提取(扫描 *-master.md mainlines 主线/stage 行) 建议补
- R3 视觉空 svg → 标 degraded, 提示补数据或生成器兜底

## 三、R006 九标准
| # | 实现 |
|---|------|
| 1 | 独立 bb-blueprint-content-check.py |
| 2 | --selfcheck |
| 3 | 黑板可配, 降级本地 |
| 4 | --tool-version |
| 5 | 本文档 |
| 6 | 版本台账 |
| 7 | 报告输出文件 |
| 8 | 结果写黑板 data/audit/blueprint-content/ |
| 9 | --scan/--check-all/--fix/--json |

## 四、CLI
```
python3 bb-blueprint-content-check.py --scan            全部蓝图检查(健康度表)
python3 bb-blueprint-content-check.py --check <bp>      单蓝图
python3 bb-blueprint-content-check.py --fix <bp>        尝试修复(从 md 提 stages)
python3 bb-blueprint-content-check.py --selfcheck       TCC
python3 bb-blueprint-content-check.py --json            结构化
```

## 五、验收
| # | 标准 |
|---|------|
| A1 | 15 蓝图全检查, 输出健康/空/退化分类 |
| A2 | 空判定准确(website 修复前空→后健康能区分) |
| A3 | --fix 对可修数据(有 md 源)能补 stages |
| A4 | --selfcheck / --tool-version |
| A5 | 结果落黑板可追溯 |
