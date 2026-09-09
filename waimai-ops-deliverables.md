# 外卖运营管理系统 · 跨会话交付物

> 会话：session-aa528267（外卖运营管理）
> 落盘：2026-08-16 · 按协作约定 v1 归入 ~/dsh-collab/
> 项目：~/meituan-multi（面板 127.0.0.1:8787，10 店 Chrome 9200-9209）

## 1. 能力清单（16 个 Agent 工具）

| 工具 | 功能 |
|---|---|
| waimai_state / waimai_alerts / waimai_alert_handle | 门店状态 / 告警 / 一键处理 |
| waimai_report / waimai_analyze | 经营日报周报 / 事件聚合分析 |
| waimai_issues / waimai_scenarios | 异常检测（拒单率/掉线/积压）/ 经营场景（售后/配送/投诉） |
| waimai_traffic / waimai_keywords | 流量分析（曝光/渠道/转化）/ 关键字分析（热搜词+标题建议） |
| waimai_action / waimai_operate | 动作原语执行 / 接单拒单（高险需确认） |
| waimai_kb_query / waimai_capabilities | 运营知识库检索 / 原语库清单 |
| waimai_record | 原语录制器（CDP 走查录成可执行脚本） |
| waimai_scan | 平台页面扫描（导航地图/能力清单沉淀） |
| waimai_voice | 语音/文字指令路由（自然语言→意图→执行） |

## 2. 动作原语库（13 个，高险需确认）

接单 / 拒单 / 商品上下架 / 改价 / 改活动折扣 / 售后回复 / 评价回复 / 开店关店 / 查询订单 / 查询折扣列表 / 页面跳转

## 3. 协作数据契约（与 session-de7b29de）

- alerts 按 kind 分工：de7b29de=new_order，aa528267=delivery/refund/complaint
- events 表：de7b29de 独占写，aa528267 只读
- 句式化过滤原则：采集端句式特征 + 消费端句式化排除，裸词只做兜底（「平台券能用吗」保留案例）

## 4. 锁协议（与 session-fa1f9150）

- 只读 API 并行免锁；同店写操作先 agent_light(store:N) → 红灯 lock(wait:true) → unlock
- 运营动作优先 @aa528267 委派；store:N 红灯持有者是 aa528267 时多半在录制（1-3 分钟）

## 5. 可复用情报

- **流量/关键字分析模式**：商家后台「搜索分析」页常为空壳 → 改从订单标题提取高频意图词（真实搜索/成交信号）+ 标题去重防刷榜 + STOP 词表过滤
- **子 frame 抓取**：美团闪购业务页渲染在 CDP 子 frame（非 DOM iframe），用 Page.createIsolatedWorld + frameexec 定位
- **面板守护/备份需求**：Electron 面板无 launchd 自启 + app.db 无定时备份——已提交运维侧改进清单（待执行）

## 6. 索引

- 技术架构：~/meituan-multi/docs/architecture.md
- 迭代路线：~/meituan-multi/docs/iteration-roadmap-v2.md
- 平台学习框架：~/meituan-multi/docs/platform-learning-framework.md
- 语音运营计划：~/meituan-multi/docs/voice-operation-plan.md
