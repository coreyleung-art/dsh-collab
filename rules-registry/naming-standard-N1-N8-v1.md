---
doc: naming-standard-N1-N8
doc_version: 1.0.0
status: enforced
scope: all-bus-devices
authority: PSTD/1.0.1（Cordis 动态插件 pstd-2 · 包 pkg-8 · 工具 plugin_name_gate / plugin_standard）
authority_persistent: false  # 进程内，重启即消失 → 故有本落盘镜像
this_file_role: 正文落盘镜像（可解析）；分歧时以运行时为准并重新生成本文件
r047: RULES.md v2.23.5「插件/工具命名准入门（N1–N8）」
generated_at: 2026-10-05
generated_by: session-b250bf9d-4d0f-4786-be71-01be7d0cc57d
verification: 判据块（第 6 节）已对 19 条测试向量复现运行时 verdict；复核命令见第 8 节
---

# 命名规范 N1–N8（PSTD 标准正文 · 落盘镜像）

> **一句话**：新插件/新工具名先过命名门，再进脚手架；不合规的名字在 gate 入口即被拒（并给出可操作原因），不进入 scaffold。

## 0 · 为什么有这个文件

R047 把本规范登记为 enforced 门，但「唯一标准源」原本只存在于一个**进程内动态插件**里——CLD 重启后正文与执行体一并消失，
其它设备与会话无法查阅 N1–N8 到底写了什么。本文件把正文落盘为可解析件，供跨设备/跨会话复核。

## 1 · 适用范围

- **对象**：一切 dsh 插件目录、包名、cordis 插件行、模型可见工具名。
- **范围**：all-bus-devices（跨设备命名一致性）。
- **强度**：enforced —— 新名字不达标不进入 scaffold。存量违规按 R047 不追溯惩罚，由属主登记清理（宽限 7 天）。
- **归属**：未经属主确认禁止代改他人插件命名（R006 §8 归属优先）。

## 2 · N1–N8 判据总表

| 编号 | 项 | 判据（可机械核验） |
|---|---|---|
| **N1** | 目录名 | 目录名 = dsh-plugin-<slug>；slug 匹配 ^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$，长度 2-32（全小写 kebab-case，无点号/下划线/大写） |
| **N2** | 包名 | package.json name === 目录名 |
| **N3** | 插件行 | cordis.patch.yml 的 id === slug，name === package.json name（注意 YAML 列表项写作 "- id: x"） |
| **N4** | 工具名 | 匹配 ^[a-z][a-z0-9]*(?:_[a-z0-9]+){1,3}$（snake_case，至少两段，首段=领域前缀），长度 ≤ 48；新名字还须在活体工具表中唯一 |
| **N5** | 日志路径 | ~/dsh-collab/logs/dsh-plugin-<slug>.log |
| **N6** | 登记卡键 | data/registry/dsh-plugin-<slug> |
| **N7** | 版本单一来源 | 版本只写在 package.json；CLI --tool-version 从它读取，不得第二处硬编码 |
| **N8** | 保留字 | slug 不得为保留字（见 reserved_slugs） |

## 3 · 逐条：判据 / 为什么 / 反例

### N1 · 目录名

- **判据**：`目录名 = dsh-plugin-<slug>；slug 匹配 ^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$，长度 2-32（全小写 kebab-case，无点号/下划线/大写）`
- **为什么**：本机 43 个插件目录里 39 个合规；点号会破坏目录枚举与黑板键，devices/ 下 4 个 dsh-plugin-x.bak-* 备份目录即为反例

### N2 · 包名

- **判据**：`package.json name === 目录名`
- **为什么**：R006 ⑥：标识与版本只允许一处声明（实测 dsh-plugin-agent-bus 的 name 仍写 dsh-plugin-agent-way、files 写 dsh-files）

### N3 · 插件行

- **判据**：`cordis.patch.yml 的 id === slug，name === package.json name（注意 YAML 列表项写作 "- id: x"）`
- **为什么**：更名会留下 id/name 漂移；反例容忍度为零——这是无插件行则不可挂载的硬字段

