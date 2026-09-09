# CLD-002 · 异常退出留痕机制（看门狗）— 交付说明

> 负责人：session-3d490920（CLD/dsh 运维排障）· 2026-08-17
> 状态：实现完成 + 测试通过；**安装待用户确认**（沙箱无法写 /Applications，需用户执行两条命令或下次维护窗口）
> 附：顺带修复 `readFileSync` 未导入 bug（readModeCfg 永远返回 {}、「记住模式选择」从未生效），见实现第 5 条。
> v2（2026-08-17 04:5x）
> v2.1（2026-08-18）：按 c1111ffe 规范草稿对齐——新增 crash-reason.log（启动时人类可读摘要）、三文件写 0600、marker 增 version/uptime_sec 字段。sha256 fb70a9b89869181bb2c7090b005d8ff0b6d91a295c1c53eefca38921422c35b7。：并入快速重启修复——新增 `process.on("SIGTERM")` 干净退出处理（SIGTERM → app.quit() → before-quit → traceExit clean），重启顺序改为「先 SIGTERM 旧实例等退出→再拉起」，修复单实例锁吸收新实例导致重启无效的问题。sha256 fb70a9b89869181bb2c7090b005d8ff0b6d91a295c1c53eefca38921422c35b7。

## 需求（backlog CLD-002, P1）
本次 23:49「闪退」实为外部 `pkill -9 -f "dsh/lib/bin.js"` 强杀（SIGKILL）——无 .ips、日志无退出原因，任何异常退出都不可审计。
验收：**下一次异常退出能在 ~/.cld/logs 留下退出原因（信号/退出码/时间）**。

## 实现（main.js 新增 exit-trace 模块，约 4KB）
1. **exit-marker.json**（~/.cld/logs/）：启动时写入当前运行 marker（pid/startedAt/cleanExit:false，原子写 tmp+rename）；
   干净退出时（before-quit / process exit）覆写 cleanExit:true + 退出码/信号/结束时间/原因。
2. **heartbeat.json**：每 30s 心跳（pid/ts/iso），提供「上次运行存活到何时」的新鲜度证据（setInterval().unref()）。
3. **dsh-web.log [exit-trace] 行**：启动时检测上次运行状态——
   - 上次未干净退出（SIGKILL/崩溃）→ `[exit-trace] PREVIOUS CLD RUN (pid X, started T) DID NOT EXIT CLEANLY — no clean-exit record (crash or external kill?); last heartbeat ...; marker: {...}`
   - 上次干净退出 → `[exit-trace] previous CLD run (...) exited cleanly at ... (reason quit, code 0, signal null)`
4. **uncaughtException 捕获**：记录崩溃原因（stack）到 marker + 日志，随后 rethrow 保留默认崩溃行为。
5. **顺带修复**：`readFileSync` 未从 node:fs 导入（try/catch 吞掉 ReferenceError，导致 readModeCfg 永远返回 {}、「记住选择」模式配置从未生效）——本次补上导入。

## 验证
- 语法检查通过（node --check）。
- 四场景功能测试通过：① 首次启动无噪音；② SIGKILL 后下次启动报 DID NOT EXIT CLEANLY（含 pid/start/heartbeat）；③ 干净退出后下次启动报 exited cleanly；④ 崩溃原因（uncaughtException）可检测。
- 打包后经 Electron 自身 asar 读取器校验：main.js 完整、package.json/scripts 逐字节未动、integrity 重算通过；既有 --trusted-host 修复保留。

## 工件
| 文件 | 说明 |
|------|------|
| `~/CLD/app-cld002.asar` | 替换用 asar（92346B，sha256 fb70a9b89869181bb2c7090b005d8ff0b6d91a295c1c53eefca38921422c35b7） |
| `~/CLD/main.js.cld002` | 修复后完整 main.js（27216B，含 SIGTERM 处理 + v2.1 规范对齐） |
| 备份 | 安装时先 `cp app.asar app.asar.bak-cld002-20260817` |

## 安装（需用户执行，沙箱无 /Applications 写权限）
```bash
cp /Applications/CLD.app/Contents/Resources/app.asar /Applications/CLD.app/Contents/Resources/app.asar.bak-cld002-20260817
cp ~/CLD/app-cld002.asar /Applications/CLD.app/Contents/Resources/app.asar
```
安装后**下次启动 CLD 生效**。验收方法：正常启动后 `~/.cld/logs` 应出现 exit-marker.json + heartbeat.json，dsh-web.log 出现 `[exit-trace] previous CLD run ... exited cleanly`；随后 `pkill -9 -f 'CLD.app/Contents/MacOS/CLD'` 强杀，再次启动应出现 `[exit-trace] PREVIOUS CLD RUN ... DID NOT EXIT CLEANLY`。

## 说明
- SIGKILL 不可捕获，检测采用「下次启动比对 marker」的行业标准做法；launchd 不原生记录退出原因（KeepAlive 静默重启），marker+heartbeat 已覆盖验收。
- 若与 CLD 重签（codesign 预案 v3）同一窗口执行，先装补丁再重签，seal 会把新 asar 一并封入。