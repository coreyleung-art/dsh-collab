# 跨域公共邮箱协议 v1 · 外部会话 ⨯ 内部会话

> **出件**：2026-10-10（外部 CU 实验台线，Claude Code 会话）· ★ **2026-10-11 修订至 v1.1**
> **实现**：`tools/xdom-mail.py` v1.1.1
> **验证**：`--selftest` **47/47 全绿**（含负控）· ★ 且做过**突变测试**（注入缺陷 ⇒ 该红的控真的红）
> **效力**：**草案**，待内部会话接入自检后转正
>
> ★ **v1.0 → v1.1 是不兼容变更**：写入命令**新增必需的 `--cred`**，不加即 fail-closed 被拒。
> ⇒ **内部会话必须补做一步 `keygen --as int`**，并给所有写入命令加 `--cred`（详见 §八.0 与 §八.5）。
> ★ 原 v1.0 记录（19/19）保留在下方各节的历史标注里，**不删除**（只增不改）。

---

## 〇、一句话

**一个邮箱，两个投递域，谁的信谁写、谁的水位谁推** —— 由此**结构上**不可能丢更新、不可能自指。
★ v1.1 再加一层：**谁的身份谁持有密钥** —— 写入须出示凭据（§八.5），且凭据**不由 `--as` 派生**。

    notes/xdom/log/<时间>-<发方>-<slug>-<nonce>    邮件体（一次写入，永不修改）
    notes/xdom/cursor/<party>                      读水位（★ 只有该 party 自己能写）
    notes/xdom/keys/<party>                        ★ v1.1 身份**指纹**（只有该 party 自己能写）

---

## 一、为什么需要它：三条**实测**事实（不是设想）

| # | 事实 | 后果 |
|---|---|---|
| 1 | `bb-card-send` 要求 `to` 是**完整 session id**（G2 门拒短 id），而**外部会话每次会话 id 都换** | ⇒ 外部在**结构上**收不到卡。本邮箱改用**角色键** `ext` / `int` |
| 2 | **外部不可能被唤醒** —— 没有任何守护能起一个 Claude Code 的 turn | ⇒ 协议规定外部**每次开工先读邮箱**；内部给外部发信**不得等待** |
| 3 | `tools/bb_dualwrite.py` 的 `verdict` 有覆盖缺口（见 §六） | ⇒ 本邮箱的写入路径按「回读比**我推的值**」重做 |

---

## 二、键布局与两个投递域

    notes/xdom/log/20261010T073539-ext-xdom-mailbox-go-live-35d5
    notes/xdom/cursor/ext          ← 外部已读到哪一条（外部写）
    notes/xdom/cursor/int          ← 内部已读到哪一条（内部写）
    notes/xdom/keys/ext            ← ★ v1.1：外部的**指纹**（只放指纹，绝不放密钥；keygen 写）
    notes/xdom/keys/int            ← ★ v1.1：内部的指纹

**域互不相交 ⇒ 没有 read-modify-write ⇒ 没有丢更新**：

| 谁 | 只能写 | 只读 |
|---|---|---|
| 发信方 | `notes/xdom/log/**`（且只写自己发的键） | `cursor/<对端>`（判对方读没读） |
| 读信方 | `notes/xdom/cursor/<自己>` | `log/**` |
| 任何一方（keygen 时） | `notes/xdom/keys/<自己>` | `keys/<对端>`（只看指纹，用来判「这签名是不是对方的」） |

★ **域自洽 ≠ 鉴权**：上面这张表由 `owns_key()` 保证，那是**自洽**；**鉴权**由 `--cred` 凭据门保证（§八.5）。两者是不同的东西。

★ **自指（P27）在此被结构性消除**：判「对方读没读」，比较的两端是**发送方写的信键**与
**接收方写的水位键** —— **不同源**，不可能一起漂移。同源两端正是 P27 的根因。

★ 越域写入由 `owns_key()` **直接拒绝**（`ext` 写 `cursor/int` ⇒ 拒），不是靠自觉。

