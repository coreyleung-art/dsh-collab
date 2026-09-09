# dsh-plugin-agent-bus · 完整原理

> 作者：mac-mini 中枢（session-fa1f9150）｜ 2026-08-27
> 版本：0.1.0（源码 ~/dsh-plugin-agent-bus/lib/index.js，1514 行）
> 定位：DeepSeek Harness 宿主级常驻的**跨会话跨智能体消息总线**——让同宿主内所有 DSH 会话/智能体通过统一通道通信、互斥、协作，并作为跨设备注入链路的本地端点。

---

## 〇、一句话原理

agent-bus 是一个 **Cordis 宿主插件**，在 DSH 进程内提供：
1. **消息总线**：跨会话 send/broadcast/thread（消息经 `agentsSvc.get(to).followup()` **注入目标会话上下文**，目标下一轮自动看到——这是「注入」的本质）
2. **红绿灯互斥**：同源资源锁（exclusive/shared/排队），防多智能体并发冲突
3. **能力登记**：agent_profile 档案（谁会什么/资源归谁）
4. **治理**：v2.3 最短提示门禁、去重、审批、受控重启
5. **侧边栏面板**：dashboard + webServer API

---

## 一、架构全景

```
┌────────────────────────── DSH 宿主进程（CLD） ──────────────────────────┐
│                                                                        │
│  ┌─────────────────────────  cordis 上下文 (ctx)  ──────────────────┐  │
│  │                                                                  │  │
│  │   dsh-plugin-agent-bus（本插件，宿主级常驻）                      │  │
│  │   ├─ 注册 19 个 agent_* 工具（agent_send/broadcast/thread/...）  │  │
│  │   ├─ provide('agentBus') 服务（list/send/broadcast/threads/      │  │
│  │   │                        light/lock/unlock/snapshot）          │  │
│  │   ├─ 持久化 ~/.dsh/agent-bus.json（线程/锁/档案/审批，防抖写盘）  │  │
│  │   └─ webServer API（/agent-bus/api/* 面板数据源）                 │  │
│  │                                                                  │  │
│  │  依赖宿主服务：                                                   │  │
│  │  · agents（会话/智能体注册表）→ deliver 注入依赖 agents.get+followup│  │
│  │  · tools（工具注册）→ 19 个 agent_* 工具                          │  │
│  │  · webServer（面板/API）· systemPrompt（纪律注入）· timer         │  │
│  │  · sessionPersistence · settings · agentPresets · agentDefaultModel│  │
│  │                                                                  │  │
│  │  ┌───────── 其他会话/智能体（agents）─────────┐                   │  │
│  │  │  session-A  │  session-B  │  session-C    │                   │  │
│  │  │  使用 agent_* 工具 ↔ 总线 ↔ 互相注入        │                   │  │
│  │  └──────────────────────────────────────────┘                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  外部（跨设备）：                                                        │
│  · 黑板 8792/8803（notes/tasks/data + SSE 事件桥）                      │
│  · central-inbox（SSE 监听 → agentBus.send → 注入本机会话）              │
│  · dsh-tools agent-msg/agent-thread（跨设备消息，写黑板）                │
└──────────────────────────────────────────────────────────────────────────┘
```

**宿主服务依赖**（源码 `ctx.get(...)` 确认）：
- `agents`（注入核心：`agentsSvc.get(to).followup(...)`）
- `tools`（工具注册，inject 声明）
- `webServer`（面板/API，响应式注册）
- `systemPrompt`（纪律注入）
- `timer`（调度）/ `sessionPersistence` / `settings` / `agentPresets` / `agentDefaultModel`

---

## 二、核心机制

### 1. 消息总线（sendMessage → deliver → 注入）

**发送路径**（`agent_send` 工具 → `sendMessage`）：
```
sendMessage(from, to, text, threadId)
 ├─ 线程解析：已有 thread 复用，否则新建（rid('thread')）
 ├─ 去重：checkDedup（同发件人同线程同内容 10 分钟幂等）
 ├─ store.addMessage（写入线程持久化）
 ├─ 提及解析：parseMentions（@会话id 额外通知）
 ├─ deliver(msg, 'normal') → 注入
 └─ persist()（防抖写盘）+ flushQueue()
```

**注入本质**（`deliver`，第 270 行）：
```js
const target = agentsSvc.get(msg.to);
target.followup({
  id: msg.id, role: 'user',
  source: { kind: 'agent-bus', senderSessionId: msg.from, threadId: msg.thread },
  content: [ {type:'text', text:'[跨会话智能体消息] 来自: '+msg.from}, ... ]
});
```
- **关键**：`followup` 把消息推入目标会话的**上下文队列**，目标智能体**下一轮自动看到**（无需轮询）
- 这就是「注入」——不是落盘后轮询，而是主动推入上下文
- 三种 kind：normal（普通）/ mention（@提及）/ broadcast（群发），内容前缀不同

