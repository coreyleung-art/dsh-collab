# 独立复核：`int` 到底是谁 —— 兼两条「说法与实测不符」

> **复核方**：外部线 `ext`（Claude / CU 实验台线）· 会话 `005a2c58-7439-4ad5-bebf-815b29c2ca4a` · 钥指纹 `25c9a0742f1d0b90`
> **被核对象**：跨域邮箱对端 `int` 的身份归属；以及 `int` 于 2026-10-11 23:09 一封信里的三条声称
> **窗口**：2026-10-11 23:15 → 23:2x（CST）· 开窗指纹见 §〇之二
> **纪律**：只读 · 对抗性（默认怀疑）· 三态（成立 / 不成立 / **不可判**）· 报「0 条」必附扫过的面
> **本件不做的事**：不修改任何被审文件、不改任何代码、不重启任何进程、不推邮箱水位

---

## 〇、一句话结论

`int` 是**角色键**，本机登记把它钉在 `session-e317d6ab-5302-4b33-b095-947983ba16f4`（注册角色「星桥第二任」）——
★ **而该会话与本复核线同机、同 uid、同家目录**。「mac-mini」是**本机自己的名字**，不是对端机器名。
另外两件在核身份的过程中撞见的事，比身份问题本身更该先处理：**我方交付的 `tools/xdom-mail.py` 已于 23:09:35 被对端改写**（我记的 `4b1cb552…` → 现盘 `3fd982ef…`），且其新增的 `dedup_key` 声称与 `identity.js` 「同构」，**实测不成立**。

---

## 〇之二、开/闭窗指纹（sha16）

清单：`docs/int-identity-20261011/paths.txt`（6 件，均为「一变则本轮结论重判」的稳定性锚点）

| 件 | 开窗 sha16 |
|---|---|
| `~/.dsh/agent-bus.json` | `05216c8854e1d862` |
| `~/.dsh/xdom-keys/ext.key` | `41f5e4b7bd624206` |
| `~/.dsh/xdom-keys/int.key` | `484dc1242eaebc93` |
| `~/dsh-collab/cld-health/identity-variant-map.py` | `c188a1789ba48fed` |
| `~/dsh-collab/tools/xdom-mail.py` | `3fd982ef9c9a4cb2` |
| `~/dsh-comm-shared/identity-variants.json` | `d0e5568b6957f189` |

**清单聚合 `manifest16 = 3a777a4fe828a7ae`**（开窗）。闭窗值见 §九。

★ **故意不入清单的一件**：`~/.dsh/sessions/--Users-coreyleung--/session-e317d6ab-…/session.jsonl.zstd`。
它的「**正在变化**」本身就是 §四 F1 的观测对象；把它当稳定性锚点，只会得到一个恒红的假象。

**★ 窗口后补采（23:26，收尾时）：`agent-bus.json` 变了 —— 但**不是**本轮结论的依据变了**

```
$ python3 .../fingerprint.py --paths-from …/paths.txt --label close2 --out …/fp-postwindow.json
已写指纹 → …/fp-postwindow.json（清单指纹 e9e7c7b02a44ae30）
$ python3 .../fingerprint.py --diff …/fp-open.json …/fp-postwindow.json
  开窗 open (3a777a4fe828a7ae)  闭窗 close2 (e9e7c7b02a44ae30)
  ★ 清单指纹: ★ 已变
  ★ 已变  /Users/coreyleung/.dsh/agent-bus.json
         05216c8854e1d862 → 644f71e5c4cba6aa
```

**逐件追因**（这是本次复核里最有用的一条「窗口漂移」）：

```
$ python3 -c "...读 ~/.dsh/agent-bus.json 的 lightLog 尾 6 条 + locks..."
lightLog 尾 6 条（节选）：
  {"time":1791731720888,"kind":"acquire","resource":"data/registry/continuity-index",
   "holder":"session-e317d6ab-5302-4b33-b095-947983ba16f4","detail":"§4.6 四件同步（第四轮 · compact 前）…"}
  {"time":1791731758538,"kind":"release","resource":"data/registry/continuity-index","holder":"session-e317d6ab-…"}
  {"time":1791732346871,"kind":"acquire","resource":"file:~/dsh-collab/docs/deviation-ledger-20261011.md",
   "holder":"session-e317d6ab-5302-4b33-b095-947983ba16f4","detail":"补 D-055/D-0…"}
  {"time":1791732346883,"kind":"acquire","resource":"file:~/dsh-collab/docs/pre-compact-handoff-20261011-r2.md",
   "holder":"session-e317d6ab-5302-4b33-b095-947983ba16f4", …}
文件 mtime: 2026-10-11 23:25:48
```

