# CLD 服务器模式故障修复：`--profile <name> is required`（2026-08-16）

> 跨会话协作成果物 · 来源会话：session-3d490920-860c-4c5c-8d93-c6041834a8c6（dsh 智能体）
> 已按 `~/dsh-collab/` 约定落盘并声明路径。

## 症状

CLD 桌面壳（Electron 包装 dsh web）以「服务器模式」启动（设置了 `CLD_BIND_HOST`，
例如 `serve.sh` 或 launchd `com.cld.server`）时，dsh web 立即退出，弹窗：

```
The dsh server exited (code 1, signal null).
Last log lines:
error: --profile <name> is required
```

日志（~/.cld/logs/dsh-web.log）对应：

```
[cld] server mode: public 0.0.0.0:3081 via inject-proxy (mobile css, trusted: )
error: --profile <name> is required
```

## 根因

`main.js` 的 `spawnDsh()` 在服务器模式把 `--trusted-host <host>` 放在 `web` **之前**：

```
CLD --expose-internals .../bin.js --trusted-host coreymac-mini.taild3fd86.ts.net web --port 0
```

dsh 启动器（`@deepseek-ai/dsh/lib/bin.js`，commander：allowUnknownOption +
enablePositionalOptions）只认识自己的参数（--profile/--patch/--dump-config…），
遇到不认识的 `--trusted-host` 即把其当作位置参数消费，`web` 不再被识别为子命令
→ 根命令 action 触发 → 无 `--profile` → `error: --profile <name> is required`，
退出码 1。

`--trusted-host` 是 dsh web 应用自身的参数（/api 信任围栏），必须放在 `web` **之后**。

> 排查陷阱：日志 `trusted: ` 为空不代表没传 host —— 该行只打印自动收集的
> Tailscale/LAN IP（autoTrusted），`CLD_TRUSTED_HOSTS` 的 host 不显示。

## 修复（已应用到安装的 App）

改动（`spawnDsh()`）：

```js
// 旧
const dshArgs = ["--expose-internals", bin];
if (CFG.bindHost) { ... dshArgs.push("--trusted-host", h) ...; dshArgs.push("web", "--port", "0"); }
// 新
const dshArgs = ["--expose-internals", bin, "web", "--port", "0"];
if (CFG.bindHost) { ... dshArgs.push("--trusted-host", h) ...; logStream.write(...); }
```

修复后命令：`CLD --expose-internals .../bin.js web --port 0 --trusted-host <host>` ✓ 正常启动。

## 已落地工件

| 工件 | 路径 |
|------|------|
| 修复后 app.asar（已替换） | `/Applications/CLD.app/Contents/Resources/app.asar` |
| 原 app.asar 备份 | `/Applications/CLD.app/Contents/Resources/app.asar.bak-20260816` |
| 修复文档（详细） | `~/CLD/FIX-dsh-server-exit.md` |
| 修复后完整 main.js | `~/CLD/main.js.fixed` |

验证：Electron 自身 asar 读取器读回 main.js 完整（head `/**`、tail `}\n`）、语法 OK、
无残留 `dshArgs.push("web"`；`bin.js web --port 0 --trusted-host H` 实测可启动。

## 相关注意事项（供运维参考）

- `codesign --verify --deep --strict` 报 `code has no resources but signature indicates
  they must be present`：adhoc/linker-signed + Sealed Resources=none，本地未公证 Electron
  应用正常状态，**不影响运行**；如需消除可 `codesign --force --sign - /Applications/CLD.app`
  （不建议 --deep）。
- 沙箱环境：macOS 下 `ps` 被拦（Operation not permitted），`lsof` 可用；
  asar 手工按 header 偏移切文件会差 2 字节 padding，读取请走 Electron 自身读取器
  （`ELECTRON_RUN_AS_NODE=1 .../CLD -e "readFileSync('app.asar/main.js')"`）。
- 下次源码构建：在 CLD 源码 `main.js` 应用同样改动后重新 electron-builder 打包即可。
