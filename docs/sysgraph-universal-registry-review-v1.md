# SystemGraph 通用注册表评估 · 明鉴评审 v1.0

> 明鉴 v3 · 2026-09-06 · 应星桥请求(用户设想: SystemGraph=强制注册表+门锁编排登记表)
> 对照: comm-server/sysgraph-universal-registry-eval.md(星桥)

---

## 〇、总评

**✅ 方向成立, 底子比我预期还好** —— mechanism.json 原生 {protocols(7)/gates(7)/locks(5)/links(13)} 确是我 v2 设计 SystemGraph 时内置的"注册+编排"骨架(星桥评估准确)。SystemGraph 生来是编排总账型, 非事后扩展。

## 一、三问评审

### ① 实施可行性
**✅ 可行**, 且比一般注册表项目低风险——因为:
- 底子已内置: mechanism 门/锁骨架 + hardware-nodes(70节点) + gate_health(刚建)
- 哲学同源: "注册中心化 + 执行去中心化" = E2/R031 一致(不是推倒重来)
- 分散源都有既有载体(E2/agent_profiles/红绿灯/罗盘) → SystemGraph 做**读侧汇聚**, 各源保持自治写
- 关键风险(高可用)已识别: SystemGraph 本机随 CLD 重启 → 数据源双写 + 读侧重建(星桥方案正确)

### ② E1(mechanism 门锁编排补全) 是否启动
**✅ 启动**, 且 E1 正是我上一轮"门健康"工作的自然延伸:
- 已完成: gate_health(75规则/24结构/51纸面) + mech-graph 门健康节点 + rj4-4 审计流
- E1 补: bb-gate 五门/lean4 工具门 → gates 骨架; 红绿灯持锁 → locks 骨架
- **规模适中**: 门 7→~15(补 bb-gate 系), 锁 5→~10(补红绿灯/自动化开关); ~1-2h 数据接入 + 展示
- E1 产出即兑现用户设想第一步(门锁编排登记可见)

### ③ 分阶段(E1→E2→E3) 合理性
**✅ 合理**, 建议微调节奏:
- E1(近): 门锁编排补全 —— 建议**先做**, 规模小价值直接(我承接: 已在做门健康, 可续到 bb-gate/lean4 门接入)
- E2(中): 设备+agent 注册汇聚 —— 依赖罗盘 step4 会话级(其进行中), 建议 E1 完成后衔接
- E3(远): 强制注册协议 —— 真正大工程(schema/端侧), 建议 E1+E2 价值验证后再启动, 且强注册需配回滚/豁免(非全强制, 分类型: 工具/插件强制, 一次性脚本豁免)

## 二、架构补充建议(明鉴视角)

1. **注册 schema 分层**(E3 前定稿):
   - device(身份): hardware-nodes + E2 → id/os/ip/在线
   - agent(能力): agent_profiles → id/role/abilities
   - tool/plugin(工具): business-asset-map → 名/域/门状态
   - gate(门): mechanism.gates → id/类型/覆盖规则/lean4状态
   - lock(锁): mechanism.locks → id/资源/持有者/模式(红绿灯实时态可选接入)
2. **写权边界**: SystemGraph = 读侧汇聚总账 + 门锁定义权威; 各源(agent_bus/红绿灯/E2)= 运行时写 → 避免 SystemGraph 成写瓶颈
3. **高可用落地**: 关键元数据(门锁定义)双写本机+服务器; 运行时锁状态(红绿灯)按需拉取非实时镜像(降频)
4. **对齐 gate 工具族**: E1 的 gate 接入 = 复用 gate-auditor 识别(纸面门标注) + rj4-4 审计流 → mechanism 展示, 全链已通

## 三、结论

- **评审通过**: 方向/可行性/E1 启动/分阶段 均认可
- **明鉴承接**: E1 门锁编排补全(续门健康工作: bb-gate 五门 + lean4 工具门入 gates, 红绿灯锁入 locks)——规模 ~1-2h 数据+展示
- **协调**: 星桥(E2/E3 规划) + 罗盘(step4 会话级= E2 依赖) + HR(注册 schema 定稿 R008?)

---
*评审 v1.0 · 明鉴 · 2026-09-06 · 认可并承接 E1*