### N4 · 工具名

- **判据**：`匹配 ^[a-z][a-z0-9]*(?:_[a-z0-9]+){1,3}$（snake_case，至少两段，首段=领域前缀），长度 ≤ 48；新名字还须在活体工具表中唯一`
- **为什么**：R006 事故表记录「同名工具两处实现、行为不一致」造成认知分裂；注意唯一性只管新名字，已挂载插件自己的工具出现在活体表里是正常的

### N5 · 日志路径

- **判据**：`~/dsh-collab/logs/dsh-plugin-<slug>.log`
- **为什么**：R006 ⑦：固定路径、失败也留痕

### N6 · 登记卡键

- **判据**：`data/registry/dsh-plugin-<slug>`
- **为什么**：黑板 key 首段必须为纯小写字母（实测违规返回 400）

### N7 · 版本单一来源

- **判据**：`版本只写在 package.json；CLI --tool-version 从它读取，不得第二处硬编码`
- **为什么**：R006 ⑥ 反例：两处声明必然漂移

### N8 · 保留字

- **判据**：`slug 不得为保留字（见 reserved_slugs）`
- **为什么**：避免与宿主/框架命名空间撞车

### N1 的子判据（实现细节，审计逐条报）

- 全小写
- 无下划线
- 无点号
- 不以数字开头
- 无连续连字符
- 不以连字符结尾
- 仅含 [a-z0-9-]
- 匹配 slug 正则

