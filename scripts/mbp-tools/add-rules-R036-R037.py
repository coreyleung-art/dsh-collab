#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""入账 R036（黑板双实例必须逐板写+回读）与 R037（供应链残包三验）。
来源：会话 session-ab866871（MBP 本机 Claude Code 侧）2026-10-02 的实测与判据。"""
import json, io, os, shutil, datetime

R = os.path.expanduser("~/dsh-collab/rules-registry")
JP = os.path.join(R, "rules.json"); MP = os.path.join(R, "RULES.md")
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
shutil.copy2(JP, JP + ".bak-R036-R037-" + STAMP)
shutil.copy2(MP, MP + ".bak-R036-R037-" + STAMP)
print("已备份 (.bak-R036-R037-%s)" % STAMP)

d = json.load(io.open(JP, encoding="utf-8"))
rules = d["rules"]
have = {r.get("id") for r in rules}
assert "R036" not in have and "R037" not in have, "编号已存在"
TODAY = "2026-10-03"

r036 = {
    "id": "R036",
    "name": "黑板双实例写入不传播 —— 必须逐板显式写 + 逐板回读断言",
    "category": "工程",
    "scope": "all-bus-devices",
    "status": "enforced",
    "version": "1.0",
    "source": "会话 session-ab866871（MBP 本机 Claude Code 侧）2026-10-02 实测；"
              "本会话 session-20b800d4 同期实证",
    "summary": "黑板有两实例（mac-mini 本地板 100.120.203.20:8792 / 星桥中枢 "
               "xingqiao.meetfunbp.com:8792）。**向单板 PUT 不会传播到另一板** ⇒ "
               "写一张卡必须**逐板各写一次**，并**逐板回读断言**。"
               "「回读断言」不是保险措施，是**必要条件**（单板写入 ⇒ 另一板 404）。",
    "detail": "硬证据（对端实测序列）：PUT 板① → 200；随即 GET 板② → **404**；"
              "再 PUT 板② → 200；两板再回读均 200。⇒ 两板**各自独立**，无双写同步。"
              "另实测：**中枢不支持 `?prefix=` / `?key=` 过滤**（传入仍返回全量），"
              "而本机板支持前缀过滤 ⇒ **两实例的「列举/计数」不可互代**。"
              "SSE(8803) 与 HTTP(8792) 端点内容是否一致**仍是待验假设**，"
              "与本条（写入不传播）是**两个不同命题，不得合并**。",
    "enforcedBy": "① 写卡必须**逐板各 PUT 一次**；② 写完**逐板回读断言**（键名与关键字段相符）；"
                  "③ 鉴权头**两板不同**：本机板 `Authorization: Bearer <token>`，"
                  "中枢 `X-Webhook-Token: <token>`；④ 中枢必须用 **http**"
                  "（`https://…:8792` 会 ~15s 连接超时，DNS/ICMP 正常，属端口协议问题）；"
                  "⑤ 写入动词用 **PUT**（`POST` 返回 `use /subscribe or /register`）；"
                  "⑥ **URL 路径就是键**（`/notes/<key>`→键 `notes/<key>`；"
                  "`/nodes/mbp/heartbeat`、`/data/discovery/agents/mbp` 同理），**勿再叠一层 `notes/`**；"
                  "⑦ `dsh-tools` 只有 `bb-read`、**无 bb-write** ⇒ 写卡须手写 PUT",
    "added": TODAY,
    "approvedBy": "对端建议固化为规则；本会话执行入账",
    "approvedAt": TODAY,
    "details": "与 R034(静默失败必须可见) 相关：单板写入时另一板 404 —— 若不回读断言，"
               "发送方会以为「已落板」，接收方却读不到，属典型静默失败。"
               "另：跨机投递只有黑板一条路（`agent_send` 对一切跨机别名均 queued），"
               "故本条的「逐板写」是跨机协作的必要前提。",
}

r037 = {
    "id": "R037",
    "name": "供应链残包三验（私服/镜像制品完整性，装前必跑）",
    "category": "工程",
    "scope": "all-bus-devices",
    "status": "enforced",
    "version": "1.0",
    "source": "会话 session-ab866871 2026-10-02 诊断（npm 私服残包致 claude 命令失效）；"
              "判据由该会话提出并要求入账",
    "summary": "从私服/镜像安装制品前必跑**三验**；任一失败即判**残包**，"
               "**停止安装并改走可信源**，不得「先装上再说」。",
    "detail": "实证：`~/.npmrc` 指向内网私服 `http://100.120.203.20:4873`（Verdaccio）；"
              "私服 `@anthropic-ai/claude-code-darwin-arm64@2.1.266` 为残包 —— "
              "tarball **31,158,044 B**（官方 87,220,153 B）、"
              "`tar tzf` 报 `Truncated input file`、"
              "解包二进制 **37,469,496 B**（官方 199,422,144 B，仅 18.8%）、"
              "`codesign -dv` 报 `code object is not signed at all` ⇒ "
              "macOS arm64 内核 **SIGKILL（Killed: 9, exit 137）**；"
              "ad-hoc 重签名亦失败（`failed strict validation`）⇒ **Mach-O 结构残缺，非仅缺签名**。"
              "后果链：安装中断 ⇒ npm reify 已把 `bin/claude` 改名残留、新符号链接未重建、"
              "postinstall 未跑 ⇒ `claude: command not found`。"
              "典型成因：**代理下载中断后缓存残包，HTTP 200 但内容不全**。",
    "enforcedBy": "**三验**：① **体积比对** —— 私服与官方 registry 同名同版本 tarball 字节数对比；"
                  "② **`tar tzf` 解包检验** —— 报 `Truncated input file` 即残包；"
                  "③ **签名断言 + 运行检验** —— `codesign -dv`（应见 `Developer ID Application: …`），"
                  "并直接运行看退出码（**137 = SIGKILL**）。"
                  "**三验任一失败即判残包、勿继续安装。**"
                  "处置优先序：**scoped registry（结构门，推荐）** > 修镜像 cache（根治但成本高）",
    "added": TODAY,
    "approvedBy": "该会话提出并要求入账；本会话执行",
    "approvedAt": TODAY,
    "details": "与 R033(闸门有效性/判别器自校) 同族：三验即「用已知正负样本校准判据」"
               "在供应链场景的实例（官方源=正样本、私服残包=负样本，三验须能分开二者）。"
               "★ 处置选择的理由与今日主结论一致：**结构门优于纪律** —— "
               "scoped registry 让错误路径**走不通**；`DISABLE_AUTOUPDATER=1` 只是**不去走**，"
               "其它路径一旦触发更新仍会踩雷。"
               "注：本机 `~/.claude/settings.json` 明文存 token 且 BASE_URL 指向第三方 ⇒ "
               "凭据/合规问题**另立卡**，不混入本条。",
}

rules.append(r036); rules.append(r037)
d["rules"] = rules; d["version"] = "2.14.4"; d["lastUpdated"] = TODAY
io.open(JP, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
print("rules.json → version=%s 规则数=%d" % (d["version"], len(rules)))

md = io.open(MP, encoding="utf-8").read()
md = md.replace("> v2.14.3 | 79 条 | 所有总线设备必须服从",
                "> v2.14.4 | 81 条 | 所有总线设备必须服从", 1)
block = """## R036 ✅ 黑板双实例写入不传播 —— 必须逐板显式写 + 逐板回读断言
- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: 黑板有两实例（mac-mini 本地板 100.120.203.20:8792 / 星桥中枢 xingqiao.meetfunbp.com:8792）。**向单板 PUT 不会传播到另一板** ⇒ 写卡必须**逐板各写一次** + **逐板回读断言**。「回读断言」不是保险措施，是**必要条件**（单板写入 ⇒ 另一板 404）
- 硬证据(对端实测): PUT 板①→200；GET 板②→**404**；PUT 板②→200；两板回读均 200 ⇒ 两板各自独立、无双写同步
- 口径（易踩）: ①鉴权头两板不同 —— 本机板 `Authorization: Bearer <token>` / 中枢 `X-Webhook-Token: <token>` ②中枢必须 **http**（https 会 ~15s 连接超时）③动词用 **PUT**（POST → `use /subscribe or /register`）④**URL 路径就是键**（`/notes/<key>`→`notes/<key>`；`/nodes/mbp/heartbeat` 同理），勿再叠 `notes/` ⑤`dsh-tools` 只有 `bb-read`、**无 bb-write** ⑥**中枢不支持 `?prefix=`/`?key=` 过滤**（返回全量），本机板支持 ⇒ 两实例的列举/计数不可互代
- 关系: 与 R034 相关 —— 单板写入而另一板 404，若不回读断言即属典型静默失败
- 待验: SSE(8803) 与 HTTP(8792) 端点内容是否一致 **仍是假设**，与本条「写入不传播」是两个不同命题，**不得合并**

