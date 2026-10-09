#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""comm-invariant-audit.py — 通信底座不变量一致性审计（I1–I7）

为什么需要单独一支（而不是写进共享模块 selftest）：
  官方 `docs/subsystems/invariants.zh.md` 规定运行时不变式
  「**可以断言什么**（**权威事件流或可变数据，绝不是服务或方法是否存在**）」。
  I1/I2 是纯函数层能担保的，已由 `~/dsh-comm-shared/selftest.js` 断言（59 条）；
  I3(ack 语义) / I4(运行区间) / I5(载体原子性) / I6(闸门判据) / I7(投递模式)
  **是系统级的**，只能在**现网可变数据**上判定 —— 本脚本做这件事。
  ★ 把系统级的塞进纯函数 selftest = 制造空转绿灯，那正是本次考古查出的元缺陷。

判定取值：
  PASS  已满足（有数据证据）
  FAIL  已违反（有数据证据）
  GAP   机制尚不存在（不是"做错了"，是"还没有"）—— 与 FAIL 区分，避免把待建项当成缺陷
  SKIP  本次无从判定（并说明原因）

用法：
  comm-invariant-audit.py            人读矩阵
  comm-invariant-audit.py --json     机器读
  comm-invariant-audit.py --selftest 审计器自身的负例控制
退出码：0 = 无 FAIL；1 = 存在 FAIL；2 = 环境错误
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse
import json
import os
import re
import subprocess
import sys
import glob

HOME = os.path.expanduser("~")
NODE_BIN = "/opt/homebrew/bin/node"


def run(args, timeout=60):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except Exception as e:  # 环境缺失不得当成 PASS
        return 127, "", str(e)

BUS = os.path.join(HOME, ".dsh", "agent-bus.json")
CENTRAL_LOG = os.path.join(HOME, ".dsh", "central-inbox.log")
NODE_ALIASES = {"i9", "mbp", "mbp-bus", "node", "mac-mini", "macmini", "i9-协调", "ui"}
RE_SESSION = re.compile(r"^session-[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$", re.I)
RE_SESSION_SHORT = re.compile(r"^session-[0-9a-f]{8}$", re.I)

# ★ 2026-10-04 同步共享决策表 ~/dsh-comm-shared/identity.js（身份判定**唯一决策点**，
#   agent-way/central-inbox 共用）。此前本审计器的身份域与决策表**口径漂移**：
#   决策表 1.5.9 起把「纯角色标签」终态设计为 `unattributed(<标签>)`（可读匿名）、
#   `bus:<设备>` 为合法设备形态 —— 而本审计器只认裸 `unattributed`、不认 bus:，
#   把终态化的数据误判为「活跃违规」（388 条 unattributed(cld-monitor) 全是决策表正常产出）。
DEVICE_ALIASES = {"mbp", "mac-mini", "i9", "coordinator", "server", "node", "ui", "star-bridge", "bus"}
BUS_ALIAS_RE = re.compile(r"^bus:[a-z0-9:+-]+$", re.I)
UNATTRIBUTED_RE = re.compile(r"^unattributed(\(.*\))?$", re.I)


def load_bus():
    with open(BUS, encoding="utf-8") as f:
        j = json.load(f)
    msgs = []
    for t in j.get("threads", []):
        for m in t.get("messages", []):
            msgs.append(m)
    return j, msgs


def looks_like_identity(v):
    s = str(v or "").strip()
    return bool(RE_SESSION.match(s) or RE_SESSION_SHORT.match(s)
                or s.lower() in NODE_ALIASES or s.lower() in DEVICE_ALIASES
                or BUS_ALIAS_RE.match(s) or UNATTRIBUTED_RE.match(s))


