# blueprint:flowernet · 花店生意演进 · v2.3
> 生成：bb-blueprint-create.py（stages 数据）· 2026-09-01T06:11:35 · 三件套纪律
> 状态： · 门禁：① 3.0 端侧 ROI_eff>1 才进 4.0 ② d25-4 须 p2-1 完成 ③ d3-3 采纳率≥90% 才自动 ④ p4 门店扩张须 p2 标准化达标（先复制标杆再扩张）
> 依据：research/ops-science/flower-shop-evolution-research.md

## 主线
- **digital**：数字化（大脑） — 纯手工→表格→ERP→端侧→垂直引擎
- **physical**：物理（身体） — 非标人力→标准化→IoT传感→无人产线→门店网络扩张
- **supply**：供应链（血液） — 采购优化→冷链→融资（损耗优化天花板+扩张资金）

## 阶段与子阶段
### 2.5 ERP 信息流系统 [active]
- d25-1 数据规范性底座 [done] — chuheng_erp 57控制器/PG16/PDA-RFID
- d25-2 AI MCP 接入 [done] — 14工具 + robot-ai 门店绑定(PR#24)
- d25-3 外卖→ERP 数据打通 [active] — 全平台10店打通（美团6+京东2+抖音2）；任务卡 T1 映射→T2 回填→T3 增量→T4 对账
- d25-4 流程闭环（进销存/采购/生产/销售/财务） [todo] — 门禁=p2-1 SKU 拆解完成才启动；任务卡 T1 进销存/T2 财务/T3 生产

### 3.0 端侧自动化智能控制 [partial]
- d3-1 端侧模型部署 [active] — Ollama 11模型 + i9 4060Ti CUDA
- d3-2 感知闭环（外卖智能体） [active] — 面板8787 原语/告警/日报
- d3-3 决策-执行闭环 [todo] — 渐进自动化四阶段：人工基线→半自动建议→采纳率回收评估→达标(≥90%)自动（用户定案）
- d3-4 生产/运营任一环节无人值守 [todo] — 无人值守=全部环节（接单/定价/补货/生产），用户定案

### 4.0 云聚+垂直品类引擎 [todo]
- d4-1 数据聚合清洗 [active] — 聚合方案完成，Phase A 订单域可做
- d4-2 垂直模型训练（需求预测/损耗优化） [todo] — flower-yolo 是首块试金石
- d4-3 数据飞轮（模型下发→更优执行→更优数据） [todo] — 护城河

### 2.0 流程标准化 [partial]
- p2-1 SKU 拆解（花壳/花泥/花材/配件） [partial] — 先对齐命名（ERP物品库+采购平台 i9 phoneuse花伍/阿里/淘宝）再定 SKU；不阻塞 ERP；任务卡 T0/T0b/T1/T2/T3
- p2-2 预加工标准化（保鲜/插泥/包扎） [todo] — 
- p2-3 流水线工位分工（10分钟/束节拍） [todo] — 

### 3.0 IoT 传感数据化 [todo]
- p3-1 RFID PDA [partial] — 试点=天河3号店；场景：库存盘点/履约追溯
- p3-2 传感器手套/摄像头（工艺数据化） [active] — 试点=天河3号店（复用12㎡测试冷库）；拆 3 子步：环境传感→摄像头→DOGlove 手套

### 4.0 门店网络扩张 [todo]
- p4-1 选址评估 [todo] — 五山店选址：商圈/流量/租金/竞争分析；任务卡 T1 候选评估/T2 选址定案
- p4-2 门店启动 SOP [todo] — 开店 SOP 复用（标准化复制）：装修/设备/招聘/上线；任务卡 T1 启动清单/T2 首店试运营
- p4-3 复制节奏 [todo] — 标杆店→复制：5 店节奏/资金规划；任务卡 T1 单店模型/T2 复制计划

### 1.0 供应链+融资 [todo]
- s1-1 采购体系优化 [todo] — 前置采购/产地直采/多平台比价（phoneuse 花伍/阿里/淘宝）；任务卡 T1 采购分析/T2 直采链路
- s1-2 冷链升级 [todo] — 中央冷库规划（现 12㎡ 测试仓→规模化）；任务卡 T1 冷库评估/T2 冷链方案
- s1-3 融资路径 [todo] — 融资准备：BP/财务模型/资方对接/里程碑；任务卡 T1 财务模型/T2 BP/T3 资方路演

## 自动化开关锁（R027 + Lean4 逻辑锁）
- **d3-3**：决策-执行闭环：接单/定价/补货自动化（渐进自动化 T4 达标候选）
  - 开关点：`automation-switch on --bp <bp> --stage d3-3 --by <人类> --level L3` · 默认态：OFF
  - 熔断：`automation-switch off --bp <bp> --stage d3-3 --by <人类> --reason <原因>`
- **d3-4**：无人值守：接单/定价/补货/生产 4 环节无人值守（每环节独立开关）
  - 开关点：`automation-switch on --bp <bp> --stage d3-4 --by <人类> --level L3` · 默认态：OFF
  - 熔断：`automation-switch off --bp <bp> --stage d3-4 --by <人类> --reason <原因>`
- **d4-2**：垂直模型决策：需求预测/损耗优化（模型输出建议，人类采纳闸）
  - 开关点：`automation-switch on --bp <bp> --stage d4-2 --by <人类> --level L3` · 默认态：OFF
  - 熔断：`automation-switch off --bp <bp> --stage d4-2 --by <人类> --reason <原因>`

## works
（27 项 works，状态分布 {'done': 2, 'active': 9, 'todo': 14, 'partial': 2}）

---
*blueprint:flowernet · v2.3 · switch 声明已含*