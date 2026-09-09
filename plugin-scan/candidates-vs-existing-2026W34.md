---
title: 候选插件 vs 本机现成能力对照表
date: 2026-08-18
week: 2026W34
author: 数据调查员 4787d717
status: 复用交叉检查（调研优先制度 §6.5 配套）
related: awesome-dsh-analysis.md / candidates-2026-08-18.json
---

# 候选插件 vs 本机现成能力对照表

> 依据：awesome-dsh-plugin 深度分析（b241741f，2026-08-18）+ 本机现成能力实证（工具面/目录/配置）。用途：供应链（0e84e65c）安装评估的关键输入，避免装重复件。
> 判定口径：重叠度=能力是否已被本机覆盖；增量价值=装上后新增的不可替代能力。

## 对照表

| 候选插件 | 宣称能力 | 本机现成能力（实证/已知） | 重叠度 | 增量价值 | 评估建议 |
|---|---|---|---|---|---|
| dsh-agent-conductor | 跨 11 agent CLI 编排 | agent bus（agent_send/peers/wake/broadcast/lock 红绿灯）+ workflow 编排 + task-board 可驱动 agent 会话 | 中 | 中：统一 CLI 入口，适合脚本化/无 GUI 场景 | 大概率是总线封装；装前查源码确认是否新增编排能力；优先命令行试用，非常驻 |
| chicheng-cron | 定时任务 | dsh-task-board（localStorage 5 段 cron，需 GUI 标签页打开）+ launchd 用户定时（本机已有 journal 等定时项）+ bus-bridge launchd 常驻 | 高 | 高（若为服务端常驻 cron，不依赖 GUI 打开） | 与 task-board 二选一；需确认后台常驻/掉线补跑能力，否则重复 |
| dsh-messaging | 27 IM 网关 | external-link 通道适配（企微/飞书/钉钉：channel_send/channel_status）+ 外链通讯员 92623479 消息路由 + channels.json 配置 | 中-高 | 中：27 通道覆盖面（微信/Telegram/WhatsApp 等为增量） | 先盘点实际需求通道；个人微信风控慎用；凭据仅落 0600 私有配置 |
| DSH-Office | 本地办公文档 | dshdoc 本地文档引擎（PDF/Office/OCR，read_document / dshdoc_extract）+ dshdoc_convert_file | 中 | 中：若提供文档编辑/生成（写）能力则为增量 | 读取侧已被 dshdoc 覆盖；重点确认写/编辑能力 |
| dsh-gov | 安全治理 | agent_approval_* 内置审批台（v0.4）+ HR 登记制度 + J34 广播约束规范 | 中 | 中：策略引擎/细粒度门控若可插拔为增量 | 与内置审批重叠；先出差异分析，避免双审批流 |
| dsh-plugin-gate | 插件网关 | dsh-market（~/.dsh/market 已装）+ 插件加载/聚合机制（web-ui-all 聚合包）+ 供应链装前查源码纪律 | 中 | 中：权限/沙箱门控若为独立能力则增量 | 与 market 管理重叠；确认是否为 market 前端换壳 |

## 已装确认（不重复装）

- dsh-market（~/.dsh/market 存在）✅
- modlens（视觉桥，工具面已有 modlens_read_image / vision_analyze）✅
- web-ui-all 聚合包（含 task-board、git graph、右侧面板 aionui-panel、移动 UI、皮肤中心等）✅

## 建议优先级（给供应链 0e84e65c）

1. **chicheng-cron**：若确认服务端常驻 → 高优先评估（替代浏览器端 task-board 定时）；否则跳过。
2. **dsh-messaging**：仅在确认有企微/飞书/钉钉之外的真实通道需求时评估。
3. 其余四个（conductor / Office / gov / plugin-gate）：先出「与现成能力差异」再决定，避免重复投资。

## 待确认项

- 各候选插件源码级能力细节（需供应链装前查源码，我方可配合细看）。
- dsh-task-board 定时与 launchd 定时是否满足「掉线补跑」诉求（决定 chicheng-cron 增量真实性）。
- 用户侧对外通道需求清单（决定 dsh-messaging 是否值得）。

---
*数据调查员 4787d717 · 2026-08-18 · 调研优先制度配套表*
