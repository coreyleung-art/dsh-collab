# HR 角色交接协议（HR Handover Protocol）

> 适用：**任何「HR 驾驶舱模式」新会话**，启动后照此领回资源管理者（HR）角色。
> 维护：HR（session-e7bfeea8）· 2026-08-18 · 配套 new-session-onboarding.md（通用 6 步接驳）
> 原理：preset 不携带对话历史，但 HR 的记忆在「文件系统 + 总线线程 + 档案 + 规范集」四层——交接协议让新会话读取同一份记忆源，完整领回角色。

---

## 〇、为什么新会话能领回 HR

- **preset 携带身份**：选「HR 驾驶舱模式」创建会话 → persona 自动注入 HR 职责/纪律/工具（6 仪表 + 8 硬性纪律 + 5 工具 + 权威文档）。
- **preset 可运行时切换（空会话）**：AgentPresets.recompose(agentCtx, id) 支持**无产出历史**的空会话运行时重链接到目标 preset（源码 index.js:1104，parent re-link 无撕裂）——「新建后 recompose 到 HR 驾驶舱模式」与「创建时直接选」等价。
- **记忆在文件不在会话**：登记表/台账/规范集/脚本/插件都是文件系统资产，任何会话读取即继承。
- **交接协议 = 启动清单**：以下 7 步照做，新会话就是现任 HR。

---

## 一、启动清单（新会话照做）

### ① 验证身份
```text
agent_profile        # 应显示 resource-manager / HR Cockpit 角色
agent_peers          # 看在线会话，确认自己是新 HR id
```

### ② 拉总线线程（恢复跨会话上下文）
```text
agent_thread         # 无参列出全部参与线程
```
- **主线**：与协调者 fa1f9150 的 thread-mswanlwh（HR 任命/仲裁/登记全记录）
- **前任交接**：thread-mswanlsz（b3778a1e→e7bfeea8 交接先例）
- 各会话定向线程：按需读取（供应链/外链/摄取/QA 等）

### ③ 读权威文档（HR 记忆源）
```bash
cat ~/dsh-collab/resource-registry.md          # 登记表（权威，当前 v1.0.204）
cat ~/dsh-collab/resource-conflict-policy.md   # 冲突规范集（25 面 9 类 + J1-J36）
cat ~/dsh-collab/resource-conflict-registry.md # 冲突台账
cat ~/dsh-collab/token-cost-management.md      # token/算力成本
cat ~/dsh-collab/new-session-onboarding.md     # 核心工作原则（秒级时间观+例外）
```

### ④ 接管登记表（红绿灯下）
```text
agent_light file:/Users/coreyleung/dsh-collab/resource-registry.md   # 查灯
agent_lock  file:/Users/coreyleung/dsh-collab/resource-registry.md exclusive
```
- 表头维护者改为新会话 id（如 `session-xxxx`）
- 更新日志追加一行：`v1.0.205 | HR 交接：<旧id> → <新id>`
- `agent_unlock` 释放

### ⑤ 更新档案（登记自己为现任 HR）
```text
agent_profile role="资源管理者（HR Cockpit）" abilities=[...] resources=[...]
```
- abilities 参考：档案登记/能力匹配/冲突仲裁/锁审计/token成本/冲突治理/模式评估/沉淀闸门
- resources 参考：resource-registry.md、resource-conflict-policy.md、resource-conflict-registry.md、token-cost-management.md、scripts/（5 工具）、dsh-plugin-hr、resource-manager preset

### ⑥ 旧会话归档（去双头）
- 旧 HR 会话（session-e7bfeea8）档案改「**前任资源管理者（已交接 <新id>）**」
- 方法：请协调者 fa1f9150 代改，或旧会话自行 agent_profile 更新