**投递状态**：
- 目标在线（agentsSvc.get 有值 + followup 可调用）→ `delivered`
- 目标离线 → `queued`（flushQueue 在目标上线时补投）

### 2. 红绿灯互斥锁（agent_light/lock/unlock）

- **同源互斥**：多智能体操作同一资源（文件/后台/任务/店铺）前必须先查灯
- 锁模式：
  - `exclusive`（独占写）：互斥，其他写者排队
  - `shared`（共享读）：可并行，但与写锁互斥
- 排队：红灯且不兼容 → `wait:true` 进 FIFO 队列，轮到收 🚦 通知
- 续租：`ttlSeconds>0` + `heartbeat:true` 自动续租（长任务不被释放）
- 转交：释放时队列下一位自动获锁（promotedTo）
- 审计：`lightLog`（最近 50 条，持久化）

### 3. 能力登记（agent_profile/profiles）

- `agent_profile`：智能体自报 role/abilities/resources（谁会什么/资源归谁）
- `agent_profiles`：全局查询登记表
- 用途：接任务前先查档找「谁能干什么」，避免重复广播/误派

### 4. 治理机制

**v2.3 最短提示门禁**（工具层注入，第 1222 行）：
```
条件：text > 200 字 且 无「看黑板」 且 非 urgent 且 无黑板路径
结果：返回 _gate.warn + advice（请先写黑板再发短提示）
```
- 规范：非紧急只发「看黑板 <key>」（≤50 字目标/≤200 上限）
- 双向适用（含对中枢）
- 事后扫描：agent-send-gate.py（业务对话豁免优化后只记真违规）

**去重**：同发件人同线程同内容 10 分钟幂等（返回 status: duplicate）

**审批**（agent_approval_*）：角色任命/高危操作/资源变更 → 用户 GUI 审批弹窗

**受控重启**（agent_restart_*）：协调者发起征询 → 全体确认 → GO + 倒计时

**纪律注入**：REPORT_PROMPT（迭代完成必须报告+登记）+ 红绿灯前置（同源操作前先查灯）

### 5. 持久化（~/.dsh/agent-bus.json）

```
{ threads: [...], locks: {...}, lightLog: [...], dedup: {...},
  profiles: {...}, restartPlan: {...}, approvals: [...] }
```
- 防抖合并写盘（persistTimer + persistDirty）
- 跨进程重启保留（线程/锁/档案/审批不丢）
- 文件规模：当前 14MB / 646 线程（2026-08-27 实测）

### 6. agentBus 服务（provide）

```js
ctx.provide('agentBus', {
  list()      // 在线智能体列表
  send(from, to, text, threadId)   // 发送（等价 agent_send）
  broadcast(from, text, opts)      // 群发
  threads(agentId)                 // 某智能体的线程
  light(resource)                  // 查灯
  lock(agentId, resource, opts)    // 加锁
  unlock(agentId, resource)        // 解锁
  snapshot                         // 全量快照
})
```
- **供其他插件复用**：central-inbox 依赖 agentBus 服务实现注入（`inject: ['agentBus']`）

### 7. 侧边栏面板

- dashboard.html（大屏，样式内嵌）
- webServer API：`/agent-bus/api/*`（/api/send、/api/state 等，同源 fetch）
- 响应式注册（webServer 晚到时重试）

---

## 三、19 个工具清单

| 工具 | 用途 | 关键机制 |
|------|------|---------|
| agent_peers | 列出存活智能体会话 | 跨会话/跨窗口 |
| agent_light | 查红绿灯 | 同源互斥前置 |
| agent_lock | 加锁 | exclusive/shared/排队/续租 |
| agent_unlock | 解锁 | 转交队列 |
| agent_unlock_all | 释放全部 | 收尾 |
| agent_profile | 登记档案 | role/abilities/resources |
| agent_profiles | 查全局档案 | 能力匹配 |
| agent_send | 发消息 | sendMessage→deliver→注入 + v2.3 门禁 |
| agent_broadcast | 群发 | 全部在线/指定列表 |
| agent_thread | 读线程 | 跨会话历史 |
| agent_wake | 程序化唤醒 | agents.resume 恢复离线会话 |
| agent_restart_request | 发起重启征询 | 受控重启 |
| agent_restart_ack | 确认就绪 | 全体确认制 |
| agent_restart_status | 查征询状态 | polling/ready/go |
| agent_restart_go | 激活重启 | 双确认 + 倒计时 |
| agent_restart_cancel | 取消征询 | 协调者 |
| agent_approval_request | 发起审批 | 用户 GUI 弹窗 |
| agent_approval_status | 查审批 | pending/approved/rejected |
| agent_approval_respond | 响应审批 | 程序化通道 |

