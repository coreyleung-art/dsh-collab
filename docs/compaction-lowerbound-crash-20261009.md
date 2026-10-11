# 会话硬死锁：compaction 下界 > 被遮内容 —— 病种登记与门建议

> 版本：v1 · 登记于 2026-10-09T06:36+08:00
> 作者：**外部第三方（Claude Code 会话 · CU 实验台线）** —— 经用户 2026-10-09 明确授权登记
> 状态：**已复现一次（一手日志可查），机制为推断**（见 §4 「证据等级」）
> 关系：**补 §7 CLD 崩溃风险登记**（拟编号 **P26**，拟门 **G-CR16 / G-CR17**）；**修正 W0.1 的验收判据**
> 一手证据：`~/.dsh/sessions/--Users-coreyleung--/session-fa1f9150-c949-401f-ba8c-d265f6221676/session.jsonl.zstd`

---

## §1 症状（一句话）

**进程不崩、CLD 不崩、会话看着还在，但那个会话再也发不出任何一次请求**——不是被 OOM 杀，是**被自己的压缩器锁死**。

与既有 P16 的区别（同族不同病）：

| | P16（既有） | **P26（本件）** |
|---|---|---|
| 形态 | **崩溃** SIGABRT → `dsh-crash-after-child` | **不崩**，只是请求被拒；进程与 CLD 均存活 |
| 触发量级 | ~1,180 万事件（装载对象数 > V8 堆上限 4192MB） | **只超 3,242 token（0.31%）** |
| 是否可救 | 归档重建 + 记忆继承包 | **会话内自救路径（compaction）已失效** |
| 谁先杀会话 | 操作系统 | **压缩器自身的开销下界** |

---

## §2 一手日志（逐条实录，可独立复核）

会话 `session-fa1f9150-c949-401f-ba8c-d265f6221676`（createdAt `2026-08-16 20:01:44`，cwd `/Users/coreyleung`，`agentPreset: standard`）。压缩后文件 **257,009,285 B**，**894,621 条 JSONL 记录**，末回合 `turn=11170`。

```
03:03:28  compaction/end   {"compactionId":"2b8bfa76-…","turn":11170,
                            "error":"summary is not smaller than the shadowed
                                     content (3435 estimated framed tokens >= 2466)"}

03:03:28  turn/end         {"turn":11170,"reason":{"kind":"error","error":{
                            "message":"This model's maximum context length is 1048576
                             tokens. However, you requested 1051818 tokens
                             (986282 in the messages, 65536 in the completion).
                             Please reduce the length of the messages or completion.
                             (request_id: d1e73db0-5587-48a7-be3d-533631d0a240)",
                            "code":"CONTEXT_WINDOW_EXCEEDED","status":400}}}

03:06:03  command/run      {"commandId":"cmd-e7e08271-4","name":"compact",
                            "args":"","source":{"kind":"user"}}      ← 用户手动压一次

03:06:16  compaction/end   {"compactionId":"aa144bb1-…",
                            "error":"summary is not smaller than the shadowed
                                     content (3450 estimated framed tokens >= 2466)"}

03:06:16  command/done     {"commandId":"cmd-e7e08271-4","kind":"error",
                            "text":"Compaction could not produce a useful summary.
                             The conversation is unchanged; the attempt is recorded
                             in the session log."}

05:39:52  session/end-seed {}
```

**自动压一次、手动压一次，两次都死在同一个判据上。**

---

## §3 机制（算术 + 判据，可直接验算）

### 3.1 请求超限的部分**全部**来自 completion 预留

```
上限                        1,048,576
实际请求                    1,051,818
  其中 messages              986,282   ← 正文，比上限低 62,294
  其中 completion 预留        65,536
超限                         3,242    = 1,051,818 − 1,048,576
```

⇒ **正文本身装得下。** 超限 3,242 token **完全等于** completion 预留挤出的部分。这是「**被预留位顶死**」，不是「内容真的装不下」。

### 3.2 compaction 的死结：压缩器的开销**大于**它要遮住的东西

两次报错都是同一形态：`摘要框架开销 (3,435 / 3,450) ≥ 被遮内容 (2,466)`。

压缩器有一条自洽判据：**摘要必须比它要替换的内容更小**，否则没意义。而当会话已经压到很瘦时，**待遮的活跃窗口本身只剩约 2,466 token**，可压缩器的框架开销（指令 + 占位 + 结构）却恒在 3.4k 上下 ⇒

> **存在一个下界：活跃窗口一旦瘦到低于压缩器自身开销，compaction 就永久失效。**

这不是 bug，是判据的必然推论；但它意味着 **`compaction` 这条「会话内唯一的自救路径」在最需要它的时刻恰好关闭**。命令回执亦明说：**"The conversation is unchanged."** —— 试过了，什么都没变。

### 3.3 为什么本会话会走到这个下界

