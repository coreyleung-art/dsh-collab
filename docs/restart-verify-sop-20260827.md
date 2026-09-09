# 跨设备打通 · 重启后验证 SOP（2026-08-27）

> 目标：用户醒来后 **5 分钟**完成 MBP + i9 两端 CLD 重启与注入验证，无人监督下自动闭环。
> 前置：两端完整底座已装（MBP v1.0.0 物理复制 / i9 完整版），所有工具已就绪。
> 用时：每端约 2 分钟操作 + 重启等待。

---

## 一、重启前必查（30 秒）

### MBP（macOS）
```bash
# 1. 确认 profile bundles 含插件（R4 发现的关键点）
grep -A 5 '"bundles"' ~/.dsh/profiles/web/package.json | grep -E "agent-bus|central-inbox"
# 应看到:
#   "dsh-plugin-agent-bus"
#   "dsh-plugin-central-inbox"
# 若无 → 补上（agent-bus 在 central-inbox 前）再重启

# 2. 确认插件目录 cordis.patch.yml 存在
ls ~/.dsh/profiles/web/node_modules/dsh-plugin-agent-bus/cordis.patch.yml
ls ~/.dsh/profiles/web/node_modules/dsh-plugin-central-inbox/cordis.patch.yml
```

### i9（Windows）
```powershell
# 1. 确认 profile bundles 含插件
Get-Content "$env:USERPROFILE\.dsh\profiles\web\package.json" | Select-String "bundles" -Context 0,10
# 应含 dsh-plugin-agent-bus + dsh-plugin-central-inbox
# 若无 → 按黑板 notes/i9/install-bundles-fix 补齐

# 2. 确认插件目录 cordis.patch.yml 存在
Test-Path "C:\Program Files\CLD\resources\dsh-runtime\runtime\node_modules\dsh-plugin-agent-bus\cordis.patch.yml"
```

---

## 二、重启 CLD（每端 1 分钟）

### MBP
1. Cmd+Q 退出 CLD（或菜单 → 退出）
2. 等 5 秒（确认进程退出）
3. 重新打开 CLD
4. 等待 30-60s（插件加载）

### i9
1. 关闭 CLD 窗口（或任务管理器结束 CLD）
2. 等 5 秒
3. 重新打开 CLD
4. 等待 30-60s

---

## 三、自动验证（无需操作）

重启后 verify-watch 守护（中枢 launchd 每 5min）会自动：
1. 检测两端心跳变化（离线 >90s 判定）
2. 写恢复探针 notes/<node>/verify-recovery-*
3. central-inbox 生效 → 探针自动注入两端本地会话
4. 两端智能体收到探针 → 回报 notes/collab/verify-<node>-ack（payload.confirm=true）
5. verify-watch 检测到 confirm ack → 打印「🎉 验证通过」

**验证标准**：黑板 notes/collab/verify-mbp-ack + verify-i9-ack 出现 `payload.confirm: true`。

---

## 四、人工确认（可选，1 分钟）

重启后检查 CLD 日志应见：
- `[agent-bus]` 总线就绪
- `[central-inbox] 启动 node=mbp 监听 notes/mbp/,notes/collab/`（MBP）
- `[central-inbox] 启动 node=i9 监听 notes/i9/,notes/collab/`（i9）

---

## 五、若验证未通过

| 现象 | 可能原因 | 处理 |
|------|---------|------|
| 无 [central-inbox] 日志 | bundles 未注册 | 按第一节补齐 → 重启 |
| 无 [agent-bus] 日志 | 插件未加载 | 检查 profile bundles + cordis.patch.yml |
| 探针注入但无 ack | 两端智能体未处理 | 手动回报 verify-<node>-ack |
| 心跳中断 | node-bridge 未启动 | 检查 launchd/服务 |

---

## 六、验证通过后的下一步

1. **MBP node-bridge 升级**（可选）：v1.1.1 → v1.2.0（genebank mbp-bridge-upgrade.tar.gz）
2. **8/28 成本复核**：docs/cost-review-prep-20260828.md 预检已备
3. **三设备对称验证**：写 notes/mbp/test + notes/i9/test → 两端应自动注入

---

*本 SOP 由中枢（mac-mini）休息期准备，verify-watch v3.1 已就绪，等待两端重启。*
