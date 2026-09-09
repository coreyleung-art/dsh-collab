# blueprint:blueprint-platform · 蓝图平台本身（多蓝图库 + BP-9 标准 + 工具化制定流程） · v1.0（源自 v0.3 设计）

> 生成：bb-blueprint-create.py · 2026-09-01T06:11:28 · 三件套纪律（文档/代码/依赖）
> 状态：active · 门禁：① P0 蓝图库+relations 齐全才进 P1 ② P1 标准定稿（引用语法扩展）才进 P2 ③ 每工具 R006 九标准+Rust 化评估
> 依据：research/blueprint-platform-design-v0.3.md + 用户深化要求（2026-08-29/09-01）

## 〇、BP-9 元信息

| 字段 | 值 |
|------|-----|
| id | blueprint-platform |
| name | 蓝图平台本身（多蓝图库 + BP-9 标准 + 工具化制定流程） |
| version | v1.0（源自 v0.3 设计） |
| mainlines | {"library": {"desc": "多蓝图并存 data/blueprint/<id>/ 独立 namespace + relations 关系网络",... |
| stages | [{"id": "bp0", "mainline": "library", "name": "多蓝图库", "stage": "P0", "status": "... |
| works | [{"owner": "明鉴", "stage": "bp0-1", "status": "active", "work": "5 蓝图并存管理（独立 name... |
| gate | ① P0 蓝图库+relations 齐全才进 P1 ② P1 标准定稿（引用语法扩展）才进 P2 ③ 每工具 R006 九标准+Rust 化评估 |
| status | active |
| ts | 2026-09-01T05:50:35 |

## 一、主线

- **library**：蓝图库 — 多蓝图并存 data/blueprint/<id>/ 独立 namespace + relations 关系网络
- **standard**：BP-9 标准 — 9 字段契约 + 引用/标注语法（blueprint:<id>#<stage> / @blueprint:<id>）
- **tooling**：工具化 — blueprint-create/dialog/refine + registry/shell（制定/沟通/迭代/交互全工具化）

## 二、阶段与子阶段

### P0 多蓝图库 [active]
- bp0-1 5 蓝图并存 [active] — flowernet/flowernet-platform/agent-network/blueprint-platform/aistartup ✅
- bp0-2 relations 关系网络 [todo] — 父子/依赖/派生/引用 4 关系类型（用户定案）+ 影响分析

### P1 BP-9 标准 [active]
- bp1-1 九字段契约 [done] — id/name/version/mainlines/stages/works/gate/status/ts ✅
- bp1-2 引用/标注语法 [active] — blueprint:<id>#<stage> ✅ + 跨蓝图引用扩展

### P2 工具化 [partial]
- bp2-1 bb-blueprint-create [done] — 正式化工具（三件套纪律）✅ 已实现
- bp2-2 bb-blueprint-registry [todo] — 标准化蓝图库（blueprints 单集合 KB + relations 字段）待实现
- bp2-3 bb-blueprint-shell [todo] — 交互 CLI（list/relations/deps-tree/impact）待实现
- bp2-4 blueprint-dialog/refine [todo] — 沟通/迭代工具（Blueprint Platform 三工具排期中）

## 三、工作项（works）

| 状态 | 工作 | owner | stage |
|------|------|-------|-------|
| active | 5 蓝图并存管理（独立 namespace） | 明鉴 | bp0-1 |
| todo | relations 关系网络建模（4 类型） | 明鉴 | bp0-2 |
| active | BB 引用语法扩展（跨蓝图跳转） | 明鉴 | bp1-2 |
| todo | bb-blueprint-registry 实现（单集合+relations） | 明鉴/4787d717 | bp2-2 |
| todo | bb-blueprint-shell 实现（relations/deps/impact） | 明鉴 | bp2-3 |

## 四、依赖关系（relations）

- **consumed_by**：Evolve Loop
- **manages**：flowernet, flowernet-platform, agent-network, aistartup

## 四b、自动化开关锁（R027 + Lean4 逻辑锁）

（无自动化开关声明——非 AI 自动化阶段或待补）

## 五、门禁链

① P0 蓝图库+relations 齐全才进 P1 ② P1 标准定稿（引用语法扩展）才进 P2 ③ 每工具 R006 九标准+Rust 化评估

---
*blueprint:blueprint-platform · v1.0（源自 v0.3 设计） · 三件套纪律落盘*
