# FlowerNet 主蓝图 v3.1 · 完整细化版（再审查补全）

> 作者：mac-mini 中枢 ｜ 2026-08-27
> 依据：FlowerNet 主蓝图 v2.0（项目体系）+ 依赖可靠性审计（10 缺口）
> 定位：企业级（复用到所有门店 + 付费订阅花店商家）——完整、稳定、可靠。
> 本次更新：按可靠性审计结果，**补全每层依赖清单、任务分解、验收标准**，消除所有「未实现/未声明/无HA/无清理」缺口。

---

## 〇、蓝图总览（v3.0 更新点）

```
FlowerNet 主蓝图 v3.0
├── P0 协议层 · FlowerNet FNP ★（+v0.7 权限 / v1.1 能力发现）
├── P1 基础设施 · HubBridge Server（+身份层 / 计量层 / HA / audit清理 / genebank启用）
├── P2 插件层 · dsh 插件家族（+peerDeps 补全 11 个 / npm 发布 / 门店插件）
├── P3 桥接层 · node-bridge + dsh-tools（+跨平台看门狗）
├── P4 治理层 · deploy-check/自适应/台账（+台账自动化）
└── P5 应用层 · 花店蓝图 + 订阅平台（+ERP HA / 订阅计量）
```

**更新点（对比 v2.0）**：按可靠性审计补齐 10 项缺口——每层加「依赖清单」「任务分解」「验收标准」，企业级完整度。

---

## P0 · 协议层（FlowerNet FNP）

### 依赖清单
| 依赖 | 用途 | 状态 |
|------|------|------|
| rust-blackboard（传输实现）| KV+SSE 协议宿体 | ✅ |
| FNP v1.0 规范 | 语义定义（时间轴/任务卡/事件/身份/治理）| ✅ |
| **v0.7 per-namespace 授权** | 门店数据隔离 | ❌ 待实现 |
| **v1.1 能力发现** | 门店上报 capabilities | ❌ 待实现 |