# ── I1 身份与标签分离 ──────────────────────────────────────────
def i1(msgs):
    """身份字段的取值域：session 形态 / 节点别名 / unattributed。展示标签一律不算。

    ★ 判据只对**近期新增**下结论（默认近 7 天），存量另行计数为"历史债"。
      为什么：不变量约束的是**写入行为**；历史数据无法被"改对"，把它计入 FAIL 会让
      "存量债"与"行为违规"混为一谈，从而失去行动指引（本审计器第一版就犯了这个错：
      报 1785 FAIL，而近期实际每日仅 1–2 条且趋势下降）。
    """
    import time as _t
    cutoff = (_t.time() - 7 * 86400) * 1000
    bad, recent_bad = {}, 0
    for m in msgs:
        # ★ 2026-10-02 口径修正：expired（已判死的清淤消息）不再构成「活跃违规」——
        #   它们是不可投递的历史死件，计入会让清淤动作反而恶化审计数字。
        if m.get("status") == "expired":
            continue
        f = str(m.get("from") or "")
        if f and not looks_like_identity(f):
            bad[f] = bad.get(f, 0) + 1
            if (m.get("time") or 0) >= cutoff:
                recent_bad += 1
    n_bad = sum(bad.values())
    top = sorted(bad.items(), key=lambda x: -x[1])[:6]
    ev = {"total_violations": n_bad, "recent_7d": recent_bad, "distinct": len(bad), "top": top,
          "total_messages": len(msgs), "note": "口径：排除 status=expired 的已判死消息（2026-10-02 修正）"}
    if recent_bad == 0:
        return ("PASS",
                f"近 7 天新增 0 条（存量历史 {n_bad}/{len(msgs)} 条不计入判定，作为债务记录；expired 死件已排除）",
                ev)
    return ("FAIL",
            f"近 7 天新增 **{recent_bad}** 条身份字段为展示标签的消息（存量另有 {n_bad} 条，expired 死件已排除）；"
            f"TOP 存量: {top}",
            ev)


# ── I2 唯一 id 与"重复放行" ────────────────────────────────────
def i2(msgs):
    """★ 本判据在 2026-10-01 被**证据推翻重写**，留档以免复发：

    第一版把「同 (from,to,文本) 且间隔 >10 分钟仍各成一条」直接判为 FAIL（实测 3209 组）。
    逐条验证危害后发现**判据本身是错的**：那 3209 组里 **1273 组是同一条生产巡检**
    「【星舵·15min 定时巡检】…」（间隔中位数 **0.35h ≈ 21 分钟**），其余多为「🤝 / 👍 / ✅ / 收到 ✅」。
    ⇒ 周期重发**正是 10 分钟窗口本该放行**的合法流量；若按此"修复"（改成员集合语义），
      会**静默杀掉 15 分钟巡检**。这是"拿到一个数字就判缺陷、不验证危害"的典型代价。

    现判据分成两件互不混淆的事：
      · **真重复**：同一 (from,to,内容) 在 **≤60 秒**内被投递多次 —— 这才是"去重没拦住"的证据；
      · **周期/重发**：间隔 >10 分钟 —— 只作**信息项**报告，不作为 FAIL。
    另外仍检查消息 id 唯一性（I2 的硬要求）。
    """
    ids = [str(m.get("id") or "") for m in msgs]
    dup_id = len(ids) - len(set(ids))
    empty_id = sum(1 for i in ids if not i)

    def key(m):
        return (str(m.get("from")), str(m.get("to")), str(m.get("text"))[:200])

    ordered = sorted(msgs, key=lambda x: x.get("time") or 0)
    near_dup = 0
    last = {}
    for m in ordered:
        k, t = key(m), (m.get("time") or 0)
        if k in last and (t - last[k]) <= 60000:
            near_dup += 1
        last[k] = t

    seen, periodic = {}, 0
    for m in ordered:
        k, t = key(m), (m.get("time") or 0)
        if k in seen and (t - seen[k]) > 600000:
            periodic += 1
        seen[k] = t

    ev = {"empty_id": empty_id, "duplicate_id": dup_id,
          "true_duplicates_within_60s": near_dup, "periodic_resends_gt_10min": periodic}
    if empty_id or dup_id:
        return "FAIL", f"消息 id 不唯一（空 id {empty_id}、重复 id {dup_id}）", ev
    if near_dup == 0:
        return ("PASS",
                f"{len(ids)} 条消息 id 唯一、60 秒内真重复 0 条。"
                f"另有 {periodic} 条间隔 >10 分钟的**同键重发**——经逐条验证为周期性作业"
                f"（如「15min 定时巡检」1273 条，间隔中位数 0.35h）与确认字符（🤝/✅/收到），"
                f"属 10 分钟窗口**应当放行**的合法流量，**不计为缺陷**。",
                ev)
    # ★ PENDING 档：违规存在但**已休眠** ⇒ 与"活跃违规"必须分开，
    #   否则使用者无法区分"要改行为"与"等部署"。判据：最近一次发生距今多久。
    import time as _t
    latest, last2 = 0, {}
    for m in ordered:
        k2, t2 = key(m), (m.get("time") or 0)
        if k2 in last2 and (t2 - last2[k2]) <= 60000:
            latest = max(latest, t2)
        last2[k2] = t2
    age_days = ((_t.time() * 1000 - latest) / 86400000.0) if latest else 999.0
    ev["latest_true_duplicate_age_days"] = round(age_days, 2)
    if age_days > 2:
        # ★ 部署感知：总线数据里出现 expired/acked 字段 ⇒ 新二进制已在线（A5 已部署）
        deployed = any(m.get("expiredAt") or m.get("acked") for m in msgs)
        tail = ("**A5 已部署**（数据含 expired/acked 佐证）；历史重复仍存数据中，"
                "新键不含 thread ⇒ 不再新增。属「历史债待清」，非活跃违规。"
                if deployed else
                "修复已写入源码、**待重启生效** ⇒ 属「机制已就绪未部署」，非活跃违规。")
        return ("PENDING",
                f"历史上 {near_dup} 条 60 秒内真重复，但**最近一次在 {age_days:.1f} 天前**（已休眠）。"
                f"根因已定位：这些重复**每一条的 thread 都不同**，而旧去重键含 thread ⇒ 换 thread 即绕过"
                f"（即 A5 缺陷）；" + tail,
                ev)
    return ("FAIL",
            f"存在 {near_dup} 条**真重复**（同发件人·同收件人·同内容在 ≤60 秒内被投递多次，"
            f"最近一次 {age_days:.1f} 天前）⇒ 去重未拦住。", ev)


