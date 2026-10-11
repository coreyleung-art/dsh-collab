# K6 挂载前置门清单 + 回滚方案

> Q-K「上下文存活后端」· 生成 2026-10-10 · 节点 mac-mini（CoreydeMac-mini.local / Mac16,10）
> 插件 `dsh-plugin-context-survival` v0.7.1 · **本文件只描述与核验，不执行任何挂载**
> **挂载是不可逆动作，按纪律由用户执行**（本文件即为其执行前的最后一份清单）

---

## 〇、一句话

**前置门已全绿；缺的只有你两个决定：① 挂载点（Q-K6）② 授权执行。** 本文件把这两件事需要的一切都摆在此处。

---

## 一、Q-K6：挂载点三选项（含实测现状）

| 选项 | 现状核实 | 代价 | 与既有惯例的一致性 |
|---|---|---|---|
| **(a) 搬到 `~/dsh-plugin-context-survival`** | 该目录**不存在**（需先搬） | 搬家 ⇒ 24 个文件路径全变；已登记的绝对路径（登记卡 / 索引 / 台账）**全部要改** | 多数插件在 `~/` 下 |
| **(b) 留在 `devices/` + 写绝对路径 link** | 目录**已在此**（`~/dsh-collab/devices/dsh-plugin-context-survival`） | **零搬家**；只改 profile 两处 | ★ **与 `dsh-plugin-cldvoice` 完全同形**（已实测可用） |
| **(c) MCP 形态** | 未评估 | ★ 需重写载体 | ⚠️ 见下「为什么不建议」 |

### ★ 为什么不建议 (c)（本项目的立论所系）

本后端的核心机制是 **`agent/pre-step` 守卫** —— 它在**每个模型步之前自动触发**。
**MCP 服务器注册不了这个钩子**：MCP 只是工具调用协议，模型必须**自己决定**去调。
⇒ 若靠模型自愿调 `csx_recall`，就退化回「靠模型记得」—— 而**恰好在上下文快满、模型最迟钝时，它最不会记得**。
**自动性就是这个设计的全部意义。**

MCP 真正合适的位置是**另一半**：内容存储与按需检索侧。两者互补，不是二选一。

### ★ 选项 (b) 的一处**已知代价**（说清楚，不藏）

本机 `hb-forward.py` 的组件采集器是**硬编码 6 个包名的清单**，且读 `~/<pkg>/package.json`。
⇒ 本插件在 `devices/` 下 ⇒ **不会被采集进 `data/discovery/agents/mac-mini` 的 `services`**。
这**不影响功能**（只影响 R038 组件版本可见性），但**R006 ⑧ 的 ⓑ push 判据本来就卡在这里**（见 §四）。

---

## 二、★ 挂载需要改的**两处**（缺一处不生效）

实测 `dsh-plugin-cldvoice`（已挂载且工作）在 `~/.dsh/profiles/web/package.json` 里出现在**两个位置**：

```
line 23  dependencies:  "dsh-plugin-cldvoice": "link:/Users/coreyleung/dsh-collab/devices/dsh-plugin-cldvoice"
line 83  （bundles 段）  "dsh-plugin-cldvoice",
```

⇒ 本插件挂载时**两处都要加**：

```
dependencies:            "dsh-plugin-context-survival": "link:/Users/coreyleung/dsh-collab/devices/dsh-plugin-context-survival"
bundles（同段）:          "dsh-plugin-context-survival",
```

### ★ 配置项（`cordis.patch.yml` 里的这一段随插件自带，无需改 profile）

```yaml
enableGuard: false      # ★ 挂载后仍为 false；首次冒烟通过后才谈开启
retainTokens: 5120      # K3 已消费（保活窗口）
preemptRatio: 0.7       # 抢先上限（< 官方 0.8，否则抛 BAD_PREEMPT）
```

---

## 三、前置门清单（全部实跑于 2026-10-10，状态为**实测**非声称）

