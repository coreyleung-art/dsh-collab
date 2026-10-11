# 智能体通信底座 · 现状总览（交接视图）

> **时点** 2026-10-01 深夜 / 10-02 凌晨 ｜ **节点** mac-mini ｜ **会话** session-fa1f9150
> **配套详档**：
> · `docs/agent-comm-substrate-mechanisms-and-archaeology-20261001.md`（v1 · 机制与证据链）
> · `docs/agent-comm-substrate-archaeology-official-baseline-v2-20261001.md`（v2 · 考古全图 + 官方基准重审）
> · `~/dsh-comm-shared/INVARIANTS.md`（I1–I7 契约 · 三层判定 · 实测规格）
> **本文定位**：不看过程，只看「现在什么状态、什么没过、下一步该做什么」。

---

## 0.5 最终验收（2026-10-02 04:34 重启后 · 目标已达成）

| 目标项 | 验收结果（实测） |
|---|---|
| ① 断产因 | node-bridge v1.4.2（日志 0 KB/15s、inbox churn 0%）· bb-sub v1.12.2×8（订阅日志 16MB）· guard 署名（重启后生效，A6 self-echo 实测拦截） |
| ② 清淤 | queued **2059→305**（expired 回收 1771，与预期分毫不差）· 标签式 from **1785→507**（迁移修复 1284；507 为无 id 可抽的角色标签 = R2 残留）· 订阅日志 **666k 行→2MB** |
| ③ 建机制 | I3/I4/I5/I6/I7 审计全 PASS；一键验收 **6/6**；A6 自回声探针返回 self-echo（零污染） |
| 最终矩阵 | **PASS 5 · PENDING 1（历史债）· GAP 0 · FAIL 1（衰减中：近 7 天 4 条且全为重启前）** |

**遗留（不影响目标达成，已各有文档）**：清淤清单待批（cleanup-candidates-list）；两处 plist 明文凭据待处置（security-node-bridge-plaintext-token）；R2 残留 507 条角色标签须发送侧改约定；I2 历史重复属数据债。

## 0.5 第 3–4 轮更新（2026-10-02 凌晨）

> 目标已立（goal-a56e76d5）：单设备+多设备跨 agent 协作架构的科学/有效/节约/资源治理底座。

| 项 | 状态 |
|---|---|
| **P0 官方镜像** | ✅ 已恢复 `~/tech-research/dsh-docs/`（582 文件/23MB + refresh.sh）；`guard_doc_check` 端到端命中 |
| **bb-sub 修复上推** | ✅ 主线 v1.25.1 携同一修复（去重+轮转+启动轮转），副本编译通过；与已部署 v1.12.2 一致 |
| **rust-bridge CHANGELOG 欠账** | ✅ v1.4.0/1.4.1 从 git 事实回填 |
| **dsh-doc 告警** | ✅ 根因锁定：**不在 `dsh.profile.bundles`**（有意停用）⇒ 修改式残块每次 dump 报警；已改为纯注释并留恢复路径，告警清零 |
| **plist 凭据审计** | ⚠ 两处明文凭据：node-bridge（已知）+ **wecom-inbox（新发现）**；处置四步已列文档，未动手 |
| **agent-way 版本** | 1.5.6（I3/I4 回执订阅 + I5 原子写 + I7 inject + A2 过期/DLQ + I1 from 迁移）全部待重启 |

## 1. 一句话现状

**已完成三批改动（A 批修复 / D2.1 署名 / 两处空转闸门 + I1-I7 契约），全部通过闸门但尚未重启生效；
官方回执机制已实测可订阅（I3/I4 的实现路径已明确）；同时在清点工具库时抓到一个正在跑的实质缺陷——跨设备通道 node-bridge 每 5 秒重放全部 1,513 个历史键。**

---

## 2. 已改、待重启生效（**这是当前最大的悬空项**）

