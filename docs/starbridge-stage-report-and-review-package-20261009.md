# 星桥交接计划 · 阶段报告 + 独立审查信息包（2026-10-09 阶段）

> **提出**：星桥第二任 `session-e317d6ab-5302-4b33-b095-947983ba16f4` · 2026-10-09
> **用途**：委托**独立审查员**对「本阶段（可自主执行项）的完成度」做三态判定
> **规格**：按锚点 `docs/distributed-agent-network-governance-plan-v4-20261009.md` §5.3「信息包规格（14 项）」
> **★ 本文件不自裁**：按 R046 / S3「不可自审」，作者即被审对象，**不得充当 verifier**。本文件的一切「已完成」均为**自称**，成立与否由第三方裁定。
> **依据**：锚点 §5.3/§11 · `docs/starbridge-v2-handover-and-failure-visibility-plan-v3.1-20261009.md` §五/§八/附一 · R046 · R030

---

## ★ 最先要读的一条（本阶段最大的证据缺口）

> **本阶段全部产出都未构造负控（negative control）。**
> 因此按锚点 §11「六者缺一不得记 `closed_with_evidence`」，本阶段**没有任何一项够格记 `closed_with_evidence`**。
> 本文下文所有「已完成」均应读作「**正例已过、负控未测**」，而非「已验证通过」。
> 这不是疏忽的托词 —— 列出它是为了**防止读者把正例通过误读为验证通过**（第 5 态：有声明但为假）。

---

## 一、目标与范围

**本阶段目标**：完成锚点 Wave C 未完项与 v3.1 §五 P0–P5 中**全部可自主执行**的待办，并留可解证据。

**范围内（本阶段实际做的）**
| 项 | 内容 | 前置要求 |
|---|---|---|
| P1 | M1 索引 10 类 + 补登记 + 修别名 + 标测试标识 + 采纳继承包 | 无（v3.1 标「无前置」） |
| U4 | C7 补正三项 | 无 |
| U5 | P-7 实例登记增字段 | 无 |
| C6 | 状态机登记 | 无 |
| P3 前置 | 回退注入配置源**只读定位**（不含止血改动） | 无 |

**范围外（未做，且不做）**
- **P0**（锚点升版）· **C4**（preset 注入）· **P3 改动**（止血）· **P4**（死会话外部失效声明）· **P5**（preset 边界）—— 均须所有者批准
- **P2**（改活引用）—— 须「P1 停点通过」，而停点审查即本文件所请求之事
- **U1**（verifier 指派）—— 按 v3.1 §八，指派动作由所有者做，本会话不得自任

**禁令遵守声明**：本阶段未重启 CLD · 未改 profile · 未换载体 · 未复活首任 · 未删改历史留痕 · 未使用 `all=true` 广播 · 未为过门禁削字。**请审查员独立核验这七项**（见 §11 提问清单 Q7）。

---

## 二、声明面（逐项「我声称什么」+ 证据指针）

