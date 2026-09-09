# 智能体黑板订阅模式 v1.0（事件驱动泛化）

> 日期：2026-08-23 · 协调者 fa1f9150 · 把黑板事件驱动泛化到所有本地智能体
> 组件：黑板 8792（KV + SUBSCRIBE）+ 黑板事件桥 8803（回调→SSE）+ sse-sub（客服实现，智能体订阅器）

## 一、架构（泛化模式）

```
黑板 8792（存储 + SUBSCRIBE 回调）
  │ 变更 → POST 回调（已订阅 tasks/ + notes/ + data/）
  ▼
黑板事件桥 8803（blackboard-events.py，常驻）
  │ SSE 广播（/events 长连接）
  ▼
各智能体 sse-sub（订阅 http://127.0.0.1:8803/events）
  │ 按 key 前缀分发（tasks/* / notes/* / data/*）
  ▼
事件驱动处理（零轮询，空闲零成本）
```

## 二、智能体怎么用（通用步骤）

```bash
# 1. 用 sse-sub 订阅黑板事件流（配置式）
sse-sub --url http://127.0.0.1:8803/events --config my-sub.json

# 2. 配置（my-sub.json）——按自己关注的 key 前缀分发
{
  "url": "http://127.0.0.1:8803/events",
  "handlers": [
    {"match": "tasks/central/queue/*", "handle": "on_central_task"},
    {"match": "notes/*", "handle": "on_note"},
    {"match": "data/recovery/*", "handle": "on_recovery_update"}
  ]
}

# 3. 事件到达 → 触发处理函数 → 业务逻辑
```

## 三、各智能体订阅建议（按职责）

| 智能体 | 订阅前缀 | 用途 |
|---|---|---|
| 协调者 | tasks/<node>/results/* · tasks/central/queue/* · data/genebank/* | 收回报/收节点消息/收基因注册 |
| HR | data/recovery/* · data/i9/config · notes/* | 恢复状态/配置变更/通知 |
| 客服 | tasks/central/queue/*（用户消息提审结果） | 收中枢消息 |
| 运营 | tasks/<node>/results/*（差评/日报回报） | 收执行结果 |
| i9 节点 | tasks/i9/queue/* · notes/i9/* | 收派单/收通知 |

## 四、与轮询的关系

- **订阅为主**：高频/实时路径用 sse-sub（事件驱动，零轮询成本）
- **轮询兜底**：订阅不可用/一次性低频查询用轮询
- 已接入：黑板全事件流（tasks/notes/data）→ 桥 → SSE

## 五、收益

1. **零轮询成本**：所有智能体事件驱动，空闲零 HTTP（复用 sse-sub 已验证范式）
2. **单连接共享**：桥单点广播，多个智能体共享一个事件流（不用各自连黑板）
3. **泛化**：任何本地智能体订阅自己关注的 key 前缀即可，不重复实现
4. **异步并发**：黑板变更即时推送（配合双向队列 v2.0 + 并发回报）

## 六、组件清单

- `scripts/blackboard-events.py`（桥，:8803，常驻）
- `~/dsh-collab/im-reply/tools/sse-sub.js`（订阅器，客服实现）
- 黑板 `SUBSCRIBE`（tasks/notes/data → 桥）

## 七、验证

端到端实测：写 tasks/i9/queue/777 + notes/test/hello → SSE 客户端收到 change 事件（含 key/value）✅

---

# 补充：sse-sub v2（黑板事件格式支持）

> 2026-08-23 · 客服 b193c782 升级 · 解决 v1 按 d.type 分发与黑板事件 {key} 不匹配

## v2 双模式自动识别

```
事件有 d.key → keyPrefix 分发（黑板事件格式 {key,value,version,ts}，按 key 前缀匹配）
事件有 d.type → events 分发（面板事件格式，按 type 匹配）
→ 无缝兼容黑板事件桥 + 面板 SSE 两种源
```

## v2 用法（--keyPrefix）

```bash
sse-sub --url http://127.0.0.1:8803/events --keyPrefix 'data/recovery/*' --handle on_recovery
# 或多个前缀：--keyPrefix 'tasks/i9/queue/*' 'notes/*'
```

## 配置示例（黑板事件格式）

```json
{
  "url": "http://127.0.0.1:8803/events",
  "keyPrefix": ["data/recovery/*", "tasks/i9/queue/*", "notes/*"],
  "handlers": {
    "on_match": "读 event.key + event.value → 按职责处理",
    "on_unknown": "仅记录（被动模式）"
  }
}
```

## 收益

- 6ed4daf2 的 recovery-sub（自写适配）可改用标准 sse-sub v2（keyPrefix data/recovery/）
- 后续 HR/运营/QA 等订阅黑板免各自适配（keyPrefix 即可）

---
*智能体黑板订阅模式 v1.0 + sse-sub v2 补充 · 协调者 2026-08-23*
