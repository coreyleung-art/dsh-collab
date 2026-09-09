# 迭代需求 · 系统架构管理器「导览 + 计划档案图谱」 v1

> 作者: 明鉴 v2 · 2026-09-03 · 状态: 规划中(用户定案范围)
> 背景: 用户要求 ①以后可直接拉起管理器并定位到具体页面 ②把管理器内所有智能体的计划性文件 md + 版本汇总建关系图谱

## 一、需求拆解(用户拍板)

### R1 拉起与定位(两者都要)
- **R1a 导览首页**: 管理器首页做成全 Tab 大卡片导览(点卡片即定位到该 Tab)
- **R1b 对话直达链接**: 对话里提供 `#<tab>` 直达链接; 支持用户说「打开通讯桥/看蓝图库」就拉起对应页
- 现状: 已有 #hardware-comm 深链 + switchTab; 需补全所有 Tab 深链 + 首页导览卡片

### R2 计划档案汇总 + 关系图谱(全量)
把所有智能体的计划性文件与版本汇聚进管理器, 建立统一档案与关系图谱:
- **采集范围**: 
  - 计划性 md: ~/meituan-multi/docs/plans/、~/meituan-multi/docs/*plan*.md、~/meituan-multi/laodeng-h5/ROADMAP.md、~/dsh-collab/docs/*.md(计划类)、各项目 ROADMAP/plan
  - 版本文件: CHANGELOG.md / VERSION / VERSIONING.md / version.json / version-map.json(蓝图版)
  - 蓝图库: data/blueprint/<id>/ 各版本 md
  - **两端考古(用户追加)**: i9(PC)/MBP 两侧计划性文件 + 版本档案 —— 经 R031 黑板通道邀请两端本地智能体自陈(见 notes/session-f38244df/cross-end-plan-archive-invite), 回报并入 plan-archive
- **产出数据**: data/blueprint/gallery/plan-archive.json(统一档案: 每项 {id, title, type(计划/路线图/版本/变更日志), domain(域/智能体), file, version, status, relatedTo(蓝图/资产/智能体), updated})
- **新 Tab「📋计划档案」**: 汇总表 + 关系图谱(计划↔蓝图↔智能体↔版本 力导向)

## 二、设计

### 数据结构 plan-archive.json
```json
{
  "version": "1.0",
  "updated": "2026-09-03",
  "domains": ["明鉴","星桥","老登","守灯","司库","罗盘","i9","MBP","系统","ERP",...],
  "items": [
    {"id":"plan-xxx","title":"...","type":"plan|roadmap|version|changelog",
     "domain":"老登","file":"相对路径","blueprint":"关联蓝图id或-",
     "agent":"关联智能体或-","version":"v1.0","status":"active|done|todo",
     "related":["flowernet","mtm"],"updated":"2026-09-03","desc":"摘要"}
  ],
  "links": [{"source":"plan-xxx","target":"flowernet","type":"plan-for"}]
}
```

### 图谱关系
- plan --plan_for--> blueprint(计划服务某蓝图)
- plan --owned_by--> agent(智能体域)
- plan --has_version--> version(版本链)
- changelog --tracks--> project/blueprint

### 扫描器 scripts/bb-plan-scanner.py
- `--scan`: 全量扫(glob 计划 md + 版本文件 + 蓝图目录)→ 生成/更新 plan-archive.json(增量: 按文件 mtime 更新)
- `--selfcheck`: 校验(引用完整性/重复 id/孤儿)
- `--list`: 打印汇总
- 可复跑(幂等), 纳入 sysgraph-version release 流程

## 三、验收标准
| # | 标准 |
|---|------|
| A1 | 首页 = 导览大卡片(全部 Tab 可点直达) |
| A2 | 任意 Tab 可经 #<tab> 深链直达; 对话说「打开X」拉起对应页 |
| A3 | plan-archive.json 覆盖: meituan plans/docs + dsh-collab docs + ROADMAP + 蓝图版本 + CHANGELOG/VERSION |
| A4 | 📋计划档案 Tab: 汇总表(可按域/类型/状态过滤) + 关系图谱 |
| A5 | 图谱点计划 → 看其关联蓝图/智能体/版本; 点蓝图 → 反查其计划 |
| A6 | 扫描器幂等可复跑; 新计划文件入域后 --scan 即收录 |

## 四、里程碑
- M1 导览首页 + 深链全补(A1/A2) — 当日
- M2 扫描器 v1 + plan-archive.json(A3) — 当日
- M3 📋计划档案 Tab(表+图谱)(A4/A5) — 当日
- M4 扫描器进版本发布流程 + 文档(A6) — 收尾

## 五、三件套
- 文档: 本文档 + docs/plan-archive-guide.md(收录规范: 计划文件放哪/如何标记关联)
- 代码: scripts/bb-plan-scanner.py + gallery 后端 build_plan_graph + 前端 renderPlanArchive
- 数据: data/blueprint/gallery/plan-archive.json(自动生成)
