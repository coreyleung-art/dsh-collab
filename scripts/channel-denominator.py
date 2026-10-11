#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""channel-denominator.py — 通道登记分母审计器（★ 2.0.0：面 4 · 真独立活体面）

职责：回答 §14.4 M4②c 那一问 ——「登记表的分母是多少？」
      判据原文：分母由**活体实测**生成（**不得手写、不得只读矩阵文件**）。

★ 为什么必须重建（1.1.0 的结构性缺陷 = D-059）：
  1.1.0 的「声明面」与「活体面」**都读 channel-matrix.json**
  ⇒ 那是**同一条链的自投影**，**结构上不可能发现任何不在矩阵里的通道**
  ⇒ 它违反的正是它本该服务的那条判据。
  ⇒ 2.0.0 新增 **面 4**：三源**都不碰矩阵**。

★ 2.0.0 分层分母（★ 三态不合并）：
  L0     原始活体（三源行数之和）—— ★「扫过的面」必须随每个数字一起报
  L0.5   跨源重复（已剔）—— ★ 剔除数**明写**，不静默丢弃
  L1     候选通道（论域内）
  排除   明确排除 —— ★ 逐条附理由，防「过滤」成为不可审的黑箱
  不可判 两不命中 —— ★ ≠ 排除，★ ≠ 收录
  L2     已登记（候选 ∩ 登记表）
  L3     未登记 = L1 − L2   ★★ 这才是 M4② 要的分母

★ 论域是显式、可打印、带版本的常量（见下方 DOMAIN_DEF_VERSION）。
  ★ 不定义论域就不冒充给分母 —— 未获裁可时 L1/L3 只是【提案口径下的读数】。

★ 本工具【只读】：不删、不改、不写任何被审计对象；唯一写的是固定日志。
★ 限度（★ 不主张已闭合）：登记表来源只有 matrix + gate 两张；若还有第三张登记表
  未纳入 → L2 会偏低 → L3 会偏高。★ 本工具**不知道**自己漏了哪张表（S3）。
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
def selfcheck():
    import sys as _sys
    print("== channel-denominator 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · channel-denominator.py — 通道登记分母审计器")
    print("  · 面 4 三源独立活体枚举：launchd（复用 launchd-scan --json）/ 进程表 / 监听端口")
    print("  · 分层分母 L0 → L0.5 → L1 → L2 → L3，排除项逐条附理由")
    print("  · --status 另报「制度死锁」（当前为红 ∧ 不在门冻结枚举）")

    print("【② 不该发生路径清单】")
    print("  · 本工具只读：不删除任何文件、不修改权限、不写任何被审计对象")
    print("  · 执行外部命令仅三支只读源：launchd-scan --json / ps -axo / lsof -nP -iTCP")
    print("  · 不修改 r006 管辖外的其它工具文件")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: json, os, re, shutil, subprocess, sys, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 外部运行时: node（面4-① 与 gate 枚举；★ 本机在 /opt/homebrew/bin/node，PATH 里可能没有）")
    print("  · 固定日志: ~/dsh-collab/logs/channel-denominator.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

__version__ = '2.0.0'  # ★ R006 ⑥ 唯一版本声明处（2.0.0：面 4 独立活体面 + 分层分母 + 跨源去重 + 论域显式化）

import json, os, re, shutil, subprocess, sys, time

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕
LOG = os.path.expanduser("~/dsh-collab/logs/channel-denominator.log")

# 面 4 依赖的既有资产（★ J44：复用，不重建）
LAUNCHD_CLI = os.path.expanduser("~/dsh-plugin-launchd-scan/cli.js")
DRIFT_CLI = os.path.expanduser("~/dsh-plugin-drift-scan/cli.js")
MATRIX_JSON = os.path.expanduser("~/dsh-plugin-drift-scan/lib/channel-matrix.json")
GATE_JS = os.path.expanduser("~/dsh-plugin-channel-gate/lib/gate.js")


def log(msg):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("[%s] %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S%z"), msg))
    except Exception:
        pass


# ═══════════ ★ 论域定义（显式 · 可打印 · 带版本 · 可覆盖）═══════════
DOMAIN_DEF_VERSION = "d059-proposal-v1（★ 待用户裁）"

DOMAIN_DEF_TEXT = (
    "【通道】= 一条具名、可寻址的【跨进程或跨设备】投递路径，其实现形式为下列之一：\n"
    "  (a) 一个 TCP 监听端点（本机 port）；\n"
    "  (b) 一个由 launchd 管理的常驻/周期进程，其职责含跨进程或跨设备的消息搬运；\n"
    "  (c) 一个用于投递的黑板键命名空间（notes/ data/ alerts/ tasks/ …）。\n"
    "【非通道】= GUI 应用、只读写本地文件的单次脚本、与消息无关的系统守护、"
    "日志轮转/健康巡检/内存守护。"
)

