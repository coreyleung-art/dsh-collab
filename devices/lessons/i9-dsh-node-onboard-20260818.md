# i9 dsh 节点落地 · D4② 完成记录

> 沉淀：session-5a5368af（设备协调）· 2026-08-18 · 类型：成果落链（迭代自动落链 v1.0）

## 一、成果

PC-i9（DESKTOP-P8E7OP1，Windows 11 Pro）验证 dsh headless 执行能力，成为分布式网络第 3 个 DSH 节点（mac-mini 宿主 + MBP 独立节点 + PC-i9 headless）。

## 二、关键事实

- dsh 版本：0.1.0-rc.5（C:\Users\admin\.dsh\profiles\node_modules 既有安装，非从零）
- headless profile：dsh-base + dsh-headless bundles
- web profile：含 PhoneUse 手机控制 MCP 配置（既有）
- 凭据：.credentials.yaml 冒号解析注入环境变量（不落明文，遵守凭据纪律）
- 端到端实测：`dsh --profile headless "say OK and exit"` → OK；自定义任务 → 42
- 命令通道：向日葵 cmd2（remote_id 1640748650），大输出超时策略=断开重连

## 三、启动器

- 路径：C:\Users\admin\dsh-run.ps1
- 用法：`powershell -ExecutionPolicy Bypass -File dsh-run.ps1 "<task>"`
- 功能：读取 .credentials.yaml 注入 DEEPSEEK_API_KEY 环境变量 → 运行 headless

## 四、登记

- HR 台账：device:i9 dsh 节点（v1.0.230）
- device-assets.md：v1.3（第 3 个 DSH 节点）

## 五、后续增强（待办）

- i9 web profile 插件扩展（mcp-station/workflow-capture/flower-cockpit/excalidraw，1e54d56d 预交付清单）
- i9 视觉节点（Qwen2.5-VL-7B，aa528267 建议，排期已评估）
- i9 常驻 agent（mbp-node 类似物）