> **路径型入参的两种行为（易误判，务必分清）**：`action=check` 会先把路径归一化为 basename（`../../etc/passwd` → `passwd`，宽松）；
> 而 `plugin_pattern_scaffold` 对含 `/` `..` `\` 的 raw slug 直接判 `PATH_GATE` 拒绝（严，不归一化）。

## 4 · 保留字表（26 个，N8）

`dsh` `plugin` `plugins` `cordis` `agent` `agents` `tool` `tools` `test` `tests` `node` `index` `client` `server` `core` `lib` `api` `new` `default` `config` `app` `sdk` `main` `bin` `docs` `runtime`

## 5 · 判据块的两个分区（重要）

- `operative`：**复核器真正执行**的字段（正则/长度/保留字/子判据）。每个字段都必须被至少一条测试向量覆盖，
  由 `verify-naming-standard.py --mutation` 逐个字段做变异自检证明——改宽某个字段而**没有**任何向量转红，即判该字段**未被覆盖**。
- `descriptive`：**仅声明语义**、不被复核器执行的字段（目录前缀、日志路径、登记卡键、插件行形态、N2/N3/N5/N6/N7 的核验归属）。
  它们分别由 `plugin_name_gate action=audit` 与 `plugin_review` 核验；**本文件不代其作证**。

## 6 · 机器可读判据（JSON）

```json
{
  "doc": "naming-standard-N1-N8",
  "doc_version": "1.0.0",
  "authority": {
    "id": "PSTD/1.0.1",
    "kind": "cordis-dynamic-plugin",
    "plugin_id": "pstd-2",
    "package_id": "pkg-8",
    "persistent": false
  },
  "scope": "all-bus-devices",
  "r047": {
    "ledger": "~/dsh-collab/rules-registry/RULES.md",
    "ledger_version": "2.23.5",
    "status": "enforced"
  },
  "norm_ids": [
    "N1",
    "N2",
    "N3",
    "N4",
    "N5",
    "N6",
    "N7",
    "N8"
  ],
  "norms": [
    {
      "id": "N1",
      "title": "目录名",
      "rule": "目录名 = dsh-plugin-<slug>；slug 匹配 ^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$，长度 2-32（全小写 kebab-case，无点号/下划线/大写）",
      "why": "本机 43 个插件目录里 39 个合规；点号会破坏目录枚举与黑板键，devices/ 下 4 个 dsh-plugin-x.bak-* 备份目录即为反例"
    },
    {
      "id": "N2",
      "title": "包名",
      "rule": "package.json name === 目录名",
      "why": "R006 ⑥：标识与版本只允许一处声明（实测 dsh-plugin-agent-bus 的 name 仍写 dsh-plugin-agent-way、files 写 dsh-files）"
    },
    {
      "id": "N3",
      "title": "插件行",
      "rule": "cordis.patch.yml 的 id === slug，name === package.json name（注意 YAML 列表项写作 \"- id: x\"）",
      "why": "更名会留下 id/name 漂移；反例容忍度为零——这是无插件行则不可挂载的硬字段"
    },
    {
      "id": "N4",
      "title": "工具名",
      "rule": "匹配 ^[a-z][a-z0-9]*(?:_[a-z0-9]+){1,3}$（snake_case，至少两段，首段=领域前缀），长度 ≤ 48；新名字还须在活体工具表中唯一",
      "why": "R006 事故表记录「同名工具两处实现、行为不一致」造成认知分裂；注意唯一性只管新名字，已挂载插件自己的工具出现在活体表里是正常的"
    },
    {
      "id": "N5",
      "title": "日志路径",
      "rule": "~/dsh-collab/logs/dsh-plugin-<slug>.log",
      "why": "R006 ⑦：固定路径、失败也留痕"
    },
    {
      "id": "N6",
      "title": "登记卡键",
      "rule": "data/registry/dsh-plugin-<slug>",
      "why": "黑板 key 首段必须为纯小写字母（实测违规返回 400）"
    },
    {
      "id": "N7",
      "title": "版本单一来源",
      "rule": "版本只写在 package.json；CLI --tool-version 从它读取，不得第二处硬编码",
      "why": "R006 ⑥ 反例：两处声明必然漂移"
    },
    {
      "id": "N8",
      "title": "保留字",
      "rule": "slug 不得为保留字（见 reserved_slugs）",
      "why": "避免与宿主/框架命名空间撞车"
    }
  ],
  "operative": {
    "slug_regex": "^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$",
    "slug_len_min": 2,
    "slug_len_max": 32,
    "tool_regex": "^[a-z][a-z0-9]*(?:_[a-z0-9]+){1,3}$",
    "tool_len_max": 48,
    "reserved_slugs": [
      "dsh",
      "plugin",
      "plugins",
      "cordis",
      "agent",
      "agents",
      "tool",
      "tools",
      "test",
      "tests",
      "node",
      "index",
      "client",
      "server",
      "core",
      "lib",
      "api",
      "new",
      "default",
      "config",
      "app",
      "sdk",
      "main",
      "bin",
      "docs",
      "runtime"
    ],
    "n1_subchecks": [
      "全小写",
      "无下划线",
      "无点号",
      "不以数字开头",
      "无连续连字符",
      "不以连字符结尾",
      "仅含 [a-z0-9-]",
      "匹配 slug 正则"
    ]
  },
  "descriptive": {
    "enforced_by_this_verifier": false,
    "dir_prefix": "dsh-plugin-",
    "log_path_pattern": "~/dsh-collab/logs/dsh-plugin-<slug>.log",
    "registry_key_pattern": "data/registry/dsh-plugin-<slug>",
    "patch_row": "cordis.patch.yml: - insert: / - id: <slug> / name: dsh-plugin-<slug>",
    "n2_n3_n5_n6_n7": "包名/插件行/日志路径/登记卡键/版本单一来源：由 plugin_name_gate action=audit 与 plugin_review 分别核验，本文件只记录判据文本"
  },
  "entrypoints": {
    "plugin_name_gate action=check": "宽松入口：路径型入参先归一化取 basename，再判 slug 形式 + 工具名形式 + 目录是否被占 + 是否与活体工具表重名",
    "plugin_name_gate action=allocate": "从用途描述机械生成 slug（纯中文如实拒绝，不做假音译）并查占用",
    "plugin_name_gate action=audit": "只读全机审计：N1/N2/N3 判实据，N4 只判形式（已挂载插件自己的工具出现在活体表里是正常的）",
    "plugin_pattern_scaffold": "严入口：raw slug 含 / 或 .. 或 \\ → PATH_GATE 直接拒（不归一化）；随后才过命名门（N1–N4）"
  },
  "test_vectors": [
    {
      "input": "abcdefghijklmnopqrstuvwxyzabcdefg",
      "kind": "slug",
      "expect": "reject"
    },
    {
      "input": "aa_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
      "kind": "tool",
      "expect": "reject"
    },
    {
      "input": "-a",
      "kind": "slug",
      "expect": "reject"
    },
    {
      "input": "my-new-tool",
      "kind": "slug",
      "expect": "accept"
    },
    {
      "input": "flower-cockpit",
      "kind": "slug",
      "expect": "accept"
    },
    {
      "input": "agent-bus",
      "kind": "slug",
      "expect": "accept"
    },
    {
      "input": "My_Plugin",
      "kind": "slug",
      "expect": "reject"
    },
    {
      "input": "cordis",
      "kind": "slug",
      "expect": "reject"
    },
    {
      "input": "9lives",
      "kind": "slug",
      "expect": "reject"
    },
    {
      "input": "x.bak-v1",
      "kind": "slug",
      "expect": "reject"
    },
    {
      "input": "花店",
      "kind": "slug",
      "expect": "reject"
    },
    {
      "input": "a",
      "kind": "slug",
      "expect": "reject"
    },
    {
      "input": "a--b",
      "kind": "slug",
      "expect": "reject"
    },
    {
      "input": "a-",
      "kind": "slug",
      "expect": "reject"
    },
    {
      "input": "mytool_scan",
      "kind": "tool",
      "expect": "accept"
    },
    {
      "input": "pstd_review_deep",
      "kind": "tool",
      "expect": "accept"
    },
    {
      "input": "BadName",
      "kind": "tool",
      "expect": "reject"
    },
    {
      "input": "scan",
      "kind": "tool",
      "expect": "reject"
    },
    {
      "input": "my-tool",
      "kind": "tool",
      "expect": "reject"
    }
  ],
  "known_boundaries": [
    "★ 执行点不常驻：plugin_name_gate 属进程内动态 Cordis 插件（pstd-2/pkg-8），CLD 重启即消失；落盘为常驻插件包前，本门的执行体在重启后不存在。",
    "「登记」未被本门约束：scaffold 已被命名门拦住，但黑板登记卡（bb_card_send / data/registry）无前置校验，不合规名字仍可被登记。",
    "跨设备执行面：base 探测 = 本机 workspaceRoot/~ + ~/dsh-collab/devices；N4 唯一性查的是本机活体工具表。跨设备需各设备各自运行或分发落盘包。",
    "豁免无结构化表达：本工具没有 exemption 字段——豁免只能在 package.json 的 r006 段或账本里显式声明，无法在门里表达（这正是 R047「禁止声明即豁免」的结构性缺口）。",
    "N4 唯一性只对新名字：审计模式刻意不把「本插件自己已挂载的工具」当冲突（v1.0.1 修复的误判）。"
  ],
  "errata": [
    "勘误 2026-10-05：R047 详情③ 曾记「16 负例全拒」，实测为 **15** 条负例（10 条命名/工具名 + 5 条门负例），正例 12 条。错误源头＝PSTD 交付卡与工具描述里的声明面数字，非账本录入者。运行时 selfproof 输出一直为 15。",
    "本轮复核另确认：`plugin_standard` 的 norms/r006/patterns/gates 四个切片动作因返回体含 undefined 被 harness lossless-JSON 校验拒绝（只有 all 与 selfproof 可用）——记为待修缺陷。",
    "勘误 2026-10-05（负控抓到自己的空洞通过，第 2 例）：把 `slug_regex` 改成 `^.*$` 复核器仍 PASS —— 因为所有「reject」向量都被更细的子判据拦下了，**正则字段实际没被任何向量覆盖**。已补 `-a`（只因首字符必须 [a-z] 被拒）并引入 `--mutation` 变异自检，逐个放宽 operative 字段、要求至少一条向量转红，否则判该字段「未覆盖」。修后 6 个字段全覆盖，8 条负控全红。",
    "★ 两条勘误指向同一条教训（R006 坑#3）：**负控不红＝没有覆盖，不是「没问题」**；一个字段「在文件里写着」不等于「被执行过」。"
  ]
}
```

## 7 · 执行点与已知边界

1. ★ 执行点不常驻：plugin_name_gate 属进程内动态 Cordis 插件（pstd-2/pkg-8），CLD 重启即消失；落盘为常驻插件包前，本门的执行体在重启后不存在。
2. 「登记」未被本门约束：scaffold 已被命名门拦住，但黑板登记卡（bb_card_send / data/registry）无前置校验，不合规名字仍可被登记。
3. 跨设备执行面：base 探测 = 本机 workspaceRoot/~ + ~/dsh-collab/devices；N4 唯一性查的是本机活体工具表。跨设备需各设备各自运行或分发落盘包。
4. 豁免无结构化表达：本工具没有 exemption 字段——豁免只能在 package.json 的 r006 段或账本里显式声明，无法在门里表达（这正是 R047「禁止声明即豁免」的结构性缺口）。
5. N4 唯一性只对新名字：审计模式刻意不把「本插件自己已挂载的工具」当冲突（v1.0.1 修复的误判）。

## 8 · 复现命令

```text
# 取运行时正文（与写在本文件里的内容逐字对照）
plugin_standard action=all          # 当前可用
plugin_standard action=norms        # ★ 已知缺陷：该切片动作报 undefined 错，待修包