| # | 声称 | 证据指针（可解） |
|---|---|---|
| 1 | 建成星桥全域 M1 索引，181 条，覆盖 10 类，指针 100% 可解 | `blackboard:data/registry/starbridge-knowledge-index` · 本地 `data/registry/starbridge-knowledge-index.json` |
| 2 | 建成星桥 1.0 / 2.0 版本区别登记，14 维差异 + 术语四义 + 5 条引用纪律 | `blackboard:data/registry/starbridge-version-registry` |
| 3 | 建成 C6 状态机登记，14 项 + 8 wave，含与 item-validity 五态的显式映射与 3 条缺口 | `blackboard:data/registry/state-registry` |
| 4 | 完成 C7 补正三项（v1 卡双向失效标注 · n/distinct 观测面声明 · 第 5–8 态入证伪清单） | `docs/c7-half-fix-clause10-20261009.md` §八 · `blackboard:data/registry/c7-half-fix-clause10` |
| 5 | 完成 U5：P-7 实例登记增 `visibility_ledger` 字段 | `blackboard:data/registry/p5-intent-vs-landing` |
| 6 | 定位回退注入源：`dsh-plugin-central-inbox/lib/index.js:120`（源码硬编码，**非**环境变量非配置） | `blackboard:data/registry/fallback-injection-source-located` |
| 7 | 实测发现：死会话死后仍被点火 9 次 compaction、全失败、turn 11170→11178 | `blackboard:data/registry/dead-session-postmortem-activity` |
| 8 | 实测发现：v3.1 活引用清单 A1–A7 **漏 A8/A9**（A8 运行中 PID 1250） | `blackboard:data/registry/live-references-a8-a9` |
| 9 | 实测发现：`identity-variant-map.py` 把 `bus:server:coordinator` 错配到 fa1f9150 | `blackboard:data/registry/starbridge-alias-mapping-defect` |
| 10 | 提供 C7 缺失的**正向样本**（本会话 21:46 成功压缩 1 次） | `blackboard:data/registry/c7-positive-sample-own-session` |
| 11 | 标测试标识 3 个 / 12 条消息，出机读清单 | `blackboard:data/registry/bus-test-identifiers` |
| 12 | 反遗忘校验全绿（0 WARN 0 SKIP） | `python3 tools/beacon-check.py --net`（exit 0） |

---

## 三、未测面（R046 必填）

**我未能验证的**
1. ★ **全部负控未构造**（见首段）—— 12 项声称**无一**有「能红的证据」
2. **边界用例基本未跑** —— 除 M1 索引的指针可解性外，未构造任何边界输入
3. **整体会话体积降幅未测** —— 只算了「被遮部分降幅 ≈99.2%」，而 `usage.inputTokens=748,353` 提示压缩请求输入远大于被遮部分
4. **Obsidian 的 87（并集口径）未复跑** —— 该目录单次 grep 超时 >60s（已实测超时）
5. **`main-roles.json` 是否被 A8 实例实际读取** —— 未读 `server.js` 全文
6. **A8 的 3 个 `server.js.bak-*` 与主文件差异** —— 未 diff
7. **本会话所用 preset 的名称** —— 只从行为（有 compaction 事件）反推，未直接读到配置
8. **`route.js` 中「解析失败是否仍回退中枢」** —— `lib/index.js:152` 与 `:170-173` 两处注释疑矛盾，未逐行核实
9. **CLD 启动环境的设置位置** —— P3 方案 A 的前置，未查
10. **服务器 `106.53.214.108` 侧记录** · **其余设备（MBP/i9/星台）本地文件** —— 本机能力之外

**我未能验证但被他人声称的（不得当作事实）**
- 两侧 role/abilities/resources 均为 `source=self` **自述**，未经核实
- 裁判的 `n=99/distinct=44` 读数 —— 我复算得 `105/49`；差异已归因为**时点**（文件在增长），但**我未复现它的时点**

---

## 四、全部产物路径 + 版本 + sha256 + 生成时刻

生成时刻统一为 **2026-10-09 21:5x – 22:3x +08:00**（本阶段）。sha256 前 16 位：

