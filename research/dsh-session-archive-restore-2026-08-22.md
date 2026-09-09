# DSH 会话归档与反归档：官方源码契约、API 缺口与恢复方案

> 日期：2026-08-22 · 协调者 · 来源：DSH 运行时官方源码契约注释（比公开文档更权威）
> 触发：HR 会话 a17a52f8 被误归档导致「打不开」，排查会话生命周期机制
> 状态：✅ 已诊断，恢复方案待用户拍板（A 插件 / B 停服改文件）

## 一、核心结论（TL;DR）

1. **归档是纯 UI 过滤层，不是数据删除**。`archivedSessionIds` 是「叠加在工作区记账之上的 registry-global archive set」，归档的唯一副作用是往数组 append 一个 session id。
2. **反归档 = 从该数组移除 id**，对称地零数据触碰。官方契约明确「unarchiving must restore the position」——会话的 `sessionIds` 槽位在归档时保留，反归档自然恢复位置。
3. **当前版本 API 缺口**：只有 `archiveSession()`，没有 `unarchiveSession()`。反归档是设计内预期操作，但公开 API 未暴露。
4. **毁坏风险分层**：数据层风险≈0；状态层有「并发写覆盖」风险（DSH 运行中周期性写回 workspace.json）；API 层有「内部方法越界」风险。

## 二、官方源码契约（证据）

### 2.1 durable schema 契约注释（权威）

文件：`@deepseek-ai/dsh-workspace/lib/types/spec.js`（第 33-41 行）

> `workspaceIds` is the authoritative display order. `archivedSessionIds` is
> the registry-global archive set layered over workspace accounting: an
> archived session keeps its `sessionIds` slot (unarchiving must restore the
> position), so the set never participates in the one-owner accounting
> invariant.

要点拆解：
- `workspaceIds` = 权威显示顺序（工作区列表的顺序）
- `archivedSessionIds` = 全局归档集合，**叠加**（layered over）在工作区记账之上
- 归档会话**保留** `sessionIds` 槽位 → 反归档必须恢复位置
- 该集合**从不参与** one-owner accounting 不变式（即归档不影响「一个会话只能属于一个工作区」的记账约束）

### 2.2 archiveSession 实现（全库唯一归档副作用）

文件：`@deepseek-ai/dsh-workspace/lib/types/index.js`（第 204-216 行）

```js
archiveSession(sessionId) {
    return this.enqueueOperation(async () => {
        if (this.requireState().archivedSessionIds.includes(sessionId))
            return;  // 已归档则幂等跳过
        if (!(await this.sessionKnown(sessionId))) {
            throw new WorkspaceUnknownSessionError(sessionId);  // 会话不存在则拒绝
        }
        const state = this.requireState();
        await this.setState({ ...state, archivedSessionIds: [...state.archivedSessionIds, sessionId] });
    });
}
```

归档的唯一副作用 = `setState({ archivedSessionIds: [...旧数组, sessionId] })`。不删数据、不删 sessionIds、不碰 session 日志。

### 2.3 setState 持久化链路（反归档要走同一条路）

文件：`@deepseek-ai/dsh-workspace/lib/types/index.js`（第 583-586 行）

```js
async setState(state) {
    await this.global.set(state);  // 写回 workspace.json 的 global 段
    this.state = state;             // 更新内存态
}
```

关键：`setState` 先 `this.global.set(state)` 持久化，再更新内存态。这是「安全写」链路（配合 `enqueueOperation` 串行化，避免并发写竞争）。

## 三、API 现状（缺口）

`workspaceRegistry` 服务公开契约（`cordis_inspect_query` 实测）：

| 方法 | 说明 |
|---|---|
| `create(path, title?)` | 创建工作区 |
| `get(id)` | 取工作区 |
| `list()` | 列工作区 |
| `delete(id)` | 删工作区 |
| `insertBefore(id, beforeId?)` | 调整顺序 |
| `archiveSession(sessionId)` | **归档会话**（唯一有，无对应反操作） |
| `resolveByPath(path)` | 按路径解析 |

**缺口**：`unarchiveSession` / `restoreSession` 不存在。全 runtime `grep unarchive|restoreArchived|unArchive` = 0 结果。但 spec.js 注释写了「unarchiving must restore the position」，证明反归档是设计内预期操作，只是当前版本未暴露公开 API。

