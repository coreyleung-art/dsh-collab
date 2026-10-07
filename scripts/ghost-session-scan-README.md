# ghost-session-scan — 幽灵会话扫描器（R006 十项）

> 属主: HR 司库 · v1.0.0 · 2026-09-11 · 用途: **每次内存治理的重点对象扫描**

## 解决什么
用户报告: 「**无缘无故突然出现在会话列表、新增但没有角色命名**的会话」

**根因(本次实测确认)**: 当 `agent_send`/`agent_broadcast` 投递到**非活跃/已退役的会话 ID** 时，
运行时**为其创建新会话来承载消息** → 产生「无角色、无用户消息、只有 bus 注入」的幽灵会话。

实测: 65/82 磁盘会话为幽灵(79%); 全部幽灵满足 `bus注入>0 且 用户消息=0`。

## 四类判定
| 码 | 名称 | 判据 |
|---|---|---|
| **G1** | 未登记 | 会话存在但不在 resource-registry |
| **G2** | 无角色(无命名) | 磁盘有会话但无 agent_profile —— **用户核心诉求** |
| **G3** | 突然出现 | mtime 在 N 天内(默认 3)+ 未登记 |
| **G5** | 微小存根 | ≤10KB 且无角色(疑似废弃) |
| G4 | 归档(信息项) | 已在 archivedSessionIds —— 非异常, 仅提示 |

## 评分(聚焦用户诉求)
G2 无角色 **40** + G3 近期出现 **35** + G1 未登记 **25** + G5 微小存根 **20** + 体积 10-20

## 用法
```bash
ghost-session-scan.py scan [--days 3] [--json] [--top 20]   # 扫描+落链
ghost-session-scan.py classify <session-id>                 # 单会话判定
ghost-session-scan.py selfcheck|lean4-check|version|cld-check|version-check
```
落链: `data/registry/ghost-sessions-<date>.json`

## 治理建议(工具输出后)
1. **幽灵会话**(G2+G3+G5, 无用户消息): 内容仅为 bus 注入 → bus/黑板已留档 → 可清理
2. **预防(根因)**: 投递前用**探照灯**(R034 三灯)确认目标活跃 —— 黄灯转黑板, **不盲发**(盲发即造幽灵)
3. **广播收敛**: `all=true` 会命中退役 ID → 造幽灵; 应改用黑板域单卡(R033)

## R006 对照
①插件 P2 ②selfcheck ✅ ③cld-check ✅ ④version-check ✅ ⑤README ✅ ⑥--version ✅ ⑦~/.dsh/ghost-session-scan.log ✅ ⑧落链 ✅ ⑨argparse ✅ ⑩lean4-check ✅
