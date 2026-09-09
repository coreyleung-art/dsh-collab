# Agent Bus 跨会话协作名册

> 归属：协作约定 v1（~/dsh-collab/）· 维护方：Agent Bus（session-fa1f9150-c949-401f-ba8c-d265f6221676）
> 更新：本文件为总线侧成果，索引方可将本条加入 INDEX.md

## 系统状态
- 插件：动态版 v11 运行中（agbus-2/pkg-39）；常驻版 `dsh-plugin-agent-bus` 待重启接管（含自动冲突检测）
- 8 个全局工具：agent_peers / agent_send / agent_broadcast / agent_thread / agent_light / agent_lock / agent_unlock / agent_unlock_all
- 投递：走宿主真实收件箱（followup 唤醒），与用户消息同路径；持久化 `~/.dsh-agent-bus.json`（防抖写盘）

## 能力登记（截至协作网络 15 会话）
| 会话 | 能力/角色 |
|---|---|
| 6e49710e | DSH mac mini 运维（日志 ~/.cld/logs、健康体检、重启窗口） |
| c1111ffe | mac mini 故障修复 |
| 43b1a2d3 | 手机远程访问 / tailnet 代理 / Host-Origin 改写 |
| 3d490920 | CLD server 模式修复（app.asar 补丁） |
| dcac2308 | repo-pipeline（GitHub/Gitee 双仓 + CI/CD） |
| eb5ee9cc | 插件安装/验证/加载运维 |
| 3b5efeef | 文件/文档增强（dsh-files/knowledge/doc） |
| b241741f | 系统运维/知识库（Dify RAG + ChromaDB + sysops） |
| de7b29de | 外卖多平台数据侧（10 店、事件库、8787 面板） |
| aa528267 | 外卖运营动作侧（14 waimai 工具、录制器） |
| 1e54d56d | GUI 插件开发（MCP 工作站 / 工作流捕获） |
| 75815fa9 | dsh-pet 电子宠物定制/禁用 |
| 3221f810 | 语音输入助手 |
| 582093dd / e0c391f7 等 | 通用会话 |

## 外卖域锁约定（同店互斥）
- 店铺窗口生命周期 / 同店写操作 → `lock("store:N")` 复用同一把锁
- config.json（项目 + Application Support 双份）→ `lock("file:config.json")`
- 只读聚合（state/alerts/im/replies，8787 API）→ 免锁并行
- 分工：events/im_sessions 表 de7b29de 独占写；capabilities/scenarios 归 aa528267

## 红绿灯协议（所有会话）
1. 同源操作前先 `agent_light(resource)`：绿灯直接做；红灯看 holders/队列
2. 独占需求 `agent_lock(resource, mode:"exclusive"|"shared", wait:true)`：不兼容可排队，轮到收 🚦 通知
3. 完成后 `agent_unlock`（转交队列下一位或变绿）
4. 不要绕过锁；write/edit 命中红灯会被常驻版自动拦截（动态版无 guard）

## ⚠️ 健康判定铁律（2026-08-17 新增，8787 假阴性教训）
- **宿主服务健康判定必须走宿主 API 工具**（waimai_state / waimai_* 等），**bash curl 受沙箱网络隔离不可作权威依据**（实测：curl 127.0.0.1:8787 = 000 是沙箱假阴性，waimai_state 返回 10 店全活）
- 不要用「特定 PID + lsof」判定存活：面板 server 是独立 node 进程（detached 于 Electron 壳），PID 随重启变化
- 判定标准：宿主 API 工具返回真实数据 = 存活；对拍冲突时以「宿主 API 工具实测」为权威，curl/PID 结果仅作参考线索
- **采集活性 vs 事件活性分口径（2026-08-17 de7b29de 数据实证）**：`customer_msg` 事件只在「客户消息内容变化」时触发（lastClient 比对 + 8s 节流），深夜无新消息则事件静默属**正常行为**，不是断流
  - 采集层活性信号 = `lastTick 实时刷新` + `im_sessions updated_at 持续更新`（watcher 每 tick upsert 列表层，即使内容不变也刷新）
  - `customer_msg 事件最新时间` 只反映「最后一次新客户消息」，**禁止**用作断流/健康判定指标（避免误报）
- 已撤销 CLD-010「面板宕机」子项（假阴性）；MTM_DATA_DIR 修复保留为有效改进记录

## 环境情报速查
- CLD 桌面实例 **不读** profile 的 trustedHosts 补丁（壳进程用 `--trusted-host` 启动）；恢复域名判定的入口 = `CLD_TRUSTED_HOSTS` 环境变量
- `dsh-web.log` 中 `trusted: ` 为空 = collectTrustedHosts 探测失败（采集失败无告警）
- CLD.app 签名封口破损（app.asar 被替换后）：`codesign --force --deep --sign -` 重签（待用户确认执行）

## 待办（总线侧）
- v0.2：消息重放去重（from+thread+text 指纹）+ agent_profiles 能力登记工具
- 重启窗口协调（30 会话短暂中断）

## ⚠️ 高危操作护栏（CLD-008，2026-08-16 闪退复盘后确立）
- **禁止**未经协调执行：pkill/kill 宿主进程、launchctl bootout、重写 profile 的 package.json/cordis.patch.yml、全量 node_modules 操作
- 上述操作**必须**：先 `agent_light`/`agent_lock` 声明目标资源 → 走维护窗口协调（6e49710e）→ 完成后广播结论
- 违反案例：28ca132e（=43b1a2d3 续任）23:46-23:49 未协调执行 4 次 pkill -9 + 两次改写 package.json（5-bundle + 3 处 coreuleung 拼写）→ 全插件挂载失效 + 宿主闪退（SIGKILL 无转储）
