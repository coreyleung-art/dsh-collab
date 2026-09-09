# 部件卡 · dsh-storage-domain（领域 KV 存储 / workspace.json 幕后）

> 填卡：2026-09-04 · 依据：官方 subsystems/storage.md 全文 + workspace.json 实证
> 状态：learned（registry: storage-domain）

## 1. 一句话定位
持久化"一切非会话日志"的可选能力接缝：hub(`ctx.storage`, 只做中转无 IO) → Provider(json/sqlite backend 拥有介质) → Consumer(dsh-storage-domain `ctx.storageDomain`, 类型化 API, 产品包唯一接触层)。session 日志走 persistence.md 另一接缝。

## 2. 概念与定义
- **hub**：`backend` = name→backend 表（可并存多个 backend；consumer 配置路由，非 hub 全局选）；`form` 挂载 facility（form-not-mounted 直到 owning plugin 加载——assembly 靠顺序保证非静默推迟）。
- **Backend contract**：一个 backend 拥有一个介质 + 可选操作面（唯一 shipped = kv）；KvUnit{loadAll/putRecord/deleteRecord/setGlobal/close}。单次调用原子+落盘后 resolve；**不序列化并发写（顺序属 caller）**。
- **DomainSpec**：name(UNIT_NAME_RE)/version/layout(single|per-record)/compatibleVersions/global/tables。defineDomain 在模块加载期 fail-loud（名字非法/version 非负/global 接受 null 均 throw——null 是"never written"哨兵）。
- **读写语义（关键）**：读 = 同步权威**内存态**；写 put/delete/update/global.set **排队在 per-domain 链** → backend 落盘 → 改内存 → 发 domain/changed。backend 写拒 → 内存不动（读永不偏离介质）。update = 原子 RMW（链槽位）；delete 缺失 key resolve false 无写无事件。**返回的是存储对象本身非拷贝——用 put/update 改，勿原地 mutate**。
- **open 严格序**：already-open 拒 → 路由(backend-not-found) → kv facet(facet-unsupported) → 开 unit(version-mismatch/malformed-medium) → 校验记录/global 对 zod(invalid-record 带表与 key)。invalidRecords:'backup-and-skip' 允许派生数据损坏跳过。

## 3. 作用与生命周期
workspace 卡印证：workspace.json = single 布局 unit（global: initialized/workspaceIds/archivedSessionIds + tables.workspaces）。workspace init 时 open(workspaceDomainSpec) → recoverPendingMutation → replaceHeaderIndex 只改**内存** header 索引（不落盘 table）——解释"workspace.json 72 不随 boot 更新"（72 是上次持久化账，rebuild 是内存态）。创建/删除走 pending-mutation marker 两写防撕裂。

## 4. 约束（红线/不可违）
- 勿手工改 workspace.json 落盘文件（读是内存权威态；文件只是介质，改文件≠改运行时态，且可能 version-mismatch）。
- backend 写拒时内存不动——诊断"改了不生效"先看是否内存态被某路径覆盖。
- form-not-mounted = 依赖插件未加载（同 plugin-loader 卡 inject 语义）。
- 返回对象勿原地 mutate（要 put/update 替换）。

## 5. 依赖
- ctx.storage(hub) → 依赖 backend 注册(storageBackendServiceKey 防竞态)；ctx.storageDomain 依赖 form 挂载。被依赖：dsh-workspace（init open domain）。

## 6. 规范要点（标准）
- 查"配置/账目为什么不生效"：区分 介质文件(json) vs 内存权威态 vs domain/changed 事件链。
- workspace.json 的 bak 恢复 = 介质替换，需重启让 open 重读；改后 version 必须匹配。

## 7. 关联
- 官方文档：subsystems/storage.md · 工具箱：T1（workspace 内存态误导）· 路由：无直接 OP
- 代码：dsh-storage{,-json,-sqlite,-domain}/lib/ · 实证文件：~/.dsh/storages/workspace.json(+7 个 .bak)

## 8. 待补
- json vs sqlite backend 切换影响（性能/原子性）。
- domain/changed 事件消费方（哪些缓存监听）。

## 9. 学-建-用 沉淀
- 2026-09-04：卡毕业——解释了"workspace.json 72≠磁盘 191"与"内存态不落盘"两大实证谜团；支撑 T1 诊断(勿改文件)。