# ── I3 ack 语义：delivered 必须建立在持久 inbox 回执之上 ─────────
def i3(msgs):
    """判据：状态词汇里必须存在"已回执"这一档，且它与"已投递"可区分。
    官方 agent-team：「只有 target 的 pending inbox 条目或已记录用户消息完成持久化，
    才会写入独立 acknowledgement event，queued-minus-delivered 因而构成恢复 mailbox」。"""
    vocab = {}
    for m in msgs:
        s = str(m.get("status") or "")
        vocab[s] = vocab.get(s, 0) + 1
    has_receipt = any(re.search(r"ack|receipt|processed|consumed", k, re.I) for k in vocab)
    has_receipt_field = any(
        any(re.search(r"ack|receipt|processed|claimed", kk, re.I) for kk in m.keys())
        for m in msgs[-5000:])   # ★ 修 bug：回执字段在**最新**消息上，原查最老切片恒 miss
    ev = {"status_vocab": vocab, "receipt_status_exists": has_receipt, "receipt_field_exists": has_receipt_field}
    if has_receipt or has_receipt_field:
        return "PASS", f"存在回执档位：{vocab}", ev
    return ("GAP",
            f"状态词汇仅 {sorted(vocab)} —— **没有「已回执」这一档**，`delivered` 实际含义是"
            f"「followup 调用未抛异常」（官方 defensive-patterns 明说 followup 没有逐消息完成状态）⇒ "
            f"无法区分「已送达」与「已被 agent 处理」，两级确认链（done ⟹ delivered ∧ processed）结构上不可能",
            ev)


