# bus-queue-triage · agent-bus 积压队列分诊清理工具

> 版本 1.0.0（版本单一来源：脚本内 `const VERSION`，--selfcheck 自动校验无第二处声明）
> 路径 `~/dsh-collab/scripts/bus-queue-triage.js` · 零依赖 Node CLI（node ≥ 18，仅内置模块）

## ① 为什么需要（事故/证据）

- **2026-10-03 i9 上线自带 2797 条 queued**：设备离线期间积压的跨会话消息，若启动时被插件 flushQueue 全量投递 = 注入风暴。
- **同日实测本机 581 条 queued 的成分**：383 条来自已退役星舵会话的 15min 定时泄漏 + 191 条 to 为空的跨设备「看黑板」指针 + 占位/歧义 id。
- 积压必须**分诊**而非一刀切：死形态（空 to/裸 UUID/纯角色标签/占位 id/短 id 歧义）永远投不出去，留着只会污染审计与统计；而在线目标的新鲜消息要保留给插件自然投递。一刀切全投=风暴，全删=丢消息。
- 前身：rust-tools `queue-drain`（2026-08-30，决策表之前）只做「抽走/归档」，无身份形态分类、无 DLQ 语义、无 R006 门。本工具是**决策表代**的系统性升级。

## ② 用法（含退出码）

```bash
node bus-queue-triage.js                  # = --scan：只读分诊报告（默认，零变更）
node bus-queue-triage.js --apply          # 把处置类置 expired（备份+原子写+回读+幂等）
node bus-queue-triage.js --apply --keep-days 3
node bus-queue-triage.js --json           # 机器可读输出（scan/apply）
node bus-queue-triage.js --selfcheck      # 能力边界/不该发生路径/依赖/等价断言
node bus-queue-triage.js --lean4-check    # 约束门 A–F 六项
node bus-queue-triage.js --tool-version
```

退出码：`0` 成功 · `1` 失败/门失效 · `2` 用法或 IO 错误。未知旗标 → 用法错误（exit 2）。

### 处置/保留类

| 类 | 含义 | 动作 |
|---|---|---|
| expired-age | 超龄（默认 >7 天，对齐插件 A2 TTL） | → expired |
| dead-empty | to 为空 | → expired |
| dead-placeholder | 占位/伪造 id（deadbeef、-0000-…） | → expired |
| dead-shortid-ambiguous | 短 id 在活性表 0 或 ≥2 命中（fail-closed） | → expired |
| dead-form | 纯角色标签（无 id 可抽） | → expired |
| live-target | 完整 id 在活性表 | 保留（插件自然投递） |
| keep-offline | 完整 id 不在活性表 | 保留（TTL 兜底） |
| keep-device-form | bus:* / 设备别名（跨设备合法寻址） | 保留 |
| keep-live-unknown | 活性表不可得时的短 id | 保留（保守） |

**结构约束**：本工具没有删除能力——唯一写动作是把 queued 置 `expired`（status/expiredAt/triage 三字段，DLQ 语义）。写目标=读入的文件本身：先备份 `*.triage-bak-<ts>` → 原子写（tmp+rename）→ 回读断言数量。

## ③ R006 达标矩阵

| 项 | 判定 | 说明 |
|---|---|---|
| ① dsh 插件形态 | ⚠️ 偏离（声明） | 目标设备（i9）不加载第三方插件，插件形态不可用；独立 CLI + 全套门。若需宿主内形态可后续包装 |
| ② TCC 检测 | ✓ | `--selfcheck` 三段：能力/不该发生路径/依赖 |
| ③ CLD 自适应 | ✓ | 零宿主依赖；活性表不可得时降级为保守保留 |
| ④ dsh 版本自适应 | ✓ | 零运行时依赖，不 import 宿主模块 |
| ⑤ 文档化 | ✓ | 本文件（事故/用法/矩阵/坑/复现） |
| ⑥ 版本管理 | ✓ | `VERSION` 单一来源 + 自检反查源码 |
| ⑦ 统一日志 | ✓ | `~/dsh-collab/logs/bus-queue-triage.log`（无则 `~/.dsh/`） |
| ⑧ 自动落链 | ✓ | 黑板 `data/registry/bus-queue-triage` 登记卡 |
| ⑨ CLI 治理 | ✓ | 严格旗标（未知→exit 2）/ 固定退出码 / 默认 dry-run / `--json` |
| ⑩ 约束前置 | ✓ | `--lean4-check` A–F 全绿（类型锁：无删除旗标可表达；入口门：--apply 唯一写入口） |

## ④ 坑（实测）

1. **本机 webServer 对 keep-alive 不闭合响应流**：Node `http.get` 的 `end` 永不触发 ⇒ promise 悬空 ⇒ 事件循环排空静默 exit 0（无输出、无报错、exit 0——最阴险形态）。修法：显式 `Connection: close` + 看门狗强制 settle。
2. **/agent-bus/api/state 响应 8.37MB**（全量快照而非纯 agents 列表）——活性查询上限放宽到 32MB；该端点体积本身是通讯面待优化项（见架构审计报告）。
3. **短 id 跨设备**：短 id 在本机活性表 0 命中（目标在对端机器）会被置 expired——跨设备消息本就该走 bus 别名/黑板通道，短 id 形态在本机 bus 上永远投不出去，expired（DLQ）如实留痕。
4. **幂等**：`--apply` 可安全重跑（第二轮变更 0、回读断言通过）；备份文件滚动累积需自行清理。

## ⑤ 复现命令

```bash
# 全门
node ~/dsh-collab/scripts/bus-queue-triage.js --selfcheck && \
node ~/dsh-collab/scripts/bus-queue-triage.js --lean4-check
# 安全演练（副本）
cp ~/.dsh/agent-bus.json /tmp/bus-test.json
node ~/dsh-collab/scripts/bus-queue-triage.js --scan --file /tmp/bus-test.json
node ~/dsh-collab/scripts/bus-queue-triage.js --apply --file /tmp/bus-test.json   # 两次：第二次应 0 变更
# 真跑（先停插件？不需要：插件防抖写盘会覆盖——务必在插件停止时执行 --apply，否则竞争）
```
> ⚠️ **真跑前置**：`--apply` 直接改 agent-bus.json，运行中的 agent-way 插件有 1.5s 防抖写盘，会把内存态覆盖回磁盘 ⇒ **在 CLD 停止期间执行 --apply**（或接受写入被覆盖、重跑一次）。
