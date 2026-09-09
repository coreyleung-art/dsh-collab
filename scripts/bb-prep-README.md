# bb-prep-learn.py / bb-prep-research.py — 提前学习/调查扫描器（R021）

> 明鉴 v2 · 2026-08-31 · R025 规则配套工具（学习调查类任务不受 gate 限制可提前并行）
> 位置：`~/dsh-collab/scripts/bb-prep-learn.py` / `bb-prep-research.py`
> R006 九标准合规：CLI 形态 / TCC 自检（--selfcheck）/ CLD 自适应 / 版本管理（--tool-version）/ 文档化（本 README）/ 统一日志（黑板落链）/ 自动落链（taskboard）/ CLI 治理（argparse）/ dsh 插件化预留

---

## 两个工具的分工

| 工具 | 识别类型 | 关键词侧重 | 默认委派 |
|------|----------|-----------|----------|
| **bb-prep-learn.py** | 提前学习（数据学习/规则学习/模型学习/基线分析） | 学习/基线/分析/规则库/模型/定价/损耗/预测/SOP | 知了 a3bc8cba |
| **bb-prep-research.py** | 提前调查（方法调研/数据源/论文/竞品/可行性） | 调研/调查/方法/数据源/论文/方案/评估/选型 | 数据调查员 4787d717 |

## 用法

```bash
# 扫描：识别可提前学习的 todo 卡（候选清单，人工确认）
python3 bb-prep-learn.py --scan
python3 bb-prep-research.py --scan

# 自动插卡标记（候选 → prep_ahead:true，可指定委派角色）
python3 bb-prep-learn.py --insert --who 知了
python3 bb-prep-research.py --insert --who 4787d717

# TCC 自检 & 版本
python3 bb-prep-learn.py --selfcheck
python3 bb-prep-research.py --tool-version
```

## 工作流（与 taskboard 无缝衔接）

```
扫描（候选清单）→ 主编确认 → --insert 标记 prep_ahead
  → 执行侧领卡（bb-taskboard --claim）→ 完成 --report 自动登记
  → 产出供后续阶段任务引用（d4-2/d3-3/d4-3 即插即用）
```

## 验证记录（2026-08-31）

- TCC 自检：双 PASS（语法/黑板连通/scan 可用）
- 扫描实测：学习候选 15 张 / 调查候选 11 张（含关键词误命中——候选需主编判定，工具不出最终标记）
- 实证：知了 4 学习卡 + 4787d717 4 调查卡全闭环（节日定价/损耗链路/预测基线/规则库 + GBDT/flower-yolo/飞轮/L2D）

## 设计要点

- **候选而非自动**：关键词匹配会产生误命中（如「模型训练」同时命中学习/调查）——工具输出候选清单，主编人工判定后 `--insert` 才标记
- **prep_ahead 标志**：标记后卡在 taskboard 状态机正常流转，但带 prep_type（learn/research）标识，供统计与自动化使用
- **与 R021 联动**：规则生效后，此工具是规则的可执行载体（自动识别可提前任务）

## 自动化规划（配套）

| 级别 | 方式 | 频率 | 说明 |
|------|------|------|------|
| A 定时扫描 | launchd（com.dsh.mingjian.prep-scan.daily） | 每日 3:00 | 自动扫描 → 黑板 prep-ahead-scan-<ts> 候选清单 → 主编次日确认 |
| B 事件驱动 | 黑板 taskboard 更新订阅（sse-sub） | 实时 | 新 todo 卡出现 → 触发扫描 → 命中即通知主编 |
| C 委派通知 | --insert 后自动 agent_send | 插卡时 | 通知知了/4787d717 有可领的提前卡 |

---
*bb-prep-learn/research v1.0.0 · 2026-08-31 · 明鉴 v2 · R025/R006*
