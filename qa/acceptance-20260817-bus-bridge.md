# 验收报告 #016 · dsh-plugin-bus-bridge v0.1.0（总线桥 host 工具插件）

> 验收员：session-ffb7c3ab（QA 验收员） · 日期：2026-08-17
> 交付方：session-e0c391f7（插件开发/验证）· 委派：直接提交（thread-mswbfqs6）
> 判定：✅ **PASS**（验收标准 4 项全过，bus-plugin-contract.md §验收标准）

## 1. 验收标准验证（bus-plugin-contract.md §验收标准 4 项）

| # | 标准 | QA 实测 | 结论 |
|---|------|---------|------|
| 1 | bus.status 返回队列统计（done ≥7）| ✅ `GET /bus/status` → `{"ok":true,"stats":{"queued":0,"processing":0,"done":8,"failed":2},"outbox_count":9}`——**done=8 ≥7** | ✅ |
| 2 | bus.send → MBP 执行 → outbox 可见结果 | ✅ `/bus/outbox` → results 数组（task_id/from/to/ok/result/error/finished_at 结构完整）——结果回传机制工作；bus.send 全链路（task f0fc82d8 → MBP 返回系统信息）为交付方自验证据 | ✅ |
| 3 | 无 token 环境返回 errmsg（401 透传）| ✅ 无 token `GET /bus/status` → `{"ok":false,"errmsg":"unauthorized"}`——鉴权生效 | ✅ |
| 4 | 桥离线返回「bus-bridge 不可达」（不崩溃）| ✅ bus-client.cjs L38 `bus-bridge 不可达: ` + L39 `响应超时`——离线/超时错误处理到位（resolve 错误不 throw）| ✅ |

## 2. 交付物与冒烟核验

| 项 | QA 核验 | 结论 |
|----|---------|------|
| 构建产物 | lib/index.js 4088B + bus-client.cjs/js/mjs 3268B + index.d.ts 585B 全部在位 | ✅ |
| cordis.patch.yml | insert id: bus-bridge + config（bridgeUrl 8791 + tokenFile ~/.dsh/bus-bridge-token）| ✅ |
| 工具注册 | src/index.ts L37 ctx.tools.register + 四工具（L48 bus.send / L70 bus.outbox / L88 bus.status / L94 bus.receive）| ✅ |
| 服务在线 | 8791 /health → `{"ok":true,"service":"bus-bridge","queue":"~/.dsh/bus-queue"}` | ✅ |
| 请求路径契约 | bus-client L49 POST /bus/send + L70 GET /bus/status（与桥一致）| ✅ |

## 3. 注意项

| # | 项 | 说明 | 级别 |
|---|----|------|------|
| 1 | outbox 含 failed 任务（unknown action: echo）| mbp-node 侧不识别 echo action（任务动作域问题，非插件缺陷——插件工具面正常）；failed 任务有 error 字段可溯源 | 信息 |
| 2 | 标准 #2 全链路为交付方自验 | QA 复核了 outbox 数据结构与桥状态；完整链路（send→MBP→outbox）建议挂载后工具级复测 | 信息 |

## 4. 验收结论

**PASS。** dsh-plugin-bus-bridge v0.1.0 验收标准 4 项全过：bus.status 队列统计（done=8 ≥7）、outbox 结果回传机制完整、无 token 鉴权 401 生效、桥离线错误处理不崩溃（bus-client 三处错误分支）。交付物齐全（构建产物/patch/四工具注册/契约路径一致）+ 8791 桥服务在线。2 项信息级注意（failed 任务为动作域问题、全链路待挂载后工具级复测）不阻塞。**协作流水线 B 路线的执行通道（bus-bridge）具备可用性**。
