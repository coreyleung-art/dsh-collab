# 重启验证完成（2026-08-27）

> 1e54d56d GUI 插件开发

## ✅ 已验证
1. **flower-cockpit 生效**（ws.register 修复验证通过）：
   - /api/state → 真实 JSON（非 SPA 兜底）：周报模板（天河1号店-守白鲜花 2026-W34）+ 促销方案 7 条 + 8 卡 dashboard（销售额 ¥1500.85 + 7 天趋势 events 数据）
   - /api/artifacts → 契约 API 正常（count 0 + contract 声明）
2. **central-inbox 依赖链**：agent-way(=agent-bus symlink) 提供 agentBus 服务确认（lib/index.js），bundles 31 项
3. **产物/持久化**：5 插件产物全在 + 4 数据文件完好

## ⏳ 待验证
- central-inbox 注入链路（8803 SSE 连接日志 → 写 notes/mac-mini/ 测试消息 → 中枢收到『看黑板 <key>』）
- excalidraw 前端加载（sidebar 白板按钮）
- gov 磁盘补丁生效

## 📌 说明
- 端口 52074（当前 DSH web）flower API 已通；8787 面板无此路由（预期，host 在 DSH 宿主内）
- 若 QA 需要复验三范围：模块加载 ✅ / API ✅ / 功能（dashboard 数据）✅
