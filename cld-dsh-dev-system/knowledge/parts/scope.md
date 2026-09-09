# 部件卡 · dsh-scope（作用域注册 / per-agent 路由）

> 填卡：2026-09-04 · 依据：官方 subsystems/scope.md + runtime 源码
> 状态：learned（registry: scope）

## 1. 一句话定位
库级原语（非 Cordis 服务）：提供身份(key)、路由载体(Scoped)、注册上下文(Scope)、分层注册表(ScopedLayers)——让"一个注册上下文"同时表达 per-agent 可见性与共享生命周期所有权。

## 2. 概念与定义
- **ScopeKey**：不透明对象身份，恒等比较（shipped loop 用 live Agent 对象当 key，原语不检查对象）。
- **Scoped\<T\>**：`scopeTarget(base, key)` 返回的路由载体（编译期 brand）；scope 过滤的事件声明以它作 this 类型，真实事件主体是显式参数。
- **Scope**：`{ctx, rawDispose(精确 disposer, 用于有序复合 effect), dispose(公共静默边界, 竞态调用等同一完成)}`。
- **ScopeLayer**：某 registry 在全局或精确 scope 层的完整贡献；isEmpty() 全空 → ScopedLayers 回收 scoped 态。
- **ScopedLayers\<L\>**：急切的全局层 + 惰性精确层；读不建层(peek undefined=无覆盖)；merge 物化插入序全局命名项 + scoped shadows。
- **NamedEntries**：插入序查找+live 迭代+调用方重复错误；**AnonymousEntries**：每次 append 唯一身份（等值也独立）。

## 3. 作用与生命周期
注册用**同一 ctx** 同时管可见性和 Cordis effect 所有权；收集一个同步 undo → 可选通知 → 返回 Cordis 精确 disposer；scope 层仅当其完整 ScopeLayer 空时回收。

## 4. 约束（红线/不可违）
- key 恒等比较——勿用值相等语义的 key。
- 事件上溯不下传（ancestor 监听者收 descendant 事件；descendant 不收 ancestor）——会话/agent 事件路由依赖此。
- 迭代在单代非空表内 live；drain 表使既有迭代器脱离后续插入。

## 5. 依赖
- 库原语，被 dsh-session/workspace/agent 等引用（scopeTarget/scopeOf）。无自身服务依赖。

## 6. 规范要点（标准）
- 诊断"会话/事件路由错乱"先查 scope key 归属（per-agent 用 Agent 对象当 key）。
- scopeOf(ctx) 得当前 scope；scopeTarget 造路由载体。

## 7. 关联
- 官方文档：subsystems/scope.md；架构 agent-scope Agent Note
- 工具箱：T1（会话归属）· 代码：`dsh-runtime/.../dsh-scope/lib/`
- 知识：workspace 卡（scope 决定会话挂哪个 workspace 目录——projectKey(cwd)）

## 8. 待补
- 事件上溯链与 scoped-dispatch invariant 的边界实测（agent 嵌套场景）。

## 9. 学-建-用 沉淀
- 2026-09-04：卡毕业；为 workspace/会话归属诊断提供原语理解。
