# dsh 插件审查器 · 设计与标准（v1.1 草案）

> 设计：数据调查员 4787d717 · 2026-09-06 · 需求：用户「10 项标准建审查器 + 合规/安全/代码质量/CLD 适配 + 模型兼容 + 多实例安全 + 防反注入盗取 + 防非友方远控」
> 关联：R006 v2（十项标准）/ J37（隔离验证）/ R027（审批）/ 守链 0e84e65c（供应链）/ 验金石 ffb7c3ab（QA 验收）
> 参考：dshmarket validate-registry（E1-E12 目录门）+ dsh-sentinel-scanner（安全 X 光）+ dsh-market probe-tmp

---

## 一、审查器定位

**一句话**：把 dsh 社区插件「拉到本地后」自动审查是否可安全安装——按 R006 十项标准 + 合规/安全/代码质量/CLD 适配度多维打分，输出「装/谨慎/拒装」建议。

**输入**：本地已 clone 的插件目录（或 npm 包 / GitHub repo）
**输出**：结构化审查报告（JSON + Markdown）+ 通过/警告/拒绝 三态判定

## 二、审查维度（8 组 36 项）

### 维度 A：R006 十项标准符合度（工程治理）

| # | 标准 | 审查点 | 检测方式 |
|---|---|---|---|
| A1 | dsh 插件形态 | package.json 有 `dsh.bundle.patch` 或 cordis.patch.yml | 静态查 package.json |
| A2 | TCC 检测 | 类型/契约检查可用（tsc/类型声明） | 查 tsconfig + .d.ts |
| A3 | CLD 自适应 | 是否适配 CLD 桌面壳（vs 纯 dsh web） | 查 client 注入 / webServer 路由 |
| A4 | dsh 版本自适应 | peerDeps/engines 声明版本范围，非钉死 | npm view peerDependencies |
| A5 | 文档化 | README/用法/配置说明齐全 | 文件存在性 |
| A6 | 版本管理 | 有版本号 + changelog + git tag | package.json.version |
| A7 | 统一日志 | 有日志输出规范（非裸 console） | 代码扫 logger |
| A8 | 自动落链 | 有结果落盘/登记机制 | 代码扫 registry/write |
| A9 | CLI 治理 | 有 CLI 入口或命令治理 | bin/scripts 检查 |
| A10 | Lean4 约束门 | 涉及"不该发生路径"时有不可绕过约束 + --lean4-check | 代码扫 约束门 |

### 维度 B：合规标准（法律/ToS/数据）

| # | 审查点 | 检测 | 风险级 |
|---|---|---|---|
| B1 | 逆向/非官方端点 | 代码 URL 含 backend-api/grok/oauth 逆向 | 🔴 拒装 |
| B2 | 凭据采集 | 读 keychain/~/.claude/.credentials | 🔴 拒装或警告 |
| B3 | 数据外传（telemetry）| 代码含 beacon/analytics/telemetry 域名 | 🟡 警告 |
| B4 | 开源许可 | LICENSE 存在且非 GPL 传染（可选） | 🟢/🟡 |
| B5 | 订阅 ToS 灰区 | 用订阅账户自动化调 API | 🔴 拒装 |
| B6 | 敏感路径访问 | 读 ~/.ssh/~/.dsh 全域 | 🟡 警告 |

### 维度 C：安全审查（静态 X 光）

| # | 审查点 | 检测 | 风险级 |
|---|---|---|---|
| C1 | 代码执行面 | eval/Function/new Function/child_process | 🟡 需审 |
| C2 | 下载执行 | 安装脚本 curl|sh / 远程代码拉取 | 🔴 拒装 |
| C3 | 依赖供应链 | 依赖数/锁文件/来源（github vs npm） | 🟡 记录 |
| C4 | 混淆/压缩 JS | 代码 minified/混淆（难审） | 🔴 警告 |
| C5 | 文件写入面 | 写 ~/.dsh / 系统目录 | 🟡 需审 |
| C6 | 网络外连面 | 外连域名清单 | 🟡 记录 |
| C7 | 已知漏洞 | 依赖版本 vs advisory | 🟡 npm audit |

