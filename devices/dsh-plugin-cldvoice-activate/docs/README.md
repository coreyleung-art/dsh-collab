# cldvoice-activate · CLD-Voice 激活性重启（R006 十项达标）

> 星桥 · 2026-09-10 · v1.0.1 · R006 ②③④⑤⑥⑦⑧⑨⑩ 全达标 · 位置 `~/dsh-collab/devices/dsh-plugin-cldvoice-activate/`

## 为什么需要它（实证，不是推测）

`launchctl kickstart -k <label>` 与 KeepAlive 服务并存时会出现两类问题，且**都实际发生过**（2026-09-10）：

| 现象 | 实测证据 |
|---|---|
| 升级后服务起不来，必须人工再来一次 | `kickstart -k com.dsh.cld-voice` → `:8902/:8903` 未监听、launchd `last=1`、日志 `OSError: [Errno 48] Address already in use`；第二次才成功（PID 14671 → 36339） |
| 工具报"失败"但服务其实一直健康 | 初版工具要求"端口先释放"，而 `KeepAlive=true` 会让 launchd 立刻自动拉起 → 端口从未空过 → 对 `voice-service` 连续 3 次判失败**假失败**（服务当时健康） |

**两次都源于同一个错误心智模型**：把「端口释放」当成重启的前置条件。实际上在 KeepAlive 下它只是症状。

## 正确模型（本工具实现）

1. **热重启优先（R035）**：后端文件若早于进程启动时刻 → 运行中已是当前代码 → **不重启**，直接判"热生效"（前端 `client.js` 改动只需刷新页面）。
2. **原子重启**：`launchctl kickstart -k <label>`（停+起原子操作，与 KeepAlive 共存）；`-k` 不可用时回退 `kill SIGTERM` + `kickstart`。
3. **判据是"重启后就绪"**：端口在听 **且** 健康端点返回 ok（不是"端口是否空过"）。
4. **失败重试**：未就绪则记录诊断（端口状态/上次退出码/健康响应）后重试，默认 3 次。
5. **自愈复核**：放弃前再看一眼——KeepAlive 可能已自愈 → 判成功，**不报假失败**。

> 残留（已观测、已自动化、如实登记）：`cld-voice` 偶发第 1 次不就绪（`-k` 起新进程时旧 socket 尚未释放），**第 2 次 1 秒内成功**；该重试由工具自动完成，**不再需要人工兜第二次**。日志里 `attempt` 字段可查每次是否重试。

## 用法

```bash
node cli.js --status                 # 只读：launchd pid / 上次退出码 / 端口 / 健康
node cli.js --service cld-voice      # 激活（先判热重启，需要则重启）
node cli.js --all                    # 白名单全部
node cli.js --all --dry-run          # 只打印计划，零变更（lean4-check 会实测其零变更）
node cli.js --all --force            # 跳过热重启判定，强制重启
node cli.js --selfcheck              # R014 自查门 + 能力边界（TCC）
node cli.js --lean4-check            # 结构门自证（A–F 六项，见下）
node cli.js --tool-version
```

退出码：`0` 成功/门生效 · `1` 失败/门失效 · `2` 用法错误

## R006 十项达标矩阵

| # | R006 项 | 达标 | 实现 |
|---|---------|------|------|
| ① | dsh 插件形态 | ✅ | `package.json` + `cordis.patch.yml` + `lib/index.js`（`inject:['tools']`，注册 `cldvoice_activate` / `cldvoice_status`）|
| ② | TCC 检测 | ✅ | `--selfcheck`：输出能力边界（唯一的下杀调用是 `launchctl kill SIGTERM <白名单 label>`；无按 PID 杀；无宽杀）|
| ③ | CLD 自适应 | ✅ | 纯 `launchctl` + node 内置模块（`net`/`http`/`child_process`），不依赖 CLD 内部 API |
| ④ | dsh 版本自适应 | ✅ | 运行期零 dsh 私有 API；peer 仅 `cordis`/`dsh-tools`，经 profile `node_modules` 解析 |
| ⑤ | 文档化 | ✅ | 本文件 + `docs/R006-ten-items.md` + 源码 docstring（含错误模型复盘）|
| ⑥ | 版本管理 | ✅ | `--tool-version` v1.0.1；`package.json` version 同步 |
| ⑦ | 统一日志 | ✅ | `~/dsh-collab/logs/cldvoice-activate.log`（每次尝试/结果/诊断结构化留痕）|
| ⑧ | 自动落链 | ✅ | `RULES.md R035` 登记 + `data/registry/` 卡登记 + 本包 README |
| ⑨ | CLI 治理 | ✅ | 参数校验（未知旗标 exit 2）、`--dry-run` 零变更、退出码语义明确、`--json` |
| ⑩ | 约束前置·不可绕过 | ✅ | 见下节（结构门 + `--lean4-check` 六项自证）|