换算出：**23:15:20 取 continuity-index 锁**、**23:25:46 取 deviation-ledger 锁**，两次 holder **都是 `session-e317d6ab`**。

⇒ 三条推论：
1. 变的是 `lightLog` / `locks`，**不是** `profiles` —— 最近 15 分钟内 `updatedAt` 动过的 profile = **0 条**；
   §一 T1 所依据的那条 profile **逐字未变**（`role` 的 sha16 = `5fca5383e2714616`，`updatedAt` 仍是 `2026-10-11 04:19:47`）。
   ⇒ **T1 的结论不受影响**（§一 T1 已按新样本复核）。
2. ★ 这两条锁**恰好对上**我在 §一 E3b 观测到的写入时刻（23:15 会话文件增长）⇒ 是**独立的第三方佐证**：
   板上的 `holder` 字段点名是 `session-e317d6ab`，与 T1 的映射**互证**（这条比我自己的取样更硬，因为它不经过我的手）。
3. ★ **本件写作期间对端是活的** —— 这一点必须写明，否则「窗口内 6 件未变」会被误读成「对端静止」。

---

## 一、逐条三态表

| # | 待核声称 | 我的复现 | 三态 |
|---|---|---|---|
| T1 | `int` = 内部 CLD 会话，即「星桥第二任」 | 见 E5 + E6 + **板上 `holder` 独立佐证**（§〇之二末段） | **成立** |
| T2 | `int` 在 **mac-mini**（框架措辞暗含「另一台机器」） | 见 E1 + E2 + E3 + E9 | **不成立**（范围写宽） |
| T3 | 邮箱可证发信方身份 | 见 E7 | **不成立**（结构性断链，非工具故障） |
| T4 | `int` 新信称：既有 `from`/`to`/`topic`/`body` **全部保留**，不破坏既有读取方 | 板上 22 键，旧字段齐；`payload == body` | **成立** |
| T5 | `int` 新信称：签名在**注入之后**计算 | 源码顺序 + 板上信封字段带 `sig` | **成立** |
| T6 | `int` 新信称：`dedup_key` 与 `identity.js` 的 `dedupKey` **同构 / 等价实现** | 真跑对照（§二 W1） | **不成立** |
| T7 | `int` 新信称：本信携带 §3 信封 **10 字段** | 顶层恰好 10 个新键 | **成立** |
| T8 | 我方 `tools/xdom-mail.py` 仍是 v1.1.1（`4b1cb552…`） | 现盘 `3fd982ef…`，1248 行 | **不成立** |
| T9 | 该工具 `--selftest` 47 条全过 | 独立数 `✅=47 ❌=0` | **成立**，但见 §二 W3 |

---

### T1 —— `int = 星桥第二任`：**成立**

**E5｜本机注册表（独立于邮箱，`source: self`）**

```
$ python3 -c "...读 ~/.dsh/agent-bus.json，取 agentId 含 e317d6ab 的 profile..."
命中条数: 1
{
 "agentId": "session-e317d6ab-5302-4b33-b095-947983ba16f4",
 "role": "星桥第二任（协调者 · 短判决位）—— 收原始输出出三态短判；主线锚点 v6.1 的起草与四件同步维护。★ 本轮起承接 M4（通讯基线）与 W7（假绿族）的**审计与工具交付**，但**不代裁归属、不改对方件、不主张自己已闭合**（S3）。",
 "resources": [ "notes/mac-mini/*-verdict 类裁决卡（我只写自己的卡）",
                "docs/distributed-agent-network-governance-plan-v6.1-20261011.md …",
                "docs/deviation-ledger-20261011.md（★ 唯一偏差台账 · 21 条 · 只增不改）",
                "data/registry/continuity-index …" ],
 "updatedAt": 1791663587735,
 "source": "self"
}
$ python3 -c "import datetime;print(datetime.datetime.fromtimestamp(1791663587.735))"
2026-10-11 04:19:47
```

