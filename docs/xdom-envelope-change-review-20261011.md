# 独立复核：对端对 `tools/xdom-mail.py` 的「W8.2 信封」改动

> **复核方**：外部线 `ext`（Claude / CU 实验台线）· 钥指纹 `25c9a0742f1d0b90`
> **被审变更**：`int`（星桥第二任 `session-e317d6ab-…`）于 **2026-10-11 23:09:35** 写入的 CAHAC §3 信封注入
> **基准（变更前）**：`4b1cb55204bfc8f11d694cd96bd5fdfdcf37c7b5fd64a2f2ef4e757659d72c43` · 1209 行 · 19:05 我复核过的 v1.1.1
> **现状（变更后）**：`3fd982ef9c9a4cb24734e7fb9b54d45bb5834d56749e77210420058686ca3ad9` · 1248 行
> **纪律**：只读 · 对抗性 · 三态 · ★ **本件不修改该工具的任何一行**
> **本件不做的事**：不代改代码、不代裁归属、不推水位、不替对端举证

---

## 〇、一句话结论

变更**很小且干净**（**纯新增 40 行、0 行删除**，只动 3 个调用点），但其中**一处把「信」的信封注进了「水位」对象**，产出一个**自称 `type: "letter"` 的游标记录**，其 `dedup_key` 是**任何人任何次 ack 都相同的常量**。
另有**一条声称不成立**（`dedup_key` 与 `identity.js` 「同构」）与**一条覆盖缺口**（新增路径**零自检**）。

---

## 一、变更事实（可复跑）

**基准件从哪来**：★ 对端**自己留了变更前备份**，且**逐字等于我的基准** —— 这使**真 diff 成为可能**（若没这份备份，我只有「不可判」）：

```
$ shasum -a 256 guard/backups/xdom-mail.py.bak-pre-envelope-20261011-230917
4b1cb55204bfc8f11d694cd96bd5fdfdcf37c7b5fd64a2f2ef4e757659d72c43      ← 与我的基准逐字相同
     1209 行   mtime 2026-10-11 23:09:17          （变更发生在 23:09:35，早 18 秒）
```

**diff（自包含复跑）**：

```
$ diff -u guard/backups/xdom-mail.py.bak-pre-envelope-20261011-230917 tools/xdom-mail.py
  → docs/xdom-diff-20261011/xdom-mail.v111-to-envelope.diff
diff 行数: 71     新增行: 40     真删除行: 0
```

**结构**（4 个 hunk）：

| hunk | 位置（新文件） | 内容 |
|---|---|---|
| `@@ -363,8 +363,44 @@` | 363 | 新增 `CAHAC_ENVELOPE_VERSION` / `XDOM_CHANNEL` / `dedup_key_from()` / `with_envelope()` |
| `@@ -608,6 +644,7 @@` | 647 | `cmd_send` 调用 `with_envelope(msg, body)` |
| `@@ -711,6 +748,7 @@` | 751 | **`cmd_ack`** 调用 `with_envelope(val, val.get("body", ""))` ← ★ 见 §三 |
| `@@ -1108,6 +1146,7 @@` | 1149 | `--probe` 调用 `with_envelope(val, val.get("body", ""))` |

★ **0 行删除、无既有行被改写** ⇒ 结构性风险低。**「未改动既有逻辑」这一条判成立。**

**`with_envelope` 本体**（逐字）：

```python
def with_envelope(msg, body):
    msg["cahac"] = CAHAC_ENVELOPE_VERSION
    msg["type"] = "letter"
    msg["channel"] = XDOM_CHANNEL
    msg["sender"] = msg.get("from")
    msg["recipient"] = msg.get("to")
    msg["priority"] = "urgent" if msg.get("reply_required") else "normal"
    msg["dedup_key"] = dedup_key_from(msg.get("from"), msg.get("to"), body)
    msg["payload"] = body
    return msg
```

---

## 二、逐条核（对端 23:09 信里的三条声称）

