# bb-blueprint-version.py — 蓝图版本管理 + 日志管理

> 明鉴 v2 · 2026-09-01 · 蓝图本身版本/日志管理工具化插件化
> 位置：`~/dsh-collab/scripts/bb-blueprint-version.py`
> R006 九标准合规：CLI 形态 / TCC(--selfcheck) / 文档化 / 版本管理(--tool-version) / 自动落链 / CLI 治理

---

## 是什么

对蓝图本身做**版本管理**（版本号/历史/差异/快照/回滚）+ **日志管理**（操作日志统一登记/查询/审计）——把散落的 changelog 归集为统一版本日志。

## 命令

### 版本管理
```bash
python3 bb-blueprint-version.py --version-list                     # 各蓝图当前版本表
python3 bb-blueprint-version.py --bump banking --level minor --why "原因"  # 版本升级（major/minor/patch）
python3 bb-blueprint-version.py --history banking                  # 版本历史（含变更摘要）
python3 bb-blueprint-version.py --diff flowernet v2.2 v2.3         # 两版本差异（变更轨迹）
python3 bb-blueprint-version.py --snapshot banking v1.0            # 快照导出（BP-9 完整落盘）
python3 bb-blueprint-version.py --rollback banking v1.0            # 回滚（从快照恢复）
```

### 日志管理
```bash
python3 bb-blueprint-version.py --log "变更描述" --bp flowernet     # 登记操作日志
python3 bb-blueprint-version.py --logs [--bp X] [--limit N]        # 查询日志
python3 bb-blueprint-version.py --audit [--bp X]                   # 审计汇总（按蓝图/操作）
python3 bb-blueprint-version.py --migrate                          # 存量 changelog 归集
```

## 存储

- 统一版本日志：黑板 `data/blueprint/versionlog`（entries 操作流 + blueprints 版本表）
- 快照：`~/dsh-collab/data/blueprint/snapshots/<bp>-<ver>-<ts>.json`
- 存量 changelog：`data/blueprint/changelog/*`（migrate 归集后仍保留原文）

## 验证记录（2026-09-01）

- TCC PASS（语法/黑板连通）
- migrate：21 个 changelog key → 9 条归集 ✅
- version-list：6 蓝图版本表 ✅
- bump：v1.0→v1.1（patch）✅ / v1.1→v1.2（minor）✅
- history/logs/audit：操作流 + 汇总 ✅
- snapshot：banking-v1.0 快照导出 ✅
- rollback：快照恢复逻辑 ✅（需先 snapshot）

## 后续

- Rust 化：高频 version-list/logs 查询 → dsh-tools 子命令（R029 范式）
- diff 增强：阶段级深度对比（不只是变更轨迹）
- 与 bb-blueprint-create/registry 联动：正式化/变更时自动登记版本日志

---
*bb-blueprint-version v1.0 · 2026-09-01 · 明鉴 v2*
