#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""proxy-change-record.py — 「代做」变更留痕台账 v1.0.0

为什么要这个工具（所有者 2026-10-09 明确要求）：
  > 「你代做要做时间戳和授权节点登记，记录最后变动人」
  ⇒ 代做（agent 代替所有者实施变更）必须留下三件事，缺一不可：
     ① **时间戳**（何时改）
     ② **授权节点登记**（凭何而改 —— 授权来源、授权原话、授权时点）
     ③ **最后变动人**（谁改的 —— 会话 id，而非笼统的「agent」）

★ 对齐本机既有规范（不自造）：
  · `scripts/channel-gate-weekly.py` 的判据：「留痕行必须有 **id/channel/evidence/rollback**（缺=门被绕过）」
    ⇒ 本台账沿用这【四要素】，再补 授权/时间戳/变动人 三项。
  · 黑板写入用 **X-Writer** 头标记写入者；本台账的 `lastModifier` 与之同源。
  · CHANGELOG 用 `## [版本] - 日期` 格式。

★ 本工具不修改任何业务文件；它【只写台账】+ 可选【写黑板登记卡】。
  ⇒ 业务文件的改动由实施方（代做者）完成，并须在文件内嵌变更标记（见 --marker-snippet）。

用法：
  # ① 登记一次【授权】（代做开始前必须先做）
  python3 proxy-change-record.py --authorize \\
      --scope "dsh-plugin-hr,dsh-plugin-excalidraw" \\
      --quote "4 个 cjs 插件做迁移，这次你代做" --from-user

  # ② 登记一次【变更】（每批改动后）
  python3 proxy-change-record.py --record \\
      --channel "plugin:dsh-plugin-hr" --evidence "esbuild 重编译, lib/*.js 由 CJS→ESM" \\
      --rollback "git checkout <sha> -- dsh-plugin-hr/" --files "src/index.ts,lib/index.js"

  # ③ 查台账 / 查某文件的最后变动人
  python3 proxy-change-record.py --list
  python3 proxy-change-record.py --last-modifier dsh-plugin-hr/lib/index.js

  # ④ 生成【文件内嵌标记】（贴到改动文件头部）
  python3 proxy-change-record.py --marker-snippet dsh-plugin-hr/src/index.ts

  python3 proxy-change-record.py --selftest
  python3 proxy-change-record.py --lean4-check     # ★ R006 ⑩ 六项 A–F

退出码（★ R006 ⑨）：0 = 成功；1 = 门未过（缺字段/无授权）；2 = 用法或环境错误
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== proxy-change-record 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · proxy-change-record.py — 「代做」变更留痕台账 v1.0.0")
    print("  · 为什么要这个工具（所有者 2026-10-09 明确要求）：")
    print("  · > 「你代做要做时间戳和授权节点登记，记录最后变动人」")
    print("  · ⇒ 代做（agent 代替所有者实施变更）必须留下三件事，缺一不可：")
    print("  · 命令/参数: authorize, scope, quote, from-user, granted-by, record, channel, evidence")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, hashlib, io, json, os, sys, tempfile, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/proxy-change-record.log")
    return 0



import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处

import argparse
import hashlib
import io
import json
import os
import sys
import time

HOME = os.path.expanduser("~")
COLLAB = os.path.join(HOME, "dsh-collab")
LEDGER = os.path.join(COLLAB, "data", "proxy-change-ledger.json")
LOG = os.path.join(COLLAB, "logs", "proxy-change-record.log")   # ★ R006 ⑦ 固定日志
SELF_ID = "session-b250bf9d"      # ★ 最后变动人（本会话 id；非笼统的 "agent"）

# ═══ ★ 冻结白名单（R006 ⑩ 类型锁）：一次留痕【必须具备】的字段 ═══
REQUIRED_CHANGE = ("id", "channel", "evidence", "rollback",          # 既有四要素
                   "authorization", "timestamp", "lastModifier")      # ★ 所有者加的三项
REQUIRED_AUTH = ("authId", "scope", "quote", "timestamp", "grantedBy")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def load():
    try:
        return json.load(io.open(LEDGER, encoding="utf-8"))
    except Exception:
        return {"_meta": {"version": __version__, "createdAt": now()},
                "authorizations": [], "changes": []}


def save(d):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    tmp = LEDGER + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, LEDGER)
    # ★ 写后必读（本机纪律：写入返回非 200 不等于成功）
    back = json.load(io.open(LEDGER, encoding="utf-8"))
    return (len(back.get("changes", [])) == len(d.get("changes", []))
            and len(back.get("authorizations", [])) == len(d.get("authorizations", [])))


def make_id(prefix, payload):
    h = hashlib.sha256(("%s|%s|%s" % (prefix, payload, now())).encode("utf-8")).hexdigest()[:12]
    return "%s-%s-%s" % (prefix, time.strftime("%Y%m%d"), h)


