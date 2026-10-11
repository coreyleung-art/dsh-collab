# 通讯规范端口（Agent Communication Portal）v1 · 2026-10-02

> **一句话**：AI 要做任何跨会话/跨设备/通道相关操作前，先查本页拿「正确姿势」——照做零摩擦；
> 走错的路径会被结构门（channel-gate / bb-card-send / drift-scan / launchd-scan）拒绝，**拒绝消息里也带回到本页的指引**。
> 双轨原则（用户 2026-10-02 指示）：**堵截（门）+ 引导（本端口）缺一不可**——只有堵截，AI 会反复撞门；只有引导，AI 不知道哪条路是对的。

## 0. 操作类型 → 正确路径（总表）

| 我要做什么 | 正确路径（照做） | 工具/命令 | 走错的后果 |
|---|---|---|---|
| 同机会话间发消息 | agent_send（≤50 字 + 内容落黑板再发「看黑板」指针） | agent_send 工具 | 全文 >50 字被 v2.4 门禁拒绝 |
| ★ 跨设备发消息 | **只有黑板卡一条真通道**（双写两板） | `bb-card-send` | agent_send 跨机不通：静默排队 7 天进 DLQ（MBP 实测 146 条 0 送达）；1.5.9 前别名路径还返回假 delivered |
| 跨设备发内容卡 | 双写两板 + 回读断言 + to 必填完整 id | `bb-card-send`（CLI/工具） | 漏 to → 对端白名单静默不注入（2026-10-02 事故） |
| 要求对方回复 | 信封 reply_required=true（同机用 agent_send 参数；跨机=卡上标 reply_required:true） | agent_send / 卡字段 | 通知语义 → 对方空闲时排队不唤醒 |
| 变更任何通道/守护 | 先登记变更单（5 字段+回滚点真实存在）→ 人工执行 → 后跑 drift-scan | channel-gate register → 执行 → drift-scan | 不过门=变更不可表达；熔断中=机械拒绝 |
| 探测通道健康 | drift-scan（9 项矩阵）+ launchd-scan（job 加载） | 两工具 CLI | 漂移/静默失效不被发现 |
| 接入新设备/新会话 | 按 §5 自检清单 → 回执给协调者 | — | 注册表不在册、心跳旧 |
| 报修 | 降级纪律 v1 §五 求救提示词（结构化） | 模板见 §6 | 边求救边乱试 |

## 1. 发消息（三种语义，别混用）

| 语义 | 正确姿势 | 反例 |
|---|---|---|
| 通知（不要求回复） | 内容落黑板 → 发「看黑板 <key>」短指针 | 全文直发（被门禁拒）；要求回复却用通知（对方不唤醒） |
| 要求回复 | `reply_required: true` + 明确问题 | 无标记的「请回」 |
| 紧急 | urgent 标记豁免 + 仍尽量短 | 把 urgent 当日常用 |

## 2. 发卡模板（合法示例，可直接套用）

```bash
echo '{"type":"<类型>","title":"<标题>","content":"<内容>","sent_at_epoch_ms":<ts>}' | \
  /opt/homebrew/bin/node ~/dsh-plugin-bb-card-send/cli.js \
  notes/<域>/<key> session-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx --stdin
```

门规则：to 必须完整 session id（短 id/别名会被 G2 拒）；payload 不得含 from/from_label/to（防伪造署名）；key 首段纯小写；写后自动双写两板+回读断言。

★ 卡片结尾的回复指引（2026-10-03 MBP 通道诊断后修正）：**跨机回复写「回复请写 notes/<对端>/ 卡」**；不要写「回复请调用 agent_send」——那条路跨机不通且会静默过期（曾经还返回假 delivered）。

★ 即刻协议（2026-10-03 通讯连续性事故，运行代码即生效）：**凡要求对方行动的卡，必须带 `reply_required: true` + `awaiting: <对方>`**——I7a 唤醒已在运行代码中生效，缺 reply_required 的「看黑板」指针不唤醒收方，是 11.5h 互相等待的直接机制根因。方案 A（默认唤醒）部署后，reply_required 降级为「更强提示」语义，此协议自动放宽。

