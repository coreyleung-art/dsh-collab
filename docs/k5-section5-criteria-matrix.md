# 立项书 §5 判据对照表（每条附可复跑命令）

> Q-K 上下文存活后端 · v0.7.2 · 2026-10-10 · 节点 mac-mini
> ★ 本表把立项书 §5 的**每一条**判据落成「状态 / 复跑命令 / 证据」三列。
> ★ 状态为**实测**，不是声称 —— 凡未跑者一律标 `⏸ 需真跑`，**不标"待验证"含混带过**。

---

## 一、正控（4 条）

| # | 判据（立项书原文） | 状态 | 复跑命令 | 证据 |
|---|---|---|---|---|
| **正控 1** | 构造「活跃窗口 ≥ 阈值」的会话，守卫触发后 `tokenMeter.measure` 的 `totalTokens` **严格下降** | ⏸ **需真跑** | — | 需活体会话（`apply()` 授权） |
| **正控 2** | `retainTokens` 窗口内的最近内容**逐字未变**（sha 比对） | ✅ **达标（离线）** | `node cli.js --recall-check` | 用例 **T 组 6 条**：保活区 = 尾部两条（120 token）；**规范 JSON 逐字节比对未变**；刁钻正文（前导空格/制表符/中文/emoji/尾随空格）逐字保留；计划未改动输入 |
| **正控 3** | 被省略段用 `csx_recall` 取回，与原文**逐字相等** | ✅ **达标（离线）** | `node cli.js --recall-check` | 用例 **B 组 15 条** + 扫描不变量（15 类刁钻正文含 `\u0000`/`\u200b`/全角空格/`\r\n`/千字符逐字节比对） |
| **正控 4** | 守卫阈值**严格小于**官方 `floor(cw×0.8)`（对**所有** cw，含 8192 级小窗）；`preemptRatio ≥ 0.8` 被拒 | ✅ **达标（离线）** | `node cli.js --budget-check` | **170/170**；B32「抢先不变式：9 个 cw 下 `threshold < floor(cw×0.8)`」· B9 含 4 条 `BAD_PREEMPT` 负例 |

## 二、负控（3 条）

| # | 判据 | 状态 | 复跑命令 | 证据 |
|---|---|---|---|---|
| **负控 1**<br>**（立论所系）** | **把活跃窗口压到摘要模板地板以下**（机制二复发条件），本后端**仍能缩小**；若判"缩不动" ⇒ **立项失败** | ✅ **达标（离线）** | `node cli.js --calibration` | 官方地板 **3435**（实测常量）· 本核地板 **192**（最优）/ **2000**（最差）⇒ 区间 **[2000, 3435) 宽 1435**；**★ 官方崩溃点被遮 2466 落在区间内 ⇒ 该点本核必能缩小**。★ 且**非恒真**：要求抬到不可能 ⇒ 本核无地板 ⇒ 报告**必须**报「立项失败」（用例 R 组负控） |
| **负控 2** | 官方 `compaction-basic` 同时在线；本守卫拒动/报错时，官方行为**零变化**（对照事件流） | ◐ **纯半达标 · 并存半需真跑** | `node cli.js --checkpoint-check` | ★ **纯半已达标**（2026-10-10 补 · 我此前整体判「需真跑」是**判粗了**）：新增 **Z2 组 6 条** —— 证明「拒动时零变化」在**结构上**成立：① `decide()` **键集固定且零写载荷** （surfaceOp/shadowedSeqs/handoffText/replacement/append 全不在键集里）· ② 决策对象 **`Object.freeze`** ⇒ 下游无法挂载荷 · ③ ★ **COMPRESS 与非 COMPRESS 的键集完全相同 ⇒ 决策与写彻底解耦**。★ **反向对照已做**：给决策对象注入 `surfaceOp` ⇒ Z2 变红（193/195）⇒ **判据有判别力**。★ 剩余「**并存半**」（官方同进程真跑、对照事件流）需 `apply()` |
| **负控 3** | 阶梯走到尽头时，事件流**必须出现** `WARN` + notice（**不能只有"没动作"**） | ◐ **partial —— 投递半＝宿主不可达（非我方未做）** | `node cli.js --recall-check` | ★ **纯半已达标**：新增 `lib/notice.js` + 用例 **S 组 23 条** —— 通知带 **4 组实测数字** + **闭集成因码**；`isSilent`/`distinguishable` 把「必须与沉默可区分」做成**可跑判据**；`ok=true` 时**抛 `NOT_A_FAILURE`**（不许给成功态发通知，否则通知退化成噪声）。★ **投递半**（真写进事件流）**判定 partial**，原因＝**宿主不可达**（**非我方未做**，2026-10-10 星桥裁 A）：`compaction/notice` **不在**宿主 `KNOWN_SESSION_EVENT_TYPES`（`dsh-session/lib/index.js:1054+`）；且 `session.append` 只认 `sourceEventSeqs`/`surfaceOp` 两个 opts（`dsh-session/lib/index.js:1444-1465`）⇒ **无法**给事件打 `ignorable` 标记 ⇒ 一旦落盘，持久化**读路径拒绝解释整个会话**（`dsh-session-persistence/lib/index.js:1117-1121`，`SessionFormatUnsupportedError`）。★ 现状：只写 `WARN` 日志 + 计数（`guardStats.notices`），**不落未知类型事件**。缺口卡 `data/registry/host-ignorable-event-gap` |