### 维度 D：代码质量

| # | 审查点 | 检测 |
|---|---|---|
| D1 | 测试覆盖 | tests/ 存在 + 数量 |
| D2 | 结构清晰 | src/lib 分离，非单文件巨型 |
| D3 | 错误处理 | try/catch + 失败路径 |
| D4 | 维护活跃度 | 最近 commit / open issues |
| D5 | 类型语言 | TS（好）vs JS（需评） |

### 维度 E：CLD 适配度审查

| # | 审查点 | 检测 | 意义 |
|---|---|---|---|
| E1 | 运行时版本匹配 | peerDeps vs 本机 0.1.1-rc.2 | 版本墙检测 |
| E2 | 客户端注入面 | client 注入需的 dsh-client-* 服务在否 | seam 兼容 |
| E3 | host 服务依赖 | 依赖 webServer/shell/tools 服务在否 | 挂载即崩风险 |
| E4 | 资源占用 | 重依赖（puppeteer/libsql）vs 轻量 | 磁盘/内存评估 |
| E5 | 重启策略 | 装后需重启 or 热装 | 部署窗口 |

### 维度 F：与本地生态冲突

| # | 审查点 | 检测 |
|---|---|---|
| F1 | 已装等效 | 与本机 30+ 插件功能重叠 |
| F2 | 工具名冲突 | 注册工具名撞车 |
| F3 | seam 抢占 | 多个插件抢同一 seam（searchProvider 等） |


### 维度 G：模型兼容性（新增 · 用户补充）

| # | 审查点 | 检测 | 风险级 |
|---|---|---|---|
| G1 | 默认/依赖模型 | 代码硬编码模型名（gpt-4o/claude/gemini/deepseek-chat 等） | 🟡 记录 |
| G2 | 外部 API 依赖 | 需 OpenAI/Anthropic/Google/自定义 provider key 才可用 | 🟡 记录（有无 key 兜底） |
| G3 | key 获取方式 | 环境变量/settings 交互（✅）vs 硬编码/明文文件/URL 参数传 key（🔴） | 🔴 硬编码 key 拒装 |
| G4 | 本地 vs 云 | 能否用本地 Ollama/LM Studio（本机有）替代外部 API | 🟢 加分 |
| G5 | 模型路由侵入 | 是否替换模型选择器/seam（如 vision-toolkit 变体路由）——影响面 | 🟡 警告 |

### 维度 H：多实例安全（新增 · 用户补充）

| # | 审查点 | 检测 | 风险级 |
|---|---|---|---|
| H1 | 自启服务/端口 | 插件是否起 server/监听端口（net.listen/express/http.createServer） | 🟡 记录端口 |
| H2 | 绑定地址 | 绑定 0.0.0.0（外网可达 🔴）vs 127.0.0.1（✅）vs tailnet IP | 🔴 0.0.0.0 无鉴权拒装 |
| H3 | 双实例互斥 | 是否有锁/单例机制（防双 dsh 实例并发写会话——历史事故） | 🟡 警告无锁 |
| H4 | 端口冲突 | 声明端口 vs 本机已用（8787/8792/8803/8915/9200-9209） | 🟡 记录 |
| H5 | 共享状态写 | 是否写 ~/.dsh/storages 或 sessions（多进程写风险） | 🔴 无原子写拒装 |

### 维度 I：反注入盗取（新增 · 用户补充：插件反向偷信息）

| # | 审查点 | 检测 | 风险级 |
|---|---|---|---|
| I1 | 敏感文件读取 | 读 ~/.ssh / ~/.aws / credentials / .env / keychain | 🔴 一票拒装（除非声明且白名单） |
| I2 | 内部数据访问 | 读 agent-bus.json / sessions / app.db / comm.db / 凭据库 | 🔴 拒装或需审 |
| I3 | 会话/对话外传 | 把会话内容/tool 结果发外网（非白名单域名） | 🔴 拒装 |
| I4 | 后台静默外连 | setInterval/setTimeout 周期外连（beacon 心跳特征） | 🔴 拒装 |
| I5 | 安装后自动执行 | postinstall/prepare 脚本里做网络请求/读文件 | 🟡 需审（postinstall 禁网络） |
| I6 | 数据聚合外传 | 把多处本地数据聚合后单点外传（隐蔽泄露） | 🔴 需深度审 |

