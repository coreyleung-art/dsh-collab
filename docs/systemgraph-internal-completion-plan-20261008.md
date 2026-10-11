# SystemGraph 内部功能补全与端到端跑通规划（2026-10-08 · 星桥 · R048 送审版）

> 用户指令：同步规划把系统架构管理器内部完整功能补充和跑通。
> 流程：本方案先行送审（R048，audit-reviewer），裁定通过后与属主（明鉴 session-a190c54c，离线排队）对齐实施。

## 一、现状基座（2026-10-08 实测）

| 件 | 现状 | 缺口 |
|---|---|---|
| 后端 bb-blueprint-gallery.py v1.4.0（8798） | 31 个只读端点（overview/blueprints/agents/relations/rules/philosophy/versions/assets/biz-assets/system-assets/hardware/cap-perm/connect-lab 等） | 无写端点；数据靠静态快照（83 张） |
| 前端 index.html（146KB 壳） | 只读可视化 | 无编辑/无 diff/无推荐交互 |
| 数据层 gallery 目录 | 21 蓝图 · 53 边 · **76 智能体（2026-10-08 实测）** · 19 版本 · 孤岛 26 / 穷举候选 767 / 接口返回 60 | 非实时 |
| 壳 | macOS（com.coreyleung.systemgraph）+ iOS（.ios）已注册 ASC | 壳指向静态包，未接实时后端 |
| 基建可复用 | 黑板 SSE（8803，?nodes= 过滤）、R046 验收门、双仓已建 | — |

## 二、补全清单（功能 → 实现要点 → 验收）

### A 组 · 数据实时化（跑通的第一道关）
1. 后端加订阅：SSE 客户端订阅黑板 data/ 与 notes/ 相关键（复用星台桥同款链路），变更触发内存模型更新 + 版本号自增
2. 快照退居备份位：实时模型为主，定时快照仅做归档（现有 83 快照机制保留）
- 验收：改黑板一张 agent 卡 → 10s 内 /agents 反映变化；断连重订阅不丢事件（游标/ts 续传）

### B 组 · 蓝图编辑与版本治理
3. POST /blueprints/<id>（编辑，校验 schema + 必填字段），PUT 版本自增；DELETE 软删（加 retired 标记）
4. POST /blueprints/<id>/review → 生成 R046 声明体草案（proposer=明鉴/executor=编辑者/adjudicator=审查员），待裁定后生效发布
5. 前端双栏 diff 视图（19 版本数据模型已有）
- 验收：编辑→版本+1→diff 可看；无 review 的变更不进入对外视图（草稿态隔离）

### C 组 · 孤岛推荐引擎
6. POST /connect-lab/score：按实现 5 特征打分排序返回（实测口径：孤岛 26 / 穷举候选 767 / 接口返回 60）
7. 一键建边：确认后写 confirmed-links + 版本记录
- 验收：推荐 top10 里人工盲评 ≥60% 有意义（明鉴判定）；建边幂等

### D 组 · 能力体检与风险视图
8. GET /cap-report：65 agents 的能力冗余/缺口矩阵（cap 分布直方 + 无人覆盖的 cap 清单）
9. GET /risk-report：单点依赖（某资源独占边=1 条）、扇入/扇出热点、权限越界（perm 边超出声明域）
- 验收：两个报告各自带 --selftest 负控（造异常数据必红）

### E 组 · 壳对齐与跑通
10. macOS/iOS 壳 baseURL 切实时后端（星台 BridgeConfig 同款双 URL + fallback）
11. 端到端链路：黑板写入 → 后端 → UI → 壳，全链验收清单落卡

## 三、跑通顺序（依赖序）

```
A(实时) → B(编辑/版本) → C(推荐) → D(体检/风险) → E(壳对齐)
```
A 是基座；B/C/D 在 A 上叠加；E 最后打通壳。每步含 selftest + 负控（检查通过≠被检验纪律）。

## 四、分工与治理

- 属主：明鉴（主源架构师）——实施主体；星桥协调 + 送审；审查员裁定（R048）
- 每一步的「通过」声明按 R046 过门（surface_measured 条目级实测清单）
- 后端新增写端点属通道变更 → 过 channel-gate（R036）登记

## 五、风险与前置

- 后端单进程（8798）：订阅逻辑加内存上限（事件缓冲有界），防 OOM（中央板前车之鉴）
- 黑板键写权限：写 confirmed-links 走 bb_put 门 + 回读断言
- 明鉴离线：实施排队；本方案仅为送审稿，不代属主动工（R006 §8）

