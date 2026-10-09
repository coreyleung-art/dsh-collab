# CHANGELOG

## 0.2.0 — 2026-10-10 · K2 只测量

- **守卫实现，但只测量**：`agent/pre-step` 监听器现在会读压力、算阈值、判是否该压，**然后原样放行**。
  默认仍 `enableGuard: false`，且**未挂载**；检查点产出与表面替换在 K3。
- 新增 `lib/budget.js` — **纯决策核**（零 import / 零 I/O / 逐位确定）：预算公式、目标解析、
  阈值判定、（P26 机制二的）下界判定 `canShrink`。
- 新增 `lib/guard.js` — 观察器：把宿主对象读成一条读数；**任何一步读不到都如实报原因码**，
  绝不抛出到调用方。服务用 `ctx.get()` 取（**不写进 `inject`**，见 README 坑 6）。
- 新增 `lib/k2-selftest.js`（唯一用例来源，被 CLI 与 node:test 共用）+ `lib/budget.test.js` /
  `lib/guard.test.js`（node:test 驱动）。
- 新增 CLI `--budget-check`：**进程内**跑 125 条断言（预算 84 + 守卫 41），末尾打印逐位确定摘要
  `sha256=700c199a…`（本机 3 次独立进程运行相同）。`npm test` 走 node:test 同一条用例。
- **修正 K1 的一处猜测**：`agent/pre-step` 处理函数签名从 `(_payload, next)` 改为官方真实形状
  `({ agent, signal }, next)`（`dsh-compaction-basic/lib/index.js:780`）。
- **`--lean4-check` F 项的实测面扩大**：纳入新增 4 个源文件后仍是 15 个文件零变更（A 项零执行点保持）。
- `--status` / `csx_status` 阶段串改为 `K2-measure-only`；`csx_status` 新增 `guard` 读数块。
- **本轮测试抓出一条真缺陷**：`session.requestHeader()` 原先在 guard.js 的 try/catch 之外调用，
  会话销毁时会把异常抛给调用方（违反"观察器绝不抛出"的契约）；已包住并回退 `agent.options`。

## 0.1.0 — 2026-10-10 · K1 骨架

- 立项：Q-K 自研 no-summary 压缩后端（用户 2026-10-09 回复「2. 立项」批准）。
  立项书：`~/dsh-collab/docs/project-init-context-survival-backend-20261010.md`。
- 交付骨架（**只建目录，不挂载、不重启**）：
  - `package.json` / `cordis.patch.yml`（宿主平面插件行，`enableGuard: false`）
  - `lib/index.js` — 空守卫（`inject = ['tools']`，宿主端零客户端服务）
  - `lib/gate.js` — R006#10 结构门（零外部命令 + 召回目标枚举化 + inject 白名单）
  - `lib/meta.js` — 标识/版本/日志（版本单一来源 = package.json）
  - `lib/selfcheck.js` — R014 自查门
  - `cli.js` — `--status / --dry-run / --selfcheck / --lean4-check / --tool-version`
  - `docs/README.md`
- 命名门：slug `context-survival`、工具 `csx_status`/`csx_checkpoint`/`csx_recall`
  经本地 N1–N8 判据（`rules-registry/naming-standard-N1-N8-v1.md` §6 机器可读块）复核为合规。
- **未做**：守卫逻辑（K2 起）、真挂载冒烟（需授权）、挂载（K6，不可逆，由用户执行）。