# 命名门实测
plugin_name_gate action=check name="my-new-tool" tools=["mytool_scan"]
plugin_name_gate action=audit       # 全机 dsh-plugin-* 审计

# 本文件自校验（判据 ↔ 运行时 verdict 对照）
python3 ~/dsh-collab/rules-registry/verify-naming-standard.py --mutation
python3 ~/dsh-collab/rules-registry/verify-naming-standard.py --tool-version   # 复核器版本（单一来源）
#   exit 0 全绿 / 1 校验失败 / 2 用法或 IO 错误；--json 机器可读
```

## 9 · 单一来源声明（R006 ⑥）

N1–N8 的**版本不进本文件**：本文件的 `doc_version` 只是镜像自身的修订号。规范正文的唯一来源是
运行时 `PSTD/1.0.1`（`plugin_name_gate` / `plugin_standard`）。本文件是**派生镜像**，不是第二处声明；
发现分歧时的处置：以运行时为准，并按第 8 节命令重新生成本文件。

## 10 · 勘误（有错就记，不改历史）

- 勘误 2026-10-05：R047 详情③ 曾记「16 负例全拒」，实测为 **15** 条负例（10 条命名/工具名 + 5 条门负例），正例 12 条。错误源头＝PSTD 交付卡与工具描述里的声明面数字，非账本录入者。运行时 selfproof 输出一直为 15。
- 本轮复核另确认：`plugin_standard` 的 norms/r006/patterns/gates 四个切片动作因返回体含 undefined 被 harness lossless-JSON 校验拒绝（只有 all 与 selfproof 可用）——记为待修缺陷。
- 勘误 2026-10-05（负控抓到自己的空洞通过，第 2 例）：把 `slug_regex` 改成 `^.*$` 复核器仍 PASS —— 因为所有「reject」向量都被更细的子判据拦下了，**正则字段实际没被任何向量覆盖**。已补 `-a`（只因首字符必须 [a-z] 被拒）并引入 `--mutation` 变异自检，逐个放宽 operative 字段、要求至少一条向量转红，否则判该字段「未覆盖」。修后 6 个字段全覆盖，8 条负控全红。
- ★ 两条勘误指向同一条教训（R006 坑#3）：**负控不红＝没有覆盖，不是「没问题」**；一个字段「在文件里写着」不等于「被执行过」。

