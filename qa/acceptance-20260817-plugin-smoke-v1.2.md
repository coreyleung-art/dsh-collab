# 验收报告 #005 · 冒烟工具链 plugin-smoke v1.2

> 验收员：session-ffb7c3ab（QA 验收员） · 日期：2026-08-17
> 交付方：session-b241741f（冒烟工具链属主，4 bug 修复 + logSinceBoot）· 委派：直接提交（thread-mswbfjhm）
> 判定：✅ **PASS**

## 1. 交付物与验证点（b241741f 提供口径 vs QA 实测）

| # | 验证点 | 期望 | QA 实测 | 结论 |
|---|--------|------|---------|------|
| ① | bash 语法 | bash -n 通过 | ✅ `bash -n plugin-smoke.sh` 语法 OK | ✅ |
| ② | 实跑输出 | 主流程四段 + exit=0 | ✅ 实跑 dsh-plugin-agent-bus：①构建（产物校验）②patch 挂载标记 ③host 日志（boot 段截取）④UI 人工项；汇总 PASS 2 / FAIL 0，exit=0 | ✅ |
| ③ | plugins.example.json 挂载标记 | patch/host/ui 配置位齐全 | ✅ patch.file+applied / host.logGlob+errorPatterns+successPatterns+bootMarker / ui.checks / note 字段齐 | ✅ |
| ④ | logSinceBoot/bootMarker 支持 | boot 段截取避免旧残留 | ✅ L71-88 实现完整：bootMarker 匹配最后 boot 段（tail -n +LAST 截取）+ 临时文件清理；**实跑生效**：「仅统计最后 boot 段（bootMarker: CLD boot, 行 1002）」 | ✅ |
| ⑤ | UI 静态 | settings.section 注册 | ✅ 已在验收 #004 静态核验（源码 slots.inject + 产物引用）| ✅ |

## 2. 实跑证据（QA 实测，dsh-plugin-agent-bus 单插件）

```
── ① 构建: echo 'agent-bus: 无 build script…' → ✅ 构建成功 + 产物齐 (lib/index.js lib/client.js lib/dashboard.html)
── ② patch: cordis.patch.yml → ✅ patch 文件存在且含挂载标记
── ③ host 日志: ~/.cld/logs/dsh-web.log → ↳ 仅统计最后 boot 段（bootMarker: CLD boot, 行 1002）
   ⚠️ 未见明确加载痕迹（host 日志路径或需重启后回看）——弱断言，符合 README 已知边界
── ④ UI 人工确认: /agent-bus/dashboard 路由 HTTP 200（已实测）
═══ 汇总: ✅ PASS: 2 ❌ FAIL: 0 → exit=0
```

## 3. 注意项

| # | 项 | 说明 | 级别 |
|---|----|------|------|
| 1 | host 日志弱断言 | 实跑时「未见明确加载痕迹」——日志最后修改 04:05（boot 段截取行 1002 但无插件痕迹）；README 已知边界「无报错≠已加载，强断言需人工看 UI」| 信息（工具设计边界）|
| 2 | README 标题仍「模板 v1」 | 脚本已 v1.2 功能（logSinceBoot），README 头部版本行未同步（2026-08-17 核对）| 信息（文档一致性）|

## 4. 回归基线登记

- plugin-smoke 工具链版本：**v1.2 验收通过**（4 bug 修复 + logSinceBoot/bootMarker）
- 基线登记：回归基线第 1 节工具链版本状态更新为「v1.2 已验收（#005）」；8787 端点口径与 45f89009/e032fb77 归一（state 200/alerts/business 端点字段示例由 b241741f 提供后回填）

## 5. 验收结论

**PASS。** 冒烟工具链 plugin-smoke v1.2 验证点全过：语法正确、实跑主流程四段完整（exit 0）、配置位齐全、logSinceBoot/bootMarker 功能实跑生效（boot 段截取避免旧残留误报——正是 plugin-smoke-result 改进建议的落地）。2 项信息级提示（host 日志弱断言为工具设计边界、README 版本行待同步）不阻塞。工具链可正式作为回归基线冒烟工具使用。

### 5.1 logSinceBoot 补丁后复跑对照（2026-08-17，6ed4daf2 补丁 + QA 复跑）

- 补丁内容（6ed4daf2）：bootMarker 段截取修正为「最后 boot 行」（grep -nF + tail -1 + tail -n），plugins.json 4 插件启用 host.bootMarker="CLD boot"
- **QA 全量复跑：PASS 8 / FAIL 0，exit=0**（4 插件 × 构建+patch 双通道）——与 6ed4daf2 声称一致
- 关键验证：**host 日志 0 误报**——补丁前误报的「agent-bus Invalid token / repo-pipeline Cannot find package」旧残留不再出现（仅统计最后 boot 段，行 1002 之后）
- 附注：repo-pipeline typecheck 通过（其 workspace node_modules 已重建，tsc 在位；与 qa-001 修复 f9b659e 联动）
- 对照登记：补丁前 PASS 11（含 3 条旧残留痕迹）→ 补丁后 PASS 8 / FAIL 0（0 误报）
- 回归基线：工具链版本 v1.2（含 6ed4daf2 补丁）维持 PASS
