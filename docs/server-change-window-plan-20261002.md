# 服务器变更窗口计划（三期③ · 2026-10-02 星桥起草）

> 一次窗口合并两件事：bb-sub 升级去重 + bus-bridge token 多端白名单。都动 xingqiao 服务器。
> 触发条件：交叉编译工具链就绪（musl linker）或 Docker 编译通道可用。

## 变更 1：bb-sub 升级（v1.4.2 → v1.25.1 编译产物）

| 项 | 内容 |
|---|---|
| 判据 | journal 实测同一键重复推送（00:14→00:17 同键两次）——无去重实锤 |
| 动作 | 交叉编译 linux-musl 静态二进制 → scp 到 /opt/comm-layer/bin/dsh-tools.new → 备份旧 → 替换 → 重启 8×comm-bb-sub-*.service |
| 验收 | 同一键 3 分钟内只推 1 次（journal 对照）；服务 8/8 active；订阅链路回归（写一张测试卡看注入） |
| 回滚 | 旧二进制备份 + 8 服务重启回旧 |

## 变更 2：bus-bridge token 多端白名单

| 项 | 内容 |
|---|---|
| 判据 | 单 token 双端共享+无轮换=中风险（评估文档 bus-token-rotation-eval-20261002.md） |
| 动作 | 服务器 bus-bridge.js 的 authOk 改 TOKENS 集合成员判定 → env 加 TOKENS 逗号分隔 → 每端独立 token 分发 |
| 验收 | 新 token receive ok / 旧 token 401（正负对照）；两端 bus send 全链路复测 |
| 回滚 | bus-bridge.js.bak + env 还原 + systemctl restart |

## 执行纪律
- 每项变更前经 channel-gate 登记（board-central 通道，drift-fix/change 按性质）。
- 窗口期：服务器 1G 内存，禁止同时跑重活；变更一步一验（R030）。
- 用户在场或授权后执行。

## 依赖清单（先解后行）
1. musl 交叉链接器（brew install FiloSottile/musl-cross/musl-cross）或 Docker CLI 配置。
2. 用户批准执行时间。

## 变更 3：SSE 事件重放（Last-Event-ID）—— catch-up 结构补全

| 项 | 内容 |
|---|---|
| 判据 | central-inbox 纯 SSE + 重连不带 Last-Event-ID；服务器 sse.rs 无 id 字段/无重放缓冲 ⇒ 断线期间漏卡不可回放（客户端已靠 sync-from-central 兜底，但 SSE 本身不完整） |
| 动作 | sse.rs：broadcast 每条事件带 `id: <全局递增 seq>`；连接时读 Last-Event-ID 头，从 seq+1 重放（有界缓冲，如 500 条）；central-inbox 重连时带上上次收到的 id |
| 验收 | 断 SSE 30s 期间写 3 卡 → 重连后 3 卡按序重放注入（对照：改前 3 卡丢失） |
| 回滚 | sse.rs.bak + 重启 |


## 执行日志（2026-10-03 用户授权执行）

| 变更 | 结果 | 证据 |
|---|---|---|
| 1 bb-sub 升级 | ✅ v1.25.3 | v1.25.1 的 (key,version) 去重被「板每写必增 version」推翻（探针 3 写 3 推）→ 改 key#内容指纹：同内容 3 写 1 推、内容变照常推 |
| 2 token 多端白名单 | ✅ | TOKENS=旧+新-mac（新-mbp 已撤销，MBP 改自生成哈希互证流程）；三真 200/伪 401/无 401 |
| 3 SSE 重放 | ✅ v0.6.10→0.6.11 | sse.rs id+500 缓冲+Last-Event-ID；顺带修了**双重广播 bug**（store.notify 与 http 层各广播一次，SSE 客户端每事件收两遍）；测试区断连 2 事件按序重放各一次 |
| ★ 事故 | 🔴 黑板数据丢失+恢复 | 中央板 9-06 起持久化静默失败（root 属主+ubuntu 运行，audit 写入被吞）⇒ 27 天内存态 ⇒ 重启全丢；88MB 快照恢复引发 1G 内存颠簸 20+ 分钟，用户控制台删快照空态恢复；现 v0.6.11 持久化失败会告警 + 数据目录已 chown。恢复：本机板定向推送（mbp 590/registry 852/collab 458/ops 12152/rules）+ E2 自愈 + MBP 重推独有键 |

## 变更 4（预备 · 2026-10-03 登记 · 10-04 04:00 窗口执行）：i9 路径豁免移除（板端 v0.6.17）