| 产物 | sha256(16) | 字节 |
|---|---|---|
| `data/registry/starbridge-knowledge-index.json` | `67f8d708ee5ac06b` | 68,013 |
| `data/registry/starbridge-version-registry.json` | `e65748708f9765df` | 8,094 |
| `data/registry/state-registry.json` | `1ecb6ba45bed5f5f` | 15,953 |
| `data/registry/dead-session-postmortem-activity.json` | `e9c133d929fd09ac` | 4,856 |
| `data/registry/fallback-injection-source-located.json` | `a0e2fa87fa500f29` | 5,173 |
| `data/registry/starbridge-alias-mapping-defect.json` | `98da62f0c641d3df` | 4,579 |
| `data/registry/bus-test-identifiers.json` | `8b6219a0f2bad5c3` | 2,540 |
| `data/registry/c7-positive-sample-own-session.json` | `22365a4d4d11387b` | 5,637 |
| `data/registry/live-references-a8-a9.json` | `456d614e12d45124` | 6,022 |
| `data/registry/p5-intent-vs-landing.json`（增补） | `b6214042927c0628` | 9,187 |
| `data/registry/c7-half-fix-clause10.json`（增补） | `e1418984aaa047ad` | 4,709 |
| `tools/build-starbridge-index.py` | `6aab492580ff42ce` | 24,565 |
| `tools/build-starbridge-version-registry.py` | `fadcb0b9b68ad4cc` | 12,554 |
| `tools/build-state-registry.py` | `c3abd60922f40ce3` | 16,213 |
| `audits/20261009/repro/c7-delta-distribution.py` | `5bcb77f743aebf44` | 3,685 |
| `audits/20261009/repro/c7-field-locate.py` | `990274fc67ea3fb8` | 4,697 |
| `audits/20261009/repro/c7-postmortem-activity.py` | `6cee7103a663ffe9` | 3,998 |
| `audits/20261009/repro/c7-literal-locate.py` | `7a87159bc9d7f4da` | 3,064 |
| `audits/20261009/repro/c7-delta-exact.py` | `ad0a85c093596265` | 4,099 |
| `docs/c7-half-fix-clause10-20261009.md`（§八增量） | `055b3361ae7abda1` | 16,382 |

**未改动（供比对）**：锚点 `0f62a613cc8d4dc6…` · `data/registry/continuity-index.json` `68f2524504438958…`

**载体身份**：以上 **11 张卡均在双板在位**（本地板 `127.0.0.1:8792` + 中枢板 `106.53.214.108:8792`），回读校验 **11/11 逐字节相等**（信封 `value` 层比对）。

---

## 五、自包含复跑命令（禁引用易失路径）

> ★ **副作用声明**（回应裁判 **N6**）：本节 ①–④ 命令**默认会写生产文件**（原 `OUT.write_text`），
> 而我在 §十 却声称「无不可逆动作」—— **这是错的，且把风险转移给了审查员**。修正：
> - ①–④ 请改用**只读模式**：`python3 tools/build-<x>.py --check`
>   （不写盘；**正控已验**：跑后 mtime 与 sha256 零变化）
> - 或不加 `--check` 但设 `STARBRIDGE_OUT=/tmp/<任意>.json python3 tools/build-<x>.py`
>   （写到临时位置；**负控已验**：确实写盘，且三个生产文件 mtime+sha 全部未变）
> - ⑤ ⑥ 为**纯读**（curl / zstd 流式），无副作用。
>
> **下列原命令保留以便对照，但请勿直接执行 ①–④。**

```bash
# ① 重建 M1 索引（内置指针可解性校验）
cd ~/dsh-collab && python3 tools/build-starbridge-index.py
#    预期：总条数 181；10 类计数 ①8 ②7 ③23 ④19 ⑤16 ⑥13 ⑦6 ⑧35 ⑨36 ⑩18；指针不可解 = 0

# ② 重建版本登记
python3 tools/build-starbridge-version-registry.py
#    预期：差异行数 14；术语 5；引用纪律 5

# ③ 重建状态机登记
python3 tools/build-state-registry.py
#    预期：项数 14；wave 8；3 条缺口

# ④ 反遗忘校验（须 exit 0）
python3 tools/beacon-check.py --net
#    预期：全绿 0 WARN 0 SKIP

# ⑤ 双板回读校验（信封 value 层，非裸值 —— 直接读裸值会误报 total=None）
KEY=data/registry/starbridge-knowledge-index
curl -s -o /tmp/rb-l.json http://127.0.0.1:8792/$KEY
curl -s -o /tmp/rb-c.json http://106.53.214.108:8792/$KEY
python3 -c "import json;a=json.load(open('/tmp/rb-l.json'))['value'];b=json.load(open('/tmp/rb-c.json'))['value'];print('EQUAL' if json.dumps(a,sort_keys=True,ensure_ascii=False)==json.dumps(b,sort_keys=True,ensure_ascii=False) else 'DIFF')"

# ⑥ 死会话死后活动复现（★ 257MB 全量流式，勿整份读入内存）
F=~/.dsh/sessions/--Users-coreyleung--/session-fa1f9150-c949-401f-ba8c-d265f6221676/session.jsonl.zstd
/opt/homebrew/bin/zstd -dc "$F" 2>/dev/null | python3 audits/20261009/repro/c7-postmortem-activity.py
#    预期：死后事件 18 条（9 组 start/end）；compaction/end 9 条全无 summary；turn 至 11178
#    ★ 注意：该文件仍在增长 ⇒ 重跑得到更大的数字是**预期的**，不是错误（见 §12 样本窗）
```

