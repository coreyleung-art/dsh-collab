# 孤岛探索工作流工具 · 设计规范（bb-island / dsh-tools island）

> 明鉴 v2 · 2026-09-02 · 用户指示：把孤岛探测+建议功能化/工具化/插件化/自动化规划 → 形成新 workflow
> 用户补充：符合 R006 九标准 + 考虑 rust 化（复用 dsh-tools 子命令族）——已咨询星桥接入规范
> 自动化定案：**检测自动(cron)·连接人工(R027 人类确认)**

## 〇、为什么工具化（价值）

孤岛探测目前是蓝图管理器里的一个 UI 卡（L1）。工具化后：
1. 独立 CLI 可被 cron/launchd 调度 → 每日自动扫
2. 建议引擎可批处理 → 产出待审清单
3. 人类确认后一键连接 → 图谱长出
4. 全程落链（黑板 changelog）→ 可追溯自进化过程

## 一、R006 九标准逐条对照（设计承诺）

| # | R006 项 | 本工具落地 |
|---|---------|-----------|
| 1 | dsh 插件形态 | rust-tools 子命令 `island`（复用 dsh-tools 二进制，rust 化） |
| 2 | TCC 检测 | `--selfcheck`：读 agent-bus/黑板/mapping 三数据源 + 孤岛算法自检 |
| 3 | CLD 自适应 | 无 CLD 特定依赖（纯数据/黑板读）——自适应说明入 README |
| 4 | dsh 版本自适应 | 读取 dsh 版本不硬编码 |
| 5 | 文档化 | 本设计 + island.md 使用说明（含三件套） |
| 6 | 版本管理 | `--tool-version` + Cargo.toml 版本同步 |
| 7 | 统一日志 | 结果 JSON 落黑板 data/blueprint/gallery/island-runs/<ts>.json |
| 8 | 自动落链 | 每次运行 → 黑板落链 + (可选)knowledge 入库 |
| 9 | CLI 治理 | 用法统一（--selfcheck/--tool-version/--dry-run 等） |

## 二、命令面设计

```
dsh-tools island [子命令] [选项]

子命令:
  detect          探测孤岛（各图谱未连接节点）
    --graph agents|rules|mech|all   [默认 all]
    --json                         输出 JSON（供管道）
  suggest         对孤岛生成候选连接建议（语义匹配）
    --limit N                      最多 N 条建议 [默认 20]
    --confidence 0.0-1.0           最低置信度过滤 [默认 0.3]
    --dry-run                      只输出不落盘
  apply           应用已确认的连接（写入 mapping/relations）
    --file <suggestions.json>      确认后的建议文件（人类编辑过）
    --dry-run                      预览将写入哪些边
  report          生成自进化报告（孤岛率/采纳率/新边）
    --days N                       统计近 N 天 [默认 7]
  cron            检测+建议自动跑（供 launchd/cron 调用）→ 黑板落链
  --selfcheck     TCC 自检
  --tool-version  版本
```

## 三、自进化工作流（完整闭环）

```
┌─ [cron 每日] detect+suggest 自动跑
│      ↓
│  黑板 data/blueprint/gallery/island-runs/<ts>.json
│  （孤岛清单 + 候选边 + 理由 + 置信度）
│      ↓
├─ [人类/星桥] 查看报告 → 编辑候选（勾选/否决）
│      ↓
├─ rule-judge L2 断言机械校验（可判定的）
│      ↓
├─ [人类确认 R027] apply --file <确认清单>
│      ↓
│  写 mapping/relations → 图谱长出 → 孤岛消失
│      ↓
└─ report 度量进化（孤岛率下降/采纳率） → 循环
```

## 四、建议引擎（suggest）核心

对每个孤岛节点，用语义匹配找潜在伙伴：
- **智能体**：能力关键词 × 其他 agent 资源/角色域 → 建议协作边
  例：DSH 插件开发(e0c391f7) 能力"插件验证" × 验金石"QA验收" → 建议
- **规则**：summary 提及蓝图/agent 但未标 → 建议约束边
- **机制**：依赖关系缺失 → 建议链
每条建议含：from/to/理由/置信度/来源字段（AI 建议 vs 数据可证）

**防幻觉护栏**：
1. AI 只建议不连线（R027：生产区人类掌权）
2. 建议落黑板可审，不直接改 mapping
3. rule-judge L2 对可判定类（如 J 属主）机械校验
4. apply 需人类确认文件

## 五、里程碑

| 里程碑 | 内容 | 验收 |
|--------|------|------|
| M1 | island detect 子命令（rust） | 三图谱孤岛数与 UI 卡一致 |
| M2 | island suggest（语义匹配） | 13 孤岛各产出 ≥1 建议 + 理由 |
| M3 | apply + report（人工确认闭环） | 确认后孤岛减少、图谱新边出现 |
| M4 | cron 自动化 + 黑板落链 | 每日自动跑出报告可查 |
| M5 | workflow 固化（文档+一键） | start-island-cron.sh + 使用说明 |

## 六、与既有机制衔接

- **蓝图管理器**：UI 孤岛卡显示 detect 结果；apply 后图谱刷新可见
- **星桥规则体系**：规则建议走 mapping（本体他维护，映射我维护）
- **rule-judge L2**：候选确认的机械层
- **R027**：apply=生产区变更，人类 GUI 确认
- **agent-mapping.json/rule-mapping.json**：连接写入目标（已有文件）

## 七、三件套纪律

- 文档：本文 + island.md 使用说明
- 代码：rust-tools/src/island.rs + main.rs 注册（等星桥接入规范确认）
- 依赖：agent-bus.json / 黑板 relations / rule-mapping.json / mechanism.json

---
*孤岛探索工作流工具设计 · 明鉴 v2 · 2026-09-02*
