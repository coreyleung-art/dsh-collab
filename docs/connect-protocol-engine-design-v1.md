# 连接实验室升级 v2 · 协作协议引擎设计（B 方案 MVP）

> 明鉴 v3 · 2026-09-06 · 用户裁决: 连线裁决后自动生成持续机制(非仅登记)
> 状态: 设计稿 v1(待用户确认形态后实现)
> 纪律: 三件套(文档+代码+依赖) · R030(无验证成功=未成功) · Φ8(两次即工具化)

---

## 〇、要解决的真问题

连线(confirmed)现在只是"关系声明"——两端知悉但不产生持续产出。
B 方案: 给边绑定**协作协议(protocol)**, 裁决后系统自动按协议节奏驱动两端干活, 形成持续产出闭环。

## 一、核心概念: 协作协议(ConnectProtocol)

```
一条已确认的边(如 验金石↔回声) + 一个协作模式 = 一个可持续运转的机制
```

### 协议字段(BP 式九字段)
| 字段 | 说明 | 例 |
|---|---|---|
| id | 协议 id | proto-qc-yanshi-echo-v1 |
| edge | 绑定哪条边(from/to) | 验金石↔回声 |
| mode | 协作模式 | qc(质量抽检) / relay(接力) / build(共建) |
| trigger | 触发节奏 | 事件驱动(回声每10条回复) / 定时(每6h) / 手动 |
| action | 触发后做什么 | 生成抽检任务 → 派验金石 → 验回报 → 回声收 |
| owners | 双方角色 | from=生产方(回声), to=验收方(验金石) |
| channel | 结果回写通道 | 黑板 data/protocols/<id>/runs/ + 通知两端 |
| gate | 约束门(R006#10) | 必须两端 agentId 真实 + 任务卡 schema |
| status | active/paused/archived | active |
| ts | 版本时间 | — |

### 三种模式(先做 qc, 后扩 relay/build)
1. **qc(质量抽检)**: 生产方产出达阈值 → 自动派验收方抽检 → 结果回报生产方
2. **relay(接力)**: A 完成上游 → 通知 B 接手下游(链式任务)
3. **build(共建)**: 双方各自产出 → 定期合并校验

## 二、MVP: qc 模式落地(验金石↔回声试点)

**业务场景(真实)**: 回声=智能客服自动回复, 验金石=QA 验收员。
协议: **回声每累计 10 条已发送客服回复 → 验金石自动抽检最近 1 条(质量/合规) → 结果回报回声 + 明鉴记录**

### 触发链(事件驱动, 复用现有资产)
```
回声 im-duty-sse(已在跑) → 发送成功事件 → 计数器 data/protocols/proto-qc-*/counter
    ↓ 每满 10
bb-protocol-runner.py(新) → 生成抽检任务卡 data/protocols/*/tasks/<ts> (schema门)
    ↓ 派发
通知验金石(黑板 notes/ffb7c3ab/ + agent_send) → 验金石验收(复用其 QA 流程)
    ↓ 回报
结果写 data/protocols/*/runs/<ts> → 通知回声 → 计数器清零 → 循环
```

### 组件清单(三件套)
| 组件 | 形态 | 依赖 |
|---|---|---|
| bb-protocol-register.py | CLI: 注册/暂停协议(边→协议绑定) | 黑板 + confirmed.json |
| bb-protocol-runner.py | CLI: 事件计数/阈值触发/任务卡生成 | 读回声发送事件 + 黑板写 |
| 协议数据 | data/protocols/<id>/{config,counter,tasks,runs}.json | 黑板 |
| RULE | R-ERR4 相邻: 协议规范(写入=runner/读=双方) | 规则账本 |

### 验证(R030)
- 注册协议 → 注入 N 条回声发送事件 → runner 满 10 → 验金石收到抽检卡(黑板+agent_send 实测)
- 验回报 → 回声收到结果 + 计数器重置 → 循环可复跑

## 三、与现有机制关系(不重复造)
- 回声发送计数: im-duty-sse 已有发送事件 → 只加计数器读取(不改其引擎)
- 验金石验收: 已有 QA acceptance 流程 → 抽检卡指向其标准流程
- SystemGraph: 连线 UI 增加「绑定协议」步骤(评估后选 mode → 注册), 图显示⚙协议边
- 触发调度: 本地 sysops-cron(守灯塔) 或 launchd 每 5min 查计数器(轻量)

## 四、风险与门
| 风险 | 缓解 |
|---|---|
| 自动抽检打扰验金石 | 抽检卡标 priority, 验可批量/延迟处理 |
| 计数器漂移 | runner 幂等(已处理 runId 去重) |
| 协议空转(无真实产出) | 周复盘看 runs 数, 0 产出协议自动 warn |
| 范围膨胀 | MVP 只做 qc+1 条边, 验证后再扩模式/边 |

## 五、分阶段(防上下文爆炸)
- P1(MVP 1-2h): 协议 schema + register/runner 最小实现 + qc 1 条边(验金石↔回声)事件计数验证
- P2: SystemGraph UI「绑定协议」+ 图上协议边标记
- P3: relay/build 模式 + 多边扩展
每阶段用户确认 + 验证后才进下阶段(Φ6 理论先行/最小化)

---
*设计 v1 · 明鉴 · 2026-09-06*

## P1 实现状态(2026-09-06 沙箱试跑完成 ✅)
- bb-protocol-register.py / bb-protocol-runner.py 已实现(源码 ~/dsh-collab/scripts/, 均带 --lean4-check + AST 护栏: 零真实发送)
- 协议 proto-qc-echo-yanshi (active): from=回声(生产) → to=验金石(验收), threshold 10
- 沙箱验证(R030): MOCK 注入 10 → 任务卡生成 → 通知验金石域(notes/ffb7c3ab/, notify_delivered=True) → 计数重置; runs=1
- 护栏实证: runner AST 检查无任何 im_send/发送调用; 全程零真实客户消息
- 修复记录: 短id解析(session- 后首段) / 黑板慢响应回读确认 / notify 状态回填任务卡 / qc 语义 from=生产 to=验收

## P2 待办(SystemGraph UI 绑定协议 + 协议边标记)
## P3 待办(relay/build 模式 + 真实事件接入: 回声 im-duty-sse 发送计数)