| 项 | 内容 |
|---|---|
| 判据 | is_public_path 对 i9 全路径免鉴权（含写）⇒ i9 写端无 token 也 200，flip 对 i9 形同虚设 |
| 动作（两相） | ①服务器白名单 env 追加 `bb-token-20261003-i9`（指纹 48ae1cf50cf27799）+ 重启板；②i9 配置令牌并回执（卡 notes/i9/token-onboarding 已发）；③v0.6.17 移除 is_public_path 全部 i9 行 + 部署 + 重启 |
| 验收 | i9 带 token 写 notes/i9/x → 200；i9 无 token 写 → 401；GET 公开仍 200；clock/register 公开不变 |
| 回滚 | 服务器旧二进制 rust-blackboard.bak-20261003-033454 + env 回退 + 重启 |
| 门 | board-central 通道变更 2/24h 配额（10-03 已被 flip 用满）→ 10-04 00:00 后配额滚动方可 register；变更前跑 drift_scan + channel_gate register |
| 预备状态 | ✅ 源码 store.rs 已删豁免（v0.6.17，Cargo.toml 同步）；✅ 单元测试 public_path_i9_exemption_removed 12/12 通过；✅ linux-musl 二进制已预编译（target/x86_64-unknown-linux-musl/release/rust-blackboard）；✅ 令牌+指纹+上线卡已发 i9（notes/i9/token-onboarding，双板一致） |
| 前置条件 | i9 回执「已配置+实测 200」（reply_required 卡在途） |

## 变更 5（用户裁决 2026-10-03 · launchd 编排）：review-group.daily 退役 + 2 cron 挂载

| 项 | 内容 |
|---|---|
| 判据 | launchd-scan 08:26Z：com.dsh.waimai.review-group.daily loaded 但引用脚本 daily-review-group.py 不存在（已归档 archived-*）；用户裁决「沉淀清理记录后删 plist」。另 ⑧ 积压治理 2 cron（bus-triage 每周一 09:00 / queue-condense 每月 1 日 09:30）plist 已备 |
| 门状态（★10-03 16:5x 读门状态文件实测） | launchd-daemons / board-central / bus-8791 的 24h 窗口起点=1790937770（10-03 01:22:50Z）⇒ **配额 10-04 09:22 CST 才滚动**；tailscale-direct 10-04 12:25 CST。故 04:00 维护重启窗口内 launchd/board 变更仍被门挡，改按下列时序 |
| 一期（10-04 04:00 CST，非门控项） | ①CLD 维护重启（既有 plist）→ 重启后 post-restart-acceptance 全量验收；②CLD 停机期跑 bus-queue-triage --apply（expireable 205 基线实测；死形态靠 --apply，插件 A2 TTL 只管超龄）——数据处置非通道变更 |
| 二期（10-04 09:22 CST 起，launchd 2/2 + board-central 2/2） | ①删 review-group plist（备份+记录已备）②装 com.dsh.cron.bus-triage（已备）③服务器：token 白名单追加 i9（additive）→ 若 i9 已回执则 v0.6.17 部署+重启+验收矩阵（/tmp/comm-server-1004-deploy.sh 已上服务器） |
| 三期（10-05，launchd 1/2） | 装 com.dsh.cron.queue-condense（dsh-tools v1.25.0 实测可用：本机 595 queued/429 精确重复） |
| 回滚 | 各 plist 删除前备份；卸载=launchctl bootout 即回滚 |
| 预备状态 | ✅ 清理记录落盘 ✅ plist 备份 ✅ 2 cron plist + install.sh（cron-ready/，plutil OK）✅ queue-condense 命令实测 ✅ 服务器 10-04 脚本+二进制已上 /tmp（见变更 4） |

## 变更 6（10-04 窗口 · 账本迁移两步法，MBP 更正采纳）

| 项 | 内容 |
|---|---|
| 判据 | 我侧 J 资源冲突=43 vs MBP=31；差额 12 条（J29/J33-J44）他已在 10-03 重新分类为行为规则（跨对象行为准则=规则留账本；具体路径/端口/服务占用=数据进外挂表）。直接按 43 迁会把 12 条规则当数据搬走=规则丢失 |
| 动作 | ①先按 MBP 表重新分类 12 条（J29→工程/J33→协作/J34→协作/J35→工程/J36→架构/J37→工程/J38→协作/J39→方法论/J40→方法论/J41→协作/J43→方法论/J44→工程）②再 R041 迁移仅剩 31 条（分章节 ^## J 精确删+断言被删全为资源冲突类+retiredEntries 索引+一致性门）③rules-integrity.py 复跑 ④计数口径更新（87 → 56+新分类分布） |
| 附带 | role-map 已并集（+mbp×4 键，共 24）；put-card-selftest 前缀已移 notes/_selftest/（自污染修复） |
