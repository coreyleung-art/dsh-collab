# i9 节点能力登记快照(2026-09-09)

> 采集: HR 司库 · 来源: nodes/i9 心跳 + i9-hr 每日同步(9/7-9/8) + agent-msg 请求回报中
> 状态: 基础层已实测确认, 扩展层待 i9 capability-report 补充

## 一、基础层能力(心跳实测 02:51 在线)

| 能力 | 说明 | 来源 |
|---|---|---|
| gpu-cuda | RTX 4060 Ti 本地 GPU 算力 | 心跳 |
| ollama | 本地模型服务(零成本推理) | 心跳 |
| dsh | DSH headless/守护 | 心跳 |
| python3 | Python 执行 | 心跳 |
| shell | Windows shell | 心跳 |
| file-e-drive | E 盘文件访问 | 心跳 |

## 二、已知扩展(i9-hr 日同步 9/7-9/8)

| 项 | 值 |
|---|---|
| 工具库 | 453 个(tool_lib, 含 Coze/自动化脚本族) |
| 工具链 | 408 tools_count(link_gate 9/1) |
| 规则本 | rules.json 75 条(9/6 已同步, 差 R-ERR4) |
| 磁盘 | C: 42GB free / E: 993GB free |
| GPU | free 5.1GB / used 2.8GB / util 0-4% |
| ledger | 290 行(9/7) |
| vector docs | 1026(9/7) |
| 吸收 | coze-full-pull 15.2GB(E盘) + batch2 162MB(C盘) |

## 三、i9 角色家族(已知, 待 capability-report 确认状态)

| 角色 | 类型 |
|---|---|
| flower-biz | 花店业务(v4-flash) |
| activity | 活动运营(v4-flash) |
| supply-chain | 供应链(Ollama 零成本) |
| tools | 工具链(Ollama) |
| ai-lab | AI 实验室(Ollama) |

## 四、待补充(agent-msg 已请求 notes/i9/capability-report-20260909)

1. 新增工具/服务/通道(较基础层)
2. 各角色当前状态
3. Ollama 模型清单
4. 新增部署(守护/comm 等)
5. GPU 最新可用

---
*快照 v1.0 · HR 司库 · 2026-09-09 · 待 i9 回报后补全登记*
