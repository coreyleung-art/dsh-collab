# 设备数据地图 v1 · Device Data Map

> 维护：session-5a5368af（设备协调智能体）· 2026-08-17 · v1.0
> 状态：mac-mini 侧 ✅ 已扫描；MacBook Pro / PC-i9 侧 ⏳ 待 SSH 密钥接通后扫描
> 数据归集守属主：ChromaDB/Notion 命名隔离，先登记再写（数据归集走 55d4d1bd 摄取链路）

---

## 一、mac-mini（本机）数据地图 ✅（2026-08-17 实测）

| 位置 | 大小 | 内容 | 分类 | 状态 |
|---|---|---|---|---|
| ~/Desktop | ~200K | DSH 运维：health-check.sh / CLD-resign.sh / 防崩溃手册 / 故障诊断报告 ×2 / DSH-备份 | 运维 | 已盘点（CLAUDE.md 记载的 6 分类目录已不存在，桌面已清空归整） |
| ~/Downloads | ~2.5G | 安装包 DMG（WeCom 596M/TraeWork 392M/TRAE 366M/Chrome 263M/抖店 209M/Coze 208M/Obsidian 203M/扣子×2/AingDesk/MiniMax/Cloudflare MSI）+ 岗位标准化项目文件 36M + 视频 | 安装包/待归档 | ⚠️ 多为已装应用安装包，可清理（用户确认后） |
| ~/Documents | ~430K | trae_projects（openclaw-config）、自动化运营资讯搜集、手机AI自动化搜集、AI经济信息雷达每日采集 | 项目/资料 | 已盘点 |
| ~/Coze/Drive | 51M | 初蘅花店管理 AI 协作中心（门店制度/利润表/招商/调研）、花材价格监控中心、金牌法务顾问、业务法务管理、数据信息源调研分析师 | 生意核心资产 | 已盘点（159 文件，登记 v1.0.55）；待摄取归集 |
| ~/Dropbox | ~0（本地） | 商业文档（云端） | 生意 | 本地已空，云端需确认 |
| ~/OpenChronicle | 4.5M | 本地优先记忆层 | 系统 | 运行中 |
| ~/autoresearch-mlx | 620M | MLX 自主 ML 实验 | 项目 | 已盘点 |
| ~/crawler-lab | 300M | 爬虫工具链（v0.21.0） | 工具链 | 4787d717 独占 |
| ~/papers-db | 2.0M | AI 论文库（69 篇×8 主题） | 知识 | 4787d717 独占 |
| ~/meituan-multi | 859M | 外卖多店管理（app.db/comm.db/面板） | 生意运营 | de7b29de/a3bc8cba 等独占 |
| ~/dsh-collab | 3.0M | 跨会话协作成果（登记表/报告/交付物） | 协作 | 共享 |
| Obsidian vault | ~5.4M | raw/（原始资料）+ wiki/（编译知识）+ 日记/ | 知识库 | 已索引 ChromaDB（wiki 集合） |
| ~/Library/Containers | 62G | **Docker 58G** + WeCom 2.9G + WPS 393M | 系统缓存/容器 | ⚠️ Docker 占 58G，磁盘 95% 满主因 |
| ~/Library/App Support | ~20G | TRAE SOLO 6.2G + Notion 4.0G + Trae CN 3.9G + Lark 2.6G + Docker install 2.1G + 外卖面板 1.2G + Dropbox 1.1G | 应用数据 | 已盘点 |

### mac-mini 数据特征小结
- **可归档/可清理**（用户确认后）：Downloads 安装包 ~2.5G、Docker 58G、Caches 7G
- **知识资产**：Obsidian vault（raw+wiki）、Coze Drive 51M、papers-db、meituan-multi 运营数据
- **待归集**：Coze Drive → 摄取链路（55d4d1bd）入知识库；岗位标准化项目 21 份已登记（55d4d1bd 处理中）

## 二、MacBook Pro / PC-i9 数据地图（向日葵 MCP 已通）

