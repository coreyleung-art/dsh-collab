# 安全审查过程 · Cordis 插件无崩溃风险审查（可复用 SOP + 工具化）

> 日期：2026-08-22 · 会话：协调者 session-fa1f9150 · 对象：dsh-plugin-hr client preset 门控改造
> 用途：以后任何 Cordis 插件改动的「无崩溃风险审查」照此流程，产出审查结论，省 token、防事故。

## 一、审查五步法（核心 SOP）

### 步骤 1：锁定「声明式 API 的调用时机」
- 检查 `slots.inject` / `slots.register` / `ctx.effect` / `ctx.on` 等声明式 API 是否**只在 apply 顶层同步调用**。
- **红线**：在 `subscribe` 回调 / 定时器 / 异步 then 里动态调用 slots.register——slots 层对同 id 重复 register 抛 `"already has an entry"`，会崩溃。
- 判定：grep `slots.inject` 出现次数，应仅 1 处（apply 顶层）。

### 步骤 2：检查「可撤销性」与副作用
- 每个 `ctx.effect(() => ...)` 是否返回 disposer（清理函数）？——停止/更新/卸载时能否完整移除副作用。
- DOM 注入（document.createElement + MutationObserver）是否返回 cleanup（disconnect + remove）？
- 订阅（subscribe）是否返回 unsubscribe 并接入 effect disposer？

### 步骤 3：检查「服务依赖」的可选性
- `inject: ['serviceName']` 声明的是**硬依赖**——服务缺失时插件会进入 waiting（不崩但永不 apply）。
- 可选服务应 `ctx.get('serviceName')`（返回 undefined 需兜底）而非直接 `ctx.serviceName`。
- 新增服务依赖（如 sessions）前，确认该服务在目标运行时**确实存在**（查同类插件 inject 先例）。

### 步骤 4：检查「数据字段」的防御性
- 读快照/对象字段用**可选链**（`snap?.byId?.[id]?.agentPreset`），缺字段不抛。
- 读外部数据用 try-catch 兜底，异常返回 undefined 而非上抛。

### 步骤 5：构建产物验证（grep 实证）
- 构建后 grep 产物，确认关键守卫逻辑在位：`slots.inject` 仅 1 处 / `return null` 存在 / `inject` 数组含新服务 / 无「订阅回调里 register」模式。

## 二、工具化（可复用审查脚本）

### 2.1 审查清单（审查者逐项打勾）

```text
[ ] 声明式 API 只在 apply 顶层？（grep slots.inject 次数 = 1）
[ ] 无 subscribe 回调里动态 register？
[ ] ctx.effect 都返回 disposer？
[ ] DOM 注入有 cleanup？
[ ] 订阅有 unsubscribe 且接入 effect？
[ ] 硬依赖服务在目标运行时存在？（查同类插件 inject 先例）
[ ] 可选服务用 ctx.get 兜底？
[ ] 数据字段可选链 + try-catch？
[ ] 构建产物 grep 验证守卫逻辑在位？
```

### 2.2 一键审查脚本（scripts/cordis-crash-audit.py 骨架）

```python
# 用法: python3 cordis-crash-audit.py <lib/client.js>
# 检查项: slots.inject 次数 / return null / inject 数组 / 订阅回调里 register 反模式
import re, sys
src = open(sys.argv[1], encoding='utf-8').read()
issues = []
n_inject = len(re.findall(r'\.slots\.inject\(', src))
if n_inject != 1:
    issues.append(f'slots.inject 出现 {n_inject} 次（应仅 1 次 apply 顶层）')
if not re.search(r'return null', src):
    issues.append('缺少门控 return null（非目标会话未渲染空）')
# 反模式：subscribe 回调内 register（启发式）
if re.search(r'subscribe\s*\([^)]*\).*register', src, re.S):
    issues.append('疑似 subscribe 回调内 register（崩溃风险）')
print('✅ 无崩溃风险' if not issues else '❌ 风险: ' + '; '.join(issues))
```

## 三、本次审查实录（可复用的「问题→修复」案例）

| 审查发现 | 风险等级 | 修复 |
|---|---|---|
| 初版在 sessions.list.subscribe 回调里动态 ctx.slots.inject | 🔴 崩溃（同 id 重复 register throw） | 改为 slot 一次性 inject + 组件内门控 |
| mountSidebar 无 cleanup | 🟡 副作用泄漏 | 返回 disconnect + remove + unsubscribe |
| 新增 sessions 硬依赖未确认存在 | 🟡 可能永不 apply | 查 task-board 先例确认 sessions 是标准服务 |
| 数据字段直接访问 | 🟡 缺字段抛错 | 可选链 + try-catch |

## 四、关联

- 模式专属工具复用模式（preset-scoped-tool-pattern.md）——配套文档
- dsh-client-ui-slots register 源码（同 id 重复抛 already has an entry）
- task-board 官方 inject 先例
- J37 插件安装验证纪律（构建→冒烟→验证链）

---
*安全审查 SOP v1.0 · 协调者 2026-08-22 · 可复用，做 Cordis 插件改动前必查*
