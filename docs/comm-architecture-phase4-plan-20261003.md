# 通讯架构治理 · 阶段四规划 v1.1（2026-10-03 星桥定稿 · MBP 对齐合并）

> 依据：阶段三全部成果 + 今日与 MBP 互查沉淀 + 星台↔xingqiao 通道审查 6 处违规 + 10-04 窗口执行表。
> 原则延续：每步带可验收指标 · 声明附证据（哈希/行号/输出片段）· 机械门而非头痛医头 · 双侧判据。

## 0. 阶段三收口清单（基线）

| 项 | 状态 | 关键证据 |
|---|---|---|
| ⑥ flip 板端鉴权 | ✅ v0.6.16 全矩阵 | 无头401/正规200/伪401/i9豁免/GET公开/SSE hello |
| ⑦ 方案 A | ✅ 补实现 1.5.12 | A-1 唤醒反转 L544 / A-2 限速 RATE_N=10 / A-3 阈值200；行为验收待重启 |
| ⑧ 积压治理 | ✅ 工具+基线 | triage 595/205/390；2 cron 编排两期 |
| 通讯连续性 | ✅ 0.2.10/1.5.12 | 冒烟递归 livelock 三证据；fs 导入；死前缀三处双侧修复 |
| 规范 v1.3 + R040 | ✅ | 铁律6 + rsync 陷阱 + 打包 SOP；registry 200 |
| R006 存量 | ✅ 273/273 | cldvoice 0.6.1 正负控 |
| 星台 App | ✅ 收口 | 签名过期→重签 SOP；通道审查 6 处；cldvoice 集成（成稿+草稿管理 v9.14） |
| MBP 互查 | ✅ | 共有缺陷双侧修复；交付协议（可复现打包/冻结/哈希/内容寻址）；R041 工具链 |

## 1. 阶段四目标

**A 通讯链路收敛**（0.2.11 批次，10-04 窗口后发）
1. central-inbox：own-node 别名（mac-mini/mbp/i9）→ 中枢解析；role-mapped-offline → 排完整 id 待唤醒（不丢卡）
2. 桥：/api/reply 加 latest-<session>→latest-main fallback；星桥通道统一 session='main'
3. bus-mrole 信封消费归位 + 补语义字段（reply_required/notify_only/subject）
4. mobile-reply 自动化（回复手机消息自动写卡，替代手工双键）
★ 5-9 MBP 对接点（两侧判据对齐）：
5. 别名可解析性带前缀判：`notes/<node>/` 前缀 ↔ `to:<node>` = 可解析（否则他 B7 拦、我收端放=双侧语义不一致）
6. 结局词汇细分：delivered / queued(offline) / unresolvable / dup-of-delivered / dup-of-queued（duplicate≠送达证据）
7. 收端 warn：awaiting 存在但 reply_required!==true（不唤醒却以为叫醒了）
8. from 规范化：∈{session-<id>, bus:<node>}；其他标 unattributed+warn
9. 去重键打日志前缀（「去重」与「投递失败」日志可区分）
- 验收：MBP 三卡形态回放（to=mac-mini → 中枢 delivered）；角色离线后唤醒自动投递；App 通道回复免手工；结局五词机器可判

**B 交付体系结构化**（10-04 窗口后即刻；MBP 9 条全采纳）
1. sha256 完整 64 位（16 位只识别不校验）
2. 载荷必带 files[]（逐文件对账，防清单手打漏项）
3. 键格式 data/packages/<name>-<sha8>.tgz-b64（sha8=sha256 前 8 位）
4. 幂等：同键同哈希跳过 PUT
5. 可复现三归零：tar mtime/uid/gid/uname/gname 归零 + 条目排序 + gzip(mtime=0)
6. 排除集 .bak*/__pycache__/.DS_Store/._*
7. 内容变→换键不覆盖；旧键保留可回滚
8. 发布前 GET 自检（键不存在或内容一致）
9. 工具就位：publish-package.py + verify-remote-package.py（自证 7+5 例）
- 验收：两次打包同 sha256；被篡改可检出；重发跳过 PUT

**C 账本与规则收敛**（10-04 09:22 窗口，两步法）
1. 12 条重分类（J29/J33-J44 按 MBP 表）→ 43→31
2. R041 迁移 31 条（merge-r041.py + verify-r041-migration.py 前后基线；改前基线已取 B1/C1/D1 无 G1/F1）
3. retiredEntries 索引 + 一致性门接入 + rules-integrity.py 复跑 + 计数口径更新
4. ★ 双侧规则编号冲突待决：我侧 R040=自查不得自指 / 他侧 R40=多出口同源、R41=补丁验命中——两账本同号不同义 ⇒ 定编号映射表或统一改号（迁移时一并处理）
- 验收：verifier exit 0（8 不变量）；迁移后基线全绿

