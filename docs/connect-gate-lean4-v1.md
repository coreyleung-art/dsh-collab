# 连接实验室 · Lean4 逻辑门评估(确认门) v1

> 作者: 明鉴 v2 · 2026-09-05 · 用户提出(呼应 Φ9 约束前置 / R027 人开关锁)
> 一句话: 确认一条候选连接 = 构造 `ConfirmedEdge` —— 必须有 `Authorization`(门评估通过 + 用户授权), 否则结构上不可达

## 一、问题
原"确认连接"按钮 = 直接写 confirmed.json(无评估、无门禁)。违反 Φ9: 确认无约束前置, 可能误连/越权连。

## 二、Lean4 类型锁模型

```lean
-- 连接实验室 · 确认门类型锁
inductive GateVerdict          -- 门评估结果(自动化, 无人类授权)
  | L1 : Level1Verdict         -- 绿灯: 同域+高置信+无冲突
  | L2 : Level2Verdict         -- 黄灯: 跨域/共享边界 → 需用户显式确认
  | L3 : Level3Verdict         -- 红灯: 独占资源/关键节点 → 需双重确认

inductive Authorization        -- 授权凭证(可构造 ConfirmedEdge 的唯一途径)
  | GateApproved : GateVerdict → Authorization     -- 门过 + 级别
  | HumanConfirm : Record → GateVerdict → Authorization  -- 人类确认记录 + 门

inductive ConfirmedEdge
  | Edge : Agent → Agent → Authorization → ConfirmedEdge  -- 真实边必须有授权

def confirmEdge (a b : Agent) (auth : Authorization) : ConfirmedEdge := Edge a b auth
-- 类型系统保证: 没有 Authorization 就构造不出确认边(不是运行时 if, 是结构不可能)
```

## 三、门评估维度与判定
| 维度 | 信号 | 影响 |
|------|------|------|
| score | 向量语义置信(≥0.5 high / 0.38-0.5 mid) | 高置信=基础 |
| 域 | 同域(ops↔ops) vs 跨域(ops↔biz) | 跨域=黄/红 |
| 资源独占 | 候选涉及独占资源(排他) | 独占=红 |
| 关键性 | 连接 gov/协调/资源中枢等关键节点 | 关键=红 |
| 冲突 | 与已有 share/confirmed 冲突或反向 | 冲突=红/去重 |

## 四、流程(前端按钮: 评估 → 显示门判 → 用户确认)
1. 点候选的「🔍 评估连接」 → 调 /api/connect-gate?from&to
2. 返回: level(L1/L2/L3) + 判定依据 + 建议
3. 用户基于门判决定:
   - L1: 一键确认(仍记 HumanConfirm)
   - L2: 确认需附原因(文本必填)
   - L3: 确认需附原因 + 明确再次确认(弹框双重)
4. 确认 → /api/connect-confirm 写 confirmed.json —— **每条必须带 gate 评估记录**(缺则 API 拒)

## 五、confirmed.json schema(带 auth)
```json
{"links": [{
  "from": "...", "to": "...",
  "auth": {"by": "user", "ts": "...", "gate": {"level": "L1|L2|L3", "score": 0.72, "verdict": "approve", "reasons": ["同域(ops)", "语义 31%", "无独占"]}},
  "reason": "用户填或自动",
  "ts": "..."
}]}
```
> 结构保证: 无 auth.gate 的 link = 非法 → 图谱拒绝渲染为实线(Φ9: 约束在数据层不可绕过)

## 六、验收
| # | 标准 |
|---|------|
| A1 | /api/connect-gate 评估候选返回 level+依据 |
| A2 | L1/L2/L3 分级(同域高置信=绿; 跨域/独占/关键=黄红) |
| A3 | confirm API 拒绝无 gate 记录(返回错误) |
| A4 | confirmed.json 每条含 auth{gate} |
| A5 | 图谱只渲染带合法 auth 的 confirmed 边 |
| A6 | 前端: 评估→门判显示→分级确认流程 |