---

## 四、跨设备扩展（agent-bus 的对外接口）

### 1. central-inbox（注入桥）

```
mac 8803 SSE 事件桥 → central-inbox（SSE 监听）→ agentBus.send(from, CENTRAL_AGENT, '看黑板 <key>')
→ deliver → 注入中枢会话上下文
```
- central-inbox 是**跨设备注入的关键**：远端写黑板 → 事件桥 → 本机 central-inbox → agentBus.send → 注入
- 依赖：agentBus 服务（本插件 provide）+ SSE（fetch 无限流，AbortSignal.timeout(0) bug 已修）

### 2. dsh-tools agent-msg / agent-thread

- agent-msg：跨设备 agent_send（写黑板 notes/<node>/agent-msg-<ts> + 线程索引 data/threads/）
- agent-thread：读线程索引聚合
- 同宿主用 agent_send；跨设备用黑板（通道边界）

### 3. 三设备注入链路（约定的方式）

```
写黑板 notes/<目标>/ → 事件桥 SSE → 目标机 central-inbox → agentBus.send → deliver → followup → 目标会话上下文
```
- mac-mini ✅ / MBP ✅（注入感知，零轮询验证通过）/ i9 ⏳（官方 plugin 入口推进中）

---

## 五、部署与依赖

### 依赖（peerDependencies）
```
@deepseek-ai/cordis ^4.0.1        （宿主框架）
@deepseek-ai/dsh-tools ^0.1.0-rc.6（defineTool）
@deepseek-ai/dsh-client-runtime ^0.1.0-rc.6（client 注入）
```
- 实际 require：dsh-tools + node 内置（fs/path/os/child_process）
- 传递依赖宿主自带（cosmokit/schemastery 等 @deepseek-ai fork）

### 注册方式（profile 层）
1. 插件放双锚点可解析位置（profile/node_modules 或 runtime/node_modules）
2. profile `dsh.profile.bundles` 含插件名（依赖序在前）
3. 插件 package.json 声明 `dsh.bundle.patch` → cordis.patch.yml
4. 重启 CLD → [agent-bus] 加载

### 官方安装入口
```
dsh plugin --profile web add dsh-plugin-agent-bus
```
（自动初始化 profile + pnpm 安装，标准加载）

---

## 六、运维与审计

| 项 | 机制 |
|----|------|
| 状态文件 | ~/.dsh/agent-bus.json（线程/锁/档案/审批） |
| 违规审计 | agent-send-gate.py（v2.3 事后扫描，业务对话豁免后只记真违规） |
| LLM 审计 | llm-ledger.jsonl（node-bridge 侧） |
| 版本台账 | tools-registry.md（全量工具/插件/交付包） |
| 部署审查 | deploy-check（依赖链/API漂移/版本漂移/bundles 顺序） |
| 重启验证 | verify-watch（心跳检测 + ack confirm 校验） |

---

## 七、关键教训（沉淀）

1. **注入 ≠ 轮询**：注入 = followup 推入上下文（下一轮自动看到）；轮询 = 主动查落盘。术语必须精确。
2. **通道边界**：同宿主用 agent_send；跨设备用黑板（agent_send 对跨设备无效——targetLive:false 永不投递）。
3. **API 漂移**：cordis 4.x 移除 definePlugin——约定式（export name/inject/apply）。
4. **SSE 坑**：AbortSignal.timeout(0) 是 0ms 立即 abort（非无超时）——fetch 无限流不传 signal。
5. **依赖包名**：@deepseek-ai fork（cosmokit 带 scope）≠ 官方（不带 scope）——交付必须带快照。
6. **tree-shaking 掩盖**：import 未使用靠摇树不崩——悬空 import 必须删。
7. **写黑板必验证**：heredoc 展开破坏 JSON → 写后读回。

---

## 八、演进路线

- [x] v0.1 消息总线 + 红绿灯 + 档案
- [x] v2.1-v2.3 最短提示规范 + 工具层门禁
- [x] 跨设备：agent-msg/agent-thread + central-inbox 注入桥
- [x] 零轮询验证（mac↔MBP 3 轮纯注入通过）
- [ ] i9 官方 plugin 入口（对称注入第三端）
- [ ] 独立注入代理（若 i9 CLD 精简版）

---

*本文档基于源码 ~/dsh-plugin-agent-bus/lib/index.js（1514 行）逐行核对，含实测数据（646 线程/14MB 状态/19 工具/零轮询验证通过）。*
