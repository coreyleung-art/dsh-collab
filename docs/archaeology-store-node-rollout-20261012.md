# 考古：「面向所有门店投放分布式智能体节点」构想（2026-10-12）

> **出件**：子代理 `809fd306-71f1-44bd-a599-10dc4a72c006`（受星桥第二任 `session-e317d6ab` 委托）
> **落盘**：2026-10-12T02:3x（+08:00）· 星桥第二任代落（原子代理受 CLD 自重启影响未完成落盘）
> **效力档位 L1（已记录）** · ★ **不宣布任何事项已闭合** · ★ 全程只读
> ★★ **本件最重要的结论**：★ **圈二不是空白，是【想了、验证了、然后被后续治理主线遗忘在另一个目录里】。**

---

## 〇、一条影响任何复跑者的坑

★ **本机 `rg`（ripgrep）未安装**（`which rg` 未找到）。
★★ 则该子代理第一轮用 `rg` 扫出的「全关键词 0 命中」**全部是 exit 127 的【假零】**，已作废。
★ 后续一律改用 Python `str.count` / `grep` 复核。
★★ **任何在本机用 `rg` 得出的「没找到」都不可信。**

> ★ 本线（星桥）自查：本线全程用 bash `grep` 与 python，★ **二者读数一致**，★ 本线工具链**不受此坑影响**。

---

## 一、扫过的面

| 面 | 方式 | 文件数 | 命中 |
|---|---|---|---|
| `dsh-collab/docs/` | Python os.walk | **631** | 门店节点=3 · store-reader=1 · 多租户=7 · 信任模型=2 · 不可控节点=1 · 远程吊销=1 · 门店隔离=5 |
| `dsh-collab/` 根级 md | 限 `dp==root` | **113** | 门店节点=1 · 多租户=1 · 租户边界=1 · **投放门店=1** |
| `data/industry/` | 同上 | **190** | ★ **分布式落店=39 · 门店采集机=23** · 多租户=2 |
| `research/cost-governance/` | 同上 | **74** | 门店节点=1 · 多租户=4 · 租户边界=2 · ★ **投放门店=2** · `data/<tenant>`=3 |
| `comm-server/` | 同上 | **33** | store-reader=1 · 门店瘦采集=1 |
| `scripts/` | 同上 | **451** | 门店节点=1 · 多租户=2 · 信任模型=1 |
| `rules-registry/` | 同上 | **69** | 门店节点=3 · 多租户=5 · 不可控节点=2 · 门店隔离=4 |
| `devices/` | 同上 | 338 | 门店 3/8 · 分布式 13/27 · 鉴权 25/40 · 模板 48/94 |
| `~/meituan-multi/` | 排 node_modules/dist/build | **607** | 门店+节点 **零共现** |
| `~/dsh-plugin-*`（31 目录） | 同上 | **607** | 门店 4/21 · 多租户 **0** |
| `~/.dsh/` | maxdepth=3 | **12002** | `agent-bus.json`: store-reader=20 · 门店=288 · 投放 13/53 |
| 锚点 `docs/distributed-agent-network-governance-plan-v6.1-20261011.md`（2873 行） | Python count | 1 | ★★ **门店=0 · 投放=0 · 多租户=0 · 租户=0 · 克隆=0**；规模化=1 · 节点=9 · 分布式=7 · 隔离=4 · 模板=7 |
| 黑板活体（本地板 + 中枢） | curl | — | 见 §三 |
| `~/.dsh/agent-bus.json`（17MB 消息总线） | Python 递归字符串扫描 | 1 | store-reader=20 · 门店=288 |

**共现精确扫描**：全机 **47,294 个文本文件**中，「门店系词 × 节点/智能体/部署系词」同现 **692 行 / 248 文件**（含噪音，已人工筛）。

### ★ 没扫的面（如实列出）
`guard/backups/`（38,000+ 文件）· `dsh-collab/backups/` · `archives/` · `audits/20261009/frozen-snapshot-v1/` · 中枢板 `audit-*.jsonl` ×11（**未拉取**）· `token-monitor/blackboard/snapshot.json` 29MB（仅关键词命中检索）· Obsidian vault / ChromaDB · `~/meituan-multi/node_modules`

---

## 二、命中清单（★ 四类归类：已实现 / 已讨论 / 仅设想 / 仅提问）

### A. 已实现（有代码/产物，可实跑或实读）

**A1 · `comm-server/comm_domains.py` — 门店域 + store-reader 动态写权（单店隔离）**
- `:36-37`｜`    # 门店域 (2026-09-07 Windows 试点): notes/store-<id>/ = 门店瘦采集数据域`
- `:39`｜`STORE_DOMAIN_PREFIX = "notes/store-"`
- `:61-63`｜`    # store-reader: 门店采集器 (Windows 试点) —— 只写本店 notes/store-<id>/ 数据域` / `    # 动态匹配: 写权 = 键前缀 notes/store/<own-store-id>/ (bb-gate can_write 校验)`
- `:192-198`｜`    # store-reader 动态规则: store-reader-<store-id> 只写本店 notes/store-<store-id>/` / `        return key.startswith(f"notes/store/{store_id}/") or key.startswith(f"notes/store-{store_id}/")`

**A2 · `scripts/blackboard-server-v0.6.py` — 黑板原生支持「门店类型节点」**
- `:6`｜`v0.5 → v0.6 变更（2026-08-23 · 协调者，用户指示：门店规模化前补齐归属机制）：`
- `:8`｜`  3. 【门店身份】PUT /nodes/<id> 支持 store 类型（store_id/code/location/type）+ GET /stores 列出`
- `:344`｜`                    {"method": "GET", "path": "/stores", "desc": "门店类型节点列表（v0.6）"},`

**A3 · `windows-trial/store-reader-agent.py` — 门店节点智能体（E2 注册 + 心跳 + 采集）**
- `:4-7`｜`> store-reader 方案 (星桥交付 2026-09-07) · Windows 试点 step2 (明鉴验收)` / `> 每店：E2 注册 data/discovery/agents/store-<id> + 30-60s 心跳 + 采集写 notes/store-<id>/` / `> 只写本店 store 域 (comm-domains store-reader 角色, lean4 无写门)`
- `:33`｜`    reg = {"device": f"store-{sid}", "schema": "v1", "status": "online",` ★ **每店一个独立节点身份**

**A4 · `windows-trial/step1-last-result.json`**｜`"node": "i9-sim"`，三店 `store 2 / 8 / 7`，`"mode": "B-slim-collect"`

