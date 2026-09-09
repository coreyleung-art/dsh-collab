# 崩溃修复记录 · 2026-08-18 批量插件连环出错

## 事件概述
mac mini 因批量安装 6 个未验证插件（dsh-plugin-hr / gate / gov / flower-cockpit / bus-bridge / office）连环出错导致崩溃。用户完成修复，共修 5 个坏插件。

## 修复明细

| 插件 | 问题 | 修复 |
|------|------|------|
| dsh-plugin-hr | ①缺 dsh.bundle 声明 ②async apply 导致 Invalid effect ③profile 里重复 insert | 补 dsh.bundle + 改同步 apply + 删重复段 |
| dsh-plugin-gate | output.schema 乱用 required + 缺 additionalProperties + union type | 清 required + 补 additionalProperties（后暂移出 bundles） |
| dsh-plugin-gov | output.schema 同款 required 问题 | 清 required |
| dsh-plugin-flower-cockpit | type:module 但 lib 是 CJS 产物 | 去 type:module（后暂移出 bundles） |
| dsh-plugin-bus-bridge | 声明 dsh.client 但没构建 client.js | 去 client 声明 |
| dsh-plugin-office | Config 是普通对象非 schema | 暂移出 bundles |

## 最终状态
- mac mini CLD 正常运行（58139, HTTP 200 ✅）
- **26 bundles 正常挂载**：@deepseek-ai/dsh-base、dsh-web-app、dsh-web-ui-all、modlens、genui、dsh-better-sidebar、agent-bus、local-projects、market、mcp-station、research、sandbox-policy-ui、voice、workflow-capture、knowledge、files、doc、repo-pipeline、waimai、gov、read-url、openpencil、ui-spec、external-link-policy、bus-bridge、hr
- 移出 bundles（待重新验证）：gate、flower-cockpit、office（deps 27 仍引用，修复后即可挂回）
- 所有修改均有 .bak-* 备份

## 关键服务状态（崩溃修复后核验）
- 外卖面板 8787：HTTP 200 ✅
- cron #28（launchd com.dsh.cron.*）：6 plist 在 ✅
- 内存：38%（较崩溃前 25% 改善，重启释放）
- 总线桥 8791 / 外链 8910：鉴权/路径预期行为（需 token/特定路径），非故障

## 流程问题与治理建议（用户提出）
「装插件 → 不验证 → 上生产 → 崩」循环治理：
1. 装插件后先 `dsh --profile web --dump-default-config` 验证能加载
2. 或先在隔离副本验证（/tmp/dsh-test-home）
3. 一批一批装，不要一次装 6 个

## 影响与后续
- 驾驶舱插件（flower-cockpit）暂移出：C1 代码层验收 #019/#020 结论仍有效（代码层），UI 插件级冒烟待重新挂载后执行
- 三插件重新挂载走「先 dump-default-config 验证 → 再挂载」新流程
- HR 登记新基线（26 bundles）+ 评估规则写入协作规范

## 关联
- 用户修复操作人：coreyleung（GUI 手动修复）
- 协作网络：12 活跃会话已广播断点审查任务
