# gate-auditor / gate-repairer 落点评估 v1.0

> 明鉴 v3 · 2026-09-06 · 应星桥请求(用户指示扫描 SystemGraph 评估落点)
> 工具: gate-auditor v1.1(纸面门审查) + gate-repairer v3.0(纸面门加固)
> 起源: archify 事故(纸面门被跳过) · R006#10 · lean4-check 同源

---

## 〇、工具本质定位

```
纸面门(声明无工具, 靠人执行可跳过)  ← gate-auditor 识别
结构门(有代码+lean4-check, 不可绕过) ← gate-repairer 加固(annotate/scaffold)
```

它们不是"内容/渲染"工具(非 gallery), 而是**治理层门健康审计工具** ——
审计对象 = 规则账本/流程声明; 产出 = 纸面门清单 + 加固包。

## 一、SystemGraph 域扫描结论

| SystemGraph 域 | 是否落点 | 理由 |
|---------------|---------|------|
| gallery 渲染/工具系 | ❌ | 渲染/内容工具族, 两工具非此性质 |
| checker/integrity 系 | ⚠️ 部分 | 内容检查器(蓝图完整度), 非"规则门"检查——非同族但可关联 |
| mechanism.gates 域 | ✅ **展示落点** | mechanism.json 已有 gates 结构门清单(restart-gate/自查门/dev-sandbox)——auditor 的"结构门注册表"与此天然对应, 审计结果应映射此域展示 |
| 连接实验室 | ❌ | 智能体连接, 无关 |
| 规则账本治理域(rules-registry) | ✅ **主落点** | 两工具执行于此: 扫 RULES.md/落报告 rules-registry/; 与 R006/Φ9 门系同族 |

## 二、与既有工具整合判断

| 既有 | 整合关系 | 建议 |
|------|---------|------|
| bb-schema-gate(契约门) | **被整合对象** | schema-gate 是"结构门工具"实例——auditor 应把 schema-gate 识别为结构门(注册表已有?), repairer 用其做模式参考 |
| bb-blueprint-integrity/checker | 平行工具 | 蓝图完整性检查(内容向); auditor 是规则门审计(治理向)——不合并, 但 auditor 报告可关联蓝图 gate |
| gallery mechanism.gates | 展示整合 | auditor 报告 → mechanism.gates 数据源(纸面门 vs 结构门状态可见于 SystemGraph) |
| 规则账本 RULES.md | 扫描对象 | auditor 扫 RULES.md 声明; repairer annotate 生成 RULES.md 标注补丁(人工审核后应用) |

## 三、推荐落点(三问回答)

### ① 落 SystemGraph 哪个域?
**主域 = 规则账本治理域(rules-registry)** —— 两工具本就是治理审计/加固工具, 执行于此。
**展示 = SystemGraph mechanism.gates 域** —— 审计结果(门健康: 纸面/结构/已修复)映射 mechanism.json, 使"哪些门是真的"在架构管理器可见。

### ② 能否吸收/整合既有?
- **不合并**到 schema-gate/integrity(各司其职: 前者守数据契约, 后者审规则门)
- **展示整合**: auditor 产出 → mechanism.gates(新增 status: 纸面/结构 + 修复链)
- **注册表整合**: auditor 的 STRUCTURAL_TOOLS 注册表应含 schema-gate/integrity/checker 等本族工具(确认现状)

### ③ 落规则账本治理域?
**✅ 是主落点** —— 与 R006/R-ERR/Φ9 门系并排; 建议:
- gate-auditor/repairer 与 R006 同组(门治理族)
- 新增机制文档: 定期跑 auditor(门健康巡检) → repairer 修复 → mechanism.gates 同步
- 归属: 星桥(规则/门治理主理) + 明鉴(工具族注册表一致性)

## 四、落地建议(供星桥/用户)
1. 工具执行位: rules-registry/(现状已对) — 确认归属主理(建议星桥)
2. 展示整合: auditor 报告映射 mechanism.gates(明鉴做数据桥接, ~小)
3. 注册表核对: STRUCTURAL_TOOLS 含本族全部结构门工具(schema-gate/integrity/checker/connect-execute等)
4. 巡检机制: 门健康月度巡检(或并入 R006 审计)——与竞品 L1 类似节奏, 可挂 sysops
5. 蓝图: rule-judge 蓝图(验证族)加"门健康审计"work, 或归 R006 治理

---
*落点评估 v1.0 · 明鉴 · 2026-09-06 · 主落点规则账本治理域 + 展示落点 mechanism.gates*
