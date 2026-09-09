# 模式专属工具复用模式 · preset 门控 client 插件（可复用经验）

> 日期：2026-08-22 · 会话：协调者 session-fa1f9150 · 场景：dsh-plugin-hr 看板「全局挂载」→「仅 HR 驾驶舱模式显示」
> 用途：以后做「某个工具/UI 只在特定 preset（模式）会话出现」时，直接复用本模式，省 token。

## 一、问题

dsh-plugin-hr 的 client 前端（dock 面板 + 侧边栏看板）通过 profile 级 `cordis.patch.yml` + profile `bundles` 全局挂载，导致**所有 preset 会话**（梁神模式/普通模式/协调者会话等）右下角都出现「HR 资源看板」，且因 host 端 `/hr/api/*` 路由未注册而显示红色「HR 看板加载失败」。

## 二、根因链（三层）

1. **client 端全局挂载**：dsh-plugin-hr 在 profile 的 `dsh.profile.bundles` 列表中（package.json），是 profile 级 bundle，所有会话加载。
2. **无 preset 门控**：client.js 的 `apply` 直接 `ctx.slots.inject('conversation.input.dock', ...)`，不判断当前会话 preset。
3. **host 路由未注册**：host 端 `index.js` 依赖 webServer 服务晚到重试，但 `/hr/api/*` 实测 502（路由未成功注册，与 flower-cockpit 导出问题同源的「待重启生效」状态）。

## 三、关键机制（官方通道，已源码实证）

### 3.1 会话 preset 从 host 传到 client 的途径

- **会话摘要字段**：`sessionSummarySchema.agentPreset`（`dsh-client-connection/lib/client.js`）——`sessions.list` 快照里每个 session 带 `agentPreset: string().optional()`。
- **client 服务注入**：`inject: ['sessions']` → `ctx.sessions.list.getSnapshot()` → `{ current: 当前会话id, byId: { [id]: { agentPreset, ... } } }`。
- **读当前会话 preset**：`snap.current` + `snap.byId[snap.current].agentPreset`。
- **另有官方 RPC**：`agentPreset.read`（PRIVILEGED_METHODS，仅 loopback 授权），返回 `{ agentPreset, trust, content }`——但组件场景用 sessions.list 快照更轻量。

### 3.2 preset 注册名对照

- 「HR 驾驶舱模式」preset 的注册 id = `resource-manager`（`~/.dsh/.agent-presets/resource-manager/preset.yml`，order=6）。
- 会话头 `session.jsonl.zstd` 首行 `{"type":"session", "agentPreset": "..."}` 记录会话启动时的 preset id。
- **教训**：用错 preset 开会话（如 HR 用了 liangshen 开），`agentPreset` 字段会写死为 liangshen，且「有产出历史的会话不可 runtime 重链接 preset」（源码 lib/index.js:1104）——必须重开会话。

## 四、安全实现（方案 B：slot 一次性 inject + 组件内门控）

### 4.1 错误做法（有崩溃风险，已规避）

在 `sessions.list.subscribe` 回调里动态调用 `ctx.slots.inject` / `slots.register`——slots 层对同 id 重复 register 抛 `"already has an entry"`，会话来回切换会触发崩溃。

### 4.2 正确做法（本模式核心）

```tsx
const HR_PRESET_IDS = new Set(['resource-manager', 'hr-cockpit']);

function currentPresetOf(sessions) {
  const snap = sessions?.list?.getSnapshot?.();
  const currentId = snap?.current;
  if (!currentId) return undefined;
  return snap?.byId?.[currentId]?.agentPreset;  // 会话摘要 agentPreset 字段
}

// React hook：订阅 sessions.list，随会话切换更新当前 preset
function useCurrentPreset(sessions) {
  const [preset, setPreset] = useState(() => currentPresetOf(sessions));
  useEffect(() => {
    const update = () => setPreset(currentPresetOf(sessions));
    update();
    if (sessions?.list?.subscribe) return sessions.list.subscribe(update);
  }, [sessions]);
  return preset;
}

// 门控壳：非目标 preset 渲染 null（slot 已注册，仅控制内容显隐）
function GatedDock(props) {
  const preset = useCurrentPreset(props.sessions);
  if (preset === undefined || !HR_PRESET_IDS.has(preset)) return null;
  return React.createElement(HrDock, props);
}

function apply(ctx) {
  const sessions = ctx.sessions ?? ctx.get?.('sessions');
  // slot 只 inject 一次（绝不动态卸载），门控下沉到组件
  ctx.slots.inject('conversation.input.dock', () =>
    ctx.slots.register(
      { name: 'conversation.input.dock', id: 'hr-panel', order: 40 },
      (props) => React.createElement(GatedDock, { ...props, sessions })
    )
  );
  ctx.effect(() => mountSidebar(sessions));  // sidebar 同样内部门控
}
export const inject = ['slots', 'effect', 'sessions'];
```

### 4.3 三条安全铁律

1. **slot 只在 apply 顶层 inject 一次**，绝不放进 subscribe 回调（防重复 register 崩溃）。
2. **preset 判断下沉到 React 组件**（return null），纯渲染逻辑、可随会话切换响应式显隐。
3. **sessions 用可选链兜底**（`ctx.sessions ?? ctx.get('sessions')`），无 sessions 服务时退化为不挂载，不崩。

## 五、参考先例（client 插件注入会话服务的官方模式）

- `dsh-plugin-dock-cards` / `dsh-client-ui-task-board`：`inject: ['slots','sessions','workspaces',...]` + `ctx.sessions.list` / `sessions.binding(id)` 访问会话。
- task-board 的 `currentOf(sessions)` = `sessions.list.getSnapshot().current`（读当前选中会话）。

## 六、可复用检查清单（以后做「模式专属工具」照抄）

- [ ] 目标 preset 注册名是什么？（`~/.dsh/.agent-presets/<preset>/preset.yml` 的 order/name）
- [ ] 会话头 agentPreset 字段确认？（`zstd -dc <session.jsonl.zstd> | head -1` 看 `agentPreset`）
- [ ] client inject 声明加 `sessions`？
- [ ] slot 是否只在 apply 顶层 inject 一次？
- [ ] 门控是否下沉到组件 return null（而非动态 inject/uninject）？
- [ ] 非目标会话是否零副作用（不 fetch、不注入 DOM、无红字）？
- [ ] 构建后 grep 验证：`slots.inject` 仅 1 处、`return null` 存在、`inject` 数组含 sessions？

## 七、止血/回滚

- 临时止血：从 profile `package.json` 的 `dsh.profile.bundles` 移除该插件（备份 package.json 后改，改完需宿主重载）。
- 完整方案：改 src 源文件 → `node scripts/build.mjs` 重建 lib → 验证产物 → 宿主重载。
- 备份清单：src/client/index.tsx.bak-preset-gate-* · lib/client.js.bak-preset-gate-* · package.json.bak-hr-removal-*。

## 八、关联

- flower-cockpit 导出修复（同源「待重启生效」教训，J37 实证）
- hr-preset-tuning-prompt.md（HR preset 微调规范）
- resource-manager preset（agent.cordis.yml + preset.yml + mjs）
- J44 资源复用 / J46 官方文档沉淀（本模式即复用官方 sessionSummarySchema）

---
*模式专属工具复用模式 v1.0 · 协调者 2026-08-22 · 可被 knowledge_search 命中复用*
