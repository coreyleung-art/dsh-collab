# 重启救援协议 v1.0（Restart Rescue Protocol）

> 2026-08-29 星桥-mac-mini-协调者 · 用户指示：互为救援设备，重启前准备标准化——重启方留准备信息给救援方观察，有问题再救援；先约定救援过程和方式，禁止破坏性操作
> 依据：既有「互为外部救援设备」约定 + CCEP 永续通讯 + R011 强制门 + R012 完整体 + verify-watch 单向观察经验

## 一、原则

1. **互为救援**：三台设备（mac-mini 中枢 / MBP / i9）互为救援对象和施救方，互为外部救援设备
2. **重启方留档**：重启方在重启前，把「准备重启信息」写入黑板，供救援方观察
3. **救援方观察**：救援方监控重启方状态（心跳/日志/进程），发现问题才介入
4. **禁止破坏性**：救援方只能执行非破坏性救援动作（只读诊断/拉日志/重启服务），禁止删数据/改配置/清缓存等破坏性操作
5. **先约定后执行**：救援过程、方式、边界在重启前已约定（本文档），不在救援中临时决定

## 二、角色定义

| 角色 | 定义 | 责任 |
|------|------|------|
| 重启方（Restarter）| 要重启的设备 | ① 重启前留准备信息 ② 执行重启 ③ 重启后回报状态 |
| 救援方（Rescuer）| 另一台在线的设备 | ① 观察重启方状态 ② 发现问题发救援信号 ③ 经授权执行非破坏性救援 |
| 协调者（Coordinator）| mac-mini 中枢 | ① 维护救援协议 ② 仲裁救援动作 ③ 记录救援事件 |

**救援对**（互为）：mac-mini ↔ MBP ↔ i9（任意两台互为救援）

## 三、重启前准备（重启方必做）

### 步骤 1：健康检查（R011 强制门）
```
dsh-tools restart-guard <插件>... → 0 FAIL 才允许重启
```

### 步骤 2：写「准备重启信息」到黑板（R012 完整体）
```json
{
  "key": "notes/collab/restart-intent-<node>-<ts>",
  "type": "restart-intent",
  "from": "<重启方>",
  "ts": "<时间戳>",
  "status": "preparing",           // preparing → restarting → recovered → failed
  "node": "<重启方设备>",
  "planned_time": "<计划重启时间>",
  "reason": "<重启原因>",
  "impact": {
    "services_down": ["central-inbox", "agent-way", ...],
    "expected_downtime": "<预计中断时长>",
    "message_handling": "备用通道缓存 + 恢复回放"
  },
  "prechecks": {                    // R011 强制门结果
    "restart_guard": "0 FAIL / 15 OK",
    "health_check": "12 项全绿"
  },
  "rescue_contact": {
    "rescuer": "<救援方>",
    "channel": "黑板 notes/collab/rescue-<node>-<ts>",
    "escalate_after": "<超时阈值，如 10 分钟无恢复>"
  },
  "rollback": "<回滚方案>"
}
```

### 步骤 3：通知救援方
- 写黑板 `notes/collab/restart-intent-<node>-<ts>`（救援方 central-inbox 会感知）
- 救援方收到后回报「观察就绪」（`notes/collab/rescue-<node>-watch-<ts>`）

## 四、救援观察（救援方必做）

### 观察指标（救援方监控）

| 指标 | 正常 | 异常（触发救援） |
|------|------|----------------|
| 心跳 | ≤60s 更新 | >90s 无更新（离线） |
| 黑板写权限 | 可写 | 写入失败（黑板自身故障）|
| 进程 | 重启方 node-bridge/CLD 在线 | 崩溃/消失 |
| 恢复信号 | restart-intent status=recovered | 超时未恢复 |

### 观察工具
- 复用 verify-watch 逻辑（心跳间隔 >90s 检测离线）
- 救援方新增：读 `restart-intent-<node>-<ts>` 状态字段（preparing/restarting/recovered/failed）
- 超时阈值：`escalate_after`（默认 10 分钟无 recovered → 救援信号）

## 五、救援流程（发现问题 → 救援）

```
【救援方发现异常】
1. 心跳 >90s 离线 / 重启方超时未恢复
2. 写黑板 notes/collab/rescue-<node>-<ts>（救援信号：现象/证据/建议动作）
   ↓
【协调者仲裁】
3. 协调者评估：是否真故障？（区分计划重启 vs 意外崩溃）
4. 批准救援动作（仅非破坏性）或要求重启方自检
   ↓
【救援方执行（非破坏性）】
5. 允许的救援动作：
   - 只读诊断：拉日志 / 查进程 / 查黑板状态
   - 服务重启：launchd kickstart（node-bridge 等守护）
   - 环境检查：磁盘/内存/网络（只读）
   ⛔ 禁止的破坏性动作：
   - 删数据/清缓存/重置配置
   - 覆盖文件/降级/卸载
   - 修改重启方业务数据
   ↓
【恢复确认】
6. 救援后写黑板 rescue-<node>-<ts>-result（动作/结果/状态）
7. 重启方恢复后回报 restart-intent status=recovered
8. 协调者记录救援事件（踩坑档案 + registry）
```

## 六、救援动作白名单（允许）与黑名单（禁止）

### ✅ 允许（非破坏性）
| 动作 | 说明 |
|------|------|
| read logs | 拉取重启方日志（ssh/黑板）|
| check process | 查看进程状态 |
| check disk/mem/net | 只读资源检查 |
| restart daemon | launchd kickstart（node-bridge/黑板等守护进程）|
| write status | 写黑板状态记录 |
| notify | 通知用户/协调者 |

### ⛔ 禁止（破坏性）
| 动作 | 说明 |
|------|------|
| delete data | 删数据/文件/缓存 |
| modify config | 改配置/降级/替换 |
| reset | 重置/清空 |
| destructive project | 破坏性项目/脚本 |
| business data | 动业务数据（订单/客户等）|

**原则**：救援 = 恢复服务可用性（重启守护/诊断），不做任何改变数据/配置的破坏性操作。

## 七、与既有机制衔接

| 机制 | 角色 |
|------|------|
| CCEP 沙箱先行 | 重启前必须沙箱验证（R011 强制门）|
| R011 restart-guard | 健康检查工具（重启方 precheck）|
| R012 完整体 | 准备重启信息 = 完整体（含意图/回滚）|
| verify-watch | 单向观察（中枢→端侧）→ 升级为双向救援观察 |
| 备用通道协议 | 重启期消息缓存 + 恢复回放 |
| 踩坑档案 | 救援事件沉淀（error-to-sop 闭环）|

## 八、工具化（可插件化项）

| 工具 | 功能 | 状态 |
|------|------|------|
| `restart-intent.py` | 重启方：生成标准准备重启信息（模板化 JSON）→ 写黑板 | 待建 |
| `rescue-watch.py` | 救援方：监控重启方心跳+intent 状态，异常发救援信号 | 待建 |
| `rescue-act.py` | 救援方：执行白名单救援动作（只读/守护重启），黑名单拦截 | 待建 |
| verify-watch 升级 | 复用现有守护，加双向 intent 状态监控 | 待改 |

## 九、规则账本

- **R013「重启救援协议」enforced**：重启前留准备信息 + 救援方观察 + 非破坏性救援 + 禁止破坏性
- 与 R005（CCEP）配套：CCEP 定义永续通讯，R013 定义重启期的救援保障
- 触发：任何设备重启（计划/故障）→ 重启方留档 + 救援方观察