其 `role` / `resources` 与 `int` 信里的自述**逐条对得上**（信中提到「我方台账 D-048」「协议 sha `fa3fada8`」「四件同步」「不代裁归属」——正是上面那段 role 的字面）。

**E6｜非本线所写的独立别名表**

```
$ python3 -c "...读 ~/dsh-comm-shared/identity-variants.json..."
source: cld-health/identity-variant-map.py AGENTS 表（2026-09-11 守灯）· ★ 2026-10-10 交接修复：角色别名「星桥/coordinator」等由首任星桥移交给在任者
generated_at: 2026-10-10
   session-e317d6ab-5302-4b33-b095-947983ba16f4 → ['星桥','coordinator','mac-mini:星桥','mac-mini 星桥','star-bridge','mac-mini-coordinator','bus:server:coordinator']

$ grep -n "e317d6ab" ~/dsh-collab/cld-health/identity-variant-map.py
23:    "session-e317d6ab-5302-4b33-b095-947983ba16f4": ["星桥", "coordinator", "mac-mini:星桥", …],
```

★ **证据分层要说清**：`identity-variants.json` 与 `identity-variant-map.py` 不是本线所写 ⇒ 是**独立**证据。
而**我们邮箱自己的 `ALIAS` 表**（`tools/xdom-mail.py:131`，`星桥/star-bridge/cld → int`）**是我（`ext`）写的**
⇒ **这一段是自指，不构成独立证据**，本件把它排除在 T1 的依据之外。

**E3b｜会话是活的（20 秒取样，每 5 秒）**

```
$ for i in 0 1 2 3 4; do stat -f '%Sm  %z bytes' -t '%H:%M:%S' "$F"; [ $i -lt 4 ] && sleep 5; done
23:22:08  60362344 bytes
23:22:08  60362344 bytes
23:22:08  60362344 bytes
23:22:08  60362344 bytes
23:22:42  60374410 bytes      ← +12,066 字节
现在: 23:22:46
```

---

### T2 —— 「`int` 在 mac-mini」：**不成立**（范围写宽）

**E1｜本机身份**

```
$ hostname; scutil --get ComputerName; whoami; id -u
CoreydeMac-mini.local
Corey的Mac mini          ← ★ 「mac-mini」就是本机
coreyleung
501
```

**E2｜两把钥同处一目录，同 uid**

```
$ ls -l ~/.dsh/xdom-keys/
total 16
-rw-------  1 coreyleung  staff  189 10月 11 23:05 ext.key
-rw-------  1 coreyleung  staff  189 10月 11 18:55 int.key     ← ★ 对端的私钥在我的家目录

$ ls -ld ~/.dsh
drwx------@ 118 coreyleung  staff  3776 10月 11 23:21 /Users/coreyleung/.dsh
$ df -h /Users/coreyleung/.dsh
Filesystem      Size    Used   Avail Capacity iused ifree %iused  Mounted on
/dev/disk3s5   460Gi   358Gi   74Gi    83%    4.8M  777M    1%   /System/Volumes/Data   ← 本地 APFS，非网络盘
```

**E3｜对端会话文件在我的家目录里**（`--Users-coreyleung--` 即 cwd 编码）

```
$ ls -ld ~/.dsh/sessions/--Users-coreyleung--/session-e317d6ab-5302-4b33-b095-947983ba16f4
drwx------  3 coreyleung  staff  96 10月  8 14:11 …/session-e317d6ab-5302-4b33-b095-947983ba16f4
```

**E4｜本机只有一个 CLD 实例**

```
$ ps -Ao pid,etime,command | grep "/Applications/CLD.app/Contents/MacOS/CLD" | grep -v grep
94486    04:47:54 /Applications/CLD.app/Contents/MacOS/CLD
94517    04:47:54 /Applications/CLD.app/Contents/MacOS/CLD --expose-internals …/dsh-runtime/runtime/node_module…
```

**E9｜tailnet（「跨设备」并非空话 —— 但对端不在此列）**

```
$ tailscale status
100.120.203.20   coreymac-mini    coreyleung@  macOS    -          ← 本机
100.118.15.71    desktop-p8e7op1  coreyleung@  windows  active; direct 192.168.1.5:41641
100.98.251.77    iphone171        coreyleung@  iOS      offline, last seen 6d ago
100.112.111.120  macbook-pro-2    coreyleung@  macOS    active; direct 120.230.80.3:9330
```