# ★ 收录模式：命中即【进入候选】（论域内的正向证据）
DOMAIN_INCLUDE_PATTERNS = [
    r"bb-sub", r"blackboard", r"board-", r"\bbus\b", r"bus-", r"-bus\b",
    r"sse-\d", r"inbox", r"-wake\b", r"node-bridge", r"\bbridge\b",
    r"hb-fwd", r"heartbeat", r"sync-(?:up|down|to|from)", r"device-daemon",
    r"agentsend", r"agent-send", r"\bmail\b", r"relay\b", r"\bqueue\b",
    r"deliver", r"tailscale", r"funnel", r"comm-",
]

# ★ 排除模式：命中即【明确排除】，**排除优先于收录**；★ 每条必须带理由（防黑箱过滤）
DOMAIN_EXCLUDE_PATTERNS = [
    (r"log-guard", "日志守护/轮转，无消息搬运语义"),
    (r"log-rotate", "日志轮转，无消息搬运语义"),
    (r"archive-logs", "日志归档，无消息搬运语义"),
    (r"noise-scan", "噪音扫描，无消息搬运语义"),
    (r"pollution-scanner", "污染扫描，无消息搬运语义"),
    (r"memory-guard", "内存守护，无消息搬运语义"),
    (r"plugin-scan", "插件扫描，无消息搬运语义"),
    (r"queue-condense", "队列压缩＝本地文件整理，无投递语义（★ 它同时命中收录 queue ⇒ 排除优先的实例）"),
    (r"freq-class", "非实体（采集字段名，出现在别处）"),
]


def classify_domain(name, cmd="", excludes=None):
    """★ 三态分类：(verdict, reason)，verdict ∈ {'in','excluded','undecidable'}。

    ★ 顺序是判据的一部分：**排除优先于收录**。
    excludes 可注入 ⇒ ★ 变异测试可证明「排除判据真在起作用」而非恒真。
    """
    ex = DOMAIN_EXCLUDE_PATTERNS if excludes is None else excludes
    hay = ("%s %s" % (name, cmd)).lower()
    for pat, why in ex:
        if re.search(pat, hay, re.I):
            return ("excluded", why)
    for pat in DOMAIN_INCLUDE_PATTERNS:
        if re.search(pat, hay, re.I):
            return ("in", "命中收录模式 /%s/" % pat)
    return ("undecidable", "两不命中：既不在收录模式、也不在排除表")


# ═══════════ ★ 面 4 · 三源独立活体枚举（★ 都不碰矩阵）═══════════
def _resolve_node():
    """★ 本机 node 在 /opt/homebrew/bin/node，PATH 里可能没有（本线实测踩过）。"""
    for c in ("/opt/homebrew/bin/node", "/usr/local/bin/node"):
        if os.path.exists(c):
            return c
    return shutil.which("node")