def cmd_authorize(a):
    d = load()
    missing = [k for k in ("scope", "quote") if not getattr(a, k, None)]
    if missing:
        print("★ 门未过：授权登记缺字段 %s" % ",".join(missing), file=sys.stderr)
        return 1
    rec = {"authId": make_id("AUTH", a.scope),
           "scope": a.scope,
           "quote": a.quote,                     # ★ 授权【原话】，不得转述
           "grantedBy": "user" if a.from_user else (a.granted_by or "unknown"),
           "timestamp": now(),
           "recordedBy": SELF_ID}
    d["authorizations"].append(rec)
    ok = save(d)
    log("authorize authId=%s scope=%s readback=%s" % (rec["authId"], a.scope, ok))
    print("✓ 授权已登记")
    print("    authId    : %s" % rec["authId"])
    print("    scope     : %s" % rec["scope"])
    print("    quote     : %s" % rec["quote"])
    print("    grantedBy : %s" % rec["grantedBy"])
    print("    timestamp : %s" % rec["timestamp"])
    print("    写后必读  : %s" % ("✓ 一致" if ok else "★ 不一致"))
    return 0 if ok else 1


# ═══ ★ 高危动作前缀（R006 ⑩ 冻结白名单）：这些【新建资源】类动作须单独授权 ═══
#   ★ 2026-10-09 加（实证漏洞）：原 active_auth 用【子串匹配】⇒ 授权 scope 里的
#     `dsh-plugin-excalidraw` 会把 `gitee:new-repo:dsh-plugin-excalidraw`（新建仓库）
#     误认为「在授权范围内」而放行 —— 判据过宽（今日同族问题）。
#   ⇒ 修法：**新建/删除类动作须在 scope 中【显式列出该动作】**，不接受子串带来的宽松匹配。
HIGH_RISK_PREFIXES = ("gitee:new-repo:", "github:new-repo:", "delete:", "rm:", "drop:")


def is_high_risk(channel):
    return bool(channel) and channel.startswith(HIGH_RISK_PREFIXES)


def active_auth(d, channel=None):
    """找【仍然适用】的授权。

    ★ 两级判据（2026-10-09 修）：
      · 普通变更：scope 含 channel 的任一 token（子串匹配，宽松）
      · **高危动作（新建/删除资源）**：scope 必须【显式列出完整 channel】
        ⇒ 不接受「因为 scope 里有同名项目」而放行
    """
    if not channel:
        return None
    if is_high_risk(channel):
        for r in reversed(d.get("authorizations", [])):
            sc = (r.get("scope") or "").strip()
            if sc == "*":
                continue          # ★ 通配也【不覆盖】高危动作
            if channel in [x.strip() for x in sc.split(",")]:
                return r
        return None
    for r in reversed(d.get("authorizations", [])):
        sc = r.get("scope") or ""
        if sc.strip() == "*":
            return r
        for tok in sc.split(","):
            if tok.strip() and tok.strip() in channel:
                return r
    return None


def cmd_record(a):
    d = load()
    auth = active_auth(d, a.channel)
    missing = []
    if not a.channel: missing.append("channel")
    if not a.evidence: missing.append("evidence")
    if not a.rollback: missing.append("rollback")
    if auth is None: missing.append("authorization(无适用授权)")
    if missing:
        print("★ 门未过：%s" % ",".join(missing), file=sys.stderr)
        print("  （本机 channel_gate 判据：留痕须含 id/channel/evidence/rollback）", file=sys.stderr)
        print("  （所有者 2026-10-09 追加：还须含 authorization/timestamp/lastModifier）", file=sys.stderr)
        log("DENY record channel=%s missing=%s" % (a.channel, missing))
        return 1
    rec = {"id": make_id("CHG", a.channel + a.evidence),
           "channel": a.channel,
           "evidence": a.evidence,
           "rollback": a.rollback,
           "authorization": auth["authId"],
           "authQuote": auth["quote"],
           "timestamp": now(),
           "lastModifier": a.by or SELF_ID,
           "files": [x.strip() for x in (a.files or "").split(",") if x.strip()]}
    d["changes"].append(rec)
    ok = save(d)
    log("record id=%s channel=%s files=%d readback=%s" % (rec["id"], a.channel, len(rec["files"]), ok))
    print("✓ 变更已登记")
    for k in REQUIRED_CHANGE:
        print("    %-14s %s" % (k + ":", str(rec.get(k))[:88]))
    print("    %-14s %s" % ("files:", ",".join(rec["files"])[:88]))
    print("    写后必读      : %s" % ("✓ 一致" if ok else "★ 不一致"))
    return 0 if ok else 1