### 维度 J：防非友方远控（新增 · 用户补充：C2/反向 shell）

| # | 审查点 | 检测 | 风险级 |
|---|---|---|---|
| J1 | 反向 shell | child_process spawn 连接外部 IP/域名（shell 到非常规主机） | 🔴 一票拒装 |
| J2 | 动态代码拉取执行 | 运行时 fetch 远程代码 → eval/require/new Function | 🔴 一票拒装 |
| J3 | 隐藏命令通道 | WebSocket/自定义协议监听（非 UI 用途）+ 远程指令解码执行 | 🔴 拒装 |
| J4 | 持久化注入 | 写 launchd/注册表/开机自启/改 ~/.zshrc | 🔴 拒装 |
| J5 | 加密混淆通讯 | base64 多层解码执行 / 隐藏域名 / 动态拼接 URL（规避静态审） | 🔴 警告深度审 |
| J6 | 可疑外连 IP | 连非常规端口 IP（非 80/443 云厂商） | 🔴 拒装 |
| J7 | 命令执行面声明 | 需 child_process 的：审查是否白名单命令 | 🟡 需审 |

## 三、评分与判定

```
每项：通过(+1) / 警告(0) / 违规(-2) / 不适用(N/A)
安全项(B/C 红色) + 反注入(I1/I2/I3/I4/I6 红) + 反远控(J1/J2/J3/J4/J6 红) + 多实例(H2/H5 红) = 一票否决 → 拒装
总分 → 三态：
  ≥80% 且无红色 → ✅ 装-安全
  50-79% 或仅黄 → ⚠️ 谨慎（人工复核）
  <50% 或任一红色 → ⛔ 拒装
```

## 四、输出格式

```json
{
  "plugin": "dshmarket",
  "version": "1.44.0",
  "reviewed_at": "2026-09-06",
  "score": {"total": 92, "grade": "A"},
  "verdict": "✅ 装-安全",
  "dimensions": {
    "A_r006": {"score": 95, "items": [{"id": "A1", "pass": true}, ...]},
    "B_compliance": {"score": 100, "red_flags": []},
    "C_security": {"score": 90, "flags": ["child_process 使用需审"]},
    "D_quality": {"score": 85},
    "E_cld_fit": {"score": 92, "version_ok": true},
    "F_conflict": {"score": 80, "note": "与本地 dsh-plugin-market 功能重叠"}
  },
  "report_md": "path/to/report.md"
}
```

## 五、实现方案

- **形态**：Python 审查器（~/.dsh 生态已有 python 工具链惯例），后续可 Rust 化（R006 第 9 项 CLI 治理）
- **位置**：`~/dsh-collab/dsh-plugin-reviewer/`
- **命令**：
  ```
  python3 reviewer.py <插件目录或npm包> [--json] [--report-dir DIR]
  python3 reviewer.py --scan <仓库目录>    # 批量扫本地拉取的插件
  python3 reviewer.py --rules               # 列出审查规则
  python3 reviewer.py --check-version <pkg> # 快速版本兼容检查
  ```
- **规则库**：`rules/` 目录 JSON 规则（可扩展），非硬编码

## 六、交付物

1. 本设计文档（评审后定稿）
2. 规则库 rules/*.json（36 项规则定义，8 维度）
3. reviewer.py 主程序
4. 实测报告（对已拉取的 dshmarket 等候选验证）
5. 使用说明 + 回报 HR（合规）& 星桥（执行）

---
*设计草案 · 4787d717 · 待评审（用户 + HR 合规 + 守链供应链 + 验金石 QA）*
