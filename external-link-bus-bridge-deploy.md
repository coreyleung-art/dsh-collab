# 总线桥部署包 · bus-bridge（mac-mini 侧）

外链通讯员 session-92623479 · 2026-08-17
依据：协调者 fa1f9150 确认方案（总线桥部署在总线所在进程侧 = mac-mini）

## 组件
- `~/external-link-mcp/bus-bridge.js` — 总线桥服务（纯 Node，无外部依赖）
- 本文件 — 部署说明（部署方：mac-mini 运维会话，协调者安排）

## ⚠️ 部署前须知（协调者实测确认）
- **mac-mini 8790 已有 external-link-webhook 在运行**（PID 48060，绑定 127.0.0.1 仅本机）——bus-bridge **用 8791**，勿占 8790
- **必须绑定 0.0.0.0 或 100.120.203.20**（HOST 默认 0.0.0.0 已满足）——不能绑 127.0.0.1，否则 MBP 经 Tailscale 访问不到

## 部署步骤（在 mac-mini 上执行）
1. 拷贝服务文件到 mac-mini（路径建议 `~/external-link-mcp/bus-bridge.js`）：
   - 从 MBP `~/external-link-mcp/bus-bridge.js` 经可用通道（SSH/Tailscale scp/论坛附件）传输
   - 或直接粘贴源码（约 260 行，纯 Node）
2. 校验：`node --check bus-bridge.js` && `node --version`（需 Node ≥18）
3. 测试启动：`PORT=8791 WEBHOOK_TOKEN=<内部Token> node bus-bridge.js`（前台试跑，确认 5 端点可用）
4. 常驻：launchd plist（模板见下），或 `nohup node bus-bridge.js > /tmp/bus-bridge.log 2>&1 &`
5. 验证：`curl http://127.0.0.1:8791/health` → `{"ok":true,"service":"bus-bridge",...}`；MBP 侧 `curl http://100.120.203.20:8791/health` 应同样可达

## launchd plist 模板（com.external-link.bus-bridge.plist）
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.external-link.bus-bridge</string>
    <key>ProgramArguments</key>
    <array><string>/usr/local/bin/node</string><string>/Users/<用户名>/external-link-mcp/bus-bridge.js</string></array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PORT</key><string>8791</string>
        <key>WEBHOOK_TOKEN</key><string><内部Token></string>
    </dict>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>StandardOutPath</key><string>/tmp/bus-bridge.log</string>
    <key>StandardErrorPath</key><string>/tmp/bus-bridge.log</string>
</dict>
</plist>
```
`launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.external-link.bus-bridge.plist`

## 环境变量
| 变量 | 默认 | 说明 |
|---|---|---|
| PORT | **8791** | 监听端口（mac-mini 8790 已被 webhook 占用） |
| HOST | 0.0.0.0 | 全接口监听（Tailscale 内可达，**勿绑 127.0.0.1**） |
| WEBHOOK_TOKEN | 空 | X-Webhook-Token 鉴权（建议启用） |
| BUS_QUEUE_DIR | ~/.dsh/bus-queue | 队列目录（tasks/ + outbox/，0600） |
| BUS_ALLOWED_FROM | 空 | 来源白名单，逗号分隔（空=不限） |
| BUS_ALLOWED_ACTIONS | 空 | 动作白名单，逗号分隔（空=不限） |

## 端点契约
| 端点 | 方法 | 语义 |
|---|---|---|
| /bus/send | POST | 入队 {from,target,action,payload,ttl_sec} → {task_id}；`?wait=1` 长轮询等结果(≤30s) |
| /bus/receive | GET | 取任务（最老 queued→processing；`?target=` 过滤）→ {task} 或 {task:null} |
| /bus/reply | POST | 提交结果 {task_id,ok,result?,error?} → done/failed + 入 outbox |
| /bus/outbox | GET | 拉结果（`?task_id=`/`?from=`/`?since=`；`?consume=1` 拉后删） |
| /bus/status | GET | 统计 queued/processing/done/failed + recent 10 |
| /health | GET | 健康检查 |

## 消息格式
任务 body：
```json
{"from":"mac-mini","target":"mbp-agent","action":"resource.call","payload":{"resource":"flower-shop","op":"list"},"ttl_sec":3600}
```
reply body：
```json
{"task_id":"<uuid>","ok":true,"result":{"shop":"守白鲜花","count":10},"error":null}
```

## 本机自测记录（MBP，模拟 mac-mini 侧，PORT=18790）
- send→receive→reply→outbox 全链路 ✅（status 从 queued→processing→done，outbox 含 result）
- wait=1 长轮询：任务被 reply 时返回 done+result ✅；无人 reply 30s 超时返回 queued+拉取提示 ✅
- consume=1 拉后删除 ✅；TTL 过期自动 failed（懒清理）逻辑内置
- 白名单/鉴权逻辑内置（BUS_ALLOWED_FROM/BUS_ALLOWED_ACTIONS/WEBHOOK_TOKEN）

## 双向使用示意
- mac-mini 调用方（总线侧）：
  - 下发：`curl -X POST http://127.0.0.1:8791/bus/send -d '{"from":"mac-mini","target":"mbp-agent","action":"...","payload":{...}}'`
  - 拉结果：`curl "http://127.0.0.1:8791/bus/outbox?from=<我的设备>&consume=1"`
- MBP 侧 agent（资源侧，经 Tailscale 访问 mac-mini）：
  - 取任务：`curl "http://100.120.203.20:8791/bus/receive?target=mbp-agent"`
  - 回结果：`curl -X POST http://100.120.203.20:8791/bus/reply -d '{"task_id":"...","ok":true,"result":{...}}'`
