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
4. **治理**：v2.4 最短提示门禁（分级：紧急 urgent 豁免 / 日常 deny）、去重、审批、受控重启
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

**v2.4 最短提示门禁**（工具层注入，2026-08-30 升级 warn→deny，阈值 200→50）：
```
条件：text > 50 字 且 无「看黑板」 且 非 urgent 且 无黑板路径（紧急/日常分级保留：urgent 标记豁免全文；日常全文 deny）
结果：返回 _gate.deny（硬拒绝发送）+ advice（写黑板再发「看黑板 <key>」，urgent 豁免）
```
- 规范：非紧急只发「看黑板 <key>」（≤50 字目标）；紧急（urgent）全文放行（分级保留）
- 双向适用（含对中枢）
- 事后扫描：agent-send-gate.py（业务对话豁免优化后只记真违规）

**去重**：同发件人同线程同内容 10 分钟幂等（返回 status: duplicate）

**审批**（agent_approval_*）：角色任命/高危操作/资源变更 → 用户 GUI 审批弹窗

**受控重启**（agent_restart_*）：协调者发起征询 → 全体确认 → GO + 倒计时

**纪律注入**：REPORT_PROMPT（迭代完成必须报告+登记）+ 红绿灯前置（同源操作前先查灯）

**版本管理自动化**（2026-08-28 固化，dsh-tools v1.5.0）：
```
完成实质迭代（修 bug/加能力/改配置）后，对源码仓库自动执行：
dsh-tools version --type fix|feat|breaking --desc '<变更描述>' --repo <仓库路径>
```
- 自动完成：bump 版本（node package.json / rust Cargo.toml）→ 追加 CHANGELOG → git commit → git tag → 推送提示
- 变更类型：fix→patch / feat→minor / breaking→major（semver）
- 推送：GitHub 主站 443 被墙时用 REST API 兜底（`scripts/rest-push.py`，gh token）或 repo setup 的 SSH deploy key 通道
- 目的：替代手动逐项版本管理，让「记录变更 → 版本化」跟随任务自动完成

**论文全文自动化**（2026-08-28 用户授权，无需再问）：
```
调研论文后，自动执行 research-pipeline 3-5 步（不再询问用户）：
3. research-fetch 抓全文 → 4. 编译 wiki 报告 → 5. 向量索引 ChromaDB
```
- 论文档案落 research/papers-local/，元数据追加 ai-papers-database.md
- 评级：新论文 B 级临时入库，2 独立来源 + 代码开源/会议收录后升 A
- 触发：任何涉及论文调研的迭代完成后自动执行

**新插件上线检查清单**（2026-08-28 崩溃教训，peerDeps 缺导致 CLD 启动崩）：
```
每个新 dsh 插件上线前必须：
1. peerDependencies 声明完整（import 的 @deepseek-ai/* 全部声明，对齐 agent-way v1.3.0 模式）
2. 本地加载验证（非仅 dump-config——dump-config 不 import 模块，不能当运行证明）
3. 用 deploy-check 静态审查（依赖/API 漂移/解析链）
4. 上线即版本化（dsh-tools version + CHANGELOG + tag）
```
- 教训来源：dsh-plugin-openchronicle v0.1.0 缺 peerDeps → CLD 启动 ERR_MODULE_NOT_FOUND 崩溃（mbp-bus 修复记录）
- 兜底机制：插件目录 symlink → 运行库副本（非破坏，纯新增）

**黑板消息发送规范**（2026-08-28 空内容教训，JSON 转义坑）：
```
写黑板消息（含换行/特殊字符/中文标点）必须用 python json.dumps 生成 JSON 文件再 curl 发送：
  python3 -c "import json; json.dump({...}, open('/tmp/msg.json','w'), ensure_ascii=False)"
  curl -X PUT http://.../notes/<key> -H "Content-Type: application/json" --data-binary @/tmp/msg.json

禁止：
  ❌ curl -d "{\"body\": \"...\"}"  —— heredoc 引号/斜杠转义出错 → value 空
  ❌ printf '{"body":"...\\n..."}' —— printf 把 \n 转成字面换行 → JSON 非法 → value 空
```
- 症状：设备收到空消息（value 空对象），黑板 PUT 返回 200 但内容丢失
- 判定：写入后立即 GET 回读验证 value 非空（每次发消息后自检）

**插件化工具化标准**（2026-08-28 用户确立，强制规则）：
```
凡用户说「插件化 / 工具化」，默认按以下标准执行（缺一不可）：
1. **dsh 插件形态**：cordis 插件（约定式 export name/inject/apply + defineTool/ctx.tools.register）
2. **TCC 检测**：macOS 权限自动检测（参考 meituan-multi/scripts/tcc-check.sh，TCC.db 查询 + 降级提示）
3. **CLD 自适应**：自适应 CLD 或让 CLD 适配（版本差异不硬编码）
4. **dsh 版本自适应**：版本指纹 + 能力探测（参考 agent-bus/lib/adapt.js 的 KEY_PACKAGES + probeCapabilities）
5. **文档化**：README（工具说明/用法/环境变量）+ 工具注释
6. **版本管理**：git + tag + CHANGELOG + GitHub Release（dsh-tools version 流程）
7. **日志管理**：统一日志（文件落盘，参考 central-inbox.log 方案——CLD stdout 不可见，必须 appendFileSync 落盘）
8. **自动落链**：知识库（ops-science-research）+ 台账（tools-registry.md）+ 黑板归档
9. **CLI 治理**（2026-08-29 用户确认）：工具化若有治理需求（增删改查/审批/状态），必须带 CLI 或治理接口（参考 rules-cli.py：list/get/add/approve/reject/sync/audit）
10. **约束前置 · Lean4 逻辑门**（2026-09-06 用户批准扩展）：凡工具/规则涉及"不该发生的路径"（违规写/越权/跳步/非法引用），约束须前置为结构不可绕过（类型锁/入口门/schema门/状态机），且工具带 --lean4-check 自检（违规路径实测被拒）。参考 docs/r006-proposal-lean4-gate-v1.md
```
- 验收：新插件/工具必须 9 项全达标才交付（对照本清单）

