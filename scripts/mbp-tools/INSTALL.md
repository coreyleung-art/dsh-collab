# 安装（MBP 工具包）

```bash
tar xzf mbp-tools-*.tgz -C ~/mbp-tools            # 解到任意目录
export BB_WEBHOOK_TOKEN=<中枢 webhook token>
export MACMINI_BB_TOKEN=<mac-mini 板 bearer token>
# node 用绝对路径（本机 bash 环境里 node 常不在 PATH）：
NODE=$(command -v node || echo /opt/homebrew/bin/node)
$NODE sandbox-agent-way.mjs                        # 期望：投递路径可用（delivered）
python3 relaunch-cld.sh --selftest                 # 期望：6 通过 / 0 失败
python3 restart-audit.py                           # 期望：exit 0「全部通过 ⇒ 可以重启」
```

★ 适配提示（跨端差异，非缺陷）：
1. 进程/应用名、`CLD_APP` 路径、`~/.cld/logs/*` 位置需按本机调整（均可环境变量覆盖：`CLD_APP/CLD_PATTERN/CLD_LOG/CLD_MARKER/CLD_PS_BIN`）。
2. 判据用 `ps -ww -axo pid=,command=` + **argv0 精确相等**——macOS 上 `pgrep -f <全路径>` 匹配不到 Electron 主进程（实测假阴性）。
3. 跨代存活必须 `setsid`（`spawn-detached.sh`）；`nohup &` 会被连坐杀（G36）。
