# Docker 工作流迁移 PC-i9 评估报告 v1

> 产出：session-5a5368af（设备协调智能体）· 2026-08-17 · 用户发起
> 目的：评估将 mac-mini 的 Docker 相关工作流工具（Kanvas/ngrok/mailhog/kindest 等扩展 + 容器化工具）迁移到 PC-i9 是否更资源高效（释放 mac-mini 内存/磁盘/负载）

---

## 一、结论先行

**✅ 迁移可行且推荐，但需分区处理**：

| 迁移对象 | 结论 | 理由 |
|---|---|---|
| **Docker Desktop 扩展**（Kanvas/ngrok/mailhog/kindest 等 4.5-5G） | **直接删除不迁移** | 日常未用、mac-mini 侧价值低；PC-i9 已有同款扩展镜像（kindest/kubernetes 全套已在 PC-i9 Docker 里） |
| **Dify 工作流栈** | **PC-i9 已在跑更完整实例** | fi-dify-* 8 容器 Up 18h，资源占用 <1GiB；mac-mini 侧 12 容器 3.2GiB |
| **容器化工具链**（ollama/milvus/mysql 等） | **PC-i9 已有镜像** | ollama 9GB/milvus 2.4GB/mysql 1GB 镜像已在 PC-i9 |
| **wecom-api / 外卖运营栈** | **保留 mac-mini** | 与 8787 面板/企微客服链路耦合，非 Docker 迁移范畴 |

## 二、PC-i9 承载能力实测（2026-08-17 向日葵 MCP 采集）

| 项 | 实测值 | 评估 |
|---|---|---|
| CPU | i9-14900KF（32 线程，Docker 分配 32 核） | ✅ 远超 mac-mini M4（10 核） |
| 内存 | 32GB 物理 / WSL2 分配 15.52GiB / 空闲 6.1GB | ⚠️ 物理内存被前台占用多，但 WSL2 池内 Dify 栈仅用 <1GiB，余量充足 |
| 磁盘 | C 盘剩 7GB（⚠️ 紧张）/ **E 盘 1.25TB 空闲** | E 盘可放 Docker 数据目录（迁移时指定） |
| Docker | **Docker Desktop 29.2.1 + WSL2 已装且运行** | ✅ 零安装成本 |
| 现有负载 | **11 容器运行**（fi-dify 8 + tailscale 等）、38 镜像 | 已是活跃 Docker 节点 |
| 网络 | Tailscale 组网 + 向日葵 MCP 通道已通 | ✅ 远程运维可达 |

**关键发现**：PC-i9 已运行**一整套 flower-intel Dify 栈**（fi-dify-api/worker/plugin-daemon/web/redis/pg/sandbox，Up 18 小时，CPU <2%、内存 <1GiB 合计）——即用户问的「Docker 工作流」在 PC-i9 已有同构部署，迁移本质是**统一到 PC-i9**而非「搬过去」。

## 三、mac-mini 侧现状（对比基准）

| 项 | 实测值 | 备注 |
|---|---|---|
| Dify 栈 | 12 容器，合计 ~3.2GiB 内存 | nginx/web 为 8080 入口必需（不可停） |
| 内存压力 | swap 10.2G used / free 1.2G | ✅ 较清理前（28.7G）大幅改善 |
| 负载 | loadavg 4.17（vs 早前 22-28） | ✅ 清理效果显著 |
| 数据卷 | 95%（剩 26Gi） | 仍需控制增长 |
| 扩展镜像 | 4.5-5G（kanvas/kindest 等） | 用户已定保留不清理 |

## 四、迁移收益测算（若统一到 PC-i9）

| 场景 | mac-mini 释放 | PC-i9 增加 | 净收益 |
|---|---|---|---|
| Dify 主实例迁 PC-i9 | ~3.2GiB 内存 + 24GB 镜像 | 已有同构栈（fi-*），增量小 | ✅ 内存压力缓解 |
| 扩展镜像删除 | 4.5-5G 磁盘 | 0（PC-i9 已有） | ✅ 磁盘释放 |
| 开发/实验容器（kind/k8s） | — | PC-i9 32 核更合适 | ✅ 算力匹配 |

## 五、风险与注意事项

1. **C 盘紧张**（7GB）：PC-i9 Docker 数据目录需指到 E 盘（1.25TB），避免 C 盘耗尽
2. **双 Dify 实例冲突**：PC-i9 已有 fi-dify（flower-intel 栈），mac-mini dify（外卖运营 KB/QA 在用）——**不建议合并**，两栈用途不同（fi=竞品情报，dify=运营知识库）；迁移仅针对「开发/实验类容器」与「扩展」
3. **网络依赖**：PC-i9 Docker 网络出口（Tailscale 已配 tailscale 容器）需确认可访问 mac-mini 服务（8787 等）
4. **向日葵通道运维**：远程 Docker 操作走 cmd2（大输出不稳定）——建议配合 SSH（需凭据）或仅执行短命令

## 六、建议行动（待用户拍板）

1. **推荐**：mac-mini 扩展镜像直接删除（用户已定保留——可复议，4.5-5G 释放价值高）
2. **推荐**：开发/实验类容器（kind/k8s/mailhog 等）后续新建统一放 PC-i9（32 核 + E 盘空间），mac-mini 专注生产栈
3. **可选**：若需真正统一 Dify，评估两栈合并到 PC-i9（需迁移 8787 依赖的 wecom-api 链路，工作量大，本期不建议）
4. 向日葵 cmd2 通道对 PC-i9 远程 Docker 操作可行（短命令），复杂操作建议 SSH

## 七、数据来源

- PC-i9：向日葵 MCP cmd2 实测（wmic/docker info/docker stats/docker ps）
- mac-mini：本机 docker stats / vm.swapusage / vm.loadavg

---

*评估完成 · 设备协调智能体 · 2026-08-17*