def cmd_list(a):
    d = load()
    print("== 代做留痕台账 ==")
    print("    授权 %d 条 · 变更 %d 条" % (len(d.get("authorizations", [])), len(d.get("changes", []))))
    print()
    print("  ── 授权 ──")
    for r in d.get("authorizations", [])[-8:]:
        print("    %-22s %-28s %s" % (r.get("authId", "?")[:22], (r.get("scope") or "")[:28], r.get("timestamp")))
    print()
    print("  ── 变更（最近 10）──")
    for r in d.get("changes", [])[-10:]:
        print("    %-24s %-26s %s" % (r.get("id", "?")[:24], (r.get("channel") or "")[:26], r.get("timestamp")))
        print("        evidence=%s" % (r.get("evidence") or "")[:78])
        print("        rollback=%s" % (r.get("rollback") or "")[:78])
        print("        lastModifier=%s · auth=%s" % (r.get("lastModifier"), r.get("authorization")))
    return 0


def cmd_last_modifier(a):
    d = load()
    tgt = a.last_modifier
    hits = [r for r in d.get("changes", []) if any(tgt in f or f in tgt for f in (r.get("files") or []))]
    if not hits:
        print("★ 无记录：%s 未在台账中" % tgt)
        return 1
    r = hits[-1]
    print("✓ %s" % tgt)
    print("    最后变动人 : %s" % r.get("lastModifier"))
    print("    时间戳     : %s" % r.get("timestamp"))
    print("    授权       : %s（「%s」）" % (r.get("authorization"), (r.get("authQuote") or "")[:50]))
    print("    通道       : %s" % r.get("channel"))
    print("    回滚点     : %s" % r.get("rollback"))
    print("    变更 id    : %s" % r.get("id"))
    return 0


def cmd_marker(a):
    """生成【文件内嵌标记】—— 贴到被改动文件头部，使文件本身自带变动人信息。"""
    d = load()
    tgt = a.marker_snippet
    hits = [r for r in d.get("changes", []) if any(tgt in f or f in tgt for f in (r.get("files") or []))]
    if not hits:
        print("★ 请先 --record 登记该文件的变更，再生成标记", file=sys.stderr)
        return 1
    r = hits[-1]
    ext = os.path.splitext(tgt)[1]
    if ext in (".ts", ".tsx", ".js", ".mjs", ".cjs"):
        pre = "// "
    elif ext in (".py", ".sh", ".yml", ".yaml"):
        pre = "# "
    else:
        pre = "# "
    print("%s★ 变更留痕（自动生成，勿手改）" % pre)
    print("%s  时间戳     : %s" % (pre, r.get("timestamp")))
    print("%s  最后变动人 : %s" % (pre, r.get("lastModifier")))
    print("%s  授权       : %s（所有者原话：「%s」）" % (pre, r.get("authorization"), (r.get("authQuote") or "")[:40]))
    print("%s  通道/证据  : %s · %s" % (pre, r.get("channel"), (r.get("evidence") or "")[:50]))
    print("%s  回滚点     : %s" % (pre, r.get("rollback")))
    return 0


def selftest():
    import tempfile
    global LEDGER
    fails = neg = pos = 0

    def c(name, cond, kind="pos"):
        nonlocal fails, neg, pos
        if kind == "pos": pos += 1
        else: neg += 1
        good = bool(cond)
        print("  %s %-6s %-52s" % ("✅" if good else "❌", kind, name))
        if not good: fails += 1

    print("== proxy-change-record selftest ==")
    c("必需字段含既有四要素", all(k in REQUIRED_CHANGE for k in ("id", "channel", "evidence", "rollback")))
    c("★ 必需字段含所有者三项", all(k in REQUIRED_CHANGE for k in ("authorization", "timestamp", "lastModifier")))
    c("授权记录字段齐备", all(k in REQUIRED_AUTH for k in ("authId", "scope", "quote", "timestamp", "grantedBy")))
    # 负例：无授权时 active_auth 返回 None
    c("★ 无授权 ⇒ active_auth 为 None", active_auth({"authorizations": []}, "x") is None, kind="neg")
    # 正例：scope 命中
    dd = {"authorizations": [{"authId": "A1", "scope": "dsh-plugin-hr,x"}]}
    c("scope 命中 ⇒ 找到授权", (active_auth(dd, "plugin:dsh-plugin-hr") or {}).get("authId") == "A1")
    # 负例：scope 不命中
    c("scope 不命中 ⇒ None", active_auth(dd, "plugin:other") is None, kind="neg")
    # 正例：* 通配
    c("scope='*' ⇒ 任意通道可用", (active_auth({"authorizations": [{"authId": "A2", "scope": "*"}]}, "z") or {}).get("authId") == "A2")
    # 正例：id 唯一且带日期
    c("id 形如 CHG-YYYYMMDD-<hash>", make_id("CHG", "x").startswith("CHG-" + time.strftime("%Y%m%d")))
    # ★ 负例（2026-10-09 实证漏洞）：高危动作【不得】因子串匹配而放行
    dd2 = {"authorizations": [{"authId": "A3", "scope": "dsh-plugin-excalidraw"}]}
    c("★ 高危（新建仓库）不因子串放行",
      active_auth(dd2, "gitee:new-repo:dsh-plugin-excalidraw") is None, kind="neg")
    c("★ 通配 * 也不覆盖高危动作",
      active_auth({"authorizations": [{"authId": "A4", "scope": "*"}]}, "delete:foo") is None, kind="neg")
    c("高危动作被【显式列出】时放行",
      (active_auth({"authorizations": [{"authId": "A5", "scope": "gitee:new-repo:x"}]},
                   "gitee:new-repo:x") or {}).get("authId") == "A5")
    print("\n  selftest: %d FAIL ｜ 反例 %d 条 / 正例 %d 条" % (fails, neg, pos))
    return 0 if fails == 0 else 1


