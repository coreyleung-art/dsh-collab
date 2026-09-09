# 可控自动化发送 · 设计方案（用户决策：继续研究可控自动化）

> 提出：de7b29de（采集/IM会话）· 2026-08-17 · 状态：设计定稿，待用户解除停止令后实施
> 前提：用户停止令有效——本方案仅为设计，一切真发冻结

## 一、目标
自动发送内容**必须等于**期望文本（消除残留内容风险：preview=旧文本/React tracker 竞争）+ 发送内容经**总线 agent 审核**后才可触发。

## 二、实施方向①：内容完整性硬闸（im-send.js）

### 2.1 发送前校验（注入后、点发送前）
```js
// 3b 注入完成后：
const injected = await cdp.evaluate("读取 chatInputTextarea.value");
if (injected !== text) {
  cleanup();
  return { ok: false, reason: "内容完整性校验失败：输入框≠期望文本（残留风险）", injected: injected.slice(0, 30) };
}
// 相等才继续点发送
```
- **不等 → 立即中止**，不点发送按钮（残留内容永远不会发出去）
- 相等 → 继续发送流程

### 2.2 发送后校验（点击发送后、watcher 验收前）
```js
// 3d 后：读消息区最后一条 staff 消息
const lastMsg = await cdp.evaluate("读 [class*='message-wrapper'] 内 text-message 的最后一条");
if (lastMsg !== text) {
  // 不等：标记失败 + P1 告警（即使输入框已清空）
  addAlert(storeId, { kind: "im_content_mismatch", severity: "high", detail: { expected: text, actual: lastMsg } });
  return { ok: false, reason: "发送后内容不一致（已告警）" };
}
```
- **不等 → 失败 + 告警**（及时发现，不视为成功）

### 2.3 与闸门4（watcher 验收）衔接
- 硬闸（DOM 实时校验）→ 闸门4（watcher 采集回写）双层确认
- 硬闸失败不进入 watcher 验收等待（快速失败）

## 三、实施方向②：总线 agent 审核层（approval_token 升级）

### 3.1 现状
- approval_token 是共享字符串（config.send.approval_token）——调用方拿到即无限使用，无法承载「审核通过」语义

### 3.2 升级：HMAC 内容绑定 token
```js
// lib/approval.js
const crypto = require("node:crypto");
function issueToken(secret, { storeId, sessionKey, text, ts }) {
  const payload = [storeId, sessionKey, text, ts].join("|");
  const sig = crypto.createHmac("sha256", secret).update(payload).digest("hex");
  return { token: sig, ts };   // token 绑定内容+时间
}
function verifyToken(secret, token, { storeId, sessionKey, text }) {
  // 校验签名 + ts 新鲜度（≤10min）
}
```
- **审核 agent（b193c782）**在总线审核通过后，用 secret 生成 token（含内容绑定）
- 调用 /api/im/send 传 token —— server 校验签名+内容匹配+新鲜度
- **防重放/防篡改/防滥用**：token 与内容绑定，改内容即失效

### 3.3 审核流程（总线内）
```
智能客服拟稿 → 总线发审核请求（内容+目标会话）→ 审核 agent（b193c782 或指定）审 → 通过则发 token 给调用方 → 调用 /api/im/send（带 token）→ server 校验 → 硬闸校验 → 发送 → watcher 验收
```

## 四、实施方向③：六道闸门衔接（已落地）
- 闸门2（禁止词拦截）在硬闸之前（内容校验前置）
- 闸门3（token）升级为 HMAC 内容绑定（3.2）
- 闸门4（watcher 验收）保持（最终事实）
- 闸门5（频率/重试）保持
- 闸门6（污染告警）增加 content_mismatch 告警类型

## 五、实施顺序（恢复后）
1. lib/approval.js（HMAC token 生成/校验）+ 单测（node --test 或手写断言）
2. im-send.js 硬闸（2.1/2.2）——dry-run 可验证（不落区）
3. server.js 接入 token 校验升级
4. 集成验证：dry-run 全链路 → 1 条闭环验收（用户确认）→ 逐条确认

## 六、安全边界
- 停止令解除前：不部署、不测试、不触发
- 硬闸保证：即使代码 bug，残留内容也不会发出（输入框不等即中止）
- token 绑定内容：即使 token 泄露，改内容即失效
