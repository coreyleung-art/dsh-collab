# Evolve Loop 插件 · 详细设计方案 v0.2（2026-08-29 细化）

> 设计：HR 司库（资源管理者）· 调研基础：research/evolve-loop-survey-2026-08-29.md
> 形态：dsh-plugin-evolve（插件为主）+ evolve preset（可选）· 状态：设计细化中，待用户批准
> ⚠️ v0.3 更新：蓝图平台化（Blueprint Platform 设计 v0.3）——蓝图与循环解耦（多蓝图/多线程/BP-9 标准/沟通工具化/版本迭代）。本设计的目标源改为引用 blueprint:<id> 任意蓝图，非硬编码 data/blueprint/。详见 research/blueprint-platform-design-v0.3.md

---

## 〇、关键发现（细化中搜集的信息）

| 发现 | 意义 |
|---|---|
| 蓝图体系已存在（data/blueprint/，v2.1，数字化 2.5→3.0 + 物理 2.0，子阶段/里程碑/works 挂载） | **蓝图目标锚点现成**——Evolve Loop 直接消费 data/blueprint/stages + works，无需新建蓝图体系 |
| gate 机制已存在（3.0 端侧 ROI_eff>1 才进下一阶段） | 循环边界天然存在——gate 即进化循环的「阶段门」 |
| token 使能计划进行中（BLACKBOARD_TOKEN v1.3.2，端侧升级中） | 循环需要 token 通道（黑板写/读），需等端侧同步完成 |
| KB 246 docs/11957 chunks（ops-science-research） | 技能库/经验沉淀容量充足 |
| goal 工具当前无活动目标 | Evolve Loop 首次运行时创建蓝图锚定 goal |
| Reflexion/Voyager/self-evolving 论文已入库 | 三范式实现依据现成 |
| dsh-self-improved 插件（GitHub madage）未安装 | 可评估借鉴其 L0 capture→L1 memory 分层 |

---

## 一、架构设计（插件形态）

### 1.1 插件结构（按 R006 插件化标准 8 项）

dsh-plugin-evolve/
  ├── package.json          （版本管理，R006-6）
  ├── lib/index.js         （apply 入口 + webServer API）
  ├── lib/client.js        （面板 UI）
  ├── lib/adapt.js         （dsh 版本自适应，R006-4）
  ├── lib/evolve-core.js   （循环核心：状态机）
  ├── lib/shortboard.js    （短板评估器）
  ├── lib/skill-lib.js     （技能库管理）
  ├── lib/reflexion.js     （反思回归模块）
  ├── lib/curriculum.js    （课程推进/下一题选择）
  └── README.md            （文档化，R006-5）

### 1.2 数据流（六步循环）

蓝图 data/blueprint/ → ① 目标解析（goal 锚定当前 active 子阶段）→ ② 执行-反思（Reflexion）→ ③ 技能沉淀（沉淀链 5 步，造牌）→ ④ 短板评估（shortboard：能力表 vs 蓝图差距）→ ⑤ 课程推进（curriculum：选下一子阶段/新问题）→ ⑥ 目标校验（gate 检查：ROI_eff>1?）→ 循环

### 1.3 状态机

IDLE → PARSING(目标解析) → EXECUTING(执行) → REFLECTING(反思/失败回归) → SEDIMENTING(技能沉淀) → ASSESSING(短板评估) → ADVANCING(课程推进) → GATE_CHECK(目标校验) → IDLE 或 COMPLETE

状态迁移表：
| 当前 | 事件 | 迁移 |
|---|---|---|
| IDLE | 蓝图 active 子阶段存在 | PARSING |
| PARSING | 里程碑解析完成 | EXECUTING |
| EXECUTING | 任务成功 | SEDIMENTING |
| EXECUTING | 任务失败 | REFLECTING |
| REFLECTING | 反思完成可重试 | EXECUTING（重试） |
| REFLECTING | 反思完成不可修 | ASSESSING（记短板） |
| SEDIMENTING | 技能沉淀完成 | ASSESSING |
| ASSESSING | 评估完成有新问题 | ADVANCING |
| ASSESSING | 评估完成无短板 | GATE_CHECK |
| ADVANCING | 下一题选定 | EXECUTING |
| GATE_CHECK | gate 通过 | ADVANCING（下一阶段） |
| GATE_CHECK | gate 未过 | IDLE（等条件） |
| GATE_CHECK | 蓝图全完成 | COMPLETE |

---

## 二、模块设计

### 2.1 目标解析（PARSING）
- 读 data/blueprint/stages（当前 active 子阶段）+ data/blueprint/works（各工作归属）
- 用 goal 工具创建/更新锚定目标（objective=当前子阶段名）
- 输出：可执行里程碑清单（每个 work 一项）

### 2.2 执行-反思（EXECUTING + REFLECTING，Reflexion 范式）
- 执行：调工具/委派子代理完成任务（按 work 归属）
- 回馈：结果成功/失败/部分
- 失败→反思：生成反思记录（失败原因/修复方案/教训）→ 写 KB（reflexion 库）→ 重试或标记短板
- 重试上限：3 次（防死循环）

