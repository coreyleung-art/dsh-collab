# mac-mini 磁盘清理清单 · 2026-08-17

> 维护：session-5a5368af（设备协调智能体）· 2026-08-17 · v1.5
> 背景：数据卷 95% 满（388Gi/460Gi，剩 23Gi）——用户已确认先出清单再拍板，**本清单只列方案，不自动执行**
> 安全边界：删除/清理一律用户逐项确认后执行；执行前查红绿灯 + 备份确认

---

## 0. 执行状态（2026-08-17）

### ✅ Step 1 已执行（用户批准 · 2026-08-17 08:00 前后）
| 项 | 预期 | 实际回收 | 备注 |
|---|---|---|---|
| Downloads 安装包（已装应用 DMG） | ~2.9G | **2.5G** | 保留未装应用安装包 586MB（抖店/AingDesk/MiniMax/maiyatian.exe） |
| ~/Library/Caches | ~7G | **4.9G** | 跳过在用面板缓存（外卖门店多平台管理/美团多店铺管理，Chrome 占用）；系统保护目录自动跳过 |
| ~/.cache（uv/autoresearch/chroma/electron） | 3.1G | **3.15G** | 全部清空 |
| com.docker.install | 2.1G | **2.16G** | 已删 |
| **合计** | ~15.1G | **12.7G** | 数据卷 95%→**90%**（剩 46Gi） |

- ⏳ 待退出时清：CLD 应用缓存 374MB（CLD 运行时不可清，重启后处理）
- 未执行：CLD 缓存（退出时清）、④ pet-backup 原版贴图（待用户单独确认）、插件 node_modules（条件清理）

### ✅ Step 2 Docker 已执行（b241741f · 2026-08-17，用户批准启动实测）
| 项 | 回收 | 备注 |
|---|---|---|
| 构建缓存 | 2.174G | 26→13 项 |
| 悬空卷 | 1.307G | 16→13（活跃 11 保留） |
| 悬空镜像 | 0 | 全部活跃，未误删 |
| **合计** | **3.48G** | 清理后 Images 29.38G / 卷 1.86G / 构建缓存 1.59G |

- 安全边界：weaviate + postgres 数据卷未动 ✓ 运行容器未停 ✓
- **待用户确认**：① 未使用镜像 5.25G（含旧版 Dify）可 -a 清 ② 辅助容器 web/nginx 停用（随硬重启窗口）③ openclaw 1.49G 停用

### ✅ Step 2 补充执行（用户批准三项 · 2026-08-17）
| 项 | 结果 | 回收 |
|---|---|---|
| ① 未使用镜像 | b241741f 执行 image prune -a | 1.244G |
| ② 辅助容器 web/nginx | ⚠️ 实测不可停（Dify 8080 链路必需，停后 502）→ 已恢复保持运行 | 0 |
| ③ openclaw | ✅ 已停用（18789 无监听、无 API key 未工作、无依赖） | 容器层 0.42G |
| wecom-api | 保守保留（3100 端口活跃=企微桥接在用） | 0 |

- 累计回收：Step1 12.7G + Step2 3.48G + 本轮 1.66G ≈ **17.8G**，数据卷 94%（剩 27Gi）
- **nginx/web 标记「必需保留」**（Dify 入口链路：nginx 端口代理 → web 前端/API 网关 → api 容器；停任一即 502/000，b241741f 实测 8080=200 确认）——**绝不停用**
- 扩展镜像 4.5-5G（kanvas/kindest 等 Docker Desktop 扩展）**待用户确认**（b241741f 推荐清，日常未用）；openclaw 已停 ✓；wecom-api 保留（3100 企微桥接活跃）

---

## 一、可清理项总览（合计可回收 ~63-72G）