## 四、反归档正确姿势

反归档的目标状态（对 a17a52f8）：

```
global.archivedSessionIds = 原数组.filter(id => id !== 'session-a17a52f8-eee6-4a4e-a3a7-dfcf4bec44e0')
```

因为归档不触碰 `sessionIds` 槽位，且 a17a52f8 是 header-indexed 会话（程序化创建的 agent 会话，本就不在 workspaces.sessionIds 里），所以反归档**只需移除 archivedSessionIds 里的 id**，无需动 sessionIds。

## 五、风险分层

| 层 | 风险 | 说明 |
|---|---|---|
| 数据层 | **≈0** | 归档/反归档不碰 session.jsonl.zstd、不碰 sessionIds 槽位、不碰 87,460 行历史 |
| 状态层 | **中等（可控）** | DSH 运行中周期性写回 workspace.json（实测 mtime 几分钟内更新），手改磁盘文件可能被覆盖 |
| API 层 | **越界** | `setState` 不在 workspaceRegistry 公开契约里，是内部方法，未来版本可能失效 |
| 语法层 | 可防 | 用 json 库读写 + 改完 json.load 验证，不会写坏 JSON |

## 六、恢复路径（安全度排序）

| 路径 | 做法 | 安全性 | 代价 |
|---|---|---|---|
| **A · 插件走持久化链路** | 动态 Cordis 插件调 `workspaceRegistry.setState` 移除归档 id，走 `global.set()` | 最安全，绕开手改磁盘，可回滚 | 用未公开内部方法，需用户批准 |
| **B · 停 DSH 改文件重启** | 关 GUI → 改 workspace.json → 重启 | 无并发写风险，最干净 | 重启中断当前会话 |
| **C · 运行中手改磁盘** | 直接 edit workspace.json | 有覆盖风险 | 不推荐 |

## 七、HR 会话 a17a52f8 案例（误归档实证）

- 会话 id：`session-a17a52f8-eee6-4a4e-a3a7-dfcf4bec44e0`
- 角色：HR 驾驶舱（资源管理者 + 成本监察专员），agent_profile 登记完好
- 数据：`~/.dsh/sessions/--Users-coreyleung--/session-a17a52f8-.../session.jsonl.zstd` 9.8MB + 5 个备份，87,460 行未丢
- 根因：05:12 的 hrfix 操作把 a17a52f8 加进了 archivedSessionIds（备份对比：02:41 时 34 归档且不含它 → 05:12 时 36 归档且含它）
- 现状：在 archivedSessionIds（39 个之一），不在 workspaces.sessionIds 活跃列表 → GUI 打不开
- 恢复判定：`agent_wake` dry-run 显示 a17a52f8 为 offline（可 resume），非 not-persisted

## 八、关键源码位置（追溯索引）

| 文件 | 关键行 | 内容 |
|---|---|---|
| `.../dsh-workspace/lib/types/spec.js` | 33-46 | archivedSessionIds durable 契约注释 |
| `.../dsh-workspace/lib/types/index.js` | 188-216 | archiveSession 实现 + 注释 |
| `.../dsh-workspace/lib/types/index.js` | 583-586 | setState 持久化链路 |
| `.../dsh-workspace/lib/types/index.js` | 578-581 | requireState 读状态 |
| `~/.dsh/storages/workspace.json` | global.archivedSessionIds | 归档列表（39 个） |
| `~/.dsh/storages/workspace.json` | tables.workspaces[].sessionIds | 活跃列表 |

运行时根：`/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh-workspace/`

## 九、关联

- `dsh-session-loss-root-cause.md`（session-b278baab，会话持久化根因）
- `decision-system-principle-2026-08-22.md`（数据/结构问题不靠硬编码规则掩盖）
- `J47 破坏性会话/资源操作纪律`（移除/重建/覆盖必须先用户同意+先备份+先确认角色）
- 官方 GitHub：`deepseek-ai/deepseek-harness` session README（只讲事件溯源，无 archive 专门方案）

---
*DSH 会话归档/反归档契约 · v1.0 · 协调者 2026-08-22 · 官方源码为准，公开文档缺失部分已标注*