## 六、验收总判据（跑通的最终定义）

1. 黑板改数据 → UI 10s 内可见（A）
2. 一次完整编辑流：编辑→版本+1→送审→裁定→发布→diff 可见（B）
3. 孤岛推荐一轮真实使用，建边 3+ 条且无误报（C）
4. cap/risk 两份报告产出且负控全红（D）
5. macOS 壳打开即见实时数据，iOS 壳同（E）

## 八、实测更正（2026-10-08 明鉴主源复核，取代旧快照数字）

> 原方案数字取自 2026-09-15 静态导出快照（README 规模行）——已过期。以下为实测当前值，判据一律以实测为准。

| 组 | 原方案（错） | 实测（明鉴） | 修订 |
|---|---|---|---|
| C 组 | 588 候选·三路打分（名称相似度/能力重叠/权限边） | 孤岛 26 · 穷举候选 767 · 接口返回 60；实现为 5 特征打分 | 打分特征对齐实现（5 特征），候选口径=接口返回 60 |
| D 组 | 65 agents 能力矩阵 | 76 agents；466 ability 中 460 单例 | 先 ability 归一化，再出冗余矩阵（否则假读数） |
| B 组 | 19 版本双栏 diff | 19 版本属实，但是 changelog 事件流非内容快照 | diff 需引入内容快照机制（版本流 ≠ 快照） |
| E 组 | 双 URL fallback | 属实 ✓ | 无修订 |

- 连带修订：A 组真源 76 profiles（agent-bus.json），非 65。
- 文件监听元组 (mtime,size,ctime)；SSE 水位线=已消费最大 id；/sse-stats 不可得→自建计数。
- 待裁判裁定后定稿 v3。

## 九、B 组范围最终定稿（2026-10-08 明鉴两轮更正后）

- 修复对象 = 黑板卡 `data/blueprint/versionlog`（v12）的**流程层**：自 09-07 起停写（19 条跨 08-30→09-07），恢复写入流程。
- 明确**不在范围**：①「9 条 src 断链」——撤回（那 9 个值是黑板键不是路径，实测 9/9 存在 200 且真内容；明鉴自更：核错了域）②version-map.json——渲染状态缓存，versions:{} 设计如此。
- diff 内容基准 = 一版一文件（blueprint-<id>-v<X.Y>.md）。

## 十、裁判有条件通过的 4 项前置整改（2026-10-08）

① **声明体**：audits/20261008/r048-systemgraph-claim.json（surface_measured/unmeasured 齐备，经门）。

② **C 组机器可核下界**（替换「人工盲评 60%」）：
- 离线评估（防泄漏版）：以 confirmed-links 为 ground truth，**按时间留出最近 20% 作 hold-out 测试集**；该 20% 不参与特征构建、不参与候选生成；recall@60 ≥ 0.5 只在 hold-out 上计（机器可核、可复跑）
- **复跑手段（不是声称）**：`python3 ~/dsh-collab/scripts/holdout-split.py --input <confirmed-links.json>`
  · 排序字段显式声明：`ts` → `confirmed_at` → `created_at` → `updated_at`（缺失者显式计数 untimed，不假装已排序）
  · 输出：total/train/holdout + `holdout_digest`（同输入两次一致 ⇒ 可复跑）+ holdout_ids
  · 自检：`python3 ~/dsh-collab/scripts/holdout-split.py --selftest`（6 例，含 3 条负控：空输入报错 / 无时间字段显式计数 / 同输入指纹一致）
  · v1.0.0 · 依据：裁判 2026-10-08 复核「『可复跑』是声称而非手段」
- **实跑输出（2026-10-08，星桥执行）**：
  · A) 真实数据源 `~/Desktop/SystemGraph-本地文件化/api/confirmed-links.json`（导出快照）：
    `ERROR: 无记录（检查 --input 是否为 confirmed-links 形态）` rc=1
    ⇒ **该数据源当前 0 条**（hold-out 与 recall@60 目前**无法在真实数据上计算**；这是 C 组实施前的真实前置缺口，不是脚本问题——脚本对空输入报错而非静默返回空划分）
  · B) 机制演示（20 条样本，**明确非真实数据**）：
    `total=20 train=16 holdout=4 ratio=0.2 · time_field_used={'ts': 20} untimed=0 · holdout_digest=e87f8d95a9994d63 · holdout_ids=L16..L19`