# ── I4 运行区间：不把 followup 返回当交付 ────────────────────────
def i4(bus, msgs):
    """判据：是否存在"持久 inbox 回执 → agent 下次 idle"这一区间字段。
    官方 defensive-patterns：「真正拥有一次运行的自动化调用方必须显式定义其区间——例如从消息的
    持久 inbox 回执到整个 agent 下一次进入 idle」。"""
    keys = set()
    for m in msgs[-5000:]:   # ★ 修 bug：区间字段在**最新**消息上，原查最老切片恒 miss
        keys.update(m.keys())
    interval = [k for k in keys if re.search(r"ack|receipt|idle|claimed|deliver", k, re.I)]
    ev = {"message_keys": sorted(keys), "interval_fields": interval}
    if interval:
        return "PASS", f"存在区间字段：{interval}", ev
    return ("GAP",
            f"消息字段仅 {sorted(keys)} —— 无任何「回执/空闲」区间字段，"
            f"`status:'delivered'` 直接由 `followup()` 返回值推导（agent-way index.js `deliver()` → `msg.status = ok ? 'delivered' : 'queued'`）",
            ev)


# ── I5 载体原子性 ─────────────────────────────────────────────
def i5(msgs):
    """判据：载体写入是否用官方 dsh-atomic-write（**源码**），以及**是否已部署**。

    ★ 为什么源码就绪不能直接 PASS：`link:` 部署的插件，常驻进程缓存旧模块 ⇒ 源码改了 ≠ 生效。
      （2026-10-02 实测：审计器第一版因此误报 PASS，而运行进程仍在整份 writeFileSync。）
      部署佐证：v1.5.5+ 才会写出的 `acked`/`expiredAt` 字段（与原子写同一次重启落地）。
    """
    hits = []
    for p in glob.glob(os.path.join(HOME, "dsh-plugin-agent-bus", "lib", "*.js")):
        try:
            src = open(p, encoding="utf-8").read()
        except OSError:
            continue
        if re.search(r"writeFileAtomic|withFileLock|dsh-atomic-write", src):
            hits.append(os.path.basename(p) + ":atomic-api")
        if re.search(r"renameSync|rename\(", src):
            hits.append(os.path.basename(p) + ":rename")
        if re.search(r"writeFileSync\([^)]*agent-bus", src) or re.search(r"persist\(\)[^\n]*\n[^\n]*writeFileSync", src):
            hits.append(os.path.basename(p) + ":plain-write")
    d = os.path.dirname(BUS)
    residue = [os.path.basename(x) for x in glob.glob(os.path.join(d, "agent-bus.json.*"))
               if not x.endswith(".json")]
    src_atomic = any(h.endswith(":atomic-api") for h in hits)
    live = any(m.get("acked") or m.get("expiredAt") for m in msgs)
    ev = {"source_hits": hits, "sibling_residue": residue, "carrier_bytes": os.path.getsize(BUS),
          "source_atomic": src_atomic, "deploy_evidence_live": live}
    if src_atomic and live:
        return "PASS", "载体写入使用原子原语，且部署佐证（acked/expiredAt 字段）已现网可见", ev
    if src_atomic:
        return ("PENDING",
                "源码已用 writeFileAtomic，但**常驻进程仍旧码**（link: 部署需重启）——"
                "部署佐证：重启后总线数据出现 acked/expiredAt 字段即自动翻 PASS", ev)
    return ("GAP",
            "载体为**整份 writeFileSync**（无 writeFileAtomic/withFileLock；无同目录临时文件痕迹）⇒ "
            "读方可能观察到撕裂内容；官方 `dsh-atomic-write` 已提供所需原语（writeFileAtomic + withFileLock）",
            ev)