**A5 · `scripts/tier-gate-test.py` — 多租户网关分级 PoC（★ 子代理实跑 9/9 PASS）**
```
PASS 门店A-跨店隔离 | store-token-A | waimai.review-stats | 403 tenant boundary: data/store-B/review not in data/store-A/
PASS 门店A-改价审批 | store-token-A | price.change | approval_required (L3 escalate)
PASS 订阅-访问门店 | sub-key-1 | report.read | 403 tenant boundary: data/store-A/ not in data/sub-1/
== 9/9 PASS ==
```

**A6 · `scripts/gateway-security-check.py`（★ 实跑 7/7 PASS）**：含 `PASS C3 跨租户 403` · `PASS A1 白名单快照（内部工具全禁）| 0 泄露`

**A7 · `scripts/node-executor.py`**｜`docs/node-executor-README.md:11`｜`· 未来门店节点（蓝图 3.0：每节点一个执行器，零 token 值守）；· 任意分布式节点（MBP/门店…）`

**A8 · 黑板实存键（本地板实测）**
- `notes/store-2/collect-1788770324840` · `notes/store-8/collect-1788770324908` · `notes/store-7/collect-1788770324951`
- `nodes/store-2/heartbeat` · `nodes/store-7/heartbeat` · `nodes/store-8/heartbeat`（ts=`2026-09-07T16:39`）
- `nodes/store-01` / `nodes/store-01/heartbeat`（ts=`2026-08-23T19:06`，★★ **`hostname=CoreydeMac-mini.local` · `os=Darwin`** ⇒ ★ **是 mac-mini 本机登记的占位，非真门店机**）

### B. 已讨论（文档 / 卡片 / 往来消息）

**B1 · `docs/windows-store-deployment-eval-v1.md`（2026-09-06/07 · 明鉴 v3）—— 圈二主评估件**
- `:1`｜`# 运营能力外放 Windows 门店电脑 · 架构评估 v1.0`
- `:16`｜`\| 关键风险 \| 门店电脑员工可碰=不可控节点 \| — \|` ★ **信任模型风险**
- `:20`｜`\| 维度 \| A. 整 MTM 本地(每店) \| B. 门店只采集(mac/i9 管理) \| C. 全集中 i9 算力中枢 \|`
- `:25`｜`\| 维护成本 \| ❌ 每店一台=多节点运维 \| ✅ 门店瘦客户端 \| ✅ 单点维护 \|`
- `:51`｜`2. **写权不落门店**: 门店采集器无动作能力(Lean4 门: 结构上不含写原语)——需动作时回中枢由运营执行`
- `:53`｜`4. **护栏跨设备**: R026/R027 只在集中层生效, 门店节点=只读传感器`
- `:91`｜`\u250c\u2500 门店 Windows(每店 = MCP 节点) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510`
- `:107`｜`1. **一套协议通吃**: 门店节点/i9/MBP/未来第三方 = 都经 E2 + MCP 接入, 不造门店私有栈`
- `:116`｜`3. 铺门店: 分发=comm-layer 同款(dsh-tools win 先例)` ★ **逐字含「铺门店」**

**B2 · `docs/store-access-form-spectrum-v1.md`（2026-09-07 · 明鉴 v3）—— 形态谱系 + 产品化**
- `:17`｜`**共同本质**: 门店 = MCP 运营网络的边缘节点(E2 注册 + comm-mcp 接入); 差异 = 接入端形态与交互面。`
- `:36`｜`\| 关键点 \| ①便携 Node+隐形 Chrome 负载 ②自举(引导启动, Windows autorun 被禁) ③凭据加密+远程吊销(E2) ④多钥备份 \|`
- `:44`｜`\| 硬件候选 \| A 轻量安卓盒(¥400-600, 量产稳) / B 树莓派触屏(¥600-1000, 可玩) / C 二手平板改造(¥200-400, 最快样机) \|`
- `:49`｜`\| 决策待办 \| 本地微模型兜底(断网可用) vs 纯云端瘦终端? 信任模型(服务商资产锁死 vs 商家开放)? 语音在门店环境可用性? \|`
- `:78`｜`- **flowernet 扩张面**: 门店节点(A/B/C) 都归 store 节点体系(Windows 部署评估)`

**B3 · 黑板卡片（★ 实读，非转述）**
- `data/registry/windows-deploy-consensus-20260906`（ts `2026-09-07T01:30:26`）｜`【三方共识汇总】Windows 门店外放讨论结论(HR/明鉴/星桥):` + `推荐形态: B 门店瘦采集 + 集中管理(三方一致)`
- `notes/mingjian-step2-accept-20260907`（ts `2026-09-07T16:40:49`）｜`MCP 接入形态(门店=E2 节点 + store-reader 角色)已在真实链路验证——Windows 门店 B 形态 + MCP 融合的『门店边缘节点』假设成立(采集/注册/心跳/回流/门控全通)`；`remaining`：`i9 承载补验(step1 遗留: 任务卡 shell 受限, 采集在 mac-mini 本地跑)——部署细节非架构假设`
- `notes/collab/store-reader-deliverable`｜`## 1. comm-domains store 域支持（已落地）`
- `data/device/windows-trial-step1-status`｜`"i9_exec":"受阻-任务卡shell拒绝访问…"`

**B4 · 往来消息（`~/.dsh/agent-bus.json`）**
- thread 1406[39]｜`星桥：Windows 试点已获用户批准启动 ✅ 请出 store-reader 角色(comm-domains)+E2 store 节点接入方案配合 step2。`
- thread 1613[6]｜`store-reader step2 验证通过：3 店 store-2/7/8 已 E2 注册（data/discovery/agents/store-<id>，status online，role store-reader-<id>）+ 心跳（nodes/store-<id>/heartbeat）+ 采集回流（notes/store-<id>/collect）……供明鉴 step2 验收：E2注册✅/G5心跳✅/数据回流✅/store域角色+lean4只读✅`
- thread 1613[8]｜`罗盘：Step2 验收通过 ✅ 四要素数据实锤(E2三店online/store-reader角色/G5心跳ok/回流在/lean4只读)。MCP 门店节点假设成立。`
- thread 1560[1]｜`看黑板 notes/session-fa1f9150/store-bus-device-view — 星桥总线/设备视角共评：门店直连中枢（零本地黑板依赖）+ E2 发现层 store-<id> 节点（R-ERR4 注册）+ notes/store-<id>/ 域权门（bb-gate 无写原语结构门）……试点 i9 模拟 2-3 店可零新基础设施。`
- thread 1557[2]｜`司库：评估升级 v1.1(MCP融合)已回帖，门店=边缘MCP节点。`

