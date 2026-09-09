# blueprint-dialog/refine · bp2-4 落地 v1

> 明鉴 v2 · 2026-09-06 · blueprint-platform P2 推进到完成
> P2 现状: bp2-1 ✅create · bp2-2 ✅registry · bp2-3 ✅shell(registry 含 deps/impact) · bp2-4 active(本件)

## 一、bp2-4 意图(对话式蓝图维护)
蓝图创建/迭代不靠手写 md/json, 而是**对话驱动**: 用户说自然语言(如"给 mtm 加个新阶段"),
工具用结构化规则把变更应用到蓝图数据(黑板 data/blueprint/<id>) — 与明鉴对话链路无缝。

## 二、bb-blueprint-dialog.py(实现)
对话意图 → 蓝图操作:
- `--create <id> --name X --dim 域` : 新建蓝图骨架(BP-9 字段)
- `--add-stage <id> --name Y --status` : 加阶段
- `--add-substage <id> --stage Z --name S --note` : 加子阶段
- `--set-status <id> --stage X --status done/active/...` : 改状态
- `--add-work <id> --stage X --work W --owner O` : 加工作项
- 每次操作: schema-gate 校验(BP-9 字段/引用)+ 幂等 + 审计落黑板
- 对话式 = 明鉴理解用户 → 调本工具执行(工具做结构保证)

## 三、与三工具闭环
```
blueprint-create(建) + dialog(对话改) + registry/shell(查/分析)
→ 蓝图全生命周期: 建→改(对话)→查/依赖/影响 → 完整度检查把关
```

## 四、R006
1 独立脚本 · 2 --selfcheck · 3 黑板可配 · 4 --tool-version · 5 本文档
6 版本 · 7 操作日志 · 8 变更落黑板 · 9 CLI 治理

## 五、验收
| # | 标准 |
|---|------|
| A1 | --create 建蓝图骨架(可被 integrity 检查 60+) |
| A2 | --add-stage/substage/set-status 幂等应用 |
| A3 | 每次写前 schema-gate 校验(字段/引用) |
| A4 | 操作审计黑板(data/blueprint/audit/) |
| A5 | 演示: 对话式给某蓝图加阶段 → 详情/图更新 |
