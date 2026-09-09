# FlowerNet 主蓝图 v4.0 · 完整细化 + 可靠性审计全映射

> 作者：mac-mini 中枢 ｜ 2026-08-27
> 版本历程：v2.0（项目体系）→ v3.0（可靠性审计细化）→ v3.1（再审查补 5 缺口）→ **v4.0（全 15 缺口映射 + 正式版）**
> 依据：依赖可靠性审计（15 缺口）
> 定位：企业级（复用到所有门店 + 付费订阅花店商家）——完整、稳定、可靠。

---

## 〇、总览

```
FlowerNet 主蓝图 v4.0
├── P0 协议层 · FlowerNet FNP ★
├── P1 基础设施 · HubBridge Server（+身份/计量/HA/audit/token认证/genebank）
├── P2 插件层 · dsh 插件家族（+peerDeps 11/npm/门店插件/清理）
├── P3 桥接层 · node-bridge + dsh-tools（+看门狗/版本统一）
├── P4 治理层 · deploy-check/自适应/台账（+自动化）
└── P5 应用层 · 花店蓝图 + 订阅平台（+ERP HA）
```

**15 项可靠性缺口全部落入任务 + 里程碑**（见 §四）。

---

## P0 · 协议层（FlowerNet FNP ★）

### 依赖清单
| 依赖 | 用途 | 状态 |
|------|------|------|
| rust-blackboard（传输实现）| KV+SSE 协议宿体 | ✅ |
| FNP v1.0 规范 | 语义定义 | ✅ |
| v0.7 per-namespace 授权 | 门店数据隔离 | ❌ |
| v1.1 能力发现 | 门店 capabilities | ❌ |