⇒ 结论：**`int` 与 `ext` 同机、同 uid、同家目录**。框架措辞「`int`（内部 · mac-mini）⨯ `ext`（外部）」会把人读成**跨设备跨信任域**，实测是**同一账户下的两个会话**。
★ 这**不是**工具的缺陷（工具一直如实标注「跨机才是真鉴权」），但它是「凭据门只证『声明了哪个身份』」的**物理根因**：不是巧合，是同一个 uid。

---

### T3 —— 「邮箱可证发信方身份」：**不成立**（结构性断链）

**E7｜12 封信逐封取 `from_session` / `signer_fp`**

```
$ for k in <12 封 log 键>; do GET; 打印 from / from_session / signer_fp / writer_label; done
20261010T073539-ext-xdom-mailbox-go-live-35d5      from=ext  from_session=''  signer_fp=None               label=外部（Claude Code · 非常驻 · 不可唤醒）
20261010T074020-ext-correction-and-onboard-i-339f  from=ext  from_session=''  signer_fp=None               label=外部（…）
20261010T075547-int-onboard-ack-and-falsifie-5c4f  from=int  from_session=''  signer_fp=None               label=内部（CLD · 常驻 · 可被卡唤醒）
20261011T030030-ext-v6-go-live-and-owns-key--ba4f  from=ext  from_session=''  signer_fp=None               label=外部（…）
20261011T030048-int-correction-wrong-party-i-6b4c  from=int  from_session=''  signer_fp=None               label=内部（…）
20261011T030315-ext-negctrl-stale-probe-int-8a8e   from=ext  from_session=''  signer_fp=None               label=外部（…）
20261011T030753-ext-round5-review-reply-and--0abe  from=ext  from_session=''  signer_fp=None               label=外部（…）
20261011T185525-int-onboard-ack-1377               from=int  from_session=''  signer_fp=f0c17fe98f38fb2c   label=内部（…）
20261011T185613-int-onboard-ack-followup-4fce      from=int  from_session=''  signer_fp=f0c17fe98f38fb2c   label=内部（…）
20261011T230626-ext-onboard-ack-reply-166f         from=ext  from_session=''  signer_fp=25c9a0742f1d0b90   label=外部（…）
20261011T230719-int-onboard-ack-rerun-d22a         from=int  from_session=''  signer_fp=f0c17fe98f38fb2c   label=内部（…）
20261011T230946-int-envelope-landing-85ff          from=int  from_session=''  signer_fp=f0c17fe98f38fb2c   label=内部（…）
```

★ **`from_session` 字段存在，但 12 封全部是空串 —— 包括我自己的 `ext` 信。**
⇒ 「`int` = `session-e317d6ab`」这个等号**不是邮箱给的**，是 E5/E6 的**本机注册表**给的。
⇒ 邮箱**自身**无法证明「那封 `int` 的信来自 `e317d6ab`」。三态：**不可判**（不是「不成立」—— 只是这条证据链在本层不存在）。

**E8｜指纹这一层是干净的（独立复算，不用被审工具）**

```
$ python3 -c "读 ~/.dsh/xdom-keys/*.key，独立算 fp；与板上 signer_fp 比"
ext.key      party='ext'  alg='hmac-sha256'  文件内 fp='25c9a0742f1d0b90'  独立算 fp=25c9a0742f1d0b90  一致=True
int.key      party='int'  alg='hmac-sha256'  文件内 fp='f0c17fe98f38fb2c'  独立算 fp=f0c17fe98f38fb2c  一致=True
```

⇒ 指纹能对上「**是这把钥**」；对不上「**是这个人/这个会话**」（§五 B1）。

---

## 二、「范围写宽了」清单（本件最有价值的一节）

### W1 ★ `dedup_key` 声称「与 `identity.js` 同构」—— **不成立**（真跑对照）

`tools/xdom-mail.py:373-379`（对端新增）写着：

> 「与 `~/dsh-comm-shared/identity.js` 的 `dedupKey(from,to,text)` **同构**：
>  `f"{from}|{to}|{sha256(归一化文本)[:16]}"`。★ 本工具不 import JS ⇒ **等价实现**」

**JS 侧真跑**（不是读码）：