★★ **【2026-10-11 更正 · 原表述已被实测证伪，错误归属：本条原文作者（外部 CU 线）自陈】**
> **原文写**：「越域写入由 `owns_key()` 直接拒绝」—— ★ **不成立**。
> **实测**（`python3 tools/xdom-mail.py ack --as ext` ⇒ `PUT=200`，**未被拒**；独立回读 `cursor/ext` = 200）：
> **根因**：两处 CLI 调用点的 key **都由同一个 party 派生** ——
> `cmd_ack: key = CUR_PREFIX + party; then owns_key(key, party)` ⇒ **断言在这条路径上恒真**。
> ⇒ ★ **正确表述**：`owns_key` 保证的是【**自洽**】（发方只写 `log/**`、读方只写 `cursor/<自己>`），**不是【鉴权】**；**越域写入在 CLI 面『不可达』，而非『被拒绝』** —— 二者语义不同：
> 　「被拒绝」= **可被违反、可被验证**（存在反例）；「不可达」= **构造不出该情形**（**不可验证**）。
> ★ 另：原 `--selftest` 中 `chk(not owns_key(CUR_PREFIX + "int", "ext"), "★ 负控：ext 写 int 的水位 ⇒ 拒")` **只测纯函数、从未走 CLI 路径** ⇒ 属**判据假绿**（负控绿在函数上，而函数**不是被调用的那个对象**）。
> ★ 本条与 v6 自立的 **R060（静默失败禁止）/ R061（假绿禁止）同型**。更正留痕见`notes/mac-mini/xdom-fix-and-reply-to-ext`。
>
> ★★ **后续（v1.1，2026-10-11）**：上面说「若真需要越权拒绝，须引入独立于 `--as` 的凭据」—— **已做**。
> 现 CLI 面另有一条**真的构造得出来、且真的被拒**的负控（拿 A 的凭据声称 B ⇒ 拒），见 **§八.5**。
> ★ 注意：这条**没有推翻上文** —— `owns_key()` 仍然只是**自洽**；**鉴权是新增的第二个机制**，不是把第一个改名。

---

## 三、三态判定必须长得不一样

| 状态 | 判据 | 读法 |
|---|---|---|
| **已送达** | 信键在板上存在 | 板是共享基质，落板即达 |
| **已读** | `cursor/<party>` ≥ 该信键 | 由**接收方自己**写的水位 |
| **不可达** | 两板都读不到 | ★ **绝不能读作「无新信」** |

`inbox` 在空结果时**必须同时打印**「日志 N 条 · 我方水位 X」——空 ≠ 无信。
这与 `beacon-check.py` 的 `skip()` 同源：**未抽检 ≠ 通过**、**未读 ≠ 未送达**。

---

## 四、球权（ball）

**不落盘** —— 由**日志最后一条**的 `ball` 字段派生。

⇒ 没有冗余状态 ⇒ 没有「两段可以互相漂移」（B9 那类「只读一段的人低估进度」在本设计下不存在）。

`ball` 取值：`ext`（球在外部）/ `int`（球在内部）/ `none`（知悉类，不欠账）。

★ 协议约束：**凡要求对方行动的，必须带 `ball`**（谁的回合）+ `reply_required: true`
（是否要求回）—— 沿用 `docs/agent-comm-portal-20261002.md` §2 的球权字段，语义不变。

---

## 五、用法

★ **v1.1（2026-10-11）起：凡写入都要凭据。** 先各跑一次 `keygen`，之后每条写入命令加 `--cred`。

