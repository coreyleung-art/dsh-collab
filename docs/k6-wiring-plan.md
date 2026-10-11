# K6 接线方案（写入 → 落盘 → 召回）

> 出件 2026-10-10 · 星桥 `session-e317d6ab` · 插件 v0.11.1
> **为什么有这份文档**：接线是三件互相依赖的改动，而我的上下文已接近上限 ⇒ **不让它随会话丢失**。
> **当前状态**：挂载成功 · 三工具可用 · `guard.enabled=false` · `implemented=false`（诚实）。

---

## 〇、★ 先说顺序（这决定了一切）

`csx_recall` 依赖**账本**，而账本**只在产出检查点时写入**。

⇒ **先接召回 = 只会永远返回「账本为空」** —— 诚实但无用。

**⇒ 正确的依赖顺序：**

```
① 写入（replace.js → session.append）   ← 承重件，必须先做
      ↓
② 落盘（产出检查点后写 ledger-io）
      ↓
③ 召回（csx_recall → ledgerForUse + recall）
```

★ 同理，**正控 1 / 负控 3 投递半 在 ① 完成前不可达** —— 它们验的正是 ①。

---

## 一、① 写入接线（承重）

**目标**：守卫触发时，把 `lib/replace.js` 的产出真正接到会话上。

**官方契约（逐字，`dsh-compaction-basic/lib/index.js:605-616`）**：

```js
session.append("user/message", checkpointMessage, {
  surfaceOp: { op: "replace", start, end },
  sourceEventSeqs: [startEvent.seq, summaryEvent.seq, ...shadowedSeqs]
});
```

**本插件已就位的东西**：

| 件 | 位置 | 状态 |
|---|---|---|
| `buildReplacement(...)` | `lib/replace.js` | ✅ 纯层，产出 `{ surfaceOp:{op,start,end}, shadowedSeqs, handoffText, entryText, entryKind }` |
| `requiresHostMeterCheck: true` | 同上 | ✅ 契约标记 —— **接线时须遵守：改写前用宿主 meter 复算一次** |
| 契约判据 | `--checkpoint-check` O 组 **21 条** | ✅ 全绿 |

**要做的**：
1. 在 `agent/pre-step` 守卫钩子里，拿到 `session`（现在只有 `guardStats`，**没拿 session**）
2. 触发判定通过（`decide()` → `DECISION.COMPRESS`）且 `planCheckpoint()` ok 时：
   - 按 `requiresHostMeterCheck` 契约，用宿主 `tokenMeter` **复算**一次被遮 token 数
   - 复算不满足 ⇒ **放弃写入并告警**（不硬写）
   - 满足 ⇒ `session.append(entryKind, entryMessage, { surfaceOp, sourceEventSeqs })`
3. `guardStats.compress++` 并记 `lastAt`

**★ 不可绕过的前提（已在插件里做成结构约束，接线不得削弱）**：
- `enableGuard` 默认 **false** —— 接线完成后**仍保持 false**，直到 ① 被独立验证
- 并发护栏（`lib/events.js` 逐字复刻官方 `assertNoActiveCompaction`）**必须在写前再判一次** —— 官方压缩在途时**绝不写**

**验证**：
- 纯层：`--checkpoint-check`（已 195/195）
- 端到端：**正控 1** —— 触发前后各记 `totalTokens`，判据是**严格下降**
- 失败处置：读数不降 ⇒ **真缺陷**，按 R030 不得声称达标，回报原始读数，**不自行调参**

---

## 二、② 落盘接线

**目标**：每次产出检查点，把账本写到磁盘，供 ③ 召回。

**已就位**：`lib/ledger-io.js`（**本插件第一个无需挂载即可完整验证的副作用层**）
- `saveLedgerFile(filePath, ledger)` —— 确定序序列化 + 原子写（tmp + rename）
- `loadLedgerFile` / `ledgerForUse` —— **三态读 `ABSENT` / `OK` / `DEGRADED`**（**绝不静默给空**）
- 双上限（`maxCheckpoints` + `maxChars`）+ `evicted` 记账

**要做的**：
1. **配置项**：在 `cordis.patch.yml` 加 `ledgerFile:`（默认建议 `~/.dsh/ledger/context-survival.jsonl`）
2. ① 写入成功后：`recordCheckpoint(ledger, ...)` → `saveLedgerFile(ledgerFile, ledger)`
3. ★ **落盘失败不得静默**：写失败 ⇒ 记 `guardStats` + 告警，**不影响会话**（观察器契约：绝不抛出）

**验证**：`--recall-check`（已 156/156）· 真文件往返 8 条（`node --test`）

---

## 三、③ 召回接线

**目标**：`csx_recall` 从「`implemented:false`」变成真能取回。

**已就位**：
- `ledgerForUse(filePath)` → `{ status, ledger, reason }`（三态）
- `recall(ledger, target)` → `{ status: HIT|MISS|DEGRADED, entries, text, evicted, reason }`
- `resolveRecallTarget({kind, id})` —— 结构门（枚举 + 有界数字/区间，**不接受路径/命令/URL**）

**要做的**（把 `lib/index.js` 里 `csx_recall` 的 `execute` 换成）：

```js
const led = ledgerForUse(LEDGER_FILE);
if (led.status !== READ_STATUS.OK) {
  // ★ 三态如实回报：**账本不可用 ≠ 该内容不存在**
  return { ok: true, target, status: RECALL_STATUS.DEGRADED, reason: led.reason, ... };
}
return { ok: true, target, ...recall(led.ledger, target) };
```

**★ 铁律（已在 S/R 组钉死，接线不得削弱）**：
- **`DEGRADED` 绝不冒充 `MISS`** —— 账本读不回来时，**不得**说「该内容不存在」
- 工具描述里的 `implemented:false` 与 `coreStatus.wired:false` **接线后须同步改**（否则又是「工具契约滞留」—— 本会话已犯过一次）

**验证**：写一个账本 → 三种 target 各召回一次 → 逐字比对

---

## 四、三件的共同纪律

| 纪律 | 依据 |
|---|---|
| **每件先跑纯断言 + 闸门，再重启验端到端** | 本会话实证：`output.render` 缺失这类缺陷**只有真实调用能发现** |
| **`enableGuard` 接线后仍保持 false**，直到 ① 被独立验证 | 目标明文 |
| **契约变更须同步描述** | 本会话已犯过一次（三工具文案滞留） |
| **门不通过就报不通过**，不自行调参 | R030 |
| **看不到就报看不到** | 验收会话已示范 |

---

## 五、接线完成后的验证清单（第 2 层）

见 `notes/mac-mini/csx-layer2-verification-ready`：

1. **正控 1** —— 触发前后 `totalTokens` **严格下降**
2. **负控 3 投递半** —— 事件流里**真出现** `compaction/notice`（不是看返回值）
3. **负控 2 并存半** —— 官方 `compaction-basic` 同时在线，本守卫拒动时官方**零变化**

★ 三项各自**独立报**，不得由一项通过推断另一项。

---

## 六、当前状态（本文件写作时）

| | |
|---|---|
| 挂载 | ✅ 三工具在活体工具表里 |
| `apply()` | ✅ 零异常，注册 3 工具 |
| `enableGuard` | ✅ **false**（守只测量） |
| `implemented` | ❌ **false —— 三件接线一件都没做** |
| 纯层 | ✅ 195 + 156 + 170 断言全绿 · 七门 exit 0 |
| R006 | 7/10 |