| # | 判据 | 复跑命令 | 实测 |
|---|---|---|---|
| 1 | K3 决策核 180 条 | `node cli.js --checkpoint-check` | ✅ exit 0 · `sha256=29fc6e9ab955f90d…` |
| 2 | K4 召回纯核 113 条 | `node cli.js --recall-check` | ✅ exit 0 · `sha256=8a4b416ba5ce5468…` |
| 3 | K2 预算与守卫 170 条 | `node cli.js --budget-check` | ✅ exit 0 · `sha256=aa2472270d9db9b5…` |
| 4 | **K5 负控 1（立论所系）** | `node cli.js --calibration` | ✅ exit 0 · 区间 [2000, 3435) 宽 1435 · **崩溃点 2466 落在区间内** |
| 5 | R006⑩ 结构门 A–F | `node cli.js --lean4-check` | ✅ exit 0 |
| 6 | node:test（含真文件往返） | `node --test lib/*.test.js` | ✅ 36/36 |
| 7 | 零外部变更 | `node cli.js --dry-run` | ✅ exit 0 |
| 8 | 用法错误退出码 | `node cli.js --nope` | ✅ exit 2 |
| 9 | 三段能力边界 | `node cli.js --selfcheck` | ✅ 输出三段（冒烟 `skipped`，**符合预期**，见下） |
| 10 | ★ 真挂载冒烟 | `node cli.js --selfcheck --allow-apply`（**需授权**） | ⏸ **未跑**（见 §六） |

**★ 第 9 项的 `skipped` 是正确的、不是缺陷**：`--selfcheck` 默认**不执行 `apply()`**
（2026-10-10 加固 —— 该冒烟会真执行 `apply()`，而禁令要求单独授权）。
总判随之如实报 ❌「门未生效」，**不粉饰**。

---

## 四、R006 十项现状（PSTD/1.0.4 实测）

✅ **R3** CLD 自适应 · **R4** dsh 版本自适应 · **R5** 文档化 · **R6** 版本管理 · **R7** 统一日志 · **R9** CLI 治理（6 项）
⚠️ **R1** 真挂载冒烟：审计器未启用 deep ⇒ 显示 skipped。**非本插件缺件**（第 10 项能跑，但需授权）
⚠️ **R2** 三段能力边界：已按判据归位，待审计器复评
⚠️ **R8** 自动落链：**ⓐ pull ✅ 达标**（登记卡 200 · KB 命中 0.914）· **ⓑ push ❌ 未达** ⇒ 已按要求**显式标注 pull-only（有已知风险）**
⚠️ **R10** 约束前置：两处告警已判读 —— `lib/gate.js` 的 exec 命中为**假阳性**（实为 `RegExp.prototype.exec`）· `cli.js rmSync/unlinkSync` 为**正当清理**

### ★ R8 ⓑ 与 K6 的关系（重要）

R006 ⑧ 的 ⓑ push 判据要求「产出在**默认注入面**里 ⇒ 不查也会看到」，其可机械核判据之一是：
**ⓑ-2 注册为可调用工具（出现在会话工具表里）**。
⇒ **挂载即满足**（届时 `csx_status` / `csx_checkpoint` / `csx_recall` 三工具进表）。
**这是 K6 除了「治病」之外的第二个产出。** 在此之前，本项目的可见性依赖「有人主动查」。

---

## 五、回滚点与回滚步骤

### 回滚点（**已就位**，2026-10-10T04:41:55 建）

```
~/dsh-collab/guard/backups/k6-rollback-point-20261010-044155/
  package.json      4504 B   sha256[0:16]=dc65727d443a18bd   ← 与现 profile 一致（已比对）
  pnpm-lock.yaml  338354 B   sha256[0:16]=9492d745a944b152
  cordis.patch.yml  3628 B   sha256[0:16]=5df4683acdc1c86d
```

**挂载前请再比对一次**：`shasum -a 256 ~/.dsh/profiles/web/package.json | cut -c1-16` 应等于 `dc65727d443a18bd`。
不等 ⇒ **profile 已被别处改过**，回滚点需重建后再挂。

### 回滚步骤（三步，按序）

```bash
# ① 还原 profile（把两处新增删掉，或整文件还原）
cp ~/dsh-collab/guard/backups/k6-rollback-point-20261010-044155/package.json ~/.dsh/profiles/web/package.json

# ② 重装依赖（link: 形态变化后需重解析）
cd ~/.dsh/profiles/web && pnpm install

# ③ 重启 CLD（★ 由用户执行）
```

