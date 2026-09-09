# 星台会话级切换架构 v1（v9.7 · 用户定案完整版 2026-09-04）

> 需求：星台左滑抽屉 → 设备内智能体会话列表 → 允许切换对话对象
> 用户原话：「顶部=在线设备切换；左折叠页面=设备内智能体切换」

## 一、现状（机制约束）

| 层 | 现状 | 约束 |
|---|---|---|
| 设备切换 | 已通（标题 Menu → 桥 target 路由 → notes/<node>/sb-dialog） | 目标=该节点「总线」，不精确到会话 |
| 会话注入 | central-inbox 把 notes/<node>/* 全注入**本节点中枢会话**（CENTRAL_AGENT/fa1f9150） | ❌ 不支持按 to:会话id 定向注入 |
| mac-mini 会话池 | agent-bus.json profiles 52 个（真实会话：星桥/明鉴/老登/守灯塔…） | 可作会话清单数据源 |

## 二、目标架构（三层）

```
星台 App
 ├─ 顶部 Menu：设备切换（mac-mini / MBP / i9）——已有
 └─ 左滑抽屉：设备内会话列表 → 点选切换对话对象（新）
       ↓ target=设备 + session=会话id
星台桥 :8820 /api/chat（带 target + to）
       ↓ 黑板卡 {target, to:会话id, text}
central-inbox v2（改造：按 to 定向注入）
       ├─ to 为本机会话 → agentBus.send(来源, to会话, text)   ← 新增
       └─ to 为空/中枢 → 注入中枢会话（现逻辑保留）
```

## 三、分阶段实施

### P1 桥层会话路由（mac-mini 侧，先做）
- [ ] `/api/devices` 扩展：每设备返回 agents[]（mac-mini 从 agent-bus.json profiles 读 52 会话，含 role；MBP/i9 先返回 [{id:"bus",role:"总线"}] 占位）
- [ ] `/api/chat` 支持 `to` 字段：`to=会话id` 时黑板卡带 to
- [ ] 会话白名单：只允许 to=星桥已知角色（防乱注）

### P2 central-inbox 定向注入改造
- [ ] central-inbox 读事件 value.to → to 匹配本机会话且非中枢 → 注入该会话
- [ ] 会话存在性检查（agentBus 会话列表）
- [ ] 注入后回报：写 notes/<node>/mobile-reply/latest-<session>（星台按会话轮询）
- [ ] 防回声 + 去重保留

### P3 App 左滑抽屉
- [ ] 左边缘滑入手势（drag from leading edge）→ 抽屉面板
- [ ] 显示当前设备 agents[]（星桥/明鉴/老登… + 总线入口）
- [ ] 点选 → model.currentAgent 切换 → 发送带 to
- [ ] 每会话独立轮询（reply?session=<agent>）+ 独立历史
- [ ] 抽屉顶部显示设备切换入口（呼应顶部 Menu）

### P4 跨设备会话清单上报
- [ ] MBP/i9 侧上报 agents 清单（各端 agent-bus profiles）→ nodes/<node>/agents-registry
- [ ] 桥 /api/devices 合并各端上报 → 完整会话树

## 四、验收
- [ ] A1: mac-mini 抽屉列出真实会话，点「老登」发消息 → 注入老登会话 → 回复显示在星台（定向注入通）
- [ ] A2: 不选会话（默认）→ 仍注入星桥中枢（回归不破）
- [ ] A3: 切 MBP → 抽屉显示 MBP 会话（P4 后）
- [ ] A4: 每会话历史独立持久化

## 五、风险
- central-inbox 是 shared 部署插件 → 改造需先沙箱/副本验证（J37）
- 会话 id 变化（重启后新 id）→ 用 agentId 稳定段匹配
- 定向注入其他会话 = 跨会话唤醒 → 遵循红绿灯（目标会话忙则排队）
