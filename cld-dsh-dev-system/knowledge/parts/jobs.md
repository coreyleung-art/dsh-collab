# 部件卡 · dsh-jobs（后台任务运行时）

> 填卡：2026-09-05 · 依据：官方 subsystems/jobs.md
> 状态：learned（registry: jobs）

## 1. 一句话定位
长跑任务(producer)与 `ctx.jobs`/job controls 共享的类型与运行时：**producer 拥有执行资源，runtime 拥有 identity/access/lifecycle state**。JobKind 从 merge-extensible map 派生(bash/subagent…)，registry 把 kind 当不透明 id 命名空间。

## 2. 概念与定义
- **JobId** = Branded `<kind>-N`。**访问控制靠 owner 授权，非 id 保密**。
- **JobStatus**：'running'|'stopping'|'completed'|'killed'|'failed'；producer 专属事实放 JobSnapshot.detail。
- **JobStart**：{kind(=id 前缀), label(单行 model 面标签), starter}。runtime 先 preflight(access+cleanup) 再调 run()，commit 无后续可 fail 步。
- **Producer contract**：producer 管执行资源(进程/子 agent)；runtime 管身份/访问/生命周期。Consumer views：控制(job controls)从 registry 查询/操作。

## 3. 作用与生命周期
start(kind,label,starter) → runtime preflight → run(执行) → 状态机 running→(completed|killed|failed|stopping)。job controls(UI/工具) 按 owner 授权操作。

## 4. 约束（红线/不可违）
- producer 不得依赖 runtime 做资源清理之外的事；runtime 不碰 producer 资源。
- status 由 runtime 管；detail 才放 producer 事实。
- owner 授权模型：非 owner 操作由 access 层拒。

## 5. 依赖
- 被依赖：tool-bash/subagent(producer)；job controls(consumer)。对应本环境 job_* 工具(bash 后台 job = bash kind)。

## 6. 规范要点（标准）
- 长命令用 job(可 kill/collect)而非前台吞死——ShellProcess 后台句柄与 jobs 协同。
- 诊断"卡住的后台任务"：status 是 killed/failed/stopping？detail 里 producer 事实。

## 7. 关联
- 官方：jobs.md、schedule.md · 工具箱：— · 路由：—
- 代码：dsh-jobs/dsh-tool-*；本环境 job_list/job_output/job_kill = 界面实例。

## 8. 待补
- schedule(定时)与 jobs 的关系。

## 9. 学-建-用 沉淀
- 2026-09-05：卡毕业。