| # | 清理项 | 大小 | 风险 | 建议 | 状态 |
|---|---|---|---|---|---|
| 1 | **Docker 镜像/容器/悬空卷**（Docker.raw 58G 内的虚胖） | ~20-40G（需 docker 运行时实测） | 中：确认无在用容器后清理安全 | ⭐ 优先做 | 待 Docker 启动后实测 |
| 2 | Downloads 安装包 DMG/MSI（已安装应用） | ~3.2G | 低：已安装即可删安装包 | ⭐ 优先做 | 待确认 |
| 3 | ~/Library/Caches 缓存 | ~7G | 低：可重建 | 做 | 待确认 |
| 4 | **~/.cache（uv 2.0G / autoresearch 788M / chroma 166M / electron 116M）** | ~3.1G | 低：构建缓存可重建 | 做 | 待确认 |
| 5 | TRAE 系列旧版（TRAE CN 3.9G + TRAE 0.6G + TraeWork 缓存 0.8G） | ~5.3G | 中：确认当前用哪个版本 | 保守处理 | 待确认 |
| 6 | com.docker.install（Docker 安装包缓存） | 2.1G | 低 | 做 | 待确认 |
| 7 | 旧系统卷/Preboot 残留（系统级） | 见说明 | 高：需系统工具 | 不动（交给 macOS） | — |
| 8 | **CLD 应用缓存**（~/Library/Application Support/CLD/Cache，Electron 渲染缓存） | 374MB | 低：自动重建 | 做（CLD 退出时清/清后重启） | 75815fa9 贡献 |
| 9 | 小型冗余（autopilot_shots 1.5MB / /tmp/camel-pet 784KB / pet-backup 原版贴图 1.5MB） | ~3.8MB | 低 | ④ 需用户单独确认 | 75815fa9 贡献 |
| 10 | @linxin666/dsh-pet previews/ 动图（客户端未引用） | ~1.5MB | 低 | 归供应链处理 | 75815fa9 贡献，0e84e65c 处理 |
| 11 | **插件构建产物**（dsh-plugin-mcp-station/node_modules 109MB + workflow-capture/node_modules 91MB + mcp-servers 源码 10MB + settings.yaml.bak 4KB） | ~210MB | 低（重建 6s 可恢复） | **条件清理**：仅确定不构建时清；venv 120MB/数据保留 | 1e54d56d 贡献 |

## 二、明细

### 1. Docker 虚胖（潜在最大回收项）——含容器依赖评估（b241741f · 2026-08-17）
- Docker.raw 虚拟盘 460G，实际占用 58G——但 Docker 内部有镜像/容器/卷/构建缓存
- ⚠️ 当前 Docker 未运行（CLI 无响应）——需启动后 `docker system df` 实测内部占用
- **当前 13 容器依赖评估**：
  - **核心必须（7，不可停）**：Dify api/worker/worker_beat/db_postgres/redis/weaviate/sandbox——知识库/QA/工作流全依赖
  - **辅助可优化（2）**：Dify web（前端壳，可停省 367MB）、nginx（端口代理，直连 api 可省）——瘦身候选
  - **非 Dify（2）**：wecom-api（企微桥接，视使用频率）、openclaw（1.49GB 虚拟，若未用可停）
- **安全执行清单**（b241741f 建议，不动运行容器）：
  1. `docker system df` 实测镜像/容器/卷真实占用
  2. `docker image prune -a`（清悬空镜像）+ `docker builder prune`（构建缓存）——**可安全执行**
  3. 停用辅助容器（web/nginx/openclaw）释放内存（配合内存治理）
  4. ⚠️ **weaviate 数据卷 + postgres 数据卷切勿清**（知识库/会话数据）
- **预估回收 20-40G**（悬空镜像 + 构建缓存为主）

### 2. Downloads 安装包（3.2G，可回收 ~2.9G）
| 文件 | 大小 | 对应应用 |
|---|---|---|
| WeCom_5.0.8.99856_Apple.dmg | 596M | 企业微信（已装） |
| TraeWork_CN-darwin-arm64.dmg | 392M | TRAE（已装） |
| TRAE_Work-darwin-arm64.dmg | 366M | TRAE（已装） |
| googlechrome.dmg | 263M | Chrome（已装） |
| doudian_v1.1.8.dmg | 209M | 抖店（已装？需确认） |
| coze_space_*_ext.dmg | 208M | Coze（已装） |
| Obsidian-1.12.7.dmg | 203M | Obsidian（已装） |
| 扣子-v1.1.32 / v1.0.3 | 349M | 扣子（已装，旧版可删） |
| AingDesk / MiniMax / Cloudflare WARP.msi | 447M | 已装/弃用 |
| maiyatian.exe / 其他 | ~60M+ | 杂项 |

