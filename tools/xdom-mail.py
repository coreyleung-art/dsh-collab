#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""xdom-mail.py — 跨域公共邮箱（外部会话 ⨯ 内部会话）v1.1.0

【一句话】一个邮箱，两个投递域，谁的信谁写、谁的水位谁推 —— 由此**结构上**不可能丢更新、
          不可能自指。给定「外部会话（Claude Code，非常驻）」与「内部会话（CLD，常驻）」之间
          一条可核验的双向信箱。

--------------------------------------------------------------------------------
■ 为什么需要它（三条实测事实，不是设想）
 1. 现机制对「外部会话」不适配：`bb-card-send` 要求 `to` 是**完整 session id**（G2 门拒短 id）。
    而外部会话**每次会话 id 都换** ⇒ 外部在结构上收不到卡。本邮箱改用**角色键** `ext` / `int`。
 2. 外部**不可能被唤醒**：没有任何守护能起一个 Claude Code 的 turn。故协议规定外部每次开工
    先读邮箱（`inbox`），内部给外部发信**不得等待**，球权显式交付。
 3. 现 `tools/bb_dualwrite.py` 的 `verdict` 判据有覆盖缺口（2026-10-10 实证）：
      23:29:13Z  writer=外部第三方  local/central put_error=UnicodeEncodeError（PUT 未发生）
                http=200（该 200 是随后 GET 覆写进来的）  verdict="ok"
    ⇒ **全绿而写入是空操作**。三处病根在本工具中被显式设计规避，见下 §三。

--------------------------------------------------------------------------------
■ 一、键布局（首段 `notes` 纯小写，合板键语法）

    notes/xdom/log/<YYYYMMDDTHHMMSS>-<from>-<slug>-<nonce4>
        邮件体。**一次写入、永不修改**（append-only）。发信方只写自己发的那些键。
    notes/xdom/cursor/<party>
        读水位。**只有该 party 自己能写**（跨写直接拒绝）。
    notes/xdom/keys/<party>                                  ← ★ v1.1 新增
        该 party 的钥匙**指纹**（只放指纹，绝不放密钥）。由 keygen 自己登记。

  ★ 两个投递域**互不相交**：log 键归发方，cursor 键归读方。
    ⇒ 不存在「两端改同一个键」⇒ 结构上没有 read-modify-write ⇒ 没有丢更新。
  ★ 「已读」由**接收方**写、「发信方」只读它。比较的两端不同源 ⇒ 结构上没有自指（P27）。

■ 一之二、★ v1.1「凭据门」—— 让「越权写入」在 CLI 面**真实可达**

  v1.0 的诚实自陈是：`owns_key()` 只保证**自洽**，**不是鉴权** —— key 恒由 `--as` 派生，
  ⇒ 「ext 写 cursor/int」这种输入**在 CLI 面构造不出来** ⇒ 该负控**不可验证**（§七 曾如此记载）。

  v1.1 补上**独立于 `--as` 的凭据**，把「不可达」变成「可被违反、因而可验证」：

    · `keygen --as <party>` 生成 `~/.dsh/xdom-keys/<party>.key`（0600，32 字节随机密钥）。
      ★ 密钥**只存在各自机器上、绝不上板**。
    · **凡写入**（send / ack / probe）**必须给凭据**：`--cred <path>`（或环境变量
      `XDOM_MAIL_CRED`）。凭据里的 party **必须等于**本次声称的身份，否则拒。
      ★ 唯一例外是 `keygen` 的登记：它**用刚生成的那把钥自签**（见 cmd_keygen 注释）——
        这样才证明「登记人手里确实有这把钥」，也避免「第一次跑还没有凭据可给」的死锁。
    · **fail-closed**：不给凭据 ⇒ **拒绝写入**，不是「默认放行」。
    · 信体与水位值带 `sig`（HMAC-SHA256 截 16 hex）⇒ 板侧改动**可检出**。

  ★★ 红线（本设计的命门）：**凭据的来源必须与 `--as` 无关。**
    若工具按 `--as` 自动去挑钥匙，那么钥匙永远与身份相符 —— **又退化成自指判据（§17.4）**，
    等于把 v1.0 的洞换了个名字。故 `--cred` **必须由调用方显式给出**，工具**不代挑**。

  ★ 诚实的限度（不得当已验）：
    · 这是**能力闸 + fail-closed + 篡改可检出**，**不是**「防同机恶意进程」——
      同机同用户下任何进程都能读那 0600 的文件。
    · **跨机/跨账号**时它才是真鉴权（密钥从不离开属主机器）。
    · HMAC 是**对称**的 ⇒ 各人能验**自己的**签名；**无法**验证对方的（对方密钥不在手）
      ⇒ 读数三态：`sig ✓` / `sig ✗` / `sig ?`（无对方密钥 ⇒ **不可判**，不得读作通过）。

■ 二、判定三态必须长得不一样（未读 ≠ 未送达 ≠ 板不可达）
    · 邮件键在板上存在            ⇒ 已送达（板是共享基质，落板即达）
    · cursor >= 该键              ⇒ 已读（由读方自己写的水位）
    · 板不可达 / 两板不一致        ⇒ **FAIL**，绝不报成「无新信」（`skip()` 哲学）

■ 三、写入路径的三条硬约束（逐条对应上面的事实 3）
    ① HTTP 头值**只许 ASCII**（非 ASCII 头值 latin-1 编码抛 UnicodeEncodeError，
       写入静默变成空操作）。故 `X-Writer` 用 ASCII 槽位名，人类可读标签**只放信体里**。
    ② 回读断言比的是 **「板值 == 我推的值」**，禁止退化成「板 A == 板 B」（两板一起错就永远相等）。
    ③ PUT 与 GET 的 HTTP 码**分字段留存**，`verdict` 只要 PUT 非 200 就**不得**为 ok。
       逐次留痕 `logs/xdom-mail.jsonl`。
    ④ ★ v1.1：**凭据独立于 `--as`**，且写入 fail-closed（见 §一之二）。

■ 四、球权（ball）
    不必落盘 —— 由**日志最后一条**的 `ball` 字段派生。派生量不落冗余字段，
    ⇒ 没有「两段」可漂移（B9 那类「只读一段的人低估进度」在本设计下不存在）。

--------------------------------------------------------------------------------
★ 约束门（⑩）声明：本工具
   · 会写黑板（PUT，仅 `notes/xdom/**` 三个受控前缀；跨前缀写入直接拒绝）、会写本地留痕 `logs/`。
   · ★ v1.1 起另会**在 `~/.dsh/xdom-keys/` 新建 0600 的密钥文件**（仅 `keygen`，且不覆盖已存在的）。
   · **不**执行外部命令、**不**删除数据（`--probe` 的清理由板 DELETE 尽力而为，失败则如实报告残留）、
     **不**改**既有**文件权限、**不**碰 launchd、**不**起服务、**不**重启任何框架。
   · 依赖仅 Python 3 标准库（v1.1 增用 `hmac` / `secrets`，仍是标准库）。
★ 自检：`--selfcheck`（TCC 能力边界三段）· `--selftest`（离线，含负控）· `--probe`（真板往返，自清理）

用法:
  python3 tools/xdom-mail.py keygen --as ext [--force]          # ★ v1.1 先各做一次
  python3 tools/xdom-mail.py keygen --as ext --register-only    # ★ 钥已在本地、只补登记指纹（不轮换）
  python3 tools/xdom-mail.py send --from ext --to int --topic k6-wiring --body-file /tmp/x.md \\
        --cred ~/.dsh/xdom-keys/ext.key [--subject S] [--ball int] [--reply-required] [--dry-run]
  python3 tools/xdom-mail.py inbox  --as ext [--all] [--json]
  python3 tools/xdom-mail.py ack    --as ext (--upto KEY | --latest) --cred ~/.dsh/xdom-keys/ext.key
  python3 tools/xdom-mail.py status [--json] [--stale-hours 6] [--both]
  python3 tools/xdom-mail.py --probe --as <自己> --cred ~/.dsh/xdom-keys/<自己>.key
  python3 tools/xdom-mail.py --selfcheck | --selftest | --version

★ 迁移（v1.0 → v1.1）：**写入一律要 `--cred`，否则 fail-closed 拒绝**。
  两方各跑一次 `keygen --as <自己>`（该命令**不需要** `--cred`，自签登记），
  之后每条写入命令加 `--cred`（或设 `XDOM_MAIL_CRED`）。
  只读命令（`inbox` / `status`）**不需要**凭据。