- **前置结论（供裁判/属主）**：C 组的机器可核下界需要 confirmed-links 有真实数据；当前为 0 ⇒ 实施时须先补数据或改用可见的 ground truth（否则 recall 判据在空集上无意义）。
- **★ C 组实施前置条件（显式登记，2026-10-08 裁判建议单列）：数据源 ≥ N 条**
  · 现行状态：**数据源 0 条 ⇒ recall@60 不是「未测」，而是「无条件可测」**（手段就绪 ≠ 数据就绪）
  · 穷举证据（可复跑，2026-10-08）：
    - `~/Desktop/SystemGraph-本地文件化/api/confirmed-links.json` 存在，`links` 条数 = **0**
    - `~/dsh-collab/data/blueprint/{gallery/,}confirmed-links.json` **均不存在**
    - 板端键 `data/blueprint/confirmed-links` / `data/connect-lab/confirmed` / `notes/mac-mini/confirmed-links` **均 404**
    - 后端 API `http://127.0.0.1:8798/api/confirmed-links` → `{"links": []}`
  · 前置门槛建议：**N ≥ 50**（recall@60 在更小样本上无判别力）；达门槛前 C 组的机器下界判据标记「无条件可测」而非「未测」。
- 先验/后验拆分：hold-out recall = **先验门**（离线可复跑）；上线采纳率 = **后验观测**（不作门，仅报告）
- 上线指标：推荐被采纳（写 confirmed-links）的比例 30 天 ≥ 20%（数据源=confirmed-links 卡，机读）

③ **B 组写端点三件**：
- 授权：写端点要求 Bearer board-token + 调用者身份登记（写卡留痕 author）
- 回滚：软删（retired 标记）+ 版本可回退（POST /blueprints/<id>/rollback?to=<v>）
- 幂等：同内容重复 PUT 返回同版本号，版本不自增

④ **A 组计数对账**（不丢事件的机器判据）：
- SSE 事件序号连续性检查（水位线 id 单调递增，跳号即告警）
- 每 10 分钟全量对账：模型内计数 vs 板端枚举计数，不等即报「丢事件」

### 十·补 C 组机器判据补全（裁判 c2 fix_suggest 全量采纳）
- 推荐边两端实体必须存在且未被硬删（否则判据 FAIL）
- 不得推荐已存在的边（重复边拒绝）
- 同一请求幂等：重复调用结果一致
- 返回条数有界（≤ 接口返回 60 的上界不放大）
- 单特征退化下界：仅用任一单特征时的 recall@60 也须 ≥ 0.3（防多特征掩盖单特征失效）

## 十一、A 组 v2 裁定落实（2026-10-08 裁判）

- ✅ 双通道保留（文件写入通道=明鉴 09-28 依赖的工作流不破坏）；术语澄清：**双通道/双触发**（两种触发方式）≠ **双写**（写两个板实例）
- 前置1：文件监听元组 = (mtime, size, ctime)（cp -a/cp -p/rsync -a 保 mtime 的静默写必须可见）
- 前置2：**权威源单一** = 后端内存模型（初始化时由文件全量加载；文件变更与 SSE 事件都只作「触发重读」信号，不以事件载荷直接改模型）
- 前置3：验收逐路四条——①黑板写 ②普通文件写 ③保留 mtime 写（cp -a）④原子 rename——每路单独断言 10s 内反映；四路全过才算 A 组验收通过
- 明鉴 401 修复（Bearer blackboard-token）采纳入实施

### 十一·补 A 组实现层两条（裁判 2026-10-08）
- 补1：**轮询间隔 < 10s 且留余量**（最坏时延 = 间隔 + 处理时间；任一路 ≥10s 则该路必然失败且只在验收暴露）。
  ★ 2026-10-08 裁判更正：**主路径事件驱动 ≠ 兜底路径免约束** —— 兜底轮询仍在，其间隔**同样须 <10s**；
  若确要放宽，**必须显式声明事件驱动路径具备独立丢失检测**（SSE 序号连续性 / 心跳缺口告警），
  否则即「用主路径的性质豁免兜底路径的要求」——而兜底存在的理由恰恰是主路径会失败。
- 补2：**逐路记录结果**——四路各记 pass/fail + 实测时延，禁止只报总失败（四路失效原因各不相同，聚合失败无法定位）。
- 注：第③路「保 mtime 写」即验证 ctime 生效那条（裁判确认设计到位）。
