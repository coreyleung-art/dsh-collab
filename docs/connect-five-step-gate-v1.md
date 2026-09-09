# 连线规则门 · 五步标准流程 v1(Connect Pipeline Gate)

> 作者: 明鉴 v2 · 2026-09-05 · 用户提出
> 「评估、建议、计划、审批、执行 分为标准化五步连线规则门」
> 定位: 连接实验室候选从识别到建边的完整流水线, 每步有产出、有门判, 状态机推进(Lean4: 下一步必须上一步通过)

## 一、五步状态机(不可跳步)

```
NEW ──评估──▶ EVALUATED ──建议──▶ RECOMMENDED ──计划──▶ PLANNED ──审批──▶ APPROVED ──执行──▶ EXECUTED
 (候选)      (打分+门判L1-3)    (价值叙事+行动建议)   (落地步骤/负责人/影响)  (人类确认+auth)   (已建边/图谱实线)
```

| 步 | 门/产出 | 谁 | 依据(Lean4) |
|----|---------|-----|-------------|
| 1 评估 Evaluate | 5 特征打分 + L1/L2/L3 门判 | 工具(bb-connect-lab) | /api/connect-gate |
| 2 建议 Recommend | 价值叙事(为什么) + 行动建议(做什么) | 工具 | reason 三段式 |
| 3 计划 Plan | 落地步骤: 建边类型/涉及节点/影响面/回滚 | 工具+可调 | sandbox 预览(冲突/孤岛) |
| 4 审批 Approve | 人类授权: 附 auth{gate+sandbox+plan} | 用户 | confirm 双门校验 |
| 5 执行 Execute | 写 confirmed.json → 图谱紫实线 | 系统 | auth 完整才落 |

## 二、每条候选的推进状态(数据)
```json
{"from":..., "to":..., 
 "step": "NEW|EVALUATED|RECOMMENDED|PLANNED|APPROVED|EXECUTED",
 "gate": {"level":"L1", "score":0.71, "reasons":[...]},
 "recommendation": "共同能力…；价值…；行动…",
 "plan": {"steps":["登记资源边界","建共享边"], "impact":"消除1孤岛", "rollback":"删confirmed行"},
 "auth": {"by":"user","ts":...},
 "executed": true}
```

## 三、前端(连接实验室按步骤分列)
- Tab 区: 候选池(NEW) → 已建议 → 已计划 → 待审批 → 已执行(实线)
- 每步卡片: 点「推进下一步」→ 调对应 API → 状态迁移
- 不可跳步: 未评估不能建议; 未审批不能执行(结构保证)

## 四、Lean4 状态锁
```lean
inductive Step : Type
  | NEW | EVALUATED | RECOMMENDED | PLANNED | APPROVED | EXECUTED
-- 状态转换必须携带上一步证明(不可跳步)
def advance : (s : Step) → ProofNext s → Step
-- EXECUTED 需 auth(审批记录), 否则类型不成立
```

## 五、API
| 端点 | 动作 |
|------|------|
| /api/connect-lab | 候选池(含 step 状态) |
| /api/connect-gate | 步1 评估 |
| /api/connect-plan | 步3 计划(生成计划+影响) |
| /api/connect-approve | 步4 审批(带 plan 记录) |
| /api/connect-confirm | 步5 执行(校验全部前置) |

## 六、验收
| # | 标准 |
|---|------|
| A1 | 候选状态机 6 态可推进, 不可跳步 |
| A2 | 每步有产出(评估分/叙事/计划/auth) |
| A3 | confirm(执行)只接受 APPROVED 候选 |
| A4 | 前端分列显示各步候选 |
| A5 | 执行后图谱实线 + confirmed.json 完整 auth |
| A6 | 沙箱预览并入计划步(影响/回滚) |