**B5 · `data/industry/FLOWERNET-BP-MASTER-v2.md`（2026-09-10）—— ★ 最完整的规模化投放方案**
- `:1202`｜`**做什么**：在**每家门店**部署一台标准化采集机（Windows 迷你主机／工控机），运行独立浏览器实例……**使用该门店的真实 IP 与运行环境**采集订单、IM、评价数据；同时做跨系统支持与环境隔离。`
- `:1204`｜`**为什么必须分布式落店，不能中央化**（全篇最重要的技术判断）：`
- `:1207`｜`**核心是"封装"**：把采集程序打包成**门店人员插上就能用的一键安装包**——自带依赖、开箱即跑、能自动更新、能远程运维`
- `:1209`｜`这正是"一次建造、多处部署"的杠杆：**建一次采集器，部署到 30 家店还是 300 家店，边际成本几乎不变**`
- `:1215`｜`**验收**：① 一键部署成功（**不需工程师到店**）；② 采集环境符合平台账号使用规则；③ **门店间环境隔离生效**；④ 订单 43 列／IM／评价稳定回流。`
- `:1263`｜`一台 24GB 内存的机器，跑 10 家门店的浏览器实例就已经很吃紧——反推**真实内存占用约 2GB/店**……24GB 约承载 10 家店、64GB 约 26 家店、128GB 约 51 家店。`
- `:1445`｜`**架构地基是"中央上云 + 采集落店 + 算力租赁"。**`
- `:1486`｜（★ 把「采集器封装、门店采集机(H1)」放在 **Q2（第 4-6 月）**）

**B6 · `research/cost-governance/flowernet-protocol-v1.0-2026-08-23.md` —— FNP 协议**
- `:12`｜`- **协议名**：FlowerNet（花网）· Distributed Agent Network Protocol`
- `:33`｜`\u2502 物理层：mac-mini 中枢 / i9 / MBP / 门店   \u2502`
- `:44`｜`- 门店（store）：蓝图 3.0 接入，\`type=store\` 注册于 \`nodes/<store-id>\`（v0.6 已支持）`
- `:67`｜`- 门店身份：\`nodes/<store-id>\` 带 store_id/code/location/type`

### C. 仅设想（设计/蓝图，无实现）

**C1 · `docs/flowernet-master-blueprint-20260827.md`**｜`:45`｜`\u2502     \u2514\u2500\u2500 子项 4.4 多租户隔离 + 安全（ZTNA/mTLS）\u23f3`；`:122-123`｜`\| 状态 \| deploy-check ✅ / adapt ✅ / 台账 ✅ / 多租户 \u23f3 \|`
**C2 · `docs/flowernet-master-blueprint-v3-20260827.md:191`**｜`\| **M4** \| 多租户（门店隔离 + 订阅逻辑）\| P0-1/P4-4 \| 门店 PoC（A 看不到 B）\|`
**C3 · `docs/flowernet-reliability-audit-20260827.md:78`**｜`\| 订阅平台 \| **未实现**（支付/计费/多租户）\| ❌ \|` ★ **阴性证据**
**C4 · `docs/hubbridge-protocol-research-20260827.md:139-152`**｜`### 多租户（门店/商家订阅）` / `tenant（门店/商家）→ 独立 namespace（genebank chromosome 前缀 + 身份隔离）` / `· 每个订阅商家：自己的设备白名单 + 资产空间 + 计量账户` / `1. **多租户隔离**：数据/身份/计量按 tenant 隔离` / `3. **安全**：TLS/mTLS + 设备认证 + 消息签名（防伪造）`

### D. 仅提问 / ★ 可疑声明

**D1 · `docs/store-access-form-spectrum-v1.md:49`**｜`\| 决策待办 \| 本地微模型兜底(断网可用) vs 纯云端瘦终端? 信任模型(服务商资产锁死 vs 商家开放)? 语音在门店环境可用性? \|` ★ **信任模型在此【仅列为待办问句】**

**D2 · `rules-registry/gate-flowernet-claim-report.md`（2026-09-07 · 明鉴）—— 自称三态核查，多处口径可疑**
- `:21`｜`\| P5-3 门店端到端(注册→隔离→数据→订阅) \| ✅ 四栈 MCP + 门店 MCP 节点规划 \|` ★★ **「✅」后接的却是「规划」，【自相矛盾】**
- `:22`｜`\| M4 多租户/门店隔离 \| ✅ mechanism schema + store 分区契约(server-governance L4) \|` ★★ 子代理按关键词搜 `server-governance` / `store 分区契约`：**仅出现在该报告与该报告的下游引用，未见实现文件** ⇒ ★★ **此 ✅ 不可采信**
- `:24`｜`\| 首个付费订阅门店接入 \| 📋 规划中(商业评估, 非门) \|`

---

## 三、有没有做过？（三态）

### ★ **部分成立** —— 「已实现」严格限定为**单机制品层**；「已部署到门店」**不成立**

**成立**：多租户/单店隔离网关分级 PoC 已实现（`tier-gate-test.py` 实跑 **9/9 PASS**；`gateway-security-check.py` 实跑 **7/7 PASS**，含 `C3 跨租户 403`）· 门店域权隔离**已进生产代码**（`comm_domains.py:192-198`）· 黑板**原生支持门店类型节点**（`blackboard-server-v0.6.py:8,344`）· 门店节点智能体脚本**已交付** · 通用节点执行器**已交付** · 试点产物**实存于黑板**。

**不成立（★ 关键反证，均为子代理本轮活体实测）**：
- ❌ **没有任何真实门店跑过节点**。活体 E2 注册表：本地板 `GET /data/discovery/agents/` ⇒ 仅 **`mac-mini`、`mbp`**；中枢板 ⇒ 仅 **`i9`、`mac-mini`、`mbp`**；`data/discovery/agents/store-{2,7,8}` **两块板均返回 404**。★ **这与 thread 1613 当年「三店已 E2 注册 ✅」的回报【冲突】。**
- ❌ **`nodes/store-01` 是伪门店节点**：值 `{"capabilities":["python3","shell","dsh"],"hostname":"CoreydeMac-mini.local","os":"Darwin",...}` ⇒ ★ **在 mac-mini 本机登记**。
- ❌ **试点明确是模拟**：`step1-last-result.json` 内 `"node": "i9-sim"`；`data/device/windows-trial-step1-status` 记 `i9_exec: 受阻`；验收卡自述遗留 `i9 承载补验(step1 遗留: 任务卡 shell 受限, 采集在 mac-mini 本地跑)`。
- ❌ **规模化投放未启动**：`FLOWERNET-BP-MASTER-v2.md:1486` 把「门店采集机(H1)」放在 **Q2（第 4-6 月）**；`:1424` 门店采集机仍为「约 0.8 万元/台」的**测算**。

