# Blueprint Platform · 蓝图平台设计 v0.3（2026-08-29 用户深化）

> 设计：HR 司库（资源管理者）· 基础：Evolve Loop 设计 v0.2 + 用户深化要求
> 核心转变：蓝图 ≠ 单一文件，而是「平台」——多蓝图并存、与循环解耦、可多线程消费、标准化工具化插件化

---

## 〇、用户 5 问 → 设计结论

| 用户问题 | 设计结论 |
|---|---|
| 蓝图可以很多个？ | ✅ 多蓝图并存（每蓝图独立 namespace：data/blueprint/<id>/） |
| 与进化循环解耦？ | ✅ Blueprint Platform（供应者）≠ Evolve Loop（消费者）——解耦，循环可消费任意蓝图 |
| 可以多线程？ | ✅ 多循环并行（每循环=一个 goal + 一个蓝图引用），共享护栏 |
| 制定新蓝图过程标准化工具化插件化？ | ✅ blueprint-create 工具 + 标准定义流程（沟通→起草→定稿→发布） |
| 蓝图定义沟通工具化插件化？ | ✅ blueprint-dialog 工具（用户↔智能体结构化对话模板） |
| 9 标准让智能体快速调用引用标注？ | ✅ BP-9 标准（9 字段元数据契约，见 §四） |
| 主动沟通完善蓝图版本迭代？ | ✅ blueprint-refine 循环（执行反馈→主动找用户→版本迭代） |

---

## 一、架构：蓝图平台 vs 进化循环（解耦）

Blueprint Platform（供应层）:
  ├── 多蓝图库（data/blueprint/<id>/）：每个蓝图独立 namespace
  ├── BP-9 标准（统一元数据契约）：所有智能体可快速调用/引用/标注
  ├── blueprint-create（新蓝图制定工具化）
  ├── blueprint-dialog（蓝图沟通工具化）
  ├── blueprint-refine（版本迭代循环）
  └── blueprint-api（webServer：查询/引用/标注接口）

Evolve Loop（消费层，v0.2 已设计）:
  └── 消费任意蓝图（引用 data/blueprint/<id>/stages）→ 多实例并行（每实例=一循环一蓝图）

两者关系：
  - 平台产蓝图（版本化、标准化、可引用）
  - 循环消费蓝图（目标锚定、执行推进、反馈迭代）
  - 循环执行反馈 → 蓝图平台（版本迭代输入）→ 平台再产新版蓝图 → 循环继续

---

## 二、多蓝图 + 多线程设计

### 2.1 多蓝图并存
| 蓝图 id | 示例 | namespace |
|---|---|---|
| flowernet-v2.1 | 花店生意演进（数字化+物理双主线） | data/blueprint/flowernet/ |
| evolve-loop | 自主进化循环自身建设 | data/blueprint/evolve-loop/ |
| 其他业务 | 未来任何蓝图 | data/blueprint/<id>/ |

### 2.2 多线程（多循环并行）
- 每循环 = 一个 goal 实例 + 引用一个蓝图 + 独立状态机
- 并行度受护栏约束：成本门禁（多循环共享预算）+ 红绿灯（共享资源锁）+ 优先级调度
- 循环间通过黑板事件驱动通信（一个完成→另一个可启动）

---

## 三、新蓝图制定流程（标准化工具化）

### 3.1 标准流程（blueprint-create 工具封装）

1. 沟通（blueprint-dialog）：用户↔智能体结构化对话——目标/边界/里程碑/验收
2. 起草：生成蓝图文档（BP-9 标准格式）→ data/blueprint/<id>/draft
3. 评审：用户确认 + 相关角色评审（HR 资源评估/星桥协调）
4. 定稿：v1.0 发布 → data/blueprint/<id>/stages + works
5. 发布通知：黑板广播（相关智能体可引用）

### 3.2 blueprint-create 工具接口

blueprint-create --name <蓝图名> --mainlines <主线> --gate <门禁>
  → 创建 namespace → 初始化 stages/works → 进入 dialog 模式

---

## 四、BP-9 标准（9 字段元数据契约）

让所有智能体快速调用/引用/标注蓝图的统一契约：