| 设备 | remote_id | 硬件（已实测） | 数据资产（已扫描 2026-08-17） |
|---|---|---|---|
| **MacBook Pro** | 1639073357 | M3 / 16GB / macOS 26.5.2 / 磁盘 926Gi（仅用 12Gi，13%） | ✅ 已扫描（SSH 通道，见下方明细） |
| **PC-i9** | 1640748650 | i9-14900KF / 32GB / Win11 / 4060 Ti / 1TB NVMe+2TB HDD | ✅ 已扫描（见下方明细） |

### MacBook Pro 数据资产明细（2026-08-17 SSH 实测）
| 位置 | 大小 | 内容 | 分类 |
|---|---|---|---|
| ~/Desktop/01_银行活动公司 | — | 银行活动资料 | 生意·活动 |
| ~/Desktop/02_花店业务 | — | 门店投资协议（江南西店）/花千束合作协议/初蘅运营统计/item_naming_cli（商品命名工具） | 生意·花店 |
| ~/Desktop/03_供应链业务 | — | 供应商资料（中行贵金属/工行设计/思淇乐/恒仕文化合同） | 生意·供应链 |
| ~/Desktop/05_AI自动化 | — | AI 知识库汇总（GPT 小红书/活动策划机器人/投标文件审核智能体/合同改写规则等知识库文档） | 项目·AI |
| ~/Desktop/06_个人资料 + 08_广州校园文化促进会 | — | 个人资料/校园文化 | 个人 |
| ~/Documents/trae_projects | — | openclaw-multi-agent-system 等 | 项目 |
| ~/Downloads/鲜花图片训练数据集 | 3.2G | 鲜花图片训练集（flower-classifier 素材）→ **已归集 mac-mini**（见下） | 数据·AI 训练 |
| ~/Downloads/活动策划方案相关 + 美陈布置 + 开业活动合集 | ~1.3G | 活动策划案例 | 生意·活动 |
| ~/Downloads 其余 | ~4G | 安装包/神秘学/照片等 | 待分类 |
| 磁盘 | 926Gi（13% 用） | **大容量低占用**——可作备份/数据节点 | 系统 |

> ⚠️ MBP 磁盘 926Gi 仅用 13%（约 814Gi 空闲）——分布式资源池的**潜在备份/归档节点**。

> ✅ **2026-08-18 训练集归集完成（D4③）**：MBP ~/Downloads/鲜花图片训练数据集（3.2G/133,472 文件）已 rsync 全量归集至 mac-mini `~/dsh-collab/datasets/flower-yolo/`（102 类 YOLO 数据集 + yolov8n 权重 + 分类图集）；dataset-manifest.md 索引 + classes_chinese.txt/args.yaml 已由 55d4d1bd 摄取入库（research 可检索「flower-yolo 数据集」）；图片/权重本体留数据集目录不入向量库；dataset/classes.txt 等 GBK 文件未摄取（乱码无知识价值）。

