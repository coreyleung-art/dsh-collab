# bb-workbench.py — 蓝图工作台 v3（缺口评估 + 任务卡细化 + 主蓝图落盘）

> 明鉴 v2 · 2026-08-30 · 用户指示：缺口评估/任务卡细化/主蓝图落盘三个前置环节独立工具化
> 位置：`~/dsh-collab/scripts/bb-workbench.py`
> 设计哲学：**工具负责结构（模板/校验/落盘/检索），AI 负责智能（结论/动作）**——二者互补

---

## 三个独立命令

### ① 缺口评估器 `gap`
```bash
python3 bb-workbench.py gap [--bp flowernet] [--out 路径]
```
- **自动做**：读蓝图 stages/works → 提取现状表（版本/位置/门禁/16 子阶段状态）→ 生成三类缺口框架（能力/依赖/风险）+ 论文检索提示
- **AI 填**：缺口内容、依据、建议、结论
- 输出：缺口报告框架（落盘或控制台）

### ② 任务卡细化器 `taskcards`
```bash
python3 bb-workbench.py taskcards --stages d25-3,d3-3 [--calib "校准点"] [--out 路径]
```
- **自动做**：读子阶段现状 → 生成 T1..T5 任务卡模板（依赖链自动 T1→T2→T3…）
- **AI 填**：具体动作名、描述、验收、owner、工时
- 输出：统一格式任务卡（可被 bb-blueprint2 master 解析）

### ③ 主蓝图落盘器 `deploy`
```bash
# BP-9 字段校验（只读）
python3 bb-workbench.py deploy --check-only

# 实际更新
python3 bb-workbench.py deploy --version v2.3 \
    --stage-status d25-3:active,d3-3:todo \
    --substep "p3-2a:todo:环境传感试点" \
    --add-work "供应链支线" --work-stage p2 --work-owner 明鉴 --work-status todo
```
- **全自动**：版本 bump + 子阶段状态 + 子步增改 + works 增补（去重）+ BP-9 校验
- 黑板 stages/works 原子更新（R003 纯内容）

---

## 与既有工具的关系（工具族全景）

| 工具 | 版本 | 职责 |
|------|------|------|
| bb-blueprint.py | v1 | 工作登记/更新/子阶段状态/下一步建议 |
| bb-blueprint2.py | v2 | 升级流程：变更同步四步走 + Master 汇总 + 门禁检查 |
| **bb-workbench.py** | **v3** | **前置环节：缺口评估 + 任务卡细化 + 主蓝图落盘** |
| bb-blueprint-ui.py | — | 蓝图 GUI（8797 看板） |

**完整升级链路**：`gap（发现缺口）→ taskcards（细化任务）→ deploy（落盘主蓝图）→ bb-blueprint2 --full（同步+汇总）→ bb-blueprint-ui 刷新看板`

---

## 验证记录（2026-08-30）

- `gap` ✅ 生成缺口报告框架（现状表 16 子阶段 + 三类缺口模板）
- `taskcards` ✅ 生成 d25-3/p3-2 任务卡模板（依赖链自动）
- `deploy --check-only` ✅ BP-9 校验（发现黑板存储与 BP-9 契约字段映射差异：id/name/works/status 在独立位置——需注意）
- `deploy --version` ✅ 版本 bump（v7→v8→v9 实测，已恢复 v2.2）
- `deploy --stage-status/--substep/--add-work` ✅ 全部生效（测试项已清理，works 回到 20）

## 已知点（改进方向）

- BP-9 校验与黑板 stages 存储有字段映射差异（works 独立 key、id/name/status 在 meta）——check-only 会提示，需在工具内做映射或接受现状
- 任务卡模板固定 5 卡，可加 `--count` 参数
- gap 的论文检索是提示引导（AI 用 knowledge_search），可后续接 KB API 自动检索

---
*bb-workbench v1.0 · 2026-08-30 · 明鉴 v2*
