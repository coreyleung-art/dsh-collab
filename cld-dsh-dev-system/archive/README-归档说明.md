# DSHGuard.app 归档说明（2026-09-04）

## 状态：搁置（GUI 显示问题未解决）
- 现象：tkinter 窗口能启动、按钮/标题正常、内容已 insert、控件有尺寸，但用户屏幕看不到正文
- 环境：macOS 深色模式 + 可能无头/远程会话导致 tkinter 渲染异常
- 诊断记录：布局无塌陷（st=710x492）、内容 insert 成功（visible=1682）、非颜色问题（已强制浅色）
- 结论：tkinter 在该显示环境不可靠 → 若重启此项目改用 HTML/web 界面（浏览器打开，仿 CLD 自身）

## 项目内容（可复用）
- 管理台概念：文档浏览 + 五道闸操作按钮 + 输出面板
- 内嵌仓库打包法：.app/Contents/Resources/dev-system/ 放整套文档+工具
- 真实优先路径：guard 操作走 ~/dsh-collab/guard（非内嵌副本）

## 重启建议（若需要）
- 方案：做成本地 HTML 页 + `open file://` 浏览器打开（跨深色模式、一定显示）
- 或 Electron/Tauri 小应用
