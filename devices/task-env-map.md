# 任务-环境映射表 v1.2 · Task-Environment Map

> 维护：session-5a5368af（设备协调智能体）· 2026-08-17 · v1.2（过时修正：待确认项核实 + P3 分布式 MCP 能力登记）
> 用途：识别任务类型 → 路由到最合适设备/环境；Windows 专属任务 → PC-i9，macOS 专属 → mac-mini/MacBook Pro
> 决策权在用户：本表给出建议，实际分派由用户拍板

---

## 一、路由决策规则（v1.2）

1. **Windows 专属**（.NET/Windows 软件/兼容性测试/Windows 工具链）→ **PC-i9**（唯一 Windows 环境）
2. **macOS 专属**（Xcode/Swift/iCloud/Keychain/AX 自动化）→ **mac-mini**（宿主，DSH 工具面最全）
3. **重算力**：
   - **GPU 渲染/训练/推理**（CUDA 生态、SD/视频渲染、大模型训练）→ **PC-i9（RTX 4060 Ti 8GB）首选**——全网络唯一 CUDA GPU
   - CPU 密集批处理 → PC-i9（i9-14900KF 24 核）或按负载路由
   - 本地 LLM 推理（LM Studio）→ mac-mini
4. **移动端采集/随手记录** → iPhone 17（拍照/剪藏/语音），数据归集回 mac-mini
5. **通用**（文档处理/爬虫/批处理）→ 默认 mac-mini，负载高时溢出到 MacBook Pro

## 二、任务-环境映射表

| # | 任务类型 | 推荐环境 | 首选设备 | 备选 | 说明 |
|---|---|---|---|---|---|
| 1 | .NET / C# 开发构建 | Windows | PC-i9 | — | 唯一 .NET 原生环境 |
| 2 | Windows 软件操作/测试 | Windows | PC-i9 | — | 兼容性/功能测试必需 |
| 3 | Windows 工具链（Powershell/注册表/MSI） | Windows | PC-i9 | — | — |
| 4 | **大模型微调/训练**（>10GB） | **GPU** | **PC-i9（4060 Ti）** | mac-mini | 需用户确认预算；CUDA 唯一 |
| 5 | **CUDA 推理/Stable Diffusion/视频渲染** | **GPU** | **PC-i9（4060 Ti）** | — | ✅ 显卡实测确认（v1.1） |
| 6 | 本地 LLM 推理（LM Studio 模型） | macOS | mac-mini | MacBook Pro | 本机已部署 LM Studio 模型服务 |
| 7 | 批量 OCR（olmocr/tesseract） | macOS | mac-mini | — | 工具链在本机（~/dsh-toolchain/ocr） |
| 8 | 视频转码/编码（无 CUDA 需求） | 重算力 | PC-i9 | MacBook Pro | i9 多核；GPU 加速需确认工具链 |
| 9 | 大批量爬虫 | 通用+重算力 | mac-mini | PC-i9 / MacBook Pro | 爬虫工具链在本机（crawler-lab），量大可分流 |
| 10 | 文档批量摄取（PDF/DOCX/OCR） | macOS | mac-mini | — | DSH 文档工具面在本机 |
| 11 | Xcode / Swift / iOS 开发 | macOS | mac-mini | MacBook Pro | macOS 专属 |
| 12 | 桌面自动化（AX 权限） | macOS | mac-mini | — | 需辅助功能权限，本机已配 |
| 13 | Tailscale/远程访问运维 | 任意 | mac-mini | — | 宿主控制面 |
| 14 | 移动端采集（拍照/剪藏/语音） | iOS | iPhone 17 | — | 数据归集回 mac-mini |
| 15 | 双仓 CI/CD（GitHub/Gitee） | 任意 | mac-mini | — | repo-pipeline 在本机 |
| 16 | 通用批处理/脚本 | 通用 | mac-mini | MacBook Pro | 负载高时溢出 |
| 17 | 企业微信/IM 运营 | macOS | mac-mini | — | 外卖运营栈在本机 |

## 三、环境能力清单

| 环境 | 能力 | 缺失 |
|---|---|---|
| macOS（mac-mini） | 全量 DSH 工具面、LM Studio 本地模型、OCR 工具链、爬虫工具链、AX 自动化、iCloud/Obsidian/Notion 链路 | .NET、Windows 软件、CUDA GPU |
| **Windows（PC-i9）** | **.NET、Windows 软件、i9-14900KF 24 核、RTX 4060 Ti 8GB（CUDA）**、1TB NVMe+2TB HDD | DSH 完整工具面、AX 自动化（macOS）、本地模型栈（未确认） |
| macOS（MacBook Pro） | 移动生产力、闲置算力（M3/16G）、**磁盘 926Gi 仅用 13%（814Gi 空闲）——分布式备份/归档节点候选** | 常驻服务（非宿主）、CUDA |
| iOS（iPhone 17） | 拍照/剪藏/语音采集 | 算力任务 |

### 跨平台插件部署注意（eb5ee9cc 情报 · 2026-08-17）
- **平台绑定原生依赖**：node-pty（better-sidebar 终端）、ssh2/cpu-features/cloudflared（dsh-ssh）——Windows 侧需确认 prebuilds 存在 + pnpm allowBuilds/onlyBuiltDependencies 按平台配置
- @linxin666/dsh-web-ui-all 皮肤/面板类为纯前端，跨平台较安全
- **路由影响**：PC-i9 部署 DSH 插件前需目标平台兼容性预检（eb5ee9cc 按此清单执行）

## 四、待确认项（已核实清单更新 · 2026-08-17）

