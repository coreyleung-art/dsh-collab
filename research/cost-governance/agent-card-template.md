# Agent Card 声明模板（CAHAC v1.0 §11）

> 建立：2026-08-19 · HR · 用途=各会话声明通信能力与预算，供 CAHAC 一致性校验（compliance-check 周检）
> 更新方式：agent_profile（abilities/resources 加声明字段）；示例=HR 已声明（见文末）

---

## 一、声明格式（JSON 五字段）

```json
{
  "cahac_version": "1.0",
  "channels": ["p2p", "blackboard", "mailbox", "eventbus"],   // 支持的通道（可子集）
  "topics": ["ops.status", "task.registry", "alert"],          // 订阅/写入的黑板主题
  "budget": {"day_tokens": 500000000},                         // 日预算（默认 500M）
  "comm_style": ["task", "collab"]                             // 通信风格：task/collab/status-only
}
```

## 二、各角色建议值

| 角色 | channels | topics | budget | comm_style |
|---|---|---|---|---|
| 协调者 | p2p+blackboard+eventbus | ops.status/task.registry/alert | 500M/day | task+collab |
| HR | p2p+blackboard+mailbox+eventbus | 全部 | 500M/day | task+collab |
| 运营 | p2p+eventbus+blackboard | alert/store.status | 500M/day | task+status |
| 设备协调 | p2p+blackboard | ops.status/task.registry | 500M/day | task |
| 摄取 | mailbox+blackboard | task.registry | 300M/day | status-only |
| QA | p2p+blackboard | task.registry/qa.status | 300M/day | task |
| 后台/子代理 | p2p（默认） | — | 100M/day | task |

## 三、落地动作

1. 各会话用 agent_profile 更新（abilities 加 "channels:..."; resources 加 "topics:...; budget:...; comm_style:..."）
2. HR 周检 compliance-check.py 扫描采纳率
3. 未声明=默认 p2p（向后兼容，不阻断）

## 四、HR 示例（已声明 2026-08-19）

```json
{ "role": "HR 驾驶舱（资源管理者）· CAHAC 示范",
  "abilities": ["...成本治理...", "...协议治理（CAHAC 通道/回执纪律）...", "channels:p2p+blackboard+mailbox+eventbus"],
  "resources": ["...", "budget:500M/day", "topics:ops.status/task.registry/alert/cost", "comm_style:task+collab"] }
```

---
*Agent Card 模板 v1.0 · HR · 2026-08-19 · 配套 cahac-compliance-check.py*