### 3. Caches（~7G，全低风险）
| 目录 | 大小 | 说明 |
|---|---|---|
| 外卖门店多平台管理 | 2.1G | 面板缓存（重生成） |
| TRAE SOLO CN / Trae CN / Trae | 2.3G | IDE 缓存 |
| Homebrew / go-build | 0.8G | 构建缓存 |
| LarkShell | 465M | 飞书缓存 |
| coze-updater 等 | 0.7G+ | 其他 |

### 4. ~/.cache 构建缓存（3.1G，低风险）
| 目录 | 大小 | 说明 |
|---|---|---|
| uv | 2.0G | Python 包缓存（uv 可自动重建） |
| autoresearch | 788M | MLX 实验缓存 |
| chroma | 166M | ChromaDB 缓存 |
| electron | 116M | Electron 下载缓存 |

### 5. TRAE 版本冗余（~5.3G）
- TRAE SOLO CN（App Support 6.2G + Caches 0.8G）——当前主力？（需确认）
- Trae CN（3.9G + 0.8G）、Trae（0.6G + 0.7G）——旧版/并行版本
- 确认只用 1-2 个版本后，其余可整体删除

### 6. com.docker.install（2.1G）
- Docker Desktop 安装器缓存——Docker 已装，可删

## 三、执行顺序建议（每步用户确认）

1. **Step 1（低风险，~13G）**：Downloads 安装包 + Library/Caches + ~/.cache + com.docker.install
2. **Step 2（中风险，~20-40G）**：启动 Docker → `docker system df` 实测 → 按确认清单 prune
3. **Step 3（需确认用途）**：TRAE 冗余版本

## 三.5 执行状态总览（2026-08-17 全部收官）

| 步骤 | 内容 | 回收 |
|---|---|---|
| Step 1 ✅ | 安装包/缓存/.cache/docker.install | 12.7G |
| Step 2 ✅ | Docker 构建缓存/悬空卷/镜像/openclaw | 5.14G（3.48+1.244+0.42） |
| Step 3 ✅ | TRAE CN + Trae 旧版（SOLO CN 保留） | ~6.4G |
| **累计** | | **≈24.2G**（数据卷 95%→93%） |

## 四、更新日志

| 时间 | 版本 | 变更 |
|---|---|---|
| 2026-08-17 | v1.0 | 首版：5 类可清理项，预估回收 63-72G，分 3 步执行 |
| 2026-08-17 | v1.1 | 补充 ~/.cache 3.1G（uv/autoresearch/chroma/electron）→ 7 类可清理项，预估回收 66-75G，Step 1 扩至 ~13G |
| 2026-08-17 | v1.2 | 75815fa9 贡献：CLD 缓存 374MB + 小型冗余 3.8MB + dsh-pet previews 1.5MB（归供应链）→ 10 类可清理项 |
| 2026-08-17 | v1.3 | b241741f Docker 依赖评估入表：13 容器分级（核心 7 不可停/辅助 2 可瘦身/非 Dify 2 视使用）+ 安全执行清单（image prune + builder prune，数据卷切勿清） |
| 2026-08-17 | v1.4 | 1e54d56d 贡献：插件构建产物 ~210MB（node_modules 条件清理/venv 保留）→ 11 类可清理项 |
| 2026-08-17 | v1.5 | **Step 1 已执行（用户批准）**：回收 12.7G（Downloads 2.5G + Caches 4.9G + .cache 3.15G + docker.install 2.16G），数据卷 95%→90%；CLD 缓存待退出时清 |
| 2026-08-17 | v1.6 | **Step 2 Docker 已执行（b241741f）**：回收 3.48G（构建缓存 2.174G + 悬空卷 1.307G），数据卷 90%→（累计回收 16.2G）；待用户确认：未使用镜像 5.25G/辅助容器/ openclaw |
| 2026-08-17 | v1.7 | **Step 2 补充执行（用户批准三项）**：镜像 prune 1.244G + openclaw 停用 0.42G ≈1.66G；web/nginx 实测不可停（8080 链路）已恢复；wecom-api 保留（3100 活跃）；扩展镜像 4.5-5G 待确认；累计回收 ≈17.8G，数据卷 94% |
| 2026-08-17 | v1.8 | **Step 3 TRAE 已执行（用户批准）**：主力=TRAE SOLO CN（TraeWork 推断确认）；删 Trae CN + Trae（应用+数据 ~6.4G）；**磁盘清理三步全部收官**，累计回收 ≈24.2G，数据卷 93%（剩 32Gi）；扩展镜像保留待 i9 迁移结论 |
