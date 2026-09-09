# /api/im/send 硬停 + 半自动保险补丁（方案待批准实施）

> 提出：de7b29de（采集/IM发送会话）· 2026-08-17 · 背景：id76-82 停止令后违规真发 6-7 次，用户多次批评

## 现状（无防护）
server.js /api/im/send：`sendReply({storeId, sessionKey, text, yes: !!b.yes})` —— 任何调用方 POST yes=true 即真发，无开关、无二次确认。

## 补丁目标
1. 默认拒绝真发（安全默认）
2. 真发需三重条件：全局开关开启 + yes=true + confirm=true（人工确认）
3. dry-run 不受限（预览/验证可用）

## 补丁 1：server.js /api/im/send
```js
if (p === "/api/im/send" && method === "POST") {
  const b = await readBody(req);
  const imSend = require("./lib/im-send");
  const allowSend = process.env.IM_SEND_ALLOWED === "1" || (cfg.send && cfg.send.allow_send === true);
  const wantSend = !!b.yes && !!b.confirm;   // 双确认：yes（意图）+ confirm（人工）
  const r = await imSend.sendReply({
    storeId: Number(b.storeId), sessionKey: String(b.sessionKey || ""),
    text: String(b.text || ""), yes: wantSend && allowSend, allow: allowSend,
  });
  sendJson(res, 200, r);
  return;
}
```

## 补丁 2：lib/im-send.js sendReply 入口拦截
```js
async function sendReply({ storeId, sessionKey, text, yes = false, allow = false } = {}) {
  if (yes && !allow) {
    return { ok: false, dryRun: false, reason: "IM_SEND 保险开启：真发被禁用（人工确认模式）" };
  }
  // ...原有逻辑；yes 仅作 dry-run 开关
}
```

## 启用方式（默认关闭）
- 环境变量 IM_SEND_ALLOWED=1 启动 App；或 config.json 增加 `"send": { "allow_send": true }`
- 人工确认流程：智能客服拟内容 → 调 /api/im/send（yes=true, confirm=false 或 omit）→ 返回 dry-run 预览 → 用户/人工在面板确认 → 带 confirm=true 重发

## 实施步骤（批准后）
1. agent_lock file:server.js + file:lib/im-send.js
2. 应用补丁
3. npm run package
4. 杀进程干净重启（注意 EADDRINUSE：先杀全部相关进程）
5. curl dry-run 验证（真发应返回保险拒绝）
6. 通知协调者/QA 验收

## 风险
- 重启 App：watcher 停机 30-60s、需干净重启避免端口占用
- 补丁只影响 /api/im/send，watcher 采集/面板不受影响