**删前考古纪律**（2026-08-28 HR 工具化，J47 扩展）：
```
删除/清理共享资源前，先跑 pre-delete-archaeology.py 考古评估：
  python3 scripts/pre-delete-archaeology.py <路径>
三态判定：safe_delete（安全删）/ archive_meta（归档元数据）/ sediment_first（先沉淀）
```
- 适用：全部智能体（删共享资源前）+ 全部项目（删资产前留考古清单）+ 端侧 i9/MBP（Python 跨平台）
- 与 sedimentation-chain-scan 形成「一进一出」闭环（入库沉淀 + 删前考古）
- SOP：docs/pre-delete-archaeology-sop.md

**central-inbox 注入目标必须显式配置**（2026-08-28 i9→mac 不通教训）：
```
每台设备的 central-inbox 必须显式设 CENTRAL_AGENT=<本机中枢会话id>：
  launchctl setenv CENTRAL_AGENT session-<中枢id>   # macOS
  setx CENTRAL_AGENT session-<中枢id>               # Windows

禁止依赖自动找第一个会话（findCentralAgent 回退逻辑）：
  - 自动找 = agentBus.list() 第一个会话，可能是普通/历史会话（如 session-288848db）
  - 导致跨设备消息注入到错误会话，中枢收不到（i9→mac 不通的根因）
```
- v0.1.2 起 CENTRAL_AGENT 显式优先（`const explicit = process.env.CENTRAL_AGENT`）
- 三端双向注入验收标准：每端设对 CENTRAL_AGENT（mac-mini=中枢 fa1f9150，MBP/i9=各自中枢会话）
- 排查：`grep "注入目标已就绪" ~/.cld/logs/dsh-web.log` 看注入到谁

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
| agent_send | 发消息 | sendMessage→deliver→注入 + v2.4 门禁（分级）|
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
- **v1.3.0 起 peerDeps 补全 11 个**（修复可靠性审计 #1，可独立安装）：
  `cordis / dsh-tools / dsh-client-runtime / dsh-agent / dsh-session-persistence / dsh-settings / dsh-system-prompt / dsh-host-webserver / dsh-agent-default-model / dsh-agent-presets / dsh-client-locale`

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

### 当前安装路径（M1，2026-08-27）
- **npm 官方发布被认证阻塞**（"Public registration is not allowed"）→ 用 **git URL 锁 ref**：
  ```
  dsh plugin --profile web add git+https://github.com/coreyleung-art/dsh-plugin-agent-way.git#v1.3.0
  ```
- **双实例防护三件套**（详见 docs/m1-git-url-install-path-20260827.md §6.3~6.5）：
  1. `nodeLinker: hoisted` + `autoInstallPeers: false`（pnpm-workspace.yaml）
  2. @deepseek-ai/* 符号链接 → CLD runtime（34 个，guard 脚本守护）
  3. peerDeps 在 profile「缺失」是安全态（Node 解析链命中 runtime 单实例）
- **守护脚本**：`~/dsh-collab/scripts/ensure-hub-symlinks.sh`（v2，幂等，三端可用）

---

## 六、运维与审计

| 项 | 机制 |
|----|------|
| 状态文件 | ~/.dsh/agent-bus.json（线程/锁/档案/审批） |
| 违规审计 | agent-send-gate.py（v2.4 事后扫描，业务对话豁免后只记真违规） |
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
6. **GitHub 主站 443 可能被墙**：git push/clone 走主站会超时，但 `api.github.com`/`codeload.github.com` 正常——用 `gh api` REST 建 ref/tag 绕过（M1 实测：5 个 tag 全推成功）。
7. **符号链接 ≠ 双实例**：web profile 的 @deepseek-ai/* 符号链接指向 CLD runtime 是「同一物理模块」；若 pnpm 复制成独立副本才是双实例（guard 脚本自动替换）。peerDeps 在 profile「缺失」反而是安全态（解析链命中 runtime 单实例）。
8. **指纹锚点优先于解析链**：adapt.js `readHostVersion` 第一优先读 CLD runtime 显式锚点（文件直读），不依赖 profile 解析链——审查的「cordis MISSING」仅发生在模拟环境；真实环境 missing=0。加固：CLD 升级换路径时显式设 `DSH_RUNTIME_NODE_MODULES`。
6. **tree-shaking 掩盖**：import 未使用靠摇树不崩——悬空 import 必须删。
7. **写黑板必验证**：heredoc 展开破坏 JSON → 写后读回。

---

## 八、演进路线

- [x] v0.1 消息总线 + 红绿灯 + 档案
- [x] v2.1-v2.4 最短提示规范 + 工具层门禁（v2.4：warn→deny + 分级保留）
- [x] 跨设备：agent-msg/agent-thread + central-inbox 注入桥
- [x] 零轮询验证（mac↔MBP 3 轮纯注入通过）
- [ ] i9 官方 plugin 入口（对称注入第三端）
- [ ] 独立注入代理（若 i9 CLD 精简版）

---

*本文档基于源码 ~/dsh-plugin-agent-bus/lib/index.js（1514 行）逐行核对，含实测数据（646 线程/14MB 状态/19 工具/零轮询验证通过）。*
