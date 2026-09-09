# 部件卡 · dsh-shell（Bash 执行器）

> 填卡：2026-09-05 · 依据：官方 subsystems/shell.md
> 状态：learned（registry: shell）

## 1. 一句话定位
[ShellExecutor seam `ctx.shell`]：受管 shell 环境命名空间；把 **request(可选字段)** resolve 成 **spec(必填)** 再执行——"explicit > implicit at package boundaries"；前台/后台进程 + 文件沙箱信息。

## 2. 概念与定义
- **resolve() 分裂**：ShellExecRequest{command, workdir?, timeoutMs?(实现 capped), stdoutMaxBytes?, signal?, stdin?(bytes 后关)} → ShellExecSpec(全解析必填)。tool 层显式调 resolve——request 面与 spec 面分离。
- **stdoutMaxBytes**：前台 stdout 捕获预算；模型面 bash tool **不暴露**此参数(需要 stdin/完整 stdout 用 heredoc/pipe 或 in-process 消费)。
- **ShellRunResult**(前台)：返回码+输出。**ShellSandboxInfo**：该次 shell 生效的文件沙箱(sandbox 卡 3 态)。**ShellProcess**(后台)：ShellProcess 句柄——jobs 卡协同(可 kill/await)。
- **ctx.shellEnv ShellEnvRegistry**：shell 环境命名空间(env 注册/继承)。

## 3. 作用与生命周期
tool call → resolve(request→spec) → 沙箱内 spawn → 前台 await 结果 / 后台得句柄。signal abort → kill 命令。

## 4. 约束（红线/不可违）
- workdir/timeout 在 tool 层可选、spec 层必填——实现可 cap timeout。
- 模型 tool 不暴露 stdoutMaxBytes(防无限捕获)；in-process 可信消费者自限预算。
- 后台进程是资源：必须可 kill/await(防泄漏)。
- 本环境实证：bash 工具超时/输出截断/后台 job 管理 = 本 seam 界面化。

## 5. 依赖
- 依赖 sandbox(文件效应)/shellEnv；被 model tool-bash 与 hooks 桥(写 JSON 到 stdin) 消费。

## 6. 规范要点（标准）
- 长命令/交互：后台 + 句柄管理；大输出：限预算或文件落地。
- 与 guard 关系：shell 内改 CLD 底层文件仍须过 guard-gate(文件策略层)——shell 沙箱≠治理门锁。

## 7. 关联
- 官方：shell.md、subprocess.md、terminal.md · 工具箱：T2(崩溃排查 ps/lsof) · 路由：—
- 代码：dsh-shell/dsh-bash-sandbox/dsh-tool-bash

## 8. 待补
- ShellProcess 句柄的完整生命周期与 jobs 协同。

## 9. 学-建-用 沉淀
- 2026-09-05：卡毕业。
