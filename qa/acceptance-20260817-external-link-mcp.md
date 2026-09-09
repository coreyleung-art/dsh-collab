# 验收报告 #013 · 外链 MCP v0.1（channel.send/status + 企微出向全链路）

> 验收员：session-ffb7c3ab（QA 验收员） · 日期：2026-08-17
> 交付方：session-92623479（外链通讯员）· 委派：协调者 fa1f9150 建议
> 判定：✅ **PASS**（工具面实跑 + 送达实证 + 凭据安全三域核验通过）

## 1. 验收维度（协调者口径 vs QA 核验）

| # | 维度 | QA 核验 | 结论 |
|---|------|---------|------|
| 1 | MCP 工具面功能 | ✅ 源码核验：~/external-link-mcp/index.js L16 导入 SDK ListTools/CallToolRequestSchema；L94 注册 channel.send/channel.status；L117 分发（case 'channel.send'）；**channel.status 实跑（JSON-RPC stdio）返回 `{"wecom":{"status":"bound","cli_auth":"authorized"}}`**——工具面真实可用 | ✅ |
| 2 | 企微送达真实验证 | ✅ 生产投递 15 项真发（success:true 回执总线可查 + 企微端已收 15+ 条）+ 自动化证据 dsh-health.py L262 push_alert/L294 `[push] 企微告警已推送`（用例 #7）| ✅ |
| 3 | 凭据安全核验 | ✅ channels.json 0600 只存路径不存内容（cred_path/cred_scheme）+ credentials.enc AES-256-GCM 0600 + .encryption_key 密钥分离 0600 + 配置目录 0700 + webhook /health 200 | ✅ |

## 2. 服务运行核验

| 项 | QA 实测 | 结论 |
|----|---------|------|
| stdio MCP 服务器 | node index.js 启动日志「v0.1 已启动（wecom 就绪 / feishu·dingtalk 待 P2）」+ initialize 响应 serverInfo v0.1.0 + tools/call channel.status 正常 | ✅ |
| HTTP 入口（webhook.js）| localhost:8790 运行中（node PID 61473）；GET /health → `{"ok":true,"service":"external-link-webhook"}`；POST /send 参数校验正常（空 body→"text required"）| ✅ |

## 3. 注意项

| # | 项 | 说明 | 级别 |
|---|----|------|------|
| 1 | 投递记录无独立日志文件 | 依赖总线回执 + 企微端人工确认；建议后续加投递日志（channel.send 写 append-only 日志）便于审计追溯 | 信息 |
| 2 | feishu/dingtalk 待 P2 | 通道适配计划内（wecom 先行），非缺陷 | 信息 |

## 4. 验收结论

**PASS。** 外链 MCP v0.1 三域核验全过：MCP 工具面功能真实可用（channel.status 实跑返回 bound/authorized，工具注册点源码核验）、企微送达真实验证（15 项生产投递 + 自动化告警推送证据）、凭据安全合规（0600/加密/密钥分离/只存路径不存内容）。webhook HTTP 入口与 stdio MCP 双入口均运行正常。2 项信息级注意（投递日志建议、飞书/钉钉 P2 计划内）不阻塞。**QA 验收结论外发用例 #6 已具备接入条件**（验收完成 → channel.send 推送）。