### ★ 回滚的**前提条件**（若挂载后 CLD 起不来）

`cordis.patch.yml` 里 `inject` 只有 `['tools']` —— **宿主平面真实存在的服务**。
本插件的 `tokenMeter` / `llm` 是**可选**依赖，一律运行期 `ctx.get()` 取，**不写进 inject**
（写进去 = 给自己加一条能绊倒整棵树的强依赖 —— 2026-10-09 excalidraw 事故正是此形态）。
⇒ 即便本插件自身有缺陷，**也不会因 inject 缺项导致整棵树加载失败**。
★ 但仍建议回滚步骤 ① 之前**先 `node cli.js --lean4-check`**（D 项即 inject 合规判据）。

---

## 六、挂载后要做的**第一件事**（负控 0）

**在开 `enableGuard` 之前**，先做**最小挂载冒烟**：

```bash
node cli.js --selfcheck --allow-apply     # 应 pass：name/inject/tools 三项到位
```

**pass 之后**才谈 `enableGuard`。**顺序不可颠倒** —— 理由：
`enableGuard: true` 才会注册 `agent/pre-step` 监听器；若插件本身挂不上却先开了守卫，
得到的是一个**看起来在工作、实际没注册**的静默失效（正是本项目要消灭的那种形态）。

### 开启守卫的**硬前提**（立项书 §4 纪律，逐条）

1. 负控 0 通过（上）
2. **`canShrink` 门已被证明** ⇒ ✅ **已由 `--calibration` 证明**（本核最差地板 2000 < 崩溃点 2466）
3. ★ **但 K3 的「真写入」尚未接线**（`session.append(..., {surfaceOp})`）——
   ⇒ **目前即便开 `enableGuard`，守卫也只会测量与记录，不会真的替换表面**（这是**刻意**的：未经验证的写入路径不接）。
   ⇒ 故 `enableGuard` 此刻开启**无风险但也无收益**；真正生效要等真写入接线（需 `apply()` 授权）。

---

## 七、已知风险（挂载前应知）

| # | 风险 | 缓解 |
|---|---|---|
| 1 | 与官方 `compaction-basic` 在**同一 `agent/pre-step` 事件**上叠加，可能双重压缩 | 并发护栏已接**真判据**（复刻官方 `assertNoActiveCompaction`）；守卫默认关，可随时退回 |
| 2 | 表面替换落在 step 边界，可能找不到合法切点 | `findBalancedWindow` 起止**只向内收**，收无可收即 `ok:false` 记 skipped，**绝不硬来** |
| 3 | `tokenMeter` 用 `CHARS_PER_TOKEN=4` 固定启发式 ⇒ 中文约 4× 低估 | 阈值用**同一 meter**（与官方同口径）；CJK 余量问题另案，不在本后端兜 |
| 4 | 交接块依赖 goal/todo 投影，某些会话无该投影 | 缺字段**如实留空并标注**，绝不编造 |
| 5 | 本守卫自身出错 | `ctx.effect` 注册 + `try/catch` 全包 + 观察器契约「**绝不抛出**」；`inject` 零可选依赖 |
| 6 | 落盘账本损坏 | **三态读**（ABSENT / OK / DEGRADED）—— 账本不可用时**绝不冒充**「未命中」；原子写防残缺 |

---

## 八、本文件**不做**什么（禁令逐条）

- ❌ **不挂载**（不可逆动作，由用户执行）
- ❌ **不改 profile**（本文件只读它；回滚点是复制，不是修改）
- ❌ 不重启 CLD · 不换载体 · 不复活首任 · 不删历史留痕 · 不用 `all=true` 广播 · 不为过门禁削字
- ❌ **不执行 `apply()`** —— `--selfcheck --allow-apply` 亦需**单独授权**（见 §三 第 10 项）

---

## 九、你只需要回答两件事

1. **Q-K6 挂载点**：(a) 搬到 `~/` ｜ **(b) 留 `devices/` 写绝对路径 link（推荐：零搬家 + 与 cldvoice 同形）** ｜ (c) MCP 形态（**不建议**，见 §一）
2. **是否授权**先跑 `--selfcheck --allow-apply`（负控 0）与后续的真写入接线

⇒ 其余**全部就绪**。