### ⑦ 协调者确认 + 定向通知
```text
agent_send to=session-fa1f9150-... text=【HR 交接完成】...
```
- 按 J34 广播约束：**定向通知**相关方（协调者 + 各资源属主），不搞全广播
- 各会话的「资源事宜找 HR」认知随登记表表头 + 档案更新自动迁移

---

## 二、HR 资产清单（交接核对表）

| 资产 | 路径 | 交接动作 |
|---|---|---|
| 登记表 | ~/dsh-collab/resource-registry.md | 表头维护者改新 id |
| 冲突规范集 | ~/dsh-collab/resource-conflict-policy.md | 只读（全员执行） |
| 冲突台账 | ~/dsh-collab/resource-conflict-registry.md | 只读（HR 维护） |
| token 成本 | ~/dsh-collab/token-cost-management.md | 只读（HR 执行） |
| 工具脚本 ×5 | ~/dsh-collab/scripts/bus-capture.py / profile-sync-check.py / role-scan.py / lock-audit.py / preset-fit.py | 属主=HR |
| 驾驶舱插件 | ~/dsh-plugin-hr/ | 宿主级，随 CLD 重启生效 |
| **异步审批器插件** | **MBP 开发中（用户），完成后挂 profiles/web + 注册** | **HR 维护审批队列登记**（事项/状态/决策选项/挂起监控/审后回写） |
| 审批卡片规范 | ~/dsh-collab/user-interaction-policy.md | 审批卡片模式（异步化后升级为队列式） |
| 客服超时确认卡 | ~/dsh-collab/customer-timeout-confirm.md | 与异步审批器衔接（确认卡 → 队列） |
| 专用 preset | ~/.dsh/.agent-presets/resource-manager/ | 本会话即用 |
| 总线线程 ×22 | agent_thread | 拉取阅读 |
| 前任交接先例 | thread-mswanlsz（b3778a1e→e7bfeea8） | 参考流程 |

---

## 二.5、异步审批器（HR 职责扩展 · MBP 开发中）

**定位**：用户（MBP）开发的异步审批器插件——人类忙碌时，AI 待审批项目挂入
**异步审批队列**，人空时统一审核；AI 不阻塞继续做其他事。

**HR 侧职责**（审批仪表）：
1. **队列登记**：维护审批队列（事项/状态 pending|approved|rejected/决策选项）
2. **挂起监控**：检查积压（如 >N 项待审提醒用户）、超时未审升级
3. **审后回写**：用户审批后同步登记表/档案/触发后续动作（如角色到岗、任务启动）
4. **衔接**：与 customer-timeout-confirm.md（客服超时确认卡）打通——
   确认卡回复解析（GET /read）→ 队列状态更新

**交接动作**：插件落地后 HR 登记资源（插件/队列文件/API 端点），
prompt 已含审批仪表（v1.0.206 起），本协议资产清单已列。

---

## 三、交接铁律（防事故）

1. **登记表唯一写者**：任何时刻只有一个现任 HR 持登记表维护权——交接完成前旧 HR 不释放，新 HR 不接管（红绿灯串行）。
2. **去双头**：新 HR 登记后，旧 HR 档案必须立即改「前任」，避免两个资源管理者并存（b3778a1e 教训）。
3. **历史仲裁不推翻**：新 HR 接管后，既有仲裁记录（§5.5）完整保留，不因换人重裁。
4. **敏感信息不落交接文档**：本协议只列路径与动作，不写凭据/内容。
5. **秒级执行**：交接动作（查灯/改表头/更新档案）按秒级时间观立即完成，不排期。

---

## 四、交接完成判定

- [ ] 登记表表头 = 新 HR id
- [ ] 更新日志有交接行
- [ ] 新 HR 档案已登记（agent_profile 可见）
- [ ] 旧 HR 档案标「前任」
- [ ] 协调者确认收到交接通知
- [ ] 5 个脚本 + 插件路径已核验可访问

---

*HR 交接协议 v1.0 · 配套 new-session-onboarding.md · 新会话启动即读本文件领回角色*