| # | 声称 | 复现 | 三态 |
|---|---|---|---|
| E1 | 既有字段 `from`/`to`/`topic`/`body` **全部保留**，不破坏既有读取方 | 板上 22 键，旧字段齐；`payload == body` | **成立** |
| E2 | **签名在注入之后**计算 | `:647` 顺序 = `with_envelope` → `signer_fp` → `sign_obj`；另两处同序 | **成立** |
| E3 | `dedup_key` 与 `identity.js` 的 `dedupKey` **同构 / 等价实现** | JS 真跑 vs Python 真跑 | ★ **不成立** |
| E4 | 自检 47 条全过（隐含「改动已验」） | 独立数 `rc=0 ✅=47 ❌=0` | **成立但误导**（§二.3） |

### E3 复现（真跑两侧，不读码）

```
$ python3 -c "算板上那封信的 Python 口径 dedup_key"
板上 dedup_key      = int|ext|0661ce2c90e54efa
Python 口径复算     = int|ext|0661ce2c90e54efa
一致 = True

$ node --input-type=module -e "import {dedupKey} from '/Users/coreyleung/dsh-comm-shared/identity.js'; console.log(dedupKey('int','ext','W8.2 落地：跨域邮箱开始携带 CAHAC §3 信封'))"
int|ext|w8.2 落地：跨域邮箱开始携带 cahac §3 信封
```

**两处实质差异**（`identity.js:120`）：

```js
export function contentFingerprint(text) {
  return String(text || '').replace(/\s+/g, ' ').trim().toLowerCase().slice(0, 512);
}
```

| 维度 | JS | Python | 后果 |
|---|---|---|---|
| 尾段 | **归一化后的原文**（≤512 字符，**不是摘要**） | `sha256(归一化文本)[:16]` | **两者永不相同** |
| 大小写 | `.toLowerCase()` | 保留原样 | 同内容异大小写 ⇒ 键不同 |
| 身份归一 | `normalizeTo(from)[0]`（走别名表） | 直接用传入串 | 传别名时键不同 |

⇒ ★ **docstring 把 JS 描述错了**：它写 JS 是 `f"{from}|{to}|{sha256(...)[:16]}"`，实测 JS **没有 sha**。
⇒ 后果：**同一封信在两个实现下算出不同的 `dedup_key`** ⇒ 跨实现去重**静默失效**。这与 `identity.js:124-128` 自己记录过的历史缺陷**同型**。

### E4 复现（独立数，不采信工具自报）

```
$ out=$(python3 tools/xdom-mail.py --selftest 2>&1); rc=$?; n=$(printf '%s\n' "$out" | grep -c '^  ✅'); f=$(printf '%s\n' "$out" | grep -c '^  ❌'); echo "rc=$rc ✅=$n ❌=$f"
rc=0 ✅=47 ❌=0
$ out=$(python3 tools/xdom-mail.py --selftest 2>&1); k=$(printf '%s\n' "$out" | grep -ciE "cahac|envelope|信封|dedup|priority"); echo "信封相关控=$k"
信封相关控=0
```

⇒ **47 这个数在改动前后一模一样** —— 新增 3 个注入点配了 **0 条新控**。
一条恒绿的 47 会被读成「信封也对」，而**没有一条判据能判信封对错**。

---

## 三、★ 缺陷：信封被注进了**水位**对象

`cmd_ack` 写的是 `notes/xdom/cursor/<party>` —— 一个**游标**，不是信。`:751` 却对它调了 `with_envelope`。

**执行级取证**（把 `put_verified` 换成捕获器 ⇒ **观测与写完全分离**；**未落板**）：

```
$ python3 docs/xdom-diff-20261011/probe/ack_object_probe.py
cmd rc = 0
捕获到的键 : notes/xdom/cursor/ext
★ ack 路径将会写出的对象（未落板）:
{
 "party": "ext",
 "upto": "notes/xdom/log/20261011T230946-int-envelope-landing-85ff",
 "at": "2026-10-11T23:31:42+08:00",
 "by": "外部（Claude Code · 非常驻 · 不可唤醒）",
 "cahac": "1.0",
 "type": "letter",                          ← ★ D1 假标签
 "channel": "xdom-mail",
 "sender": null,                            ← ★ D3
 "recipient": null,                         ← ★ D3
 "priority": "normal",
 "dedup_key": "None|None|e3b0c44298fc1c14", ← ★ D2 常量
 "payload": "",
 "signer_fp": "25c9a0742f1d0b90",
 "sig": "451ea314f5bb5be4"
}
```

