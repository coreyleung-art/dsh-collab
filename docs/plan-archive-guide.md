# 📋 计划档案 · 收录规范与使用指南

> 作者: 明鉴 v2 · 2026-09-03 · 配套: bb-plan-scanner.py + gallery 📋计划档案 Tab
> 目标: 把所有智能体的计划性文件(md)与版本档案统一汇入系统架构管理器, 建关系图谱

## 一、收录范围(自动)
| 源 | 目录/模式 | 识别为 |
|----|----------|--------|
| 计划/规划 | ~/meituan-multi/docs/、~/dsh-collab/docs/ 中 *plan*/计划/迭代 类 md | plan |
| 路线图 | **/ROADMAP.md(如 laodeng-h5) | roadmap |
| 蓝图版本 | ~/dsh-collab/data/blueprint/<id>/blueprint-*.md | blueprint |
| 变更日志 | **/CHANGELOG.md | changelog |
| 版本声明 | **/version.json · VERSION · VERSIONING.md · VERSIONS.txt · VERSION-MANIFEST.md | version |
| 系统台账 | ~/system-graph-app/ 台账 | version |
| 两端考古 | i9/MBP 回报(data/asset-inventory/<端>/plan-archive/ 或 notes/<node>/) | plan |

## 二、扫描命令
```bash
python3 ~/dsh-collab/scripts/bb-plan-scanner.py --scan       # 全量重扫 → plan-archive.json
python3 ~/dsh-collab/scripts/bb-plan-scanner.py --list       # 打印汇总
python3 ~/dsh-collab/scripts/bb-plan-scanner.py --selfcheck  # 校验(重复id)
```
- 幂等可复跑; 建议每次发布/归档后跑 --scan 保持档案新鲜
- 产物: `~/dsh-collab/data/blueprint/gallery/plan-archive.json`(管理器 📋Tab 数据源)

## 三、新增计划文件的规范(供各智能体)
1. 计划文件放各域既有目录(meituan docs/plans、dsh-collab docs、蓝图目录)
2. 命名含 **plan/roadmap/迭代/backlog** 关键字(便于类型识别) 或标题行写「计划: xxx」
3. 标题首行写完整(扫描器取首行作 title); 版本类文件内标注版本(vX.Y.Z)
4. 关联蓝图: 路径/文件名含蓝图 id(flowernet/mtm/…)或文档内写 blueprint:<id>
5. 跑一次 `bb-plan-scanner.py --scan` → 管理器 📋Tab 自动出现

## 四、图谱关系(管理器内)
- **域**(大圆: 老登/MTM · 老登App · 明鉴/SystemGraph · 协作文档 · 蓝图 · 工具链 · ERP…) 
- **条目**(中圆: 各计划/版本文件, 按类型配色: 绿plan/黄roadmap/蓝blueprint/紫changelog/青version)
- **蓝图**(蓝边: 条目 ↔ 关联蓝图)
- 点击条目 → 浮层卡(标题/类型/域/版本/路径/关联蓝图/更新时间)
- 表格可按类型/域/蓝图查看; 蓝图链接可跳蓝图详情

## 五、两端考古(i9/MBP)
- 邀请: notes/session-f38244df/cross-end-plan-archive-invite(经星桥 R031 分投)
- i9 → data/asset-inventory/i9/plan-archive/; MBP → notes/mbp/plan-archive-reply
- 回报格式: {domain, title, type(plan|roadmap|backlog|version|changelog), file/location, version, status, desc}
- 回报并入 = 写入扫描器可发现的路径或直接 merge 进 plan-archive.json(加 node 字段标注来源端)

## 六、验收(对应迭代需求)
| # | 标准 | 验证 |
|---|------|------|
| A1 | 导览首页大卡片(15 Tab 可点直达) | 截图 ✅ |
| A2 | #<tab> 深链直达 + 对话「打开XX」 | hash 测试 ✅ |
| A3 | plan-archive.json 覆盖本地计划+版本 | 57 项 ✅ |
| A4 | 📋Tab: 汇总表+图谱 | DOM 57 行 ✅ |
| A5 | 图谱点条目看详情/跳蓝图 | clickHandler ✅ |
| A6 | 扫描器幂等可复跑 | 多次 --scan 稳定 ✅ |
