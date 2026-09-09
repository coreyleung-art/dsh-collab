# bb-taskboard.py — 任务卡执行状态机（并发调度器）

> 明鉴 v2 · 2026-08-30 · 用户指示：角色/节点完成后自动标注汇报 → 快速插卡登记 → 领卡，
> 形成任务进度状态机，支持并发开展任务（非线性推进）。
> 位置：`~/dsh-collab/scripts/bb-taskboard.py`

---

## 状态机模型

```
todo（待领）──claim──▶ claimed（已领/执行中）──report──▶ done（完成待验收）──verify──▶ verified（验收通过）
                           │                                    │
                           └──────block──────▶ blocked（阻塞）◀──┘
                                                    │
                                                    └──unblock──▶ claimed
```

| 状态 | 含义 | 谁操作 |
|------|------|--------|
| todo | 待领 | — |
| claimed | 已领/执行中 | 执行角色 `--claim` |
| done | 完成待验收 | 执行角色 `--report`（自动登记 changelog） |
| verified | 验收通过 | 主编/QA `--verify` |
| blocked | 阻塞 | 任意 `--block`（带原因）→ `--unblock` 解阻 |

## 用法速查

```bash
# 初始化（从 taskcards 文件导入）
python3 bb-taskboard.py --init ~/dsh-collab/data/blueprint/flowernet/taskcards-v1.md

# 领卡（并发：多角色可同时领不同卡）
python3 bb-taskboard.py --claim d25-3-T1 --who 运营
python3 bb-taskboard.py --claim d3-1-T1 --who i9          # 与上并行，互不阻塞

# 汇报完成（自动登记 changelog，可加备注）
python3 bb-taskboard.py --report d25-3-T1 --who 运营 --note "映射表完成"

# 验收
python3 bb-taskboard.py --verify d25-3-T1 --who 明鉴

# 插卡（执行中发现新任务，动态编号 T5/T6…）
python3 bb-taskboard.py --insert "平台对账复核" --stage d25-3 --owner 运营 --dep T4

# 阻塞/解阻
python3 bb-taskboard.py --block d3-1-T1 --reason "等网络"
python3 bb-taskboard.py --unblock d3-1-T1

# 看板 & 进度图
python3 bb-taskboard.py --list [--stage d25-3] [--status claimed]
python3 bb-taskboard.py --graph
```

## 并发模型（非线性推进）

- **每卡独立状态**：多角色同时领不同卡互不阻塞 → 任务并行推进
- **依赖软约束**：领卡时检查 `dep`，依赖未完成给警告（`--force` 可跳过）——不硬卡，靠提示
- **插卡随时**：执行中发现新任务即时插入（自动分配 T 编号）
- **自动登记**：`--report` 完成自动写黑板 changelog（审计留痕）
- **存储**：黑板 `data/blueprint/flowernet/taskboard`（cards JSON，R003 规范）

## 验证记录（2026-08-30）

- `--init` ✅ 45 张任务卡导入黑板
- `--claim` ✅ 并发领卡（运营/i9/知了 同时，互不阻塞）
- `--report` ✅ 完成 + 自动登记 changelog
- 依赖软约束 ✅ T3 领卡时警告 T2 未完成（--force 可跳过）
- `--insert` ✅ 动态插卡（d25-3-T5）
- `--block/--unblock` ✅ 阻塞/解阻流转
- `--graph` ✅ 进度图（完成率/并发执行中统计）
- 测试数据已重置（45 卡全 todo 干净状态）

## 与工具族的关系

```
bb-workbench（规划：gap→taskcards→deploy）
   ↓ 产出 45 任务卡
bb-taskboard（执行：领卡→执行→汇报→验收，并发调度）★本次
   ↓ 完成反馈
bb-blueprint2 --full（同步：changelog+广播+master）
   ↓
bb-blueprint-ui（看板可视化）
```

**规划-执行闭环**：workbench 规划产出任务卡 → taskboard 执行调度（并发/插卡/汇报/验收）→ blueprint2 同步 → UI 呈现。蓝图从静态文档变成**活的状态机**。

---
*bb-taskboard v1.0 · 2026-08-30 · 明鉴 v2*