### PC-i9 数据资产明细（2026-08-17 向日葵 cmd2 实测）
| 位置 | 内容 | 分类 |
|---|---|---|
| C:\Users\admin\flower-intel-agent | 初蘅·智能运营&竞品情报平台（FastAPI+ChromaDB+Dify 5 Agent，.dev-sqlite.db 94KB） | 生意·竞品情报 |
| C:\Users\admin\flower-intel-knowledge | Obsidian 知识库（000 索引 + 100系统/200定价/300竞品/400活动/500供应商/600SOP/900会议）+ ChromaDB RAG（159 chunks 实测入库）+ scripts | 生意·知识库 |
| C:\Users\admin\phoneuse | 手机 App 自动化采集系统 v0.12（花坞订单采集/OCR/OmniParser），DB 空/5 行 | 工具·自动化 |
| C:\Users\admin\Documents\trae_projects | price_robot（企微采购价监控）、meituanwaimai-monitor、GANs、x/ | 工具·监控 |
| E:\chuheng_miniprogram_backup | 初蘅鲜花小程序完整源码（uni-app + 飞书 sync-service + 商品导出脚本） | 生意·小程序 |
| E:\My vibe codding\花伍自动化采集项目 | 花伍（鲜花批发平台）订单采集截图（脚本/数据不在） | 生意·采集痕迹 |
| E:\My vibe codding\flower-classifier | 花束图片分类（CLIP/HDBSCAN/FAISS，591 图） | 项目·AI |
| E:\My vibe codding\flowercheck | 鲜花批发价格监控工具 | 生意·价格 |
| E:\My vibe codding\flower\flower_platform | 花艺创研赏金平台（前后端） | 项目·平台 |
| E:\有花漾商品库.xlsx | 花漾商品库 | 生意·商品 |
| C:\Users\admin\Desktop | 初蘅运营文件（薪酬/考勤/利润表/商品数据/门店 SOP 大量 Excel+DOCX） | 生意·运营 |
| E:\网页下载 / WeChat / 微信 / 百度网盘 | 下载与社交数据 | 待分类 |

> 注意：PC-i9 数据主要分布在 C:\Users\admin 与 E:\ 盘；C 盘仅剩 12.6G（⚠️ 亦需关注）；未发现「花店地图 POI」现成数据，最接近为 flower-intel 框架与花伍采集痕迹。
> 2026-08-17 补充：flower-intel-knowledge 知识库只读快照已生成 → ~/dsh-collab/devices/flower-intel-knowledge-snapshot.md（供 2fe61625 dogfooding 评估）；核心文档（000/110/120/130/210/310/320/610/620）已读取入快照，140/150/160 为空壳，.chroma_data 未传输。

## 三、归集管线（v1 规划）

```
跨设备扫描（mac-mini 本机 + SSH 远程）→ 分类打标（生意/项目/资料/待归档/可清理）
→ 归集（Obsidian raw+wiki / DSH KB / ChromaDB，前缀隔离）→ 数据地图更新
```

- 文档类 → 55d4d1bd 文档摄取链路（dshdoc_extract + OCR → raw/wiki + 索引）
- 生意资产（Coze/Notion）→ 2fe61625 用户洞察 + Notion 只读通道
- 命名隔离：ChromaDB 集合前缀先登记 HR（resource-registry.md）+ 对齐 b241741f 命名规范

## 四、更新日志

| 时间 | 版本 | 变更 |
|---|---|---|
| 2026-08-17 | v1.0 | 首版：mac-mini 全量数据地图（14 类）+ 远程设备待扫描计划 + 归集管线 |
| 2026-08-17 | v1.1 | 向日葵 MCP 接入：远程设备硬件实测登记（MBP=M3/16G、PC-i9=i9-14900KF/4060 Ti/1TB+2TB）；扫描计划改走向日葵会话 |
| 2026-08-17 | v1.2 | **PC-i9 数据资产全量扫描完成**（向日葵 cmd2 实测）：12 类数据源登记（flower-intel 竞品情报/初蘅小程序源码/花伍采集痕迹/价格监控/运营文件等）；未发现花店地图 POI 现成数据；MBP 待扫描 |
| 2026-08-17 | v1.3 | **MacBook Pro 数据扫描完成**（SSH 通道，用户开启远程登录）：Desktop 17G（银行/花店/供应链/AI 分类）+ Downloads 8.8G（鲜花图片训练集 3.2G 等）+ Documents；磁盘 926Gi 仅用 13%——分布式资源池潜在备份节点；**三设备数据地图全部完成** |
| 2026-08-18 | v1.4 | **③ 训练集归集完成（D4③）**：MBP 鲜花图片训练数据集 rsync 全量归集至 mac-mini ~/dsh-collab/datasets/flower-yolo/（3.2G/133,472 文件）；manifest 索引 + classes_chinese/args.yaml 摄取入库（55d4d1bd 执行，research 可检索）；图片/权重本体不入向量库 |