★ 球权字段（2026-10-03 死锁事故采纳，MBP 提议）：**凡要求对方行动的卡，必须带 `awaiting` 字段**（如 `awaiting: "mbp"` / `awaiting: "mac-mini"`），显式声明球在谁手上；发送方设了它就不许再自行「等」。判据：无 awaiting 且要求行动 ⇒ 协议缺陷（R030 无验证不陈述的通讯版）。

## 3. 变更通道模板（channel-gate 合法变更单）

```json
{
  "channel": "bus-8791",
  "action": "换轮询间隔 5s→10s",
  "evidence": "对照探测：GET /bus/receive 连续 3 次 >5s 超时；同机黑板 GET 200 正常（排除本机网络）",
  "rollback": "~/dsh-collab/guard/backups/device-daemon.py.bak-good-*",
  "blast_radius": "跨设备信封投递延迟翻倍；仅 mac-mini 侧守护"
}
```
然后：`echo '<上面JSON>' | node ~/dsh-plugin-channel-gate/cli.js register --json`
登记成功后人工执行变更，执行后跑 `drift-scan` 确认无漂移。**熔断中（24h>2 次）会被机械拒绝，等解冻或找协调者裁决。**

## 4. 探测健康（只读，随时可跑）

```bash
/opt/homebrew/bin/node ~/dsh-plugin-drift-scan/cli.js          # 通道漂移 9 项（0=绿）
/opt/homebrew/bin/node ~/dsh-plugin-launchd-scan/cli.js        # job 静默失效（71=…）
curl http://xingqiao.meetfunbp.com:8792/data/discovery/agents/<dev>  # E2 注册表（status+hb_age_s）
```

判活口径：只信**心跳 payload ts**（hb_age_s<90=online）；键体 ts 会被镜像刷新（伪新鲜）。

## 5. 接入新设备/新会话自检清单（MBP 接入流程的通用化）

1. 心跳：守护每 60s 写 `nodes/<dev>/heartbeat`，payload 带 ver 字段。
2. 注册：`data/discovery/agents/<dev>` 含你的完整 session id（不在册 → 告诉协调者，由心跳代理写入，禁止会话直写 R-ERR4）。
3. 通道：跨设备内容走黑板双写（notes/<目标域>/），信封走 bus-8791（X-Webhook-Token，0600，勿明文）。
4. 验证：发一张测试卡 + 「看黑板」指针 → 等对端 ack（acked=claimed 才算已消费，delivered 是临时态）。
5. 自报版本：node-bridge/dsh-tools/插件版本写一张卡给协调者。

## 6. 报修模板（降级纪律 v1 §五）

```
🚨 [节点求救] <设备名> <时间戳>
症状: <具体现象+持续时长>
已自动尝试: <守护重连N次/降级留痕X条>
仍失败原因: <如有判断>
本地数据: <日志/黑板键路径>
请求: <期望动作：重启服务器/检查xingqiao/恢复黑板/人工转发>
```

## 附录 A. 门拒绝消息 → 正确姿势对照

| 门拒绝（error） | 正确姿势 |
|---|---|
| MISSING_FIELD evidence | 补一条对照探测（同动作对健康对象测一次） |
| ROLLBACK_MISSING | 回滚点写真实存在的路径，或改为「kill 进程即回滚」式描述 |
| UNKNOWN_CHANNEL | 通道名查 §0 矩阵（7 个枚举之一） |
| CHANNEL_FROZEN / MELT_DOWN | 等解冻或找协调者裁决，勿绕门 |
| NO_TO（发卡） | 用 agent_peers/E2 注册表查完整 session id |
| FORGED_FROM | 删掉 payload 里的 from/from_label——工具自动注入 |

## 附录 B. 禁用清单（实测会崩/会坏的通道）

- **禁用 `POST http://127.0.0.1:31888/reload`**：CLD 壳 main.js:570 存在 `undefined.reloading` 缺陷（2026-10-02 16:29 实测触发 uncaughtException → 壳崩溃自动重启）。插件代码生效走正常重启，不走热重载。
