# 今晚总目标 · 唯一执行契约 v1

> 明鉴 · 2026-09-10 · 用户在今晚明确督导后立下的铁律，防我因上下文风险反复推倒/覆盖
> **重要性：这是约束我行为的最优先级规则，上下文压缩后也必须遵守。**

---

## 一、今晚唯一总目标（用户明确定义）

**把今天讨论的所有目标/内容，吸收到同一个 HTML 文件里，出一个完整版本。然后用户来排序、分章节。**

- 唯一目标文件：`/Users/coreyleung/dsh-collab/data/industry/flowernet-strategy-complete.html`
- 已通过 8812 访问：`http://127.0.0.1:8812/flowernet-strategy-complete`
- 用户后续：排序、分章节。我**不得预设顺序**（我目前只是"按文档顺序罗列"，最终由用户定）

## 二、铁律（防覆盖/防推倒重来）

1. **绝对不覆盖**：`flowernet-strategy-complete.html` 是唯一完善对象。**绝不 write 覆盖它**（write 会整文件替换=可丢内容）。补内容**只准用 `edit` 增量追加**，且**每次 edit 前必须先 `read`** 当前全文，确保不丢已有章节。
2. **绝不新建替代品**：不造 `-v2`/`-final`/`-new` 等其他 HTML，不搞"重新做一个"，只用这一个。
3. **内容源锚定**：每个章节内容以 **`docs/flowernet-strategy-*.md` 7份文档** 为唯一来源。不凭记忆、不凭上一轮猜测、不凭空发明。
4. **改前必备份**：每次修改前 `cp` 当前文件到 `backup-strategy-complete-*.html`（已备份一个基底）。
5. **每步验证**：改后 `grep -c '<h2'` 确认章节数不减少，再展示给用户。
6. **目标优先**：只做"完善 complete.html"这一件事。**不响应**任何"要不换个颜色/换个布局/做个别版本"的自我发散。用户明确"不要再搞其他东西"。

## 三、已完成的状态（基底，03:30 已备份）

- complete.html 当前 188 行，含章节：〇战略地图 / 一战略方向 / 二第一阶段BP(含IP四象限) / 三终局叙事 / 四落地执行 / 五资本计划 / 六评估坐标
- 7份 md 文档源全在位（flowernet-strategy-map/direction/phase1-bp/endgame-narrative/execution-masterplan/fourstage-capital/milestone-eval-coordinates）
- 8812 路由 `/flowernet-strategy-complete` 已生效
- 备份：`dsh-collab/backup-strategy-complete-*.html`

## 四、用户明确禁止我做的事（诚实记录，绝不重犯）

- ❌ "不要为了造个B把A抹掉" — 曾覆盖原始版
- ❌ "不要再重新搞其他东西" — 曾反复推倒重来
- ❌ "不要为了造另一个东西毁掉原有的" — 曾用新版本覆盖
- ✅ 正确做法：**增量完善唯一文件，改前备份，用md源，不覆盖不新建**

---
*今晚总目标契约 v1 · 明鉴 · 2026-09-10 · 优先级最高，上下文压缩后也必须遵守*