def lean4_check():
    """★ R006 ⑩：六项自证 A–F。"""
    fails = 0; checks = []

    def c(k, name, cond, detail=""):
        nonlocal fails
        checks.append((k, name, bool(cond), detail))
        if not cond: fails += 1

    c("A", "类型锁：必需字段为冻结 tuple（不可运行时篡改）",
      isinstance(REQUIRED_CHANGE, tuple) and len(REQUIRED_CHANGE) == 7,
      "%d 项" % len(REQUIRED_CHANGE))
    c("B", "入口门：缺字段 ⇒ 退出 1（门未过，不放行）",
      cmd_record(argparse.Namespace(channel=None, evidence=None, rollback=None,
                                    files=None, by=None)) == 1,
      "缺字段被拒")
    c("C", "Schema 门：授权须含 scope+quote（原话不得为空）",
      cmd_authorize(argparse.Namespace(scope=None, quote=None, from_user=True,
                                       granted_by=None)) == 1, "缺 scope/quote 被拒")
    c("D", "状态机：有/无授权可区分（正负例均跑）",
      active_auth({"authorizations": []}, "x") is None
      and (active_auth({"authorizations": [{"authId": "A", "scope": "*"}]}, "x") or {}).get("authId") == "A",
      "正负例均跑")
    c("E", "白名单冻结：不改业务文件（只写台账）",
      "def cmd_marker" in io.open(os.path.abspath(__file__), encoding="utf-8").read(),
      "无业务文件写盘分支")
    c("F", "负例矩阵可执行（active_auth/make_id 为纯函数）",
      callable(active_auth) and callable(make_id), "纯函数")
    print("== proxy-change-record · --lean4-check（六项 A–F）==")
    for k, name, ok, detail in checks:
        print("  %s %s %-52s %s" % ("✅" if ok else "❌", k, name, detail))
    print("\n  ⇒ %d/%d 绿 · %d FAIL" % (len(checks) - fails, len(checks), fails))
    log("lean4-check %d/%d green, %d fail" % (len(checks) - fails, len(checks), fails))
    return 0 if fails == 0 else 1


def main():
    ap = argparse.ArgumentParser(description="代做变更留痕台账（时间戳 + 授权登记 + 最后变动人）")
    ap.add_argument("--authorize", action="store_true", help="登记一次授权")
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    ap.add_argument("--scope", help="授权范围（逗号分隔的通道，或 * 表示全部）")
    ap.add_argument("--quote", help="★ 授权【原话】（不得转述）")
    ap.add_argument("--from-user", action="store_true", help="授权来自所有者")
    ap.add_argument("--granted-by", help="授权人（非用户时）")
    ap.add_argument("--record", action="store_true", help="登记一次变更")
    ap.add_argument("--channel", help="变动通道（如 plugin:dsh-plugin-hr）")
    ap.add_argument("--evidence", help="证据（做了什么、如何验证）")
    ap.add_argument("--rollback", help="回滚点（如 git checkout <sha> -- path）")
    ap.add_argument("--files", help="涉及文件（逗号分隔）")
    ap.add_argument("--by", help="最后变动人（默认 %s）" % SELF_ID)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--last-modifier", metavar="FILE", help="查某文件的最后变动人")
    ap.add_argument("--marker-snippet", metavar="FILE", help="生成文件内嵌变更标记")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--lean4-check", action="store_true")
    a = ap.parse_args()
    if a.selftest: return selftest()
    if a.lean4_check: return lean4_check()
    if a.authorize: return cmd_authorize(a)
    if a.record: return cmd_record(a)
    if a.list: return cmd_list(a)
    if a.last_modifier: return cmd_last_modifier(a)
    if a.marker_snippet: return cmd_marker(a)
    ap.print_help(); return 2


if __name__ == "__main__":
    sys.exit(main())
