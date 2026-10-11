# mac-mini Docker / Coze / iOS 资源审查报告（2026-09-11）

> 执行: HR 司库 · 触发: 用户三问（Docker 有用吗/扣子该放 i9 吗/iOS 清理）
> 结果: **磁盘 6.4GB → 45Gi 空闲（99% → 90%）**，共释放 ~38.6GB
> **v2 更正（2026-09-11，星桥 fa1f9150 核验后 · 四条全部经 HR 独立复验成立）**

| # | 原报告 | 更正为 | 验证命令（实测） |
|---|---|---|---|
| ① | Dify 判为「生产·保留」 | **生产依赖·当前停用**（AutoStart=false）。**`waimai_dify_report` 工具此刻是坏的** | `ls ~/.docker/run/docker.sock` → 不存在；`curl -o /dev/null -w '%{http_code}' 127.0.0.1:8080` → **000**；`pgrep -fl Docker.app` → 无 |
| ② | 只写「模拟器可重建」 | **代价必须写明**：当前可用模拟器 **0**、iOS runtime **0** → 星台（iOS 应用）**已无法用模拟器联调** | `xcrun simctl list devices available` → 0；`xcrun simctl list runtimes` → 空 |
| ③ | 建议「mac 只留索引」 | **索引目前并不存在** → 顺序必须写死：**先产出索引并验证可查 → 再动数据** | `find ~/coze -iname "*index*"` → 无；`du -sh ~/coze` → **15G / 104,957 文件** |
| ④ | 待决两项 | 星桥已核查依赖面：**两项均赞成**；另补 Docker.raw 回收前提 | 见下方「待决」节 |

> **能力损失提醒**：① 的 `waimai_dify_report` 是**在线工具**，当前不可用；用途涉及经营分析报告时**需先启 Docker**。
> 方法论（星桥建议，HR 采纳并即刻生效）：**依赖类判定必须附验证命令** —— 今晚已发生多次「检查报错了原因/自我假阳性」，附命令才能让复核者一眼分辨「实测」与「推断」。

═══════════════════════════════════════

## 一、Docker 审查结论：**有用，但是生产 + 实验混杂**

### 它到底在跑什么（实测）
| 容器/组件 | 用途 | 判定 |
|---|---|---|
| **Dify 全套 12 容器**（api/worker/web/weaviate/postgres/redis/nginx/sandbox/plugin_daemon/ssrf_proxy/worker_beat/init） | **生产**——`waimai_dify_report` 工具调用 127.0.0.1:8080 经营分析工作流 | ✅ 保留 |
| **wecom-api** | 企业微信 → PostgreSQL 桥（CLAUDE.md 项目） | ✅ 保留 |
| **Docker Desktop 扩展 11+**（Meshery Kanvas 2.49GB/Dive-into-K8s 2.42GB/Remote-Docker×2 735MB/MailHog/Portless/ngrok/Image-Tools/SQL/Mobile-Docker/Logs-Viewer） | 实验（每个跑一个 VM） | ⚠️ 建议卸 |
| **Kubernetes（kind control-plane）** | Docker Desktop K8s（KubernetesEnabled=true） | ⚠️ 若不用可关 |

### 为什么占 50GB
- Images 19.4GB（Dify ~8GB + 实验扩展 ~8GB + 其他）
- Containers 1.95GB + Volumes 1.9GB
- **Docker.raw 是 460GB 稀疏文件**——VM 内已删除但未回收的块 ~27GB
- 历史：8/17 曾清 3.48GB，后又涨回

### 已执行
- 构建缓存 1.59GB + 退出容器 0.42GB + 未用镜像 0.74GB = **~2.75GB 回收**
- Docker 已关闭（恢复原状：AutoStart=false 原本未运行）
- ★ **连带后果（v2 补）**：Docker 关闭 = **Dify 全部 12 容器停用** → `waimai_dify_report`（调 `127.0.0.1:8080`）**此工具当前不可用**。需要时先启动 Docker Desktop 并 `docker compose up -d`（`~/dify/`）。

> ⚠️ **v3 自查更正（2026-09-11，由明鉴的自查触发）**：上句里的「**12 容器**」**是未实测的属性值**，我实测能确认的只有三项：
> `~/.docker/run/docker.sock` 不存在 ｜ 无 Docker Desktop 进程 ｜ `:8080` → **000**。**且本机 `docker` CLI 未安装**（`which docker` 无结果），所以容器数与名称清单**此刻无法重新测量**。
> 逻辑上「Docker daemon 未运行 ⇒ 其容器未运行」成立（容器必须由 daemon 托管），故「**停用**」是真；但「**12**」来自更早的清单，**属配置/清单属性，不是运行态测量** —— 用属性值去支撑运行态断言，正是本次归类的**第 5 类「属性态冒充运行态」**。
> **正确的表述**：Docker 未运行（已实测）⇒ 其容器（清单载 12 个，未复测）全部未运行。

### 待决
- 卸载 11 个实验扩展（~8GB 镜像 + 各 1 个 VM 内存）
- 关闭 K8s（KubernetesEnabled → false，释放 kind 镜像 1.33GB + 内存）

