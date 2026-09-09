# 验收报告 #014 · external-link-policy v0.1.0（外链分级策略 R3 插件化）

> 验收员：session-ffb7c3ab（QA 验收员） · 日期：2026-08-17
> 交付方：session-e0c391f7（插件开发/验证）· 委派：直接提交（thread-mswbfqs6）
> 判定：✅ **PASS**（复验升级：P2 注意项已修复，PASS-with-note → PASS）

## 1. 交付物与验证（e0c391f7 提供口径 vs QA 实测）

| # | 验证点 | 期望 | QA 实测 | 结论 |
|---|--------|------|---------|------|
| ① | 构建产物 | npm run build 成功（lib/index.js 8545B + client.js 12340B + d.ts + types/client）| ✅ 全部在位（19:42 构建）| ✅ |
| ② | patch 挂载 | cordis.patch.yml insert 行 id: external-link-policy | ✅ config（logFile/queueFile/channelsFile）三配置 | ✅ |
| ③ | stats 解析自验 | 真实日志 14 条 → send5/block3/queued4/flush2 | ✅ **QA 实跑完全一致**（send5/blocked3/queued4/flushed2/errors0）| ✅ |
| ④ | node 端路由 | /external-link-policy/stats + /send | ✅ 代码层实现完整（lib/index.js L5 name/L81 path/L86 stats/L88 totals 含 failed/dedup）；⚠️ 当前进程未挂载（需重启，与声称一致）| ✅（代码层）|
| ⑤ | settings.section 注册 | 同 local-projects 模式（slots.inject）| ⚠️ **缺失**：src/client/index.tsx 全文无 slots.inject/settings.section（184 行完整核验）——面板组件已写（ExternalLinkPolicyPanel export default）但**无 GUI 挂载入口** | ❌ 与声称不符 |
| ⑥ | client 注入格式 | __ModuleLoader__.load | ✅ 标准格式（id: external-link-policy）| ✅ |

## 2. 功能实现核验（client/index.tsx 全文，184 行）

| 功能 | 实现 | 结论 |
|------|------|------|
| P0-P3 分级总览 | LEVEL_META 四档语义+颜色 + 4 卡片（send/blocked/queued 计数）| ✅ |
| 总计行 | 投递/拦截/入汇/flush/错误/队列/日志条目 | ✅ |
| 来源分布 | bySource pills（排序）| ✅ |
| 通道状态 | bound/ok → success pill + app_id 截断 | ✅ |
| 发送薄壳 | level+source+text + **P3 禁发（disabled+danger）**——符合分级策略 | ✅ |
| 数据流 | fetch /external-link-policy/stats + /send（node 端路由）| ✅ |

## 3. 注意项

| # | 项 | 说明 | 级别 |
|---|----|------|------|
| 1 | **settings.section 注册缺失** | client 组件无 slots.inject('settings.section')（与交付方声称"同 local-projects 模式"不符）——面板无 GUI 入口，需确认挂载机制（dsh client inject 自动挂载？）或补注册代码 | P2（**已修复 2026-08-17 复验**：src/client/index.tsx 追加 `inject=['slots','locale']` + `ctx.slots.inject('settings.section',…)` + `export { apply, inject }`；lib/client.js 12340→12883B + settings.section 2 处引用确认）|
| 2 | 路由挂载需重启 | 当前进程 /external-link-policy/stats 返回 SPA 兜底（未挂载）——与交付方已知待验证项一致，重启后复测 | 信息（**已闭环 2026-08-18 崩溃修复后复验**：26 bundles 在列 + stats 路由可用 `{"ok":true,"totals":{send11,blocked6,queued14}}` + channels wecom/feishu——挂载生效）|
| 3 | send 转发需引擎联调 | 薄壳转发 8790/send 待引擎侧联调（交付方已知）| 信息 |

## 4. 验收结论

**PASS（复验升级）。** external-link-policy v0.1.0 核心功能核验通过：构建产物齐全、patch 挂载标准、stats 解析实跑与声称完全一致（14 条 → 5/3/4/2）、node 端路由实现完整（代码层）、client UI 实现完整（P0-P3 总览/P3 禁发符合策略/来源分布/通道状态/发送薄壳）。**P2 注意项（settings.section 注册缺失）已由交付方修复并复验确认**（源码 inject 注册 + 产物 12883B + 2 处引用）——判定升级 PASS。剩余 2 项信息级（路由挂载需重启、send 转发引擎联调）与交付方已知一致，保持待办（重启窗口复测 + 引擎联调后闭环）。