---

## 四、有没有讨论过？（三态）

### ★ **成立，且相当充分**（2026-08-22 → 2026-09-10）

六步证据链：**08-22** 用户提出接入分级 → **08-23** 黑板 v0.6 落「门店身份」（变更理由逐字「**门店规模化前补齐归属机制**」）→ **08-27** FLOWERNET 蓝图 P0/P2/P4 + M4 → **09-06** 三方共识（HR/明鉴/星桥）→ **09-07** 用户批准试点 + step2 验收通过 → **09-10** BP MASTER v2「分布式落店」。

**限度**：讨论**集中在 09-10 之前**。`docs/` 中 **409 篇是 10 月的**，按 `ls -t docs/*.md | head -80` 逐篇检查「门店 且 节点/投放/分布式/规模化」——**零命中**。锚点 v6.1（2873 行）内 **门店=0 · 投放=0 · 多租户=0**。

---

## 五、有没有思路记录？（三态）

### ★ **成立**

成体系的思路记录：`windows-store-deployment-eval-v1.md`（三形态可行性矩阵）· `store-access-form-spectrum-v1.md`（A/B/C 形态谱系 + 双形态产品化 + 五条启停 gate）· `FLOWERNET-BP-MASTER-v2.md`（L1/L2/L5 分层 + 内存墙外推）。风险提示已有（`:16` 不可控节点 · `:25` 多节点运维 · `:62-66` 风险与门表）。待办已有（`:49` 决策待办 · `:61-72` 四条启用条件）。

★ **但用户本次原话「面向所有门店投放建立分布式智能体节点」在全机无逐字命中**：搜 `面向所有门店`=0 · `投放建立`=0 · `铺智能体`=0 · `分布式智能体节点`（仅命中 **MBP 端侧总线定名**与**内部设备协作文档标题**，与门店无关）⇒ ★ **该表述是用户的现场概括，此前未被逐字写下。**

---

## 六、★★ 两圈之分：有没有被显式区分过？

# ★ **成立 —— 被显式区分过，而且分得很清楚。**

★ **最重要的发现**：区分**不在 `docs/`**，而在 **`research/cost-governance/`**，时间 **2026-08-22**，署名 **HR**，标注 **「用户提出」**。

### 证据 1 · `research/cost-governance/access-tiering-role-model-v0.1.md`
- `:3`｜`> 设计：2026-08-22 · HR · 用户提出（接入时区分节点角色和权限：Tailscale=自有设备 / 公网=门店 / 付费订阅）· 衔接 node.bootstrap 自举 + 云 MCP 网关 + 多租户升级路径`
  ★★★ **原始表述是【三分】而非两分。**
- `:11-13`（**信任度明确分档**）：
```
| 接入层 | 来源 | 信任度 | 认证要求 |
| 内部 | Tailscale 网段（100.x） | 高（自有设备） | 内部 token（SSE_TOKEN）+ 网络白名单 |
| 公网-门店 | 云网关公网 → 门店身份 | 中（商户合同） | 门店凭据（企微身份/门店账号） |
| 公网-订阅 | 云网关公网 → 订阅用户 | 低（付费客户） | 订阅 API key（作用域） |
```
- `:19-21`（**数据边界按圈不同**）：内部设备=全网络（`nodes`/`data`/`registry` 全量）／门店=`本店 data/<门店>/*（隔离）`／订阅用户=`订阅租户 data/<subscriber>/*`（只读聚合）
- `:62`｜`2. v0.2 门店：云网关 + 门店认证 + 租户隔离（投放时）` ★ **逐字含「投放时」**

### 证据 2 · `research/cost-governance/cross-device-blackboard-design-v1.0.md:4`（★ **用户确认的决策原文**）
> `> **部署形态决策（2026-08-22 用户确认）**：现阶段=**Tailscale 内网共享账本 + 命名空间隔离**（nodes/<节点>/、data/<域>/，权限=信任内部）——完全够用，不引入多租户复杂度；**多租户升级路径（公网投放门店/员工时启用）**：① 命名空间加租户层 data/<门店>/* ② 云网关 ABAC 按角色（论文 2605.18414 已入库）③ 企微身份认证 ④ 员工操作 J45 自动升级审批 ⑤ 审计加租户维度`

### 证据 3 · `resource-registry.md:458`（同日登记 v1.0.322）
> `| 2026-08-22 | v1.0.322 | **黑板部署形态决策**（用户确认）：现阶段=Tailscale 内网**共享账本+命名空间隔离**（信任内部，不引入多租户复杂度）；**多租户升级路径已标注**（公网投放门店/员工时启用：租户命名空间 data/<门店>/* + 云网关 ABAC 按角色 + 企微认证 + J45 员工操作升级 + 租户审计）——cross-device-blackboard-design-v1.0.md 已更新 |`

### 证据 4 · `research/cost-governance/architecture-evolution-stages-v1.0.md`
- `:12`｜`| 3 | 接入分级 | 📐 设计完成 | access-tiering-role-model-v0.1（Tailscale=内部 / 公网=门店/订阅 · 角色权限/租户隔离/云网关） | 门店/订阅隔离 PoC（A 店看不到 B 店） | 公网入口关闭，回 2 |`
- `:29`｜`- **内部设备**（Tailscale）：全权限 · **门店**（公网）：本店隔离+受限 · **订阅**（公网）：只读聚合`
- `:31`｜`- 升级触发：投放门店/员工时启用（现不提前做）` ★★ **这就是「两圈不同逻辑」的最直接表述**

### 证据 5 · `research/cost-governance/external-access-tiering-design-v1.0.md:7-19`（「内外双通道架构」）
```
┌────────── 内部通道（Tailscale 安全网络）──────────┐
│ 自有设备（MBP/mac-mini/i9）→ 黑板自举(node.bootstrap) → 角色=internal → 全权限
┌────────── 外部通道（公网 → 云网关）───────────────┐
│ 门店/员工/订阅用户 → https://域名/mcp（云网关）    │
```

### ⇒ ★★ **从未「混为一谈」；恰恰相反，「两圈」被显式区分，且区分维度正是「信任模型 + 数据边界 + 认证方式 + 治理工具」**

