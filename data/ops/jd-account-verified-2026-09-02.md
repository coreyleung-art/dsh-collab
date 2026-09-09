# 京东账号归属实测确认 · 灯塔（data/ops）

- ts: 2026-09-02 02:0x
- 背景: 老登补登报告（9206+9207 logged_in, 提及手机号 13500223964）+ 黑板 jd-account-coord-to-mtm 交还账号协调
- CDP 实测（页面 DOM 门店名称）:
  - 9206 (店9 佛山禅城-京东): 页面显示「初蘅佛山禅城店」→ 账号归属 ✅ 正确（应为 19867185158）
  - 9207 (店11 天河守白-京东): 页面显示「初蘅鲜花天河区店」→ 账号归属 ✅ 正确（应为 13500223964）
- 结论: 两店登录态正常、账号各归其位，无错登（虽补登消息提及单号 13500223964，DOM 实测证明店9 实际登录佛山账号）
- 账号信息库现状: data/account-registry.json（单一权威源, 老登建）+ lib/account-registry.js (assertPhone 防错登门禁) + scripts/jd-relogin.js（已接入自检索+门禁）
- 接管声明: 登录/窗口/账号协调自即日起归采集域（灯塔 de7b29de）处理，老登不再自行操作；重登一律走 jd-relogin.js（assertPhone 防错登）
- 状态: 确认完成

## A7 接入完成（追加 22:4x）
- report.js detectIssues: logged_out 告警附正确账号（accountHint 自检索 registry）
- 实测: 佛山-京东→"账号: 19867185158（jd 验证码登录）"; 抖音→扫码提示; 美团 web_cookie→仅渠道
- server 已重启生效（restart-panel.sh, 10/10 running, 10/10 logged_in）
- 需求文件 A7 状态已改 ✅
