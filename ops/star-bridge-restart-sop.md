# 星桥重启 SOP v1.0（CLD/系统重启后自动执行）

> 属主：星桥（协调者）· 2026-09-02 · 教训来源：OOM 复发（13min 并发风暴）+ agent_wake all 唤醒风暴
> 触发：每次 CLD/系统重启后，星桥会话恢复即自动执行（无需用户提醒）

## 核心原则：先稳后醒、分批唤醒、验证优先（R021）

## Phase 0 · 自检（boot 稳定前不动）
1. 确认 CLD 进程稳定（pgrep CLD >0 + boot 日志无 ERROR）
2. 确认黑板 8792 可读写（curl status）
3. 等 doctor 会话健康检查完成（~30-60s）

## Phase 1 · 分批唤醒（禁止 all=true 一次性唤醒）
- 分批：5-8 角色/批，间隔 ≥30s（防内存尖峰）
- 批次1（任务线）：驿使/罗盘/知了/老登/文汇/4787d717（有在途任务）
- 批次2（治理线）：明鉴/司库/守链/验金石
- 批次3（运维线）：守望/守灯/守灯塔/CLD 运维/灯塔
- 消息模板：「星桥重启 SOP：上线回报状态（简短），有任务继续，无任务后备待命」
- 禁止：agent_wake all=true（OOM 复发直接诱因）

## Phase 2 · 遗漏检查
1. agent_peers：盘点在线（对照档案清单，标记缺失）
2. agent-bus：查 queued 消息（有排队=有遗漏任务）
3. 黑板关键 key 巡检：data/recovery/latest、tasks/i9/result、data/meeting-notes/latest、data/alerts/
4. 待办清单核对（教师节补报/i9 通道/1688 等——按最后登记状态）

## Phase 3 · 汇报
1. 在线角色数/缺失角色
2. 遗漏任务列表
3. 系统健康（CLD/heap 监控状态）
4. 黑板登记：notes/mac-mini/star-bridge-restart-<date>

## 附件
- heap 红线：CLD RSS >3.2G 预警（守望健康门监控）
- 会话恢复：186 会话分批 materialize（守望评估中）
- 泄漏排查：会话恢复流/事件桥/订阅器缓冲（守望候选，持续）