### ★ 但存在一处**口径张力**（必须如实报出）
较晚（2026-09-06）的 `docs/windows-store-deployment-eval-v1.md` 在**协议层主张「同一套」**：
- `:82`｜`B 形态(门店瘦采集) 与四栈 MCP 不是两件事, 而是同一架构的两面:`
- `:107`｜`1. **一套协议通吃**: 门店节点/i9/MBP/未来第三方 = 都经 E2 + MCP 接入, 不造门店私有栈`

⇒ 即：**协议/接入层主张统一（「一套协议通吃」），权限/信任层保持分离（域权/只读门/租户边界）**。★ 这与 8-22 的分级模型**不冲突但措辞相左** —— 8-22 说「现在不引入多租户复杂度，投放门店时才启用」，9-06 说「不造门店私有栈」。★★ **该张力未见任何文档显式对账。**

---

## 七、★★ 信任模型：投放到自己控制之外的环境，有没有被讨论过？

### ★ **成立，且覆盖全部五个维度**

| 维度 | 状态 | 证据（逐字 + `文件:行号`） |
|---|---|---|
| **鉴权** | ✅ 已设计（3 档） | `access-tiering-role-model-v0.1.md:13,15,17`：内部=`内部 token（SSE_TOKEN）+ 网络白名单`／门店=`门店凭据（企微身份/门店账号）`／订阅=`订阅 API key（作用域）`；`:46`｜`\| 认证 \| 门店=企微身份/账号；订阅=作用域 API key \| 2605.30998（x402 作用域凭据） \|` |
| **隔离** | ✅ 已设计 + **PoC 实跑** | `external-access-tiering-design-v1.0.md:48`｜`\| 隔离 \| 租户命名空间 data/<tenant>/* + 权限过滤 \| 2508.03095（Agent Registry 方案权衡） \|`；`tier-gate-test.py` 实跑 `403 tenant boundary: data/store-B/review not in data/store-A/` |
| **多租户** | ✅ 已设计，**明确「现在不做」** | `cross-device-blackboard-design-v1.0.md:4`｜`完全够用，不引入多租户复杂度；**多租户升级路径（公网投放门店/员工时启用）**`；`architecture-evolution-stages-v1.0.md:31`｜`升级触发：投放门店/员工时启用（现不提前做）`；`hubbridge-protocol-research-20260827.md:141-142`｜`tenant（门店/商家）→ 独立 namespace`／`· 每个订阅商家：自己的设备白名单 + 资产空间 + 计量账户` |
| **「自己控制之外」** | ✅ 已被识别为风险 | `windows-store-deployment-eval-v1.md:16`｜`\| 关键风险 \| 门店电脑员工可碰=不可控节点 \| — \|`；`:51`｜`2. **写权不落门店**: 门店采集器无动作能力(Lean4 门: 结构上不含写原语)——需动作时回中枢由运营执行`；`:53`｜`门店节点=只读传感器`；`:62`｜`\| 门店员工破坏采集器 \| 只读无价值目标 + 凭据不落门店 \|` |
| **单店可吊销** | ⚠️ **仅设想，一笔带过** | 全机仅 `store-access-form-spectrum-v1.md:36`｜`③凭据加密+远程吊销(E2)` —— ★ **无实现、无规程、无测试** |
| **数据边界** | ✅ 已设计 + 有 schema | `external-access-tiering-design-v1.0.md:39`｜`"data_boundary": "data/<tenant>/*",`；`:47`｜`\| 跨店数据 \| ❌ 硬隔离 \| — \|` |
| **审批升级** | ✅ 已设计 + PoC 覆盖 | `:45-46`｜`\| 改价/上下架 \| ❌ 默认禁 \| **必须**店长/总部确认（J45 升级）\|`；实跑 `PASS 门店A-改价审批 \| approval_required (L3 escalate)` |

### ★ 两处**明确未决**
1. **信任模型本身被列为「决策待办」（仅提问）**：`store-access-form-spectrum-v1.md:49`｜`信任模型(服务商资产锁死 vs 商家开放)?` —— ★ **「盒子归谁、谁有权关掉」这个根本问题，到 2026-09-07 仍未裁决。**
2. **多租户当前实现状态为「未实现」**：`flowernet-reliability-audit-20260827.md:78`｜`\| 订阅平台 \| **未实现**（支付/计费/多租户）\| ❌ \|`

---

## 八、三态结论

### ✅ 成立
1. 该构想在 **2026-08-22 → 2026-09-10** 间**被反复讨论过**：至少 6 份主文档 + 1 份三方共识卡 + 1 份验收卡 + 7 条往来消息线程。**不是「一片空白」。**
2. **两圈之分被显式区分过**，且正是以「信任模型」为轴（`access-tiering-role-model-v0.1.md` 三档信任度表 + `architecture-evolution-stages-v1.0.md:29,31` + `resource-registry.md:458`）。**从未混为一谈。**
3. **单店隔离/多租户权限模型有可实跑的 PoC**：`tier-gate-test.py` **9/9 PASS** · `gateway-security-check.py` **7/7 PASS**。
4. **门店域权隔离已进生产代码**；**黑板原生支持门店类型节点**。
5. **门店节点智能体已交付且试点跑通（模拟）**。
6. **规模化投放的完整方案与预算已出**（39 处「分布式落店」· 23 处「门店采集机」）。

### ❌ 不成立
1. **没有做过「投放到真实门店」**：活体 E2 注册表两块板**均无任何 `store-*` 节点**。
2. **没有一台真实门店机器在跑节点**：`nodes/store-01` 的 `hostname`/`os` 证明是 mac-mini 本机占位；试点标识 `i9-sim`。
3. **多租户生产实现不存在**（`flowernet-reliability-audit-20260827.md:78` 亲标 ❌）；**「单店可吊销」无实现**。
4. **用户本次原话全机无逐字命中**；**10 月 409 篇文档无一重提**；锚点 v6.1 内 `门店=0 投放=0 多租户=0`。
5. **不能把 `gate-flowernet-claim-report.md` 的 ✅ 当实现证据** —— `P5-3 …✅ …规划` 自相矛盾；`M4 …✅ server-governance L4` 找不到实现文件。

