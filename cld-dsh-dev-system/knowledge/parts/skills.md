# 部件卡 · dsh-skills（技能注册表）

> 填卡：2026-09-05 · 依据：官方 subsystems/skills.md
> 状态：learned（registry: skills）

## 1. 一句话定位
[ctx.skills] 技能提供者注册表：local/embedded/remote 等 provider 汇于 registry；**注册同步**，remote init/discovery 在 awaited list()。host+per-scope 分层(同 tools 注册表经 dsh-scope 的形态)。

## 2. 概念与定义
- **分层注册**：注册进 calling context scope 的层——host/repo 插件进 global；agent preset 挂的插件进 preset 层；provider name **per-layer 唯一**(非 process-wide)。读 = global + viewing scope chain 合并；nearest 层同名 outright 胜。
- **同一层内消解**：rank → provider order → local order；summaries 按名排序。
- **Provider 接口**：{name, list(options)}——list 返回 candidates 数组(完整发现简写)或 SkillProviderObservation{candidates, complete}(不权威但可直接 load)。rejected list 记日志并从不完整观察中省略；malformed 候选 fail-fast。
- **Discovery 缓存**：按 resolved scope chain 键——scope 重挂(recompose)对下次读可见，无需 registry mutation。
- **Control/signal**：provider factory 收 registration-scoped control；invalidate() 只在该注册存活时清 completed catalog；signal 在注册失败/disposal abort。in-flight discovery 在 provider generation 变时重试一次，再变返回 incomplete uncached。
- **skills/change 事件**：provider/runtime mutation 发 unfiltered 失效事件(无 diff)——consumers 以自己 lookup 重取 snapshot()。

## 3. 作用与生命周期
apply() 同步注册 provider → 读时(scope chain) list()/discovery → candidates → summary/lookup/config(候选、完整定义分离) → load。

## 4. 约束（红线/不可违）
- 语义字段校验；provider objects/options/candidates **borrowed readonly**。
- complete:false 观察不可缓存；same-layer duplicate 按 rank 消解。

## 5. 依赖
- 依赖 scope/tools 分层先例；被 skill loader/tool 消费。本环境 skill 目录(=技能清单 catalog)是界面实例。

## 6. 规范要点（标准）
- 加技能(如 lark/coze/wecom 系)= 提供者或 catalog 条目；分层决定可见性(global vs preset)。
- 诊断"技能看不到"：scope 层 + duplicate 消解 + discovery 缓存键。

## 7. 关联
- 官方：skills.md · 工具箱：— · 路由：—
- 代码：dsh-skill/skill-provider 系

## 8. 待补
- 完整技能定义(candidate→definition)的加载路径。

## 9. 学-建-用 沉淀
- 2026-09-05：卡毕业。