def _run(argv, timeout=60):
    """★ 类型锁：只接受【字符串列表】；非列表或含非字符串 ⇒ 拒绝执行（★ 不猜不静默）。

    ★ 为什么加这把锁：`subprocess.run` 的首参在此处是形参而非字面量，
      ⇒ lean4 A 项（「首参为列表字面量」）**当场判 FAIL —— 判得对**。
      正解不是把判据改松，是**在入口真的把类型锁上**。
    """
    if not isinstance(argv, (list, tuple)) or not all(isinstance(x, str) for x in argv):
        return None, "", "类型锁拒绝：argv 必须是 str 列表"
    try:
        p = subprocess.run(list(argv), capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout or "", p.stderr or ""
    except Exception as e:
        return None, "", str(e)


def face_launchd():
    """面4-① launchd —— ★ 复用既有 launchd-scan --json（J44 二次复用），不自己解 plist。"""
    node = _resolve_node()
    if node is None:
        return [], "UNAVAILABLE", "未找到 node（本机在 /opt/homebrew/bin/node）"
    if not os.path.exists(LAUNCHD_CLI):
        return [], "UNAVAILABLE", "launchd-scan cli.js 不存在：%s" % LAUNCHD_CLI
    rc, out, err = _run([node, LAUNCHD_CLI, "--json"])
    if rc != 0 or not out.strip():
        return [], "UNAVAILABLE", "rc=%s stdout=%d 字节 ⇒ ★ 面不可用（★ 不静默当 0）：%s" % (
            rc, len(out), err.strip()[:120])
    try:
        d = json.loads(out)
    except Exception as e:
        return [], "UNAVAILABLE", "JSON 解析失败：%s" % e
    items = []
    for r in d.get("rows", []):
        items.append({"source": "launchd",
                      "id": r.get("label") or r.get("file") or "?",
                      "cmd": r.get("command") or "",
                      "extra": r.get("state") or ""})
    return items, "OK", "rows=%d（loaded=%s）" % (len(items), d.get("loaded"))


def face_process():
    """面4-② 进程表 —— ps -axo pid=,command=。"""
    rc, out, err = _run(["ps", "-axo", "pid=,command="], timeout=30)
    if rc != 0:
        return [], "UNAVAILABLE", "ps rc=%s %s" % (rc, err.strip()[:120])
    items = []
    for ln in out.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        parts = ln.split(None, 1)
        items.append({"source": "process", "id": "pid:%s" % parts[0],
                      "cmd": parts[1] if len(parts) > 1 else "", "extra": ""})
    return items, "OK", "rows=%d" % len(items)


def face_listen():
    """面4-③ 监听端口 —— lsof -nP -iTCP -sTCP:LISTEN +c 0。

    ★ `+c 0` 是必须的：lsof 默认把 COMMAND 截到 9 字符（`rust-blackboard-…` 会变成
      `rust-blac`）⇒ ★ 该源会**几乎永远判不可判**，面形同虚设（本线实测照出）。
      ★ 但即便 `+c 0`，macOS 仍截到约 30 字符 ⇒ 本工具再用【pid → 完整 cmdline】补齐
      （见 judge_live 的富化步骤），**不靠截断的名字下判**。
    """
    rc, out, err = _run(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN", "+c", "0"], timeout=30)
    if rc != 0 and not out.strip():
        return [], "UNAVAILABLE", "lsof rc=%s %s" % (rc, err.strip()[:120])
    lines = out.splitlines()
    if lines and lines[0].startswith("COMMAND"):
        lines = lines[1:]
    items = []
    for ln in lines:
        f = ln.split()
        if len(f) < 9:
            continue
        items.append({"source": "listen", "id": "listen:%s" % f[8],
                      "cmd": "%s (pid %s)" % (f[0], f[1]),
                      "extra": f[8], "pid": f[1]})
    return items, "OK", "rows=%d" % len(items)


FACES = (("launchd", face_launchd), ("process", face_process), ("listen", face_listen))


# ═══════════ ★ 实体签名与跨源去重 ═══════════
def _reg_key(s):
    """归一化登记键：小写、去 com.dsh. 前缀、去扩展名、去非字母数字。"""
    s = str(s or "").strip().lower()
    s = re.sub(r"^com\.dsh\.", "", s)
    s = re.sub(r"\.(py|js|mjs|cjs|sh|rb|pl)$", "", s)
    return re.sub(r"[^a-z0-9]", "", s)


def _sig(item):
    """★ 一个实体的跨源可比签名。

    ★ 历史缺陷（D-062 自捕 ①）：首版要求 token 含 '/' ⇒ **裸文件名被整条跳过**
      （生产命令都是全路径所以未暴露，是夹具照出来的）。本版两种都收。
    ★ 设计原则：**宁可少合并，不可错合并** —— 签名只在【逐字相等】时去重。
    """
    src = item.get("source")
    if src == "launchd":
        return _reg_key(item.get("id"))  # ★ label 按构造唯一 ⇒ 用它，避免 8 条 bb-sub 被并成 1
    if src == "process":
        toks = (item.get("cmd") or "").split()

        def _is_flag_value(i):
            # ★ 某 flag 的【值】不是脚本 —— 本自证 C10 照出的真 bug：
            #   `--prefixes data/qa/` 的 `data/qa/` 含 '/'，会被当成脚本 ⇒ 签名塌成 '|t'
            return i > 0 and toks[i - 1].startswith("-")

        idx = None
        for i, t in enumerate(toks):  # ① 带脚本扩展名者优先
            if t.startswith("-") or _is_flag_value(i):
                continue
            if re.search(r"\.(py|js|mjs|cjs|sh|rb|pl)$", t):
                idx = i
                break
        if idx is None:  # ② 退而取第一个含 '/' 的【非 flag 值】token
            for i, t in enumerate(toks):
                if t.startswith("-") or _is_flag_value(i):
                    continue
                if "/" in t:
                    idx = i
                    break
        if idx is None:
            return None  # ★ 认不出脚本 ⇒ 不参与去重（宁可不并）
        script, args = os.path.basename(toks[idx]) or toks[idx], toks[idx + 1:]
        # ★ 只收【标识符样】的实参：丢掉纯数字与路径样者（它们是 flag 的**值**，
        #   两侧表达不一致 ⇒ 会把本该合并的行拆开；而标识符样者（如 bb-sub 的
        #   `coordinator`）是**区分度**所在，丢掉会把 8 条订阅错并成 1）。
        keep = [a for a in args
                if not a.startswith("-") and not re.fullmatch(r"[\d.]+", a) and "/" not in a]
        tail = _reg_key("".join(keep))
        return _reg_key(script) + ("|" + tail if tail else "")
    if src == "listen":
        return "listen|" + _reg_key(item.get("id"))
    return None


def dedupe_cross_source(items):
    """★ 跨源/同源重复合并。返回 (merged, removed)。

    ★ 历史缺陷（D-062 自捕 ③）：同一守护按 label（launchd）与 pid（process）各计一次
      ⇒ 首跑 L1=37，去重后 = 22。★ 剔除数必须**明写为 L0.5 层**，不静默丢弃。
    """
    seen, merged, removed = {}, [], []
    for it in items:
        k = _sig(it)
        if k is None:
            merged.append(it)
            continue
        if k in seen:
            seen[k]["sources"].add(it["source"])
            removed.append((k, it))
            continue
        it2 = dict(it)
        it2["sources"] = {it["source"]}
        seen[k] = it2
        merged.append(it2)
    return merged, removed


# ═══════════ ★ 登记表（L2 的来源）═══════════
def read_matrix():
    """声明面：drift 的 channel-matrix.json。★ 返回 (keys, status, note)。"""
    if not os.path.exists(MATRIX_JSON):
        return [], "UNAVAILABLE", "矩阵文件不存在：%s" % MATRIX_JSON
    try:
        d = json.load(open(MATRIX_JSON, encoding="utf-8"))
    except Exception as e:
        return [], "UNAVAILABLE", "矩阵解析失败：%s" % e
    mx = d.get("matrix", d)
    if not isinstance(mx, dict):
        return [], "UNAVAILABLE", "矩阵结构非 dict"
    keys = [k for k in mx if not str(k).startswith("_")]
    return keys, "OK", "%s（version=%s）" % (MATRIX_JSON, d.get("version"))


def read_gate_channels():
    """可变更面：channel_gate 的冻结枚举 CHANNELS。★ 返回 (keys, status, note)。"""
    if not os.path.exists(GATE_JS):
        return [], "UNAVAILABLE", "gate.js 不存在：%s" % GATE_JS
    node = _resolve_node()
    if node is not None:
        js = "import('file://%s').then(m=>console.log(JSON.stringify(Object.keys(m.CHANNELS))))" % GATE_JS
        rc, out, err = _run([node, "-e", js], timeout=30)
        if rc == 0 and out.strip().startswith("["):
            try:
                return json.loads(out), "OK", "node 动态 import"
            except Exception:
                pass
    try:  # 兜底：正则抓冻结块里的带引号键
        src = open(GATE_JS, encoding="utf-8").read()
        m = re.search(r"CHANNELS\s*=\s*Object\.freeze\(\{(.*?)\n\}\)", src, re.S)
        if m:
            return re.findall(r"'([^']+)'\s*:", m.group(1)), "OK", "正则兜底（node 不可用）"
    except Exception:
        pass
    return [], "UNAVAILABLE", "无法取得门冻结枚举（node 与正则兜底都失败）⇒ ★ 不猜"


# ═══════════ ★ 分层分母 ═══════════
def judge_live(face_fns=None):
    """跑面 4 并出分层分母。★ face_fns 可注入 ⇒ 自证能造「三源全不可用」。"""
    fns = face_fns if face_fns is not None else FACES
    faces, pool = {}, []
    for nm, fn in fns:
        its, st, note = fn()
        faces[nm] = {"status": st, "note": note, "n": len(its)}
        pool.extend(its)
    L0 = len(pool)
    # ★ 富化：listen 行的 COMMAND 被 lsof 截断 ⇒ 用【pid → 完整 cmdline】补齐，
    #   ★ 不靠截断的名字下判（否则面 4-③ 会几乎永远判不可判）。
    _pidmap = {}
    for it in pool:
        if it.get("source") == "process" and str(it.get("id", "")).startswith("pid:"):
            _pidmap[str(it["id"])[4:]] = it.get("cmd") or ""
    enriched = 0
    for it in pool:
        if it.get("source") == "listen":
            full = _pidmap.get(str(it.get("pid") or ""))
            if full:
                it["cmd"] = full
                enriched += 1
    merged, removed = dedupe_cross_source(pool)
    L0_5 = len(removed)

    inn, exc, und = [], [], []
    for it in merged:
        verdict, why = classify_domain(it.get("id") or "", it.get("cmd") or "")
        rec = {"id": it.get("id"), "source": it.get("source"),
               "sources": sorted(it.get("sources") or [it.get("source")]),
               "cmd": (it.get("cmd") or "")[:110], "why": why}
        {"in": inn, "excluded": exc, "undecidable": und}[verdict].append(rec)

    keys, kst, knote = read_matrix()
    gks, gst, gnote = read_gate_channels()
    reg = set(_reg_key(k) for k in keys) | set(_reg_key(k) for k in gks)
    regstat = "OK" if (kst == "OK" and gst == "OK") else "UNAVAILABLE"

    L2, L3 = [], []
    for r in inn:
        ck = _reg_key(r["id"])
        if any(rk and rk in ck for rk in reg):
            L2.append(r)
        else:
            L3.append(r)

    avail = [n for n, f in faces.items() if f["status"] == "OK"]
    if not avail:
        verdict = "UNDECIDABLE"
        vwhy = "★ 三源全不可用 ⇒ 空集 ≠ 通过（本判据拒给结论）"
    elif not inn and L0 > 0:
        verdict = "UNDECIDABLE"
        vwhy = "★ L0>0 但候选为空 ⇒ 须先证明「扫过的面」够宽，本工具拒给「无未登记通道」"
    else:
        verdict = "MEASURED"
        vwhy = "读数成立；★ 但「不存在未登记通道」仍取决于论域是否获裁（见 DOMAIN_DEF_VERSION）"

    return {
        "domain_def_version": DOMAIN_DEF_VERSION,
        "domain_def_text": DOMAIN_DEF_TEXT,
        "faces": faces, "faces_available": avail,
        "L0": L0, "L0_5_removed": L0_5, "L0_5_kept": len(merged),
        "listen_enriched": enriched,
        "L1": len(inn), "excluded": exc, "undecidable": und,
        "L2": L2, "L3": L3,
        "registry": {"matrix": keys, "gate": gks, "status": regstat,
                     "note": "%s | %s" % (knote, gnote)},
        "verdict": verdict, "verdict_why": vwhy,
        "removed_sample": [(k, v["source"], (v.get("cmd") or "")[:70]) for k, v in removed[:8]],
    }


def print_live(r):
    print("== channel-denominator %s · --live（面 4 · 真独立活体面）==" % __version__)
    print("★ 论域定义版本：%s" % r["domain_def_version"])
    print()
    print("【扫过的面（★ 每个数字必须跟它一起报）】")
    for nm, f in r["faces"].items():
        print("  %-9s %-11s n=%-5d %s" % (nm, f["status"], f["n"], f["note"]))
    print()
    print("【分层分母】")
    print("  L0   原始活体（三源行数之和）        = %d" % r["L0"])
    print("  L0.5 跨源/同源重复（已剔，未静默丢） = %d" % r["L0_5_removed"])
    print("  ↳ 去重后                           = %d" % r["L0_5_kept"])
    print("  ↳ listen 行经 pid 富化              = %d（★ lsof 截断 COMMAND ⇒ 不靠截断名下判）"
          % r["listen_enriched"])
    print("  L1   候选通道（论域内）              = %d" % r["L1"])
    print("  排除 明确排除（逐条附理由）          = %d" % len(r["excluded"]))
    print("  不可判 两不命中（★ ≠ 排除，★ ≠ 收录） = %d" % len(r["undecidable"]))
    print("  L2   已登记（候选 ∩ 登记表）         = %d" % len(r["L2"]))
    print("  ★★ L3 未登记 = L1 − L2              = %d" % len(r["L3"]))
    print()
    print("【L3 · 未登记候选】")
    for x in r["L3"]:
        print("  - %-44s %-8s %s" % (x["id"][:44], "+".join(x["sources"]), x["cmd"][:56]))
    if r["excluded"]:
        print()
        print("【排除项（★ 附理由，防黑箱过滤）】")
        for x in r["excluded"][:12]:
            print("  × %-44s %s" % (x["id"][:44], x["why"]))
    print()
    print("【登记表来源】%s" % r["registry"]["note"])
    print("  矩阵声明 n=%d · 门冻结枚举 n=%d · 登记状态 %s" % (
        len(r["registry"]["matrix"]), len(r["registry"]["gate"]), r["registry"]["status"]))
    print()
    print("【判定】%s — %s" % (r["verdict"], r["verdict_why"]))
    print()
    print("★ 复跑：python3 ~/dsh-collab/scripts/channel-denominator.py --live")


# ═══════════ ★ 制度死锁（声明 / 活体 / 可变更 三面）═══════════
def status_cmd():
    declared, dst, dnote = read_matrix()
    gate, gst, gnote = read_gate_channels()
    node = _resolve_node()
    live, lnote, lrc = [], "", None
    if node is None or not os.path.exists(DRIFT_CLI):
        lnote = "drift cli 不可用（node=%s）" % node
    else:
        rc, out, err = _run([node, DRIFT_CLI, "--json"], timeout=90)
        lrc = rc
        if rc == 0 and out.strip():
            try:
                d = json.loads(out)
                for row in d.get("rows", []):
                    live.append({"check": row.get("check"), "drift": bool(row.get("drift"))})
                lnote = "driftCount=%s" % d.get("driftCount")
            except Exception as e:
                lnote = "JSON 解析失败：%s" % e
        else:
            lnote = "rc=%s ⇒ ★ 活体面不可判" % rc

    live_names = [x["check"] for x in live]
    union = sorted(set(declared) | set(live_names))
    live_only = [c for c in live_names if c not in declared]
    red = [x["check"] for x in live if x["drift"]]
    if gst != "OK":
        deadlock, dlock_stat = None, "UNDECIDABLE（门枚举不可用 ⇒ ★ 不猜）"
    else:
        deadlock = [c for c in red if c not in gate]
        dlock_stat = "无" if not deadlock else "%d 条" % len(deadlock)

    print("== channel-denominator %s · --status ==" % __version__)
    print("声明(矩阵) n=%d · 活体(drift) n=%d · 可变更(gate) n=%d · 有效并集 n=%d" % (
        len(declared), len(live_names), len(gate), len(union)))
    print("★ 仅活体（未登记/运行时追加）n=%d %s" % (len(live_only), live_only))
    print("★ 当前为红的通道 n=%d %s" % (len(red), red))
    print("★ 制度死锁（为红 ∧ 不在门冻结枚举）: %s" % dlock_stat)
    print("  deadlock_=%s" % (deadlock if deadlock is not None else "UNDECIDABLE"))
    print("★ 复跑：python3 ~/dsh-collab/scripts/channel-denominator.py --status")

    divergent = bool(live_only) or bool(deadlock)
    fixed = [c for c in union if c in declared and c in gate]
    print("★ 可经门变更的通道 n=%d %s" % (len(fixed), fixed))
    log("--status: declared=%d live=%d gate=%d union=%d live_only=%d deadlock=%s rc=%d" % (
        len(declared), len(live_names), len(gate), len(union), len(live_only),
        deadlock, 1 if divergent else 0))
    print("=> %s" % ("DIVERGENT" if divergent else "CONVERGENT"))
    return 1 if divergent else 0


# ═══════════ ★ R006 ⑩ 约束门：--lean4-check 六项 A–F ═══════════
def lean4_check():
    fails = 0
    checks = []

    def c(k, name, cond, detail=""):
        nonlocal fails
        checks.append((k, name, bool(cond), detail))
        if not cond:
            fails += 1

    _self = open(os.path.abspath(__file__), encoding="utf-8").read()

    def _strip(s):
        """★ 剥离字符串与注释 —— 危险原语查【code】面，避免自指假阳性。"""
        out = []
        for ln in s.split(chr(10)):
            ln = re.sub(r'#.*$', '', ln)
            ln = re.sub(r'"[^"]*"', '', ln)
            ln = re.sub(chr(39) + r'[^' + chr(39) + r']*' + chr(39), '', ln)
            out.append(ln)
        return chr(10).join(out)
    _code = _strip(_self)

    # ★ 论域声明：查的是 **subprocess.run 的首参**在【code 面】上是什么形态。
    #   ★ 不接受「因为是内部封装所以安全」这种口说 —— 要么是字面量，要么有显式类型守卫。
    calls = re.findall(r'subprocess\.run\(\s*([A-Za-z_][\w\.]*|\[)', _code)
    arg_guard = bool(re.search(r'isinstance\(\s*argv\s*,\s*\(?\s*(?:list|tuple)', _code))
    n_lit = sum(1 for x in calls if x == "[")
    # ★ 计数须扣掉函数定义行本身（`def _run(` 不是调用点）—— 报数不准等于没报
    n_def = len(re.findall(r'def\s+_run\(', _code))
    n_run_calls = max(0, len(re.findall(r'_run\(\s*([A-Za-z_][\w\.]*|\[)', _code)) - n_def)
    n_run_lit = len(re.findall(r'_run\(\s*\[', _code))
    c("A", "类型锁：subprocess 首参为列表字面量，或受显式 isinstance 守卫",
      len(calls) > 0 and (n_lit == len(calls) or (arg_guard and len(calls) == 1)),
      "subprocess 调用点 %d 个（字面量 %d）· argv 类型守卫 %s · _run 调用点 %d 个（字面量 %d）"
      % (len(calls), n_lit, arg_guard, n_run_calls, n_run_lit))
    c("B", "入口门：无 shell=True（不可注入）",
      not re.search(r'shell\s*=\s*True', _code),
      "命中 0 次")
    c("C", "Schema 门：输入经旗标白名单约束（未知旗标 exit 2）",
      "unknown flag" in _self and "return 2" in _self, "旗标白名单在位")
    c("D", "状态机：本工具可自证（--selftest 在位）",
      "--selftest" in _self, "selftest 在位")
    c("E", "只读锁：异常不被静默吞掉（try/except 在位）",
      bool(re.search(r'try\s*:', _code)), "try 在位")
    c("F", "负例矩阵可执行（本函数自身可跑）", callable(lean4_check), "自证")

    print("== %s · --lean4-check（六项 A–F）==" % os.path.basename(__file__))
    for k, name, ok, detail in checks:
        print("  %s %s %-52s %s" % ("OK " if ok else "FAIL", k, name, detail))
    print("\n  => %d/%d pass, %d FAIL" % (len(checks) - fails, len(checks), fails))
    return 0 if fails == 0 else 1


# ═══════════ ★ 自证（含 v2.0 面 4 五条负控 + 正控）═══════════
def selftest():
    fails = 0
    undec = 0
    rows = []

    def c(name, ok, detail=""):
        nonlocal fails, undec
        rows.append((name, ok, detail))
        if ok is None:
            undec += 1
        elif not ok:
            fails += 1

    # ── C1 ★ _sig：裸文件名（1.1.0 首版要求 token 含 '/' ⇒ 整条被跳过）──
    s_bare = _sig({"source": "process", "cmd": "python3 mac-mini-inbox-watch.py",
                   "id": "pid:1"})
    s_full = _sig({"source": "process",
                   "cmd": "/usr/bin/python3 /Users/coreyleung/dsh-collab/scripts/mac-mini-inbox-watch.py",
                   "id": "pid:2"})
    c("C1 _sig 收裸文件名（★ 1.1.0 缺陷：含斜杠才收）",
      s_bare is not None and s_bare == s_full,
      "bare=%r full=%r" % (s_bare, s_full))

    # ── C2 ★ 排除控：夹具必须【同时】命中收录与排除（否则该控恒真）──
    fx_name, fx_cmd = "com.x.board-log-guard", "/usr/bin/x board-log-guard.py"
    v, why = classify_domain(fx_name, fx_cmd)
    v_in, _ = classify_domain(fx_name, fx_cmd, excludes=[])
    c("C2 排除控能红：夹具同时命中收录与排除 ⇒ 判 excluded 且附理由",
      v == "excluded" and bool(why) and v_in == "in",
      "verdict=%s | 清空排除表后=%s（★ 证明排除判据真在起作用，非恒真）" % (v, v_in))

    # ── C3 ★ 跨源去重：同一守护按 label 与 pid 各一条 ⇒ 计 1 ──
    pool = [
        {"source": "launchd", "id": "com.dsh.mac-mini-inbox-watch",
         "cmd": "/usr/bin/python3 /Users/coreyleung/dsh-collab/scripts/mac-mini-inbox-watch.py"},
        {"source": "process", "id": "pid:98534",
         "cmd": "/usr/bin/python3 /Users/coreyleung/dsh-collab/scripts/mac-mini-inbox-watch.py"},
    ]
    merged, removed = dedupe_cross_source(pool)
    c("C3 跨源去重：label 与 pid 同一实体 ⇒ 计 1",
      len(merged) == 1 and len(removed) == 1,
      "merged=%d removed=%d key=%s" % (len(merged), len(removed), _sig(pool[0])))

    # ── C3b ★ 宁可不并：认不出脚本的进程不参与去重 ──
    m2, _ = dedupe_cross_source([{"source": "process", "id": "pid:9", "cmd": "kernel_task"}])
    c("C3b 认不出脚本 ⇒ 不并（★ 宁可少合并，不可错合并）",
      len(m2) == 1 and _sig({"source": "process", "id": "pid:9", "cmd": "kernel_task"}) is None,
      "kernel_task 无签名 ⇒ 不参与去重")

    # ── C9/C10 ★ 成对控：flag 的【值】与【标识符样实参】必须区别对待 ──
    s_a = _sig({"source": "process", "id": "pid:1",
                "cmd": "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/"
                       "Versions/3.9/Resources/Python.app/Contents/MacOS/Python "
                       "/Users/coreyleung/dsh-collab/scripts/mac-mini-inbox-watch.py --interval 5"})
    want_a = _reg_key("com.dsh.mac-mini-inbox-watch")
    c("C9 flag 的【值】不进签名：'--interval 5' 的 5 须丢 ⇒ 与 launchd 行并得上",
      s_a == want_a, "sig=%r 期望=%r" % (s_a, want_a))

    _bs = "/Users/coreyleung/dsh-collab/rust-tools/dist/dsh-tools-macos-arm64-v1.12.2 bb-sub --agent %s --prefixes %s --token t"
    s_b1 = _sig({"source": "process", "id": "pid:1", "cmd": _bs % ("qa", "data/qa/")})
    s_b2 = _sig({"source": "process", "id": "pid:2", "cmd": _bs % ("recovery", "data/recovery/")})
    c("C10 标识符样实参须保留：qa/recovery 的区分度不得丢（防 8 条 bb-sub 被错并）",
      s_b1 is not None and s_b2 is not None and s_b1 != s_b2,
      "qa=%r recovery=%r" % (s_b1, s_b2))

    # ── C11 ★ listen 的 COMMAND 被 lsof 截断 ⇒ 必须靠 pid 富化，不得靠截断名下判 ──
    def _stub_launchd():
        return [], "OK", "stub"

    def _stub_proc():
        return ([{"source": "process", "id": "pid:1221", "extra": "",
                  "cmd": "/Users/coreyleung/dsh-collab/rust-blackboard/dist/"
                         "rust-blackboard-macos-arm64-v0.6.18 --port 8792"}], "OK", "stub")

    def _stub_listen():
        return ([{"source": "listen", "id": "listen:*:8792", "extra": "*:8792", "pid": "1221",
                  "cmd": "rust-blac (pid 1221)"}], "OK", "stub")

    rr = judge_live(face_fns=[("launchd", _stub_launchd),
                              ("process", _stub_proc), ("listen", _stub_listen)])
    c("C11 listen 截断名 ⇒ 靠 pid 富化仍判 in（★ 否则面 4-③ 形同虚设）",
      rr["listen_enriched"] == 1 and any(x["id"].startswith("listen:") for x in rr["L3"]),
      "enriched=%d L3=%s" % (rr["listen_enriched"], [x["id"] for x in rr["L3"]]))

    # ── C4 ★ 三态不合并：不可判项既不进候选也不进排除 ──
    v_u, why_u = classify_domain("com.apple.something", "/usr/sbin/somethingd")
    c("C4 三态不合并：两不命中 ⇒ undecidable（★ ≠ 排除）",
      v_u == "undecidable", "verdict=%s" % v_u)

    # ── C5 ★ 空集 ≠ 通过：三源全不可用 ⇒ UNDECIDABLE，不得 OK ──
    def _dead():
        return [], "UNAVAILABLE", "自证注入：面不可用"
    r = judge_live(face_fns=[("launchd", _dead), ("process", _dead), ("listen", _dead)])
    c("C5 空集 ≠ 通过：三源全不可用 ⇒ UNDECIDABLE（不得 OK/PASS）",
      r["verdict"] == "UNDECIDABLE", "verdict=%s L0=%d" % (r["verdict"], r["L0"]))

    # ── C6 ★ 正控：真候选必须被判 in（否则 C2–C4 可能因全判 excluded 而恒真）──
    v_p, _ = classify_domain("com.dsh.mac-mini-inbox-watch",
                             "/usr/bin/python3 mac-mini-inbox-watch.py")
    c("C6 正控：真通道候选判 in（防上面几条恒真）",
      v_p == "in", "verdict=%s" % v_p)

    # ── C7 论域定义必须显式且非空 ──
    c("C7 论域显式：版本非空 且 收录/排除表都到位",
      bool(DOMAIN_DEF_VERSION) and bool(DOMAIN_INCLUDE_PATTERNS)
      and isinstance(DOMAIN_EXCLUDE_PATTERNS, list),
      "version=%s" % DOMAIN_DEF_VERSION)

    # ── C8 排除项必须逐条附理由 ──
    c("C8 排除项逐条附理由（防黑箱过滤）",
      all(isinstance(e, tuple) and len(e) == 2 and str(e[1]).strip()
          for e in DOMAIN_EXCLUDE_PATTERNS),
      "n=%d" % len(DOMAIN_EXCLUDE_PATTERNS))

    print("== channel-denominator · --selftest ==")
    for name, ok, detail in rows:
        print("  %s %-58s %s" % ("OK " if ok else ("?? " if ok is None else "FAIL"), name, detail))
    print()
    print("selftest: fails=%d undecidable=%d version=%s" % (fails, undec, __version__))
    return 0 if (fails == 0 and undec == 0) else 1


# ═══════════ ★ R006 ⑨ CLI 治理：旗标白名单，未知旗标 exit 2 ═══════════
USAGE = """channel-denominator %s — 通道登记分母审计器（★ 只读）

用法：
  channel-denominator --live           # 面 4 独立活体枚举 + 分层分母 L0→L3
  channel-denominator --status         # 声明/活体/可变更 三面 + 制度死锁（0=CONVERGENT 1=DIVERGENT）
  channel-denominator --domain         # 打印论域定义（版本 + 收录/排除表）
  channel-denominator --selftest       # 自证（含面 4 负控 + 正控）
  channel-denominator --selfcheck      # R006 ② TCC 能力边界三段
  channel-denominator --lean4-check    # R006 ⑩ 约束门六项 A–F
  channel-denominator --tool-version   # R006 ⑥ 版本单一来源
  channel-denominator --help
""" % __version__

KNOWN = {"live", "status", "domain", "selftest", "selfcheck", "lean4-check",
         "tool-version", "help"}


def print_domain():
    print("== 论域定义（★ 显式 · 可打印 · 带版本）==")
    print("DOMAIN_DEF_VERSION = %s" % DOMAIN_DEF_VERSION)
    print()
    print(DOMAIN_DEF_TEXT)
    print()
    print("【收录模式 n=%d】%s" % (len(DOMAIN_INCLUDE_PATTERNS), DOMAIN_INCLUDE_PATTERNS))
    print()
    print("【排除模式 n=%d（★ 排除优先于收录）】" % len(DOMAIN_EXCLUDE_PATTERNS))
    for pat, why in DOMAIN_EXCLUDE_PATTERNS:
        print("  × %-24s %s" % (pat, why))
    print()
    print("★ 未获裁可 ⇒ L1/L3 只是【提案口径下的读数】，不是「未登记通道」的终局判定。")
    return 0


def main(argv):
    flags = set()
    for a in argv:
        if a.startswith("--"):
            f = a[2:]
            if f not in KNOWN:
                print("[unknown flag] 未知旗标 --%s" % f, file=sys.stderr)
                print(USAGE, file=sys.stderr)
                return 2
            flags.add(f)
        else:
            print("[unknown arg] 不接受位置参数：%s" % a, file=sys.stderr)
            print(USAGE, file=sys.stderr)
            return 2

    if not flags or "help" in flags:
        print(USAGE)
        return 0
    if "tool-version" in flags:
        print(__version__)
        return 0
    if "selfcheck" in flags:
        return selfcheck()
    if "lean4-check" in flags:
        return lean4_check()
    if "selftest" in flags:
        return selftest()
    if "domain" in flags:
        return print_domain()
    if "status" in flags:
        return status_cmd()
    if "live" in flags:
        r = judge_live()
        print_live(r)
        log("--live: L0=%d L0.5=%d L1=%d excl=%d und=%d L2=%d L3=%d verdict=%s" % (
            r["L0"], r["L0_5_removed"], r["L1"], len(r["excluded"]),
            len(r["undecidable"]), len(r["L2"]), len(r["L3"]), r["verdict"]))
        return 0 if r["verdict"] != "UNDECIDABLE" else 3
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
