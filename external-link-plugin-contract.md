# 外链插件化 · 接口契约（R3 开发输入）

> 提供：外链通讯员 session-92623479 · 2026-08-17
> 用途：R3 插件化（策略配置 UI + 分级统计面板 + channel.send 抽象）的开发契约
> 原则：复用 external-link-mcp 现成引擎（非自研），插件壳聚焦可视化与统计

---

## 一、复用资产（插件后端可直接调用）

| 资产 | 路径 | 说明 |
|------|------|------|
| HTTP 引擎 | `~/external-link-mcp/webhook.js` | 分级分流引擎（P0-P3 + 白名单 + 去重 + P2 队列），监听 127.0.0.1:8790 |
| MCP 壳 | `~/external-link-mcp/index.js` | channel.send / channel.status（stdio MCP） |
| digest 汇总 | `~/external-link-mcp/digest-flush.js` | P2 队列 → 每日汇总推送 |
| 通道状态 | `~/.dsh/channels.json`（0600） | 企微绑定状态（bound/bot_id） |
| 投递日志 | `~/.dsh/external-link.log`（0600） | append-only 投递/拦截/汇总记录 |
| P2 队列 | `~/.dsh/p2-digest-queue.jsonl`（0600） | P2 消息待汇总 |
| 策略文档 | `~/dsh-collab/external-link-policy.md` | P0-P3 模型/分流表/用例分级 |

## 二、HTTP 接口契约（webhook.js）

### POST /send
```json
请求: {
  "channel": "wecom",        // 可选，默认 wecom
  "text": "markdown 内容",    // 必填
  "target": "可选",           // 默认创建者 userid
  "level": "P0|P1|P2|P3",    // 可选，未填按来源推断/默认 P2
  "source": "来源标识",        // 可选，白名单推断级别
  "priority": "now",         // 可选，P2 显式即时
  "dedup": "指纹"             // 可选，10 分钟去重
}
响应: {
  "ok": true, "action": "send", "level": "P0"  // send 路径
  {"ok": false, "action": "block", "level": "P3", "reason": "..."}  // 拦截
  {"ok": false, "action": "digest", "level": "P2", "note": "..."}   // 入汇总
  {"ok": false, "action": "block", "reason": "10 分钟内重复（去重）"}  // 去重
}
```

### GET /health
```json
{"ok":true,"service":"external-link-webhook","ts":...}
```

## 三、分级引擎逻辑（插件 UI 需可视化）

### 级别判定（优先级从高到低）
1. 显式 `level` 字段（P0-P3）
2. 来源白名单推断：
   - P3 强制拦截源：`dsh-health / health-check / cld-watchdog / sysops / dependency-internal / claude-automation / launchd`
   - P1 允许源：`waimai / insight / learning / qa / plugin / ops / user-insight / supply-chain / media / ci`
3. 默认 P2（参考，入汇总队列）

### 分流决策
| 级别 | 动作 | 说明 |
|------|------|------|
| P0 | send | 立即推送（生意/资金/安全） |
| P1 | send | 定时/事件推送（用户关注交付） |
| P2 | digest | 入每日汇总队列（18:00 推送） |
| P3 | block | 拦截仅本地日志（系统运维） |

### P3_OVERRIDE（用户显式放行）
环境变量 `EXLINK_P3_OVERRIDE=source1,source2` 可放行 P3 源（如用户点名要推的运维项）

## 四、统计面板数据源（R3 分级统计）

### 投递日志 external-link.log 每行 JSON：
```json
{"ts":"ISO时间","type":"send|block|digest-queued|digest-flush|error",
 "level":"P0-P3","levelBy":"explicit|source-blocklist|source-allowlist|default",
 "channel":"wecom","source":"来源","target":"userid","ok":true|false,
 "errmsg":"可选","textPreview":"前120字"}
```

### 统计指标（面板展示）
| 指标 | 来源 | 计算 |
|------|------|------|
| 总投递数 | type=send 且 ok=true | 计数 |
| 拦截数（按级别） | type=block | 按 level 分组计数 |
| P2 汇总队列数 | p2-digest-queue.jsonl 行数 | 计数 |
| 推送失败数 | type=send 且 ok=false | 计数 |
| 分级分布 | 所有 type 的 level 字段 | 分布 |
| 来源 Top | source 字段 | 分组计数 |
| 去重命中 | type=block reason 含"重复" | 计数 |

## 五、策略配置 UI（R3 可配置项）

| 配置项 | 当前值 | 说明 |
|--------|--------|------|
| P3 拦截源列表 | 7 个源 | 可增删（改 webhook.js P3_SOURCES） |
| P1 允许源列表 | 10 个源 | 可增删（改 P1_SOURCES） |
| P3 放行例外 | EXLINK_P3_OVERRIDE env | 用户点名放行的运维源 |
| 去重窗口 | 10 分钟 | 可调（DEDUP_WINDOW_MS） |
| digest 时间 | 18:00 | launchd 调度（com.external-link.digest.plist） |
| 鉴权 token | WEBHOOK_TOKEN env | 云端暴露时启用 |

## 六、channel.send 抽象（插件暴露给各会话）

```
channel.send({ channel, text, target?, level?, source?, priority?, dedup? })
→ { ok, action: 'send'|'block'|'digest', level, reason? }
channel.status() → { wecom: { status, app_id, cli_auth } }
```

---

*接口契约 v1.0 —— R3 插件化开发输入，各会话/插件按此对接*
