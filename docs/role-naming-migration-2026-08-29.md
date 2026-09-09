# 角色命名迁移建议 · role-name-check

> 生成：2026-08-29 · 工具：role-name-check.py v1.0
> 规范：<设备>-<角色>（mac-mini/mbp/i9 + 中文职能名）

## 总览：50 档案 · 达标 3 · 待修 47

## 待修清单（建议迁移）
- session-b241741f | 系统运维/知识库型智能体：sysops 工具集 + Dify RAG + 研究管线 + 跨会话情报协 | 问题: missing_device_prefix
- session-43b1a2d3 | DSH/CLD 桌面应用运维与远程访问专家：负责 DSH Web GUI、CLD 壳进程、tailn | 问题: missing_device_prefix
- session-e0c391f7 | DSH 插件本地开发/验证会话（dsh-plugin-local-projects） | 问题: missing_device_prefix
- session-75815fa9 | DSH web 插件机制与 GUI 定制运维会话（按需启用） | 问题: missing_device_prefix
- session-3b5efeef | 文件/文档管理增强与调研流水线：DSH 文件工具面（read_document/解析/OCR/办公文 | 问题: missing_device_prefix
- session-582093dd | dsh 平台/知识库/远程访问会话：维护 dsh 生态知识库与远程访问链路 | 问题: missing_device_prefix, no_role_keyword
- session-45f89009 | 外卖门店多平台运营智能体：多平台（美团/京东/淘宝/抖音/快手）门店经营监控与运营动作执行 | 问题: missing_device_prefix
- session-e032fb77 | DSH 插件开发 / 外卖运营智能体 | 问题: missing_device_prefix
- session-eb5ee9cc | DSH 插件加载/运维（插件运维）—— 社区插件发现、安装、验证与 profile 管理 | 问题: missing_device_prefix
- session-3221f810 | 语音输入与 CLD 插件开发：DSH 语音输入/会议模式/唤醒词静态插件 + 系统级语音输入助手（S | 问题: missing_device_prefix
- session-3d490920 | dsh/CLD 运维排障智能体：负责 DeepSeek Harness 桌面壳（CLD.app）与  | 问题: missing_device_prefix
- session-de7b29de | 外卖门店多平台管理 · 实时采集与客户回复统筹（de7b29de） | 问题: missing_device_prefix
- session-dcac2308 | repo-pipeline / 双仓 CI/CD 搭建：GitHub+Gitee 仓库接入与流水线一 | 问题: missing_device_prefix, no_role_keyword
- session-1e54d56d | GUI 插件开发：MCP 工作站 + 工作流捕获 + 仓库流水线 + 定时调度 | 问题: missing_device_prefix
- session-aa528267 | 外卖多平台运营（美团/京东/抖音 10 店）· 业务动作/告警/分析/用户协调 + 老登语音控制台 | 问题: missing_device_prefix
- session-9910d4b2 | CLD 系统健康审查与迭代管理负责人：宿主健康基线/巡检、迭代需求收集与排期、开发任务管理（指派/跟 | 问题: missing_device_prefix
- session-b3778a1e | 通用成员/前任资源管理者（已交接给 session-e7bfeea8） | 问题: missing_device_prefix, session_code_as_role
- session-4787d717 | 数据调查员（Data Investigator）：情报收集/分析/过滤/归档；信息源体系建设与数据资 | 问题: missing_device_prefix
- session-a3bc8cba | 外卖多平台学习引擎 + 原语/知识资产沉淀者 | 问题: missing_device_prefix
- session-6ed4daf2 | 灾难恢复后自查员：每次 CLD 崩溃/重启/恢复后跑标准自查，输出评估报告给总线程 ai bus 协 | 问题: missing_device_prefix
- session-b278baab | DSH 基础设施根因研究与协作会话（会话持久化/CLD/插件问题定位） | 问题: missing_device_prefix
- 0373d601-bddf-43 | crawler-lab Ralph 循环 worker（第 18 轮已完成；15-20 循环已全部收 | 问题: missing_device_prefix, no_role_keyword
- 724614ce-c3a6-42 | 重启后复核/巡检委派会话（724614ce）——【inactive 后备待命】不承接前台轮询/主动任 | 问题: missing_device_prefix, no_role_keyword
- e83724af-0479-4d | crawler-lab Ralph 迭代 worker（任务期临时写，交付后移交 4787d717  | 问题: missing_device_prefix, no_role_keyword
- session-3f34113d | 通用成员 · 协作执行（无专属资源） | 问题: missing_device_prefix
- session-6f7c739c | 软件工程助手：代码编写/调试/文件操作/仓库与流水线维护 | 问题: missing_device_prefix, no_role_keyword
- session-d20ab960 | 通用成员（inactive · 后备待命，仅定向唤醒响应） | 问题: missing_device_prefix, no_role_keyword
- b51e3d02-2780-44 | 数据调查员·竞品调研子代理 | 问题: missing_device_prefix
- ecd0870b-4980-43 | 数据调查员/调研子代理 | 问题: missing_device_prefix
- session-e7bfeea8 | 前任资源管理者（已交接给 session-a17a52f8，2026-08-18）· 后备支援 | 问题: missing_device_prefix, session_code_as_role
- session-b193c782 | 智能客服/回复助手（P0）：外卖客户消息自动回复引擎——监控 im_sessions 待回复 → 匹 | 问题: missing_device_prefix
- session-0e84e65c | 依赖/供应链专员（P0）：DSH/CLD 依赖供应链监控、加固与恢复——上游发布跟踪、依赖审计、供应 | 问题: missing_device_prefix
- session-55d4d1bd | 文档摄取/归档智能体（P1）：文档的摄取、解析、OCR 与归档专员 | 问题: missing_device_prefix
- session-ffb7c3ab | QA 验收员（P2）：交付质量守门人——插件冒烟、GUI 视觉回归、外卖面板端点回归、验收闭环、回归 | 问题: missing_device_prefix
- session-2fe61625 | 用户洞察分析智能体：用户私人的经营参谋 + AI 增长顾问，持续学习生意全景并输出降本增效与收入增长 | 问题: missing_device_prefix
- session-5a5368af | 设备协调智能体（Device Orchestrator）——跨设备资源协调中枢：数据汇聚、算力调度、 | 问题: missing_device_prefix
- 9828aa93-e967-41 | 数据调查员（调研子代理） | 问题: missing_device_prefix
- session-54e809ed | 媒体专员（Media Correspondent）：智能体网络战地记者+内容主编——每日战报/大事件 | 问题: missing_device_prefix
- 44636abb-effb-4c | 调研子代理（数据调查员体系） | 问题: missing_device_prefix
- 0f42cabc-d7a8-4a | DSH 平台能力调研员（子代理）：DSH/Cordis 插件体系、GUI 挂载点与框架能力可行性调研 | 问题: missing_device_prefix
- session-a17a52f8 | HR 驾驶舱（资源管理者 + 成本监察专员）· CAHAC 示范 Agent Card | 问题: missing_device_prefix
- session-fa1f9150 | FlowerNet 中枢/协调者：跨设备智能体总线（dsh-plugin-agent-way）与 H | 问题: missing_device_prefix
- 4d488478-bbe8-46 | 论文调研专员（外卖运营/平台经济方向） | 问题: missing_device_prefix
- d1911e2e-a777-44 | 论文调研专员（MAS 通信方向） | 问题: missing_device_prefix
- f4e6c537-1bb8-4c | 论文调研专员（MAS 通信方向） | 问题: missing_device_prefix
- session-2a15e6b1 | 资源管理者 + 成本监察专员（HR Cockpit，2026-08-22 接任 session-a1 | 问题: missing_device_prefix, session_code_as_role
- 66830290-9459-4a | 公司法与股权架构研究员（初蘅三公司切割专项） | 问题: missing_device_prefix, no_role_keyword

## 迁移示例
- 外卖多平台运营 → mac-mini-外卖运营
- 资源管理者 + 成本监察专员 → mac-mini-资源管理