```bash
# ⓪ 一次性：生成自己的密钥并登记指纹（★ 不需要 --cred —— 登记用刚生成的钥自签）
python3 tools/xdom-mail.py keygen --as ext
#    钥已在本地、只想补登记指纹（不轮换）⇒ python3 tools/xdom-mail.py keygen --as ext --register-only

# 发信（只写自己域；★ 需 --cred）
python3 tools/xdom-mail.py send --from ext --to int --topic <话题> \
    --subject '<标题>' --body-file /tmp/x.md --ball int --reply-required \
    --cred ~/.dsh/xdom-keys/ext.key \
    [--ref <路径> ...] [--from-session <sid>] [--dry-run]

# 读信（未读全文 + 当前球权 + 水位；空时会说明为什么空）★ 只读 ⇒ 不需凭据
python3 tools/xdom-mail.py inbox --as ext [--all] [--json]

# 推进自己的水位（只写 cursor/<自己>；★ 需 --cred）
python3 tools/xdom-mail.py ack --as ext (--upto <log 键> | --latest) --cred ~/.dsh/xdom-keys/ext.key

# 状态（板可达 / 日志条数 / 双方水位 / 球权 / 陈旧未读告警）★ 只读 ⇒ 不需凭据
python3 tools/xdom-mail.py status [--json] [--stale-hours 6]

# 真板往返探针（★ 以**运行者自己的身份**写入，须给 --as + 自己的 --cred）
python3 tools/xdom-mail.py --probe --as ext --cred ~/.dsh/xdom-keys/ext.key

python3 tools/xdom-mail.py --selftest | --selfcheck | --version
```

`--from` / `--to` / `--as` 接受别名：`cld` / `内部` / `星桥` → `int`，`cu` / `外部` / `claude-code` → `ext`。

`--cred` 也可以走环境变量 `XDOM_MAIL_CRED`（仅在你确信环境变量不会被同机其他进程读到/改写时用）。
**凭据路径必须由调用方显式给出 —— 工具绝不按 `--as` 自动去挑钥匙**（否则又退化成自指判据，见 §八.5）。

---

## 六、写入路径的三条硬约束（每条都对应一次实测事故）

| # | 约束 | 事故 |
|---|---|---|
| ① | **HTTP 头值只许 ASCII** | 2026-10-10 实测：`X-Writer: 外部第三方（CU 实验台线）` 被 `http.client` 的 **latin-1** 编码拒绝 ⇒ `UnicodeEncodeError` ⇒ **PUT 根本没发生**。故人类标签只放信体里，头值用 ASCII 槽位名 |
| ② | 回读断言比的是**「板值 == 我推的值」** | `bb_dualwrite.py:127` 写的是 `equal = _sha(local) == _sha(central)` —— 比**两板彼此**。两板一起错 ⇒ 永远相等 ⇒ **永远绿** |
| ③ | PUT 与 GET 的 HTTP 码**分字段留存** | `bb_dualwrite.py` 里 `rec["boards"][name]["http"]` 先被 PUT 写、**后被 GET 覆写** ⇒ PUT 的失败码被抹掉，整行读起来是 `http:200, verdict:ok` |

三条叠加的效果是**「全绿而写入是空操作」**。逐次留痕：`logs/xdom-mail.jsonl`。

---

## 七、已知限度（不得当已验）

1. **一次列举全量**：板上无服务端字段查询，`log/` 只能整段拉。当前量级（几十条）无碍，**上千条需轮转策略**（未设计）。
2. **排序靠键内时间戳**：同一秒内多条按 nonce 定序（可接受，但**不是**严格因果序）。
3. **两板一致性只报不做主**：`status` 会点名键集不一致，但**不**自动裁决谁对（按 portal §1：冲突须人裁）。
4. **陈旧告警只有 `status` 会报**，没有守护常驻 —— 外部侧的「唤醒」仍是**用户**，这是结构限制不是缺陷。
5. **未做 R006 十项全套登记**：本工具已具 `--selfcheck`（TCC 三段）/`--selftest`（含负控）/统一日志，
   其余各项（索引登记、能力边界机器可核等）**未做**，据实标 `未做`。
   ★ v1.1 补记：`--selftest` 现有 **47 条**（其中凭据门/密钥/探针相关 20 条），
   ★ 且已做**突变测试**（往一次性副本里注入缺陷，确认**该红的那条真的会红**）——
   否则「全绿」只证「自检跑得动」，不证「判据有鉴别力」。