| # | 字段 | 说明 | 示例 |
|---|---|---|---|
| 1 | id | 蓝图唯一标识 | flowernet |
| 2 | name | 蓝图名 | 花店生意演进 |
| 3 | version | 版本号（semver） | v2.1 |
| 4 | mainlines | 主线数组（各自主线） | [digital, physical] |
| 5 | stages | 阶段数组（id/name/status） | [d25, d3, d4, p2, p3] |
| 6 | works | 工作数组（挂阶段/属主/状态） | [{stage:d25-3, owner:运营}] |
| 7 | gate | 阶段门禁条件 | ROI_eff>1 |
| 8 | status | 状态（active/partial/todo/done/archived） | active |
| 9 | ts | 更新时间戳 + changelog | 2026-08-29 |

引用语法：blueprint:<id>（如 blueprint:flowernet#d25-3）——智能体可快速引用/标注
标注语法：@blueprint:<id>#<stage>（如 @blueprint:flowernet#d25-3 进行中）

---

## 五、蓝图定义沟通工具化（blueprint-dialog）

### 5.1 结构化对话模板（减少来回 token，一次问全）

| 问题 | 用途 |
|---|---|
| 这个蓝图解决什么核心问题？ | 目标锚定 |
| 分几个阶段？每阶段里程碑？ | stages 规划 |
| 阶段间的 gate 条件？ | gate 定义 |
| 谁执行各阶段？ | works 属主 |
| 完成标准/验收？ | 终态定义 |
| 与现有蓝图关系（独立/依赖）？ | 依赖管理 |

### 5.2 工具接口

blueprint-dialog --id <蓝图id> [--stage <阶段>]
  → 引导式提问 → 收集回答 → 生成/更新蓝图段落

---

## 六、主动沟通版本迭代（blueprint-refine）

### 6.1 迭代触发点
1. Evolve Loop 执行反馈（短板评估发现蓝图缺阶段/缺能力）
2. 外部变化（用户新需求/市场变化/技术变化）
3. 定期复盘（如月度）

### 6.2 迭代流程

触发 → 生成变更提案（diff 建议）→ blueprint-dialog 与用户确认 → 用户批准 → bump 版本（v2.1→v2.2）→ 发布 → 相关循环接收新版本

### 6.3 主动沟通纪律
- 变更必须用户确认（蓝图是用户意图，智能体不擅自改）
- 沟通走 blueprint-dialog 模板（结构化省 token）
- 版本迭代留 changelog（可追溯）

---

## 七、与 Evolve Loop 的关系（更新 v0.2）

| 项 | v0.2（单蓝图耦合） | v0.3（平台解耦） |
|---|---|---|
| 蓝图数量 | 单一（data/blueprint/） | 多蓝图（data/blueprint/<id>/） |
| 循环数 | 单循环 | 多循环并行（护栏内） |
| 目标源 | 硬编码读 stages | 引用 blueprint:<id> 任意蓝图 |
| 版本迭代 | 无 | blueprint-refine（用户确认后 bump） |
| 沟通 | 一次性定义 | 持续对话（dialog 工具化） |
| 标准 | 无 | BP-9（统一契约） |

---

## 八、实现里程碑（v0.3 更新）

| 里程碑 | 内容 |
|---|---|
| P0 标准定稿 | BP-9 字段契约 + 引用/标注语法（用户确认） |
| P1 蓝图库 | data/blueprint/<id>/ 多蓝图 namespace 规范 + 现有 flowernet 迁移到标准格式 |
| P2 dialog 工具 | blueprint-dialog（结构化沟通模板） |
| P3 create 工具 | blueprint-create（新蓝图制定流程） |
| P4 refine 循环 | blueprint-refine（版本迭代+用户确认） |
| P5 平台 API | blueprint-api（webServer 查询/引用/标注） |
| P6 解耦接入 | Evolve Loop v0.3 改为消费 blueprint:<id>（多实例） |
| P7 闭环验证 | 用 flowernet 蓝图 + 一个新蓝图并行验证 |

---

## 九、开放问题（待用户/星桥裁决）

1. BP-9 字段是否够用（9 字段契约定稿）？
2. 现有 flowernet 蓝图是否立即迁移到 BP-9 标准格式？
3. blueprint-create/dialog/refine 是三个独立工具还是一个工具三命令？
4. 多线程并行度上限？（护栏：成本预算内）
5. 蓝图迭代的用户确认通道：异步审批队列（不阻塞）还是即时弹窗？

---
*Blueprint Platform 设计 v0.3 · HR 司库 · 2026-08-29 · 待用户批准*