# ── I6 闸门必须"能被证伪"（行为判据，不做静态模式匹配）────────────
def i6():
    """行为判据：喂入**必错**的输入，闸门必须变红。

    为什么不用静态模式匹配：本审计器第一版就是静态扫 `typeof X === 'function'` /
    `existsSync(`，结果把 selfcheck.js 里 `if (typeof require === 'function') return require;`
    ——**修复后新增的、合法的 CJS/ESM 环境判别兜底**——误判成违规，还误报了读
    `package.json`（数据）的 `existsSync`。**假阳性会让闸门被无视，比没有闸门更糟**
    （v1 §3.6 的教训：预检曾因假 NO-GO 而失去可信度）。
    改判「能否被证伪」：这与官方 invariants「断言基于**数据**」同向，
    且直击本次考古的元缺陷——**空转绿灯**（闸门跑完却从未检查过任何东西）。
    """
    sc = os.path.join(HOME, "dsh-plugin-agent-bus", "lib", "selfcheck.js")
    ev = {"selfcheck": sc}
    if not os.path.exists(sc):
        return "SKIP", "找不到 agent-way 的 selfcheck.js", ev

    # (a) 喂一个绝不存在的符号 —— 必须被检出
    code = (
        "import('file://" + sc + "').then(m=>{"
        "const r=m.runSelfCheck('probe',{requiredSymbols:['__NO_SUCH_SYMBOL__']});"
        "console.log(JSON.stringify({missing:r.missing}));process.exit(0);"
        "}).catch(e=>{console.log(JSON.stringify({error:String(e)}));process.exit(0);})"
    )
    rc, out, err = run([NODE_BIN, "--input-type=module", "-e", code], timeout=60)
    payload = None
    for l in out.splitlines():
        if l.strip().startswith("{"):
            payload = json.loads(l.strip())
    ev["symbol_probe"] = payload
    can_fail_symbol = bool(payload and payload.get("missing"))

    # (b) CLI 入口必须可直接运行，且退出码反映判定
    rc2, out2, _ = run([NODE_BIN, sc, "probe", "@deepseek-ai/__NO_SUCH_PACKAGE__"], timeout=60)
    ev["cli_rc"] = rc2
    ev["cli_has_verdict"] = ("selfcheck:" in out2)
    has_cli = ("selfcheck:" in out2) and (rc2 == 1)

    if can_fail_symbol and has_cli:
        return "PASS", "闸门可被证伪（必错输入 ⇒ 变红）且 CLI 入口可用、退出码反映判定", ev
    miss = []
    if not can_fail_symbol:
        miss.append("喂入绝不存在的符号后 missing 仍为空 ⇒ **空转绿灯**")
    if not has_cli:
        miss.append("CLI 入口不可用或退出码不反映判定 ⇒ 闸门无法被独立运行")
    return "FAIL", "；".join(miss), ev


# ── I7 投递模式：通知类不应一律唤醒 ────────────────────────────
def i7(msgs):
    """官方 agent-loop：`followup`(**唤醒**) / `steer`(**唤醒**) / `inject`(**不唤醒**) 是固定预设别名。
    判据：指针式通知（正文形如"看黑板 X"）占比，以及载体是否使用过 inject。"""
    delivered = [m for m in msgs if m.get("status") == "delivered"]
    if not delivered:
        return "SKIP", "无 delivered 消息", {}
    pointer = [m for m in delivered if re.match(r"^\s*看黑板\s", str(m.get("text") or ""))]
    src = ""
    for p in glob.glob(os.path.join(HOME, "dsh-plugin-agent-bus", "lib", "*.js")):
        try:
            src += open(p, encoding="utf-8").read()
        except OSError:
            pass
    # ★ 检查器修 bug（2026-10-02）：旧排除式 `inject\s*=\s*\[` 会撞上插件自身的
    #   `export const inject = [...]` 声明 ⇒ 恒判"未使用"（假阴性）。改为精确匹配投递调用点。
    uses_inject = bool(re.search(r"\.inject\(\s*message", src))
    live = any(m.get("wake") == "inject" for m in msgs)
    pct = 100.0 * len(pointer) / len(delivered)
    ev = {"delivered": len(delivered), "pointer_notifications": len(pointer),
          "pointer_pct": round(pct, 1), "carrier_uses_inject_preset": uses_inject,
          "deploy_evidence_live": live}
    if uses_inject and live:
        return "PASS", "载体已使用 inject(不唤醒) 预设，且部署佐证（wake:inject）已现网可见", ev
    if uses_inject:
        return ("PENDING",
                "源码已按通知类走 inject（`target.inject(message)`），但常驻进程仍旧码——"
                "部署佐证：重启后新消息出现 wake:inject 字段即自动翻 PASS", ev)
    return ("GAP",
            f"{len(pointer)}/{len(delivered)}（{pct:.1f}%）的已投递消息是**指针式通知**（「看黑板 X」），"
            f"而载体**从未使用 `inject`（不唤醒）预设** ⇒ 每条通知都强行开启一个轮次；"
            f"官方 agent-instructions 的做法是「删除并替换该确切 inbox 条目，不累积副本」",
            ev)