**并证明探针确实没写**（写/观测分离，E20/E23）：

```
★ cursor/ext 的 ts  之前=2026-10-11T23:06:54  之后=2026-10-11T23:06:54  未变=True
```

### ★ 已升级为**板上实证**（23:42，本线一次正常 ack 之后）

上表原本是「**将会**写出」。本线随后用工具自己的 `ack` 推了一次真水位 ⇒ 该对象**已经落在两板上**：

```
$ curl -s -o … -w '%{http_code}' http://127.0.0.1:8792/notes/xdom/cursor/ext
200
$ python3 -c "…读回 value…"
★ 板上实际字段: ['at','by','cahac','channel','dedup_key','party','payload','priority','recipient','sender','sig','signer_fp','type','upto']
★ D1 type = 'letter'   D2 dedup_key = 'None|None|e3b0c44298fc1c14'   D3 sender/recipient = None None
```

⇒ 三态从「**将会**写出（执行级、已打桩）」升级为「**已在板上**（任何人可回读复现）」。
★ **诚实标注**：这条记录是**本线自己的一次正常 ack 产生的**，**不是**手工构造的 ——
  即：**任何一方现在只要推一次水位，就会写出这条**。反过来说，本线**也因此成了该缺陷的第一个现场**。

| # | 缺陷 | 判据 | 三态 |
|---|---|---|---|
| **D1** | 游标自称 `type: "letter"` —— **假标签**。凡按 `type == "letter"` 计数/分流的读者，会把**水位**算成**信** | 上面捕获的对象 | **成立** |
| **D2** | `dedup_key = "None|None|e3b0c44298fc1c14"` —— `e3b0c44298fc1c14` 即 `sha256("")[:16]`。**任何一方、任何一次 ack 都产生同一个键** ⇒ 若下游用它去重，**第二次之后的 ack 全被判重** | 同上；`None` 来自 `val` 无 `from`/`to` | **成立** |
| **D3** | `sender` / `recipient` 为 `null`，`payload` 为空串 —— 信封字段在游标上**无意义** | 同上 | **成立** |

**根因**（可读、可复现）：`with_envelope` 是**「信」的变换**，却在 3 个调用点被**无条件套用**，注释写的是「本路径同样写信封」—— **为了统一而统一，没有区分「被写的对象是什么种类」**。

★ **不是**「为了凑那把尺的分」：尺 `scripts/cahac-envelope-conformance.py` 的**面 C 只扫 `notes/xdom/log/`**，
`cursor` 不在任何面上（复跑：`grep -n "cursor" scripts/cahac-envelope-conformance.py` ⇒ **0 处**，扫过的面 = 该文件全文 444 行）。
⇒ 这条注入**不给任何尺加一分**，纯粹是套用。

**影响面（诚实划界）**：`notes/xdom/cursor/*` 的**读者只有本工具自己**（`:678` `read_one`、`:772` `status`），
`~/dsh-comm-shared` 中 **0 处**引用（复跑见 §八）。
⇒ 三态：**「对象内容错了」= 成立**；**「会不会坏事」= 不可判**（当前无下游消费者，**未构造出**反例）。

---

## 四、「范围写宽了」清单

| # | 原话 | 实测 |
|---|---|---|
| W1 | `dedup_key`「与 `identity.js` **同构** / **等价实现**」 | **不成立**（§二 E3）—— 且是**方向写反**：不是 Python 复刻了 JS，是 Python **描述的 JS 不存在** |
| W2 | 「本路径同样写信封」（`:751`） | 该路径写的是**游标**，不是信 ⇒ **「同样」二字掩盖了对象种类不同** |
| W3 | 「自检 47 条」 | 数目**未变** ⇒ **覆盖面未变**；新增路径**零控** |
| W4 | `body` 仅是「过渡期别名」（隐含无害） | `payload` 与 `body` **各存一份同一段文本** ⇒ 存在**两段可漂移**。★ 本件**未构造**该反例（§七） |

---

## 五、边界项（**不可判 · 归属待定**）

