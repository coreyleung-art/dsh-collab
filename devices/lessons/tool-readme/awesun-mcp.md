# awesun-mcp（.py/.sh）· 向日葵 MCP 工具调用

> 版本 v1.1.0 · 维护：罗盘 5a5368af · 2026-09-06 R006 补全

## 用途
通过向日葵（AweSun）MCP 服务器调用远程设备控制工具（mac-mini 对 i9/MBP/各店设备）。

## 用法
```bash
# python 版
python3 ~/.dsh/devices/awesun-mcp.py device_search '{"keyword":"P8E7OP1","limit":5}'
python3 ~/.dsh/devices/awesun-mcp.py --help          # usage
python3 ~/.dsh/devices/awesun-mcp.py --version       # v1.1.0
python3 ~/.dsh/devices/awesun-mcp.py --list-tools    # 常用工具清单

# bash 版（等价）
~/.dsh/devices/awesun-mcp.sh control_command '{"session_id":"r=...","command":"echo ok"}'
```

## 工具类
- 设备：device_search / device_info / device_wakeup / device_shutdown
- 会话：control_connect / control_command / control_sessions / control_disconnect
- 桌面/通道：desktop_view / portforward（需设备信任）

## 依赖与配置
- AweSun 应用运行中（后端 127.0.0.1:8908）
- 凭据 ~/.dsh/devices/awesun.env（0600：AWESUN_API_URL/TOKEN，token 经环境变量注入不落命令行）
- 超时：AWESUN_MCP_TIMEOUT env（默认 30s）；cmd2 大输出超时策略=断开重连

## 已知限制
- cmd2 会话仅 Windows；ssh 会话仅 Linux；desktop_view/file/forward 需设备验证码（用户手动远控后信任）
- MacBook 不支持网络唤醒（hardware not binded）
