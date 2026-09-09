# labforge — 实验方法引擎

> 持续循环：设计 → 生成 → 执行 → 评估(断言) → 沉淀 → 再设计
> 位置：`~/dsh-collab/guard/tools/labforge/`
> 理念：把"主动设计实验、设定目标、设定回收与评估标准、持续循环"工具化；借鉴开源科研方案（见 tech-research/lab-methods/ 调研），不重复造轮子

---

## 一、用法

```bash
labforge new <id>           生成实验卡片（JSON 模板）
labforge run <id>           执行 runner 并回收结果到 results/<id>.latest.json
labforge eval <id> [file]   对照卡片断言评估（PASS/FAIL/N-A）
labforge loop <id>          run + eval 一键闭环（循环核心）
labforge regress            全部登记卡一键回归
labforge archaeology [目录]  故障根因考古(双目录44报告→6模式→守护缺口)
labforge hypotheses         假设登记表（各卡片 hypothesis 汇总）
labforge status [id]        实验状态/历史
labforge design <目标>      目标 → 实验设计草稿
```

## 二、实验卡片 schema（cards/<id>.json）

```jsonc
{
  "id": "实验id",              // 唯一
  "title": "标题",
  "goal": "实验目标",           // 为什么做
  "hypothesis": "H1: ...；H2: ...",  // 可证伪假设（入假设登记表）
  "kind": "crash|perf|correctness",
  "runner": "runner-xxx",      // runners/ 下的执行脚本
  "data": ["样本文件..."],       // 输入（相对 data/ 或绝对路径；须为只读副本）
  "params": { "heap": "512,1024" },  // runner 参数（--key=value 注入）
  "assertions": [              // 回收与评估标准 = 断言列表
    { "id": "A1", "metric": "指标路径", "op": "lt|gt|eq|gte|lte|contains|match",
      "target": 阈值, "desc": "含义" }
  ],
  "status": "draft|pass|fail|na",  // 自动更新
  "tags": ["memory", "oom"]
}
```

**断言 = 回收标准**：从 runner 产物 JSON 提取指标（支持 `a.b` 与 `a[0].b` 路径），对照 op+target 判 PASS/FAIL。

## 三、Runner 契约

- 放 `runners/runner-*.js`，Node 实现
- 输入：命令行位置参数 = 样本文件（来自 card.data 解析，自动解析 data/ 软链）
- 参数：`--key=value`（来自 card.params，逐对注入）
- 产物：最终一行 JSON 到 stdout 或 `--json-out=<path>`（指标字典）
- 隔离纪律：样本只读；重活放受限 heap 子进程（防 OOM 拖垮宿主）

## 四、循环工作流（怎么用）

1. **主动设计**：遇到可验证的判断/修复 → `labforge new <id>` + 填 goal/hypothesis/assertions
2. **执行回收**：`labforge loop <id>` → runner 跑 → 指标回收 → 断言判定 → 卡片状态自动更新
3. **沉淀对照**：`labforge status`/`hypotheses` 看登记；结果 JSON 留档 results/
4. **持续循环**：新修复上线前 `labforge regress` 全量回归（防退化）；实验发现回写引擎模板（自举）

## 五、当前登记实验

| id | 目标 | 状态 |
|---|---|---|
| memory-crash-oom-repro | 多会话全量物化 OOM 复现 + 帧索引治理对照 | pass (4/4) |
| single-session-governance | 单会话治理收益回归 + 反向证实多会话叠加为 OOM 根因 | pass (4/4) |

## 六、开源借鉴映射（详见 tech-research/lab-methods/ 调研）

| 借鉴 | 来源 | 落地 |
|---|---|---|
| HYPOTHESIS.md / stage-gates / autopsy | g-experiment (galdr) | 卡片 hypothesis 字段 + 断言即 gate + hypotheses 命令；autopsy 待补 |
| 假设→实验→验证→知识图谱 | Kosmos AI Scientist | 断言=验证维度；结果→黑板决策链接 |
| 8 维质量框架 | Kosmos | 断言维度化方向 |
| hydra 配置组合 | DVC+Hydra | params 覆盖语法方向 |
| 树搜索多假设 | Sakana v2 | labforge explore（未来） |
| Refiner 自改进 | Continual Harness | 实验沉淀回写模板（自举哲学） |
