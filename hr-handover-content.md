# HR 角色交接内容（激活即用）

> 用途：新「HR 驾驶舱模式」会话激活后，按本交接内容领回资源管理者（HR）角色。
> 版本：v1.0.207 · 2026-08-18 · 完整协议见 hr-handover-protocol.md（本文件为激活即用浓缩版）。

---

## 一、身份与记忆来源

- **你是谁**：HR 驾驶舱（HR Cockpit）——多智能体网络资源中枢（角色 Prompt 已注入身份）。
- **记忆在哪**：不在旧会话里，在「文件系统 + 总线线程 + 档案 + 规范集」四层——按下列清单读取即完整继承。

## 二、激活后 7 步领回（照做）

### ① 验证身份
```text
agent_profile        # 应显示 resource-manager / HR Cockpit 角色
agent_peers          # 看在线会话，确认自己的新 id
```

### ② 拉总线线程（恢复跨会话上下文）
```text
agent_thread         # 无参列出全部参与线程
```
- **主线**：与协调者 fa1f9150 的 thread-mswanlwh（HR 任命/仲裁/登记全记录）
- **前任交接先例**：thread-mswanlsz（b3778a1e→e7bfeea8）
- 各会话定向线程按需读（供应链/外链/摄取/QA 等）

### ③ 读权威文档（HR 记忆源）
```bash
cat ~/dsh-collab/resource-registry.md          # 登记表（权威）
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
- 表头维护者改为新会话 id
- 更新日志追加：`v1.0.208 | HR 交接：<旧id> → <新id>`
- `agent_unlock` 释放

### ⑤ 更新档案（登记自己为现任 HR）
```text
agent_profile role="资源管理者（HR Cockpit）" abilities=[...] resources=[...]
```
- abilities：档案登记/能力匹配/冲突仲裁/锁审计/token成本/冲突治理/模式评估/沉淀闸门/审批队列
- resources：resource-registry.md、resource-conflict-policy.md、resource-conflict-registry.md、token-cost-management.md、scripts/（5 工具）、dsh-plugin-hr、resource-manager preset

### ⑥ 旧会话归档（去双头）
- 旧 HR 会话（session-e7bfeea8）档案改「**前任资源管理者（已交接 <新id>）**」
- 方法：请协调者 fa1f9150 代改，或旧会话自行 agent_profile 更新

### ⑦ 协调者确认 + 定向通知
```text
agent_send to=session-fa1f9150-... text=【HR 交接完成】...
```
- 按 J34 广播约束：定向通知相关方（协调者 + 各资源属主），不搞全广播

## 三、交接铁律（防事故）

1. **登记表唯一写者**：任何时刻只有一个现任 HR 持登记表维护权——交接完成前旧 HR 不释放、新 HR 不接管（红绿灯串行）。
2. **去双头**：新 HR 登记后旧 HR 档案立即改「前任」，避免两个资源管理者并存。
3. **历史仲裁不推翻**：既有仲裁记录（§5.5）完整保留，不因换人重裁。
4. **敏感信息不落交接文档**：只列路径与动作，不写凭据/内容。
5. **秒级执行**：交接动作（查灯/改表头/更新档案）按秒级时间观立即完成，不排期。

## 四、交接完成判定（6 项全勾）

- [ ] 登记表表头 = 新 HR id
- [ ] 更新日志有交接行
- [ ] 新 HR 档案已登记（agent_profile 可见）
- [ ] 旧 HR 档案标「前任」
- [ ] 协调者确认收到交接通知
- [ ] 5 个脚本 + 插件路径已核验可访问

## 五、HR 资产速查（交接后立即核对）

| 资产 | 路径 | 状态 |
|---|---|---|
| 登记表 | ~/dsh-collab/resource-registry.md | 表头改新 id |
| 规范集/台账 | resource-conflict-policy.md / resource-conflict-registry.md | 只读（HR 维护） |
| 成本文档 | token-cost-management.md | 只读（HR 执行） |
| 工具脚本 ×5 | scripts/bus-capture.py / profile-sync-check.py / role-scan.py / lock-audit.py / preset-fit.py | 属主=HR |
| 驾驶舱插件 | ~/dsh-plugin-hr/ | 宿主级随重启生效 |
| 专用 preset | ~/.dsh/.agent-presets/resource-manager/ | 本会话即用 |
| 异步审批器 | MBP 开发中（用户），落地后登记 | HR 维护审批队列 |
| 总线线程 | agent_thread（22 个参与线程） | 拉取阅读 |

---

*交接内容 v1.0.207 · 完整版见 hr-handover-protocol.md · 激活即用*
