# 星台 & 语音迭代需求文档 v0.1（R1-R4）

> 2026-09-09 · 星桥编录 · 范围：用户圈定的三块（治理收件箱 / 晨报订阅 / 语音笔记·静默会议助手）
> 基础能力盘点（实测在库）：CLD-Voice（MBP 侧 cld-voice/backend：asr_server.py · stream_bridge.py(8903 流式 ASR) · duplex_bridge.py(8904 全双工 Seeduplex 1.2.6.0) · 成稿引擎）；mac-mini 已部署 8903 桥(launchd com.dsh.voice-bridge) + 插件 L1(CLD 内可用)；whisper 本地 MVP(单句 ≤2s, POC2 pass)；外网受限已用 hf-mirror。

---

## R1 📮『待你决定』收件箱（治理痛点 · 星台）

**目标**：把散落各处「需老板拍板」的事项聚合为星台一个徽标页，手机上决定即回。

**聚合源（现有）**：
| 源 | 形态 | 位置 |
|---|---|---|
| R008/角色任命/高危动作审批 | pending 审批单 | agent_approval / dsh_approval 状态 |
| 三方会签待签 | pending 提案 | data/registry/convention-proposals/*.json |
| L3 人类求救 | node-sos 模板触发 | 桌面模板/黑板 |
| DeepSeek 低余额 | balance < 阈值 | sb server 余额缓存 |

**改动**：
1. server.js 新增 `GET /api/pending-decisions` → 聚合上面源（读本地黑板 data/registry + 审批状态 JSON + 余额缓存），输出 `[{id,kind,title,detail,ts,urgency}]`
2. iOS 新增首页徽标 + 「待你决定」列表页（kind 图标/urgency 排序/一键决定）
3. **决定回写通道（关键设计）**：手机批准/拒绝 → `POST /api/decision {id,verdict,note}` → server 写黑板 `data/ops/decision-<id>` 回执卡 → coordinator（星桥）订阅桥接执行（approve 转真实审批 API/会签状态推进）。诚实标注：harness 审批非 HTTP，需 coordinator 桥接一跳。

**验收**：造 1 个 R008 pending → 星台徽标 +1 → 手机批准 → 状态转 approved（黑板可见）。

## R2 ☀️ 晨报 / 订阅推送（星台）

**目标**：醒来一屏看全局：昨夜订单/差评/agent 产出/待办。

**聚合源**：waimai_report(昨订单/差评)、hr-daily-sync、守灯健康摘要、黑板迭代报告(昨 agent 产出)、R1 待办数。

**改动**：
1. server.js `GET /api/morning-brief` → 时间线卡（分节：订单 / 差评 / Agent 动态 / 待你决定 / 健康）
2. iOS 早报页 + **本地通知**（UNUserNotificationCenter 定时 08:00，iOS 首次请求通知权限——需用户授权，诚实标注非 APNs）
3. 订阅开关（哪些节入简报/推送）

**验收**：打开星台首页见昨日聚合卡；授权后 08:00 本地通知到达（App 在后台存活时）。

## R3 🎙️ 语音即笔记（cld-voice 基础）

**目标**：随口说 → 转写 → 自动成稿归档（黑板 + Obsidian），语音即笔记。

**场景**：开车/干活时对星台或 CLD 说「记一下…」→ 落一条带时间戳的语音笔记。

**改动**：
1. 复用 mac-mini 8903 桥（已部署）+ whisper/火山转写（whisper 本地为默认——静默/隐私友好）
2. server.js `POST /api/voice-note {text}` → 写黑板 `data/notes/voice-<ts>` + 可选归档 Obsidian（现 obsidian-server MCP 通道）
3. iOS 语音笔记页（列表/重听/转写校对/标签）

**验收**：说 30s 中文 → 转写正确率≥预期(whisper 级) → 黑板落卡可检索；说「归档」关键词自动入 Obsidian。

## R4 🤫 静默会议助手（旁听长时 · cld-voice 端到端基础 · 重点）

**目标**：设备放会议旁**静默旁听**（不打断不出声），长时会话 → 自动成结构化纪要（议题/要点/待办/分工）。

**依赖基础**：8903 流式 ASR(interim/final) + 8904 全双工协议(committ/静音尾包=话轮边界，已验证) + 成稿引擎(asr_server)。

**设计**：
| 环节 | 方案 | 依赖 |
|---|---|---|
| 采集 | mac-mini 常驻旁听模式(接麦克风/系统音频, 16k PCM 分包——复用插件管线) | com.dsh.voice-bridge |
| 话轮切分 | VAD / 1.2s 停顿 commit(已验证踩坑5) | 8904 协议 |
| 长时拼接 | 流式分片→时间戳序列→超长自动分段存档(30min 不丢) | 成稿引擎扩展 |
| 说话人区分 | v0 靠话轮顺序标 发言人A/B；diarization 列 P1(外部引擎/火山可选) | 开放项 |
| 静默纪要 | 成稿引擎模板化(议题/要点/待办/分工, markdown) | asr_server |
| 归档 | 黑板 notes/meetings/<date>-<topic> + Obsidian | R3 归档链复用 |
| 隐私 | 音频本机处理；仅文本上火山(若用云端 ASR)；磁盘可设保留期 | 设计约束 |

**开放项（诚实标注）**：
- 语音引擎二选一：whisper 本地(隐私/离线/单句已验证) vs 火山流式(长时准确, 需 key 流式权限)——建议双通道、默认本地
- 说话人分离 v0 从简(A/B 按话轮)，真 diarization 需评估外部服务
- 会议助手运行宿主：mac-mini 常驻(桥已就位)；接入 CLD-Voice 运行时 vs 独立旁听进程——留 MVP 里程碑评审

**验收**：旁听 2 人 30min 对话 → 产出 markdown 纪要（议题≥2/待办带归属）；中途可在星台看进度；手机可打开纪要并转发。

---

## 分期建议
- **P1(近期)**：R1 收件箱(治理最高频) → R3 语音笔记(复用已部署桥，1-2 天级)
- **P2**：R2 晨报(聚合+本地通知授权) → R4 会议助手 v0(旁听-成稿单机闭环)
- **P3**：R4 说话人分离/多会议管理 → 语音全双工对话态（并入 CLD-Voice MVP 里程碑评审，防双栈）

## 归属与仓库
- 星台侧(R1/R2/R3 入口)：~/sb-mobile（git tag 管理，见 CHANGELOG）
- 语音引擎(R3/R4 内核)：cld-voice（MBP 后端 + mac-mini 桥），L1 已部署
- 本需求文档：dsh-collab data/reports/requirements/（随版本管理）