### ❓ 不可判（★ 及缺什么证据）
1. **当年三店 E2 注册究竟是否真的成功过？** 证据冲突：thread 1613[6] + 验收卡说成功；**今日两板 404**。★ **缺**：本地板 `audit-*.jsonl` 中 2026-09-07 时段 `PUT data/discovery/agents/store-*` 审计行（**本次未拉取归档**）。
2. **`nodes/store-*` 心跳在而 E2 注册不在** —— 无法判断是「被后续 PUT 覆盖」「被清理」还是「当时只写了心跳路径」。★ **缺**：同上审计日志。
3. **「两圈不同逻辑」是否被用户当面确认过（还是仅由 HR 归纳）？** `access-tiering…:3` 写「用户提出」，`cross-device…:4` 写「用户确认」，★ 但 `:66` 又写「**待用户确认后**并入 node.bootstrap 设计」。★ **缺**：该次交互的原始会话记录 / 用户原话。
4. **`server-governance L4` 的「store 分区契约」究竟是哪份文件？** ★ 未定位。**缺**：`gate-flowernet-claim-report` 作者的引用出处。
5. `docs/` 于 **2026-09-09 才入版本控制**（`d7a6f29`）⇒ ★ 子代理**未**依赖 git 历史作「不存在」判据，全部结论基于**当前磁盘 + 活体黑板**。

---

## 九、复跑命令块

```bash
# ── 0. 先验证工具（\u2605 本机 rg 不存在，勿用）──
which rg || echo "rg 未安装 ⇒ 任何 rg 的 0 命中都是假零"
python3 -c "print(open('/Users/coreyleung/dsh-collab/docs/distributed-agent-network-governance-plan-v6.1-20261011.md',encoding='utf-8').read().count('\u95e8\u5e97'))"   # 期望 0

# ── 1. 两圈区分的五大证据 ──
sed -n '1,25p;41,65p' ~/dsh-collab/research/cost-governance/access-tiering-role-model-v0.1.md
sed -n '4p'           ~/dsh-collab/research/cost-governance/cross-device-blackboard-design-v1.0.md
sed -n '458p'         ~/dsh-collab/resource-registry.md
sed -n '12p;29p;31p'  ~/dsh-collab/research/cost-governance/architecture-evolution-stages-v1.0.md
sed -n '1,30p'        ~/dsh-collab/research/cost-governance/external-access-tiering-design-v1.0.md

# ── 2. 多租户/单店隔离 PoC 实跑（\u2605 唯一「已实现」硬证据）──
python3 ~/dsh-collab/scripts/tier-gate-test.py          # 期望 9/9 PASS
python3 ~/dsh-collab/scripts/gateway-security-check.py  # 期望 7/7 PASS

# ── 3. 门店节点代码与产物 ──
sed -n '33,64p;189,200p' ~/dsh-collab/comm-server/comm_domains.py
sed -n '6,9p;344p;351,353p' ~/dsh-collab/scripts/blackboard-server-v0.6.py
sed -n '1,40p' ~/dsh-collab/windows-trial/store-reader-agent.py
python3 -c "import json;d=json.load(open('/Users/coreyleung/dsh-collab/windows-trial/step1-last-result.json'));print('node=',d['node'],'stores=',[s['store'] for s in d['stores']])"   # 期望 node= i9-sim

# ── 4. \u2605 反证：活体注册表有没有门店节点（今天仍为否）──
curl -s http://127.0.0.1:8792/data/discovery/agents/   | python3 -c "import json,sys;print(list(json.load(sys.stdin)['list'].keys()))"   # 期望只有 mac-mini, mbp
curl -s http://106.53.214.108:8792/data/discovery/agents/ | python3 -c "import json,sys;print(list(json.load(sys.stdin)['list'].keys()))"   # 期望只有 i9, mac-mini, mbp
curl -s http://127.0.0.1:8792/data/discovery/agents/store-2   # 期望 404
curl -s http://127.0.0.1:8792/nodes/store-01 | python3 -c "import json,sys;print(json.load(sys.stdin)['value'])"   # \u2605 hostname 应为 CoreydeMac-mini.local（伪门店节点）

# ── 5. 试点残留键 ──
curl -s http://127.0.0.1:8792/notes/store-2/ | head -c 400
for k in nodes/store-2/heartbeat nodes/store-7/heartbeat nodes/store-8/heartbeat; do echo "--- $k"; curl -s "http://127.0.0.1:8792/$k"; echo; done

# ── 6. 规模化投放方案 ──
sed -n '1200,1216p;1261,1272p' ~/dsh-collab/data/industry/FLOWERNET-BP-MASTER-v2.md
sed -n '84,95p;121,123p' ~/dsh-collab/docs/flowernet-master-blueprint-20260827.md   # 多租户 \u23f3
sed -n '78p'             ~/dsh-collab/docs/flowernet-reliability-audit-20260827.md  # 多租户 ❌ 未实现

# ── 7. 讨论链（卡片 + 消息）──
curl -s http://127.0.0.1:8792/data/registry/windows-deploy-consensus-20260906
curl -s http://127.0.0.1:8792/notes/mingjian-step2-accept-20260907
python3 - <<'PY'
import json
d=json.load(open('/Users/coreyleung/.dsh/agent-bus.json',encoding='utf-8'))
def w(o):
    if isinstance(o,dict):
        for v in o.values(): yield from w(v)
    elif isinstance(o,list):
        for v in o: yield from w(v)
    elif isinstance(o,str): yield o
for s in w(d):
    if 'store-reader' in s: print(s[:200],"
")
PY

# ── 8. 时间衰减：10 月有没有重提 ──
grep -rln --include='*.md' -E "\u63a5\u5165\u5206\u7ea7|\u591a\u79df\u6237\u5347\u7ea7|\u6295\u653e\u95e8\u5e97" ~/dsh-collab/docs ~/dsh-collab/data   # 期望仅 docs/tier-gate-test-README.md
for f in $(ls -t ~/dsh-collab/docs/*.md | head -80); do grep -q \u95e8\u5e97 "$f" && grep -qE "\u8282\u70b9|\u6295\u653e|\u5206\u5e03\u5f0f|\u89c4\u6a21\u5316" "$f" && echo "$f"; done   # 期望无输出

# ── 9. 扫过的面（数字复现）──
find ~/dsh-collab/docs -type f | wc -l          # 632（.md 614）
find ~/dsh-collab/guard/backups -type f | wc -l # \u2605 38,000+，不要遍历
git -C ~/dsh-collab log --diff-filter=A --format='%ai %h %s' -- docs/ | tail -3   # docs 最早入仓 2026-09-09
```

---

## 附：一句话总结

**圈二不是空白，也远不是「只有零星痕迹」** —— 它有一套 **2026-08-22 起的分级信任设计**（还带**实跑通过的 PoC**）、一次**三方共识**、一次**模拟试点验收**、一份**带预算的规模化方案**；但它停在了「设计 + 模拟」这一层：**真实门店零部署**（活体 E2 注册表可证）· **多租户生产实现为 ❌** · **10 月之后（含 2873 行的治理锚点）再无一次重提**。