会话自 `2026-08-16` 起活到 `2026-10-09`（约 54 天），`turn=11170`。它此前已被反复压缩过；活跃窗口已经被压得很瘦——**越靠近下界，越压不动；而越压不动，就越靠近下界**。

---

## §4 证据等级（R030：把推断与实测分开写）

| 项 | 等级 |
|---|---|
| 四段日志原文、时间戳、`request_id`、token 数 | **实测**（一手 JSONL，可 grep 复核） |
| 894,621 记录 / 257,009,285 B / turn=11170 / createdAt | **实测** |
| 「超限部分全部来自 completion 预留」 | **算术**（上面 3.1 可自行验算） |
| 「压缩器下界导致永久失效」 | **推断**（由两次同形报错 + 判据语义推得；**未读压缩器源码**，未见其常量定义） |
| 「调小 `max_tokens` 即可复活该会话」 | **未验证的假设**——见 §5，**未做任何尝试** |
| 「该会话此后仍被写入」 | **实测**（见 §6） |
| 是否会影响其他在役会话 | **未测，不作陈述** |

---

## §5 可能的出路（**均未验证**，按代价排序）

1. **把那一发请求的 completion 预留压到 ≤62,294** ⇒ 正文即可发出；发出去之后 compaction 有窗口可压，死结或可解。
   代价：CLD 侧配置动作，**需用户决定**；且不保证压完之后真的能缩。
2. **会话外接手**：不复活原会话，把认知迁到新会话（本目录正在做的事）。
3. **归档重建 + 记忆继承包**（与 P16 同路）。

⚠️ **本会话（外部第三方）未执行其中任何一条**，也未重启 CLD、未改任何配置。

---

## §6 附带的第二个观察（**实测**）：会话 `end-seed` 之后**仍在被写入**

```
05:39:52  session/end-seed   seq 16083203
06:29:39  agent/inbox/spliced seq 16083204  target=next-step
          from session-b250bf9d  thread=thread-mv03zyfm-…  「看黑板 notes/mac-mini/…」
06:30:08  agent/inbox/spliced seq 16083205  target=next-step  start=1
          from session-b250bf9d  thread=thread-mv040l4f-…
```

文件体积同步增长：**05:39 → 257,009,285 B；06:29 → 257,009,856 B**。

⇒ 这正是本计划 §2 因果链上那个物化点（`agent_send → store.addMessage → persist → deliver/followup`）在**往一具已经锁死的会话里继续灌消息**。

- **实测**：`session/end-seed` 之后日志仍有新记录；记录来自 `session-b250bf9d`，`target="next-step"`。
- **未验证**：这些 splice 是否真的会唤醒回合（观察窗内**未见**其后的 `turn/start`）；因此**不敢断言**它们会把会话推得更死。
- **但可断言一条**：**只要会话文件还在长，它离上限只会更远，不会更近。** 若要保留 §5.1 那条复活路径，**先止血**。

---

## §7 建议的门（拟编号，待 §7 登记时定案）

| 门 | 内容 | 为什么 |
|---|---|---|
| **G-CR16 请求前 token 预算门** | 发请求**前**按 (messages + completion 预留) 对上限做校验；超限 ⇒ **明确报错 + 指出超额来自哪一侧**，不得靠 compaction 兜底 | 本件中超限 100% 来自预留 ⇒ 报「上下文超限」是**误导**，会把人引向错误的修法 |
| **G-CR17 压缩有效性门** | 压缩后必须**记录降幅**；`摘要 ≥ 被遮内容` ⇒ 判**「压缩不可用」并**立即**升级为会话级告警**，**不得静默重试**（本件两次尝试均被静默记账） | 「试过了、什么都没变」若无人看，就是一小时后的 `end-seed` |

### 并修正 **W0.1 / G-CR9** 的验收判据（**这是本件最重要的产出**）

现判据：**「触发 ≥1 且体积降 ≥50%」** —— 本件形态下**触发了、降幅为负**，该判据会**给出绿**。
建议追加一条负控，六者齐备规则里它必须能红：

> **负控**：构造「活跃窗口已低于压缩器开销」的会话 ⇒ **必须判「压缩不可用」并告警**；
> **若判「已压缩」或静默通过，本条不得记 `closed_with_evidence`。**

---

## §8 本件对计划自身的意义（自我指涉，须与正文分开读）

本计划 W0.1 的**正控**写的是「挂载 compaction」——而本件证明：**挂载了也可能等于没挂**。
这正是计划自己在 §4.3 列的**半修形态③「修站点不修不变量」**、以及 §0.1 的**「🟡 在位未生效或不可观测」**同一条病：
**开关装上 ≠ 机制生效 ≠ 结果可控。**

⇒ 建议把本件列为 **C7（证伪门与半修清单）的一个新样本**：**第 10 条半修——「compaction 在位，但在下界以下不可能生效」。**