### 2.3 技能沉淀（SEDIMENTING，Voyager 技能库范式）
- 成功能力 → 沉淀链 5 步（落盘 docs/ → 入库 KB → 向量化 → 登记 registry → 报告）
- 造牌：新工具/脚本 → tech-choice-evaluator.py 选型 → 开发 → R006 标准 → registry 登记
- 技能库：KB 即技能库（检索即可复用）——不重复造轮子（research-first-policy）

### 2.4 短板评估（ASSESSING，self-evolving 范式）
- 输入：registry 能力表（agent_profiles）+ 蓝图需求（当前阶段 work 所需能力）
- 规则层：对比需求关键词 vs 现有能力（缺什么牌）——纯规则零 LLM
- LLM 层：复杂差距评估（规则判定 review 时升级）
- 输出：短板清单（缺牌）+ 建议（找牌=复用现有/造牌=新开发）

### 2.5 课程推进（ADVANCING，Voyager 课程范式）
- 候选：同阶段未完成 works + 下一阶段 works + 短板衍生问题
- 选择：按价值排序（gate 优先/瓶颈优先/依赖优先）
- 输出：下一题（交给 EXECUTING）

### 2.6 目标校验（GATE_CHECK）
- 读 gate 条件（当前 3.0 端侧 ROI_eff>1）
- 通过→推进下一阶段；未过→IDLE 等条件（如端侧升级完成）
- 蓝图全完成→COMPLETE（用户确认）

---

## 三、护栏设计（关键）

| 护栏 | 机制 |
|---|---|
| 成本门禁 | 每轮消耗预算（approval-config cost_gate：单任务 L0-L3）+ 全局熔断（日 ¥100/200） |
| 循环上限 | 反思重试 3 次上限；单轮执行超时（600s 默认） |
| 用户打断 | 任何状态可 STOP（用户指令优先） |
| 造牌纪律 | 找牌优先（research-first-policy）→ 无现成才造（评估器判定） |
| 蓝图锚定 | 目标永远挂蓝图（不跑题）——每次 ADVANCING 校验是否仍在蓝图内 |
| 红绿灯 | 动共享资源走 agent_light→lock→unlock |
| 审批 | 高危操作（L3/L4/12 硬升级）走审批分级 |
| 删前考古 | 清理旧工具走 pre-delete-archaeology.py |

---

## 四、与现有机制衔接

| 现有机制 | 衔接点 |
|---|---|
| data/blueprint/（蓝图 v2.1） | 目标源（stages/works/gate） |
| goal 工具 | 锚定当前子阶段为活动目标 |
| 沉淀链（sedimentation） | 技能沉淀/造牌留档 |
| tech-choice-evaluator | 造牌语言选型（R010） |
| pre-delete-archaeology | 工具清理（R007） |
| registry（v1.0.358） | 能力登记/工具登记 |
| KB ops-science-research | 技能库/经验/论文依据 |
| 黑板事件驱动 | 循环触发（sse-sub）与状态广播 |
| token 使能（v1.3.2） | 黑板认证通道（依赖端侧同步） |
| R001-R010 规则账本 | 全部纪律自动适用 |

---

## 五、开发里程碑（待批准）

| 里程碑 | 内容 | 依赖 |
|---|---|---|
| M0 前置 | token 使能端侧同步完成（i9/MBP 升 v1.3.2） | 星桥/端侧 |
| M1 骨架 | 插件脚手架（package.json/apply/adapt/README）+ 状态机核心 | R006 标准 |
| M2 目标解析 | data/blueprint 读取 + goal 锚定 | M1 |
| M3 执行-反思 | Reflexion 模块（执行/回馈/反思/重试） | M1 |
| M4 技能沉淀 | 沉淀链集成（造牌走 tech-choice-evaluator） | M2+M3 |
| M5 短板评估 | shortboard 规则层（能力表 vs 蓝图差距） | M2 |
| M6 课程+校验 | curriculum 选题 + gate 检查 | M4+M5 |
| M7 闭环验证 | 端到端跑通（选一个蓝图子阶段实测） | M6 |
| M8 落链 | registry 登记 + KB 入库 + 报告 | M7 |

---

## 六、开放问题（需用户/星桥裁决）

1. 循环触发：事件驱动（黑板变更触发）还是定时（每日一轮）还是手动（用户说开始）？
2. 短板评估的 LLM 升级阈值：规则层 review 时升级（省 token），还是每轮都 LLM 评估？
3. dsh-self-improved 插件：先评估是否直接扩展（省开发）还是全新自研（干净）？
4. preset：evolve 模式预设（工具面收窄+纪律注入）是否需要？
5. 循环的「注意力」：单线程顺序循环 vs 多线程并行（多个 work 并发）？

---
*Evolve Loop 详细设计 v0.2 · HR 司库 · 2026-08-29 · 待用户批准*