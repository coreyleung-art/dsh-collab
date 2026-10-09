## v1.0.2 · 2026-09-13（★ 真挂载冒烟抓到整包不可挂载）

**缺陷**：`makeOutput().schema.properties.diagnosis` 写成 `{ type: 'object' }`，**嵌套 object 未显式声明 `additionalProperties`** → `defineTool` 抛 `unsupported JSON schema: ... additionalProperties must be explicitly true or false` → **`apply()` 阶段即崩** → **插件在本宿主上根本无法挂载**。

**为什么此前没被发现**：其它九项全绿（①形态 ②TCC ③CLD 自适应 ④dsh 版本 ⑤文档 ⑥版本 ⑦日志 ⑧落链 ⑨CLI ⑩约束门），而**没有任何一项会真正调用 `apply()`** —— 交付物"看起来完整"，在运行时却不存在。这正是 R006 v3.1.0 把「真挂载冒烟」列为 ① 硬项的直接动因（dispatch/collect 属主各在自身插件命中同型缺陷）。

**修复**：`diagnosis: { type: 'object', additionalProperties: true }`（见 `lib/index.js` 注释留因）。

**验证（三态，2026-09-13 实测）**：
- ✅ pass：`tools=[cldvoice_activate, cldvoice_status]`，自查总判通过、exit 0
- ❌ fail：注入 `throw` 后 → `fail — SMOKE-NEGATIVE-TEST`，exit 1（正控）
- ⊘ skipped：两级候选目录均不含依赖时 → 如实标 skipped + 明确"不得据此声称 ① 达标"，exit 1

**新增自检段**：`--selfcheck` ⑤ 插件挂载冒烟（两级解析：本目录 → profile/CLD 运行时 `node_modules`，临时软链、用完即删）。总判改为**只有 pass 算通过**（skipped ＝ 门未生效，同样判未通过）。
# CHANGELOG · dsh-plugin-cldvoice-activate

## v1.0.1 · 2026-09-10（模型修正：KeepAlive 下"端口释放"不是前置条件）

**性质**：修正一个**错误的心智模型**（v1.0.0 的端口前置判断不成立）。由本工具自己的统一日志证明。

### 证据（`~/dsh-collab/logs/cldvoice-activate.log`）
- v1.0.0 对 `voice-service` 连续 3 次判「端口未在 20s 内释放」→ 报**失败**；
  但该服务当时**一直健康**（`KeepAlive=true` 使 launchd 在 SIGTERM 后立刻自动拉起，端口从未空过）。
- v1.0.0 对 `cld-voice` 第 1 次真失败（`lastExit=1`、`ECONNREFUSED`），第 2 次才成功。

### 修正
1. **不再等待"端口释放"**（它在 KeepAlive 下是不可达状态，且只是症状而非条件），改为：
   `launchctl kickstart -k <label>`（原子重启，与 KeepAlive 共存）→ **验证重启后就绪**（端口在听 + 健康端点 ok）。
2. **失败重试**保留（默认 3 次），端口/上次退出码/健康响应降级为**诊断信息**。
3. 新增**自愈复核**：放弃前再查一次，若服务已由 KeepAlive 自愈 → 判成功，**不报假失败**。
4. 新增**热重启优先**：后端文件早于进程启动时刻 → 判"热生效"、**不重启**（R035）。
5. 端口占用**不再触发 PID 强杀**（v1 的 bash 版本会强杀占用进程）——杜绝"按 PID 杀进程"的能力。

### 实测（修正后）
- `--all --force`：两服务均成功；`voice-service` 第 1 次即就绪（1s）；`cld-voice` 第 2 次就绪（1s，重试由工具自动完成，无需人工兜第二次）。
- `--all`（非强制）：两服务均判"无需重启（热生效）"，PID 未变 —— 符合 R035。
- `--lean4-check`：A–F 六项全绿。

## v1.0.0 · 2026-09-10（首版）
- 起因：`launchctl kickstart -k` 端口竞态导致升级后服务起不来、需人工兜第二次（实测 PID 14671 → 36339 的第二次重启）。
- 首版实现：SIGTERM → 等端口释放 → kickstart → 验证 → 重试（**该模型后被证伪，见 v1.0.1**）。
- 同版确立结构门：冻结白名单 + 框架词拒绝 + 无 PID/宽杀能力 + `--lean4-check` 六项自证。