| 批 | 内容 | 状态 |
|---|---|---|
| **A4** | `to` 先 `normalizeTo` 再解析（显示名/后缀/列表） | 已改 · 预检 GO |
| **A4a** | 共享模块 `normalizeTo` 抢救**括号内 id**（`明鉴 (a190c54c)` 原先只剩 `明鉴`） | 已改 |
| **A4b** | 8 位短 id → 按活跃会话**唯一前缀解析**（歧义 fail-closed） | 已改 |
| **A4c** | `broadcast` 收件人同样归一化 + 规范 id 自排除（原为**未激活**缺陷） | 已改 |
| **A4d** | **`from` 归一化**（`to` 缺陷的镜像）+ 裸 UUID 补 `session-` 前缀。真实 11 种违规 `from` **救回 9 种** | 已改 |
| **A6 v2** | 自回声改为 `normalizeTo(from) ∩ normalizeTo(to)`（v1 判 `from`，语义颠倒且是哑火地雷） | 已改 |
| **D2.1** | `guard.repair_report` 记**真实作者**（`exec.agent.id`），显示名另置 `writerLabel`；`send-repair-report.py` 同步修 | 已改 |
| **D2.3** | 预检冒烟**隔离副作用** + 硬断言「该插件生产日志字节增量必须为 0」 | 已改 |
| **共享** | `identity.js` 增 `resolveShortId` / `resolveAuthor` / `authorLabel` / `newMessageId` / `digestKey` | 已改 |
| **闸门** | `selfcheck.js` ESM 死码修复 + 两个自检模块补 CLI 入口 + 预检 A 项假 NO-GO 修复 | 已改 |

**版本**：`dsh-plugin-agent-way 1.5.4` · `dsh-plugin-central-inbox 0.2.1` · `dsh-plugin-guard 0.1.1`（新建 CHANGELOG）
**闸门**：三插件预检 **全 GO**；五个自检 **exit=0**（共享 59 / 审计 10 / 预检 14 / central-inbox 15 / selfcheck PASS）
**回滚点**：`~/dsh-collab/guard/backups/…bak-good-2026-10-01-{16-1,17-0}` 共 6 个

> ⚠️ **不重启则以上全部不生效**（`link:` 部署但 ESM 模块缓存使改动对常驻进程不可见；已实测确认）。

---

## 3. 现网不变量矩阵（I1–I7 · 可复跑）

```
PASS 1 · PENDING 1（已休眠，修复待部署）· GAP 4（机制尚不存在）· FAIL 1（活跃违规）

✅ I6 闸门必须能被证伪          符号探针检出 + CLI 退出码=1
❌ I1 身份与标签分离            近 7 天新增 106 条（存量 1785 条另计）
🟠 I2 唯一 id 与重复放行        60 秒内真重复 1320 条，最近一次 3.7 天前；根因（A5 键）待重启
🟡 I3 ack 语义                  状态词汇仅 delivered/queued，无「已回执」档
🟡 I4 运行区间                  消息字段无回执/空闲区间字段
🟡 I5 载体原子性                20.3 MB 整份 writeFileSync
🟡 I7 投递模式                  4886/28712（17.0%）指针式通知，从未使用 inject
```

复跑：`node ~/dsh-comm-shared/selftest.js` ｜ `python3 ~/dsh-collab/scripts/comm-invariant-audit.py [--selftest]`

---

## 4. 已实测的关键事实（供后续决策，勿再重复推导）

| # | 事实 | 证据强度 |
|---|---|---|
| F1 | **第三方 Cordis 插件可订阅** `agent/inbox/{inserted,claimed,discarded}` 与 `agent/status`；非作用域监听者收得到 | ★★★ 动态插件冒烟，6 条事件实测 |
| F2 | 事件**原样带回调用方传入的 message id**；未传 id 时由 harness 分配 UUID | ★★★ 受控对照（`probe-…` vs 用户消息的 UUID） |
| F3 | `inserted → claimed` 同轮次内闭合（12ms / 17ms），`claimed` 携带 `turn` | ★★★ |
| F4 | `agent.inject()` **确不唤醒**（进上下文但不新开轮次）；`agent/status idle` 是真边界 | ★★★ |
| F5 | **总线 `followup` 路径**产生的 `inserted` 其 `msg` 是否为 `bus-xxx` | ★★ **推断**（源码 `followup({id: msg.id,…})` + F2 对照支持），未直接观测 |
| F6 | `dsh-atomic-write` 提供 `writeFileAtomic` + `withFileLock` ⇒ 原「换 SQLite 载体」可取消 | ★★★ 官方 README |
| F7 | 官方 **Agent Teams**（Agent Note 2026-08-05）覆盖身份/mailbox/task；**未随本 runtime 发布**（experimental） | ★★★ `ls node_modules` 无 team 包 |
| F8 | 官方文档在 **GitHub docs/ 75 项 + 196/202 包内 README**；**`~/tech-research` 镜像为空** ⇒ P0 闸门无数据源 | ★★★ |
| F9 | 注入会**打断 KV cache 复用**（官方原文）⇒ 注入成本不止几条消息的 token | ★★★ 官方 README |