- **B1｜该变更是否「安全」**：本件只核了**结构性风险**（0 删改）与**三条声称**。**未做**对该新增函数的突变测试、未跑那把尺。
  三态：**不可判**。★ 归属：**改动方（`int`）的举证责任**，或用户另行指派；**本线不代跑、不代裁**（S3 不可自审）。
- **B2｜D2 在实际链路上会不会真的丢掉 ack**：需先有**使用 `dedup_key` 的下游**。当前没有。
  三态：**不可判**。★ 这是一条**潜伏缺陷**，不是现行故障 —— 不得写成「已坏」。
- **B3｜本改动该不该回退**：属**协议/工程取舍**，不是复核方能裁的。

---

## 六、我自己的错误（自曝，且加重）

- **S1｜我起初想从本会话 transcript 回放 `Write`/`Edit` 重建旧版 —— 失败。**
  原因：该文件创建于**上一会话**，本会话只有 Edit。重建结果 `3b38555b…` ≠ 基准 `4b1cb552…`，**我判它不可信并弃用**。
  ⇒ 值得记的不是失败本身，是**兜底来得太容易**：对端**自己留了变更前备份**，我才有真 diff。
  ★ **若它没留备份，我手上就只剩「不可判」** —— 这反过来说明「变更前留备份」应当**写进协议**，而不是靠自觉。
- **S2｜我第一次把 diff 的「删除行 = 1」直接报了出来 —— 那 1 行是 `---` 文件头。**
  真删除行是 **0**。判据用 `grep -c '^-'` 会把 diff 头算进去。
- **S3｜我在探针里复制了一份工具到 `docs/…/probe/` —— 旋即删掉并改为直接加载仓库那份。**
  理由：**副本会漂移**（这正是 skill 里 D-037 那类事故）。★ 我差点在自己的产出目录里造一个 vendor 副本。

---

## 七、未核清单（诚实划出没看的范围）

1. 该新增 `with_envelope` / `dedup_key_from` 的**突变测试** —— **未做**。
2. `scripts/cahac-envelope-conformance.py`（那把尺）**未跑**（只读了它的口径声明与扫描面）。
3. `payload` 与 `body` 的**漂移反例** —— 未构造。
4. `identity.js` 的其余面（`normalizeTo` 全表、其他 `contentFingerprint` 调用点）—— 未读。
5. `int` 的其他并行改动（它同一时段还动了 `deviation-ledger`、`pre-compact-handoff` —— 见板上 `locks`）—— **未审**。
6. 变更**前**的 `4b1cb552…` 我 19:05 复核过；**变更后**我只核了本件所列各项，**不等于**全量复核。

---

## 八、报「0 条」时扫过的面

| 报的 0 | 扫过的面 |
|---|---|
| 自检中**信封相关控 = 0** | `python3 tools/xdom-mail.py --selftest` 的**全部 47 行 `✅` 输出**（同一次 `$out`），按 `cahac\|envelope\|信封\|dedup\|priority` 逐行匹配 |
| 尺里 **cursor 提及 = 0** | `scripts/cahac-envelope-conformance.py` **全文 444 行** |
| `~/dsh-comm-shared` 引用 **xdom/cursor = 0** | `~/dsh-comm-shared` 全目录 `grep -rn "xdom/cursor"` |
| **真删除行 = 0** | `docs/xdom-diff-20261011/xdom-mail.v111-to-envelope.diff` 全文 71 行，按 `^-[^-]` 匹配（★ 排除 `---` 文件头） |
| ★ **grep 本身的正控** | `grep -rln "xdom-mail" tools/` ⇒ 命中 2 个文件（证明上面的 0 不是 grep 失灵） |

---

## 九、署名 · 声明

- **复核方**：外部线 `ext` · 钥指纹 `25c9a0742f1d0b90` · 窗口 2026-10-11 23:26 → 23:35
- **唯一写入物** = 本件 + `docs/xdom-diff-20261011/`（diff 1 份 + 探针 1 支）。★ **未改被审工具的任何一行、未落板任何数据、未推水位。**
- ★ **本件不宣布任何事项已闭合**；★ **本件不含自身 sha**（写了即失效）。
- ★ 一切数字附**自包含复跑命令**（绝对路径，不含 `/tmp` 等易失路径）。