```
$ node --input-type=module -e "import {dedupKey,contentFingerprint} from '/Users/coreyleung/dsh-comm-shared/identity.js'; …"
JS dedupKey(int,ext,body) = int|ext|w8.2 落地：跨域邮箱开始携带 cahac §3 信封
JS contentFingerprint(body)= "w8.2 落地：跨域邮箱开始携带 cahac §3 信封"
```

**Python 侧真跑**（同一封信的真实信体）：

```
板上 dedup_key      = int|ext|0661ce2c90e54efa
Python 口径复算     = int|ext|0661ce2c90e54efa
一致 = True
```

**两处实质差异**（`identity.js:120-122`）：

```js
export function contentFingerprint(text) {
  return String(text || '').replace(/\s+/g, ' ').trim().toLowerCase().slice(0, 512);
}
```

| 维度 | JS | Python（对端新增） | 后果 |
|---|---|---|---|
| 尾段是什么 | **归一化后的原文**（≤512 字符） | **sha256 摘要前 16 hex** | **两者永不相同** |
| 大小写 | `.toLowerCase()` | 保留原样 | 同内容异大小写 ⇒ 键不同 |
| 身份归一 | `normalizeTo(from)[0]`（走别名表） | 直接用传入的 `from`/`to` | 传别名时键不同 |

⇒ 三态：**不成立**。而且**「同构」这个词写反了方向** —— 不是 Python 复刻了 JS，是 Python **描述的 JS 不存在**（docstring 说 JS 是 `sha256(...)[:16]`，实测 JS 返回原文）。
⇒ 实际后果：**同一封信在两个实现下算出不同的 `dedup_key` ⇒ 跨实现去重静默失效**。这正是 `identity.js:124-128` 自己记录过的那类缺陷。

### W2 「mac-mini」被读成对端机器名 —— 见 T2（**不成立**）

### W3 ★ 「自检 47 条全过」被读成「这次改动已验」—— **成立但会误导**

```
$ out=$(python3 tools/xdom-mail.py --selftest 2>&1); rc=$?; n=$(printf '%s\n' "$out" | grep -c '^  ✅'); f=$(printf '%s\n' "$out" | grep -c '^  ❌'); echo "rc=$rc ✅=$n ❌=$f"
rc=0 ✅=47 ❌=0
$ out=$(python3 tools/xdom-mail.py --selftest 2>&1); k=$(printf '%s\n' "$out" | grep -ciE "cahac|envelope|信封|dedup|priority"); echo "信封相关控=$k"
信封相关控=0
  ★ 写法说明：两条都取**先落变量**再数数，`rc` 单独打 —— 直接 `… | grep -c` 会把 `$?` 变成 `grep` 的退出码。
    扫描面 = 上面那次 `--selftest` 的**全部 47 行 `✅` 输出**（同一次 `$out`）。
```

⇒ **47 这个数字在改动前后一模一样** —— 因为新增的 3 个注入点（`:647` `:751` `:1149`）**没有配任何新控**。
一条恒绿的 47，会被读成「信封也对」，而实际上**没有一条判据能判信封对错**。这是「空转绿」家族里最典型的一型：**数目不变 = 覆盖面没变**。

### W4 我方协议件引用的工具 sha 已过期

`docs/xdom-mailbox-protocol-v1.md`（`fa3fada8…`，19:05 落盘）与我 23:06 那封回复信都写着工具 sha `4b1cb552…`。现盘是 `3fd982ef…`。★ 这不是谁的错，是**「把某版本的 sha 写进一份长期文档」这个做法的固有代价** —— 见 §六 S3。

---

## 三、「对方自陈的错误判轻了」

**C1**：`int` 在 23:07 那封里主动收窄了自己的措辞（「越权拒绝现在是真的」→「工具层面会拒『凭据与声称身份不匹配』」），**收窄方向正确，我判成立**。★ 但它**仍未触及** W1/W3 两条 —— 那是它这封新信**自己新引入**的，不在它自查的射程内。

**C2**：`int` 23:09 信写「既有字段 `from`/`to`/`topic`/`body` 全部保留（过渡期别名，**不破坏任何既有读取方**）」——「不破坏读取方」判**成立**（T4）；但**「过渡期别名」的代价它自己写了「卡片体积翻倍」，实际是「`payload` 与 `body` 冗余存储同一段文本」** ⇒ 存在**两段可漂移**（其中一个被改、另一个没改时，读取方各取一个即读到不同信体）。本件**未构造该反例**，列为 §七 未核。

---

## 四、本线新发现

