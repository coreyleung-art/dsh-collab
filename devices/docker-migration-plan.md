# Docker 扩展迁移 PC-i9 · 执行计划 v1

> 产出：session-5a5368af（设备协调智能体）· 2026-08-17 · 用户决策：先完成完整迁移再删本地扩展镜像
> 依据：docker-migration-pc-i9-assessment.md + mac-mini/PC-i9 扩展镜像实测对比

---

## 一、迁移范围清单

### A. 待迁移（开发/实验类扩展 → PC-i9，共 16 个扩展）
| # | 扩展 | mac-mini 占用 | PC-i9 现状 | 迁移动作 |
|---|---|---|---|---|
| 1 | layer5/kanvas + meshery | 2.54G | 需确认 | 评估后在 PC-i9 安装扩展 |
| 2 | kindest/node + desktop-cloud-provider-kind | 1.9G | ✅ 已有（kindest 1.35G + cloud-provider 595M） | 确认版本一致即可 |
| 3 | jesulonimii/portless | 339M | 需确认 | PC-i9 安装 |
| 4 | ngrok | 待确认 | 需确认 | PC-i9 安装（可选） |
| 5 | mailhog | 25M | 需确认 | PC-i9 安装（可选） |
| 6 | deep-dive / mobile-docker-extension / image-tools / sql-extension / remote-docker / logs-viewer / container-notes / openwebui / diveintokubernetes / temporal / warp | ~300M 合计 | 需逐项确认 | 按需安装，非核心 |

### B. 不迁移（保留 mac-mini 或直接停用）
- **Dify 双实例不合并**：PC-i9 fi-dify（竞品情报）/ mac-mini dify（运营知识库 8787 链路）——用途不同各自保留
- **wecom-api**：保留 mac-mini（企微桥接 3100 活跃）
- **redis/postgres/alpine 等**：非扩展，是 Dify/工具依赖镜像，不迁移

## 二、执行步骤（4 步）

| 步骤 | 动作 | 负责 | ETA |
|---|---|---|---|
| **Step 1** | PC-i9 侧：确认 kind/k8s 扩展版本与 mac-mini 一致；E 盘创建 Docker 数据目录（规避 C 盘 7GB）；安装 kanvas/portless 等核心扩展 | 设备协调 + 4787d717（调研现成方案） | 1-2 天 |
| **Step 2** | 迁移验证：PC-i9 侧跑通 kind/k8s/开发容器工作流（如 flower-intel 栈已运行=能力验证）；mac-mini 侧确认无依赖 | 设备协调（向日葵 cmd2 验证）+ QA ffb7c3ab 验收 | 1 天 |
| **Step 3** | mac-mini 停用 16 个扩展 + 删除扩展镜像（回收 ~5.2G） | b241741f 执行 | 0.5 天 |
| **Step 4** | 回归验证：mac-mini Docker 核心（Dify/wecom-api）正常 + 数据卷回落确认 | 设备协调 + QA | 0.5 天 |

**总 ETA：3-4 天**（含调研与验收；可并行压缩至 2 天）

## 三、关键风险与规避

| 风险 | 规避 |
|---|---|
| PC-i9 C 盘 7GB 耗尽 | Docker 数据目录指 E 盘（1.25TB）——`"dataFolder": "E:\\docker-data"` 或 WSL2 vhdx 迁移 |
| 双实例端口/网络冲突 | Dify 双实例不同端口段（mac-mini :8080 / PC-i9 fi-dify 独立端口）——确认无重叠 |
| 扩展功能丢失 | 迁移前逐扩展验证 PC-i9 侧等价功能可用（Step 1-2 覆盖） |
| 向日葵 cmd2 通道不稳定 | 复杂操作走 SSH（需凭据）或分批短命令 |

## 四、迁移完成判定标准

1. PC-i9 侧：kind/k8s 集群可创建 + 开发容器工作流可用（fi-dify 栈已运行 = 基础能力已有）
2. mac-mini 侧：Dify/wecom-api 无回归（8080/3100 正常）
3. 扩展镜像删除后：数据卷 94%→ 预计 90% 以下（回收 ~5.2G）

## 五、待确认项（执行前）

