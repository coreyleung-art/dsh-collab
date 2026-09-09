# 插件安装评估建议报告（供应链专员 0e84e65c）

- 响应：b241741f 评估任务包（① 安装评估建议 ② gov/gate 深审 ③ open-design 移植评估）
- 时间：2026-08-18 · 方法：GitHub 仓库核查 + 本地 clone 深审 + 与现有系统对比

---

## 一、安装评估建议（候选 10 项）

| 候选 | 供应链 | 与现有系统对比 | 建议 |
|------|--------|---------------|------|
| **dsh-gov**（安全治理） | 🟢 深审通过 | 无重叠，补安全缺口（策略门控） | ✅ **优先试点**（P1，契合权限体系） |
| **dsh-plugin-gate**（安装安全） | 🟢 深审通过 | 无重叠，供应链安全（安装扫描） | ✅ 试点（与供应链职责协同） |
| chicheng-cron（定时） | 🟢 | ⚠️ 与 task-board/launchd 重叠 | 🔶 滚动评估：增量成立仅当「服务端常驻 + 不依赖 GUI 打开 + 掉线补跑」三点确认（bbcba7ef 对照表判定标准） |
| dsh-agent-conductor | 🟢 | bus 已有跨 agent，CLI 互补待定 | 🔶 确认目标 CLI 就绪后评估 |
| dsh-messaging（27 网关） | 🟡 凭据面大 | ⚠️ 与外链三通道重叠 | ❌ 先做重复性评估（调研优先） |
| DSH-Office | 🟡 构建审查 | 文档域增量（编辑/预览） | 🔶 补齐构建审查后评估 |
| dsh-approval-gate | 待查 | 与审批卡片规范契合 | 🔶 调研中，走审批卡评估 |
| dsh-read-url | 🟢 4787d717 预评估通过（零依赖/无高危/全 charset/反爬） | 与 research-fetch 互补（6000 字符紧凑读 vs raw 全量存） | ✅ **推荐装（P0）**（调研管线价值最高，QA 三编码冒烟计划已备） |
| dsh-web-search-pro | 🟡 4787d717 预评估：P1 接入（有用非首期）| 与现有 web_search 多引擎互补 | 🔶 滚动档定级 P1 试点（read-url P0 优先）；依赖 jsdom@30 + Playwright browser-service 试点观察内存；v0.1.2 早期版本；Exa/Jina 可选 key（无 key 可不配） |
| dsh-auto-compact | 待查（倾向跳过） | CLD-017 相关 | ❌ **不装**（9828aa93 对比：官方 compaction 已装 v0.1.0-rc.6，阈值 0.8×ctx≈800k 从未触发=根因；优先官方 compaction-basic 调低 thresholdRatio——同缝/可控/无新依赖） |

## 二、dsh-gov + dsh-plugin-gate 深审结果（本地 clone 实测）

### dsh-gov（863683348/dsh-gov）🟢 通过
- 结构：lib 4 模块（index 308 行 / audit 70 / policy 67 / quota 48）+ test 3 个（audit/policy/quota）
- 依赖：**零 dependencies**（纯 JS）
- scripts：仅 test（node --test）
- 高危扫描：无 child_process/exec/eval/curl/rm -rf/环境变量读取（demo.mjs 中 rm -rf 仅为示例字符串）
- 挂载：cordis.patch.yml 标准 insert（gov 插件，root=dshHomePath('gov')，sectionOrder 5）
- 注意：quota 模块 defaultLimit 0——试点配置需按实际需求调整，避免误限

### dsh-plugin-gate（863683348/dsh-plugin-gate）🟢 通过
- 结构：lib 6 模块（index/scan/rules/targz/osv）+ test 3 个（rules/osv/scan）+ SECURITY.md
- 依赖：**零 dependencies**
- scripts：test + prepublishOnly（均为 node --test，无 install 高危）
- **性质**：它是「扫描工具」——rules.js 是检测高危模式的规则库（exec/spawn/shell:true/eval/new Function 等模式），scan.js 编排扫描，osv.js 调 OSV API 只读查询漏洞库，targz.js 纯 JS 解压（无子进程）
- 高危扫描：自身代码无执行高危操作的逻辑（扫描目标而非执行）
- 挂载：cordis.patch.yml 标准 insert
- 价值：与供应链职责天然协同（插件安装安全门）

### 深审结论
**两者均可安全试点**——零依赖、无高危操作、标准挂载、测试齐全。gov 管运行时策略，gate 管安装前安全——组合后形成「安装门 + 运行门」双层治理，与本系统权限体系高度契合。

## 三、open-design 移植评估（nexu-io/open-design，88.2K⭐）

### 关键结论：**无需移植——已原生支持 DeepSeek Harness** 🎉

- 仓库：nexu-io/open-design（TypeScript，88,244⭐，活跃）
- README 明确：**「DeepSeek Harness is now supported」**——官方 dsh 原生运行时（structured streaming/model discovery/cancellation/session resume）
- 接入方式：`od agent setup deepseek-harness`（官方 dsh CLI 安装连接组件）；或 MCP 集成（`od mcp install`）
- 依赖面：dependencies 0（脚本含 postinstall/bootstrap——需安装时审查 postinstall 内容，但无 npm 运行时依赖）
- 与现有能力：生成 web/desktop/mobile 原型、live dashboard、deck、图片、视频 + HyperFrames——与 1e54d56d OpenPencil/ui-spec 能力互补（OpenPencil=编辑画布，open-design=agent-native 设计工作流）
- 建议：不移植，直接**对接评估**（装 dsh CLI 连接组件试点）——前提：用户确认 + postinstall 脚本审查 + 内存评估（桌面应用，内存 25% 偏紧需窗口）

---

## 四、汇总建议（供用户拍板）

1. **试点 dsh-gov + dsh-plugin-gate**（安全治理双件，深审通过，P1）
2. **open-design 不移植**——改为直接对接试点（若用户需要设计工作流）
3. cron/conductor/Office 等滚动评估；messaging 先查重复性
4. 安装窗口：内存缓解或重启窗口（协调者已排期）
