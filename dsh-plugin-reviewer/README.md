# dsh 插件审查器 v1.1.0

> R006 v2 十项 + 合规/安全/质量/CLD适配/模型兼容/多实例/反注入/反远控 + Agent 运行时护栏(K)
> 作者：4787d717 · 2026-09-07 · 需求：用户（拉到本地审查 dsh 社区插件 / 映射 awesome-agent-failures taxonomy）

## 审查维度（9 组 66 项）

| 组 | 维度 | 规则数 | 说明 |
|---|---|---|---|
| A | R006 十项 | 10 | dsh形态/TCC/CLD自适应/版本/文档/版本管理/日志/落链/CLI/Lean4门 |
| B | 合规 | 6 | 逆向端点/凭据采集/遥测/许可/ToS灰区/敏感路径 |
| C | 安全 | 7 | eval/下载执行/供应链/混淆/写面/外连/漏洞 |
| D | 代码质量 | 5 | 测试/结构/错误处理/活跃度/类型 |
| E | CLD 适配 | 5 | 版本匹配/client注入/host依赖/资源/重启 |
| F | 生态冲突 | 3 | 已装等效/工具撞车/seam抢占 |
| G | 模型兼容 | 5 | 默认模型/外部API/key处理/本地模型/路由侵入 |
| H | 多实例安全 | 5 | 自启端口/绑定地址/单实例/端口冲突/共享状态写 |
| I | 反注入盗取 | 6 | 敏感读/内部数据/会话外传/静默beacon/自动执行/聚合外传 |
| J | 反远控C2 | 7 | 反向shell/远程代码/隐藏通道/持久化/混淆通讯/可疑主机/命令面 |
| K | Agent 运行时护栏 | 7 | 映射 awesome-agent-failures taxonomy 7 类失败（见 [taxonomy-mapping.md](taxonomy-mapping.md)） |

## 用法

```bash
# 审查单个插件目录
python3 reviewer.py <插件目录>

# JSON 输出
python3 reviewer.py <目录> --json

# 批量扫描（本地拉取的一批插件）
python3 reviewer.py --scan <仓库目录>

# 列出规则
python3 reviewer.py --rules

# 快速版本兼容检查
python3 reviewer.py --check-version dsh-context@0.41.3
```

## 判定

- **direction=negative 规则命中 = 发现风险**（安全组）；positive 命中 = 达标（工程组）
- critical 命中 = 一票否决 → ⛔ 拒装
- ≥80% 无红 → ✅ 装-安全；50-79% → ⚠️ 谨慎；<50% 或红 → ⛔ 拒装

## 自研信任机制

本机自研插件（~/dsh-plugin-* 或 coreyleung-art 仓库）自动识别为可信：
- 跳过安全维度(B/C/H/I/J 共 31 项)——我们自己写的代码不需当陌生人审
- 保留工程/质量/适配检查(A/D/E/F/G)**以及 K 组运行时护栏**——自己的 Agent 同样可能跑偏，K 是自研重点自检维度
- 判定直接显示 ✅ 自研可信（分数仅为质量健康度参考）
- E1 版本匹配降级（自研随 CLD 发布，无第三方版本墙）

第三方插件仍全维度 66 项安全审查。

## Agent 运行时护栏（K 组）

K 组把 [awesome-agent-failures taxonomy](../ai-agent-governance-negative-cases/ai-agent-governance-negative-cases-2026.md) 的 7 类运行时失败映射为「插件代码中护栏构件的存在性」检查（direction=positive）：
Tool Hallucination(K1) / Response Hallucination(K2) / Goal Misinterpretation(K3) / Plan Generation + Incorrect Tool Use(K4) / Destructive Confirm(K5) / Verification-Termination(K6) / Prompt Injection Guard(K7)。

- 缺失 = warn（治理缺口），不设 veto（运行时行为静态难确诊）
- 完整映射见 [taxonomy-mapping.md](taxonomy-mapping.md)
- 单文件规则源：rules/plugin-review-rules.json（K1-K7）

## 下一迭代需求（已立项 · L 组）

**「消费第三方 skill / MCP 供应链审查」**（源自负面案例 C5 供应链信任链崩塌 + 本机 MCP-station 已装 9 个 qcc server）：

- 背景: Claude Code CVE-2025-59536（仓库 config 自动批准 MCP）、Cline 被注入偷 token、MCP STDIO by-design RCE 等证明「插件自身干净 ≠ 它消费的 skill/MCP 干净」。
- 目标: reviewer 审查插件时，**递归审查其声明的外部 skill / MCP server**（package.json/_source/mcp 配置里引用的 registry 与 endpoint），形成 L 组供应链规则。
- 拟新增检查（设计稿）:
  - L1 skill/mcp 依赖清单声明（能枚举出消费的外部源）
  - L2 外部源 URL 与 registry 信任域（官方/自研 vs 未知域名，比对 J6/B1 名单）
  - L3 配置继承自动授权（类比 CVE-2025-59536：settings/mcp.json 是否有隐式 enableAll）
  - L4 远端 skill 供应链指纹（依赖锁/签名/发布门禁，类比 npm audit）
  - L5 消费端注入面：Agent 是否会把第三方 skill 输出当指令（衔接 K7）
- 触发: 用户核准后开迭代（需设计 L 组 rule type：可能需新增 `mcp_scan` / `registry_resolve` 检测器与远端解析逻辑，engine 改动较大）
- 关联资源: MCP-station servers.json（9 qcc server, 0600）、dsh-plugin-reviewer 规则库

## 实测验证（2026-09-06 / 09-07）

| 对象 | 结果 | 说明 |
|---|---|---|
| dshmarket v1.44.0 | ✅ 装-安全 80% | 与人工评估一致（2依赖/59测试/官方市场） |
| 恶意样本（反向shell+beacon） | ⛔ 拒装 46% + 4否决 | J1/I4/J6/E1 命中 |
| dsh-plugin-guard（自研） | ✅ 自研可信 | 跳过安全审查，仅质量检查 |
| dshmarket（第三方） | ✅ 装-安全 | 全维度 66 项 |

## 局限

- 静态扫描：无法识别运行时行为（需 J37 沙箱补充）
- 高权限合法工具（系统/安全类）会触发警示 → 需「用途声明」白名单机制（v2）
- 混淆代码需深度审（正则难穿透）→ 建议配合 dsh-sentinel-scanner 交叉
