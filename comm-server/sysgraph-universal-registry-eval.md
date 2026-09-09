# SystemGraph 扩展为通用注册表 + 门锁编排登记表 · 评估（2026-09-07 星桥）

> 用户设想: SystemGraph 是否可扩展为「面向所有智能体/设备/工具插件/功能的强制注册表 + 门和锁的编排登记表系统」

## 一、关键事实（底子比预期好）
mechanism.json 原生结构 = {protocols, gates(7门), locks, links}——**SystemGraph 设计时已内置门锁编排骨架**
hardware-nodes.json（设备注册 70 节点）+ business-asset-map.json（能力/工具资产）+ mechanism.gates（门健康，刚加）

## 二、分散注册源现状（待统一进 SystemGraph）
| 源 | 内容 | 位置 | 现状 |
|---|---|---|---|
| E2 发现层 data/discovery/agents | 设备+会话在线 | 服务器(24h) | R-ERR4 规范 |
| agent_profiles | 智能体能力登记 | mac-mini | 分散 |
| 红绿灯 agent_lock | 资源锁状态 | agent-bus 插件 | 无登记表 |
| mechanism.gates | 门健康(75规则) | SystemGraph | 刚建 |
| gate-auditor/repairer | 纸面门审计/加固 | 规则账本 | 星桥主理 |
| 罗盘 device-assets | 设备资产 | 罗盘 | 会话级扩展中 |

## 三、用户设想的价值（成立）
1. **单一事实源**：谁存在(设备)/谁在线(会话)/有什么能力(agent)/什么门锁它(gates/locks)/状态(健康)——统一查询/审计/编排
2. **门锁编排表**：mechanism.gates 已有 7 门骨架——扩展为全部门(bb-gate五门/lean4工具门/纸面门加固流)+全部锁(红绿灯持锁)的登记+编排
3. **强制注册协议**：新增设备/插件/能力 → 注册 SystemGraph → 全局可见可查（E2 已证注册模式可行）

## 四、架构设计（推荐）
```
SystemGraph = 编排总账(主视图/汇聚层)
├─ hardware-nodes  ← 设备注册(已有) + E2 服务器设备会话(接入)
├─ mechanism.gates ← 门编排(已有7) + bb-gate五门/lean4工具门/纸面门状态(扩展)
├─ mechanism.locks ← 锁编排(已有) + 红绿灯持锁状态(接入 agent_lock)
├─ business-asset-map ← 能力/工具资产(已有) + 插件运行注册(扩展)
└─ 统一注册协议: 各源(E2/agent_bus/插件/红绿灯) → 上报/拉取 → SystemGraph 汇聚

分层原则: 注册/登记中心化(安全) + 消息/执行去中心化(自治) —— 与 E2 同哲学
```

## 五、风险与门
1. **高可用**: SystemGraph 本机随 CLD 重启——强制注册表若依赖本机=单点。缓解: 数据源(E2/agents 在服务器)双写, SystemGraph 读侧聚合(重启可重建)
2. **范围工程**: 全类型强制注册=大工程(schema/协议/端侧接入)——分阶段
3. **注册 vs 自治张力**: 强制注册不剥夺执行自治——注册是"声明存在", 执行仍各端本地(R031)
4. **schema 统一**: 需统一注册 schema(设备/agent/工具/门/锁各类型)

## 六、分阶段建议
- E1(近): mechanism 门锁编排补全——bb-gate五门/lean4门/红绿灯锁接入 mechanism(骨架已有)
- E2(中): 设备+agent 注册汇聚——hardware-nodes + E2 服务器 + agent_profiles 统一视图
- E3(远): 强制注册协议——插件安装/新设备/新能力自动注册 SystemGraph + 校验(R006)

## 七、结论
✅ **方向成立且底子已有**(mechanism 原生 gates/locks)——SystemGraph 生来是"注册+编排"型(明鉴设计时就内置门锁概念)
🔧 缺口: 分散源未汇聚 + 全类型覆盖 + 锁状态接入 + 高可用
📋 推荐: 分阶段演进(E1 门锁编排补全先行), 不推倒重来——SystemGraph 作汇聚总账, 各源保持自治(注册中心化+执行去中心化)
