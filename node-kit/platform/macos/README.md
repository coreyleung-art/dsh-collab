# macOS launchd 平台模板 — node-kit

> 用于 macOS 节点守护常驻。Windows 节点见 platform/windows/（schtasks）。

## launchd plist 生成（deploy.sh 自动做, 也可手工）

```xml
<!-- ~/Library/LaunchAgents/com.dsh.nodekit.<node>.plist -->
<plist version="1.0"><dict>
  <key>Label</key><string>com.dsh.nodekit.<node></string>
  <key>ProgramArguments</key><array>
    <string>/usr/bin/python3</string>
    <string>~/.dsh/node-kit/<node>/device-daemon.py</string>
  </array>
  <key>EnvironmentVariables</key><dict>
    <key>DSH_NODE_ID</key><string><node></string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>~/.dsh/node-kit/<node>/daemon.out.log</string>
  <key>StandardErrorPath</key><string>~/.dsh/node-kit/<node>/daemon.err.log</string>
</dict></plist>
```

## 手工操作

```bash
launchctl load ~/Library/LaunchAgents/com.dsh.nodekit.<node>.plist   # 启动
launchctl unload ~/Library/LaunchAgents/com.dsh.nodekit.<node>.plist # 停止
pgrep -fl device-daemon.py    # 确认在跑
```

## env 契约（G-D2）

| env | 必填 | 说明 |
|-----|------|------|
| DSH_NODE_ID | ✅ 无默认 | 节点 id（mbp/i9/新节点）—— 部署门强制 |
| SERVER_BUS | 默认 | http://106.53.214.108:8791 |
| LOCAL_BB | 默认 | 本机 127.0.0.1:8792 |
| BLACKBOARD_TOKEN | 默认 | token 0600 私存 |

---
*node-kit macOS 模板 · 2026-09-09 · P1*
