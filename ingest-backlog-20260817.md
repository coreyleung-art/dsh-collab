# 待摄取文档盘点清单（文档摄取/归档智能体 · session-55d4d1bd）

> 盘点时间: 2026-08-17 · 盘点范围: ~/Desktop、~/Downloads、~/Documents（用户指定文档源）
> 状态: ⏳ 清单建立，待委派确认后逐项执行
> 边界: 敏感文档不入库只登记；append-only 日志只追加；写 vault 前查 file:vault 红绿灯

## 一、~/Desktop（3 份 MD 运维文档）

| 文件 | 类型 | 建议 | 敏感 |
|------|------|------|------|
| DSH-macmini-故障诊断报告.md | markdown | 摄取 → raw + wiki 摘要 | 否 |
| DSH-macmini-防崩溃运维手册.md | markdown | 摄取 → raw + wiki 摘要 | 否 |
| DSH-macmini-发消息故障诊断报告-20260817.md | markdown | 摄取 → raw + wiki 摘要 | 否 |

## 二、~/Downloads（38 份文档 + 34 张图片）

### 2.1 岗位标准化项目相关文件（21 份 DOCX/XLSX，批量摄取高优先级）

| 文件 | 类型 | 建议 | 敏感 |
|------|------|------|------|
| 【汇总】门店标准化运营文档.docx | docx | 批量摄取 | 否 |
| 花店运营工作岗位手册.docx | docx | 批量摄取 | 否 |
| 守白花艺-门店客服标准化话术.docx | docx | 批量摄取 | 否 |
| 守白花艺-门店标准化话术电话沟通话术与处理指引.docx | docx | 批量摄取 | 否 |
| 守白鲜花-物品命名标准化规范.docx | docx | 批量摄取 | 否 |
| 守白鲜花店6S现场管理实施细则.docx | docx | 批量摄取 | 否 |
| 守白鲜花店门店编制标准及岗位执行标准.docx | docx | 批量摄取 | 否 |
| 手机客服岗位细化图文.docx | docx | 批量摄取 | 否 |
| 电脑客服岗位细化图文.docx | docx | 批量摄取 | 否 |
| 打包岗位细化图文.docx | docx | 批量摄取 | 否 |
| 骑手对接岗位细化图文.docx | docx | 批量摄取 | 否 |
| 理花助理培训-带训人操作规范与要求.docx | docx | 批量摄取 | 否 |
| 订单高峰期-标准化人员培训文件.docx | docx | 批量摄取 | 否 |
| 门店间物品调拨 SOP（标准操作流程）.docx | docx | 批量摄取 | 否 |
| 商家必看！圣诞花束重灾区避坑指南.docx | docx | 批量摄取 | 否 |
| 花材辨认图.docx | docx | 批量摄取（含图需 OCR） | 否 |
| 外卖鲜花门店补单量激励规划.docx | docx | 批量摄取 | 否 |
| 初蘅BP.docx | docx | 批量摄取 | 否 |
| 门店营业-开店时段质控表.xlsx | xlsx | 批量摄取 | 否 |
| 守白鲜花店绩效薪酬制度.docx | docx | ⚠️ 只登记不入库 | **敏感（薪酬）** |
| 物品采购付款与费用报销 执行规范.docx | docx | ⚠️ 只登记不入库 | **敏感（财务）** |

### 2.2 其他文档（17 份，中等优先级）

| 文件 | 类型 | 建议 |
|------|------|------|
| 花壳Lab-知识库完整版.md | markdown | 摄取 |
| AgentHub_2026-04-23_开发任务清单_v1.0.md | markdown | 摄取 |
| 颁奖晚宴活动_分镜表.txt | txt | 摄取 |
| 后台框架设计.md.docx | docx | 摄取 |
| 数据库设计.md.docx | docx | 摄取 |
| 小程序框架设计.md.docx | docx | 摄取 |
| 技术方案.md.docx | docx | 摄取 |
| 完整规划.md.docx | docx | 摄取 |
| 活动海报生成_审查报告.md.docx | docx | 摄取 |
| 花店员工培训系统_审查报告.md.docx | docx | 摄取 |
| 2026-04-23_活动拍摄分镜工具.md.docx | docx | 摄取 |
| 2026-04-23_AI工具学习平台.md.docx | docx | 摄取 |
| 2026-04-23_绿植销售签收生成器.md.docx | docx | 摄取 |
| 2026-04-23_活动主持人手卡生成器.md.docx | docx | 摄取 |
| 2026-04-23_花觅小程序.md.docx | docx | 摄取 |
| agenthub开发任务清单.md.docx | docx | 摄取 |
| 开发任务清单.md.docx | docx | 摄取 |

### 2.3 图片/截图（34 张，OCR 候选，待 OCR 运行时落地）

> ⚠️ 阻塞: dshdoc 引擎 OCR 不可用（macOS 架构性），tesseract 方案 A' 待用户批准。落地前图片只登记不入库。
> 代表: 花壳教程截图×2、企业微信截图、IMG_7xxx 系列（手机截图）、548/549/553 等 JPG

## 三、~/Documents（1 份，低优先级）

| 文件 | 类型 | 建议 |
|------|------|------|
| AI经济信息雷达每日采集/AI经济信息雷达_2026-08-15.md | markdown | 每日新增，可建周期摄取 |

## 四、~/dsh-collab（90 文件，协作区，各会话交付物按委派执行）

> 已收到委派: repo-pipeline-deliverable.md / repo-pipeline-kb-full.md / README.zh.md（重复检测已完成，待确认处置方案）
> 其余交付物（remote-access-fix-r1、session-list-perf-localization-r1、恢复评估等）等待各会话正式委派

## 五、归档规范（v1，执行时遵守）

1. raw/ 放源文件（规范化副本，YYYY-MM-DD-slug.md 命名，含 frontmatter）
2. wiki/ 编译摘要页（Summary/Content/Related/Sources 结构，400-1200 词）
3. raw/index.md + wiki/index.md 登记
4. wiki/log.md append-only 追加（用 edit 追加，禁止部分读+全量写）
5. 写 vault 前 agent_light(file:vault) + 拿锁；写入前缀域 d-55d4-
6. 敏感文档（薪酬/财务/账号/密码）只登记不入库
7. 完成后附质量指标（成功率/OCR 率/入库完整性）供 QA 核验
