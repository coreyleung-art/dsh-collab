# CHANGELOG

## [0.2.0] - 2026-08-31
### Added
- price-analysis 子命令：按 store/date-range 输出逐日折扣率 + 汇总（gross/net/qty/overall_discount_pct）
- 数据源 order_sales（app.db），与 JS lib/price-analysis.js 输出一致（守白8月 gross 212412.1/net 68024.26/disc 32.0% 逐分相同）

## [0.1.0] - 2026-08-31
### Added
- chat-stats：聊天记录库统计
- chat-query：按 store/product/keyword 查询会话+消息+图片
- selfcheck：TCC 自检（R006 ②）
- version：语义化版本（R006 ⑥）
- 统一日志 ~/.dsh/dsh-data-tools.log（R006 ⑦）
- 性能：chat-stats 8ms（JS 65ms，8x）
