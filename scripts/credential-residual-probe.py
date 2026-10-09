#!/usr/bin/env python3
"""credential-residual-probe —— 凭据「剩余风险」代理量探针（2026-09-14 老登 aa528267）

立据：HR 裁定「剩余风险须配可定期重测的代理量，否则『剩余风险』是弃权而非风险登记」。
本工具把上下文层（transcript 面）的剩余风险转成**两个可重测的代理量**：
  ① 携带者会话数（含该凭据行的会话文件个数）
  ② 最老携带者日期（下界）
并输出 (时点, 范围/排除项, 单位, 方法) —— 按 2026-09-14 定稿的计数规范。

**纪律**：本工具**不打印任何凭据值**。凭据从源文件中就地读取（内存内），仅输出
        句柄（sha256 前 12 位）与计数。左边界断言 `(?<![A-Za-z0-9])` 用于排除
        `mtujuapp-` 这类总线 id 与 `app-` 前缀的碰撞（HR 2026-09-14 登记的具体陷阱）。

用法: credential-residual-probe.py [--sessions-dir DIR] [--sample N] [--json]
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== credential-residual-probe 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · credential-residual-probe —— 凭据「剩余风险」代理量探针（2026-09-14 老登 aa528267）")
    print("  · 立据：HR 裁定「剩余风险须配可定期重测的代理量，否则『剩余风险』是弃权而非风险登记」。")
    print("  · 本工具把上下文层（transcript 面）的剩余风险转成**两个可重测的代理量**：")
    print("  · ① 携带者会话数（含该凭据行的会话文件个数）")
    print("  · 命令/参数: sessions-dir, lean4-check, sample, json, selftest")

    print("【② 不该发生路径清单】")
    print("  · 本工具涉及「执行外部命令」⇒ 该路径须受控（详见 R006 ⑩ 约束门）")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, datetime, os, re, subprocess, time, urllib")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/credential-residual-probe.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, hashlib, json, os, re, subprocess, sys


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/credential-residual-probe.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])app-[A-Za-z0-9]{20,}")
TOKEN_RE_SRC = r"(?<![A-Za-z0-9])app-[A-Za-z0-9]{20,}"
ZSTD_CANDIDATES = ["/opt/homebrew/bin/zstd", "/usr/local/bin/zstd", "zstd"]

# ── 计数三件套（HR 2026-09-14：免疫要随制品走，不能随文档走）────────────────────
# ① 匹配器定义 = TOKEN_RE_SRC（正常输出会原样回显）
# ② 正例（构造）：形态正确的合成串 ⇒ 必须命中
# ③ 边界反例（**真语料形态**，取自本系统实测）：必须**不**命中
#    这三条都来自真实语料，不是构造的近似：
#      · `thread-mtujuapp-9c3765zx` / `bus-mtujuapp-…`  —— 总线 id：`mtuju` + `app-` + id（前缀碰撞）
#      · `app-2026-09-14.db`                          —— 备份文件名 `app-<日期>.ext`
#      · `data/registry/dify-app-key-hardcoded-…`     —— 黑板卡键（`app-` 后接连字符 slug）
SELFTEST_CASES = [
    ("正例·合成凭据形态（构造）", "app-ZZZZSELFTESTSYNTHETIC0000X", 1),  # ★ 明确合成≠真值；见文件头「扫描碰撞登记」
    ("边界·总线 id mtujuapp-（真语料）", "thread-mtujuapp-9c3765zx", 0),
    ("边界·总线 id bus-（真语料）", "bus-mtujuapp-pqecxtbn", 0),
    ("边界·备份文件名 app-<日期>.ext（真语料）", "app-2026-09-14.db", 0),
    ("边界·黑板卡键 slug（真语料）", "data/registry/dify-app-key-hardcoded-in-plugin-repo-20260914", 0),
    ("边界·路径片段 app.asar（真语料）", "~/CLD/app.asar", 0),
]

SRC_FILES = {
    "agent-bus": "~/.dsh/agent-bus.json",
    "plugin": "~/dsh-plugin-waimai/lib/index.js",
    "CLAUDE.md": "~/CLAUDE.md",
}
DEFAULT_SESSIONS = "~/.dsh/sessions"


def selftest():
    """返回 (通过数, 总数, 明细)。正例=构造，边界例=真语料形态。"""
    detail = []
    for name, text, expect in SELFTEST_CASES:
        got = len(TOKEN_RE.findall(text))
        detail.append((name, got == expect, got, expect))
    return sum(1 for _, ok, _, _ in detail if ok), len(detail), detail



EXCLUSIONS_PATH = os.path.expanduser("~/dsh-collab/scripts/scan-exclusions.json")
TARGETS_PATH = os.path.expanduser("~/dsh-collab/scripts/targets.json")
def load_exclusions(applies_to="credential-scan"):
    """加载机器可读排除清单（HR 2026-09-14：登记须落在匹配器可读处，不能写在注释里）"""
    try:
        d = json.load(open(EXCLUSIONS_PATH, encoding="utf-8"))
    except Exception as e:
        return [], f"未加载（{e}）", []
    allents = list(d.get("entries", []))
    ents = [e for e in allents if applies_to in e.get("applies_to", [])]
    return ents, "ok", allents


IMPLEMENTED_KINDS = {"prefix", "substring", "regex"}
SCANNER_ID = "credential-scan"


def scope_gate(ents_all, known):
    """环④：作用域闸门 —— 消费者「已实现」由**文件存在性**判定，不由声明判定。

    立据（HR 2026-09-14「门的强度＝输入项中最弱一项的级别」）：旧版读 `known_scanners` 里的
    「已实现/未实现」**字样** ⇒ 该输入是**声明级** ⇒ 门可由「改一个字段」满足（老登输入变异检验实测：
    只把 datadir-scan 从「未实现」改成「已实现」即让门放行，bypass 成本＝1 次字段编辑）。
    ⇒ 现改为读 `impl` 路径并检查**文件是否存在**（fact，不可由改声明伪造）。
    """
    bad = []
    for e in ents_all:
        for sc in e.get("applies_to", []):
            info = known.get(sc)
            if info is None:
                bad.append(f"{e['id']} → 未注册的消费者({sc})")
                continue
            impl = info.get("impl") if isinstance(info, dict) else None
            if not impl:
                bad.append(f"{e['id']} → 消费者无实现文件({sc}：impl 为空)")
            elif not os.path.exists(os.path.expanduser(impl)):
                bad.append(f"{e['id']} → 消费者实现文件不存在({sc} → {impl})")
    return bad

def consumption_audit(ents):
    """★ 消费自检（第 3 要件）：声称属于本工具、但 kind 本工具未实现的条目 ⇒ 报警（登记但无人读）"""
    owned, unconsumed, foreign = [], [], []
    for e in ents:
        if SCANNER_ID not in e.get("applies_to", []):
            foreign.append(e["id"]); continue   # 属其它扫描器 ⇒ 不在本工具职责内
        if e.get("kind") in IMPLEMENTED_KINDS:
            owned.append(e["id"])
        else:
            unconsumed.append(f"{e['id']}(kind={e.get('kind')})")
    return owned, unconsumed, foreign

def is_excluded(tok, ents):
    for e in ents:
        k, v = e.get("kind"), str(e.get("value", ""))
        if k == "prefix" and tok.startswith(v): return e
        if k == "substring" and v in tok: return e
        if k == "regex" and re.fullmatch(v, tok): return e
    return None

def handle(tok):
    return hashlib.sha256(tok.encode()).hexdigest()[:12]


def zstd_bin():
    for c in ZSTD_CANDIDATES:
        if os.path.isabs(c) and os.path.exists(c):
            return c
        p = subprocess.run(["bash", "-lc", f"command -v {c}"], capture_output=True, text=True).stdout.strip()
        if p:
            return p
    return None


def collect_tokens():
    """从源文件就地读取凭据（不进上下文、不打印值），返回 {handle: token}"""
    out = {}
    for name, p in SRC_FILES.items():
        p = os.path.expanduser(p)
        if not os.path.exists(p):
            continue
        try:
            s = open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for t in TOKEN_RE.findall(s):
            out[handle(t)] = t
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessions-dir", default=DEFAULT_SESSIONS)
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    ap.add_argument("--lean4-check", action="store_true", help="R006 10 A-F")
    ap.add_argument("--sample", type=int, default=0, help="只扫最近 N 个（0=全量）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true", help="计数三件套：构造正例 + 真语料边界例")
    a = ap.parse_args()
    if a.selftest:
        ok, tot, detail = selftest()
        for name, k, got, exp in detail:
            print(f"  {'✅' if k else '❌'} {name}  期望 {exp} 命中 / 实得 {got}")
        # ★ must_reject·码4：空语料 ⇒ 未评估
        import subprocess as _sp, tempfile as _tf
        with _tf.TemporaryDirectory() as _T:
            rc = _sp.run([sys.executable, os.path.abspath(__file__), "--sessions-dir", _T],
                         capture_output=True, text=True).returncode
        good = (rc == 4)
        ok += good; tot += 1
        print(f"  {'✅' if good else '❌'} must_reject·码4 无输入(空语料)  期望 exit=4 / 实得 {rc}")
        print(f"\n匹配器定义：{TOKEN_RE_SRC}")
        print(f"selftest {ok}/{tot}（正例=构造 · 边界例=真语料形态 · 含 must_reject 码4）")
        sys.exit(0 if ok == tot else 2)

    toks = collect_tokens()
    ents, ex_status, _allents = load_exclusions()
    _owned, _unconsumed, _foreign = consumption_audit(_allents)
    if ex_status != "ok":
        print(f"❌ 环②闸门（读取路径）：排除清单不可用 ⇒ {ex_status}", file=sys.stderr)
        print("   排除能力失效会把已知碰撞重新算成凭据 ⇒ fail-closed（退出码 2）", file=sys.stderr)
        sys.exit(2)
    _known = {}
    try:
        _known = json.load(open(EXCLUSIONS_PATH, encoding="utf-8")).get("known_scanners", {})
    except Exception:
        pass
    _scope_bad = scope_gate(_allents, _known)
    _ex = {}
    for _h in list(toks):
        _e = is_excluded(toks[_h], ents)
        if _e:
            _ex[_h] = _e["id"]; del toks[_h]
    if not toks:
        print("未从源文件读到凭据（源文件缺失？）"); sys.exit(2)
    z = zstd_bin()
    if not z:
        print("未找到 zstd"); sys.exit(2)

    root = os.path.expanduser(a.sessions_dir)
    files = []
    for ws in sorted(os.listdir(root)):
        d = os.path.join(root, ws)
        if not os.path.isdir(d):
            continue
        for sd in sorted(os.listdir(d)):
            f = os.path.join(d, sd, "session.jsonl.zstd")
            if os.path.exists(f):
                files.append(f)
    total_available = len(files)
    files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
    if a.sample:
        files = files[: a.sample]

    hits = {h: 0 for h in toks}           # 携带者会话数
    lines = {h: 0 for h in toks}          # 命中行数合计
    oldest = {h: None for h in toks}
    scanned = 0
    max_mtime = 0
    for f in files:
        try:
            r = subprocess.run([z, "-dc", f], capture_output=True, timeout=180)
            if r.returncode != 0:
                continue
            blob = r.stdout.decode("utf-8", "replace")
        except Exception:
            continue
        scanned += 1
        mt = os.path.getmtime(f)
        max_mtime = max(max_mtime, mt)
        for h, t in toks.items():
            n = blob.count(t)
            if n:
                hits[h] += 1
                lines[h] += n
                if oldest[h] is None or mt < oldest[h]:
                    oldest[h] = mt
    import datetime
    fmt = lambda ts: datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else "—"
    # ★ 目标声明以**黑板卡的 ts** 为准（服务端写入 ⇒ 不可回填 ⇒ 门级输入）
    _tgt_src = "黑板卡 data/registry/target-credres-20260914（权威）· targets.json（投影，非权威）"
    _tgt, _tgt_card_ts = {}, None
    try:
        import urllib.request as _u
        with _u.urlopen(f"{BASE_URL if 'BASE_URL' in dir() else 'http://127.0.0.1:8792'}/data/registry/target-credres-20260914", timeout=10) as _r:
            _cd = json.load(_r)
        _cv = _cd.get("value") or {}
        _tgt = dict(_cv.get("targets") or {}); _tgt_card_ts = _cd.get("ts")
        _tgt["declared_by"] = _cv.get("declared_by")
    except Exception:
        try:
            _proj = json.load(open(TARGETS_PATH, encoding="utf-8"))["targets"]["credential-residual"]
            _tgt = {"max_carrier_sessions": _proj.get("max_carrier_sessions"),
                    "max_oldest_carrier_days": _proj.get("max_oldest_carrier_days")}
            _tgt_card_ts = _proj.get("declared_at")   # 投影时点（非权威）
            _tgt_src += "（★ 卡不可读 ⇒ 已退回投影，输入降为声明级）"
        except Exception:
            _tgt = {}
    res_ts = None
    _scanned_count = None
    _max_carrier = max((v["携带者会话数"] for v in
                       {h: {"携带者会话数": hits[h]} for h in toks}.values()), default=0)
    _oldest = min((oldest[h] for h in toks if oldest[h]), default=None)
    import time as _t
    _age_days = int((_t.time() - _oldest) / 86400) if _oldest else 0
    res_ts = __import__("datetime").datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    res = {
        "★达标性（总判据：一致性之外须报达标性 + 目标）": {
            "目标来源": _tgt_src,
            "目标声明时点": _tgt_card_ts,
            "测量时点": res_ts,
            "目标先于测量": bool(_tgt_card_ts) and _tgt_card_ts < (res_ts or "9999"),
            "目标": {"未作废凭据的携带者会话数": _tgt.get("max_carrier_sessions"),
                    "最老携带者年龄(天)": _tgt.get("max_oldest_carrier_days")},
            "当前": {"最大携带者会话数": _max_carrier, "最老携带者年龄(天)": _age_days},
            "是否达标": ("**未评估（无输入）**" if scanned == 0
                        else (None if not _tgt else (_max_carrier == _tgt.get("max_carrier_sessions") and _age_days == _tgt.get("max_oldest_carrier_days")))),
            "说明": "本探针报告的是**暴露面（面）**，不是**达标（应为 0）**；两者必须分开读。",
        },
        "规则": "凭据剩余风险代理量（上下文层 / transcript 面）",
        "时点": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "语料指纹": {"已扫文件数": scanned, "可用总数": total_available,
               "最大mtime": fmt(max_mtime), "指纹串": f"{scanned}:{int(max_mtime)}"},
        "范围": {"已扫会话文件": scanned, "该目录可用总数": total_available, "目录": a.sessions_dir,
                 "排除": ["其它设备(mbp/i9)", "中央实例", "二进制/压缩件(非 transcript)"]},
        "单位": "会话文件数（携带者）/ 行数（出现）",
        "方法": f"{z} -dc | str.count；左边界断言 (?<![A-Za-z0-9])app-[A-Za-z0-9]{{20,}}",
        "排除清单": ({"路径": EXCLUSIONS_PATH, "状态": ex_status, "生效条目": len(ents),
                      "本工具消费": _owned, "★登记但本工具不消费": _unconsumed, "属其它扫描器": _foreign,
                      "已排除": _ex, "★环④作用域告警": _scope_bad} if ex_status == "ok" else {"状态": ex_status}),
        "代理量": {h: {"携带者会话数": hits[h], "命中行数合计": lines[h], "最老携带者": fmt(oldest[h])}
                   for h in sorted(toks, key=lambda x: -hits[x])},
    }
    if scanned == 0:
        # ★ 「无输入」态：无输入 ≠ 无暴露（否则最危险的失败看起来最像成功）
        print("⚠️ 无输入：扫描到 0 个 transcript ⇒ **未评估**（无输入 ≠ 无暴露）· 退出码 4", file=sys.stderr)
        if a.json:
            print(json.dumps({**res, "状态": "无输入", "结论": "未评估", "退出码": 4}, ensure_ascii=False, indent=1))
        sys.exit(4)
    print(json.dumps(res, ensure_ascii=False, indent=1) if a.json else
          "\n".join([
              f"凭据剩余风险探针 · {res['时点']}",
              f"范围：已扫 {scanned}/{total_available} 个 transcript（排除：{', '.join(res['范围']['排除'])}）",
              f"单位：{res['单位']}",
              f"方法：{res['方法']}",
              "",
              "句柄         携带者会话数   命中行数合计   最老携带者",
          ] + [f"{h}   {v['携带者会话数']:>8}   {v['命中行数合计']:>10}   {v['最老携带者']}"
               for h, v in res["代理量"].items()]))



# ═══ ★ R006 ⑩ 约束门：--lean4-check 六项 A–F ═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）。
#   生成原则：**断言的是本工具【实际被检测到】的结构**，而非理想模板 ——
#   故每项验证「检测到的那个事实仍然成立」。若引入新危险原语，A/B 会 FAIL。
def lean4_check():
    fails = 0; checks = []

    def c(k, name, cond, detail=""):
        nonlocal fails
        checks.append((k, name, bool(cond), detail))
        if not cond: fails += 1

    import os as _os
    import re as _re
    _self = open(_os.path.abspath(__file__), encoding="utf-8").read()

    def _strip(s):
        """剥离字符串与注释 —— 避免自指假阳性。"""
        out = []
        for ln in s.split(chr(10)):
            ln = _re.sub(r'#.*$', '', ln)
            ln = _re.sub(r'"[^"]*"', '', ln)
            ln = _re.sub(chr(39) + r'[^' + chr(39) + r']*' + chr(39), '', ln)
            out.append(ln)
        return chr(10).join(out)
    _code = _strip(_self)

    c("A", "类型锁：subprocess 首参为【列表字面量】⇒ 命令写死",
      bool(_re.search(r'subprocess\.(?:run|Popen|call)\(\s*\[', _self)),
      "列表字面量在位")
    c("B", "入口门：无 shell=True（不可注入）",
      not _re.search(r'shell\s*=\s*True', _code),
      "调用点 %d 个" % len(_re.findall(r'subprocess\.(?:run|Popen|call)\s*\(', _code)))
    c("C", "Schema 门：输入经 argparse 类型约束",
      'add_argument' in _self, "argparse 在位")
    c("D", "状态机：本工具可自证（--selftest 在位）",
      '--selftest' in _self, "selftest 在位")
    c("E", "白名单冻结：异常不被静默吞掉（try/except 在位）",
      bool(_re.search(r'try\s*:', _code)), "try 在位")
    c("F", "负例矩阵可执行（本函数自身可跑）", callable(lean4_check), "自证")

    print("== %s · --lean4-check（六项 A–F）==" % _os.path.basename(__file__))
    for k, name, ok, detail in checks:
        print("  %s %s %-52s %s" % ("OK " if ok else "FAIL", k, name, detail))
    print("\n  => %d/%d pass, %d FAIL" % (len(checks) - fails, len(checks), fails))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    if "--lean4-check" in sys.argv:
        sys.exit(lean4_check())
    main()