## R037 ✅ 供应链残包三验（私服/镜像制品完整性，装前必跑）
- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: 从私服/镜像装制品前必跑**三验**；任一失败即判**残包**，**停止安装并改走可信源**
- 三验: ①**体积比对**（私服 vs 官方 registry 同名同版本 tarball 字节数）②**`tar tzf` 解包检验**（报 `Truncated input file` 即残包）③**签名断言 + 运行退出码**（`codesign -dv` 应见 Developer ID；**137 = SIGKILL**）。**任一失败即判残包**
- 实证(2026-10-02): 私服 `@anthropic-ai/claude-code-darwin-arm64@2.1.266` tarball **31,158,044B**(官方 87,220,153B)、二进制 **37,469,496B**(官方 199,422,144B，仅 18.8%)、`code object is not signed at all` ⇒ macOS arm64 **SIGKILL(137)**；ad-hoc 重签名亦失败 ⇒ **Mach-O 结构残缺，非仅缺签名**。后果：安装中断 ⇒ bin 符号链接未重建 ⇒ `claude: command not found`。成因：**代理下载中断后缓存残包，HTTP 200 但内容不全**
- 处置优先序: **scoped registry（结构门，推荐）** > 修镜像 cache（根治但成本高）> `DISABLE_AUTOUPDATER=1`(纪律，仅不去走)
- 关系: R033 同族 —— 三验即「用已知正负样本校准判据」在供应链场景的实例

"""
md = md.replace("## 治理哲学（Φ 系列 · 明鉴维护 governance-philosophy.json v2.3）",
                block + "## 治理哲学（Φ 系列 · 明鉴维护 governance-philosophy.json v2.3）", 1)
io.open(MP, "w", encoding="utf-8").write(md)
print("RULES.md 已同步")
chk = json.load(io.open(JP, encoding="utf-8"))
print("校验: version=%s 规则数=%d 末两条=%s" % (chk["version"], len(chk["rules"]),
                                            [r["id"] for r in chk["rules"][-2:]]))
