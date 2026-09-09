# dsh-collab —— 跨会话协作共享工作区（约定 v1，2026-08-16 由 session-b241741f 发起）

## 约定
1. 跨会话协作的**成果物/交付物**统一落盘本目录（或本目录声明的子目录），并在广播中声明路径。
2. 涉及 Obsidian vault 的报告类成果仍走 `wiki/research/`（如 cross-session-intel-r1.md）。
3. 同源文件操作遵循红绿灯协议（agent_light → agent_lock → agent_unlock）。
4. **热点同源资源锁惯例**（增补 v1.1，2026-08-16）：`~/.dsh/profiles/web`（多会话并发改冲突实测）、`/Applications/CLD.app`（重签/补丁等触碰运行中 GUI 的操作）属热点资源——改动前必须 agent_light + agent_lock（建议命名 `file:~/.dsh/profiles/web`、`agent:CLD.app`），改完立即 agent_unlock。

## 现有成果索引（供各会话取用）· 格式：`路径 — 说明（owner 会话 · 更新）`
- 运维工具集：`~/dsh-plugin-research/sysops/`（CLI + MCP + skill + 自动化）（b241741f · 0816）
- 情报协作记录：`Obsidian/wiki/research/cross-session-intel-r1.md`（Round1 情报/需求/实施全量，28 增补）（b241741f · 0816）
- Dify 知识库运维：`~/dsh-plugin-research/docs/dify-knowledge-config-runbook.md`（b241741f · 0816）
- LM Studio 修复：`~/dsh-plugin-research/docs/lmstudio-repair.sh` + `lmstudio-full-fix.sh`（b241741f · 0816）
- 检索升级实证：`Obsidian/wiki/research/retrieval-upgrade-r1.md`
- 插件安装记录 R1：`~/dsh-collab/plugin-install-r1.md`（5 个社区插件装到 web profile，含验证结果与重启待办；由插件运维会话产出）
- 插件变更告警模板：`~/dsh-collab/plugin-alert-template.md`（用例 #2 企微外发，首投 success:true 已验证）
- GUI 插件交付物（session-1e54d56d）：`~/dsh-collab/gui-plugins-deliverables.md`（MCP 工作站 + 工作流捕获器 + MCP 生态 + 插件管线经验）
- repo-pipeline 双仓/CI 交付物：`~/dsh-collab/repo-pipeline-deliverable.md`（插件+CLI 用法、4 条网络/密钥踩坑、双仓源码地址）
- DSH 远程访问排障 R1：`~/dsh-collab/dsh-remote-access-fix-r1.md`（CLD /api 围栏机制、tailnet 代理 Host/Origin 改写修复、全链路验证；由 session-43b1a2d3 产出）
- 外卖客户消息数据契约（de7b29de⇄aa528267 双保险模式）：`~/dsh-collab/waimai-customer-msg-data-contract.md`
- 文件/文档管理增强（session-3b5efeef）：`~/dsh-collab/file-doc-management-enhancement.md`（dsh-files+knowledge+doc 安装/验证、嗅探 8192B 补丁、CLD 崩溃调查、重启待办清单）
- 会话持久化根因研究（session-b278baab）：`~/dsh-collab/dsh-session-loss-root-cause.md`（双 dsh 服务器并发写同一会话根 → 重复 seq/截断/丢失；CLD 退出 SIGKILL 丢尾部；workspace.json last-write-wins；根治方案 P0-P5）
- dsh 平台交付物（本会话）：`~/dsh-collab/dsh-platform-deliverables.md`（dsh 知识库 dsh-docs 2963 块 + 调研流水线 dsh-research + 远程访问拓扑 com.dsh.remote/com.dsh.health + 集合命名三分约定）
- DSH 宠物插件定制与禁用实录：`~/dsh-collab/dsh-pet-plugin-notes.md`（客户端代码实时读盘+no-cache、启动清单 rev 实时 sha1、settings.yaml chokidar 热加载免重启、隐藏≠禁用、贴图 8×9 契约、文案替换清单、备份 ~/.dsh/pet-backup/；由 GUI 宠物会话产出）
- 外卖学习系统交付物（session-a3bc8cba）：`~/dsh-collab/waimai-learning-system-deliverables.md`（comm.db 独立学习库 86客户/117会话/685消息、知识库同步管道、客户沟通范本聚类；与 de7b29de 实时采集互补）+ `Obsidian/wiki/research/waimai-learning-system-deliverables.md`
- Agent Bus 跨会话协作名册（总线侧）：`~/dsh-collab/agent-bus-roster.md`（15 会话能力登记、外卖域锁命名、红绿灯协议、环境情报速查、总线待办）
- 数据资源归属声明 v1.0（外卖数据层，a3bc8cba⇄de7b29de 三方确认，总线协调方落盘）：`~/dsh-collab/data-ownership.md`（comm.db 学习端专属写 / events·im_sessions 采集端专属写 / kb_docs 学习端可写 / stores 双方只读 / 跨域写走红绿灯）
- 美团商家 IM 工作台操作手册（de7b29de 实测）：`~/dsh-collab/waimai-im-workbench-manual.md`（DOM 结构/选择器/采坑实录/消息清洗规范，供灌 Dify KB）
- GUI 插件结构说明（session-1e54d56d）：`~/dsh-collab/gui-plugins-structure.md`（mcp-station/workflow-capture 架构、API、数据流、关键经验，供知识库灌入）
- 插件冒烟测试工具链（需求 #5，来源 e032fb77）：`~/dsh-collab/plugin-smoke/`（plugin-smoke.sh + plugins.example.json + README.md；构建产物+patch+host 日志四段探测，per-plugin 配置位，无 HTTP 端口插件适用）（b241741f · 0816）
- **跨会话协作 Playbook v1**：`Obsidian/wiki/dsh/cross-session-playbook.md`（红绿灯协议/热点资源锁清单/数据契约/分工模式/成果落盘/维护窗口协调/CLD 重签预案 v3/总线缺陷 v11 闭环）（b241741f · 0816）
- **ChromaDB 集合 + vault 命名约定 v1**：`~/dsh-collab/chroma-naming-convention.md`（集合三分表 + 前缀隔离 + 重建前哨兵 + SQLite 直查；来源 582093dd 碰撞事件，需求 #16）（b241741f+582093dd · 0816）
- 语音输入与会议模式（session-3221f810）：`~/dsh-collab/voice-input-assistant.md`（dsh-plugin-voice 静态插件 + CLDVoiceIME 系统助手 + 会议记录 + 语音收件箱；功能清单与关键经验）（3221f810 · 0816）
- CLD 服务器模式修复（session-3d490920）：`~/dsh-collab/cld-server-mode-fix-20260816.md`（--profile required 根因：--trusted-host 破坏 commander 解析；修复 diff + app.asar 备份 + 运维注意：签名告警无害/沙箱 lsof 技巧/asar padding 陷阱）（3d490920 · 0816）
- repo-pipeline KB 全文（工具清单/使用手册/踩坑/插件开发工作流，供 Dify+ChromaDB 摄入）：`~/dsh-collab/repo-pipeline-kb-full.md`
- 知识入库待处理箱（b241741f · 0816）：`~/dsh-collab/kb-inbox/`（repo-pipeline-plugin-dev-batch1.md + github-network-key-traps-batch2.md；均已灌 Dify ab4931ee + 索引 research 集合 9792 块，QA 三查询全命中）
- 外卖运营交付物（aa528267）：`~/dsh-collab/waimai-ops-deliverables.md`（16 工具/13 原语/数据契约/锁协议/可复用情报/项目文档索引）（aa528267 · 0816）
- CLD 闪退全局排障与重启治理 SOP（b241741f · 0816）：`~/dsh-collab/cld-crash-triage-sop-20260816.md`（23:48 事件三问自检 + package.json 拼写证据链 + 重启治理 SOP + 候选诱因）
- 外卖面板重启完整命令（aa528267 · 0816）：`MTM_DATA_DIR="$HOME/Library/Application Support/外卖门店多平台管理"` + nohup node server.js（否则加载 3 店旧库）；验证 8787/api/state stores:10 + issues 无 window_down（等 tickAll ~10s 勿早判）；动态插件 wmmon-2 需 kind:new 重建（kind:existing 报错）+ 用户批准激活。详见 cld-crash-triage-sop-20260816.md 重启检查清单
- **新会话记忆继承引导（总线侧 · 0817）**：`~/dsh-collab/new-session-onboarding.md`（新会话 6 步接驳：确认身份→拉总线线程→读协作索引→定位角色→登记档案→报到；梁神模式特别说明；记忆继承速查表）
- **资源管理者任命 Prompt（总线侧 · 0817）**：`~/dsh-collab/resource-manager-appointment.md`（standard 模式任命全文：资源登记/统筹规划/冲突仲裁/能力匹配 + 工作协议 + 角色边界）
- 会话存储健康检查脚本（session-b278baab）：`~/dsh-collab/scripts/session-storage-check.js`（回归基线用例源：撕裂帧/解析错误/重复seq/缺口检测，自动加载解码器，退出码 0/1 供 CI）
- mac mini 运维交付物（6e49710e · 0816）：`~/Desktop/DSH-health-check.sh`（一键体检 24 项）+ `~/Desktop/DSH-macmini-防崩溃运维手册.md` + `~/.claude/automation/dsh-health.py`（每小时体检，探针已修）
- session.list 性能缺陷源码级定位（session-43b1a2d3 · 0817）：`~/dsh-collab/session-list-perf-localization-r1.md`（wire 路径全量 blank 探测 = 40s 主成本、投影缓存仅 3 条目、5 条根治方向；P1 backlog 依据）
- **插件开发链路 + dsh-ssh 配置源情报（e0c391f7 · 0817）**：`~/dsh-collab/plugin-dev-pipeline-and-ssh-config-intel.md`（插件改码→重建→GUI 验证链路实测参数：构建产物格式/HMR 约束/冒烟探测口径；dsh-ssh 配置源单一来源方案 A/B 评估输入）
- **用户洞察交付物（session-2fe61625 · 0817）**：`~/dsh-collab/user-profile.md`（用户档案 v1：五大版图/商业模式/画像/交互规则/待确认项）+ `~/dsh-collab/business-map-v1.md`（生意版图全景 v1：10 店矩阵/8787 接入/健康度快照）+ `~/dsh-collab/cost-reduction-roadmap-v1.md`（降本增效路线图 v1：P0-P2 九项 ROI 排序）+ `~/dsh-collab/snapshots/`（每日生意快照，0817 起）
- **收入增长方案 v1（session-2fe61625 · 0817）**：`~/dsh-collab/revenue-growth-plan-v1.md`（市场机会扫描 5 信号 + 五条增长线：节日日历化/定价三层/私域复购/渠道补全/AI变现 + 分阶段 P0-P2）
- **商业模式画布 v1（session-2fe61625 · 0817）**：`~/dsh-collab/business-model-canvas-v1.md`（初蘅主画布 9 模块 + 五大版图要点 + SWOT + 6 项增长假设验证机制 H1-H6）——首期 5 任务全部完成 ✅
- **节日日历化运营 v1（session-2fe61625 · 0817）**：`~/dsh-collab/festival-calendar-v1.md`（2026-08→2027-02 九节日档期 + 四段式运营模板 + 档级资源分配；七夕 8/19 确认 2 天后、春节 2027/2/6）
- **每周洞察周报模板 v1（session-2fe61625 · 0817）**：`~/dsh-collab/weekly-report-template-v1.md`（生意健康+洞察+降本/增长双线+下周行动；首期 8/23 发出）
- **供应链成本监控 v1（session-2fe61625+0e84e65c · 0817）**：`~/dsh-collab/supply-chain/cost-monitor-v1.md`（花材三源价格体系：斗南⭐⭐⭐/云花苑⭐⭐⭐/TWFood⭐⭐ + 换算系数 + T-14 每日拉取计划；依据 supply-chain/flower-price-comparability.md 可比性评估）
- **AI 赚钱情报库（session-2fe61625 · 0817）**：`~/dsh-collab/ai-money/`（foreign-ai-money-modes-r1.md：国外 AI 赚钱模式 16 检索/12 模式/28 来源 + README 收录结构；Top5 落地方向已并入增长方案 v1.2 线 E）
- **flower-intel 平台摘要（5a5368af 代读 + 2fe61625 登记 · 0817）**：`~/dsh-collab/devices/flower-intel-index-summary.md`（PC-i9 已有「初蘅智能运营&竞品情报」平台全貌：A 竞品采集+Milvus 对标 / B 智能运营 Dify 5 Agent+企微审批；210 定价引擎含节日系数×1.80；510 供应商协议；410 节日模板——dogfooding 演进底座）
- **flower-intel 知识库快照（5a5368af + 2fe61625 · 0817）**：`~/dsh-collab/devices/flower-intel-knowledge-snapshot.md`（PC-i9 flower-intel 31 文件清单 + 核心摘要：6 层架构/120 安全边界/130 Agent 清单/210 定价规则/610 审批流/620 告警 SLA；dogfooding 演进底座）
- 上游讨论补充草稿（session-b278baab）：`~/dsh-collab/upstream-discussion-supplement-draft.md`（向 deepseek-harness #1586/#1497/#483 补充根因证据 + P1-P2 修复方案的 DRAFT，待 master 验证与用户确认后发布）
- 跨进程租约原型验证（session-b278baab）：`~/dsh-collab/prototype-verification-cross-process-lease.md`（副本环境实测：基线复现 dups=5 → 租约拒绝/陈旧接管/revision 校验全部 dups=0，验证通过）
- 上游发布最终文本（session-b278baab）：`~/dsh-collab/upstream-post-final.md`（GitHub 讨论 #1586 就绪文本：界定/实证/P1-P3 方案/原型验证/论文参考；待有发布通道的会话或用户执行发帖）