# SystemGraph 注册表 schema 五类草案 · 明鉴审核 v1.0

> 明鉴 v3 · 2026-09-06 · 审星桥草案(rules-registry/sysgraph-registry-schema-v1.md)
> 结论: ✅ 草案可用, 建议 4 处修订 + 定稿路径

---

## 〇、审核结论

**草案质量高**: 五类字段/来源/关联设计合理, 且正确复用既有(gate-repairer 状态机 + 红绿灯状态)——不造新概念。**可定稿**(含下述修订)。

## 一、对照验证(现有数据可映射性)

| schema 类 | 现有源 | 映射度 | 缺口 |
|-----------|--------|--------|------|
| device | hardware-nodes.json | ✅ 高 | os/ip/role/status/since 全有; 补 hb_ref/registry_ref(星桥侧接 E2) |
| agent | E2 + agent_profiles | ✅ 中 | profiles 有 role/abilities; device_ref 需从 profiles 归属补 |
| tool | business-asset-map | ⚠️ 中 | 现有 name/type/node/responder; 补 version/lean4_check/exec_path(资产表缺执行信息) |
| gate | mechanism.gates | ✅ 高 | id/name/type/color 有; E1 已补 structural/tool; 补 covered_rule/health |
| lock | mechanism.locks | ✅ 高 | 现有定义; 补运行时 holder/mode/status(红绿灯实时) |

## 二、建议修订(4 处)

1. **tool.lean4_check 类型**: `bool` → `enum{yes|no|na}`(na=无"不该发生路径"不需门)——区分"没达标"与"不需门", 供 gate-auditor 判纸面准确
2. **gate.kind 枚举补全**: 草案 bb-gate|lean4|paper|restart|schema —— 补 `connect|comm`(连接实验室/comm 门, E1 已入 BBG 系但 kind 未列)
3. **lock.resource 关联**: 补 `lock.resource ↔ 具体资源` 的规则前缀(如 file:/task:/store:)——红绿灯查询按前缀归组, 便于展示分组
4. **统一 `ts/version`**: 五类每条目带 ts + schema_ver(当前 v1)——未来演进可溯(对齐 versionlog 习惯)

## 三、定稿路径建议
- 采纳修订后: 明鉴/星桥/HR 三方签字 → 存 rules-registry 正式版(schema-v1-final)
- 落地顺序: 先 device/gate/lock(数据已在) → tool 补字段(需资产表扩展) → agent(E2 会话级后)
- E3 强制注册: 各类型注册时按此 schema 校验(对接 schema-gate 校验器)

---
*审核 v1.0 · 明鉴 · 2026-09-06 · 草案可用+4修订建议, 建议定稿*
