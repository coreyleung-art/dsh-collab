# health-check 插件吸收记录（R010 端侧吸收 · 方案 B 完整吸收）

> 决策：2026-08-30 用户拍板「完整吸收全部 4 个工具，并评估整合进目前工具链」
> 来源：i9 dsh-plugin-health-check v0.1.0（genebank sha256:582a0df9f7a928dd38a218ecfb88a0ff189cadbbaa6915a20dfc16883594f8e6）
> 落点：dsh-tools v1.13.0 `health` 子命令（Rust 化）

## 一、吸收前评估（R010）

| i9 插件工具 | 功能 | 本机现状 | 整合决策 |
|------------|------|---------|---------|
| `plugin_health` | 插件健康检查（dsh 版本/插件加载/dump-config/SSE/注入/总线） | health-check.sh（11 项）+ dsh-health.py，但无插件加载检查 | ✅ Rust 化 `health health-check`（动态扫描 profile 插件） |
| `pitfall_query` | 踩坑档案查询 | pitfalls-cli.py 已有（Python）+ docs/pitfalls/pitfalls.json 单一事实源 | ✅ Rust 化 `health pitfall query`（共享同一数据源） |
| `pitfall_add` | 踩坑档案登记 | pitfalls-cli.py 已有 add | ✅ Rust 化 `health pitfall add`（写前红绿灯提示） |
| `ops_upgrade_status` | 升级链路状态（沙箱/runner/健康日志+版本） | 无专门工具 | ✅ Rust 化 `health upgrade-status` |

**整合评估结论**：i9 版是 JS 插件 + Windows 硬编码路径（`E:/...`），不能直接装 mac-mini；本机主线是 Rust 化常驻工具。因此**完整吸收 4 工具、Rust 化进 dsh-tools**，mac 路径自适应（CLD runtime 探测），pitfall 数据源对齐本机单一事实源 `~/dsh-collab/docs/pitfalls/pitfalls.json`（items[] 格式），与 pitfalls-cli.py 并存（CLI 治理形态）。

## 二、交付（v1.13.0）

```
dsh-tools health health-check              # 插件健康检查（升级后必跑）
dsh-tools health upgrade-status            # 升级链路状态
dsh-tools health pitfall query <关键词> [--level P1]   # 查踩坑
dsh-tools health pitfall add <标题> [--level P1] [--date] [--detail]  # 登记（写前红绿灯）
```

- 源码：`~/dsh-collab/rust-tools/src/health_check.rs`（新增模块，main.rs 注册 `health`）
- dist：`dist/dsh-tools-macos-arm64-v1.13.0`（sha256 ce446376...）+ `dist/dsh-tools-win-x64-v1.13.0.exe`（sha256 709fd924...）

## 三、实测证据（mac-mini 生产环境）

```
① health-check → all_ok: True
   dsh 0.1.0-rc.6 · 20 插件全 main=ok（agent-way v1.3.1/central-inbox v0.1.6/bus-bridge v0.2.0...）
   SSE 8803 连接正常 · central-inbox 注入活动 · agent-bus.json 存在
② upgrade-status → dsh 版本 + cld/crash 日志 tail + restart-gate 可用 + pitfalls_count=6
③ pitfall query MCP → 命中 2（2026-08-30-mcp-sse-wrong-port / mcp-stdout-lock-deadlock，P1）
④ pitfall add（中文标题）→ id=2026-08-30-P7（中文兜底序号），写入验证后清理，items 恢复 6
```

## 四、R006 对齐

- ✅ dsh 插件形态（Rust 工具子命令，dsh-tools 统一入口）
- ✅ 文档化（本记录 + tools-registry.md 更新 + health_check.rs 头注释）
- ✅ 版本管理（v1.13.0，Cargo.toml bump，dist 双端 + sha256）
- ✅ 统一日志（health-check 结构化 JSON 输出）
- ✅ 自动落链（tools-registry.md 台账 + 本记录 + 迭代报告）
- ✅ CLI 治理（dsh-tools health 子命令统一入口，与 pitfalls-cli.py 并存）
- 🟡 红绿灯：pitfall add 写操作输出 R001 提示（调用方应先 agent_lock file:pitfalls.json）

## 五、遗留/建议

- i9 端保留原 JS 插件（R007 删前考古：不删端侧资产，i9 可继续用原版；本机以 Rust 版为准）
- health-check 的 dump-config 检查（i9 版 execSync 跑 bin.js）未移植（本机 profile 校验走 deploy-check，避免重复）
- 后续可加：health-check 接入 ~/.cld/logs 崩溃原因解析（升级后自动对比上次 exit-trace）
