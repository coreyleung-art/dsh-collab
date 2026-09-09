# 连接实验室 · 沙箱+灾难双门(Lean4) v1

> 作者: 明鉴 v2 · 2026-09-05 · 用户提出
> 「不能因为这个模拟实验，而影响其他原本正常的东西」→ 确认类写操作必须先过 沙箱门 + 灾难门
> 延续: dev-sandbox-simulator(sandbox-first 哲学) · 守望 pre-change 门 · Φ9 约束前置

## 一、问题
连接实验室确认一条边 → 写 confirmed.json → agent-network 图谱显示紫实线。若:
- 误连关键节点 / 与现有 share 冲突 / 大批量确认 → 污染正常图谱
- 直接写真实文件 = 无沙箱 = 影响生产(违反用户指示)

## 二、双门模型(Lean4: 构造"可确认操作"需两道 Authorization)

```lean
-- 沙箱门: 先证明"此边加入后安全"(在副本模拟, 无副作用)
inductive SandboxProof
  | Preview : ImpactReport → SandboxProof      -- 预览报告(冲突/指标/变化)
  | Safe     : SandboxProof → SandboxProof      -- 确认无冲突
-- 灾难门: 评估操作风险级
inductive DisasterVerdict
  | D1 : green   -- 低险: 同域+预览无冲突+不动已有边
  | D2 : yellow  -- 中险: 涉及关键节点/跨域
  | D3 : red     -- 高险: 大批量/动已有边/双向关键
-- 可确认操作 = 沙箱证明 + 灾难判定 + 人类确认
inductive Confirmable
  | Op : SandboxProof → DisasterVerdict → HumanConfirm → Confirmable
```

## 三、沙箱预览(门1: 不碰真实数据)
/api/connect-sandbox?from&to → 在**内存副本**模拟加边,返回 ImpactReport:
- conflict: 与现有 share/confirmed 是否冲突/重复/反向
- changeIslands: 该边加入后是否消除/新增孤岛
- netDelta: 节点度/边数变化
- recommend: ok / conflict 详情
> 纯计算, 不写任何文件 → 模拟实验不影响生产 ✅

## 四、灾难判定(门2: 风险评估)
/api/connect-gate 已分 L1/L2/L3(同域/跨域/关键) — 作为灾难级:
- L1 ≈ D1 低险 · L2 ≈ D2 中险 · L3 ≈ D3 高险
- D3(跨域/双关键/动已有边)→ 需: 沙箱预览无冲突 + 人类双重确认

## 五、确认流程(前端)
1. 🔐 评估(gate) → L1/L2/L3
2. 🧪 沙箱预览(sandbox) → 显示"加边后: 无冲突 ✓ / 冲突: xx; 消除孤岛 n"
3. 🚦 灾难判定合并 → 绿: 直接确认 · 黄: 填原因 · 红: 预览须无冲突+双重确认
4. 确认 → confirm 写(带 auth{gate + sandbox} 双证明)

## 六、confirmed.json auth 含双门
```json
"auth": {"by":"user","ts":"...",
  "gate":{"level":"L1","score":0.71,"reasons":["同域(ops)"]},
  "sandbox":{"conflict":false,"changeIslands":0,"recommend":"ok"},
  "disaster":"D1"}
```

## 七、验收
| # | 标准 |
|---|------|
| A1 | /api/connect-sandbox 内存模拟, 不写文件(零副作用) |
| A2 | 沙箱报告冲突/孤岛变化/网络指标 |
| A3 | confirm 需带 sandbox 证明, 缺则拒 |
| A4 | 灾难级并入(红=跨域/双关键需双重) |
| A5 | 真实数据(confirmed.json/图谱)只在双门通过后动 |
| A6 | 模拟实验(候选生成/预览)完全不影响生产数据 |