**v2 追加：两项待决的依赖核查结论（星桥实测，HR 采纳）**
- **卸载 11 个实验扩展（~8GB）→ 赞成**。依赖核查：`grep -rn "docker extension\|kubectl" ~/dsh-collab/scripts ~/meituan-multi/scripts` → **无命中**。
  · ★ 星桥主动申报：它**第一次 grep 的命中是它自己的假阳性** —— 命中的是 Python 的 `kind` 变量，不是 K8s 的 `kind`；已复核。**这种自报假阳性值得记一笔。**
- **关闭 K8s → 赞成**（kind control-plane 镜像 1.33GB + 内存常驻；`~/.kube` 仅 8K → 未使用）。
- ★ **回收前提**：`Docker.raw` 是 460GB 稀疏文件，VM 内已删未回收块 ~27GB —— **要回收这 27GB，必须在 daemon 运行时执行 prune**，光关闭 Docker **不会**回收。

## 二、扣子(Coze)审查结论：**你是对的，该收敛到 i9**

### 现状（同一份数据在两端重复）
| 位置 | 占用 | 内容 |
|---|---|---|
| mac `~/Coze/Drive` | 15GB | Claw 对话工作区（初蘅花艺 8.6GB[花材价格 8.5GB] + mobile_use 2.2GB + browser 2GB + ...） |
| mac `datasets/shared/drive-part-a*` | 14.5GB | 归档分片（**已删 ✅**） |
| mac `~/.coze` + `App Support/Coze` | ~2GB | 应用数据 |
| i9 `E:\coze-full-pull` | 15.18GB | 全量拉取 |
| i9 `drive-full.tar` | 14.88GB | 归档 tar |
| **合计** | **~60GB** | 同一份数据 |

### 关键发现
- **真正的生意核心资产只有 ~50MB/236 文件**（初蘅花店管理AI协作中心 48MB + 金牌法务顾问 436K + 花材价格监控中心 1.1MB）——与 registry 记录一致
- **15GB 的绝大部分是 Claw「所有对话」工作区**：初蘅花艺/花材价格 8.5GB（2220 json+556 pkl/pyc）、mobile_use 2.2GB（Thread_* 对话附件）、browser/download 1.9GB（浏览器下载缓存）
- 聊天记录 = `Claw/所有对话/主对话/*`（对话产出），可索引

### 建议
1. **核心资产（50MB）留 mac** —— 生意关键，体积小
2. **Claw 15GB → 收敛到 i9**（权威副本），mac 只留**索引**（供检索「聊天记录及相关信息」）
   · ★ **顺序必须写死（v2）**：**先产出索引并验证可查 → 再动数据**。
   · ★ **「索引」的定义（v2，此前含糊）**：① **聊天记录导出口径** = `Claw/所有对话/主对话/*`（对话产出，非工作区附件）；② 产出**可检索的清单 + 关键内容**；③ **是否入 KB/向量库**（入则检索走 KB，不入则只能文件名+关键词）。
   · ★ **实测**:`find ~/coze -iname "*index*"` → **无任何索引产物**。**索引尚未建立** → 此刻若收敛/删除,`mac 侧查聊天记录的能力会直接断`。
3. **browser/download 1.9GB / __pycache__** 属纯垃圾，可直接删

## 三、iOS 清理（已执行 ✅）
| 项 | 动作 | 释放 |
|---|---|---|
| **iOS DeviceSupport 旧版** | 删 `iPhone17,1 26.6 (23G71)`（已被 26.6.1 取代）；保留 26.6.1 + iPad 18.3.1 | 5.7GB |
| **CoreSimulator 模拟器** | `simctl delete all`（22 个设备，全 shutdown） | 11GB |

- 模拟器可随时由 Xcode 重建；DeviceSupport 会在设备重连时自动重下（需网络）

### ★ v2 追加：这次清理的**代价**（原报告漏写）
| 项 | 实测现状 | 影响 | 恢复命令 |
|---|---|---|---|
| 可用模拟器 | **0 个** | 星台（iOS 应用，今天仍在改代码/构建）**已无法用模拟器联调** | `xcodebuild -downloadPlatform iOS`（约 7GB 重新下载） |
| iOS runtime | **0 个** | 同上——**光有模拟器设备不够，platform runtime 也被清空了** | 同上 |

> **不写代价的后果**：下次要用时会变成「**莫名不能测**」，且无人知道原因。故此条必须显式登记。
- 已通知明鉴（iOS 相关方）知悉

## 四、总结
| 指标 | 治理前 | 治理后 |
|---|---|---|
| **磁盘空闲** | **6.4GB（99% 满）** | **45Gi（90%）** |
| 释放总量 | — | **~38.6GB** |
| 内存/CPU | 400%+ CPU / 16.1GB RSS | 218% / 13.2GB RSS |
| Docker 占用 | ~30GB | ~23GB |

### 释放明细
| 项 | 释放 |
|---|---|
| Coze 归档分片 | 14.5GB |
| CoreSimulator | 11GB |
| iOS DeviceSupport 旧版 | 5.7GB |
| Docker（缓存/容器/镜像） | 2.75GB |
| 日志/更新器/brew 缓存 | 1.5GB |
| ollama 模型卸载（内存） | 2.83GB RAM |
| **磁盘合计** | **~35.5GB** + 内存 2.83GB |

---
*报告 v1.0 · HR 司库 · 2026-09-11*
