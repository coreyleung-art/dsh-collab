# i9 节点能力登记(2026-09-09 · bus 通道采集 v2)

> 采集: HR 司库 · 通道: 服务器 bus/send(公约 §3.2) · i9 回报: session-2f883a6f
> 更新: 含 i9 校正(实际角色域 vs 旧五分类)——旧档案 flower-biz/activity 等为过时认知

## 一、实际运行角色域(i9 校正)

| 角色 | 状态 | 说明 |
|---|---|---|
| i9_coordinator (2f883a6f) | running | ERP 主线协调 + 跨设备消息治理 |
| erp_execution (7d48f068) | running | ERP 开发 G2-G6 已 prod, G7 待老板决策 |
| msg_filter_governance | running | R-ERR1-8 固化, G1-G7 谓词+Lean4 门禁 |
| flower_training_pipeline | — | 兰花盆训练/生成管线(GPU 按需) |

⚠️ 旧档案 flower-biz/activity/supply-chain/tools/ai-lab 五分类在 i9 侧**无同名独立服务**——已按实际域修正

## 二、工具/服务/通道

### 业务工具链
- ERP: 审查器 5 工具 + review.db(191 条) + 多店 SOP + 店前缀工具; G2/G4/G5/G6 prod
- 兰花盆: 分类/检测训练脚本 + design-workbench + 评比浏览器规划 v0.2

### 守护/常驻(4 进程)
- device-daemon-i9.py v1.2+(pid 32444): SSE 直连 bus, 防 spoof, 两级确认
- i9-executor.py(pid 49232): 心跳 + discovery 注册
- i9-heartbeat-agent.py(pid 46512) + i9-event-bridge.py(pid 19844)

### 治理引擎
- msg-filter.py: G1-G7 谓词 + Lean4 门禁(0-4 分级)
- i9-bb.py: 黑板双写(本地+中枢镜像)

### 通道
- bus SSE 直连 + bus/send 出站 ✅
- 企微外发(office_doc_search 等 MCP)

## 三、Ollama 模型(13 个)

**本地 10**: qwen2.5vl:3b / qwen2.5:1.5b / mistral:7b / qwen2.5:7b(当前加载 4.8GB 100%GPU) / llama3.1:8b / deepseek-r1:8b / moondream:1.8b / llava:7b / glm-ocr / embeddinggemma-300m-lawvault
**Cloud 3**: minimax-m2.5:cloud / gpt-oss:120b-cloud / glm-5:cloud

## 四、GPU

- RTX 4060 Ti 8GB; util 1%(算力空闲); 显存 91% 被 ollama keep_alive + 桌面应用占
- 按需 ollama stop 释放(qwen2.5:7b)

## 五、部署

- ERP prod 远程 8080(jar f606a9cf G5/G6)
- msg-filter 规则引擎常驻
- 4 守护常驻 + ollama/LM Studio/Docker/CLD host

## 六、资源含义(HR)

1. i9 实际是「ERP/兰花盆/消息治理」算力+业务节点, 非花店运营副驾(旧认知修正)
2. 本地 10 模型 = 零成本推理资源池(Ollama), 可路由批处理
3. GPU 常驻 ollama 模型占显存 91%, 但 util 1% —— 算力闲但显存被占, 需时 ollama stop
4. msg-filter Lean4 门禁 = i9 侧治理与 mac 公约同构(R-ERR 固化)

---
*登记 v2.0 · HR 司库 · 2026-09-09 · 经正确通道(bus/send)采集*