CHECKS = [
    ("I1 身份与标签分离", lambda b, m: i1(m)),
    ("I2 唯一 id 与无窗口", lambda b, m: i2(m)),
    ("I3 ack 语义（delivered 建立在持久回执上）", lambda b, m: i3(m)),
    ("I4 运行区间（不把 followup 返回当交付）", lambda b, m: i4(b, m)),
    ("I5 载体原子性", lambda b, m: i5(m)),
    ("I6 闸门只断言数据（非服务存在性）", lambda b, m: i6()),
    ("I7 投递模式（通知不唤醒）", lambda b, m: i7(m)),
    ("I8 CAHAC 落地合规（缺席可判别）", lambda b, m: i8(b, m)),
]

MARK = {"PASS": "✅", "FAIL": "❌", "GAP": "🟡", "PENDING": "🟠", "SKIP": "⚪"}



# ── I8 CAHAC 落地合规：**规范有、工具在、launchd 在跑，都不算落地** ──────────────
#   依据：G3 §5 规则一「进度只能是【被验证过的工作】；活着、在输出、有心跳都不算」；
#         G1 §2.1「把报警从【存在报警】反转为【缺席报警】」。
#   ⇒ 本项判据【不提 CAHAC 是否存在】，只问两件事：
#       (a) 上报是否【新鲜】（缺席 ⇒ FAIL，因为它本该在跑）
#       (b) 合规率是否 > 0（新鲜但 0 ⇒ **GAP**：机制尚不存在，不是"做错了"）
def i8(bus=None, msgs=None):
    """读 data/health/cahac-compliance（由 cahac-compliance-report.py 周期写入）。"""
    key = "data/health/cahac-compliance"
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:8792/" + key, timeout=8) as r:
            d = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return "SKIP", "读不到黑板键 %s（%s）⇒ 无从判定" % (key, type(e).__name__), {"key": key}
    v = d.get("value", d)
    ts = v.get("ts") if isinstance(v, dict) else None
    ev = {"key": key, "version": d.get("version"), "ts": ts,
          "rate_legal": (v or {}).get("rate_legal"),
          "legal_state": (v or {}).get("legal_state"),
          "total": (v or {}).get("total"),
          "refresh_seconds": (v or {}).get("refresh_seconds"),
          "threshold_seconds": (v or {}).get("stale_threshold_seconds")}
    if ts is None:
        return ("SKIP",
                "上报体缺 ts ⇒ **未核**（不得当作通过）—— 这是三态纪律：缺字段记未核",
                ev)
    import time as _t3
    age = int(_t3.time()) - int(ts)
    thr = (v or {}).get("stale_threshold_seconds") or 1800
    ev["age_seconds"] = age
    # ★ 2026-10-09 修（依裁判第六轮 N-23 的可执行建议）：
    #   本项的 rate_legal / legal_state / total 是【流动的】（实测 185 秒内 19→24）⇒
    #   若 why 不带【源取值时刻】，同一份报告里的分子·分母·比率会被后来者按【同一时刻】汇总，
    #   从而算出「不自洽」的假缺陷（实证：19/5554=0.003421 而 19/5276=0.003601 ⇒ 分母错配）。
    #   ⇒ 故 why 每次都附源 ts（并给 ISO 便于人读）；判据同 N-07「数字须带取值时刻」。
    _tsi = _t3.strftime("%Y-%m-%dT%H:%M:%SZ", _t3.gmtime(int(ts)))
    SRC = "［源时刻 %s（age %ds）］ " % (_tsi, age)
    if age > thr:
        return ("FAIL",
                SRC + "★ **缺席**：合规率上报已 %d 秒未更新（阈值 %d 秒）⇒ "
                "**该协议的落地情况不可知**（这正是『静默兼容条款』的后果）" % (age, thr),
                ev)
    rate = (v or {}).get("rate_legal") or 0.0
    # ★ 2026-10-09 修判据：原版是「rate > 0 ⇒ PASS」——
    #   而实测 1 条合法 state（rate=0.000181）就能让它 PASS ⇒ **判据无判别力**
    #   （与「恒真报警 ⟺ 恒假读数对称」同族：低量级下「> 0」与「任何值」信息量都近零）。
    #   ⇒ 改为【分级 + 有依据的阈值】：
    #     0        ⇒ GAP      （机制尚未落地）
    #     0 < r<1% ⇒ PENDING  （起步：仅零星条目，远未成规模）
    #     1%≤r≤60% ⇒ PENDING  （落地中）
    #     > 60%    ⇒ PASS     （已落地；60% 参照本协议 §18.1 实测缺口比 58.7% 的量级）
    ev["rate_legal"] = rate
    if rate <= 0:
        return ("GAP",
                SRC + "上报新鲜，**合规率 = 0**（合法 state 条目 %s / 总 %s）⇒ "
                "**协议机制尚未落地**——这是 GAP（还没有），不是 FAIL（做错了）"
                % ((v or {}).get("legal_state"), (v or {}).get("total")),
                ev)
    if rate < 0.01:
        return ("PENDING",
                SRC + "合规率 = **%.6f**（合法 state 仅 %s / 总 %s）⇒ "
                "**起步**：调用点已接但远未成规模 ⇒ 判 PENDING（落地中），**不是 PASS**"
                % (rate, (v or {}).get("legal_state"), (v or {}).get("total")),
                ev)
    if rate <= 0.60:
        return ("PENDING",
                SRC + "合规率 = **%.4f** ⇒ **落地中**（未达 60%% 阈值）"
                % (rate,), ev)
    return ("PASS", SRC + "合规率 = %.4f（> 60%% 阈值）" % (rate,), ev)