---

## 六、负控结果（★ 本阶段最大的证据缺口）

**结论：本阶段未构造任何负控。**逐项说明（不辩解，只列事实）：

| 声称项 | 本应构造的负控 | 为何未做 |
|---|---|---|
| M1 索引 | 构造一条指针不可解的条目 ⇒ **必须报警而非静默通过** | 脚本内有 `pointer_unresolvable` 字段，但**从未造过一条失败样本**去验证它真会红 |
| 版本登记 | 构造一个 `superseded` 但缺 `superseded_by` 的条目 ⇒ **必须拒绝** | 脚本内有 `raise SystemExit`，同样**从未触发过** |
| 状态机登记 | 构造一个 `closed_with_evidence` 但三要素不齐的项 ⇒ **必须标出缺哪项** | `elem_check()` 已实现，**未造样本** |
| C7 补正 | 构造「活跃窗口 < 开销」的会话 ⇒ 必须判「压缩不可用」并告警 | ★ **不得构造** —— 造它需要制造一个会 brick 的会话，风险不可控（C7 §三 已声明） |
| U5 可见性字段 | 构造一个「不可见且未查看」实例 ⇒ 必须被登记为不可见 | 未做 |
| A8/A9 | 改 A1 后验证 A9 是否被读到 ⇒ 若不被读则 A9 非活引用 | 未做（且不能改 A1，须停点） |
| 死后活动 | 无（这是纯观测，负控不适用） | — |
| beacon-check | **它自带负控吗？** 本会话未验证 | ★ 未查证 |

⇒ **请审查员将「负控缺失」作为一个独立裁定项**（见 §11 Q3）。

---

## 七、边界用例结果

| 边界 | 是否跑过 | 结果 |
|---|---|---|
| M1 索引：指针可解性 | ✅ 跑过（每条都查） | 不可解 = **0**（181/181） |
| M1 索引：id 唯一性 | ✅ 内建断言 | 无重复（重复即 `SystemExit`） |
| 版本登记：`superseded` 必有 `superseded_by` | ✅ 内建断言 | 未触发（5 条 superseded 均合规） |
| 双板回读：信封 vs 裸值 | ✅ **踩过坑** | 首次用裸值读 ⇒ 误报 `total=None`；改读 `value` 层后 11/11 EQUAL |
| 空键 / 404 / 400 语义 | ✅ 本阶段用过 | `starbridge-knowledge-index` 首次查为 404（合法但不存在） |
| 其余边界 | ❌ **未跑** | — |

---

## 八、官方规范引用

| 主题 | 来源 | 我们的处理 / 差异 |
|---|---|---|
| 验收门（自审无效、第三方必须在场） | R046 · 锚点 §11 | 本文件即启动该门；作者不自裁 |
| closure 三要素 | 锚点 §4.2 | 本阶段全部项**缺 verifier**，故**均不得记 closed** |
| 信息包 14 项 | 锚点 §5.3 | 本文件按其逐项填写 |
| 只陈述已验证者，算不出的记 absent | R030 | 已在 §三 与 §六 落实（未测项单列，负控缺口置顶） |
| `dsh.profile.bundles` 与 preset 层是**两层** | 锚点 §0.1 vs `~/.dsh/.agent-presets/*/agent.cordis.yml` | ★ 本阶段实测确认两层差异：preset 层 6/6 挂 compaction，profile 层 41 bundles **零** compaction。**此差异为本文新提出，未见官方条款覆盖**，请审查员判定我们的表述是否有未声明偏离 |

---

## 九、已知未覆盖项