★★ **最值得注意的一点**：★ **用户说的「两圈不同的逻辑」是对的，而且本机早在 2026-08-22 就用「信任内部 vs 公网投放门店启用多租户」把它写清楚了** ——
★★★ **但那份写在 `research/cost-governance/` 里，而 10 月所有治理叙事都建在 `distributed-agent-network-governance-plan-v6.1`（门店=0 命中）之上。**
⇒ ★★★ **圈二不是没想过，是想了、验证了、然后被后续治理主线遗忘在另一个目录里。**

---

*本件为【证据 + 三态判定】，不是最终裁定。★ 不宣布任何事项已闭合。*

---

# 补遗 · 第二遍重跑（2026-10-12 03:0x）

> **出件**：同一子代理 `809fd306-71f1-44bd-a599-10dc4a72c006` 的**独立重跑**（★ 非复述）
> **落盘**：2026-10-12T03:0x · 星桥第二任代落
> ★★ **本补遗【不改上文】** —— ★ 上文是**第一遍的如实记录**，★ 本补遗**追加更正与新增**。
> ★★★ **本线已亲验本补遗的全部关键读数**（★ 见 §补四）。

## 补〇 · 两个坑（★ 影响任何复跑者）

**坑 1 · `rg` 不存在。** `which rg` exit=1 ⇒ ★ 任何用 `rg` 得出的「0 命中」都是 **exit 127 的假零**。本遍全程改用 Python `str.count` / `grep` 复核。

**坑 2 · ★★ 上一遍的报告【已落盘】，成为本遍的「既有资产」。** 实测：
```
-rw-r--r--  1 coreyleung  staff  33877 Oct 12 02:16 docs/archaeology-store-node-rollout-20261012.md   (359 行)
```
★ ⇒ **「重新来一遍」时，上一遍的结论本身已是一份本地文档，必须把它计入面** —— ★ 否则会把自己的旧输出当成「新发现」。

## 补一 · ★★★ 本遍最重要的新发现：真实门店服务器【确实存在】

**来源**：`data/blueprint/gallery/hardware-nodes.json`（mtime `2026-09-07 16:06`）

★ **本线亲验（★ 实测输出）**：
```
硬件表节点总数: 17
  hw:srv-tianhe        天河店服务器     Win10  向日葵1687489763  店铺服务器  在线
  hw:srv-foshan        佛山店服务器     Win10  向日葵1696416965  店铺服务器  离线
  hw:srv-jiangnanxi    江南西店服务器   Win10  向日葵1676234999  店铺服务器  离线
--- 带 E2 registry_ref 的 ---
  node-macmini   → E2:data/discovery/agents/mac-mini
  node-pci9      → E2:data/discovery/agents/i9
  node-mbp       → E2:data/discovery/agents/mbp
```

★★ ★ **硬件表 17 节点 = 5 device + 8 server + 3 cloud + 1 local**；★★ **只有 3 个带 `registry_ref`（E2），且全是自有设备**；★★★ **三台门店服务器一律无 `registry_ref`，全部走「向日葵远控」而非「Tailscale + 黑板」。**

★ ⇒ ★★ **门店服务器与智能体节点：同表不同组、同表不同通道。**
★★ **这是拓扑登记层的【隐式区分】，但未被任何文档显式命名为「两圈」。**

## 补二 · ★★ 本遍新扫的面（上一遍完全未扫）

| 新面 | 量 | 关键命中 |
|---|---|---|
| ★ `data/blueprint/` | **363 文件 / 21 蓝图** | 三台门店服务器 · `distributed-network` 蓝图 · `merchant-ops-ai` 蓝图 |
| ★ `data/local-registry-index.json` | **2301 条目** | 节点工具族 12 件 |
| ★ `scripts/` 节点工具族 | — | `node-onboard-gui.py`（412 行）· `node-join-notify.py` |
| ★ `research/` MCP 服务化线 | — | `three-end-automation-roadmap.md` · `procurement-mcp-service.md` |
| ★ ERP 物理库 | grep SQL | `tenant_id` 列**实测存在** |

### 补二·1 ★★ ★ 21 个蓝图，**没有任何一个同时覆盖两圈**
★ **圈一蓝图** `data/blueprint/distributed-network/blueprint-distributed-network-v1.0.md`（2026-09-09）—— ★★ **本线亲验：「门店」出现次数 = 0**
- `:12`｜`| name | 跨设备分布式智能体节点网络 |`
- `:22`｜`- **node-net**：节点网络 — **4 设备拓扑(mac-mini宿主/MBP/i9/iPhone)** + Tailscale + 设备资产表`
- `:32`｜`- dn1-1 4 设备组网 [done] — mac-mini/MBP/i9 Tailscale 100.x 全在线`
- `:43`｜`- dn3-3 接入模板标准化 [todo] — node 接入模板/任命提示词（新设备即插即用）`

★ **圈二产品蓝图** `data/blueprint/merchant-ops-ai/blueprint-merchant-ops-ai-v1.0.md`（2026-09-06）
- `:6`｜`> 核心商业依据(妙记1): 自研 AI 运营工具产品化——自动改价/上下架/竞品监控/库存联动; **人效 20→50 店/人; 千店边际递减**; 可泛化宠物/餐饮垂类`
- `:24`｜`- **merchant-ui**：商家界面线 — 单店看板…+ AI 建议确认流 + **SaaS 订阅形态**`
- `:31`｜`- mo-2 用户对象边界 [done] — **单商家/自有+代理门店(非代运营服务商, 服务商走 mtm ops)**`
- `:53-54`｜（考量登记）`**门店接入形态谱系**…A远程(软件·已共识)→B U盘钥(服务商随身)→C 带屏盒`／`启用 gate: ①软能力验证 ②商业模式确认 ③客户形态选型 ④硬件预算批准 —— 全满足才进硬件化`