---

## 5. 考古结论（改变了对"问题性质"的判断）

| 结论 | 依据 |
|---|---|
| **真实纪年**：装于 **08-15**；总线首条消息 **08-16 15:17:33**；**08-17 为原型日** | 会话文件 mtime / agent-bus.json / `bus-plugin-contract.md` |
| **同一根因在第 3 天就被诊断**：`bus-queue-mechanism-analysis.md` v0.1 的四条根因**至今一字未改**；queued **69 → 2059（30×）** | 08-17 原文 vs 今日实测 |
| **★ 解过又解开**：08-23 黑板纪律「**迭代报告走黑板归档即止；纯确认不再 agent_send**」+ 通道分级（STATUS/ACK→黑板；TASK→p2p；COLLAB→线程；EVENT→事件总线；BATCH→邮箱） | 黑板 `data/ack/92623479` |
| **★ 订阅机制曾经有**：`subscriptions.json`（08-22）含各 agent 的 topic 表，**但从未接进 central-inbox**（后者至今硬编码单目标） | 订阅表 + `central-inbox/lib/index.js:80` |
| **★ TTL 曾经有**：08-17 初代契约的 `target/action/payload/`**`ttl_sec`**`/wait`；`~/.dsh/bus-queue/` 实盘跑过；**后在 agent-bus 上丢失** | 契约 + 状态目录最后活动 09-06 |
| 更早祖先：**AgentHub**（2026-04-23，多智能体协作平台 + 设备注册） | `~/Downloads/AgentHub_*` |

---

## 6. 🔴 当前活跃缺陷（清点工具库时抓到的）

**跨设备通道 `node-bridge`（rust-bridge v1.4.0 在跑，pid 1012）每 5 秒重放全部历史键。**

| 指标 | 实测 |
|---|---|
| 每轮处理的键 | **1,513 个**（最早 `ts=2026-08-27`，黑板 `version=1` **从未变过**） |
| inbox 文件 churn | 3 秒内 **83% 换 inode** ⇒ **≈420 次原子写/秒** |
| 日志增速 | **824 KB/s ≈ 62–68 GB/天**（现 173 MB，最早一行仅 4 分钟前 ⇒ **靠截断维持**） |
| 现有缓解 | `com.dsh.cron.log-guard.plist` + `mbp-log-guard.sh`（**治症状**） |

**源码定位**（`rust-bridge/src/main.rs`）：
```
327|  log(&format!("MSG {} = {}", k, val));        // ← 无条件：62GB/天 来源
337|  if is_llm_msg && processed_path.exists() { continue; }  // ← 闸门只覆盖 llm 消息
345|  if std::fs::write(&tmp_path, val.to_string()).is_ok() {  // ← 无条件原子重写
346|      let _ = std::fs::rename(&tmp_path, &fpath); }        //   ≈420 写/秒
```
- **没有「仅变化时写」的开关**（参数只有 `--hb/--queue/--notes/--no-llm/--token/--identity`）
- `.processed`（8,609 文件）是 **llm_loop 的消费台账**，**不能**直接复用做变更判定
- **CHANGELOG 停在 v1.3.3，1.4.x 零条目**；源码 1.4.1 vs 在跑 1.4.0
- 源码第 334 行注释已预见该风险：「不再重写 inbox——否则 notes_loop 5s 写回 → llm_loop 再处理 → 无限重复」

---

## 7. 工具库全貌（两代并存）