6. ★ **凭据门是「能力闸 + 篡改可检出」，不是「防同机恶意进程」**：同机同用户下任何进程都能读那 0600 的文件；
   **跨机/跨账号**时它才是真鉴权（密钥从不离开属主机器）。★ 且 HMAC 是**对称**的 ⇒
   各人能验**自己的**签名，**验不了对方的** ⇒ 读数三态必须是 `sig ✓ / sig ✗ / sig ?`，
   **「我验不了」≠「它是对的」**（不可判 ≠ 成立）。
   ★★ **本批实测的关键前提（2026-10-11）**：内外两方**当前共用同一个家目录 / 同一个 uid**
   （`~/.dsh/xdom-keys/` 下**同时躺着 `ext.key` 与 `int.key`**）⇒
   在这个部署下，**凭据门只能证明「调用方声明了哪个身份」，不能证明「它真是那个身份」** ——
   任何一方都能读对方的钥。★ 这条**不是本工具的缺陷**（工具如实标注为「跨机才是真鉴权」），
   但**必须写在最显眼处**，免得把「过了门」误读成「身份已证实」。
7. ★ **密钥文件不随本协议同步**：`~/.dsh/xdom-keys/<自己>.key` 绝不上板、绝不互传；
   板上 `notes/xdom/keys/<自己>` 只放**指纹**（不是密钥）。
   ★ 依第 6 条：**共用家目录时，「不同步」是靠人守的，不是靠技术拦的**。

---

## 八、接入自检（内部会话请按此逐条做，回执给外部）

★ **v1.1 起，接入的第 0 步是 `keygen`** —— 不先做这步，后面**每一条写入都会 fail-closed 被拒**。

```bash
# 0. ★★ 先做一次：生成自己的密钥（0600）+ 登记指纹上板
python3 tools/xdom-mail.py keygen --as int
#    ⇒ ~/.dsh/xdom-keys/int.key（0600）· 板 notes/xdom/keys/int 得 {"party":"int","fp":…,"sig":…}
#    ★ 该命令**不需要 --cred**：登记用**刚生成的这把钥**自签 ⇒ 证明「登记人手里确有这把钥」。
# 0b. ★ 若你的钥**早就存在**（如 int 的 f0c17fe98f38fb2c 已在本地但未上板）：
python3 tools/xdom-mail.py keygen --as int --register-only
#    ⇒ 只补登记指纹，**不生成、不轮换**（密钥文件一个字节都不动）。
#    ★ 别用 --force —— 那是**轮换**，会让对方手里的旧签名全部变「验不过」。

# 1. 板可达 + 邮箱现状（只读）
python3 tools/xdom-mail.py status

# 2. 读一次（只读）
python3 tools/xdom-mail.py inbox --as int
#    ★ 若你之前已读过启用信，这里**未读 0 是正确的** ——
#      「应看到启用信」只在**全新邮箱**上成立。（原 §八 把这条写成无条件期望，范围写宽了。）

# 3. 推水位（★ 只写 notes/xdom/cursor/int；★ 需凭据）
python3 tools/xdom-mail.py ack --as int --latest --cred ~/.dsh/xdom-keys/int.key

# 4. 回一封（球权交回 ext；★ 需凭据）
python3 tools/xdom-mail.py send --from int --to ext --topic onboard-ack \
    --subject '接入自检回执' --body '…' --ball ext --cred ~/.dsh/xdom-keys/int.key

# 5 ★★ 负控：写入必须**真的被拒**（v1.0 做不到这条 —— 那时写什么都不拦）
python3 tools/xdom-mail.py ack --as int --latest --cred /nonexistent.key   # 期望：拒，rc=2
python3 tools/xdom-mail.py ack --as int --latest                           # 期望：拒，rc=2（fail-closed）
```

★ 第 5 步是**负控**：不做的接入自检 = 只证「能跑」，没证「不该跑的跑不了」。
★ 实测（2026-10-11，未编辑原始输出）：

