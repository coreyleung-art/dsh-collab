# 升级过程备用通道保持机制 v1.0（Upgrade Standby Channel Protocol）

> 2026-08-29 星桥-mac-mini-协调者 · 用户要求：建立升级过程的备用通道保持机制，避免升级过程失联
> 依据：CCEP 永续通讯协议（通道迭代必须旧通道投递新通道）+ 用户强制纪律（沙箱先行，不依赖人类手工重连）

## 一、问题定义

升级 CLD / node-bridge / 黑板 / 插件时，CLD 内插件（agent-way、central-inbox）随重启暂时失联，
导致**注入链路中断**（i9 04:11 回传登记、司库消息等无法自动唤醒中枢会话）。

**失联的本质**：CLD 内插件失效，但 CLD 外 launchd 守护层全程在线——备用通道必须建在守护层。

## 二、通道分层（升级期视角）

| 层 | 组件 | 是否依赖 CLD | 升级期状态 | 角色 |
|----|------|-------------|-----------|------|
| L0 存储 | rust-blackboard 8792/8803 | ❌ 独立进程 | ✅ 常在线 | 消息总线（SSE 广播正常） |
| L1 桥 | node-bridge（launchd） | ❌ 独立 | ✅ 常在线（除非自身升级） | 心跳/队列/notes 读写 |
| L2 订阅 | bb-sub.coordinator（launchd） | ❌ 独立 | ✅ 常在线 | 订阅 notes/collab/,notes/mac-mini/ → 落盘 |
| L2 唤醒 | central-wake.py（launchd） | ❌ 独立 | ✅ 常在线 | 检测新增 → 写 wake-trigger |
| L3 注入 | central-inbox（CLD 插件） | ✅ 依赖 | ❌ 升级期失联 | SSE → 会话上下文注入 |
| L3 总线 | agent-way（CLD 插件） | ✅ 依赖 | ❌ 升级期失联 | agent_send/agentBus |

**关键结论**：L0-L2（守护层）是天然备用通道；失联只发生在 L3（CLD 内），且 L3 恢复后应能回放 L2 缓存的消息。

## 三、备用通道机制（三层保障）

### 保障 1：消息缓存（L2 → 落盘，防丢）
- bb-sub.coordinator 已落盘 `~/.dsh/inbox/bb/coordinator.jsonl`（append-only JSONL，含全部 notes/collab/ + notes/mac-mini/ 消息）
- 升级期消息**不丢失**，全部在缓存中
- 验证：`grep -c "<key>" ~/.dsh/inbox/bb/coordinator.jsonl`

### 保障 2：持久触发（L2 → 黑板 wake-trigger，防漏）
- central-wake.py 检测缓存新增 → 写黑板 `data/central/wake-trigger`（含 ts/key/count）
- wake-trigger 是黑板 KV，CLD 恢复后中枢会话读黑板即可感知「升级期间有 N 条消息」
- 验证：`curl 黑板/data/central/wake-trigger`

### 保障 3：恢复回放（L3 恢复 → 补注入）
- CLD 重启完成后，中枢会话执行「恢复回放」：
  1. 读 wake-trigger 的 count/last_key，与已处理水位比对
  2. 从 coordinator.jsonl 读取未处理消息（增量）
  3. 逐条处理（登记/归档/回复），更新水位
- 回放工具：`scripts/upgrade-replay.py`（新增，见下）

## 四、升级 SOP（备用通道集成）

```
【升级前】（旧通道投递新通道）
1. 确认 L0-L2 守护在跑：bb-sub.coordinator / central-wake / node-bridge（launchctl list）
2. 记录当前水位：wake-trigger count + coordinator.jsonl 行数
3. 黑板 notes/collab/upgrade-<id>-notice 广播升级计划（含备用通道说明、预计中断时长）
4. 通知端侧（i9/MBP）：升级期间消息将缓存，恢复后回放

【升级中】
5. 执行升级（CLD 重启 / 二进制替换 / 黑板切换）
6. 守护层（L0-L2）保持在线，消息持续落盘缓存
7. 若升级对象是黑板本身：先切备用黑板或短窗口（沙箱先行验证）

【升级后】（验证可行才切换）
8. CLD 恢复 → 验证 central-inbox SSE 连接建立（lsof 8803 + central-inbox.log 出现）
9. 验证 agent-way 工具可用（agent_send 探针）
10. 执行恢复回放：读 wake-trigger → 处理缓存消息 → 更新水位
11. 回放确认无遗漏（缓存已处理数 == 新增数）→ 双通道确认
12. 黑板 notes/collab/upgrade-<id>-done 广播完成 + 回放摘要
```

## 五、工具：upgrade-replay.py

```python
# scripts/upgrade-replay.py — 升级后消息回放（备用通道保障 3）
# 用法: python3 upgrade-replay.py            # 全量回放未处理
#       python3 upgrade-replay.py --dry-run  # 预览不处理
# 输入: ~/.dsh/inbox/bb/coordinator.jsonl（bb-sub 落盘缓存）
#       黑板 data/central/wake-trigger（触发水位）
# 输出: 未处理消息清单 + 处理动作（登记黑板 data/iterations/ 归档）
```

（实现：读 JSONL → 按 last_key 水位过滤 → 逐条 PUT 黑板 data/central/replay-<ts>/ 归档 → 更新水位）

## 六、验证标准（沙箱先行）

| 场景 | 沙箱验证 | 生产标准 |
|------|---------|---------|
| CLD 重启 | 模拟：写测试消息 → 重启 CLD → 回放应处理 | 无消息丢失，回放数 == 新增数 |
| node-bridge 升级 | 已有 v1.3.2 沙箱验证（心跳 value 完整） | 心跳恢复 ver 新版本 |
| 黑板升级 | v0.6.4 沙箱验证（认证/广播/写入全绿） | 切换后 SSE 广播 + 认证正常 |
| 注入恢复 | lsof 8803 有 CLD 连接 + central-inbox.log 出现 | 测试消息注入中枢会话 |

## 七、当前失联的根因与本机制的关系

- 现状：L0-L2 健康（bb-sub 落盘 491KB、central-wake 04:25 写 trigger）✅
- 失联点：L3 central-inbox 未运行（CLD 02:35 启动后 03:38 插件更新未重启）→ 注入断
- **本机制保证**：即使 L3 失联，消息仍在 L2 缓存 + L1 trigger，CLD 恢复后回放即可补上——升级不再是失联窗口

## 八、落地清单

- [ ] scripts/upgrade-replay.py 实现（回放工具）
- [ ] wake-trigger 增强：记录 last_key + count（当前只有 ts）
- [ ] CLD 重启后验证 L3 恢复（lsof 8803 + central-inbox.log）
- [ ] 首次实战：本次 CLD 重启（修复 central-inbox）即按本 SOP 执行
- [ ] 广播端侧：升级期消息缓存 + 恢复回放约定
