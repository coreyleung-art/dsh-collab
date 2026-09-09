# 双向注入修复报告（SSE 广播断链 → 全链路打通）

> 记录：2026-08-28 ｜ 中枢 fa1f9150 ｜ FlowerNet 蓝图 M1 · 双向注入验收
> 关联：M1 验收标准「三端 [agent-bus] 加载 + 双向注入」· 可靠性审计

---

## 一、背景

M1 里程碑验收要求**双向注入**（mac↔MBP 黑板消息注入对方本地会话）。实测中发现链路不通：
- mac-mini 写 `notes/mbp/*` → MBP central-inbox 应收到并注入会话 → 但 **verify-mbp-ack 从未更新**（停在 06:32 旧值）
- MBP 智能体自主诊断出 boot 时序 bug（centralAgent=null）+ DSH_NODE_ID bootstrap-only 问题，但修复后仍不注入

## 二、根因链（三层 bug 叠加）

### 根因 1（最底层）：黑板 SSE 广播断链
**rust-blackboard v0.6.0 缺陷**：`do_put`（写入主路径，8792 PUT）只调 `store.put`，**未调 `sse::broadcast`**。

```rust
// 修复前（http.rs do_put）
let (ver, seq) = store.put(&full, value, writer);   // ← 只存不广播
```

`broadcast` 只被 `handle_cb` 调用（SSE 端口 `POST /cb`），但 central-inbox 用 `GET /events` 订阅——**没人 POST /cb** → SSE 客户端只收到 `hello` + `ping`，**永远收不到 `change` 事件**。

**影响**：所有跨设备注入全断（不只是 MBP，i9 同样）。

**修复**（http.rs）：
```rust
let (ver, seq) = store.put(&full, value.clone(), writer);
crate::sse::broadcast(&full, Some(&value), ver);  // ← 补广播
```

**验证**：修复版实测——curl 订阅 `GET /events` → 写入 → 收到 `event: change` 携带完整 key/value ✅

### 根因 2：MBP central-inbox 自注入循环（自回声）
MBP 的 central-inbox 监听 `notes/mbp/*`，但**无自注入防护**：
- MBP 收到 `ask-hello` → LLM 自动应答 → 写 `notes/mbp/llm-reply-*-ask-hello` → 自己的 central-inbox 又注入 → 又应答 → 又写……
- 历史上出现 `llm-reply-llm-reply-...` 嵌套 key（无限增长）+ ~2693 次版本递增
- mac-mini 有防护（`value.from==='coordinator'` 跳过），MBP 缺失

**修复**（MBP 自主完成）：central-inbox handleEvent 加
```js
if (value.from === NODE_ID) return;  // 本节点自写消息不注入回本会话
```
已同步两个副本 + `.bak-self-inject` 备份 + `node --check` 通过。

### 根因 3：mac-mini 侧黑板写入格式错误
我（mac-mini）写黑板用 `{"value": {...}}` 包装，但黑板 PUT 协议 **body 整体就是 value**（扁平）：
```rust
// http.rs L182：body 直接当 value 存
let value: Value = serde_json::from_slice(&req.body).unwrap_or(Value::Null);
```
→ 存成 `value: {value: {...}}` 双层 → MBP 读 `value.from` 是 undefined（实际在 `value.value.from`）。

**修复**：改用扁平 body `{"body":..., "from":..., "ts":...}`。验证：`value.from: probe2` 正确读取 ✅

## 三、辅助修复

| 项 | 问题 | 修复 |
|----|------|------|
| verify-watch 探针刷屏 | 每 5 分钟发 `notes/mbp/verify-recovery-*`（累计 256+ 条），central-inbox 全注入造成排队刷屏 | 探针改为仅记录不写黑板（链路已通，探针使命完成）|
| central-inbox 探针过滤 | verify-*/sse-probe 类消息不应注入业务会话 | mac-mini 源码加过滤（跳过 verify-*/verify-recovery/sse-probe）|

## 四、验证证据链

| 验证 | 结果 |
|------|------|
| 黑板 SSE 广播修复 | ✅ `event: change` 携带完整 key/value（curl 订阅实测）|
| MBP SSE 连接建立 | ✅ 8803 上出现 `desktop-p8e7op1.taild3fd86.ts.net` 连接 |
| mac→MBP 注入 | ✅ MBP 回报「收到 mac→MBP 注入 ✅」（verify-mbp-ack-final 02:20:04）|
| MBP 自注入防护 | ✅ MBP 修复报告 + `node --check` 通过 |
| 扁平写入格式 | ✅ `value.from: probe2` 正确读取 |
| 无新循环 | ✅ llm-reply 嵌套 key 停止增长 |

## 五、环境变量要点（MBP central-inbox 配置）

- `DSH_NODE_ID=mbp`：**bootstrap-only 变量**（`DSH_` 前缀在 BOOTSTRAP_PREFIXES 禁止名单）→ **禁止放 .env**，只能 shell/launchctl 注入
- `CENTRAL_INBOX_SSE=http://100.120.203.20:8803/events`：`CENTRAL_` 前缀**非禁止** → 可放 .env
- `CENTRAL_AGENT=<会话id>`：非禁止 → 可放 .env

**重要**：`~/.dsh/.env` 里放 `DSH_NODE_ID` 会导致 CLD 启动崩溃（dsh-app-boot `isBootstrapOnly` 抛错）。已从 .env 移除，改用 launchctl setenv。

## 六、遗留/待办

- [ ] MBP 重启 CLD 让自注入防护生效（已发确认请求，待回报）
- [ ] MBP/i9 central-inbox 同步探针过滤（噪音防护）
- [ ] i9 双向注入验证（同链路，黑板 SSE 已修）
- [ ] MBP central-inbox 修改合入主仓库（git URL 安装的是副本，修复未回源）
- [ ] 黑板 PUT 协议格式文档化（body=value 扁平，无 value 包装）

## 七、经验教训

1. **SSE 广播是跨设备注入的命门**：写入端必须广播，订阅端才有事件。写端只存不广播 = 订阅端静默失联（连错误都没有）。
2. **bootstrap-only 变量红线**：`DSH_*` / `PATH` / `NODE_OPTIONS` 等禁止 .env，只能启动环境注入——踩坑即 CLD 崩溃。
3. **黑板 PUT body=value 扁平**：不要包 `{"value":...}`，否则多一层嵌套，下游取值错位。
4. **自注入防护是每个节点必备**：central-inbox 必须跳过本节点自写消息（`value.from===NODE_ID`），否则 LLM 自动应答形成无限回声。
5. **设备自主修复可行**：MBP 智能体收到黑板指令后自主完成诊断→修复→回报全链路，无需人工逐命令操作（用户只做重启动作）。

---
*关联：M1 里程碑 / FlowerNet 主蓝图 v4.0 P2-4 / 黑板协议 / central-inbox / rust-blackboard*