### 任务分解
- [ ] P0-1: v0.7 per-namespace 授权（store-01 只能写 data/store-01/*，X-Writer 校验）
- [ ] P0-2: v1.1 能力发现（门店注册时上报 capabilities，黑板 /capabilities 查询）
- [ ] P0-3: 协议版本协商（fnp/1.0 头部，旧版兼容）

### 验收标准
- 门店 A 的 store-01 无法写 store-02 命名空间（隔离生效）
- 门店注册后可被 /capabilities 发现

---

## P1 · 基础设施层（HubBridge Server）

### 依赖清单
| 子项 | 依赖 | 状态 |
|------|------|------|
| 1.1 传输 | rust-blackboard（8792+8803）| ✅ |
| 1.2 资产 | rust-genebank（/api/v1/genes）| ⚠️ 未启用 |
| 1.3 身份 | device-id + Ed25519 + token | ❌ 未实现 |
| 1.4 路由 | 黑板 KV + SSE 事件桥 | ✅ |
| 1.5 设备 | 心跳 60s + verify-watch | ✅ |
| 1.6 计量 | token 计量（SQLite）+ 订阅层级 | ❌ 未实现 |
| 1.7 HA | 独立部署（腾讯云轻量）+ 副本 | ❌ 单机 |
| 1.8 运维 | audit 轮转 + 清理 + 归档 | ❌ 无策略 |

### 任务分解
**1.2 genebank 恢复启用**
- [ ] P1-2a: 启动 rust-genebank（三平台产物已编译）→ 验证 /api/v1/genes
- [ ] P1-2b: 与黑板集成（资产注册 → data/genebank/* 同步）
- [ ] P1-2c: 内容寻址去重验证（同内容同 gene_id）

**1.3 身份层**
- [ ] P1-3a: 设备注册 API（POST /register → 生成 device-id + 签发 token）
- [ ] P1-3b: 设备端 identity.json（~/.dsh/hubbridge/identity.json：UUID + Ed25519 私钥）
- [ ] P1-3c: 认证中间件（所有 API 带 Bearer token，白名单校验）
- [ ] P1-3d: 消息签名（Ed25519 签名 → 防伪造）

**1.6 计量层**
- [ ] P1-6a: token 计量器（SQLite：消息数/字节/LLM 调用）
- [ ] P1-6b: 订阅层级（free/pro 配额）
- [ ] P1-6c: 计量 API（租户查询用量）

**1.7 HA**
- [ ] P1-7a: 部署腾讯云轻量（docker 化 rust-blackboard + genebank + 身份/计量）
- [ ] P1-7b: 数据副本/备份策略（snapshot 定时备份）
- [ ] P1-7c: 故障恢复演练（mac 挂 → 云实例接管）

**1.1b 安全认证（再审查 #11）**
- [ ] P1-1b: 黑板启用 BLACKBOARD_TOKEN 认证（启动设 token，客户端带 token）
- [ ] P1-1c: 客户端适配（node-bridge/dsh-tools/central-inbox 全部带 token）

**1.8 运维**
- [ ] P1-8a: audit 轮转（按天分文件，当前按 ~10min 切需优化为按大小+日期）
- [ ] P1-8b: 保留策略（audit 保留 N 天，超期压缩+归档）
- [ ] P1-8c: 磁盘监控告警（audit 增长速率）

### 验收标准
- 独立部署后 mac 关机，云实例继续服务（HA）
- 新设备注册 → 白名单生效 → 未注册设备 401
- audit 磁盘增长可控（轮转后 < 100MB/天）
- genebank /api/v1/genes 可用（注册/检索/去重）

---

## P2 · 插件层（dsh 插件家族）

### 依赖清单（peerDeps 补全 —— 可靠性审计 #1）
| 插件 | 完整 peerDeps（11 个）|
|------|----------------------|
| dsh-plugin-agent-way | cordis / dsh-tools / dsh-client-runtime / **dsh-agent / dsh-session-persistence / dsh-settings / dsh-system-prompt / dsh-host-webserver / dsh-agent-default-model / dsh-agent-presets / dsh-client-locale** |
| dsh-plugin-central-inbox | 依赖 agentBus 服务（agent-way 先装）|

### 任务分解
- [ ] P2-1: **补全 peerDeps 到 11 个**（对照 dsh-agent-teams 16 个写法，语义化 ^0.1.0-rc.6 覆盖 rc.8/rc.2）
- [ ] P2-2: 干净环境验证 `dsh plugin add`（pnpm 解析全部 peer）
- [ ] P2-3: npm 发布（scoped: @coreyleung-art/dsh-plugin-agent-way）
- [ ] P2-4: 三端官方安装验证（mac/MBP/i9 `dsh plugin add` → [agent-bus] 加载）
- [ ] P2-5: 门店插件（FlowerNet 接入：device-id 注册 + 消息收发）
- [ ] P2-6: npm 发布后归档 genebank 的 9 个 tar.gz（再审查 #14）

### 验收标准
- MBP/i9 用 `dsh plugin add @coreyleung-art/dsh-plugin-agent-way` 安装成功（**修复可靠性审计 #1**）
- 三端 [agent-bus] 加载 + agentBus 服务上线 + 双向注入

---

## P3 · 桥接层

### 依赖清单
| 组件 | 依赖 | 状态 |
|------|------|------|
| node-bridge | serde/serde_json/chrono（Rust）| ✅ |
| node-bridge 看门狗 | **跨平台自愈（win 计划任务/内置 supervisor）** | ❌ |
| dsh-tools | serde_json/chrono | ✅ |

### 任务分解
- [ ] P3-1: node-bridge 内置 supervisor 线程（崩溃自动重启，跨平台）
- [ ] P3-2: Windows 服务注册（i9 侧计划任务/服务）
- [ ] P3-3: 看门狗健康检查（心跳丢失 → 自动拉起）
- [ ] P3-4: 三端 node-bridge 统一 v1.2.0（MBP 1.1.1 升级 + i9 ver 字段修复，再审查 #12/#13）

### 验收标准
- i9 上 node-bridge 崩溃后 30s 内自动恢复（无需人工）
- 三端心跳持续在线

---

## P4 · 治理层

### 依赖清单
| 组件 | 依赖 | 状态 |
|------|------|------|
| deploy-check | 纯 Rust | ✅ |
| 版本自适应 | adapt.js | ✅ |
| 台账 | tools-registry.md | ⚠️ 手工 |
| 日志规范 | logs/ + 归档脚本 | ✅ |

### 任务分解
- [ ] P4-1: 台账自动化（脚本扫描 git tag + package.json version → 自动更新 tools-registry.md）
- [ ] P4-2: deploy-check 集成台账（审查后自动登记版本）
- [ ] P4-3: 审计日志统一（黑板 audit + 插件日志 + 台账联动）

### 验收标准
- 插件发版后台账自动更新（无手工）
- 台账与 git tag 一致性（脚本校验）

---

## P5 · 应用层

### 依赖清单
| 组件 | 依赖 | 状态 |
|------|------|------|
| ERP | PG16（单机）| ⚠️ 无 HA |
| 花店驾驶舱 | 面板 8787 + 黑板 | ✅ |
| 订阅平台 | 支付/计费/多租户 | ❌ |

### 任务分解
- [ ] P5-1: ERP PG16 备份策略（pg_dump 定时 + 副本）
- [ ] P5-2: 订阅平台（租户管理 + 支付接入 + 计费）
- [ ] P5-3: 门店端到端验证（注册 → 隔离 → 数据 → 订阅）

### 验收标准
- ERP 数据可恢复（备份验证）
- 首个付费订阅门店接入

---

## 里程碑路线（M1-M5，细化）

| 里程碑 | 内容 | 依赖 | 验证 |
|--------|------|------|------|
| **M1** | P2 插件可安装（peerDeps 11 + npm + 三端官方安装）| P2-1~4 | MBP/i9 dsh plugin add 成功 |
| **M2** | P1 基础可靠（genebank 启用 + 身份层 + audit 清理）| P1-2/3/8 | 设备注册 + audit 可控 |
| **M3** | P1 企业级（计量 + HA 云部署）| P1-6/7 | 云实例接管 + 计量可用 |
| **M4** | 多租户（门店隔离 + 订阅逻辑）| P0-1/P4-4 | 门店 PoC（A 看不到 B）|
| **M5** | 商业化（首个付费订阅）| P5-2/3 | 订阅收入 |

---

## 项目依赖矩阵（可靠性审计映射）

| 可靠性缺口 | 归属 | 蓝图任务 | 里程碑 |
|-----------|------|---------|--------|
| #1 peerDeps 缺 8 | P2 | P2-1 | M1 |
| #2 身份层未实现 | P1 | P1-3 | M2 |
| #3 计量层未实现 | P1 | P1-6 | M3 |
| #4 黑板无 HA | P1 | P1-7 | M3 |
| #5 audit 无清理 | P1 | P1-8 | M2 |
| #6 node-bridge 看门狗 | P3 | P3-1/2 | M3 |
| #7 台账手工 | P4 | P4-1 | M2 |
| #8 FNP v0.7/v1.1 | P0 | P0-1/2 | M4 |
| #9 genebank 未启用 | P1 | P1-2 | M2 |
| #10 ERP 单机 PG16 | P5 | P5-1 | M4 |
| #11 黑板 token 未启用 | P1 | P1-1b/1c | M2 |
| #12 node-bridge 版本不一 | P3 | P3-4 | M3 |
| #13 i9 ver 不透明 | P3 | P3-4 | M3 |
| #14 tar.gz 未清理 | P2 | P2-6 | M1 |

---

## 项目管理规则（v3.0 强化）

1. **每项目独立管理**：状态/依赖/任务分解/验收标准（本蓝图表格）
2. **可靠性优先**：任何「目前够用」不通过——必须有验收标准证明可靠
3. **依赖前置**：P0→P1→P2→P5 依赖链 + 可靠性审计映射
4. **里程碑门禁**：M1-M5 每个 PoC 验证通过才进下一个
5. **版本管理**：每插件/工具 git + CHANGELOG + SemVer（19 插件已达标）
6. **台账自动化**：P4-1 落地后自动跟踪
7. **黑板同步**：每里程碑更新 data/iterations/ + data/protocol/

---

*FlowerNet 主蓝图 v3.0 · 2026-08-27 · 基于可靠性审计完整细化 · 企业级*
