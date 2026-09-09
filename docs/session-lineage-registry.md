# 角色会话代际档案 · Session Lineage Registry

> 建立: HR 司库 · 2026-09-06 · 维护: session-rebirth.py + watchdog 自动化
> 用途: 每个角色会话重建(死锁/归档/升级)时, 登记新旧状态表格, 确保记忆完整继承 + 主动排错
> 权威: 本档案 + resource-registry.md §3 + docs/mingjian-v3-memory-inheritance-*.md

## 代际登记表

| 角色 | 代际 | 旧会话 | 新会话 | 切换日期 | 原因 | 备份路径 | 记忆继承 | 状态 |
|---|---|---|---|---|---|---|---|---|
| 明鉴 | v1→v2 | session-2fe61625 | session-f38244df | 2026-08-30 | 会话死亡 13.5 天(tool/role 配对错乱) | archives/mingjian-v1-session-2026-08-30/ | 无继承包(重建) | ✅ 已闭环 |
| 明鉴 | v2→v3 | session-f38244df | session-a190c54c | 2026-09-06 | **上下文死锁**(79.3万 tokens 压缩门控 4 连拒) | archives/mingjian-v2-deadlock-2026-09-06/ | ✅ 记忆继承包(4段摘要26.4K+指令) | ✅ 已闭环 |
| 司库 | 前任→现任 | session-a17a52f8 | session-2a15e6b1 | 2026-08-22 | 误归档退役 | ~/.dsh/sessions/(历史保留) | 文档交接(登记表/政策/台账) | ✅ 已闭环 |
| 资源管理者 | 前任→前任 | session-e7bfeea8 | session-a17a52f8 | 2026-08-18 | 交接 | — | 文档交接 | ✅ |

## 新增代际流程(工具化后标准步骤)

1. **主动排错**: watchdog 定期巡检(launchd 可挂) → 检出死锁候选(RED=门控拒≥2) → 通知 HR
2. **诊断**: `session-rebirth.py diagnose --session <id>` 确认健康度
3. **备份**: `session-rebirth.py backup --session <id> --name <别名>` → archives/
4. **记忆提取**: `session-rebirth.py extract --session <id> --name <别名>` → 记忆继承包 docs/
5. **续接提示词**: `session-rebirth.py compose --session <id> --name <别名> --role <名>` → docs/
6. **开新会话**: 用户粘贴提示词 → 新会话 agent_profile 登记 → 回报 HR session id
7. **登记本表**: 更新代际登记表(新行) + registry 会话行 + 广播全员切换
8. **归档旧会话**: 旧会话只读, 勿再投递唤醒(广播提醒)

## 记忆完整继承检查单(新会话第一回合)

- [ ] 读记忆继承包(docs/<name>-memory-inheritance-<date>.md) — 确认摘要段数 = 旧会话压缩成功次数
- [ ] agent_profile 登记(role/abilities/resources 与旧档案一致或演进)
- [ ] 验证关键状态(规则账本/黑板键/资源文件在位)
- [ ] 回报 HR: session id + 继承确认 → HR 更新本表 + registry

## 主动排错配置建议

- launchd: com.dsh.session-rebirth.watchdog(每 6h 跑 `session-rebirth.py watchdog`)
- 判定阈值: 门控拒 ≥2 → RED 通知; ≥1 → YELLOW 观察
- 预防: 上下文 >60% 即提示分段推进/压缩(deadlock 教训: 79.3万=76% 时已太晚)

*版本 v1.0 · HR 司库 · 2026-09-06*