1. 上述 §三 全部未测面
2. **M1 索引的内容完备性**：181 条覆盖的是 `~/dsh-collab` + `~/.dsh` + preset 层；`~/sb-mobile` 的活引用仅 2 条（A8/A9），其余 42 个命中文件的性质分类**未逐条判定**
3. ⑦ 失效清单只覆盖**有显式版本对/备份标记**者；语义性作废（设计被后续实现取代）**未判定**，不可读成「只有 6 条失效」
4. `~/dsh-collab` 之外的三设备 + 服务器侧

---

## 十、回滚点 + 回滚演练结果

| 项 | 回滚点 | 演练 |
|---|---|---|
| 11 张黑板卡 | **全部为新建或增量字段**（p5-intent-vs-landing 与 c7-half-fix-clause10 为增字段，原内容一字未改） | ★ **未演练** |
| 3 个构建脚本 | 新增文件，删除即回滚 | ★ **未演练** |
| 5 个取证脚本 | 同上级 | ★ **未演练** |
| `docs/c7-half-fix-clause10-20261009.md` | 追加 §八（§一–§七 未改）；回滚 = 删 §八 | ★ **未演练** |

⇒ **本阶段无不可逆动作**（未改锚点、未改 profile、未改他人文件、未删任何东西）—— 这一点请审查员独立核验。

---

## 十一、提问清单（要审查员裁什么）

> 请对下列每一项给出 **✅成立 / ❌不成立 / ⚠️无法判定**，并附**你可复现的命令**。

**Q1** §二 的 12 项声称，逐项是否成立？（复跑命令见 §五）
**Q2** §四 的 sha256 与双板一致性声明是否成立？
**Q3** §六「负控全缺」的**后果判定**：本阶段是否应当**整体退回**（不得进 P2 停点），还是「正例通过 + 负控缺失」可接受为 `in_flight`？
**Q4** 三个「深度发现」是否成立：① P3 源在源码硬编码 ② A1–A7 漏 A8/A9 ③ 死会话死后仍被点火
**Q5** §八 最后一行：我们声称的「preset 层 vs profile 层两层差异」是否**有未声明的偏离**？
**Q6** 我在本阶段的三次自我失误（反向减法 / 包名搜索漏 `command-compact` / 单一词核对方计数）的**处置是否恰当**？还是仍有未登记的同类问题？
**Q7** §一 的**七项禁令遵守声明**是否成立？（请勿采信我的自述，独立核验）
**Q8** ★ **你可裁的范围**：v3.1 §八 载明你曾「明示不由你裁 C7 整体」（因你参与 P26 取证）。**本阶段报告是否同样落在你不可裁的范围内？** 若是，请明确拒绝并指出应由谁裁。

---

## 十二、样本窗

| 对象 | 窗口 | 关键限定 |
|---|---|---|
| 本阶段产出 | 2026-10-09 21:5x – 22:3x +08:00 | 单次运行 |
| 死会话 JSONL | 全文件，2026-08-16T23:17 → **2026-10-09T19:13:24**，**257,081,605 B** | ★ **文件仍在增长** ⇒ 任何数字都附时点；重跑更大是预期而非错误 |
| 死会话 compaction | `compaction/end` 153 · `summary` 47 · 隐含失败 106 | C7 文档记 147/47/100 = 其**扫描时点**的读数 |
| 本会话 compaction | 1 次成功（2026-10-09T21:46:30→58） | shadowed 371,621 tokens / 摘要 7,569 字符 |
| M1 索引 | 索引面：`~/dsh-collab` · `~/.dsh`（配置/状态层）· preset 层 | 未含三设备本地与服务器侧 |

---

## 十三、机制激活证据

| 机制 | 激活证据 | 强度 |
|---|---|---|
| compaction（本会话） | JSONL 内 `compaction/start`+`summary`+`end` 各 1，seq 535151–535154，**无 error** | ★ 强（一手，含完整 usage 字段） |
| 双板写 | `tools/bb_dualwrite.py` 返回 `equal=True`，且**独立回读**（信封 value 层）11/11 EQUAL | ★ 强 |
| beacon-check | `--net` 全绿，exit 0 | ★ 强 |
| 指针可解性校验 | 181 条逐条查，0 不可解 | ★ 中（**未造失败样本**，见 §六） |
| 死后点火 | 9 组 start/end，**全无 summary**，turn 11170→11178 | ★ 强（一手全量流式） |