| 层 | 内容 | 状态 |
|---|---|---|
| **插件（9 挂载）** | agent-way · central-inbox · bus-bridge · external-link-policy · guard · dock-cards · hr · market · openchronicle | Gen2 主力 |
| **Rust 底座（6 工具）** | rust-blackboard **v0.6.8（RSS 1.2 GB）** · node-bridge v1.4.0 · dsh-tools v1.12.0 · rust-genebank · blackboard-mcp v0.8.4 · rust-data-tools | Gen2 活跃；**dist 堆积 16 个 node-bridge 二进制** |
| **守护进程（14）** | 上述 6 + **7 个 `bb-sub` 订阅进程** + central-wake + mac-mini-inbox-watch + bb-absorb-watch + kb-genebank-watch | Gen2 活跃 |
| **脚本（237）** | bb 60 · gate 7 · cahac 6 · node 5 · kb 5 · blackboard 5 · stance/wargame/verify/task/route 各 2–4 | **202 被引用 · 35 孤儿** |
| **Gen1（已死）** | `bus-bridge.js` · `~/.dsh/bus-queue` · `~/.dsh/outbox` · `~/.dsh/exlink-blackboard` · `~/.dsh/capture` | 最后活动 **08-26 ~ 09-06**（≈25 天） |
| **状态目录** | `~/.dsh/inbox` **405MB / 1,945 直接文件（10,564 含子目录）** · `.processed` 8,609/34MB · `queue-drain-backups` 14MB | inbox 是唯一剧烈变动者 |

**命名碰撞**：`~/dsh-collab/inbox/`（用户拖文件的收件箱，有 README）与 `~/.dsh/inbox/`（消息落盘池）**同名不同物**。

---

## 8. 待决与建议顺序

| 优先级 | 事项 | 说明 |
|---|---|---|
| **P0** | **重启 CLD** | 让第 2 节全部生效。三插件预检已 GO，无阻塞项 |
| **P0** | **修 node-bridge 重放循环** | 建议**先本地对照**：加 `HashMap<key,(version,ts)>` 变更判定，让 `log` 与 `write` 同受约束；验收看 `/tmp/node-bridge-mac-mini.log` 增速归零 + inbox inode churn 归零。**注意它跑在三台设备上** |
| P1 | 建 I3/I4（**订阅事件 + 按 id 关联**，不自建队列） | 方向已由 F1–F4 确定；需与 `agent-way` 的 `followup({id: msg.id})` 对接 |
| P1 | I5 换用 `dsh-atomic-write` | 低危；采用后**取消**原「换 SQLite 载体」计划 |
| P2 | I7 通知类走 `inject`（不唤醒） | 直接消除 17.0% 的"通知强制开轮次" |
| P2 | R2 存量 1785 条标签式 `from` | 迁移，或下游一律按不可信处理 |
| P3 | 清淤：queued 2059（85% >7 天）· 黑板无 GC · 两注入器合并 · `dsh-doc` 静默未挂载 · 100 个惰性残骸 · 35 孤儿脚本 · Gen1 死目录 · 16 个二进制标基线 | 各自独立 |

### 已否决 / 已撤回（避免重复投入）

| 项 | 结论 |
|---|---|
| ~~I2 去重淘汰策略改成员集合~~ | **否决**。3209 组"窗口放行"里 **1273 组是 15 分钟周期巡检**（间隔中位数 0.35h）⇒ 改了会**静默杀掉该巡检**。窗口是**载重结构** |
| ~~路线图第 5 步换 SQLite 载体~~ | **可取消**（`dsh-atomic-write` 已覆盖） |
| ~~「宿主插件被热重载，改源码不必重启」~~ | **已证伪**。那 4 条「启动」日志是我自己跑预检时 `apply()` 的副作用（对照实验 224→225） |

---

## 9. 方法论教训（本次最有价值的副产物）

| 教训 | 实例 |
|---|---|
| **拿到了数字 ≠ 判定了缺陷** | I2 的 3208 组、I1 的 1785 条，两条判据都被证据推翻 |
| **检查器的判据错了，比被测对象错了更隐蔽** | 验证 A4d 时我的检查器只认完整 UUID，把合法短 id 判为无效 ⇒ 输出「救回 1/11」，真实 **9/11** |
| **探针不得污染被测对象** | 预检冒烟会写生产日志，一度把我误导成「热重载」⇒ 现已加字节断言 |
| **自己的产物不算证据** | `agent-way.json` 里的 `resolved` 是我自己 CLI 测试写的；4 条「启动」是我跑预检写的 |
| **验证动作本身可能加重被测缺陷** | A6 探针因旧码在线被真的投递，把 `from===to` 从 33 加到 **34** |
| **档案说了「做过三次」不代表做过** | 存量盘点标题即「这个题目我们已经做过三次」，而 A 级 PoC（订阅唤醒）至今未落地 |

---

*本文为交接视图，所有数字均可在本机复跑验证。★/★★ 标注见第 4 节，不得据 ★★ 项直接动手。*