- [x] PC-i9 CPU/GPU 精确型号 —— **已实测**：i9-14900KF / RTX 4060 Ti 8GB（用户确认 + MCP device_info）
- [x] MacBook Pro CPU/内存/磁盘 —— **已实测**：M3 / 16GB / 磁盘 926Gi（仅用 13%）
- [x] PC-i9 磁盘/目录实测 —— **已完成**（向日葵 cmd2 扫描，12 类数据源）
- [x] 两台设备本地是否装 DSH/模型栈 —— **已确认**：PC-i9 有 Docker+WSL2（fi-dify 栈运行中）+ ollama 镜像；MBP 无 Node/DSH（curl 验证走备选）
- [ ] PC-i9 是否装 CUDA 工具链 / Python 训练环境 —— 待深测（有 ollama 镜像，CUDA 工具链未确认）
- [ ] MacBook Pro 是否装模型栈/DSH —— 待确认（当前仅作数据源/备份节点候选）

## 五、最新能力登记（2026-08-17 P3 后）

| 能力 | 说明 |
|---|---|
| **向日葵 MCP 远程操作** | PC-i9 cmd2 会话（远程命令/文件灌入/端口转发）+ MBP desktop/forward/file 会话——已验证 |
| **SSH 通道** | mac-mini → MBP（100.112.111.120）用户授权公钥后打通；PC-i9 SSH 22 开待凭据 |
| **P3 分布式 MCP 传输层** | external-link-mcp SSE 端点（100.120.203.20:8910）——PC-i9（SDK）+ MBP（curl）三设备闭环，Tailscale 内任意设备可调外链能力（channel.send/status + 分级策略） |
| **MBP 备份/归档节点** | 磁盘 926Gi 仅用 13%（814Gi 空闲）——分布式资源池潜在备份/算力节点 |
| **数据地图** | 三设备数据资产全量登记（device-data-map v1.3） |
| **分布式总线桥（mac-mini↔MBP）** | bus-bridge 8791（launchd 常驻 + 鉴权 X-Webhook-Token）——MBP mbp-node agent 轮询取任务→本地执行→自动回传（done 7+ 实证） |
| **PC-i9 GPU 推理栈** | Ollama 路线 A（KV q8_0/FA/CTX 8192）——qwen2.5:7b 等 11 模型，Tailscale 端点 100.118.15.71:11434 可用 |
| **跨设备模型路由 v1** | 路由表草案（eval/routing-table-v1.md + model-routing-preset-draft.md）——结构化→qwen2.5:7b@PC-i9 / 复杂推理→r1@PC-i9(≥2048) / 分类待统一标签；调度前 /v1/models 探活 |

## 五.5 模型路由联动（2026-08-18 · f0f40ab0 草案落地）

| task | 首选模型 | 端点 | max_tokens | temp | 备选 | 避开 |
|---|---|---|---|---|---|---|
| extraction | qwen2.5:7b | PC-i9 (100.118.15.71:11434) | 1024 | 0 | mistral:7b / llama-3-8b | qwen3.5-2b |
| tool_call | qwen2.5:7b | PC-i9 | 1024 | 0 | r1:8b(2048) / llama-3-8b | llama3.1:8b |
| summary | qwen2.5:7b | PC-i9 | 2048 | 0.2 | r1:8b | — |
| classification | r1:8b | PC-i9 | 1024 | 0 | qwen2.5:7b | llama3.1:8b（待统一标签） |
| reasoning | r1:8b | PC-i9 | 2048+ | 0 | — | — |
| embedding | bge-m3 | mac-mini (127.0.0.1:11434) | — | — | nomic | — |

> 事实来源：model-routing-preset-draft.md（f0f40ab0 2026-08-18）；数据依据 routing-table-v1.md。调度前 /v1/models 探活；r1 必须 ≥2048；0.6B/3B 小模型分流待 W35。
> ⚠️ **provisional（暂定生效）**：① classification→r1 为临时档（cls-01 标签口径 0.0→宽容复测 0.83 上限，但 verbose/CoT 输出污染判定，可靠落地需 constrained decoding 或提示词强制标签集，**维持 provisional**）② embedding(bge-m3) 未做性能评估——两项生效前按暂定处理，其余维度与实测一致正式生效。
> ✅ **正式生效（2026-08-18 LLM-judge 复测）**：summary→qwen2.5:7b@PC-i9 **转正式**（12 条全判 4/5，judge=本机 meta-llama-3-8b-instruct；首选仍 qwen2.5:7b，备选 r1:8b）——原 provisional ② 已解除；extraction/tool_call/reasoning 维持正式。明细：eval/results/llm-judge-and-classification-retest.md（f0f40ab0 2026-08-18）。

## 六、更新日志

| 时间 | 版本 | 变更 |
|---|---|---|
| 2026-08-17 | v1.0 | 首版：16 类任务映射 + 路由规则 + 环境能力清单 |
| 2026-08-17 | v1.1 | PC-i9 硬件实测：4060 Ti 独显确认，GPU 任务升级（CUDA 推理/渲染首选） |
| 2026-08-17 | v1.2 | **过时修正**：待确认项核实（PC-i9 CPU/GPU/MBP 规格/磁盘均实测完成）；补 P3 分布式 MCP 传输层/SSH 通道/向日葵 MCP 远程操作/MBP 备份节点候选等最新能力；修复重复 §四 |
| 2026-08-18 | v1.3 | **模型路由联动**：总线桥常驻 + PC-i9 GPU 推理栈 + 跨设备模型路由 v1（f0f40ab0 草案落地 §五.5） |
| 2026-08-18 | v1.4 | **模型路由补丁①**：summary→qwen2.5:7b 转正式（LLM-judge 12 条 4/5，meta-llama-3-8b-instruct 判定）；classification 维持 provisional（宽容复测 0.83 上限但 CoT 污染，需 constrained decoding）；提取/tool_call/reasoning 维持正式 |