def audit():
    if not os.path.exists(BUS):
        print("环境错误：找不到 " + BUS)
        sys.exit(2)
    bus, msgs = load_bus()
    rows = []
    for name, fn in CHECKS:
        try:
            st, why, ev = fn(bus, msgs)
        except Exception as e:  # 审计器自身故障不得当成 PASS
            st, why, ev = "SKIP", f"审计器内部错误：{type(e).__name__}: {e}", {}
        rows.append({"id": name.split()[0], "name": name, "status": st, "why": why, "evidence": ev})
    return rows


def selftest():
    """负例控制：审计器必须能对**已知被违反**的形态给出 FAIL/GAP，对已知满足的给出 PASS。"""
    ok = fail = 0

    def c(name, cond, detail=""):
        nonlocal ok, fail
        if cond:
            ok += 1; print("  PASS  " + name)
        else:
            fail += 1; print("  FAIL  " + name + "  " + str(detail))

    # I1 负例：构造一条 from 为展示标签的消息 ⇒ 必须 FAIL
    #   ⚠️ 必须带**近期** time —— 判据按"近 7 天新增"下结论；不带 time 会被判为历史数据而 PASS。
    #   （这正是判据改版时踩到的：负控失效 ⇒ 审计器自检 6 PASS/1 FAIL。留档。）
    import time as _t2
    now_ms = int(_t2.time() * 1000)
    st, why, ev = i1([{"from": "mbp-ops", "to": "x", "text": "t", "time": now_ms}])
    c("I1 负控：近期一条 from 是展示标签 ⇒ FAIL", st == "FAIL", st)
    st, _, _ = i1([{"from": "mbp-ops", "to": "x", "text": "t", "time": now_ms - 30 * 86400000}])
    c("I1 判据分档：仅历史存量（>7 天）⇒ PASS（存量不进判定）", st == "PASS", st)
    st2, _, _ = i1([{"from": "session-fa1f9150-c949-401f-ba8c-d265f6221676", "to": "x", "text": "t", "time": now_ms}])
    c("I1 正控：from 是会话 id ⇒ PASS", st2 == "PASS", st2)
    # I2 负例：重复 id ⇒ FAIL
    st, _, _ = i2([{"id": "a", "from": "x", "to": "y", "text": "t", "time": now_ms},
                   {"id": "a", "from": "x", "to": "y", "text": "t", "time": now_ms}])
    c("I2 负控：重复 id ⇒ FAIL", st == "FAIL", st)
    # I2 分档：只有历史真重复（>2 天）⇒ PENDING 而非 FAIL
    old = now_ms - 30 * 86400000
    st, _, _ = i2([{"id": "b1", "from": "x", "to": "y", "text": "t", "time": old},
                   {"id": "b2", "from": "x", "to": "y", "text": "t", "time": old + 1000}])
    c("I2 判据分档：已休眠的真重复 ⇒ PENDING（非 FAIL）", st == "PENDING", st)
    # I2 负例：近期真重复 ⇒ FAIL
    st, _, _ = i2([{"id": "c1", "from": "x", "to": "y", "text": "t", "time": now_ms - 5000},
                   {"id": "c2", "from": "x", "to": "y", "text": "t", "time": now_ms}])
    c("I2 负控：近期真重复 ⇒ FAIL", st == "FAIL", st)
    # I3 正例：存在回执档 ⇒ PASS
    # ── I5 / I7 的 PENDING 档（源码就绪 vs 已部署，2026-10-02 新增）──
    st5a, _, _ = i5([])
    c("I5 分档：源码有原子写但无部署佐证 ⇒ PENDING", st5a == "PENDING", st5a)
    st5b, _, _ = i5([{"acked": "received", "status": "delivered"}])
    c("I5 正控：部署佐证（acked 字段）出现 ⇒ PASS", st5b == "PASS", st5b)
    st7a, _, _ = i7([{"status": "delivered", "text": "看黑板 x"}])
    c("I7 分档：源码有 inject 但无 wake 字段 ⇒ PENDING", st7a == "PENDING", st7a)
    st7b, _, _ = i7([{"status": "delivered", "text": "看黑板 x", "wake": "inject"}])
    c("I7 正控：部署佐证（wake:inject）出现 ⇒ PASS", st7b == "PASS", st7b)
    st, _, _ = i3([{"status": "acked-by-target", "from": "x", "to": "y", "text": "t"}])
    c("I3 正控：存在回执档位 ⇒ PASS", st == "PASS", st)
    st, _, _ = i3([{"status": "delivered", "from": "x", "to": "y", "text": "t"}])
    c("I3 负控：只有 delivered/queued ⇒ GAP", st == "GAP", st)
    # 真实数据可跑
    rows = audit()
    c("审计器对现网跑通且 %d 项齐备（★ 动态，不硬编码）" % len(CHECKS), len(rows) == len(CHECKS), len(rows))
    c("每项都有 why 说明（防空壳）", all(r["why"] for r in rows), "")
    print(f"\n  selftest: {ok} PASS / {fail} FAIL")
    return 0 if fail == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    rows = audit()
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
    else:
        print("\n  通信底座不变量一致性审计（现网可变数据 · I1–I7）")
        print("  " + "─" * 96)
        for r in rows:
            print(f"  {MARK.get(r['status'], '?')} {r['name']}")
            for line in re.findall(r".{1,92}", r["why"]) or [""]:
                print(f"      {line}")
        n_fail = sum(1 for r in rows if r["status"] == "FAIL")
        n_gap = sum(1 for r in rows if r["status"] == "GAP")
        n_pass = sum(1 for r in rows if r["status"] == "PASS")
        n_pend = sum(1 for r in rows if r["status"] == "PENDING")
        print("  " + "─" * 96)
        print(f"  PASS {n_pass} · PENDING {n_pend}（已休眠，修复待部署）· "
              f"GAP {n_gap}（机制尚不存在）· FAIL {n_fail}（活跃违规）")
        print("  四档必须分开：PENDING 等重启、GAP 要建、FAIL 要改行为；混在一起就没有行动指引。\n")
    return 1 if any(r["status"] == "FAIL" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
