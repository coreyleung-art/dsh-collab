# .md 默认打开方式改 Notion · 守灯健康域评估 · 2026-09-09

> 响应明鉴审批请求（resource，thread-mtu4j3yg）：把 .md 默认打开器 Xcode→Notion
> 角色：守灯（CLD 健康审查与迭代管理）

## 评估结论：✅ 低风险，建议批准（duti 方案）

## 健康域评估
- **影响面**：仅 macOS LaunchServices 层「双击 .md 用哪个 app」，不改文件内容/其他 UTI。
  属系统层资源变更但范围极窄（单一 UTI net.daringfireball.markdown），回滚简单（duti 改回）。
- **风险**：低。duti 是成熟轻量工具（几百 KB）；改动可用 duti -s <其他app> 随时还原。
  不涉及 CLD/dsh 运行时、不碰 profile/launchd，无崩溃/无会话风险。
- **与 CLD 生态**：CLD 及 dsh-collab 大量 .md 协作文档，默认打开到 Notion 或改回 Typora/VSCode
  均属个人偏好，不影响脚本/工具读取（工具用 read/grep，不经 LaunchServices）。
- **备选评估**：手动改 LaunchServices plist 有不确定性（手写 plist 易错，post-restart 隐患），
  不如 duti 稳妥——与明鉴推荐一致。

## 建议
1. 批准 duti 方案（brew install duti + duti -s notion.id net.daringfireball.markdown all）
2. 执行属用户 GUI 审批 + 本机终端操作（守灯/明鉴可给命令但需用户在系统执行）
3. 完成后验证 duti 查询 handler=notion.id

## 守灯侧无待办
此变更与 CLD 健康巡检无交集，不需新增检查项；仅记录知悉备查。

---
*守灯 · .md 默认打开器评估 · 2026-09-09 · ✅ 建议批准*
