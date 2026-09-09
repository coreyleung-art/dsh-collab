# 插件变更告警模板（用例 #2 · 企微外发）

> 固化时间：2026-08-17 · 首投验证 success:true（channel.send → aibot send → 企微 markdown 完整渲染）
> 归属：插件运维会话 · 外发通道：外链通讯员 92623479
> 外链分级（policy v1.0 + 通讯员确认）：插件周报=P1；插件变更告警=P1；供应链巡检=P3（拦截）

## 触发条件
- 依赖加固（profiles/web overrides/postinstall 变更）
- 插件升级/新增/移除（bundle 层变更）
- 兼容性风险事件（如 pnpm 静默降级、平台绑定依赖问题）

## 文本结构（三节）
```
📦 插件生态周报摘要（YYYY-MM-DD）
• 变更项：<新增/升级/加固 5 项已生效>
• 供应链：<pnpm/override/平台绑定依赖状态>
• 待办：<CLD 重签等 pending 项>
```

## 分级执行
- 插件周报：level=P1, source=plugin → 可推送
- 插件变更（升级/新增/加固）：level=P1, source=plugin → 可推送
- 供应链巡检（依赖审计/巡检类）：level=P3 → 拦截不推，仅落盘登记

## 投递协议
- 我侧产出「安装记录+变更摘要」文本
- channel.send(channel=wecom, text=摘要) → 外链通讯员转发
- 回执 success/失败详情 → 失败走重试/人工确认