### 任务分解
- [ ] **P0-1**: v0.7 per-namespace 授权（store-01 只能写 data/store-01/*，X-Writer 校验）→ 缺口 #8
- [ ] **P0-2**: v1.1 能力发现（门店注册上报 capabilities，/capabilities 查询）→ 缺口 #8
- [ ] **P0-3**: 协议版本协商（fnp/1.0 头部，旧版兼容）

### 验收
- 门店 A 无法写门店 B 命名空间（隔离）
- 门店注册后可被 /capabilities 发现

---

## P1 · 基础设施层（HubBridge Server）

### 依赖清单
| 子项 | 依赖 | 状态 |
|------|------|------|
| 1.1 传输 | rust-blackboard（8792+8803）| ✅ 持久化确认 |
| 1.1b 安全 | BLACKBOARD_TOKEN 认证 | ⚠️ 源码支持未启用 |
| 1.2 资产 | rust-genebank（/api/v1/genes）| ⚠️ 未启用 |
| 1.3 身份 | device-id + Ed25519 + token | ❌ |
| 1.4 路由 | 黑板 KV + SSE | ✅ |
| 1.5 设备 | 心跳 + verify-watch | ✅ |
| 1.6 计量 | token 计量（SQLite）+ 订阅 | ❌ |
| 1.7 HA | 独立部署 + 副本 | ❌ |
| 1.8 运维 | audit 轮转 + 清理 | ❌ |

### 任务分解
**1.1b 安全认证（缺口 #11）**
- [ ] **P1-1b**: 黑板启用 BLACKBOARD_TOKEN（启动设 token）→ #11
- [ ] **P1-1c**: 客户端适配（node-bridge/dsh-tools/central-inbox 全带 token）→ #11

**1.2 genebank 恢复启用（缺口 #9）**
- [ ] **P1-2a**: 启动 rust-genebank → 验证 /api/v1/genes → #9
- [ ] **P1-2b**: 与黑板集成（资产注册 → data/genebank/* 同步）→ #9
- [ ] **P1-2c**: 内容寻址去重验证（同内容同 gene_id）→ #9

**1.3 身份层（缺口 #2）**
- [ ] **P1-3a**: 设备注册 API（POST /register → device-id + token）→ #2
- [ ] **P1-3b**: 设备端 identity.json（UUID + Ed25519 私钥）→ #2
- [ ] **P1-3c**: 认证中间件（Bearer token + 白名单）→ #2
- [x] **P1-3d**: 消息签名（Ed25519 防伪造）✅ v1.4.1（node-bridge outbox 签名 + dsh-tools sign CLI，openssl3 零依赖，实测正/负例通过）→ #2

**1.6 计量层（缺口 #3）**
- [ ] **P1-6a**: token 计量器（SQLite：消息/字节/LLM）→ #3
- [ ] **P1-6b**: 订阅层级（free/pro 配额）→ #3
- [ ] **P1-6c**: 计量 API（租户查询）→ #3

**1.7 HA（缺口 #4）**
- [ ] **P1-7a**: 部署腾讯云轻量（docker：黑板+genebank+身份+计量）→ #4
- [ ] **P1-7b**: 数据副本/备份（snapshot 定时备份）→ #4
- [ ] **P1-7c**: 故障恢复演练（mac 挂 → 云接管）→ #4

**1.8 运维（缺口 #5）**
- [ ] **P1-8a**: audit 轮转（按大小/日期分文件）→ #5
- [ ] **P1-8b**: 保留策略（N 天，超期压缩归档）→ #5
- [ ] **P1-8c**: 磁盘监控告警 → #5

### 验收
- 独立部署后 mac 关机云实例继续服务（HA）
- 新设备注册 → 白名单 → 未注册 401
- 黑板带 token（无 token 拒绝写）
- audit 磁盘增长可控（<100MB/天）
- genebank /api/v1/genes 可用

---

## P2 · 插件层（dsh 插件家族）

### 依赖清单（peerDeps 11，缺口 #1）
| 插件 | 完整 peerDeps |
|------|--------------|
| dsh-plugin-agent-way | cordis / dsh-tools / dsh-client-runtime / dsh-agent / dsh-session-persistence / dsh-settings / dsh-system-prompt / dsh-host-webserver / dsh-agent-default-model / dsh-agent-presets / dsh-client-locale |
| dsh-plugin-central-inbox | 依赖 agentBus 服务（agent-way 先装）|

### 任务分解
- [x] **P2-1**: 补全 peerDeps 11 个（语义化 ^0.1.0-rc.6）→ #1 ✅（v1.3.0，2026-08-27）
- [x] **P2-2**: 干净环境验证 dsh plugin add（pnpm 解析）→ #1 ✅（git URL + 锁 ref 实测 + dump-config 加载）
- [~] **P2-3**: 插件分发 → #1 ⏸ npm 官方发布阻塞（"Public registration is not allowed"）；**已用 git URL 锁 ref 替代**（`git+https://github.com/coreyleung-art/dsh-plugin-agent-way.git#v1.3.0`，tag v1.0.0~v1.3.0 已全部推 GitHub）；npm 认证解决后切换
- [ ] **P2-4**: 三端官方安装验证 → #1（MBP/i9 已收 git URL 指令待回报）
- [ ] **P2-5**: 门店插件（FlowerNet 接入）→ #8
- [x] **P2-6**: genebank tar.gz 归档 → #14 ✅（archive/2026-08-27/，/shared/ 仅保留当前推荐）

### 验收
- MBP/i9 `dsh plugin add` 安装成功（修复 #1）
- 三端 [agent-bus] 加载 + 双向注入
- genebank 无 tar.gz 分发（npm 统一）

---

## P3 · 桥接层

### 任务分解
- [ ] **P3-1**: node-bridge 内置 supervisor（崩溃自启，跨平台）→ #6
- [ ] **P3-2**: Windows 服务注册（i9）→ #6
- [ ] **P3-3**: 看门狗健康检查（心跳丢失→拉起）→ #6
- [ ] **P3-4**: 三端 node-bridge 统一 v1.2.0（MBP 1.1.1 升级 + i9 ver 修复）→ #12/#13

### 验收
- i9 node-bridge 崩溃 30s 内自恢复
- 三端心跳 ver 字段一致（1.2.0）
- MBP 有 LLM 执行器门禁

---

## P4 · 治理层

### 任务分解
- [ ] **P4-1**: 台账自动化（脚本扫描 git tag + package.json version）→ #7
- [ ] **P4-2**: deploy-check 集成台账（审查后自动登记）→ #7
- [ ] **P4-3**: 审计日志统一（黑板+插件+台账联动）→ #7
- [ ] **P4-4**: 多租户安全（ZTNA/mTLS，门店隔离）→ #8

### 验收
- 插件发版台账自动更新（无手工）
- 台账与 git tag 一致性（脚本校验）

---

## P5 · 应用层

### 任务分解
- [ ] **P5-1**: ERP PG16 备份（pg_dump 定时 + 副本）→ #10
- [ ] **P5-2**: 订阅平台（租户管理 + 支付 + 计费）→ #3
- [ ] **P5-3**: 门店端到端（注册→隔离→数据→订阅）→ #8

### 验收
- ERP 数据可恢复（备份验证）
- 首个付费订阅门店接入

---

## 四、可靠性缺口 → 任务映射（15 项全）

| # | 缺口 | 任务 | 里程碑 |
|---|------|------|--------|
| 1 | peerDeps 缺 8 | P2-1~4 | M1 |
| 2 | 身份层未实现 | P1-3a~d | M2 |
| 3 | 计量层未实现 | P1-6a~c, P5-2 | M3 |
| 4 | 黑板无 HA | P1-7a~c | M3 |
| 5 | audit 无清理 | P1-8a~c | M2 |
| 6 | node-bridge 看门狗 | P3-1~3 | M3 |
| 7 | 台账手工 | P4-1~3 | M2 |
| 8 | FNP v0.7/v1.1 | P0-1/2, P2-5, P4-4, P5-3 | M4 |
| 9 | genebank 未启用 | P1-2a~c | M2 |
| 10 | ERP 单机 PG16 | P5-1 | M4 |
| 11 | 黑板 token 未启用 | P1-1b/1c | M2 |
| 12 | node-bridge 版本不一 | P3-4 | M3 |
| 13 | i9 ver 不透明 | P3-4 | M3 |
| 14 | tar.gz 未清理 | P2-6 | M1 |
| 15 | AbortSignal（已修）| — | ✅ |

---

## 五、里程碑（M1-M5）

| 里程碑 | 内容 | 任务 | 验证 |
|--------|------|------|------|
| **M1** | 插件可安装 | P2-1~4, P2-6 | MBP/i9 dsh plugin add 成功 + tar.gz 清理 |

**M1 进度（2026-08-28）**：P2-1 ✅ / P2-2 ✅ / P2-3 ⏸ git URL 替代 ✅ / P2-6 ✅ ｜ **三端注入验证全部完成**：mac ✅ / MBP ✅ / **i9 ✅（agentBus 注入式达成，非轮询）** ｜ **M1 达成（2026-08-28）** ｜ 剩余：npm 官方认证（可选优化）
**通讯通道演进遵循 CCEP v1.0**（永续通讯协议：旧通道投递新通道，验证可行才切换，除死机外不中断，见 docs/CCEP-continuity-protocol-v1.md）

**M2 进度（2026-08-28 审查）**：P1-8 ✅ / P4-1 ✅ / P1-2 ✅ / P1-3a ✅（register API）/ P1-3b ✅（identity） ｜ **审查修正：token 逐步启用（非三端同时）**——
- SSE 读端无 token 校验 → 注入链路不受影响
- node-bridge --token 已解析未用（需补请求头）
- 策略：node-bridge 补 token → 逐端升级 → dsh-tools 补 → 全局启用（无同时要求）
- **P1-3c 认证中间件 ✅（v0.6.4：Bearer+白名单+SSE 校验，实测 401/200 全过）** / P1-1c 客户端 token ✅（node-bridge v1.3.1 + dsh-tools v1.9.0）→ token 逐步启用可执行 ｜ **启用前置条件（关键）**：central-inbox v0.1.3（SSE 带 token）+ 三端 node-bridge v1.3.1（写带 token）——否则 token 一开注入断 ｜ 剩余：P1-3d 消息签名（openssl 零依赖方案）
**M1 完成门禁**：MBP/i9 用 `git+...#v1.3.0` 安装成功并确认加载 + 双向注入 → **MBP 已达成（注入验证 ✅）**；i9 确认后 M1 完成 → 进入 M2
| **M2** | 基础可靠 | P1-2, P1-3, P1-8, P1-1b/1c, P4-1 | 设备注册 + audit 可控 + token 认证 |
| **M3** | 企业级 | P1-6, P1-7, P3-1~4 | 云接管 + 计量 + 看门狗 + 版本统一 |
| **M4** | 多租户 | P0-1/2, P4-4, P5-1, P5-3 | 门店隔离 PoC |
| **M5** | 商业化 | P5-2 | 首个付费订阅 |

---

## 六、项目管理规则

1. **每项目独立管理**：状态/依赖/任务/验收（本蓝图）
2. **可靠性优先**：任何「目前够用」不通过——验收标准证明可靠
3. **依赖前置**：P0→P1→P2→P5；P4 贯穿
4. **里程碑门禁**：M1-M5 PoC 验证通过才进下一个
5. **版本管理**：git + CHANGELOG + SemVer（19 插件达标）
6. **台账自动化**：P4-1 落地后自动跟踪
7. **黑板同步**：每里程碑更新 data/iterations/ + data/protocol/

---

*FlowerNet 主蓝图 v4.0 · 2026-08-27 · 15 缺口全映射 · 企业级正式版*
