# Comm-Server 服务器管理规范 v1.0（Lean4 约束前置范式 · Φ9 应用）

> 2026-09-06 星桥起草 · 服务器：xingqiao.meetfunbp.com (106.53.214.108, Ubuntu 22.04)
> 范式：**约束前置·不可绕过**（Φ9）+ Lean4 类型化分区（生产/测试隔离如类型系统）
> 状态：🟢 中枢已部署（systemd comm-server active）

---

## 〇、Lean4 式设计总纲

### L1 约束前置（不可绕过的三层约束）
```
约束0 访问层：SSH 仅密钥（root 禁用密码）+ 8792/8803 仅白名单 IP
约束1 数据层：生产/测试数据物理隔离（不同 data-dir，永不复用）
约束2 变更层：所有服务器变更走"预判卡→审批→执行→验证"（无验证成功=未成功 R030）
```

### L2 类型化分区（生产/测试如类型系统隔离）
```
Prod 区：/var/lib/comm-server（生产黑板：三端实时）
Test 区：/var/lib/comm-server-test（测试黑板：验证新版本）
隔离规则：二进制可共用，数据目录永不复用；Test 崩溃不影响 Prod
```

### L3 功能预判（穷举可能演进方向，前置规划）
```
P0 即时：通讯中枢（三端心跳/任务/黑板）          ← 已上线
P1 短期：认证加固（token 轮换 + IP 白名单）        ← 安全组放行后
P2 中期：多门店协同总线（各店 agent 注册+路由）    ← 预留 notes/store-<id>/
P3 远期：跨店数据聚合（销售/库存/客流分析中心）    ← 数据契约先行
P4 演进：云函数兜底/异地容灾（数据增量备份）
```

### L4 多门店协同准备（数据分区契约）
```
notes/store-<id>/           每店独立命名空间（如 store-2/ store-8/）
tasks/store-<id>/           每店任务队列
nodes/store-<id>/heartbeat  每店守护心跳
预留：store 注册表（id→店名→agent→通道）→ 单店故障不影响他店
```

---

## 一、安全策略（Lean4 式：防御矩阵穷举）

### 1.1 攻击面矩阵（who-can-do-what 穷举）
| 访问者 | SSH | 8792 读写 | 8803 SSE | 治理动作 |
|---|---|---|---|---|
| mac-mini（星桥） | ✅ 密钥 | ✅ | ✅ | ✅ 全权 |
| MBP 总线 | ✅ 密钥 | ✅ | ✅ | ✅（预判卡） |
| i9（Windows） | ❌（无密钥） | ✅ token | ✅ | ✅（预判卡） |
| 星台 App | ❌ | ✅ 专用 token | ❌ | ❌ |
| 公网匿名 | ❌ 拒绝 | ❌ 拒绝 | ❌ 拒绝 | ❌ |

### 1.2 三层防御（纵深）
```
D1 网络层：腾讯云安全组仅放行 {mac-mini/MBP/i9 出口 IP} × {8792,8803,22}
D2 传输层：黑板 token（每端独立 token，可单端吊销）
D3 应用层：data-dir 权限 0700 + 定时完整性校验（sha256 清单）
```

### 1.3 密钥管理
- 服务器 SSH：仅 startbrige.pem（0600）+ mac-mini 公钥注入 authorized_keys
- 禁用 root 密码登录 + PermitRootLogin prohibit-password
- 黑板 token：首次 = bb-token-comm-server-v1；接入后每端独立子 token

### 1.4 审计
- systemd journal 持久化（journald 默认）+ 定时快照（数据目录 tar + sha256）
- 异常检测：连接日志（ss 快照）+ 磁盘/内存监控（cld-monitor 思路移植）

---

## 二、生产/测试分区（类型化隔离）

### 2.1 目录结构
```
/opt/comm-server/
  rust-blackboard            # 二进制（版本化，升级换名）
  rust-blackboard-test       # 测试版二进制（验证后提级）
/var/lib/comm-server/        # PROD 数据（生产）
/var/lib/comm-server-test/   # TEST 数据（测试，可随时清）
```

### 2.2 双实例（Prod + Test 并行）
```
Prod :8792/:8803  → 三端生产流量
Test :8794/:8805  → 新版本验证（升级前先 Test 跑 24h）
升级门：Test 验证通过 → 停 Prod → 换二进制 → 起 Prod → 数据完整性校验
```

### 2.3 回滚预案
- 旧二进制保留（.prev）→ 一键回滚（systemctl + 二进制替换）
- 数据不动（分区隔离=升级不影响数据）

---

## 三、功能预判（分阶段演进）

### Phase 0 ✅ 已上线
- rust-blackboard 中枢部署（systemd active）
- 数据目录初始化

### Phase 1 安全加固（安全组放行后 1h）
- [ ] 腾讯云安全组：仅 {mac-mini/MBP/i9} IP 放行 8792/8803/22
- [ ] token 初始化 + 各端独立子 token
- [ ] root 登录禁用 + authorized_keys 注入 mac-mini

### Phase 2 三端接入（cs3）
- [ ] mac-mini：黑板端点改指 xingqiao.meetfunbp.com:8792
- [ ] MBP：同改（心跳/订阅/注入走中枢）
- [ ] i9：同改（win 客户端连中枢）

### Phase 3 多门店协同（数据契约先行）
- [ ] store 注册表设计（id→店→agent→通道）
- [ ] notes/store-<id>/ 命名空间启用
- [ ] 单店 agent 注册（守白 store-8 试点 → 全店推广）

### Phase 4 数据聚合 + 容灾
- [ ] 跨店聚合分析（销售/库存/客流）
- [ ] 每日数据快照（异地备份 mac-mini）

---

## 四、Lean4 不变量（系统必须始终成立）

```
I1 生产数据永不与测试数据混合（分区物理隔离）
I2 任何变更前必有备份（可回滚）
I3 无验证的成功=未成功（R030：改后必验）
I4 通讯永续（P3：通道异常立即修复，服务器变更不得造成三端断连）
I5 安全组白名单最小化（不放开不必要端口/IP）
```

---

## 五、待办（下一步执行序）
1. ⚡ 安全组放行 {mac-mini/MBP/i9} → 8792/8803/22（需用户腾讯云控制台操作）
2. ⚡ root 登录禁用 + mac-mini 公钥注入
3. Test/Prod 分区落地（8794 测试实例）
4. 三端接入验证（mac-mini 先）
5. store 分区契约文档（多门店协同蓝图）
