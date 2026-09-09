# DSH Harness rc.8 调研与整合方案（2026-08-20）

> 产出：session-6ed4daf2（恢复评估/技术调研）· 用户委派「harness 更新研究 + 社区挖掘 + 沉淀 + CLD 更新方案」
> 依据：调研优先制度（先查现成）+ J44 复用优先

## 一、版本现状（本机实测）
- CLD.app：0.1.0（Electron 壳，无内置自动更新器——find 无 updater）
- cld-dsh-runtime：0.1.0（内置 /Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/）
- @deepseek-ai/dsh：**0.1.0-rc.6**（落后 2 个版本）

## 二、rc.8 更新全貌（2026-08-19 发布，14 项，首个 post-beta 大更新）
### 新功能
1. **多模态原生支持**：DeepSeek 适配器可配置原生图片请求；/goal /plan 命令接收图文输入；@ 菜单引用文件和会话
2. **子代理升级**：Claude Code 与 Codex 子代理可作 Profile Bundle 按需安装；Codex 支持非交互权限模式 + 多个命名实例
3. **Windows PTY**：持久 PowerShell 会话，极简模式预设默认支持

### 修复
- 图片过大/历史图片累计载荷致模型请求失败
- 取消流式后已展示前缀未带入后续提问/分叉会话
- 自定义 OpenAI 兼容网关请求格式差异、推理内容回传缺失

### 体验优化
- 布局：HOME 目录 ~ 缩写、窄屏输入框、反馈 UI
- 操作：侧栏搜索焦点、工作流面板、模型选择器、打开本地文件失败重试
- 工具：**web_search 支持并发查询**；**子代理 reportDelivery 及时反馈并唤醒父任务**
- 安装：依赖体积改善、本地 dsh web 自动开浏览器
- 性能：大历史会话分叉优化

### 其他
- **SQLite 后端读写/分叉性能提升 + 存储体积降低，数据结构不兼容**（⚠️ 升级注意）
- 品牌规范：DeepSeek Harness 注册商标
- Python SDK：依赖配置覆盖 4 内置 Agent 预设 + rg/glob + MCP stdio

## 三、社区挖掘
### 新仓库 Ephemeral-AI-Lab/dsh-plugins（小而精）
| 包 | 版本 | 价值 |
|----|------|------|
| dsh-codex-shell | 0.1.2 | Codex 兼容 exec_command/write_stdin 持久会话 |
| dsh-loop | 0.1.3 | 会话级循环闹钟/loop 工具/slash 命令/web UI |
| dsh-mock | 0.1.0 unstable | **确定性 mock 模型回合 + 回放**（QA 测试价值高） |
| dsh-sessions | 0.1.1 | 检查/创建/读/消息 DSH 会话工具（与 agent_wake 互补） |

### 10 个高星实用插件（社区快照 2026-08-17）
- deepseek-harness-desktop 10.3k（桌面壳）/ modlens 2.6k（**已装本机**）/ dsh-web-ui 3.7k（UI 全家桶，部分重叠）/ open-design 87.8k（设计工作台，内存评估暂缓）/ OpenViking 28.7k（上下文数据库 RAG）/ archify 13.6k（架构图）/ voyager 19.5k（提示词管理）/ yao 7.6k（Agent 工作台）/ ouroboros 5.5k（访谈评测迭代闭环）/ EchoBird 3.1k（一键安装+模型配置）

### 已有资产（J44 复用，不重复调研）
- awesome-dsh-plugin 深度分析：~/dsh-collab/plugin-scan/awesome-dsh-analysis.md（1247 插件/52 高相关/Top 10，b241741f 产出）
- 插件评估模板/候选清单：plugin-scan/candidates-*.json

## 四、整合运用方案（与现有网络对接）
| rc.8 能力 | 整合点 | 优先级 |
|-----------|--------|--------|
| 多模态原生图片请求 | 减少对 modlens 依赖（modlens 兜底）；/goal /plan 图文 = 恢复自查可附图 | P1 |
| web_search 并发 | 数据调查员 4787d717 调研效率翻倍 | P1 |
| 子代理 reportDelivery 唤醒父任务 | 与 agent_wake/总线呼应，减少轮询成本 | P2 |
| Codex/Claude Code 子代理 Profile Bundle | 挂 Codex 做代码审查/修复执行（弥补「修复执行员」空白） | P2 |
| SQLite 后端 | 会话存储性能↑体积↓（⚠️ 数据不兼容，升级需迁移评估） | P2 |
| dsh-sessions | 与 agent_wake 互补：会话工具化 | P3 |
| dsh-mock | QA 确定性回归（mock 回合回放） | P3 |
| voyager 提示词管理 | 客服/运营提示词沉淀 | P3 |
| ouroboros 迭代闭环 | 与迭代报告/验收闭环思路一致（观察） | P3 |

## 五、CLD 更新方案与风险
### 路径
1. **等官方桌面壳更新**（最稳）：CLD.app 若发布新版随带 rc.8 → 替换安装，风险最低
2. **隔离副本验证**（推荐先做，J37）：/tmp/dsh-test-home 装 @deepseek-ai/dsh@rc.8 → dump-config + 插件冒烟（27 bundles）→ 验证通过再决策
3. **手动替换 runtime**（高风险）：替换 dsh-runtime/runtime/node_modules/@deepseek-ai/dsh → 需重签 CLD.app（A3/A4 先例）+ 签名告警 + SQLite 兼容验证

### 风险
- **SQLite 数据结构不兼容**：若升级后默认 SQLite 后端，本地 jsonl zstd 会话需迁移评估（dsh-session-loss-root-cause 经验）
- **CLD.app 签名**：改 runtime 需 codesign 重签（已有 A3/A4 流程与备份先例 app.asar.bak-20260816）
- **27 bundles 兼容**：rc.8 下需 J37 工具级验证全量复测（gov/agent-bus/waimai 等）
- 社区插件：不直接装生产（J37：隔离验证 → 供应链评估 → QA → HR 登记）

## 六、建议路线
1. 立即：隔离副本验证 rc.8（dump-config + 27 bundles 冒烟）——零风险获取兼容性数据
2. 通过后：等官方桌面壳更新或协调重签窗口替换 runtime（A4 预案复用）
3. 整合 P1：rc.8 生效后 web_search 并发（数据调查员）+ 多模态（恢复自查附图）
4. 观察 P2/P3：Codex 子代理（修复执行员角色）、dsh-mock（QA 回归）、SQLite（迁移评估）

## 七、工具化落地（2026-08-21 更新）
- 工具：~/dsh-harness-updater/（check.sh 版本双通道 / community.sh 社区搜查 / daily.sh 每日合并+UPDATE-FLAG）——实测 rc.6→rc.7/rc.8 可更新、rc.8@08-19、awesome 10603⭐@08-20
- 插件：~/dsh-plugin-harness-updater/（harness_update_check / harness_community_scan / harness_update_flag，J11 验证通过）
- 调度：com.dsh.harness-updater.plist（每日 09:00）——沙箱 launchctl 受限，激活需用户终端一行（launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.dsh.harness-updater.plist）
- 隔离验证：/tmp/dsh-test-home 安装 rc.8 进行中；清单 rc8-isolate-verify.md（J37：27 bundles 模块兼容 + 工具级抽查 + SQLite 影响评估）