**D 端侧注册与身份**（R038 续）
1. MBP/i9 端侧自注册器接入（services 字段 absent 约定）
2. role-map 并集发布为 registry 权威卡 + 各端同步机制（48h 内落本地）

**E 星台↔CLD 能力一致性 roadmap**
1. ✅ 成稿 + 草稿管理（v9.14）
2. 纠错按钮 UI（桥 /api/correct 已有，App 加按钮）
3. 草稿插入 CLD 上下文（桥 /api/draft/insert 转发）
4. 会议模式：先复用 MBP dsh-plugin-cldvoice 0.6.4（悬浮球全双工语音记录→setDraft+submit 注入会话；待他发接口卡+包）；增量（纠错按钮/草稿管理）先做
5. 文档漂移修复：dsh-plugin-cldvoice-agent 0.5.0-alpha README 复制自 0.6.4 未改（文档≠实现）→ 批次内改其一

**F 治理常态化**
1. 2 cron 挂载（一期 bus-triage 10-04 / 二期 queue-condense 10-05）
2. boot-sandbox 采纳（独立段，非他第⑧项=check_bundle_deps；他已有 ⑨/⑨b/⑩；R31 假绿灯已修版）
3. CLD 缺陷4 修复（owner 3d490920；已登记+入队）
4. SSE 重连基线分桶监控（方法已定：错误类型+日期分桶；阈值 0.6 次/天健康基线）

**G 服务端**（i9 回执后）
1. token 白名单追加（additive）+ v0.6.17 豁免移除 + 验收矩阵（脚本已在服务器 /tmp）
2. i9 token 上线确认（两相卡在途）

## 2. 时间锚点

| 时点 | 动作 |
|---|---|
| 10-04 04:00 CST | ★我侧窗口：维护重启（1.5.12/0.2.10 生效）→ 停窗 triage --apply → 自动验收入日志 |
| 10-04 09:22 CST 起 | launchd 一期（删 review-group + 装 bus-triage，2/2）；board-central（token 白名单/v0.6.17，需 i9 回执）；C 账本两步法（profile 补登记 excalidraw 同批） |
| 10-05 | launchd 二期（queue-condense）|
| 10-04~10-06 | A 批次 0.2.11 开发+双侧判据+发包（内容寻址键） |
| 持续 | F 常态化（cron 周/月报告 → data/ops/bus-triage-*） |

## 2.4 断电重启事故处置（2026-10-03 21:50-22:05 复盘）

- 根因：r006-retrofit.js（我方生成器）模板把「真挂载冒烟」内联进 runSelfCheck（apply 链内）→ openchronicle apply→runSelfCheck→import+apply 无限递归 → 子进程 livelock（100% CPU/日志 143MB）→ 关壳竞态撞上壳侧 main.js:434 未保护写 → 壳 abort → 崩溃循环。
- 修复：Claude 侧已修 openchronicle + 生成器模板（我方核实：现为 sync runSelfCheck + 守卫 runApplySmoke 仅 CLI，同 0.2.10 模式）。
- 我方核验：apply→runSelfCheck 调用点全盘仅 3 处（agent-way/central-inbox=我方已修好模式、openchronicle=已修）→ 10-04 重启不再触发此类。
- ★ 遗留 24 个插件仍带 async 内联冒烟模板（apply 未调用=潜伏雷，非即时炸弹）→ 批次 P0：r006-retrofit v1.4 模板已对，24 插件重生成 selfcheck（防重入+CLI 专用），10-04 窗口前完成。
- 壳侧 3 处未修（logStream 写后/热重载 undefined/运行期日志轮转）→ 已转派 3d490920 + 登记缺陷卡。
- 断电附带：Tailscale 停止（跨设备直连+Funnel 断）→ 待用户手动开；web 端口 52090→56426 漂移 → Funnel / 需 drift-fix 改指。

## 2.5 MBP 侧重启时序

- 他侧重启=用户手动动作（他不自行触发）；磁盘 1.5.12 已就位、重启前审查双出口通过（人读 exit 0 / --json _verdict=pass）。
- 是否两侧同窗口：由用户裁决（已提问）。

## 3. 风险与纪律（沿用今日教训）

- 判据必须有「应该判失败的输入」用例（MBP R31 教训）
- 发布卡附完整 64 位哈希 + 证据行号；「声明与实物一致 ≠ 已生效」口径
- 自测键不在被监听前缀（notes/_selftest/）+ 守卫拒绝 exit 3 可区分
- 交付通道=双方可达板键；PUT 冻结；内容寻址换内容必换键