## 三、边界与标准

| # | 判据 | 状态 | 复跑命令 | 证据 |
|---|---|---|---|---|
| **边界** | 空会话 / 只有一条消息 / 活跃窗口已低于任何可行预算 ⇒ 如实判"不可压"，不崩 | ✅ **达标（离线）** | `node cli.js --checkpoint-check` | 用例 **I 组 10 条**：压不动时 `verdict=IMPOSSIBLE` 且**带实测数字**（不静默）；保活吃满 ⇒ `NOTHING_TO_SHADOW`；空条目 ⇒ `NOTHING_TO_SHADOW` 且 `checkpoints=0` |
| **R006 ④** | `--selfcheck` exit 0（含真挂载冒烟三态）· `--lean4-check` A–F 全绿 · `--dry-run` 前后外部状态一致 · 未知旗标 exit 2 | ◐ **部分**（见下） | `node cli.js --lean4-check && node cli.js --dry-run && node cli.js --nope` | A–F **全绿 exit 0** · `--dry-run` exit 0 · `--nope` exit 2 ✅。★ **真挂载冒烟**：`--selfcheck` 默认**不执行 `apply()`**（2026-10-10 加固，禁令要求单独授权）⇒ 显示 `skipped`，总判如实报 ❌「门未生效」，**不粉饰**。加 `--allow-apply` 才会跑（**需授权**） |

---

## 四、汇总

| 类别 | 达标 | 部分 | 需真跑 |
|---|---|---|---|
| 正控 1–4 | **3** | 0 | 1（正控 1） |
| 负控 1–3 | **1** | **2**（负控 3 纯半达标 · **负控 2 纯半达标**） | **0** |
| 边界 | **1** | 0 | 0 |
| R006 | — | 1（真挂载冒烟待授权） | — |

**离线可完成的判据：全部完成。** ★ **本轮修正**：负控 2 此前被我整体判为「需真跑」是**判粗了** —— 其**纯半**（拒动时官方零变化的**结构**证明）已在 Z2 组达标。

**★ 2026-10-10 收口（K6 接线后重述剩余项 —— 三态：通过 / 不通过 / 未证）**：

| 剩余项 | 三态 | 说明 |
|---|---|---|
| **正控 1** | **未证** | 需在役跑（`totalTokens` 触发前后严格下降）。★ 接线已在盘面完成；**须先等一次 CLD 重启**（插件在 CLD 启动时载入） |
| **负控 3 投递半** | **partial**（非"未证"） | 已查明为**宿主不可达**（原因与行号证据见负控 3 行）：`compaction/notice` 非宿主已知事件类型、`append` 无 `ignorable` 入口 ⇒ 落盘会让**会话读不回来**。**不是我方未做** ⇒ 如实记 partial，不记 closed |
| 负控 2 并存半 | 未证 | 官方同进程真跑、对照事件流；同样须在役 |

★ 依 **§5.1 三态**：**「未证不得记 closed」**。把「宿主不可达」如实标出来**本身就是产出**（缺口卡 `data/registry/host-ignorable-event-gap`）。
★ 机械判据：`python3 tools/k6-partial-guard.py`（不许把 partial 静默改成"通过"；partial 必须带原因）。

## 五、一次性复跑全部判据

```
cd ~/dsh-collab/devices/dsh-plugin-context-survival
node cli.js --checkpoint-check   # 180/180 · sha256=29fc6e9ab955f90d…
node cli.js --recall-check       # 142/142 · sha256=230e25f225771e44…   ← 本轮 +S/T 组
node cli.js --budget-check       # 170/170 · sha256=aa2472270d9db9b5…
node cli.js --calibration        # exit 0 = 区间非空 ∧ 崩溃点判据真
node cli.js --lean4-check        # A–F 全绿
node --test lib/*.test.js        # 36/36（含 ledger-io 真文件往返 8 条）
```