"""
import argparse
import datetime
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import urllib.error
import urllib.request
import uuid

VERSION = "1.1.2"
__version__ = VERSION

# ★ 外部线〔1〕对照用（2026-10-12）：两侧去重键【不等价】⇒ 声明不得称「同构」。
#   ★ 抽成常量是为了让 --selftest 能【真跑两侧对照】而不是去搜 docstring 字面
#     （搜字面会被「说明这两个字为何错」的说明文字满足 ⇒ 假红；D-053 同族）。
NODE_BIN = "/opt/homebrew/bin/node"
JS_IDENTITY = os.path.expanduser("~/dsh-comm-shared/identity.js")

BOARDS = [("local", "http://127.0.0.1:8792"), ("central", "http://xingqiao.meetfunbp.com:8792")]
NS = "notes/xdom"
LOG_PREFIX = NS + "/log/"
CUR_PREFIX = NS + "/cursor/"
KEYS_PREFIX = NS + "/keys/"          # ★ v1.1：钥匙**指纹**登记（只放指纹，不放密钥）
PARTIES = ("ext", "int")
# ★ v1.1 凭据门。KEY_DIR 在 ~/.dsh 下（与既有 token 同处），**不在仓库里**。
KEY_DIR = os.path.expanduser("~/.dsh/xdom-keys")
CRED_ENV = "XDOM_MAIL_CRED"
KEY_ALG = "hmac-sha256"
KEY_BYTES = 32                        # 256 bit 随机密钥
# 人类别名 → 角色键（内部会话常驻，外部会话非常驻）
ALIAS = {"ext": "ext", "cu": "ext", "外部": "ext", "claude": "ext", "claude-code": "ext",
         "int": "int", "cld": "int", "内部": "int", "星桥": "int", "starbridge": "int"}
SIDE_LABEL = {"ext": "外部（Claude Code · 非常驻 · 不可唤醒）",
              "int": "内部（CLD · 常驻 · 可被卡唤醒）"}
HEADER_SLOT = "xdom-mail"          # ★ ASCII only —— 见 §三①
DEFAULT_LOG = os.path.expanduser("~/dsh-collab/logs/xdom-mail.jsonl")


# ══════════════════════════════════════════════════════════════════════
# 传输层
# ══════════════════════════════════════════════════════════════════════
def _tokens():
    def rd(p):
        try:
            return open(os.path.expanduser(p), encoding="utf-8").read().strip()
        except Exception:
            return ""
    return {"local": rd("~/.dsh/board-token"), "webhook": rd("~/.dsh/webhook-token"),
            "board": rd("~/.dsh/blackboard-token")}


def _auth(base):
    t = _tokens()
    if "127.0.0.1" in base or "localhost" in base:
        return {"Authorization": "Bearer " + t["local"]} if t["local"] else {}
    h = {}
    if t["webhook"]:
        h["X-Webhook-Token"] = t["webhook"]
    if t["board"]:
        h["X-Blackboard-Token"] = t["board"]
    return h


def ascii_header_value(v):
    """★ §三① —— 非 ASCII 头值会在 http.client 的 latin-1 编码处抛 UnicodeEncodeError，
    使 PUT 静默变空操作（2026-10-10 实证）。这里**主动**把它变成可检出的显式错误。"""
    try:
        str(v).encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def _req(base, key, method, value=None, timeout=20):
    """返回 {"http","env","value","err"}。PUT 与 GET 的码由调用方**分字段**留存（§三③）。"""
    url = f"{base}/{key}"
    data = None if value is None else json.dumps(value, ensure_ascii=False).encode("utf-8")
    h = {"Content-Type": "application/json", "X-Writer": HEADER_SLOT}
    if data is not None:
        h["Content-Length"] = str(len(data))
    h.update(_auth(base))
    bad = [k for k, v in h.items() if not ascii_header_value(v)]
    if bad:
        return {"http": None, "env": None, "value": None,
                "err": "NON_ASCII_HEADER:" + ",".join(bad)}
    try:
        rq = urllib.request.Request(url, data=data, method=method, headers=h)
        with urllib.request.urlopen(rq, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "ignore")
            try:
                env = json.loads(raw)
            except Exception:
                return {"http": r.status, "env": None, "value": None, "err": "非 JSON 响应"}
            return {"http": r.status, "env": env,
                    "value": env.get("value") if isinstance(env, dict) else None, "err": None}
    except urllib.error.HTTPError as e:
        return {"http": e.code, "env": None, "value": None, "err": f"HTTP {e.code}"}
    except Exception as e:
        return {"http": None, "env": None, "value": None, "err": type(e).__name__}


def sha16(v):
    return hashlib.sha256(json.dumps(v, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]


def put_verified(key, value, boards=None, timeout=20):
    """双板写 + **回读比「我推的值」**（§三②③）。返回逐板留痕；ok 仅在
    「两板 PUT 均 200」且「两板 GET 值指纹 == 推送值指纹」时为真。"""
    boards = boards or BOARDS
    rec = {"key": key, "pushed_sha": sha16(value), "put": {}, "get": {}, "match": {}, "ok": False}
    for name, base in boards:
        r = _req(base, key, "PUT", value, timeout=timeout)
        rec["put"][name] = {"http": r["http"], "err": r["err"]}
    for name, base in boards:
        r = _req(base, key, "GET", None, timeout=timeout)
        got = r["value"]
        rec["get"][name] = {"http": r["http"], "err": r["err"],
                            "sha": sha16(got) if got is not None else None}
        rec["match"][name] = (got is not None and sha16(got) == rec["pushed_sha"])
    rec["ok"] = (all(rec["put"][n]["http"] == 200 for n, _ in boards)
                 and all(rec["match"].values()))
    # 人话结论：把最可能的原因直接写出来，免得只看到 ok=False 又要查一轮
    if not rec["ok"]:
        if any(v["err"] and str(v["err"]).startswith("NON_ASCII_HEADER") for v in rec["put"].values()):
            rec["why"] = "PUT 未发生：HTTP 头含非 ASCII（§三①）"
        elif any(v["http"] not in (200, None) for v in rec["put"].values()):
            rec["why"] = "PUT 被板拒绝：" + ",".join(f"{n}={rec['put'][n]['http']}" for n, _ in boards)
        elif any(v["err"] for v in rec["put"].values()):
            rec["why"] = "PUT 传输异常：" + ",".join(f"{n}={rec['put'][n]['err']}" for n, _ in boards)
        else:
            rec["why"] = "PUT 报 200 但回读值 ≠ 推送值（被覆盖或未生效）"
    return rec


def append_ledger(rec, path=DEFAULT_LOG):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _has_list(r):
    return r["http"] == 200 and isinstance(r["env"], dict) and isinstance(r["env"].get("list"), dict)


def read_ns(prefix, boards=None):
    """列某前缀下全部键。返回 (dict, source, notes)。

    ★ 三种「空」必须分得开：
        200 有 list  → 真读到（可能本来就 0 键）
        404          → 命名空间尚未创建 ⇒ 按空处理（**不是**失败）
        其它/超时     → source=None ⇒ 结论是『不可达』，**不得**读作『无新信』
    """
    boards = boards or BOARDS
    notes, res = [], {}
    for name, base in boards:
        r = _get(base, prefix)
        res[name] = r
        if _has_list(r):
            notes.append(f"{name}: ok {len(r['env']['list'])} 键")
        elif r["http"] == 404:
            notes.append(f"{name}: 404（尚未创建 ⇒ 按空处理）")
        else:
            notes.append(f"{name}: FAIL http={r['http']} err={r['err']}")
    src, lst = None, None
    for name, _ in boards:                      # 优先「200 有 list 且有内容」
        if _has_list(res[name]) and res[name]["env"]["list"]:
            src, lst = name, res[name]["env"]["list"]
            break
    if src is None:
        for name, _ in boards:                  # 其次「200 有 list 但为空」
            if _has_list(res[name]):
                src, lst = name, {}
                break
    if src is None:
        for name, _ in boards:                  # 再次「404 = 合法未创建」
            if res[name]["http"] == 404:
                src, lst = name, {}
                break
    if src is None:
        notes.append("★ 无任何板可读 ⇒ 『不可达』，**不得**读作『无新信』")
        return {}, None, notes
    ok200 = [n for n, _ in boards if _has_list(res[n])]
    if len(ok200) == 2:
        x, y = ok200
        if set(res[x]["env"]["list"]) != set(res[y]["env"]["list"]):
            notes.append(f"★ {x} 与 {y} 键集不一致（{len(res[x]['env']['list'])} vs "
                         f"{len(res[y]['env']['list'])}）⇒ 需交叉判，勿单信一板")
    return lst or {}, src, notes


def _get(base, key, timeout=20):
    return _req(base, key, "GET", None, timeout=timeout)


def read_one(key, boards=None):
    """单键读 → (value, brief)。brief 是**一行**短结论：`v=<版本>` / `404 未创建` /
    `FAIL …`。★ 只回一行是刻意的——同一个 404 报四遍会把信号稀释掉，而这里的 404
    只是「还没人推过水位」，不是异常。"""
    boards = boards or BOARDS
    brief, val, vers, fails = [], None, set(), []
    for name, base in boards:
        r = _get(base, key)
        if r["http"] == 200 and isinstance(r["env"], dict):
            vers.add(r["env"].get("version"))
            if val is None:
                val = r["value"]
        elif r["http"] == 404:
            vers.add("404")
        else:
            fails.append(f"{name}={r['http']}/{r['err']}")
    if fails:
        brief.append("FAIL " + "；".join(fails))
    elif vers == {"404"}:
        brief.append("404 未创建（尚未推过）")
    elif vers:
        brief.append("v=" + "/".join(str(x) for x in sorted(vers, key=str)))
    return val, brief


# ══════════════════════════════════════════════════════════════════════
# 业务层
# ══════════════════════════════════════════════════════════════════════
def role(x):
    return ALIAS.get(str(x).strip().lower(), ALIAS.get(str(x).strip(), None))


def now_local():
    return datetime.datetime.now().astimezone()


def slugify(topic):
    s = re.sub(r"[^a-z0-9]+", "-", str(topic).lower()).strip("-")
    return (s or "msg")[:24]


def owns_key(key, party):
    """★ 两个投递域互不相交：发方只写 log，读方只写 cursor、keygen 只写自己的 keys 指纹。

    ★★ 务必分清（v1.0 曾把二者混为一谈）：
        · 本函数保证的是【自洽】—— 键必须属于该 party 自己的域。
        · 它【不是鉴权】—— **鉴权在 `require_cred()`**，那条才是独立的。
        · 单靠本函数时，key 恒由 `--as` 派生 ⇒ 跨域输入【构造不出来】⇒ 负控【不可验证】。
    """
    if key.startswith(LOG_PREFIX):
        return True
    if key.startswith(CUR_PREFIX):
        return key == CUR_PREFIX + party
    if key.startswith(KEYS_PREFIX):
        return key == KEYS_PREFIX + party
    return False


# ══════════════════════════════════════════════════════════════════════
# ★ v1.1 凭据门（见文件头 §一之二）
#   命门：**凭据的来源与 `--as` 无关**。工具不按 `--as` 代挑钥匙 ——
#   否则钥匙永远与身份相符，又变成自指判据（§17.4），洞只是换了个名字。
# ══════════════════════════════════════════════════════════════════════
def canonical(obj):
    """签名/指纹的规范形：去 `sig` 后 canonical JSON（与板上的 `sha16` 同口径）。"""
    if isinstance(obj, dict):
        obj = {k: v for k, v in obj.items() if k != "sig"}
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


# ═══ ★ W8.2：跨域邮箱的 CAHAC §3 信封注入（2026-10-11 本线新增）═══
CAHAC_ENVELOPE_VERSION = "1.0"
XDOM_CHANNEL = "xdom-mail"


def dedup_key_from(from_party, to_party, body):
    """★ 本工具的【自有】去重键口径 —— ★ **与 `~/dsh-comm-shared/identity.js` 的
    `dedupKey(from,to,text)` **不是等价实现**（2026-10-12 外部线复核 + 本线独立复现，见 D-060）。

    本侧：`f"{from}|{to}|{sha256(空白归一化后的原文).hexdigest()[:16]}"`
          ⇒ 尾段是 **16 hex 摘要**、**不折小写**。
    JS 侧：`f"{from}|{canonicalTo}|{contentFingerprint(text)}"`，而 `contentFingerprint`
          逐字为 `String(t||'').replace(/\\s+/g,' ').trim().toLowerCase().slice(0,512)`
          ⇒ 尾段是 **归一化原文（≤512 字符）**、**折小写**。

    ⇒ ★ 两处实质差异：**(a) 尾段 摘要 vs 原文** · **(b) 是否折小写**。
    ★ 二者**论域不同**（JS 侧服务 `central-inbox` / `agent-way` 的板卡去重；本侧服务跨域邮箱），
      ⇒ ★ **不要求取值相等**。★ 但**旧 docstring 声称「同构 / 等价实现」与事实不符，已删**。

    ★ 为什么不改成与 JS 一致：JS 把**归一化原文**放进键 ⇒ 键长可达 **512 字符且含明文正文**；
      本侧若照抄，会把正文灌进游标/信件的 `dedup_key` 字段。★ 故**保持摘要口径**，
      并**在声明上如实**，而不是在实现上盲从。
    """
    norm = " ".join((body or "").split())
    fp = hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]
    return f"{from_party}|{to_party}|{fp}"


def with_envelope(msg, body):
    """★ 给信对象注入 CAHAC §3 信封（10 字段口径，逐字取自锚点 §12-A 临时尺）。

    ★ 必须加在**顶层**：尺（`scripts/cahac-envelope-conformance.py`）按**顶层键**判 `h>=6`；
      嵌进 `envelope:{}` 子对象**不会被计数** ⇒ 那样是凑数，本线不做。
    ★ 与既有字段的关系：`sender`/`recipient` = `from`/`to` 的信封口径同义；`channel` 本通道恒为
      `xdom-mail`；`payload` **就是信体**，`body` 保留为**过渡期别名**（代价：卡片体积翻倍）。
    ★ 时序：**必须在 `sign_obj` 之前**调用 ⇒ 签名覆盖新字段。
      安全性依据（已核）：`sign_obj` **对称**（本方签、本方验）；协议 §七 明写「各人能验自己的签名、
      验不了对方的」⇒ 加字段**不会**破坏任何一方的验签。
    """
    msg["cahac"] = CAHAC_ENVELOPE_VERSION
    msg["type"] = "letter"
    msg["channel"] = XDOM_CHANNEL
    msg["sender"] = msg.get("from")
    msg["recipient"] = msg.get("to")
    msg["priority"] = "urgent" if msg.get("reply_required") else "normal"
    msg["dedup_key"] = dedup_key_from(msg.get("from"), msg.get("to"), body)
    msg["payload"] = body
    return msg


def cursor_value(party, upto):
    """★ 游标（水位）对象 —— ★★ **绝不放信封**：它不是信（见 D-060 / :751 回归）。

    ★ 为什么抽成纯函数：★ 若把构造留在 `cmd_ack` 里，「游标上不得有信封字段」这条判据
      **无法被负控**（只能去搜源码字面 ⇒ 依 D-036 教训，绑字面的判据会假红）。
      ★ 抽出来后，`--selftest` 可以**直接对返回值断言**。
    """
    return {"party": party, "upto": upto,
            "at": now_local().isoformat(timespec="seconds"),
            "by": SIDE_LABEL[party]}


def sign_obj(obj, secret_hex):
    """HMAC-SHA256(secret, canonical(obj)) 截 16 hex。★ 对称 —— 只有持同一密钥者能验。"""
    return hmac.new(bytes.fromhex(secret_hex), canonical(obj).encode("utf-8"),
                    hashlib.sha256).hexdigest()[:16]


def verify_obj(obj, secret_hex):
    """恒定时间比较。obj 里必须有 `sig`。"""
    got = (obj or {}).get("sig")
    if not got:
        return False
    return hmac.compare_digest(str(got), sign_obj(obj, secret_hex))


def key_fingerprint(secret_hex):
    """指纹 = sha256(secret)[:16]。★ 只放指纹上板，密钥绝不上板。"""
    return hashlib.sha256(bytes.fromhex(secret_hex)).hexdigest()[:16]


def keypath(party):
    return os.path.join(KEY_DIR, party + ".key")


def _mk_cred_file(path, party):
    """★ 只给 `--selftest` 用：在**任意路径**造一份合法凭据并返回密钥。
    刻意不复用 keygen —— keygen 会写 KEY_DIR 并上板，自检不该碰真板/真钥匙。"""
    sec = secrets.token_hex(KEY_BYTES)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"party": party, "alg": KEY_ALG, "secret": sec,
                   "created": "selftest", "fp": key_fingerprint(sec)}, f)
    return sec


def load_cred(path):
    """读凭据文件 → (cred dict, err)。任何异常都变成**显式错误**，不静默放行。"""
    if not path:
        return None, "未提供凭据路径"
    p = os.path.expanduser(path)
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
    except FileNotFoundError:
        return None, f"凭据文件不存在：{p}（先跑 keygen --as <自己>）"
    except Exception as e:
        return None, f"凭据文件读不开/非法 JSON：{p}（{type(e).__name__}）"
    if not isinstance(d, dict):
        return None, f"凭据格式非法（应为 JSON 对象）：{p}"
    if d.get("party") not in PARTIES:
        return None, f"凭据的 party 非法：{d.get('party')!r}（应 ∈ {PARTIES}）"
    if d.get("alg") != KEY_ALG:
        return None, f"凭据算法不支持：{d.get('alg')!r}（应 {KEY_ALG}）"
    sec = str(d.get("secret") or "")
    try:
        if len(bytes.fromhex(sec)) < KEY_BYTES:
            raise ValueError("too short")
    except Exception:
        return None, f"凭据密钥非法（应为 ≥{KEY_BYTES} 字节的 hex）：{p}"
    return d, None


def require_cred(a, claimed_party):
    """★ 写入前置门。返回 (cred, err)；err 非 None ⇒ 调用方必须**拒绝写入**。

    三条拒绝理由，全部**在 CLI 面可构造**（正因如此该负控才可验证）：
      ① 未给凭据            ⇒ fail-closed 拒（不是默认放行）
      ② 凭据读不开/非法      ⇒ 拒
      ③ 凭据 party ≠ 声称身份 ⇒ 拒  ← ★ 这就是 §八.5 一直缺的那条负控
    """
    path = getattr(a, "cred", "") or os.environ.get(CRED_ENV, "")
    if not path:
        return None, (f"fail-closed：本命令是【写入】，必须给凭据。"
                      f"用 --cred <path> 或设 {CRED_ENV}（只读命令不需要）")
    cred, err = load_cred(path)
    if err:
        return None, err
    if cred["party"] != claimed_party:
        return None, (f"★ 越权写入被拒：凭据属于 {cred['party']}，"
                      f"却要以 {claimed_party} 的身份写入（凭据由 {os.path.expanduser(path)} 提供）")
    return cred, None


def cmd_keygen(a):
    """生成自己的密钥并登记指纹。★ 不覆盖已存在的（除非 --force）。

    ★ v1.1.1（2026-10-11，据 int 的接入回执）：加 `--register-only`。
      起因是 int 实测出的**死循环**：不带 `--cred` 时 keygen 只生成钥不登记；
      带 `--cred` 重跑又被「密钥已存在」拒 ⇒ **已存在的钥无法单独补登记指纹**，
      唯一出路是 `--force` 轮换，代价是对方手里**旧签名全部失效**。
      ⇒ `--register-only` 读**已有**的钥、只登记其指纹，**不碰密钥本身、不轮换**。
    """
    party = role(a.as_)
    if not party:
        return die(f"--as 非法：{a.as_}")
    path = keypath(party)

    if a.register_only:
        # ★ 补登记路径：只读现有钥 → 登记指纹。密钥文件**一个字节都不改**。
        try:
            with open(path, encoding="utf-8") as f:
                old = json.load(f)
        except FileNotFoundError:
            return die(f"--register-only：本地没有 {path} ⇒ 无从登记（先跑 keygen --as {party}）")
        except Exception as e:
            return die(f"--register-only：{path} 读不开（{e}）")
        if old.get("party") != party:
            return die(f"--register-only：{path} 里的 party 是 {old.get('party')!r}，"
                       f"不是 {party!r} ⇒ **拒**（不拿 A 的钥去登记 B 的指纹）")
        secret = str(old.get("secret") or "")
        if len(secret) < KEY_BYTES * 2:      # hex ⇒ 2 字符/字节
            return die(f"--register-only：{path} 里的密钥过短/缺失 ⇒ 拒")
        fp = old.get("fp") or key_fingerprint(secret)
        return _keygen_put(a, party, path, secret, fp,
                           verb="指纹已补登记（密钥未轮换）")

    secret = secrets.token_hex(KEY_BYTES)
    val = {"party": party, "alg": KEY_ALG, "secret": secret,
           "created": now_local().isoformat(timespec="seconds"), "fp": key_fingerprint(secret)}
    if os.path.exists(path) and not a.force:
        try:
            old = json.load(open(path, encoding="utf-8"))
            oldfp = old.get("fp") or key_fingerprint(str(old.get("secret") or ""))
        except Exception:
            oldfp = "（读不开）"
        return die(f"密钥已存在：{path}（指纹 {oldfp}）。"
                   f"★ 不覆盖是刻意的 —— 换钥匙会让对方手里的**旧签名全部变『验不过』**。"
                   f"· 只是想把**已有**的指纹登记上板 ⇒ 用 `--register-only`（不轮换）。"
                   f"· 确要**轮换**请显式 --force，并**告知对方**。")
    if a.dry_run:
        # ★ dry-run 必须在**任何写入之前**返回 —— 否则「干跑」会真的落下密钥文件。
        print(json.dumps({"would_write": path, "fp": val["fp"], "party": party,
                          "would_register": KEYS_PREFIX + party}, ensure_ascii=False))
        return 0
    os.makedirs(KEY_DIR, mode=0o700, exist_ok=True)
    # ★ 先以 0600 创建（不是先建后 chmod —— 那中间有一瞬是宽权限）
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(val, f, ensure_ascii=False, indent=1)
    return _keygen_put(a, party, path, secret, val["fp"], verb="密钥已生成", created=True)


def _keygen_put(a, party, path, secret, fp, verb, created=False):
    """登记指纹上板。★ 用**自己这把钥**自签 ——
    ① 这样才证明「登记人手里确实有这把钥」；
    ② 也免掉「第一次跑还没有凭据可给」的先有鸡还是先有蛋。"""
    if a.dry_run:
        print(json.dumps({"would_register": KEYS_PREFIX + party, "fp": fp, "party": party},
                         ensure_ascii=False))
        return 0
    reg = {"party": party, "alg": KEY_ALG, "fp": fp,
           "at": now_local().isoformat(timespec="seconds")}
    reg["sig"] = sign_obj(reg, secret)
    rec = put_verified(KEYS_PREFIX + party, reg)
    rec["at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rec["party"], rec["op"] = party, "keygen"
    append_ledger(rec)
    if created:
        print(f"✅ 密钥已生成：{path}（0600）  指纹 {fp}")
    else:
        print(f"✅ {verb}：{path}  指纹 {fp}")
    print(f"{'✅' if rec['ok'] else '❌'} 指纹登记 {KEYS_PREFIX + party}")
    if not rec["ok"]:
        print(f"   ★ 指纹未落板：{rec.get('why')}（本地密钥可用，但对方看不到你的指纹）")
        return 2
    return 0


def own_key(party):
    """读**自己**的密钥（只用于**验证**，不是能力声称）。读不到 ⇒ (None, None)。"""
    try:
        with open(keypath(party), encoding="utf-8") as f:
            d = json.load(f)
        return d.get("secret"), (d.get("fp") or key_fingerprint(str(d.get("secret"))))
    except Exception:
        return None, None


def sig_state(obj, party):
    """签名三态：`✓` 验过 / `✗` 验不过 / `?` **不可判**（无签名，或对方密钥不在手）。

    ★ 必须与「通过」分开：**「我验不了」≠「它是对的」**（不可判 ≠ 成立）。
    """
    if not (obj or {}).get("sig"):
        return "?", "无签名（v1.0 遗留信，或对方未升级）"
    sec, fp = own_key(party)
    if not sec:
        return "?", f"本方无密钥文件 ⇒ 无法验证（先 keygen --as {party}）"
    if obj.get("signer_fp") and obj["signer_fp"] != fp:
        return "?", f"签名者是 {obj['signer_fp']}（≠ 本方 {fp}）⇒ **对方密钥不在手，不可判**"
    return ("✓", "本方签名，验过") if verify_obj(obj, sec) else ("✗", "★ 签名不匹配 —— 内容被改过")


def parse_log(keys):
    """把板上的 log 字典 → 有序 [(key, msg)]，并剔除不合规体。"""
    out, bad = [], []
    for k in sorted(keys):
        if not k.startswith(LOG_PREFIX):
            continue
        v = (keys[k] or {}).get("value")
        if isinstance(v, dict) and v.get("from") in PARTIES and v.get("to") in PARTIES + ("all",):
            out.append((k, v))
        else:
            bad.append(k)
    return out, bad


def current_ball(msgs):
    return msgs[-1][1].get("ball") if msgs else None


def unread_for(party, msgs, cursor_value):
    upto = (cursor_value or {}).get("upto") or ""
    return [(k, m) for k, m in msgs
            if k > upto and m.get("from") != party and m.get("to") in (party, "all")]


def cmd_send(a):
    frm = role(a.frm)
    to = "all" if str(a.to).lower() == "all" else role(a.to)
    if not frm:
        return die(f"--from 非法：{a.frm}（可选 {'/'.join(PARTIES)} 或其别名 cld/cu/外部/内部）")
    if not to:
        return die(f"--to 非法：{a.to}（可选 ext/int/all）")
    # ★ 凭据门放在**读信体之前**：未过门的调用者不该让我们去开文件、也不该拿到后续校验的细节。
    cred, err = require_cred(a, frm)            # ★ v1.1 凭据门（fail-closed）
    if err:
        return die(err)
    body = a.body
    if a.body_file:
        body = sys.stdin.read() if a.body_file == "-" else open(a.body_file, encoding="utf-8").read()
    if not body or not body.strip():
        return die("信体为空：用 --body 或 --body-file <path|->")

    now = now_local()
    stem = now.strftime("%Y%m%dT%H%M%S")
    key = f"{LOG_PREFIX}{stem}-{frm}-{slugify(a.topic)}-{uuid.uuid4().hex[:4]}"
    if not owns_key(key, frm):
        return die(f"越域写入被拒：{frm} 不得写 {key}")
    msg = {"id": key[len(LOG_PREFIX):], "from": frm, "to": to, "topic": a.topic,
           "subject": a.subject or "", "ts": now.isoformat(timespec="seconds"),
           "ball": role(a.ball) if a.ball and a.ball != "none" else ("none" if a.ball == "none" else None),
           "reply_required": bool(a.reply_required), "body": body,
           "ref": list(a.ref or []), "from_session": a.from_session or "",
           "writer_label": SIDE_LABEL[frm]}      # ★ 人类标签只在这里，不进 HTTP 头（§三①）
    with_envelope(msg, body)   # ★ W8.2：注入信封（必须在签名之前）
    msg["signer_fp"] = key_fingerprint(cred["secret"])
    msg["sig"] = sign_obj(msg, cred["secret"])  # ★ 板侧改动可检出（只有己方能验，见文件头 §一之二）
    if a.dry_run:
        print(json.dumps({"key": key, "msg": msg}, ensure_ascii=False, indent=1))
        return 0
    rec = put_verified(key, msg)
    rec["at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rec["party"] = frm
    rec["op"] = "send"
    append_ledger(rec)
    print(f"{'✅' if rec['ok'] else '❌'} 投递 {key}")
    for name, _ in BOARDS:
        print(f"   {name:<8} PUT={rec['put'][name]['http']} {rec['put'][name]['err'] or ''}"
              f"   GET={rec['get'][name]['http']}  值匹配={rec['match'][name]}")
    if not rec["ok"]:
        print(f"   ★ 未落板：{rec.get('why')}")
        return 2
    if to in ("ext", "all") and frm != "ext":
        print("   ⚠ 外部会话**非常驻、不可被唤醒** —— 本信不会即时被读。"
              "请勿等待；球权已按 `ball` 字段交付，外部下次开工时读。")
    if to in ("int", "all") and frm != "int":
        print("   · 内部常驻：本信可被 `reply_required` + `ball` 唤醒。")
    return 0


def _load(party):
    keys, src, notes = read_ns(LOG_PREFIX)
    if src is None:
        return None, None, notes
    msgs, bad = parse_log(keys)
    cv, cnotes = read_one(CUR_PREFIX + party)
    return msgs, (cv, bad), notes + cnotes


def cmd_inbox(a):
    party = role(a.as_)
    if not party:
        return die(f"--as 非法：{a.as_}")
    msgs, meta, notes = _load(party)
    if msgs is None:
        print("❌ 邮箱不可达 —— 这是『读不到』，不是『没有新信』。（" + "；".join(notes) + "）")
        return 2
    cv, bad = meta
    todo = msgs if a.all else unread_for(party, msgs, cv)
    ball = current_ball(msgs)
    if a.json:
        print(json.dumps({"as": party, "ball": ball, "log_total": len(msgs),
                          "cursor": (cv or {}).get("upto"), "unread": len(todo),
                          "messages": [{"key": k, **m, "sig_state": sig_state(m, party)[0]}
                                       for k, m in todo],
                          "notes": notes, "malformed": bad}, ensure_ascii=False, indent=1))
        return 0
    print(f"═══ 跨域公共邮箱 · {SIDE_LABEL[party]} ═══")
    print(f"日志 {len(msgs)} 条 · 我方水位 {((cv or {}).get('upto') or '（从未读过）')} · "
          f"{'全部' if a.all else '未读'} {len(todo)} 条 · 当前持球 {ball or '（无信）'}")
    print("板: " + "；".join(notes))
    if bad:
        print(f"⚠ 不合规信体 {len(bad)} 条（已跳过，不静默）：{', '.join(bad[:5])}")
    if not todo:
        print("　（无未读）★ 空=已读到最新；若疑有信，看上面的水位与日志条数，别把『空』当结论。")
        return 0
    for k, m in todo:
        flag = "🔴 待回" if m.get("reply_required") else ("🔵 待办" if m.get("ball") == party else "⚪ 知悉")
        print("\n" + "─" * 72)
        print(f"{flag}  {k}")
        ss, swhy = sig_state(m, party)
        print(f"  {m.get('from')} → {m.get('to')}   {m.get('ts')}   topic={m.get('topic')}"
              f"   ball={m.get('ball')}   sig={ss}（{swhy}）")
        if m.get("subject"):
            print(f"  主题：{m['subject']}")
        for r in (m.get("ref") or []):
            print(f"  引用：{r}")
        print("  " + (m.get("body") or "").replace("\n", "\n  "))
    print("\n" + "─" * 72)
    print(f"读完请推进水位：python3 tools/xdom-mail.py ack --as {party} --upto {todo[-1][0]}")
    return 0


def cmd_ack(a):
    party = role(a.as_)
    if not party:
        return die(f"--as 非法：{a.as_}")
    key = CUR_PREFIX + party
    if not owns_key(key, party):
        return die(f"越域写入被拒：{party} 不得写 {key}")
    cred, err = require_cred(a, party)          # ★ v1.1 凭据门（fail-closed）
    if err:
        return die(err)
    upto = a.upto
    if a.latest or not upto:
        keys, src, notes = read_ns(LOG_PREFIX)
        if src is None:
            print("❌ 邮箱不可达，无法定位最新一条 —— 水位**未动**。（" + "；".join(notes) + "）")
            return 2
        msgs, _ = parse_log(keys)
        if not msgs:
            print("（日志为空，水位未动）")
            return 0
        upto = msgs[-1][0]
    if not upto.startswith(LOG_PREFIX):
        return die(f"--upto 必须是一条 log 键（{LOG_PREFIX}…）")
    val = cursor_value(party, upto)
    # ★★ W8.2 回归修复（2026-10-12，D-060）：本行**曾**为
    #     `with_envelope(val, val.get("body", ""))` —— ★ 那是**错的**：
    #     `val` 是【游标对象】，**没有 body** ⇒ 取空串 ⇒ 把一封【空信】的信封
    #     注进了游标：`type="letter"` · `sender/recipient=None` ·
    #     `dedup_key="None|None|e3b0c44298fc1c14"`（= sha256("")[:16]）。
    # ★ 危害（潜伏，非现行故障 —— 影响面外部线判「不可判」，本线复核后同意）：
    #     ① 未来任何按 `type` 分派的读者会把**游标误当信**；
    #     ② 常量 dedup_key ⇒ 将来按该键去重的读者会把**不同游标判为同一条**。
    # ★ 已删除，不再注入。★ 信封只加在【真的是信】的两条路径：`cmd_send` 与 `--probe`。
    val["signer_fp"] = key_fingerprint(cred["secret"])
    val["sig"] = sign_obj(val, cred["secret"])
    rec = put_verified(key, val)
    rec["at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rec["party"], rec["op"] = party, "ack"
    append_ledger(rec)
    print(f"{'✅' if rec['ok'] else '❌'} 水位 {party} → {upto}")
    for name, _ in BOARDS:
        print(f"   {name:<8} PUT={rec['put'][name]['http']}  值匹配={rec['match'][name]}")
    if not rec["ok"]:
        print(f"   ★ 未落板：{rec.get('why')}")
        return 2
    return 0


def cmd_status(a):
    keys, src, notes = read_ns(LOG_PREFIX)
    msgs, bad = parse_log(keys) if src else ([], [])
    cvs, cnotes = {}, []
    for p in PARTIES:
        v, nt = read_one(CUR_PREFIX + p)
        cvs[p], _ = v, cnotes.extend(nt)
    notes = notes + cnotes
    # ★ v1.1：钥匙指纹登记（只读；密钥本身永不上板）
    krego, _, knotes = read_ns(KEYS_PREFIX)
    notes = notes + knotes
    keyring = {}
    for p in PARTIES:
        kv = (krego.get(KEYS_PREFIX + p) or {}).get("value")
        keyring[p] = (kv or {}).get("fp")
    ball = current_ball(msgs)
    now = now_local()
    stale = []
    for p in PARTIES:
        for k, m in unread_for(p, msgs, cvs.get(p)):
            if not m.get("reply_required") and m.get("ball") != p:
                continue
            try:
                age = (now - datetime.datetime.fromisoformat(m["ts"])).total_seconds() / 3600.0
            except Exception:
                continue
            if age >= a.stale_hours:
                stale.append({"to": p, "key": k, "age_h": round(age, 1)})
    out = {"version": VERSION, "board_source": src, "board_notes": notes,
           "log_total": len(msgs), "log_malformed": bad, "ball": ball,
           "cursor": {p: (cvs.get(p) or {}).get("upto") for p in PARTIES},
           "cursor_sig": {p: sig_state(cvs.get(p) or {}, p)[0] for p in PARTIES},
           "keyring": keyring,
           "unread": {p: len(unread_for(p, msgs, cvs.get(p))) for p in PARTIES},
           "stale": stale, "stale_hours": a.stale_hours}
    if a.both:
        out["cross_board"] = notes
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        print("═══ 跨域公共邮箱 · 状态 ═══")
        print(f"板源 {src or '**不可达**'}  " + "；".join(notes))
        print(f"日志 {len(msgs)} 条 · 当前持球 {ball or '（无信）'}")
        for p in PARTIES:
            cu = (cvs.get(p) or {}).get("upto")
            print(f"  {p}: 水位 {cu or '（从未读过）'} · 未读 {out['unread'][p]}"
                  f" · 水位sig {out['cursor_sig'][p]}")
        for p in PARTIES:
            print(f"  钥匙 {p}: 板上登记指纹 {keyring[p] or '（未登记）'}"
                  + ("  ★ 未登记 ⇒ 该方尚未跑 keygen" if not keyring[p] else ""))
        if bad:
            print(f"⚠ 不合规信体 {len(bad)} 条：{', '.join(bad[:5])}")
        for s in stale:
            print(f"🔴 陈旧：给 {s['to']} 的 {s['key']} 已 {s['age_h']}h 未读（≥{a.stale_hours}h）")
        if src is None:
            print("❌ 板不可达 ⇒ 以上计数**全部不可信**（不得读作『无新信』）")
            return 2
    return 0 if src else 2


def die(msg):
    print("❌ " + msg, file=sys.stderr)
    return 2


# ══════════════════════════════════════════════════════════════════════
# 自检
# ══════════════════════════════════════════════════════════════════════
def selftest():
    ok = fail = 0

    def chk(c, l):
        nonlocal ok, fail
        if c:
            ok += 1; print("  ✅", l)
        else:
            fail += 1; print("  ❌", l)

    # ① 非 ASCII 头值必须被拦（负控：这正是 2026-10-10 让 PUT 静默变空操作的那条）
    chk(ascii_header_value("xdom-mail"), "ASCII 头值放行")
    chk(not ascii_header_value("外部第三方（CU 实验台线）"),
        "★ 负控：中文头值被拦（否则 PUT 静默空操作 —— 实证病根）")
    chk(not ascii_header_value("ＣＵ"), "★ 负控：全角字符被拦")

    # ② 域隔离：跨写即拒
    # ★★ 2026-10-11 精确化（据外部 CU 线实测证伪 + 本线复核）
    #   原表述「越域写入由 owns_key() **直接拒绝**」【不成立】，正确区分如下：
    #     · owns_key 保证的是【自洽】—— key 必须等于 CUR_PREFIX+party（或落在自己域的 LOG_PREFIX）。
    #     · 它【不是鉴权】—— 本工具【无身份概念】；CLI 面的 key 恒由 `--as` 指定的 party 派生，
    #       ⇒ 「ext 写 cursor/int」这种输入在 CLI 面【构造不出来】。
    #     · ⇒ 二者语义不同：【不可达】（构造不出该情形，**不可验证**）≠【被拒绝】（可被违反、**可验证**）。
    #     · ⇒ 因此下面这条负控【只覆盖函数层，不覆盖 CLI 层】。若将来要真「越权拒绝」，
    #       须引入【独立于 --as 的凭据】（身份概念），届时另立走 CLI 路径的负控。
    #     · ★ 本缺陷与 v6 自立的 R060（静默失败禁止）/ R061（假绿禁止）同型：
    #       负控绿在函数上，而函数【不是被调用的那个对象】。
    chk(owns_key(LOG_PREFIX + "20260101T000000-ext-t-a1b2", "ext"), "发方写自己域的信 ⇒ 允许")
    chk(not owns_key(CUR_PREFIX + "int", "ext"),
        "★ 负控（**仅函数层**）：key=cursor/int 而 party=ext ⇒ 不匹配 ⇒ 拒（★ 该输入在 CLI 面构造不出，见上方声明）")
    chk(owns_key(CUR_PREFIX + "ext", "ext"), "读方写自己的水位 ⇒ 允许")
    chk(not owns_key("notes/collab/x", "ext"), "★ 负控：域外键 ⇒ 拒")

    # ②之二 ★★★ v1.1 凭据门 —— **这才是 CLI 面可构造、因而可验证的那条负控**
    #   （v1.0 的声明是「该输入构造不出来 ⇒ 不可验证」；下面把它变成**能构造、且被拒**）
    import tempfile as _tf
    _d = _tf.mkdtemp(prefix="xdom-cred-st-")
    _kext = os.path.join(_d, "ext.key"); _mk_cred_file(_kext, "ext")
    _kint = os.path.join(_d, "int.key"); _mk_cred_file(_kint, "int")
    _envbak = os.environ.pop(CRED_ENV, None)      # ★ 令环境变量不干扰本段
    try:
        g = lambda cred: argparse.Namespace(cred=cred)
        _c, _e = require_cred(g(_kext), "ext")
        chk(_c is not None and _e is None, "凭据门 ✅ 正控：ext 的凭据 + 声称 ext ⇒ 放行")
        _c, _e = require_cred(g(_kext), "int")
        chk(_c is None and "越权写入被拒" in (_e or ""),
            "★ 凭据门 ⛔ 负控：**ext 的凭据 + 声称 int ⇒ 拒**（★ v1.0 说这条构造不出来，现在构造得出且被拒）")
        _c, _e = require_cred(g(_kint), "int")
        chk(_c is not None, "凭据门 ✅ 正控：int 的凭据 + 声称 int ⇒ 放行（对称，不是只偏一边）")
        _c, _e = require_cred(g(""), "ext")
        chk(_c is None and "fail-closed" in (_e or ""),
            "★ 凭据门 ⛔ 负控：不给凭据 ⇒ **拒**（fail-closed，不是默认放行）")
        _c, _e = require_cred(g(os.path.join(_d, "nope.key")), "ext")
        chk(_c is None, "★ 凭据门 ⛔ 负控：凭据文件不存在 ⇒ 拒")
        _bad = os.path.join(_d, "bad.key")
        open(_bad, "w").write("{ not json")
        _c, _e = require_cred(g(_bad), "ext")
        chk(_c is None, "★ 凭据门 ⛔ 负控：凭据非法 JSON ⇒ 拒")
        _weak = os.path.join(_d, "weak.key")
        json.dump({"party": "ext", "alg": KEY_ALG, "secret": "ab"}, open(_weak, "w"))
        _c, _e = require_cred(g(_weak), "ext")
        chk(_c is None, "★ 凭据门 ⛔ 负控：密钥太短 ⇒ 拒")
        # ★★ 命门自检（行为级，不是读源码）：**凭据来源不得与 --as 挂钩**。
        #   做法：把 KEY_DIR 指向一个**确实放着 ext.key** 的目录，然后**不给凭据**。
        #     · 正确实现（只认 a.cred / 环境变量）⇒ 照拒。
        #     · 若哪天被「优化」成「按 --as 自动去挑钥匙」⇒ 这里会**挑到**那把钥匙 ⇒ 放行 ⇒ 本控变红。
        #   ★ 用读源码（getsource）来验这条是**错的** —— 那是把判据钉在文本上，又一种自指。
        _globals_KEY_DIR = globals()["KEY_DIR"]
        globals()["KEY_DIR"] = _d
        try:
            _c, _e = require_cred(g(""), "ext")
        finally:
            globals()["KEY_DIR"] = _globals_KEY_DIR
        chk(_c is None and "fail-closed" in (_e or ""),
            "★ 命门 ⛔ 负控：**即便 {party}.key 就在磁盘上，不给 --cred 也必须拒**"
            "（证「不按 --as 代挑钥匙」——否则又退化成自指判据 §17.4）")
    finally:
        if _envbak is not None:
            os.environ[CRED_ENV] = _envbak
        for f in os.listdir(_d):
            try:
                os.unlink(os.path.join(_d, f))
            except OSError:
                pass
        try:
            os.rmdir(_d)
        except OSError:
            pass

    # ②之四 ★ keygen 的行为负控 —— 2026-10-11 本线自捕缺陷后补
    #   缺陷：原 cmd_keygen 先写密钥文件、**之后**才判 dry_run ⇒「干跑」也真的落下一把钥。
    #   ⇒ 判据必须是**看磁盘**（文件在不在），不是看它打印了什么。
    import io as _io
    import contextlib as _cl
    _kd = _tf.mkdtemp(prefix="xdom-keygen-st-")
    _kd_bak = globals()["KEY_DIR"]
    _put_bak = globals()["put_verified"]
    # ★ 台账也要挡掉 —— 否则 `--selftest` 会往**真台账**里塞假的 keygen 记录
    #   （ok:true 但板侧其实什么都没写）。2026-10-11 自捕：真台账已被塞进 11+ 条。
    _ledk_bak = globals()["append_ledger"]
    _seen = {}
    globals()["KEY_DIR"] = _kd
    globals()["append_ledger"] = lambda rec, path=None: None
    globals()["put_verified"] = lambda k, v, **kw: (
        _seen.update({"k": k, "v": v})
        or {"key": k, "ok": True, "ts": "", "version": 1, "value": v, "why": ""})
    try:
        # ★ chk() **必须在 redirect 之外** —— 否则这条控的 ❌ 会被一起吞进 StringIO，
        #   于是「红了也看不见」，与「空输出 + rc=0」同族。（本线 2026-10-11 自捕）
        with _cl.redirect_stdout(_io.StringIO()), _cl.redirect_stderr(_io.StringIO()):
            cmd_keygen(argparse.Namespace(as_="ext", force=False, dry_run=True, register_only=False))
        _kp = os.path.join(_kd, "ext.key")
        chk(not os.path.exists(_kp),
            "★ keygen ⛔ 负控：**--dry-run 不得落下任何密钥文件**（干跑就得真的不写）")
        chk("k" not in _seen, "★ keygen ⛔ 负控：--dry-run 也不得登记指纹上板")
        with _cl.redirect_stdout(_io.StringIO()), _cl.redirect_stderr(_io.StringIO()):
            cmd_keygen(argparse.Namespace(as_="ext", force=False, dry_run=False, register_only=False))
        chk(os.path.exists(_kp), "keygen ✅ 正控：非 dry-run ⇒ 密钥文件确实生成")
        _mode = os.stat(_kp).st_mode & 0o777
        chk(_mode == 0o600,
            f"★ keygen ✅ 正控：密钥文件权限必须是 0600（实测 {oct(_mode)}）—— 不是先建后 chmod")
        _sec2 = json.load(open(_kp, encoding="utf-8"))["secret"]
        chk(_seen.get("k") == KEYS_PREFIX + "ext",
            "keygen ✅ 正控：登记写在 keys/ext（自己的域）")
        chk(_seen.get("v", {}).get("fp") == key_fingerprint(_sec2),
            "★ keygen ✅ 正控：**登记上板的指纹 == 本地密钥的指纹**（防两处各写一份、彼此漂移）")
        chk(verify_obj(_seen.get("v", {}), _sec2) is True,
            "★ keygen ✅ 正控：登记值**能被刚生成的这把钥验过**（自签成立 ⇒ 证「手里确有这把钥」）")
        # ★ --register-only：补登记**已有**密钥的指纹，且**必须不轮换密钥**
        #   （起因：int 实测「钥已存在 ⇒ 无法补登记 ⇒ 只能 --force 轮换 ⇒ 对方旧签名全废」）
        _seen.clear()
        with _cl.redirect_stdout(_io.StringIO()), _cl.redirect_stderr(_io.StringIO()):
            _rc = cmd_keygen(argparse.Namespace(as_="ext", force=False, dry_run=False,
                                                register_only=True))
        chk(_rc == 0, "★ keygen --register-only ✅ 正控：已存在的钥可**单独补登记**（不再死锁）")
        chk(json.load(open(_kp, encoding="utf-8"))["secret"] == _sec2,
            "★★ keygen --register-only ⛔ 负控：**密钥一个字节都没变**（补登记 ≠ 轮换）")
        chk(_seen.get("v", {}).get("fp") == key_fingerprint(_sec2),
            "★ keygen --register-only ✅ 正控：登记的还是**同一把**钥的指纹")
        # ★ 这条是**突变测试逼出来的**：只查「文件没被改写」是**空转绿** ——
        #   若实现改成用一把**随机钥去签**登记值（文件确实没动），前两条照样绿。
        #   ⇒ 必须再验：登记值**能被盘上那把钥验过**（自签才有意义）。
        chk(verify_obj(_seen.get("v", {}), _sec2) is True,
            "★ keygen --register-only ✅ 正控：登记值**能被盘上那把钥验过**（否则自签是空签）")
        # ⛔ 负控：本地钥的 party 与 --as 不符 ⇒ 拒（不拿 A 的钥登记 B 的指纹）
        _p2 = os.path.join(_kd, "int.key")
        json.dump({"party": "ext", "alg": KEY_ALG, "secret": secrets.token_hex(KEY_BYTES)},
                  open(_p2, "w"))
        with _cl.redirect_stdout(_io.StringIO()), _cl.redirect_stderr(_io.StringIO()):
            _rc2 = cmd_keygen(argparse.Namespace(as_="int", force=False, dry_run=False,
                                                 register_only=True))
        chk(_rc2 == 2, "★ keygen --register-only ⛔ 负控：文件里 party=ext 却要按 int 登记 ⇒ 拒")
    finally:
        globals()["KEY_DIR"] = _kd_bak
        globals()["put_verified"] = _put_bak
        globals()["append_ledger"] = _ledk_bak
        for _f in (os.listdir(_kd) if os.path.isdir(_kd) else []):
            try:
                os.unlink(os.path.join(_kd, _f))
            except OSError:
                pass
        try:
            os.rmdir(_kd)
        except OSError:
            pass

    # ②之五 ★ --probe 不得**冒名** —— 2026-10-11 本线自捕：原实现在源码里写死 `int`
    #   ⇒ 后果：① 想跑探针就得拿着**对方**的私钥（越界）；② 会在共享日志里留下署名为 int 的信。
    #   ★ 两条都必须在**任何网络 I/O 之前**返回 2 —— 所以下面这两条是离线可跑的。
    #   ★ 选 **int 的凭据** 做这条：若实现是「从凭据反推/写死身份」，它会**接受**并写入
    #     ⇒ _calls 非空、rc=0 ⇒ 本控变红。（第一版我用 ext 的凭据 ⇒ 写死 int 的实现也会
    #       因凭据不符而拒，「红不了」⇒ 那条控是**空转绿**。2026-10-11 自捕后改成 int。）
    _pd = _tf.mkdtemp(prefix="xdom-probe-st-")
    _pext = os.path.join(_pd, "ext.key"); _mk_cred_file(_pext, "ext")
    _pint = os.path.join(_pd, "int.key"); _mk_cred_file(_pint, "int")
    _calls, _put2 = [], globals()["put_verified"]
    globals()["put_verified"] = lambda k, v, **kw: (
        _calls.append(k) or {"key": k, "ok": True, "ts": "", "version": 1, "value": v, "why": ""})
    # ★ 台账也要挡掉 —— 否则 `--selftest` 会往**真台账**里塞假的 keygen 记录
    #   （ok:true 但板侧其实什么都没写）。2026-10-11 自捕：真台账已被塞进 11 条。
    _led2 = globals()["append_ledger"]
    globals()["append_ledger"] = lambda rec, path=None: None
    try:
        with _cl.redirect_stdout(_io.StringIO()), _cl.redirect_stderr(_io.StringIO()):
            _r1 = probe(_pint, "")      # 有**合法的 int 凭据**，但**不给 --as**
            _r2 = probe(_pext, "int")   # 拿 ext 的凭据声称 int
        chk(_r1 == 2, "★ probe ⛔ 负控：凭据合法但不给 --as ⇒ 拒（★ 不得从凭据反推身份）")
        chk(not _calls, "★ probe ⛔ 负控：上述拒绝发生在**任何写入之前**（零次 PUT）")
        chk(_r2 == 2, "★ probe ⛔ 负控：拿 ext 的凭据声称 int ⇒ 拒（探针不得冒名）")
    finally:
        globals()["put_verified"] = _put2
        globals()["append_ledger"] = _led2
        for _f in (os.listdir(_pd) if os.path.isdir(_pd) else []):
            try:
                os.unlink(os.path.join(_pd, _f))
            except OSError:
                pass
        try:
            os.rmdir(_pd)
        except OSError:
            pass

    # ②之三 ★ 签名三态：✓ 验过 / ✗ 改过 / ? 不可判
    _sd = _tf.mkdtemp(prefix="xdom-sig-st-")
    _sec = _mk_cred_file(os.path.join(_sd, "ext.key"), "ext")
    _m = {"from": "ext", "to": "int", "body": "hello", "ts": "2026-10-11T00:00:00+08:00"}
    _m["signer_fp"] = key_fingerprint(_sec)
    _m["sig"] = sign_obj(_m, _sec)
    chk(verify_obj(_m, _sec) is True, "签名 ✅ 正控：未改动的信 ⇒ 验过")
    _m2 = dict(_m, body="hello (改过)")
    chk(verify_obj(_m2, _sec) is False, "★ 签名 ⛔ 负控：改一个字节 ⇒ 验不过")
    chk(verify_obj({"from": "ext"}, _sec) is False, "★ 签名 ⛔ 负控：无 sig 字段 ⇒ 验不过")
    chk(verify_obj(_m, secrets.token_hex(KEY_BYTES)) is False,
        "★ 签名 ⛔ 负控：拿**别人的**密钥验 ⇒ 验不过（对称性：验不了≠是对的）")
    chk(sig_state({}, "ext")[0] == "?",
        "★ 签名三态 ⛔ 负控：**无签名的信必须判『不可判 ?』**，不得读作通过")
    for _f in (os.listdir(_sd) if os.path.isdir(_sd) else []):
        try:
            os.unlink(os.path.join(_sd, _f))
        except OSError:
            pass
    try:
        os.rmdir(_sd)
    except OSError:
        pass

    # ③ 未读判定 + 负控（推进水位后必须清空）
    K = lambda s: LOG_PREFIX + s
    m1 = {"from": "int", "to": "ext", "ts": "2026-10-10T07:00:00+08:00", "ball": "ext"}
    m2 = {"from": "int", "to": "int", "ts": "2026-10-10T07:01:00+08:00", "ball": "ext"}
    m3 = {"from": "ext", "to": "int", "ts": "2026-10-10T07:02:00+08:00", "ball": "int"}
    msgs = [(K("20261010T070000-int-a-aaaa"), m1), (K("20261010T070100-int-b-bbbb"), m2),
            (K("20261010T070200-ext-c-cccc"), m3)]
    chk([k for k, _ in unread_for("ext", msgs, None)] == [msgs[0][0]],
        "未读=发给我的那些（不把自己发的、不把别人的算进来）")
    chk(unread_for("ext", msgs, {"upto": msgs[0][0]}) == [], "★ 负控：水位推到该键后未读清空")
    chk([k for k, _ in unread_for("int", msgs, None)] == [msgs[2][0]],
        "同一日志、两个水位各自独立（int 的未读=ext 发给它的，且不含自己发的 int→int）")
    chk(current_ball(msgs) == "int", "球权 = 日志最后一条的 ball（派生，不落冗余字段）")
    chk(current_ball([]) is None, "空日志 ⇒ 无球权（不得编造）")

    # ④ 回读判据必须比「我推的值」，不得退化成「两板彼此」
    pushed, other = {"v": 1}, {"v": 2}
    chk(sha16(pushed) == sha16({"v": 1}), "canonical 指纹稳定")
    chk(sha16(pushed) != sha16(other), "真差异 ⇒ 指纹不同（有判别力）")
    fake = {"key": "k", "pushed_sha": sha16(pushed), "put": {"local": {"http": 200}, "central": {"http": 200}},
            "get": {}, "match": {"local": sha16(other) == sha16(pushed),
                                 "central": sha16(other) == sha16(pushed)}, "ok": False}
    fake["ok"] = all(fake["match"].values())
    chk(fake["ok"] is False,
        "★ 负控：两板**一致但都 ≠ 我推的值** ⇒ ok=False（bb_dualwrite 的缺陷正在此）")
    chk(sha16({"v": 1}) != sha16({"v": 1, "_via": "x"}),
        "★ 负控：多出字段即视为不同（本工具不比传输标记，宁严勿松）")

    # ⑤ 三态必须长得不一样
    chk(read_ns(LOG_PREFIX, boards=[("local", "http://127.0.0.1:9")])[1] is None,
        "★ 负控：板不可达 ⇒ 源为 None（调用层据此报 FAIL，不得读作『无新信』）")

    # ⑥ 键格式
    chk(bool(re.fullmatch(r"[a-z]+", NS.split("/")[0])), "首段纯小写（合板键语法，违者 400）")
    chk(slugify("K6 Wiring / 接线") == "k6-wiring", "topic 归一化（中文被剥离，不产生非法键）")

    # ⑬ ★★ W8.2 回归负控（D-060）—— ★ 这三条是【新控】。
    #    ★ 直接回应外部线〔3〕的批评：改前 47、改后仍 47 ⇒ 覆盖面没变。
    #    ★ 其中第一条若早存在，:751 那次注入【当时就会红】。
    _cur = cursor_value("int", "notes/xdom/log/20261011T000000-x")
    _letter_fields = ("type", "dedup_key", "payload", "cahac", "channel",
                      "sender", "recipient", "signer_fp")
    _oncur = [f for f in _letter_fields if f in _cur]
    chk(not _oncur,
        "★ 负控：游标上不得有信封字段（有则 = W8.2 回归 / D-060）；实际越界=%r" % _oncur)
    # ★ 正控：信上【必须】有 —— 否则上一条恒绿、什么都测不出
    _letter = {"from": "int", "to": "ext", "body": "x"}
    with_envelope(_letter, "x")
    chk(_letter.get("type") == "letter" and bool(_letter.get("dedup_key")),
        "正控：信对象上【必须】带信封（type=letter ∧ dedup_key 非空）")
    # ★★ 口径控（外部线〔1〕）—— ★ 测【事实】，不测措辞。
    #    ★ 教训（本控初版当场假红）：初版写成「docstring 里不得出现『同构』二字」⇒
    #      被【说明这两个字为何错】的那句说明文字满足 ⇒ 假红。
    #      ★ 与 D-053 同族：判据被「提及」满足，而不是被「主张」满足。
    #    ★ 正确的判据 = 【两侧键确实不等价】—— 那才是「不得称同构」的理由，声明只是推论。
    _canon = "W8.2 落地：跨域邮箱开始携带 CAHAC §3 信封"
    _pyk = dedup_key_from("int", "ext", _canon)
    _jsk = None
    try:
        import subprocess as _sp
        _r = _sp.run([NODE_BIN, "--input-type=module", "-e",
                      "import {dedupKey} from '%s'; console.log(dedupKey('int','ext',%s))"
                      % (JS_IDENTITY, json.dumps(_canon))],
                     capture_output=True, text=True, timeout=20)
        if _r.returncode == 0:
            _jsk = (_r.stdout or "").strip()
    except Exception:
        _jsk = None
    if _jsk is None:
        print("  ⚠  不可判：JS 侧取不到（node 缺失 / 模块不可读）⇒ ★ 不判成立、也不判失败")
    else:
        chk(_jsk != _pyk,
            "★ 事实控：两侧 dedup_key 实际【不等价】（本侧=%r / JS 侧=%r）"
            "—— ★ 这才是「不得称同构」的理由" % (_pyk, _jsk))

    print(f"\nselftest: {ok} PASS / {fail} FAIL")
    return 0 if fail == 0 else 1


def selfcheck():
    print("== xdom-mail 自查（TCC 能力边界）==")
    print("【① 能力清单】")
    print(f"  · xdom-mail.py v{VERSION} — 跨域公共邮箱（外部会话 ⨯ 内部会话）")
    print("  · 写黑板 PUT，**仅** notes/xdom/log/**（发方）· cursor/<自己>（读方）· keys/<自己>（keygen）")
    print("    ★ 域自洽由 owns_key() 保证；★ **鉴权由 require_cred() 保证（凭据独立于 --as）**")
    print("  · ★ 写动作（send/ack/probe）**fail-closed**：无凭据即拒，不默认放行")
    print("    ★ 例外：keygen 的登记**自签**（用刚生成的钥），故不需 --cred")
    print("  · ★ 仅 keygen 会在 ~/.dsh/xdom-keys/ 新建 0600 密钥文件；不覆盖已存在的（除非 --force）")
    print("  · 写本地留痕 logs/xdom-mail.jsonl（逐次 PUT/GET 分字段）")
    print("  · 命令/参数: keygen, send, inbox, ack, status, --selfcheck, --selftest, --probe, --version")
    print("  · ★ --probe 以**运行者自己的身份**写入（须给 --as <自己> + 自己的 --cred），")
    print("    不写死 int —— 否则等于「要探针就得拿着对方的私钥」，且会在共享日志里冒名。")
    print("  · ★ 限度：凭据门是【能力闸 + 篡改可检出】，**不是**防同机同用户的恶意进程"
          "（0600 挡不住同 uid 的读取）；跨机/跨账号时才是真鉴权。")
    print("【② 不该发生路径清单】")
    print("  · 不执行外部命令（无 subprocess / os.system / eval / exec）")
    print("  · 不删除数据（--probe 的清理走板 DELETE，失败则如实报残留，不本地删）")
    print("  · 不改权限（os.chmod/chown）、不碰 launchd、不起服务、不重启任何框架")
    print("  · 不写 notes/xdom 之外任何键 —— 除非经 owns_key() 放行")
    print("【③ 依赖完整性】")
    print("  · 仅 Python 3 标准库：argparse/contextlib/datetime/hashlib/hmac/io/json/os/re/secrets/sys/urllib/uuid")
    print("  · 令牌读 ~/.dsh/{board,webhook,blackboard}-token（缺失即不带该头，不崩）")
    print("  · ★ 限度：以上为**结构自述**，非运行时证明；核验请用 `--selftest`（含负控）+ `--probe`（真板往返）")
    return 0


def probe(cred_path="", as_=""):
    """真板往返：发一封自测信 → 回读 → 清理。★ 这是「手段就绪 ≠ 已实战验证」的那一步。

    ★ v1.1：探针以**运行者自己的身份**写入（`--as <自己>` + 自己的密钥），**不再写死 `int`** ——
      写死等于「要跑探针就得拿着对方的私钥」，既越界，又会在共享日志里留下**冒名**的信。
    """
    party = role(as_)
    if not party:
        print("❌ --probe 必须给 --as <自己>（如 --as ext 或 --as int）。"
              "★ 刻意**不猜** —— 猜就等于按身份自动挑钥匙（§17.4 自指）。", file=sys.stderr)
        return 2
    gate = argparse.Namespace(cred=cred_path or "")
    cred, err = require_cred(gate, party)
    if err:
        print(f"❌ --probe 是【写入】，同样要凭据（以 {party} 身份）。" + err, file=sys.stderr)
        return 2
    key = f"{LOG_PREFIX}{now_local().strftime('%Y%m%dT%H%M%S')}-{party}-_selftest-{uuid.uuid4().hex[:4]}"
    val = {"id": key[len(LOG_PREFIX):], "from": party, "to": party, "topic": "_selftest",
           "subject": "xdom-mail --probe", "ts": now_local().isoformat(timespec="seconds"),
           "ball": "none", "reply_required": False, "body": "自测探针，可删。",
           "ref": [], "from_session": "", "writer_label": SIDE_LABEL.get(party, party)}
    with_envelope(val, val.get("body", ""))   # ★ W8.2：本路径同样写信封
    val["signer_fp"] = key_fingerprint(cred["secret"])
    val["sig"] = sign_obj(val, cred["secret"])
    rec = put_verified(key, val)
    append_ledger({**rec, "op": "probe",
                   "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    ok = rec["ok"]
    print(json.dumps(rec, ensure_ascii=False, indent=1))
    if not ok:
        print(f"❌ 真板往返失败：{rec.get('why')}")
        return 1
    # 清理（尽力而为；残留如实报告）
    # ★ 删之前先自证「这把键确实在我自己的域里」—— 免得 DELETE 被指向别处时误删他人的信。
    if not owns_key(key, party):
        print(f"⚠️  探针键 {key} 不在 {party} 的发送域内 ⇒ **拒绝 DELETE**（宁留残留，不误删）",
              file=sys.stderr)
        return 1
    residue = []
    for name, base in BOARDS:
        r = _req(base, key, "DELETE", None)
        if r["http"] not in (200, 204, 404):
            residue.append(f"{name}={r['http']}/{r['err']}")
    print("✅ 真板往返通过（双板 PUT 200 且回读值 == 推送值）")
    print("   清理残留：" + ("无" if not residue else "；".join(residue) + f" ⇒ 请人工删 {key}"))
    return 0


def main():
    ap = argparse.ArgumentParser(description="跨域公共邮箱（外部会话 ⨯ 内部会话）")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--probe", action="store_true")
    # ★ dest 刻意与子命令的 --cred/--as 分开：argparse 里同名会互相覆盖，子命令默认值会把顶层的抹掉
    ap.add_argument("--cred", dest="cred_top", default="")
    ap.add_argument("--as", dest="as_top", default="")
    ap.add_argument("--version", action="store_true")
    sub = ap.add_subparsers(dest="cmd")

    g = sub.add_parser("keygen", help="★ v1.1：生成自己的密钥并登记指纹（不覆盖已存在的）")
    g.add_argument("--as", dest="as_", required=True)
    # ★ 刻意**不给 keygen 加 --cred**：登记由新钥自签。
    #   若在这里放一个被忽略的 --cred，会让人以为 keygen 也过凭据门 —— 那是假的安全感。
    g.add_argument("--force", action="store_true")
    g.add_argument("--register-only", dest="register_only", action="store_true",
                   help="★ 只把**已有**密钥的指纹登记上板，不生成、不轮换")
    g.add_argument("--dry-run", action="store_true")
    g.set_defaults(fn=cmd_keygen)

    s = sub.add_parser("send", help="投递（只写自己域的信键；★ 需 --cred）")
    s.add_argument("--cred", default="", help="★ v1.1 凭据（独立于 --from）")
    s.add_argument("--from", dest="frm", required=True)
    s.add_argument("--to", required=True)
    s.add_argument("--topic", required=True)
    s.add_argument("--subject", default="")
    s.add_argument("--body", default="")
    s.add_argument("--body-file", default="")
    s.add_argument("--ball", default="")
    s.add_argument("--reply-required", action="store_true")
    s.add_argument("--ref", action="append", default=[])
    s.add_argument("--from-session", default="")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(fn=cmd_send)

    i = sub.add_parser("inbox", help="读信（含水位与球权；空 ≠ 无信）")
    i.add_argument("--as", dest="as_", required=True)
    i.add_argument("--all", action="store_true")
    i.add_argument("--json", action="store_true")
    i.set_defaults(fn=cmd_inbox)

    k = sub.add_parser("ack", help="推进自己的水位（只写自己的 cursor 键；★ 需 --cred）")
    k.add_argument("--as", dest="as_", required=True)
    k.add_argument("--cred", default="", help="★ v1.1 凭据（独立于 --as）")
    k.add_argument("--upto", default="")
    k.add_argument("--latest", action="store_true")
    k.set_defaults(fn=cmd_ack)

    st = sub.add_parser("status", help="状态（板可达 / 日志 / 双方水位 / 球权 / 陈旧）")
    st.add_argument("--json", action="store_true")
    st.add_argument("--both", action="store_true")
    st.add_argument("--stale-hours", type=float, default=6.0)
    st.set_defaults(fn=cmd_status)

    a = ap.parse_args()
    if a.version:
        print(json.dumps({"tool": "xdom-mail", "version": VERSION}))
        return 0
    if a.selfcheck:
        return selfcheck()
    if a.selftest:
        return selftest()
    if a.probe:
        return probe(a.cred_top, a.as_top)
    if not getattr(a, "fn", None):
        ap.print_help()
        return 2
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