### 补二·2 ★★★ 「自助接入」这一规模化必备件【只做在圈一】
`scripts/node-onboard-gui.py`（**412 行** · mtime `2026-10-12 00:21`）—— ★ **本线亲验（★ 实测行号）**：
```
:67   BB = "http://127.0.0.1:8792"  # 本机黑板（GUI 跑在 mac-mini）
:75   - 通过黑板任务卡协议与 mac-mini 中枢（100.120.203.20:8792）双向联通
:99   - 黑板地址：http://100.120.203.20:8792
:107  2. 确认本机到 mac-mini 黑板连通（curl http://100.120.203.20:8792/clock）
```
★ **判读**：该工具**硬编码圈一语义** —— Tailscale 内网 IP · 要求节点具备本地 `bash`/文件/CLD 能力 · **默认授予任务卡执行 + 写权**。
★★ **⇒ 它【不能被直接用于门店投放】**（门店不在 tailnet、不应有写权、无 CLD）。
★★★ **⇒ 「自助接入」这个规模化必备件，只做在圈一。**

### 补二·3 ★ ERP：租户列**物理存在，但无真实租户值** ⇒ 「有列无隔离」
`erp-workspace/chuheng_erp/flower-server-java-patch/items_backup_before_migration.sql` ⇒ 列含 `tenant_id`，★ **值全部为 `'tenant-default'`**。

### 补二·4 ★ 多租户设计其实很细（08-17，上一遍漏扫）
`research/procurement-mcp-service.md:52-53`｜`- 起步：每租户 API Key + tenant_id 注入` / `- 数据隔离：共享库 + tenant_id 行级（数据库 RLS 行级安全 + 中间件自动注入双保险）；敏感租户可库级隔离；审计日志记录 tenant/tool/参数/结果/时间。`
`research/three-end-automation-roadmap.md:71-74,89`｜`门店侧：三端能力封装为 MCP 工具集` → `多租户：API Key/OAuth + **RLS 行级隔离** + 配额 + 超量计费 + 限流审计` → `开放：**面向外部花店提供订阅式 MCP 服务**`

## 补三 · ★★ 两圈之分：补一层「拓扑层」（上一遍只找到文档层）

★ 上文 §六 已给**文档层**（08-22 三档信任模型 + 用户确认）的完整证据 —— ★ **本补遗不重复**。
★ **本遍新增【拓扑层】**：`hardware-nodes.json` 把 17 节点分为 `device / server / cloud / local` 四组；
★ **门店服务器在 `server` 组、走向日葵远控、无 E2 ref**；★ **三台自有设备在 `device` 组、走 Tailscale、有 E2 ref**。
★★ **⇒ 分组与通道本身即区分，但未被文档命名。**

## 补四 · ★★★ 上文的一处【更正】（★ 本遍自报）

★ 上文 §三 写「**没有一台真实门店机器在跑节点**」——
★★ **措辞需更正为**：★ **有三台真实门店服务器存在并已登记**（天河**在线** / 佛山离线 / 江南西离线，均 Win10，向日葵远控），
★★★ **但它们【不是智能体节点】**（无 E2 `registry_ref`、无 tailnet、无节点协议）。

★ ⇒ **结论方向不变**（★ 仍无「投放」），★★ **但事实基础更正。**

## 补五 · 本线亲验记录（★ 本条补遗的关键读数由本线独立复跑，非采信）

| # | 子代理声称 | 本线复跑 | 判定 |
|---|---|---|---|
| 1 | 硬件表 17 节点 · 3 台门店服务器 · 仅 3 个带 E2 ref | ★ **逐字一致** | ✅ 成立 |
| 2 | 圈一蓝图 `distributed-network` 通篇零「门店」 | ★ `str.count('门店')` = **0** | ✅ 成立 |
| 3 | `node-onboard-gui.py` 硬编码 Tailscale 内网 IP | ★ `:75`/`:99`/`:107` 均为 `100.120.203.20:8792` | ✅ 成立 |

## 补六 · 复跑（本补遗新增部分）

```bash
# 三台门店服务器 + E2 ref 有无
python3 - <<'PY'
import json
h=json.load(open('/Users/coreyleung/dsh-collab/data/blueprint/gallery/hardware-nodes.json',encoding='utf-8'))
for n in h['nodes']:
    if '店' in (n.get('name') or ''): print(n['id'], n['name'], n['os'], n['ip'], n['role'], n['status'])
print('带 E2 ref:', [(n['id'],n.get('registry_ref')) for n in h['nodes'] if n.get('registry_ref')])
PY

# 圈一蓝图零门店
python3 -c "print(open('/Users/coreyleung/dsh-collab/data/blueprint/distributed-network/blueprint-distributed-network-v1.0.md',encoding='utf-8').read().count('门店'))"   # 期望 0

# 自助接入工具硬编码 Tailscale
sed -n '67p;75p;99p;107p' /Users/coreyleung/dsh-collab/scripts/node-onboard-gui.py

# 21 个蓝图
python3 -c "import json;d=json.load(open('/Users/coreyleung/dsh-collab/data/blueprint/gallery/static-export/api/blueprints.json',encoding='utf-8'));print(len(d))"

# ERP tenant_id 有列无隔离
grep -o "'tenant-default'" /Users/coreyleung/dsh-collab/erp-workspace/chuheng_erp/flower-server-java-patch/items_backup_before_migration.sql | sort -u
```

## 补七 · ★ 结论更新（★ 方向不变，事实基础更硬）

★★ **圈二不是空白，也远不是零星痕迹。** 它有：
★ 三档信任模型设计（08-22，**用户确认**）· ★ **实跑通过的租户隔离 PoC**（9/9、7/7）· ★ 三方共识 + 模拟试点验收 · ★ 带预算的「分布式落店」方案 · ★ **独立产品蓝图 `merchant-ops-ai`（千店/SaaS）** · ★★ **以及三台【已经真实存在并登记】的门店服务器**。

★★ **它卡住的地方非常具体**：
★★★ **真实门店服务器【在表里，但不在节点网络里】** —— 无 E2 注册、无 tailnet、无节点协议；
★ 唯一那件「规模化投放必备的接入自助工具」（`node-onboard-gui.py`）**硬编码了圈一语义**（Tailscale 内网 + CLD + 写权），**门店用不了**；
★ 而圈一的蓝图 `distributed-network` v1.1 **通篇零「门店」**。

⇒ ★ **「两圈不同的逻辑」用户说对了**，而且本机 **08-22 就用「信任内部 vs 公网投放门店启用多租户」把它写清楚并取得确认**。
★★★ **但那份写在 `research/cost-governance/`，而 10 月所有治理叙事都建在 `distributed-agent-network-governance-plan-v6.1`（门店=0 命中）之上。**
⇒ ★★★ **圈二不是没想过 —— 是想了、验证了、连门店机器都登记了，然后被后续治理主线遗忘在另一个目录里。**

---

*★ 本补遗为【证据 + 三态判定】，不是最终裁定。★ 不宣布任何事项已闭合。*
