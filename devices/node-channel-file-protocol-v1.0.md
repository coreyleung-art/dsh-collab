# 节点通道与文件约定协议 v1.0（mac-mini 中枢 × i9 节点）

> 目的：解决「每次升级迭代砸了旧对讲机、对空气说话」的问题——**通道/文件约定一次性固化，升级只加兼容、不换通道**
> 适用：mac-mini 协调者（fa1f9150）× i9 节点（DESKTOP-P8E7OP1）· 2026-08-25
> 原则：**已约定通道永久有效；新增能力走新键，但旧键必须保持应答（兼容不替换）**

---

## 一、通道约定（消息走哪）

### 1.1 存活探测（唯一标准）
```
通道: nodes/{node}/heartbeat
规则: 60 秒内新鲜 = 在线
禁止: 不用 tasks/{node}/cmd、不用 node-agent 进程判断（旧架构已废）
```

### 1.2 任务下发（中枢 → 节点）
```
通道: tasks/{node}/queue/{ts}          ← 新标准（v6 executor 轮询此）
兼容: tasks/{node}/cmd                  ← 旧通道仍应答（check_legacy_cmd）
动作: 只发执行类 action:
      shell | info/status | scan | dsh | ollama
禁止: 发 notify/message 类（executor 不处理，会 unknown action）
```

### 1.3 任务回报（节点 → 中枢）
```
通道: tasks/{node}/result               ← 节点回报写这里（永远不变）
历史: tasks/{node}/results/{seq}        ← 历史回报（可查）
```

### 1.4 消息对话（节点 DSH 智能体）
```
通道: notes/{node}/*                    ← 消息/状态/汇报写这（i9 侧 DSH 智能体）
约定: 节点发消息 → PUT notes/{node}/<topic>
      中枢回复 → PUT notes/{node}/coordinator-<topic>
禁止: 消息类动作走 tasks/{node}/queue（executor 不认 notify）
```

### 1.5 中枢 → 节点的「消息」（非任务）
```
方式: 写 notes/{node}/coordinator-*（节点 DSH 智能体订阅 notes）
不写: tasks/{node}/queue 的非执行动作（会 unknown action）
```

---

## 二、文件约定（什么文件放哪）

### 2.1 黑板命名空间（节点侧文件）
```
nodes/{node}/              ← 节点注册 + 心跳
tasks/{node}/              ← 任务卡 + 回报
notes/{node}/              ← 消息/状态/汇报（DSH 智能体对话）
data/{node}/               ← 业务数据/成果/迭代报告
data/{node}/share/         ← 共享产物 manifest（如考古 manifest）
data/{node}/iterations/    ← 迭代报告/讨论
```

### 2.2 本地文件（节点侧磁盘）
```
E:/My vibe codding/                    ← i9 工作区（项目/官网/考古）
E:/My vibe codding/doc/memory/         ← i9 考古/记忆沉淀
C:/（系统）                             ← 系统级（不经黑板）
```

### 2.3 中枢侧文件（mac-mini）
```
~/dsh-collab/research/zhaoshang-ppt-2026-08-25/   ← 招商/资本化素材
~/dsh-collab/devices/                             ← 节点接入脚本/Prompt/协议
~/dsh-collab/scripts/                             ← 工具脚本
```

### 2.4 升级迭代的兼容规则（核心）
```
① 新能力 → 用新键（如 tasks/{node}/queue 替代 cmd）
② 旧键保持应答（cmd 兼容 check_legacy_cmd）——不砸旧对讲机
③ 通道变更 → 必须先在黑板 notes/collab/channel-change 公告 + 双端确认
④ 任何一端发现通道不通 → 先查协议文档，不发明新通道
```

---

## 三、双端职责

### mac-mini 协调者（我）
```
- 秒级轮询: i9-poll-seconds.py（2s 查 result + cmd）常驻
- 事件订阅: i9-monitor-sub.py（tasks/i9/* 实时）常驻
- 任务下发: 只走 tasks/i9/queue/{ts}（执行类动作）
- 消息对话: 写 notes/i9/coordinator-*（不写 queue 的 notify）
- 收到回报: 更新进度/归档
```

### i9 节点
```
- 心跳: nodes/i9/heartbeat（60s）
- 队列轮询: tasks/i9/queue/（秒级）
- 任务回报: 写 tasks/i9/result
- 消息汇报: 写 notes/i9/*（DSH 智能体）
- 兼容: tasks/i9/cmd 保持应答
```

---

## 四、测试记录（2026-08-25 验证）

| 通道 | 测试 | 结果 |
|---|---|---|
| nodes/i9/heartbeat | 存活探测 | ✅ 60s 标准 |
| tasks/i9/queue/{ts} | 发 shell 任务 | ✅ i9 秒级消费执行回报 |
| tasks/i9/result | 读回报 | ✅ 实时（我 2s 轮询 3s 内抓到）|
| tasks/i9/cmd | 旧通道兼容 | ✅ check_legacy_cmd 应答 |
| notes/i9/* | 消息（待测） | ⚠️ 需确认 i9 DSH 智能体订阅 |

---

## 五、变更记录
- v1.0（2026-08-25）：首版固化。核心=任务走 queue、回报走 result、消息走 notes、存活看 heartbeat；升级只加键不换通道。
