# 星舵监督基准校准协议 v1.0 · 2026-08-30

> 来源：data/blueprint/change-sync-mechanism（用户提议 2026-08-30，星桥上线）
> 原则：**监督基准必须跟随蓝图变更**——蓝图是主线指南针，按旧 stage 判停滞=误判。

## 一、变更监听（每次巡检第一步）

1. 读黑板 `data/blueprint/changelog/` 最新条目（列出 key，取 ts 最新）
2. 扫 `notes/collab/blueprint-change-*` 广播（谁改了什么/影响哪些阶段）
3. 有变更 → 执行基准更新（第二节）；无变更 → 按现行基准巡检

## 二、基准更新流程

- 变更触发：明鉴 blueprint-create / blueprint-refine（BP-9）时自动广播
- 收到「蓝图更新，校准监督基准」短提示 → 立即：
  1. 读最新 changelog 条目（blueprint_id/version/change_summary/affected_stages）
  2. 对照我的监督基准表（当前 stages 缓存）逐项 diff：
     - active 阶段变了？→ 更新「当前盯哪些 stage」
     - stage 状态变了（done/active/todo）？→ 更新停滞判定参照
     - gate 变了？→ 更新「进下一阶段条件」
  3. 把新基准写入 data/progress/baseline-<ts>（版本化，留痕）
  4. 停滞判定一律基于**最新基准**，杜绝按旧 stage 误判

## 三、停滞判定口径（v1.0）

- **不判停滞**：active 阶段有主且有推进证据 / 阻塞在用户侧（如 M1 npm 认证）/ 阻塞在外部网络（如 arXiv）
- **判停滞**：active 阶段 ≥48h 无任何推进回报，且无用户/外部阻塞、无主或主未动
- **提醒卡门槛**：判定停滞才写；同项 24h 不重复；卡内容具体（停滞 stage + 建议动作 + 优先级）

## 四、通道纪律（R002 合规）

- 提醒卡主通道：黑板 `data/progress/reminder-<ts>`（data 命名空间，合规）
- 全局公告类（如蓝图变更）才走黑板 `notes/collab/`；定向消息走 `notes/<node>/`
- 文件系统留档：`~/dsh-collab/notes/collab/reminder-<ts>`（物理备份，防黑板丢失）

## 巡检节奏（v1.6 · 2026-08-30 用户拍板 4h→15min）

- **15 分钟主动巡检**（用户要求，2026-08-30）：
  - launchd `com.dsh.xingduo-wake`：StartInterval 900s（原 14400s），RunAtLoad true，已加载
  - 链路：xingduo-wake.py 写唤醒消息 notes/collab/xingduo-wake-<ts> → central-inbox 注入本会话 → 执行巡检
  - 已验证：唤醒消息注入 delivered（2026-08-30 20:31 实测）
- 巡检动作：扫 data/blueprint/ + data/iterations/ + data/progress/ + notes/mac-mini/ → 有停滞/信号才动作（写提醒卡/更新基准）
- 事件驱动补充：bb-sub 订阅（data/iterations/、data/blueprint/ 等前缀）→ ~/.dsh/inbox/bb/xingduo.jsonl，巡检时增量读取，不依赖星桥主动挂状态
- 防噪音纪律不变：巡检零外部噪音；无停滞不写卡；同项 24h 不重复；纯确认不往返

## 五、当前监督基准（v1.6 · 2026-08-30 用户拍板 M1 双路径）

- 蓝图：FlowerNet 主蓝图 v2.0 + stages（数字化 2.5/3.0，物理 2.0）
- 盯：d25-3（外卖→ERP 导入，运营/协调者）/ d3-1（端侧模型，i9）/ d3-2（智能体感知，运营）
- gate：3.0 端侧 ROI_eff>1
- **M1 双路径执行中**（决策：data/progress/decision-m1-path-20260830）：
  - **M1 核心验收达成 ✅**（2026-08-30 星桥 fa1f9150-m1-verdaccio-20260830）：
    - B1 ✅ Verdaccio 6.10.1 上线（4873 / launchd / Tailscale / dsh-publisher）
    - B2 核心 ✅ dsh-plugin-agent-way@1.4.0 发布 verdaccio + 纯包名 npm install 实测通过（70 包 peerDeps 自动解析 + 模块加载 OK）；npmmirror 不可发布根因解除
    - 踩坑三连已修：IPv6→0.0.0.0 / strict_ssl:false / publish 503→@scope 去 proxy
  - **M1 端侧验证 = 并行跟踪项**（星桥裁决 adopt，2026-08-30）：MBP 暂缓 / i9 待回报——继续跟踪不催办，验收债不滚大；A 路径 i9 git URL 验证为可选项
- **M2 启动推进**（星桥裁决 adopt，data/progress/m2-parallel-ruling）：
  - 剩余：P1-3d 消息签名（openssl 零依赖）+ 收尾；M2 验收 = 独立部署 + 设备注册
  - 已完成基础：genebank 恢复 ✅ / 设备注册 API ✅ / identity ✅ / token 认证 ✅ / SSE token ✅
  - 盯信号：P1-3d 完成 / M2 验收通过
- **纳入 15min 巡检**：每次扫 data/iterations/ 新增（m1-* / m2-* / P1-3d / 签名 / 端侧验证 / verdaccio 相关 key）+ changelog
- M2 验收通过 → 里程碑更新（M3：本地 LLM 零计费）；端侧验证通过 → M1 正式收官
- 基准变更时更新本文件第五节并 bump 版本