- [ ] PC-i9 扩展安装方式：Docker Desktop 扩展市场（GUI）vs CLI（`docker extension install`）——调研 4787d717 现成方案
- [ ] kanvas/meshery 在 PC-i9 是否真的需要（若非核心，可跳过只迁 kind/k8s）
- [ ] ngrok/mailhog 等工具的替代：本地已有工具或按需再装

---

*计划完成 · 设备协调智能体 · 2026-08-17 · 待用户批准后推进 Step 1*

---

## 六、v2 执行状态（2026-08-18 · vhdx 迁移 + 扩展镜像清理）

> 用户批准 D4①（2026-08-18）：Docker 迁移恢复 = vhdx 数据目录迁移 + 扩展镜像清理。协调者窗口授权（错峰 13:00 后执行，避开外卖午高峰）。

### 现状确认（2026-08-18 11:30 实测）
| 项 | 值 |
|---|---|
| Docker Desktop DataFolder | `E:\docker-data`（Step 1 已生效，E 盘 1.34TB 空闲 ✓） |
| vhdx 位置 | `C:\Users\admin\AppData\Local\Docker\wsl\disk\docker_data.vhdx`（57.1GB） |
| C 盘空闲 | 仅 14.8GB ⚠️（迁移后释放 ~57GB） |
| 运行容器 | fi-dify 8 容器（worker/api/plugin-daemon/web/redis/pg/sandbox，docker.1panel.live 镜像）+ tailscale 容器 |
| 不受影响 | Ollama 11434（Windows 原生服务非容器）；外卖主业务 8787 面板 + Chrome 10 店（不依赖 Docker）；总线中心在 mac-mini |

### 执行步骤（13:00 后）
1. Docker Desktop 重启（Apply&Restart 触发 vhdx 迁移 → E:\docker-data）
2. 验证：E:\docker-data 出现 docker_data.vhdx + C 盘释放 ~57GB
3. 容器自动拉起验证：fi-dify 8 + tailscale 恢复
4. fi-dify 健康检查（web/api/pg）
5. 扩展镜像清理（见下方候选清单，逐镜像确认无容器引用）
6. 回报：迁移完成 + 容器状态 + fi-dify 健康 + C 盘释放量

### 扩展镜像清理候选清单（2026-08-18 实测，无容器引用）
| 镜像 | 大小 | 判定 |
|---|---|---|
| milvusdb/milvus:v2.5.10（含 1panel 前缀重复 tag） | 2.41GB | 🗑 可清（无容器） |
| bitnamilegacy/elasticsearch:8.18.0 | 2.33GB | 🗑 可清 |
| kindest/node:v1.34.3 | 1.35GB | 🗑 可清（迁移目标已在 PC-i9，此为冗余） |
| mysql:8.4.5 | 1.08GB | 🗑 可清 |
| cozedev/coze-studio-server:latest | 782MB | 🗑 可清（备用） |
| docker/desktop-cloud-provider-kind:v0.5.0 | 595MB | ⚠️ 需确认（Docker Desktop 内置组件，谨慎） |
| docker/desktop-kubernetes:* | 592MB | ⚠️ 内置组件保留 |
| registry.k8s.io/kube-*（5 个） | ~495MB | ⚠️ K8s 内置保留 |
| ubuntu/squid:latest | 303MB | 🗑 可清 |
| bitnamilegacy/etcd:3.5 + quay.io/coreos/etcd ×2 | 666MB | 🗑 可清（无 K8s 集群运行） |
| bitnamilegacy/redis:8.0 | 230MB | 🗑 可清（fi-dify 用 redis:6） |
| envoyproxy/envoy:v1.36.4 | 248MB | 🗑 可清 |
| semitechnologies/weaviate:1.27.0 | 234MB | 🗑 可清 |
| postgres:16-alpine | 420MB | 🗑 可清（fi-dify 用 15） |
| nginx:alpine + nginx:latest | 333MB | ⚠️ 保留（web-nginx 生态） |
| nsqio/nsq / testcontainers/ryuk / busybox | 119MB | 🗑 可清 |
| langgenius/* 非 1panel 前缀重复 tag | 0（同 ID） | 🗑 tag 清理 |

**预计回收：~8-10GB**（排除 Docker Desktop 内置组件与运行依赖后）。清理用 `docker rmi` 逐镜像执行，保留 docker/desktop-*、registry.k8s.io/kube-*、ollama、tailscale、fi-dify 栈、nginx。
