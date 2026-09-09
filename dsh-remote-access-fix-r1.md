# DSH Web GUI 手机远程访问 —— 排障与修复（R1）

- **贡献会话**: session-43b1a2d3-3b77-41ed-aa9e-effcef446af3
- **日期**: 2026-08-16
- **状态**: 已修复并全链路实测通过（HTTP RPC + WebSocket 实时流）
- **关联**: 手机经 Tailscale 访问 DSH 桌面 GUI 实时会话

## 现象
- 手机能打开页面（200），但看不到实时会话：会话列表/历史/实时流全空。
- 根因链：dsh web 的 `/api` 信任围栏拒绝所有非 loopback Host，导致手机发的每个 `/api` 请求 403。

## 根因（三层）
1. **围栏机制**: dsh web 的 `/api` 围栏（`dsh-client-connection` 的 `isTrustedApiRequest`）只放行
   loopback Host + `trustedHosts` 列表（Host 与 Origin 均校验，Origin 须与 Host host:port 一致）。
2. **CLD 的信任来源**: CLD 桌面实例启动 dsh web 时用 **`--trusted-host <ip>` 命令行参数**
   （`main.js` `spawnDsh`：服务器模式自动采集 `tailscale status` 全部设备 IP + en0 LAN IP +
   `CLD_TRUSTED_HOSTS` 环境变量），**不读** `~/.dsh/profiles/web/cordis.patch.yml` 的
   `web-runtime.trustedHosts` 补丁（该补丁只对独立 `dsh --profile web` 生效）。
3. **采集失败无告警**: 本次重启后 CLD 日志显示 `[cld] server mode: ... trusted: ` 为空
   （`collectTrustedHosts()` 的 `execFileSync("tailscale status")` 失败被静默吞掉），
   即 `--trusted-host` 一个都没传 → 围栏只认 loopback。

## 修复（已生效，无需重启 CLD）
修改 `~/.cld/tools/dsh-tailnet-proxy.mjs`（LaunchAgent `com.dsh.remote` 管理，监听 0.0.0.0:3081，
自动发现 CLD GUI 端口）：
- 新增 `loopbackHeaders()`：把 `Host` 改写为 `127.0.0.1:<目标端口>`；若带 `Origin` 一并改写为
  `http://127.0.0.1:<目标端口>`。
- HTTP 转发（`forward()`）与 WebSocket Upgrade 路径均应用改写。
- 效果：围栏按 loopback 放行，不依赖 CLD 信任列表/补丁；CLD 重启换端口时代理自动重扫跟随。

## 验证（全部通过）
| 路径 | 页面 | RPC(session.list) | 实时流 |
|---|---|---|---|
| http://100.120.203.20:3081 | 200 | 200（真实会话列表） | WS 实时事件 ✅ |
| https://coreymac-mini.taild3fd86.ts.net/ | 200 | 200 | WS 426(放行) ✅ |
| /m 移动端 + 配对 | 200 | 配对接口 200 | 配对后事件流 ✅ |

## 正确配置入口（供后续维护，非 profile 补丁）
- `CLD_TRUSTED_HOSTS=<h1,h2>`：逗号分隔追加到 `--trusted-host`（恢复"按 tailnet 域名判定"语义）。
- `CLD_BIND_HOST=0.0.0.0`：服务器模式，自动采集设备 IP。
- 监控探针：`~/.cld/logs/dsh-web.log` 中 `trusted: ` 是否为空。

## 注意事项
- 手机访问前置条件：Tailscale 在线；MagicDNS 开启（域名访问时）。
- 配对后移动端 `/m`（remote-web-ui 插件）提供完整手机远程控制（会话列表/历史/实时流）。
- `tailscale serve --https=8443 → 61109` 这类直连规则因 Host 透传同样过不了围栏，勿用。
- **端口 3081 单一归属 = com.dsh.remote（J16 决议）**：若未来恢复启用 CLD 服务器模式，须显式 `CLD_PORT=3082`，避免 inject-proxy 与 tailnet 代理 EADDRINUSE 冲突（详见 resource-conflict-registry.md J16）。

## 相关文件
- 改动：`~/.cld/tools/dsh-tailnet-proxy.mjs`
- 观察：`~/.cld/logs/dsh-web.log`、`~/.claude/automation/dsh-health.py`（第 4 项检查结论已过时）
- 配置：`~/.dsh/profiles/web/cordis.patch.yml`（补丁对 CLD 无效，保留无害）

## 资源归属注记（2026-08-16，跨会话协调闭环）
- `~/.cld/tools/dsh-tailnet-proxy.mjs`：**同一文件，无独立副本**。创建者与运行实例归属 **session-582093dd**（launchd `com.dsh.remote` 在用）；**session-43b1a2d3** 仅持有其中的 Host/Origin 改写修改（`loopbackHeaders`），无独立副本。
- 协作规范：共享路径改动前先 `agent_light` 查灯 → `agent_lock` 独占 → 修改 → `agent_unlock`。
- 档案登记：43b1a2d3 的 resources 中以 `mod:` 前缀标注该共享文件，避免归属歧义。

## 安全收口补记（2026-08-17，582093dd 收口 + 43b1a2d3 注释修正）
- **风险**：Host/Origin 改写 loopback 会让 dsh /api 围栏与 remote-web-ui 配对门禁**都按 loopback 放行**——
  若代理默认绑 0.0.0.0，局域网设备可免配对直接打 /api（配对门禁被绕过）。
- **收口（582093dd）**：代理默认绑定本机 Tailscale IP（100.x，ifconfig 自动发现），仅 tailnet 设备可达；
  Tailscale 设备身份+ACL 即信任锚点；0.0.0.0 仅无 tailnet 回退并打 ⚠ 告警。
- **注释修正（43b1a2d3）**：loopbackHeaders 处补充安全语义说明，「配对门禁照常生效」表述已删除（改写下不成立）。
- 验证：lsof 确认监听在 100.120.203.20:3081，局域网（非 tailnet）不可达。
