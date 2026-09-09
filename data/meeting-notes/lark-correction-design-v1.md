# 妙记口语自纠正工具库 · 设计（v1.0）

驿使 92623479 · 2026-09-05 · J42 需求设计文档
协作：明鉴出种子/蓝图实体，驿使建工具库并集成妙记管线

## 背景

用户国语口音 + 飞书妙记 ASR 识别不完全正确 → 会议文本实体常有误（实例：华云系=桦桓艺 同音混淆）。需求：口语自纠正工具库（同音 + 向量语义匹配）。

## 架构

```
lark-notes 收取（妙记章节文本）
  → 校正管线（correction-lib.py scan）
     ① 种子加载（correction-seeds + entity-alias-map）
     ② 同音/近音匹配（拼音近似——华云系/华宏系/桦桓艺同音族）
     ③ 向量语义匹配（章节上下文 → bge-m3 向量 → 与实体描述比对）
     ④ 建议生成（原文→候选→置信度）
  → 校正报告（黑板 data/meeting-notes/corrections/ + 本地落盘）
  → 人机闭环（高置信自动应用标记；低置信待确认）
```

## 组件

| 组件 | 职责 |
|---|---|
| lark-correction/correction-lib.py | 核心：种子/拼音/向量/扫描/校正建议 |
| correction-seeds.json | 实体→别名种子（明鉴已建，待扩充） |
| entity-alias-map.json | 别名→实体详细映射（明鉴已建） |
| 校正报告输出 | 黑板 data/meeting-notes/corrections/ |

## 同音匹配（核心逻辑）

- 实体/别名 → 拼音（无 pypinyin 时用内置同音字族表：华/桦/花 huà-huá 等）
- 妙记文本扫描疑似实体（种子实体在文本中的变形）
- 近音判定：拼音编辑距离 ≤1 或同音字族命中
- 实例：华云系(pinyin: hua-yun-xi) ≈ 桦桓艺(hua-huan-yi) → hua 同音族命中 → 候选桦桓艺公司

## 向量语义匹配

- 章节文本切片 → Ollama bge-m3 向量（11434）
- 实体描述（entity-alias-map evidence/domain）向量化缓存
- 语义相似度 > 阈值 → 交叉验证同音候选

## 置信分级

- HIGH：精确别名命中 或 用户确认过（entity-alias-map confidence=high）→ 自动应用
- MED：同音+向量双匹配 → 建议（待用户/agent 确认）
- LOW：仅同音 或 仅向量 → 标记待查

## 集成

- feishu-minutes-fetch.sh 收取后自动调 correction-lib.py scan（新增妙记）
- 输出校正报告到黑板 + 本地 ~/.dsh/meeting-notes/corrections/

## 交付

1. correction-lib.py（种子加载/拼音同音/向量匹配/扫描/报告）
2. 种子扩充机制（扫描发现的疑似别名自动建议加入种子，人审）
3. 向量通道（Ollama bge-m3，复用现有 embedding 体系）
4. 与每日收取管线集成（fetch.sh 后置 hook）
