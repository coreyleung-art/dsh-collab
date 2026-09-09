# 自动化恢复决策表 v1.0

> 生成：2026-08-23 · 协调者 fa1f9150 · 依据：launchd 实况 + registry 登记 + 成本停令背景
> 用途：成本停令解除后，逐项决定哪些自动化「立即恢复 / 带门禁恢复 / 继续停 / 归档」

## 一、现状实况（实测，非记忆）

| 项 | 实测值 |
|---|---|
| LaunchAgents plist 总数 | 39 个（dsh/external-link/media/waimai/sysops 相关） |
| launchctl 已加载 | **0 个**（成本停令：全部未加载） |
| blackboard-server 8792 | ✅ nohup 在跑（PID 8360），非 launchd |
| bus-bridge 8791 | ⚠️ **进程没了**（外联以为常驻，实际未加载）——i9 指挥依赖它，需核实 |
| node-agent / event-bus / blackboard-subscribe | ❌ 未跑 |

> ⚠️ 关键偏差：外联 92623479 自报「桥侧 8791 已 launchd 常驻」，但实测 launchctl 0 加载 + 进程不存在。恢复时需先核实 8791 的真实状态。

## 二、分类标准

| 轴 | 判断 |
|---|---|
| 成本 | 本地零订阅（纯规则/本地模型）= 低成本；调订阅 LLM = 高成本 |
| 稳定性 | 写共享资源/有崩溃风险 = 需门禁；只读巡检 = 稳定 |
| 价值 | 直接支撑「知识复利 / 节点指挥 / 值班投递」= 高价值；纯报告类 = 低价值 |

## 三、A 类 · 立即恢复（零成本 + 高价值 + 稳定）

> 恢复自动化时第一批拉起，不消耗订阅 token。

| plist | 功能 | 恢复理由 |
|---|---|---|
| com.external-link.bus-bridge | 总线桥 8791（节点指挥） | **i9 节点指挥核心**，MBP 闭环依赖，零 LLM |
| com.external-link.mcp | MCP 8910（带 token） | **i9 接入**，外联侧已就绪 |
| com.dsh.hr.blackboard-server | 黑板 8792 | i9 节点注册/心跳中枢（已在 nohup，补 launchd 常驻） |
| com.dsh.hr.node-join-notify | 节点上线/下线告知 | i9 节点接入自动告知（阶段 2.4），零 LLM |
| com.dsh.hr.event-bus | 事件总线消费（值班投递） | S6 放行例外，值班投递核心 |
| com.dsh.hr.kb-health.daily | KB 健康巡检 | 零 LLM，自动验证向量化 |
| com.dsh.hr.kb-incremental.daily | KB 增量索引 | 零 LLM，知识复利 |
| com.dsh.hr.rules-sync | 规则向量化同步 | 零 LLM（mtime+sha 幂等） |
| com.external-link.wecom-inbox | 企微监听 | 外联维护，客服/消息路由 |
| com.external-link.digest | P2 digest 汇总 | 外联维护 |

## 四、B 类 · 带门禁恢复（有成本或需确认）

> 恢复但挂成本门禁（任务级分档 + 全局熔断）。

| plist | 功能 | 门禁 |
|---|---|---|
| com.dsh.hr.daily-brief | 每日简报企微推送（22:00） | 用户已批准，单次 LLM 摘要，挂 cost_cap |
| com.dsh.waimai.daily-bad-review | 差评采集 | 外卖已放行 |
| com.dsh.waimai.observe-review | 评价观察 | 外卖已放行 |
| com.waimai.learning-daily | 外卖学习日报 | 外卖已放行 |

## 五、C 类 · 继续停（报告类 / 低价值 / 高成本）

> 纯报告类，停着省钱，需要时手动跑。

| plist | 功能 | 停的原因 |
|---|---|---|
| com.dsh.hr.token-roi.daily | token ROI 日报 | 报告类，消耗 LLM，非刚需 |
| com.dsh.hr.cahac-replay.daily | CAHAC 重放日报 | 报告类 |
| com.dsh.hr.cahac-replay.weekly | CAHAC 重放周报 | 报告类 |
| com.dsh.hr.approval-tier.daily | 审批分级日报 | 报告类 |
| com.dsh.hr.waimai-audit.daily | 外卖审计日报 | 报告类 |

## 六、D 类 · 归档（重复 / 历史遗留）

> sysops 与 cron 两组重名，需确认哪组是现行、哪组废弃。

| plist 组 | 情况 | 处理 |
|---|---|---|
| com.sysops.*（6 个：health/intel.collect/kb.watcher/lm.memory-guard/plugin-scan/waimai.watchdog） | 与 com.dsh.cron.* 完全重名 | 疑似旧版，待确认后归档 |
| com.dsh.cron.*（6 个，同名） | 与 com.sysops.* 完全重名 | 疑似新版（v1.0.328 cron #28），待确认 |
| com.dsh.waimai.review-group.daily | v1.0.319 已停用（HR 侧改 aa528267 侧） | 归档 |
| com.dsh.bus-capture | 总线捕获（历史） | 待确认是否仍需要 |

## 七、恢复顺序建议

```
第 1 批（i9 节点指挥，零成本）：bus-bridge 8791 + mcp 8910 + blackboard-server 8792 + node-join-notify
第 2 批（知识复利 + 值班，零成本）：event-bus + kb-health + kb-incremental + rules-sync
第 3 批（带门禁）：daily-brief + 外卖差评类
继续停：token-roi / cahac-replay / approval-tier / waimai-audit（报告类）
归档：sysops vs cron 重复组 + review-group.daily + bus-capture（待确认）
```

## 八、待用户拍板项

1. bus-bridge 8791 真实状态核实（外联说常驻 vs 实测进程没了）
2. sysops vs cron 重复组：哪组现行、哪组归档
3. 第 1/2 批（零成本）是否立即恢复
4. 第 3 批（带门禁）的门禁阈值

---
*自动化恢复决策表 v1.0 · 协调者 2026-08-23 · 待用户逐项拍板后交 HR 执行*
