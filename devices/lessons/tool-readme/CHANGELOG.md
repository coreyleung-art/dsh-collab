# 设备协调工具集 · CHANGELOG

## v1.2.0（2026-09-11 · 验证发现的 6 处自身缺陷修复）
> 来源：**验证 HR 对本人工具的登记时**，发现该登记所依赖的机制不成立 ——
> 缺陷由「验证」发现，非由「加规则」发现（同形态第 3 例）。证据卡：`data/device/selfdefects-from-verification`

- **device-audit v0.5.3 → v0.6.0**
  - 修 **status 恒真**：原无条件写 `ok`，discovery 全不可达、7/7 走兜底也报 ok → 现 `ok` / `degraded` + `degraded_reason`
  - 修 **退出码恒 0** → 现 **0=ok / 2=degraded / 1=failed，降级不并回 0**
  - 修 **归属错（数值维）**：matrix 兜底常量原标 `_source="register"`（指向未产出它的源）→ 新增 `infer_unreachable`
  - 修 **「不存在 vs 无法验证」混淆**：`HTTPError 404`（黑板可达但键不存在）原与 `URLError`（不可达）同吞进一个 except → 现分**四态** `source_status`：有值 / `absent`(404) / `http_error` / `unreachable`
  - `--help` 补**退出码约定**与四态说明（新行为必须可发现，R006 ⑨）
  - 三约束门 `--lean4-check` / `--samples` / `--fallback-check` 全部 ✅
- **mem-scope v1.3.5（内修补）**
  - 修 **失败映射成成功**：失败路径原 `exit 0` → 现 `exit 1`（否则 `|| 回退` 永不触发）
  - 修 **失败声明只覆盖 1/4 输出模式**：原仅 `--json` 打印，`--track`/`--verdict`/默认三模式**直接 KeyError 崩掉、声明完全丢失** → 现四模式**全输出完整声明**
- ⚠️ **接口变更**：两工具退出码语义变更；调用方若仅判 0/非 0 需复核（device-audit 新增 `2=degraded`）

## v1.1.0（2026-09-06 · R006 十项补全）
- **awesun-mcp.py/sh**：+VERSION 常量 +USAGE/--help/--version/--list-tools（补 ⑤⑥⑨）
- **mcp-sse-test.js**：+VERSION/--help/--version，SDK require 延迟（--version 免依赖）
- **mbp-bus-client.sh**：+--help/--version 分支（补 ⑨）
- **mbp-node-agent.py / i9-node-agent.py**：+argparse --version（v1.1.0）
- 新增 tool-readme/（README 索引 + 各工具文档 + 本 CHANGELOG）
- 资产登记：device-assets-lessons 更新

## v1.0.x（2026-08-17~08-18 · 初始版本）
- awesun-mcp.py/sh：向日葵 MCP 通道打通（device_search/info/wakeup 实测）
- mcp-sse-test.js：SSE 端点验证（P3 跨设备链路）
- mbp-bus-client.sh：v1.1 协议定稿（数组鉴权 AUTH_ARGS + token tr 去尾换行）
- mbp/i9-node-agent.py：黑板任务卡协议执行器（shell/info/scan/ollama 动作）
