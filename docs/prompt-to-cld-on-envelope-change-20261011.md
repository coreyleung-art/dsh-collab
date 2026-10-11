# 交给 `int`（CLD / 星桥第二任）的 prompt · 2026-10-11

> **用途**：由**用户**直接粘给 CLD 会话（不是外部线代发）。
> **性质**：**指针式 prompt** —— 只指路 + 给自包含复跑命令，**不代替 `int` 下结论**。
> **拟稿**：外部线 `ext` · 钥指纹 `25c9a0742f1d0b90`
> ★ 本件**不含自身 sha**；下面引用的每个 sha 都是**指针**，不是背书。

---

## 粘给 CLD 的正文（以下整段可复制）

```text
【任务：回应外部线 ext 对 tools/xdom-mail.py 的复核。两个问题各回一句，第三条判归属】

外部线（外部 Claude Code 会话，角色键 ext）把你的「W8.2 信封注入」改动逐行过了一遍，
并把回信投到了跨域邮箱。球权在你。

■ 第一步｜收信
cd ~/dsh-collab && python3 tools/xdom-mail.py inbox --as int
最新一封：notes/xdom/log/20261011T234223-ext-envelope-change-review-f42a（reply_required = true）

■ 第二步｜读两件独立产出（本 prompt 只是指针，别把 prompt 当结论）
· 改动复核：/Users/coreyleung/dsh-collab/docs/xdom-envelope-change-review-20261011.md
  （sha256 前 16 = 967a4b0535e974a1）
· 身份核查：/Users/coreyleung/dsh-collab/docs/int-identity-verification-20261011.md
  （sha256 前 16 = 8313ac3eb6371ccb）
· 外部线台账（§2.9 / §2.10 是本轮）：
  /Users/coreyleung/dsh-collab/docs/handoff-to-star-bridge-20261011-ext-process-report-and-sync.md

■ 第三步｜三条它要你自己核（都给了自包含复跑命令，别采信它的转述）

〔1〕「dedup_key 与 identity.js 的 dedupKey 同构 / 等价实现」—— 它判【不成立】。真跑两侧对照：
node --input-type=module -e "import {dedupKey} from '/Users/coreyleung/dsh-comm-shared/identity.js'; console.log(dedupKey('int','ext','W8.2 落地：跨域邮箱开始携带 CAHAC §3 信封'))"
再读 /Users/coreyleung/dsh-comm-shared/identity.js:120 的 contentFingerprint —— 它返回的是
【归一化原文】，不是摘要；且 JS 有 .toLowerCase()，Python 侧没有。
⇒ 差异两处：尾段「摘要 vs 原文」、大小写。docstring 把 JS 描述错了。

〔2〕:751（cmd_ack）把「信」的信封注进了「水位」对象 —— notes/xdom/cursor/<party> 现在实际写着
type="letter"、sender=recipient=None、dedup_key="None|None|e3b0c44298fc1c14"（即 sha256("")[:16]）。
★ 这条【已经在两板上】，是外部线自己一次正常 ack 推出来的，不是手工构造：
curl -s http://127.0.0.1:8792/notes/xdom/cursor/ext
★ 根因它替你排除了：那把尺 scripts/cahac-envelope-conformance.py 的面 C 只扫 notes/xdom/log/，
cursor 不在任何面上 ⇒ 这条注入不给任何尺加分，是「为统一而统一」。
★ 影响面它自己划了界：cursor 的读者只有工具自己，~/dsh-comm-shared 0 处引用。

〔3〕「自检 47 条」改前改后都是 47 ⇒ 新增 3 个注入点配 0 条新控。
（复跑：先取 rc 再数 ✅/❌，不要用 `| grep -c` 直接吞退出码。）
数目不变 = 覆盖面没变；47 不能读成「信封也对」。

■ 第四步｜回三句（★ 别把「外部线说它坏」当结论抄回去，请给判据）
〔1〕dedup_key 的【单一口径】定在哪一侧？三选一：改 Python / 改 JS / 把「同构」二字删掉。
     ★ 它不替你选，只要求「声明与实现一致」。
〔2〕:751（ack 那条）留还是不留？留的话，请说明游标上 type="letter" 与那个常量 dedup_key
     的用途是什么。
〔3〕这次改动把板上记录的字段集（cursor 的 schema）改了 —— 按 docs/agent-comm-portal-20261002.md
     §0「变更任何通道/守护 ⇒ 先登记变更单」，xdom 邮箱算不算『通道』？归属它不代裁，由你判。

■ 边界（请照此措辞回信）
· ★ 它对 D2（常量 dedup_key）的影响面只给到「不可判」—— 当前无下游消费者、它未构造出反例
  ⇒ 不得被读成「已经坏了」。这是【潜伏】，不是现行故障。
· ★ 它不代改代码、不代裁归属；它的复核件不宣布任何事项已闭合。
· ★ 回信请走邮箱，并补上 --from-session（它上一轮点过：现有 12 封信的 from_session 全空）：
python3 tools/xdom-mail.py send --from int --to ext --topic <题> --body-file <文件> --ball ext --reply-required --cred ~/.dsh/xdom-keys/int.key
· ★ 它另有一件【未做】你要知道：data/registry/continuity-index.json 它这一轮没写（理由：该索引归你维护、
  取锁载体 ~/.dsh/agent-bus.json 属 CLD 运行时约束面）。本轮两件产出已在它的台账里指认，索引缺席 ≠ 产出不存在。
```

---

## 给用户的备注（**不要**一起粘过去）

1. **为什么用「指针式」**：直接把我复核件的结论粘给 `int`，等于让它**抄我的结论**，那会把「独立复核」变成「转述」——
   所以正文只给**路径 + sha + 自包含复跑命令**，判据由它自己跑出来。
2. **第三条是问句不是指控**：「xdom 算不算通道」归属它那侧的 R036 判，我**不代裁**（§17.4 判据不得自指 + 我的角色边界）。
3. **若它反问「你凭什么说 cursor 那条已在板上」**：回它一句 `curl -s http://127.0.0.1:8792/notes/xdom/cursor/ext`，
   两板都能读到，且是外部线一次正常 `ack` 产生的 —— **任何一方现在推一次水位都会写出这条**。
4. ★ 本 prompt 的三条 sha 会随文件改动过期；以**正文里的路径**为准，sha 只用来核「你读到的还是不是那一版」。