## ⑩ 结构门：为什么"不可绕过"不是靠纪律

本工具唯一的"不该发生路径"是：**为了重启语音后端而杀死整个框架进程**（CLD / Electron / dsh-runtime），或按 PID / 宽杀任意进程。

约束是**结构上不可表达**，而不是"检查后放行"：

1. **没有那个入口**：服务表 `ALLOWED` 是冻结常量，入参只能是其中的**键**（`cld-voice` / `voice-service`）。不存在 `--label <任意字符串>`、`--pid`、`-9` 之类的参数；工具 schema（`enum`）与 CLI 共用同一集合。
2. **没有那个能力**：实现里**不含**按 PID 杀进程、`killall`、`pkill`、`process.kill(-1)`；唯一的终止调用是 `launchctl kill SIGTERM <白名单 label>`，唯一的命令白名单是 `[launchctl, ps]`。
3. **有那个证明**：`--lean4-check` 运行六项自证，全绿才允许交付：

| 项 | 证明内容 | 方法 |
|---|---|---|
| A | 源码无宽杀调用 | 去注释/字符串/正则字面量后扫描（如实标注：**源码结构扫描，非完整 AST**——本包零外部依赖、宿主内无可用解析器）|
| B | 负例全部被拒 | 13 条恶意/越界输入（`CLD`/`electron`/`dsh-runtime`/`all`/`*`/`killall node`/`nginx`/`../cld-voice`/空值…）逐条实测必被 `GateError` |
| C | 白名单键可用 | 正例：两个键都能解析到对应 label（防"门太严把功能也拦了"——初版正是这样）|
| D | `--dry-run` 零变更 | 运行 dry-run 前后 PID 与端口**实测完全一致** |
| E | 白名单冻结 | `Object.isFrozen(ALLOWED) === true` |
| F | 外部命令白名单 | 枚举全部 exec/spawn 执行点，断言命令集 ⊆ `[launchctl, ps]` |

## 开发过程中被自己的检查抓到的三次错误（如实登记）

写这个工具的过程本身验证了今天反复出现的主题——**检查会撒谎**：

1. **门太宽**：框架禁用词 `cld` 命中了自己的合法键 `cld-voice` → 工具被自己的门拒绝、完全不可用。修法：**先精确白名单命中，再对非白名单输入做框架词判定**。
2. **扫描器把自己当靶子**：源码扫描把检测用的正则与帮助文本当成宽杀调用 → 假阳性。修法：先剥去注释/字符串/正则字面量。
3. **空洞通过**：剥字面量后，"第一个实参是不是字面量"无从判断 → 执行点枚举返回 0，"0 ⊆ 允许"**空集通过**。修法：用去字面量后的位置定位调用点，再回原文读实参。

> 结论：**假阳性会让人去修不存在的问题，空洞通过会让人误信不存在的能力**；两者都比"没检查"更危险。

## 与 R035 的关系

R035（2026-09-10 用户指示）：**能热重启的，就不要直接杀死整个框架。**
本工具是该原则的第一台机器化实现：① 它没有任何重启框架的能力；② 后端未变时它**主动选择不重启**（热生效）；③ 需要重启时也只重启白名单内的两个后端服务，不触框架。
