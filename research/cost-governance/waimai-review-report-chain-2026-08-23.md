# 外卖评价/经营日报发群链路迭代记录（2026-08-23）

> 归属：外卖运营 aa528267 · 迭代自动落链制度（v1.0）示范条目
> 关联 registry：待 HR 登记（提供素材）

## 完成项
1. **差评/评价日报发群闭环**（用户指令「每日评价分析、差评预警发群」）：
   - scripts/daily-review-push.js：4 主力店接口直连采集（fetchBadReviewsApi，comment/r/list）→ 关键词分类（品质/实物图/配送/包装/客服）→ 8790/send P1 发群 → 落盘 docs/reviews/daily-review-YYYY-MM-DD.md
   - 调度器 bad-review-scheduler.js：每日 10:00 差评采集 + 11:00 评价日报发群 + 白天 08:00-22:30 每 30 分钟观察采样（夜间跳过省 CPU）
   - scheduler-watchdog.js：每 60s 守护自动拉起（教训：8/22 内存压力中断 27h 后加装）
2. **经营日报 12:30 恢复**（用户拍板恢复）：
   - scripts/daily-report-push.js：12:30 读 45f89009 产出（docs/reports/daily-report-YYYY-MM-DD.md）→ 8790 P1+source=daily-report 发运营群（含昨日兜底）
   - 接口约定：45f89009 每日 12:25 前落盘，已确认
3. **8790 通道参数固化**（外联 92623479 提供）：level 必须是 JSON body 字段 "P1"（文本 [P1]/🚨 无效）；source=daily-review/daily-report 白名单自动 P1；target=群 chat_id 指定群（实测生效）；P2 无 priority=now 进 digest 队列不即时
4. **资源优化**（HR 告警 mac 内存/CPU）：夜间跳过观察采样（Chrome 导航 -40%）；窗口盘点（IM 工作台=客服线/商家首页=监听，关闭需协调 b193c782/de7b29de）

## 结果/验证
- 8/22 评价日报 P1 发群成功（初蘅5/客村4/江南西5/佛山6，20 条存量；预警：初蘅包装 8/20、江南西配送+花材 8/20；分类：花材品质 50% 首要问题）
- 8/23 经营日报链路验证：45f89009 产出 → daily-report-push.js → 8790 P1 发运营群 ✅
- 调度器 PID + watchdog 双进程运行中；8/22 中断缺口已记录（不回补历史，数据并入 8/23）

## 产出文件
- ~/meituan-multi/scripts/daily-review-push.js
- ~/meituan-multi/scripts/daily-report-push.js
- ~/meituan-multi/scripts/scheduler-watchdog.js
- ~/meituan-multi/scripts/bad-review-scheduler.js（更新：12:30 环节+夜间跳过）
- docs/reviews/daily-review-YYYY-MM-DD.md（每日日报）
- docs/reports/daily-report-YYYY-MM-DD.md（经营日报，45f89009 产出）

## 教训/遗留
- 教训：nohup 常驻进程在内存压力下会被杀且无告警 → 加 watchdog 自动拉起；日期用 UTC toISOString 凌晨会取前一天 → 改本地时间
- 遗留：经营日报 45f89009 产出定时待协调者裁决（当前被动/手动）；企微群 webhook 未配（8790 通道已够用，用户未要求）；发群唯一性=push.js（HR 已裁决），daily-review-group.py cold standby
