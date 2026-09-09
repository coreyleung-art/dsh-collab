# blueprint:rule-judge · 裁判层/规则引擎（AI 提议→确定性验证→打回重来） · v1.0

> 生成：bb-blueprint-create.py · 2026-09-01T09:51:28 · 三件套纪律（文档/代码/依赖）
> 状态：active · 门禁：① L1 机械验证 fail-closed 达标才进 L2 ② L2 规则灰度（影子模式误杀率达标）才转硬阻断 ③ L3 语义软门只决定 retry/escalate ④ 每动作四段闭环：授权(R027)→锁(R029)→验证(本蓝图)→复核(M4)
> 依据：research/ai-judge-pattern.md（R025 R2）+ lean4-full-chain.md + GOV-2026-0901-01 恒true缺陷 + R030 验证层 + 事件回顾 P2/P4

## 〇、BP-9 元信息

| 字段 | 值 |
|------|-----|
| id | rule-judge |
| name | 裁判层/规则引擎（AI 提议→确定性验证→打回重来） |
| version | v1.0 |
| mainlines | {"audit": {"desc": "全量审计链：谁提议/依据/逐条校验结果/谁放行——可回放可复核", "name": "审计证据层"}, "loop": ... |
| stages | [{"id": "rj1", "mainline": "verify", "name": "L1 机械验证", "stage": "1.0", "status"... |
| works | [{"owner": "知了/明鉴", "stage": "rj1-1", "status": "active", "work": "结构化动作契约 schem... |
| gate | ① L1 机械验证 fail-closed 达标才进 L2 ② L2 规则灰度（影子模式误杀率达标）才转硬阻断 ③ L3 语义软门只决定 retry/escalate ④ 每动作四段闭环：授权(R027)→锁(R029)→验证(本蓝图)→复核(M4) |
| status | active |
| ts | 2026-09-01T09:51:21 |

## 一、主线

- **audit**：审计证据层 — 全量审计链：谁提议/依据/逐条校验结果/谁放行——可回放可复核
- **loop**：打回循环 — 有界 verify-repair 循环：最大重试+预算上限+单调退化检测→停止降级（人工/L2D）
- **verify**：验证层 — 三层验证漏斗：L1 机械（schema/类型 100%确定性）→ L2 规则（业务断言/红线）→ L3 语义（模型侧软门）

## 二、阶段与子阶段

### 1.0 L1 机械验证 [active]
- rj1-1 结构化动作契约 [active] — AI 只产出 action+参数对象；schema 校验器机械校验（morphllm 六类护栏 format 类）
- rj1-2 类型/格式约束 [active] — JSON Schema/类型检查/参数枚举——100% 确定性 fail-closed
- rj1-3 反向用例自检 [todo] — 每个判定配反向用例（未成功必须 false）——GOV-0901 缺陷教训（M3）

### 2.0 L2 规则验证 [todo]
- rj2-1 业务断言库 [todo] — 红线：成本≤X/库存上限/毛利率≥Y/折扣率∈[0.5,0.9]——可配置断言（Datalog/规则引擎）
- rj2-2 策略编译 [todo] — 业务约束编译为可执行策略，AI 提议必须满足才放行（Policy Compiler 2602.16708）
- rj2-3 灰度影子模式 [todo] — 新规则先只告警不拦截，历史数据回测误杀率→转硬阻断（M3 反向用例）

### 3.0 有界打回循环 [todo]
- rj3-1 verify-repair 循环 [todo] — 不通过→打回重试：最大重试+预算上限+单调退化检测→停止（2607.17641）
- rj3-2 降级路径 [todo] — 停止后统一降级：L2D 人工/简化方案/放弃（衔接 d33-adoption-learning）
- rj3-3 失败信号回流 [todo] — 校验失败原因结构化回喂提议层（学习信号，AlphaProof 强化学习模式）

### 4.0 审计证据 [partial]
- rj4-1 全量审计链 [active] — 谁提议/依据数据/逐条校验结果/谁放行——可回放（M5 证据字段）
- rj4-2 证据字段规范 [todo] — API 响应体/状态快照/enterTime 等证据入库（GOV-0901 M5）
- rj4-3 月度审计 [todo] — 抽 N 条核对验证证据，入 HR 台账（事件回顾 P4）
- rj4-4 门健康审计 [todo 2026-09-06] — gate-auditor 扫纸面门 vs 结构门(现 24结构/51纸面) → gate-repairer 加固 → mechanism.gates 门健康可见; 节奏并入 R006 月度巡检

## 三、工作项（works）

| 状态 | 工作 | owner | stage |
|------|------|-------|-------|
| active | 结构化动作契约 schema 校验器 | 知了/明鉴 | rj1-1 |
| todo | 业务断言库（成本/库存/毛利/折扣红线） | 明鉴/老登 | rj2-1 |
| todo | verify-repair 有界循环 | 明鉴/4787d717 | rj3-1 |
| todo | 审计证据字段规范（M5） | 司库-HR | rj4-2 |
| todo | 门健康审计（gate-auditor→repairer→mechanism 可见, 并入 R006 巡检） | 明鉴/星桥 | rj4-4 |
| active | 判定器实证对接（知了提供） | 知了 | rj1-1 |

## 四、依赖关系（relations）

- **consumed_by**：aistartup, banking, flowernet
- **depends_on**：agent-network
- **requires**：blueprint-platform

## 四b、自动化开关锁（R027 + Lean4 逻辑锁）

- **rj2-3**：规则灰度→硬阻断自动切换
  - 开关点：`automation-switch on --bp rule-judge --stage rj2-3 --by <人类> --level L3` · 默认态：OFF
  - 熔断：`automation-switch off --bp rule-judge --stage rj2-3`
  - 授权：HumanApproval(L3)

## 五、门禁链

① L1 机械验证 fail-closed 达标才进 L2 ② L2 规则灰度（影子模式误杀率达标）才转硬阻断 ③ L3 语义软门只决定 retry/escalate ④ 每动作四段闭环：授权(R027)→锁(R029)→验证(本蓝图)→复核(M4)

---
*blueprint:rule-judge · v1.0 · 三件套纪律落盘*
