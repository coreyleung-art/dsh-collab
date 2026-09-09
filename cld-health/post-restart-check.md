# CLD 重启后复核清单（Post-Restart Check）

> 管理者：session-9910d4b2（CLD 健康审查与迭代管理）
> 用途：CLD 重启（含维护窗口/崩溃恢复）后 5 分钟内的标准复核，验证 18-bundle profile 全量生效。
> 背景：2026-08-16 23:49 重启后实例仍为 5-bundle 运行态（磁盘 18 bundles 对下次重启生效）——本次重启后须按本清单复核。

## 前置

- [ ] 维护窗口已协调（CLD-008 护栏：pkill/重启/改 profile 需 agent_light + 协调）
- [ ] 重启原因/发起方已知（避免再发生 28ca132e 式未协调手术）

## 重启后 5 分钟复核（按序）

1. **GUI 可用**：`curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:50120` → 200（端口可能变化，以日志为准）
2. **新 boot 行**：`grep 'CLD boot' ~/.cld/logs/dsh-web.log | tail -1` → 时间戳为新；其后的 Error/throw 计数 = 0
3. **运行态 bundles = 18**：`python3 -c "import json;print(len(json.load(open('$HOME/.dsh/profiles/web/package.json'))['dsh']['profile']['bundles']))"` → 18；且 coreuleung 拼写 = 0
4. **插件树无加载失败**：日志无 `plugin tree failed`；agent-bus 加载 profile 数 ≥ 16
5. **waimai 链路**：`waimai_state` → 10 店 logged_in；面板 `curl http://127.0.0.1:8787/api/state` lastTick 新鲜（<300s）
6. **MCP 工具恢复**：本会话工具面是否出现 obsidian-server / chroma-server / openchronicle（此前 5-bundle 运行态缺失项，重点复核）
7. **3081 远程入口**：`lsof -nP -iTCP:3081 -sTCP:LISTEN` → 新 PID 正常监听（旧 PID 变化属预期）
8. **research skill**：skill 列表含 research-pipeline
9. **一键巡检**：`bash ~/dsh-collab/cld-health/health-check.sh --log` → 全绿并追加趋势记录
10. **基线快照更新**：GUI 端口 / 3081 PID / 在线会话数 / 插件挂载状态 → 写回 `cld-health-baseline-*.md`
11. **3080 端口哨兵（b278baab 实测口径）**：`lsof -nP -iTCP:3080 -sTCP:LISTEN` → **无输出=单实例**（防双实例复发）；有监听需确认双实例/哨兵预期
12. **会话日志帧完整性（b278baab 实测口径）**：① 会话数 `find ~/.dsh/sessions -name session.jsonl.zstd | wc -l`；② 撕裂帧检测=逐帧扫 ZSTD_MAGIC 帧头/校验和，**EOF 残留不完整帧即 torn**（完整脚本含重复 seq 检测可向 b278baab 取）；health-check #14 用 zstd -t 做自动化层
13. **dshdoc_health 复测（c1111ffe 遗留①）**：`dshdoc_health` → status=ready / engine=xberg-node / runtimeVersion=1.0.14（新套装 vs 运行态差异验证，libheif 1.23.0/1.23.1）
14. **compaction 挂载验证（CLD-017，协调者排期）**：重启后 standard+compaction 继承预设生效——抽查会话可执行 /compact 或压缩插件已挂载（试点会话 3b5efeef 降 90% 验证关联）

## 异常处置

| 现象 | 处置 |
|------|------|
| 面板 8787 连接拒绝 | **先查数据目录**：10 店库在 `~/Library/Application Support/外卖门店多平台管理/data/app.db`；拉起必须 `export MTM_DATA_DIR="$HOME/Library/Application Support/外卖门店多平台管理"` 再启动（裸跑 server.js 只有 3 店旧库，数据错位）；指派 aa528267/de7b29de |
| waimai_* 工具不可用 | **常驻化已批准**（`~/dsh-plugin-waimai` Host 包已产出验证）：接入后重启应自动可用（无需 cordis_run）——本项即验收点；**未接入前**仍按 wmmon `kind:new` 重建（kind:existing 报 no dynamic plugin）；指派 aa528267 |
| 插件树加载失败 | 查日志定位 bundle，走红绿灯指派 3d490920 / eb5ee9cc / 1e54d56d |
| MCP 工具未恢复 | 指派 mcp-station 会话（1e54d56d）核对插件与 MCP 服务器 |
| 负载持续 >12 | 升级 CLD-005，指派 b241741f |
| package.json 又出现裁剪/拼写 | 立即冻结写入方排查（CLD-003 复发预案），恢复 18 bundles 并备份 |

## 记录

- 复核结果回写基线报告 + backlog（如有新问题则登记新 CLD-xxx 项）
- **工具调用约定（CLD-013 教训）**：所有工具须在 `run_code` 程序内经 `tools.xxx()` 调用；直接调用报 `unknown tool` 是预期提示而非缺失（resume 会话尤注意）
- 本次复核执行人：session-9910d4b2
