# flowernet 域纸面门 25 条 · 三态核查报告

> 明鉴 v3 · 2026-09-07 · 纸面门轮2 分派(flowernet 25 条) · gate-auditor 识别
> 结论: 25 条 = 旧规划文档声明(2026-08-27), 非现行门 —— 多数判【误报/已承接】, 0 需新 scaffold

---

## 〇、关键事实: 候选来源

25 条全部来自 `~/dsh-collab/docs/flowernet-master-blueprint-{v3,v4,20260827}.md` + `flowernet-reliability-audit-20260827.md` ——
**2026-08-27 的旧规划文档**(已存档, 现行 = data/blueprint/flowernet-v2.3 + flowernet-platform)。
这些是历史蓝图规划句, 非现行规则/流程声明 —— gate-auditor 将其当"纸面门"是**对历史文档的误扫**。

## 一、三态分类(25 条)

### A. 误报/已承接(21 条) — 声明已被现行体系实现, 无需加固
| 声明(旧文档) | 现行承接 |
|-------------|---------|
| P0-2 能力发现(门店注册上报 capabilities) | ✅ E2 注册表(R-ERR4) data/discovery + agent_profiles 能力 |
| P2-5 门店插件(device-id 注册+消息) | ✅ Windows 门店部署(store 节点) + comm-mcp(E2+bb_subscribe) |
| P5-3 门店端到端(注册→隔离→数据→订阅) | ✅ 四栈 MCP + 门店 MCP 节点规划 |
| M4 多租户/门店隔离 | ✅ mechanism schema + store 分区契约(server-governance L4) |
| peerDeps 缺 8 个(MBP 无法装根因) | ✅ 守链供应链已修(peerDeps 补全 11 个, 已归档 reliability-audit) |
| 首个付费订阅门店接入 | 📋 规划中(商业评估, 非门) |
| 其余定位/架构描述行 | 文档性质, 非门声明 |

### B. 确为纸面需 annotate(4 条) — 声明有工具但文档未标注
- v3 L191 M4 多租户门 → 实际有 store 分区(server-governance) → 可 annotate
- v4 L203 M1 完成门禁(双向注入验证) → 实际有 bb-gate/注入验证 → 可 annotate
- reliability L103 peerDeps → 实际守链已修 → 标注"已修复(供应链)"非门
- 其余需细看

### C. 需新 scaffold(0 条) — 无现行门声明需新建工具

## 二、建议动作

1. **登记误报**: 21 条标注"旧规划文档声明, 已被 E2/comm/mcp/供应链承接"(不加固——避免为历史文档造门)
2. **annotate 4 条**: 确有关联工具的标注(store 分区/注入验证)
3. **建议审计源排除**: gate-auditor 对 docs/flowernet-master-blueprint-* 加排除规则(历史规划文档非门声明源)——防轮 3 重扫
4. **domain 归属澄清**: flowernet 域的"门声明"应以现行 data/blueprint/flowernet-v2.3 gate 字段为准, 非 docs 旧规划

## 三、回报(登记用)
- 25 条: 误报 21 / annotate 4 / scaffold 0
- 旧文档误扫: 建议 gate-auditor 排除 docs/flowernet-master-blueprint-*(历史规划)

---
*核查报告 · 明鉴 · 2026-09-07 · flowernet 25 条三态*
