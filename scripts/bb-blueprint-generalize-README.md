# bb-blueprint-generalize.py — 蓝图泛化探索评估器

> 明鉴 v2 · 2026-09-01 · 泛化探索评估过程工具化插件化
> 位置：`~/dsh-collab/scripts/bb-blueprint-generalize.py`
> R006 九标准合规：CLI 形态 / TCC(--selfcheck) / 文档化 / 版本管理(--tool-version) / 自动落链 / CLI 治理

---

## 是什么

把「蓝图体系泛化探索评估」的五步流程工具化：**内核盘点 → 维度打分 → 垂类对标 → 可能性探索 → 报告落盘**。

## 用法

```bash
# ① 内核盘点（蓝图/工具/规则/模式 + 泛化评级）
python3 bb-blueprint-generalize.py --scan

# ② 泛化维度打分（5 维度就绪度 1-5）
python3 bb-blueprint-generalize.py --dims

# ③ 垂类对标模板（供调研子代理填充）
python3 bb-blueprint-generalize.py --benchmark [--target "宠物,生鲜"]

# ④ 可能性探索框架
python3 bb-blueprint-generalize.py --possibilities

# ⑤ 生成完整报告（黑板+本地）
python3 bb-blueprint-generalize.py --report /path/report.md

# TCC / 版本
python3 bb-blueprint-generalize.py --selfcheck
python3 bb-blueprint-generalize.py --tool-version
```

## 五步流程（沉淀的泛化评估方法）

| 步骤 | 输出 | 说明 |
|------|------|------|
| ① 内核盘点 | 7 组件泛化评级 | 5/7 完全通用（三端/rule-judge/四段闭环/R025/蓝图方法论） |
| ② 维度打分 | 5 维就绪度 | 垂类/平台/场景/地域/行业（1-5） |
| ③ 垂类对标 | 模板框架 | 痛点同构/市场规模/竞争空白/复制难度 四维 |
| ④ 可能性探索 | 4 类框架 | 新蓝图/新能力/新市场/新模式 |
| ⑤ 报告落盘 | 黑板+本地 | 自动聚合①②④+约束 |

## 验证记录（2026-09-01）

- TCC PASS（语法/黑板连通）
- scan：7 蓝图 + 6 规则 + 31 CLI + 内核评级 ✅
- dims：垂类 5/平台 5/场景 3/地域 3/行业 1（平均 3.4/5）✅
- benchmark：宠物/生鲜模板生成 ✅
- report：黑板 + 本地落盘 ✅
- version：v1.0.0 ✅

## 与调研的衔接

- 对标调研（子代理）产出 → 填充 benchmark 模板 → 更新报告
- 泛化候选（petops 等）→ bb-blueprint-create 正式化
- 关联：generalization-full-report（2026-09-01 手工版）→ 本工具自动化

---
*bb-blueprint-generalize v1.0 · 2026-09-01 · 明鉴 v2*