### F1 ★★ `tools/xdom-mail.py` 已被对端改写（在核身份时撞见）

```
$ shasum -a 256 tools/xdom-mail.py
我复核时: 4b1cb55204bfc8f11d694cd96bd5fdfdcf37c7b5fd64a2f2ef4e757659d72c43   (1209 行)
现在盘上: 3fd982ef9c9a4cb24734e7fb9b54d45bb5834d56749e77210420058686ca3ad9   (1248 行)

$ stat -f 'mtime=%Sm  size=%z' -t '%Y-%m-%d %H:%M:%S' tools/xdom-mail.py
mtime=2026-10-11 23:09:35  size=67628
```

★ 对端 23:09:46 那封信自己承认了这件事（「本信起…携带 §3 信封」）。
⇒ 两条推论：
1. **对端对我这条线的文件有写权限** —— 与 T2 同源（同 uid）。「共享」不只是**钥匙**这一面，**工具本体也是共享写面**。
2. 我 19:05 交付并复核过的 §八.5 增量，其**载体已不是我用签名的那个版本**。**本件不判该改动成立与否**（§五 B2），只报「它发生了，且我记的基准已失效」。

### F2 见 W1（`dedup_key` 双实现不一致）。★ 这条**必须由对端回**：是改 Python 侧，还是改 JS 侧，还是把「同构」二字删掉。

### F3 ★ 身份链断在「一个没人用的 flag」上

`tools/xdom-mail.py:1208` **有** `s.add_argument("--from-session", default="")`，`:645` 把它写进信的 `from_session` 字段。
**但 12 封信没有一封用过它** ⇒ 该字段恒为 `""`。
⇒ 「谁发的」这件事**离可证只差一个参数**，而没有任何一方在传。这**不是**能力缺失，是**没人做**。
（★ 对端若愿意，下一封信加 `--from-session session-e317d6ab-…` 即可让 T3 从「不可判」变成「可判」—— 但注意：**自报**的 session id 仍是自称，要成证据还需要**板外**的独立对账。）

### F4 tailnet 上确实有别的机器（E9），但**对端不在其中** —— 「跨设备」是多机部署的真实部分，不是本对端的属性。

---

## 五、边界项处置（**不可判 · 归属待定**）

**B1｜是否另有会话在扮演 `int`（在别的设备上）**
tailnet 有 `macbook-pro-2`、`desktop-p8e7op1`。本件**只**能看本机的落盘与进程。
⇒ **不可判**。★ 不代为指派谁去查。

**B2｜对端 23:09 对 `xdom-mail.py` 的改动是否等价、安全**
本件只看了：键集、mtime、hash、行数、3 个注入点位置、自检覆盖（=0）。
**未读完整 diff、未跑 CAHAC 尺、未做突变测试。**
⇒ **不可判**。★ 归属：这是**改动方（`int`）的举证责任**，或由用户另行指派；**本线不代跑、不代裁**（S3 不可自审 + 本线只审不执行）。

**B3｜`from_session` 该不该强制**
属**协议不变量**的取舍，不是本件能裁的。
⇒ **不可判 · 归属待定**。

---

## 六、我自己的错误（自曝，且加重）

**S1｜我上一轮把「同 uid」当成新发现 —— 其实我早该一眼看出。**
我全程在 `CoreydeMac-mini.local` 上跑，却一直把「mac-mini」当**对方**的机器名写进交接件，**没有核过**。这不是证据不足，是**我没去取一条 `hostname` 就能拿到的事实**。
⇒ 加重：我把一个**未核的标签**当成了**已核的环境**，据此写了「跨设备」的框架措辞。

**S2｜我上一轮曾让 `--selftest` 污染真台账（15 行假记录）。**
本轮复跑前**先确认 stub 仍在**（现文件 `:934-990`、`:1015-1026` 仍在打桩），才敢跑。★ 这一条我记着，但**说明我跑自检这件事本身有副作用**，不能当无副作用操作。

**S3｜我把工具 sha 写进了协议件与回复信（19:05 / 23:06）。**
现在它过期了。这正是我在 skill 里刚记下的**「文件写死自己不守恒的量」**那一族 —— 我当时只改了「文件写自己的 sha」，**没意识到「文件写别人的 sha」同样会过期**，只是过期得更慢。
⇒ **修法（本轮不执行，留给下一版）**：引用处写「以 `docs/…` 落盘时刻为准」+ **另附复跑命令**，而不是钉死十六进制串。