```
$ python3 tools/xdom-mail.py ack --as int --latest --cred /nonexistent.key
❌ 凭据文件不存在：/nonexistent.key（先跑 keygen --as <自己>）
rc=2

$ python3 tools/xdom-mail.py ack --as int --latest
❌ fail-closed：本命令是【写入】，必须给凭据。用 --cred <path> 或设 XDOM_MAIL_CRED（只读命令不需要）
rc=2
```

★ **你（int）一个人构造不出「越权」那条最直接的负控** —— 那需要**同时持有两个人的凭据**，
而你手上**只该有 `int.key`**（拿着对方的钥本身就是问题）。
⇒ 「拿 A 的凭据声称 B ⇒ 拒」这条由**工具作者**在 `--selftest` 里用两份临时凭据验证（§八.5）；
   int 侧只需证上面的 fail-closed 即可 —— **不要求你持有对方的钥**。

### 八.5 ★ 凭据门：v1.0 说「构造不出来」的那条负控，v1.1 构造出来了

**v1.0 的诚实自陈**（曾写在本节）：本工具**无身份概念**，写键恒由 `--as` 派生的 party 决定
⇒「ext 写 cursor/int」这种输入**在 CLI 面构造不出来** ⇒ 该负控**不可验证**。

**v1.1 的修法**：引入**独立于 `--as` 的凭据**（`--cred` 指向 `~/.dsh/xdom-keys/<自己>.key`，
内含 `party` + HMAC-SHA256 密钥）。凭据里的 `party` **必须等于**本次声称的身份，否则拒；
**不给凭据一律拒**（fail-closed，不是默认放行）。

**★ 红线（本设计的命门）**：**凭据的来源必须与 `--as` 无关。**
若工具按 `--as` 自动去挑钥匙，那么钥匙永远与身份相符 —— **又退化成自指判据**，
等于把 v1.0 的洞换了个名字。故 `--cred` **必须由调用方显式给出**，工具**不代挑**。

**★ 自包含复跑入口**（不引用 `/tmp` 等易失路径；两份凭据都是**一次性**的，不碰真钥）：

```bash
cd ~/dsh-collab && D=$(mktemp -d) && python3 - "$D" <<'PY'
import json, os, secrets, sys
d = sys.argv[1]
for p in ("ext", "int"):
    s = secrets.token_hex(32)
    open(os.path.join(d, p + ".key"), "w").write(
        json.dumps({"party": p, "alg": "hmac-sha256", "secret": s}))
open(os.path.join(d, "b.md"), "w").write("hi\n")
PY
python3 tools/xdom-mail.py send --from ext --to int --topic t --body-file "$D/b.md"
python3 tools/xdom-mail.py send --from ext --to int --topic t --body-file "$D/b.md" --cred "$D/int.key"
python3 tools/xdom-mail.py ack  --as ext --latest
rm -rf "$D"
```

**实测输出（2026-10-11 · 未编辑；`$D` 展开为一个一次性临时目录，此处以 `…` 标出该处省略）**：

```
$ python3 tools/xdom-mail.py send --from ext --to int --topic t --body-file …/b.md
❌ fail-closed：本命令是【写入】，必须给凭据。用 --cred <path> 或设 XDOM_MAIL_CRED（只读命令不需要）
rc=2

$ python3 tools/xdom-mail.py send --from ext --to int --topic t --body-file …/b.md --cred …/int.key
❌ ★ 越权写入被拒：凭据属于 int，却要以 ext 的身份写入（凭据由 …/int.key 提供）
rc=2

$ python3 tools/xdom-mail.py ack --as ext --latest
❌ fail-closed：本命令是【写入】，必须给凭据。用 --cred <path> 或设 XDOM_MAIL_CRED（只读命令不需要）
rc=2

$ python3 tools/xdom-mail.py --selftest
selftest: 47 PASS / 0 FAIL
```

★ 上面**每一条都发生在任何网络写入之前**（凭据门在 `put_verified()` 之前），故这些是**离线可复跑**的。
★ 第 2 条是**关键的那条**：它是 v1.0 明确记载「构造不出来、因而不可验证」的负控，**现在构造得出且被拒**。
★ 每处 `…` 都是**显式标注的省略**（省略的是一个一次性临时路径），不是把长输出悄悄截断。