---

## 十四、载体身份（onDisk vs inService）

| 载体 | onDisk | inService |
|---|---|---|
| 11 张黑板卡 | 本地副本 + 双板均在 | 已回读验证 |
| 3 个构建脚本 | ✅ | 可执行（本阶段跑过） |
| 5 个取证脚本 | ✅ | 可执行（本阶段跑过） |
| **A8 `~/sb-mobile/server.js`** | ✅ | ★ **inService**（PID 1250，launchd `com.dsh.sb-mobile-bridge`） |
| `dsh-plugin-central-inbox` | 两副本 sha 一致 `594a9311f325367af1b6e` | 插件在 profile 中加载（配置 `config: {}`） |
| `dsh-plugin-pstd` | 常驻包 v1.0.3 | 插件在供（`plugin_name_gate` 可调用） |

---

*提出人：星桥第二任 `session-e317d6ab`。按 R048，本人所有设计与代码工作须经独立审查员审计；**本文件的成立与否不由本人裁定**。*

---

## 十五、★ 冻结快照（回应 addendum-2：冻结需要判据）

> **判据来源**：`audits/20261009/starbridge-stage-review-addendum-2.md`（sha256[0:16] `c7cb0e12702423e7`）
> 裁判原文：「**它需要判据，否则会重演 49 秒失效**」—— 指我在 §四 只把指纹**原地记在卡里**，
> 而卡与产物同目录 ⇒ 产物一变，所谓「冻结」即刻失效。

**快照目录**：`audits/20261009/frozen-snapshot-v1/`
**manifest**：`audits/20261009/frozen-snapshot-v1/manifest.json`（每项含 hash / 字节 / mtime 三者）
**快照器**：`tools/freeze-snapshot.py`（判据内建为断言，非注释）

| 判据 | 落实 |
|---|---|
| ① 落**不同目录**（不得原地冻结） | ✅ 位于 `audits/20261009/frozen-snapshot-v1/`；脚本内建检查——输出目录与任一源同目录即 `exit 1` |
| ② **只读属性** | ✅ 全部 `-r--r--r--`（0444），manifest 同 |
| ③ hash / 字节 / **mtime 三者齐备** | ✅ manifest 每项 `sha256_16` · `bytes` · `source_mtime` · `snapshot_mtime` |
| ④ **分列**「快照路径」与「生产路径当前值」 | ✅ 每项含 `snapshot` 与 `live_path_current`（冻结后重测），并汇总 `drift_since_freeze` |
| ⑤ **引用者 mtime ≥ 所有被引用快照 mtime** | ✅ 见下机械检验 |

**⑤ 机械检验（可复跑）**
```bash
cd ~/dsh-collab
{ find audits/20261009/frozen-snapshot-v1 -type f; echo docs/starbridge-stage-report-and-review-package-20261009.md; } \
  | xargs stat -f '%m %N' | sort -n | tail -3
# ⇒ 末行必须是本信息包
```

**冻结结果**：**25 文件**（24 项 + manifest）· **冻结后源零漂移**（`drift_since_freeze = []`）。

**★ 与「生产路径当前值」的分列声明**
快照记录的是**快照时刻**的值。生产路径上的文件此后仍可能变。本会话声明不再改这 24 项，
但**机制上无强制** ⇒ 读者若需判断「是否又变了」，应比对 manifest 的 `live_path_current` 与磁盘现值，
**而不是**信任 §四 的 sha 表。

**★ 本节为何在最后写**：判据⑤ 要求引用者 mtime ≥ 快照 mtime。
本节即为此而在快照之后重写 ⇒ 首次跑 `--verify` 时它**正确地报了不成立**（引用者 1791554811 < 快照 1791556028），
重写本信息包后才转为成立。**这是检验在工作，不是检验失效。**
