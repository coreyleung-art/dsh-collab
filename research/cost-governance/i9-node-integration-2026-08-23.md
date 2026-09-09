# i9 节点总线接入：完整经验沉淀（踩坑 + 修复 + 协议）

> 日期：2026-08-23 · 协调者 fa1f9150 · 实战全记录
> 目标：mac-mini 核心总线指挥 i9 本地智能体（deepseek-v4-flash），调动 i9 设备资源（GPU/文件/项目沉淀）完成总线任务

## 一、架构（最终形态）

```
mac-mini（核心总线中枢）
├── blackboard-server :8792（黑板：nodes/tasks/data/notes 命名空间）
├── agent bus / 协调者（派单）
└── Tailscale 内网

PC-i9（算力节点 + 数据节点）
├── DSH 智能体（deepseek-v4-flash 在线模型，常驻轮询黑板）
├── i9-bb.py（http.client 直连助手，显式 Content-Length）
├── RTX 4060 Ti 8GB（全网络唯一 CUDA GPU）
├── Ollama 11 模型（本地）
└── E 盘 1.2TB（项目沉淀）
```

## 二、任务卡协议（黑板）

```
中枢 PUT /tasks/i9/cmd  body={"task_id":"...","action":"shell|info|ollama|scan|数据沉淀","payload":{...}}
节点 GET /tasks/i9/cmd → 取 value 字段（404 视为无卡）
节点执行 → PUT /tasks/i9/result  body={"task_id":"...","ok":true,"output":"...","node":"i9"}
节点 DELETE /tasks/i9/cmd（清卡）
```

- 任务卡 action：`shell / info / ollama / scan / 数据沉淀`
- 回报格式：`task_id + ok + output`（结构化，可溯源）
- 节点注册：`PUT /nodes/i9`，心跳：`PUT /nodes/i9/heartbeat`（60s/次）

## 三、踩坑与修复（核心价值）

### 坑 1：黑板 BaseHTTPRequestHandler 只认显式 Content-Length（⚠️ 最坑）
- **现象**：curl/PowerShell/urllib 的 PUT body 被丢弃，value 恒为空对象 `{}`
- **根因**：blackboard-server 用 `int(headers.get("Content-Length", 0))` 读 body，不显式设置 Content-Length 的客户端（部分 urllib/代理场景）→ body 读不到
- **修复**：显式设置 `Content-Length: str(len(body))`，或改用 http.client（自动设置）

### 坑 2：Windows Python urllib 对 PUT body 兼容问题
- **现象**：mac-mini 的 urllib PUT 正常，i9 的 Windows Python 3.11 urllib PUT body 丢失
- **根因**：Windows urllib 的 PUT + data 组合有兼容差异
- **修复**：统一改用 `http.client`（明确控制 body + Content-Length，跨平台稳定）

### 坑 3：双执行器抢任务卡（⚠️ 必踩）
- **现象**：python 脚本（i9-node-agent.py）+ DSH 智能体同时轮询 tasks/i9/cmd → 抢任务/双执行
- **修复**：只能一个执行器——DSH 智能体全权接管，python 脚本停止（用户确认）

### 坑 4：i9 dsh 0.1.0-rc.5 的 prepare 错误
- **现象**：`Cannot read properties of undefined (reading 'prepare')`，智能体一调工具就崩
- **根因**：`ctx.tools[TOOL_RUNTIME_SCHEDULER]` undefined（ToolRuntime 调度器未注册），rc.5 的工具运行时问题
- **修复**：升级 dsh 到 rc.6（MacBook 侧修复）

### 坑 5：中文 Windows systeminfo 是 GBK 输出
- **现象**：systeminfo 中文输出乱码（GBK 被当 UTF-8 解码）
- **修复**：回报前转码（GBK → UTF-8）

### 坑 6：向日葵 MCP 远程会话需「手动远控一次」建信任
- **现象**：device_info 通（查询类），control_connect（cmd2/file）30s 超时
- **根因**：registry v1.0.44 记录「远程 CMD/桌面会话需先手动远控一次建立设备信任」
- **结论**：远程操作类工具（cmd2/file）必须用户先在向日葵手动远控一次；查询类（device_info）不需要

### 坑 7：i9 SSH 密码认证失败
- **现象**：22 端口开，但 7 个用户名变体 + 密码全部 denied（触发了 Connection reset 防爆破）
- **根因**：「corey liang」是显示名，不是 SAM 登录名（可能是微软账号邮箱或别的）
- **结论**：SSH 凭据待用户确认真实登录名；不阻塞主线（黑板方案绕开）

## 四、当前状态（2026-08-23）

| 项 | 状态 |
|---|---|
| i9 节点注册 | ✅ nodes/i9（status online） |
| i9 心跳 | ✅ 60s/次（DSH 智能体） |
| i9 任务轮询 | ⚠️ DSH 智能体声称 30s/次，但实测未取走任务卡（待 i9 侧排查轮询循环） |
| i9 的 dsh 智能体 | ✅ 已修好（rc.6）+ 已任命（deepseek-v4-flash） |
| python 执行器 | ✅ 已停止（避免双执行器） |
| 任务卡协议 | ✅ 已确认（shell/info/ollama/scan/数据沉淀） |
| i9 资产 | GPU RTX 4060 Ti 8GB / Ollama 11 模型 / E 盘 1134.8GB free |

## 五、遗留问题（待办）

1. **DSH 智能体轮询循环没真正取任务卡**——心跳循环在跑（60s），轮询循环（30s GET /tasks/i9/cmd）没取走任务卡。需 i9 侧查轮询循环的实际状态/路径
2. i9 本地 Ollama 11434 从 mac-mini 不可达（防火墙/监听问题，待查）
3. i9 SSH 真实登录名待确认（用于未来免密通道）
4. 向日葵 cmd2 待用户手动远控一次建信任（解锁远程操作）

## 六、可复用要点（其他节点照抄）

1. 黑板写入必须显式 Content-Length（或 http.client）
2. 单执行器原则：一个节点只有一个执行器轮询任务卡
3. 任务卡 action 规范化：shell/info/ollama/scan/数据沉淀
4. 心跳/轮询分离：心跳保活 + 轮询取卡，分开循环
5. i9 是「算力节点」：RTX 4060 Ti（CUDA）+ Ollama + E 盘，是 mac-mini 的 GPU 外挂

## 七、关联

- `node-relationship-model-v1.0.md`（任务卡协议设计）
- `architecture-evolution-stages-v1.0.md`（阶段 2 分布式节点）
- `devices/i9-node-agent.py`（python 执行器，已停用归档参考）
- `devices/i9-node-agent-preset.md`（i9 节点智能体任命 prompt）
- `i9-shared-assets-2026-08-23.md`（mac-mini 可共享给 i9 的知识资产）

---
*i9 节点总线接入经验 v1.0 · 协调者 2026-08-23*