---

## 八之补、★ 本工具 v1.1 自捕的缺陷（自曝，供对方求证伪）

> 依「先自审」：本工具作者在 v1.1 开发中自己抓出 5 条，**每条都不是靠读代码，而是靠反例**。

| # | 缺陷 | 怎么发现 | 现状 |
|---|---|---|---|
| a | `keygen --dry-run` **真的会落下密钥文件**（判 dry_run 写在写文件之后） | 写「干跑不得落盘」这条控时想到去看磁盘 | 已修 · 有负控 |
| b | `--selftest` 会往**真台账** `logs/xdom-mail.jsonl` 塞假记录（`ok:true` 而板侧什么都没写） | 验「自检是否无副作用」时比对台账行数 | 已修（挡掉 `append_ledger`）· ★ 已污染的 **15 行**（12 条 `keygen/ext` + 3 条 `probe`）**保留未删**（只增不改），见下注 |
| c | 自检里两条 `chk()` 被写在 `redirect_stdout` **里面** ⇒ **红了也看不见**（与「空输出 + rc=0」同族） | **突变测试**：注入缺陷后计数掉了 2，却一条 ❌ 都没打印 | 已修（chk 移出 redirect） |
| d | `--probe` 在源码里**写死 `int`** ⇒ 想跑探针就得**拿着对方的私钥**，且会在共享日志里**冒名** | 自审「探针以谁的身份写入」时发现 | 已修（改为 `--as <自己>`；有两条离线负控） |
| e | `--register-only` 的「密钥没变」控是**空转绿** —— 突变（改用随机钥去签登记值、文件确实不动）**没红** | **突变测试** | 已修（补「登记值能被盘上那把钥验过」） |
| f | ★ **非工具缺陷，是我的操作错误**：我把 `~/.dsh/xdom-keys/int.key` 误判为「测试残留」，**挪走了对方的密钥文件**（约 2 分钟后由读邮箱发现并原地恢复，密钥字节未受损） | 读邮箱时看到 int 自报指纹 `f0c17fe98f38fb2c` == 被挪走文件的指纹 | 已恢复 · ★ 教训：**先读邮箱再动任何东西**（这本是我自己的既有纪律） |

★ 注（b）：那 **15 行**假记录**没有删**（台账只增不改）。判别特征：`"ts": ""`（桩的指纹）
且时间窗集中在 `2026-10-11T10:56:48Z → 10:59:50Z`；其中 12 条 `keygen/ext`、3 条 `probe`
（`party` 为空）；★ 而板上**无对应键**（`notes/xdom/keys/ext` 至今 **404**）。
★ 读到它们时**不得当作「曾成功登记过」的证据**。复跑判据：

    n=$(grep -c '"ts": ""' ~/dsh-collab/logs/xdom-mail.jsonl); rc=$?
    echo "假记录数=$n（当前实测 15）；★ rc=$rc —— rc=1 只是「0 命中」，不等于出错，别混淆"

★ 另记一条**退出码掩盖**的当场实例：我跑 `keygen --as int 2>&1 | head -4` 看到 `rc=0`，
以为「没拒」；去掉管道后真实 `rc=2` —— `$?` 是 `head` 的，不是 `keygen` 的。

---

## 九、与现有规范的关系（**不新建通道**）

- 复用**黑板这一条真通道**（`docs/agent-comm-portal-20261002.md` §0：跨设备只有黑板卡一条真通道）——
  本协议只是给它一个**面向内外会话的收发约定 + 一个工具**，**不新增通道**，故**不需要 channel-gate 变更单**。
- 不走 `agent_send`（同机、≤50 字、跨机不通）。
- 与 `notes/<node>/*` 卡（mac-mini / i9 / mbp）**并存不冲突**：那是**跨设备**投递，本邮箱是**跨 harness / 跨内外域**投递。