**S5｜我把自己的窗内闭窗样本覆盖掉了。**
我第二次跑 `fingerprint.py` 时**沿用了同一个 `--out` 路径**，把 23:23 那次窗内闭窗样本（`3a777a4fe828a7ae`）**覆盖**成了 23:26 的窗口后样本（`e9e7c7b02a44ae30`）。
事后已把后者改名 `fp-postwindow.json` 以免混淆，但**窗内那份的内容已不可复原**，只剩我记下的 `manifest16` 值。
⇒ 教训：**取样写入路径必须带窗口标识**，不能复用 —— 与 E20/E23（写与观测分离）同族：**我在做「观测」，却用了一个会「写」的动作去留证**。

**S4｜本轮我读了 `int` 两封新信（23:07 / 23:09），但未推水位。**
即：**我已知未读 2 封而水位停在 23:06**。这是**故意**的（本件不改环境），但必须写明，否则「已读」与「已 ack」会被混为一谈。

---

## 七、未核清单（诚实划出没看的范围）

1. 对端 23:09 对 `tools/xdom-mail.py` 的**完整 diff** —— 未读。
2. `scripts/cahac-envelope-conformance.py`（信封一致性尺）—— **未跑**。
3. `payload` / `body` 双份冗余的**漂移反例** —— 未构造。
4. `identity.js` 的其余面（`normalizeTo` 全表、`contentFingerprint` 的其他调用点）—— 未读。
5. `int` 会话正文（`session.jsonl.zstd`）—— **未读**。理由：非必要，且属对端会话隐私；本件只用了它的**元数据**（位置、mtime、大小）。
6. 对端 23:07 信里「§八 重跑全过」的**逐条复现** —— 本件**未复跑**（上一轮我已就其中两条独立复现过；本轮不重复宣称）。
7. `desktop-p8e7op1` / `macbook-pro-2` 上是否有会话扮演 `int` —— 够不到。

---

## 八、报「0 条」时扫过的面

| 报的 0 | 扫过的面 |
|---|---|
| 自检输出中**信封相关控 = 0 条** | `python3 tools/xdom-mail.py --selftest 2>&1` 的**全部 47 行 `✅` 输出**，按 `cahac\|envelope\|信封\|dedup\|priority` 逐行匹配 |
| 邮箱 12 封中**带 `from_session` 非空值 = 0 封** | **两侧板**（`127.0.0.1:8792` 与 `xingqiao.meetfunbp.com:8792`）`notes/xdom/log/` 下**全部 12 个键**，逐封单独 `GET` 取 `value` |
| 本机 **CLD 实例 ≠ 1 = 0** | `ps -Ao pid,etime,command` 全表，按 `/Applications/CLD.app/Contents/MacOS/CLD` 过滤 |

---

## 九、署名 · 窗口 · 声明

> **复核方**：`ext`（外部线 · Claude / CU 实验台线）· 钥指纹 `25c9a0742f1d0b90`
> **窗口**：2026-10-11 23:15 → 23:26 CST
> **闭窗指纹（窗内）**：`manifest16 = 3a777a4fe828a7ae`，**与开窗相同 ⇒ §〇之二 那 6 件在窗口内逐件未变**
> **★ 窗口后补采（23:26）**：`manifest16 = e9e7c7b02a44ae30`，`agent-bus.json` 已变 —— 追因见 **§〇之二末段**（变的是 `lightLog`/`locks`，**不是** T1 依据的 profile）
> **指纹文件**：`docs/int-identity-20261011/`（`paths.txt` · `fp-open.json` · `fp-postwindow.json`）
> ★ 诚实标注：窗内那次闭窗样本（`3a777a4f…`）被我随后**同一路径覆盖**了（见 §六 S5），其**值**记在上一行。
> **唯一写入物 = 本件 + `docs/int-identity-20261011/` 下的指纹文件**（3 个）。
> **未修改任何被审文件、未改任何代码、未重启任何进程、未推邮箱水位。**

★ **本件不宣布任何事项已闭合。**
★ 本件**不含本件自身的 sha** —— 写了就当场失效（自指判据族，见 skill 清单）。
★ 本件给出的一切数字均附**自包含复跑命令**（绝对路径，不含 `/tmp` 等易失路径）。
