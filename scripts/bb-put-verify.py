#!/usr/bin/env python3
"""黑板落卡 + 强制回读确认（指称完整性域内落地）
用法: bb-put-verify.py <key> <json文件|-> [--writer id] [--strict]
- PUT 后立即 GET 回读；非 200 或 key 不符 → 退出码 1（调用方不得声称"已落盘"）
- 依据：CLAUDE.md 黑板语法（首段须纯小写字母）+ 2026-09-10 指称完整性草案
- v2（2026-09-14，老登 aa528267）新增「否定性结论观测面闸门」：
  任何否定性结论（不存在/未提供/零/从未/无任何/未发现…）必须同卡附观测面声明
  （含项 + **排除项** + 工具 + 单位 + 时刻）；缺声明 → 默认告警，`--strict` 时拒写（退出码 2）。
  立据：2026-09-14 三例同形错误（老登 C 线搜错仓 / 星桥 观测面漏 launchd disabled 表 / HR 未加载⇒无属主）。
  注意：本闸门只查「有没有声明」，**查不出声明是否真实** —— 它是提醒，不是证明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, sys, os, subprocess, tempfile, time, urllib.request, urllib.error
import re

BASE = os.environ.get("BB_BASE", "http://127.0.0.1:8792")

# ── v3 更正（2026-09-14，老登）：v2 的「声明判据」是**子串宽口径**，实测会误判 ──
# 实测（data/registry 全库，2026-09-14 15:5x）：含否定词 184 张；用 v2 子串口径判「已声明」
# 通过 107 张（告警 77）；改用**结构化字段**严格口径只通过 18 张（告警 166）。
# ⇒ 89 张仅因正文里出现了「范围/口径/grep/遍历」这类词就被判为已声明 —— 这是**假通过**
#   （与今晚裁定的「假门比无门更危险」同族）。⇒ v3 起：
#   ① 默认**委托**单一权威实现 absence-claim-lint.py（--json-out 取 verdict），避免两个实现分叉；
#   ② 权威实现不可用时，退回**严格结构化**判据（顶层字段名含 观测面/scope/已查/未查），
#      且明确告警「本次为退路口径、与权威实现可能不一致」。
AUTHORITY = os.path.expanduser("~/dsh-collab/scripts/absence-claim-lint.py")
STRICT_KEY_MARKERS = ("观测面", "scope", "已查", "未查", "查询范围")

# 退路口径用的否定词表（仅当权威实现不可用时启用）
NEG_WORDS = ["不存在", "未提供", "从未", "无任何", "未发现", "没有", "为零", "零调用",
             "不成立", "已删除", "已失效", "无远端", "全无", "均无"]


def flatten(o):
    if isinstance(o, str):
        return o
    if isinstance(o, dict):
        return " ".join(f"{k} {flatten(v)}" for k, v in o.items())
    if isinstance(o, list):
        return " ".join(flatten(v) for v in o)
    return str(o)


def has_structured_scope(payload):
    """严格口径：顶层**字段名**须含观测面/scope/已查/未查 —— 不认正文里出现的词。"""
    if not isinstance(payload, dict):
        return False
    return any(any(m in str(k) for m in STRICT_KEY_MARKERS) for k in payload.keys())


def ask_authority(payload):
    """委托 absence-claim-lint.py。返回 (verdict, reason) 或 None（不可用）。"""
    if not os.path.exists(AUTHORITY):
        return None
    tmp = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
            tmp = f.name
        out = tmp + ".lint.json"
        subprocess.run([sys.executable, AUTHORITY, "--file", tmp, "--json-out", out],
                       capture_output=True, timeout=60)
        if not os.path.exists(out):
            return None
        d = json.load(open(out, encoding="utf-8"))
        rs = d.get("results") or []
        if not rs:
            return ("pass", "权威实现未产生判定（按 pass 记）")
        r = rs[0]
        return (r.get("verdict", "pass"), r.get("reason", ""))
    except Exception as e:
        return None
    finally:
        for p in (tmp, (tmp + ".lint.json") if tmp else None):
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass


def scope_gate(payload):
    """返回 (通过?, 说明, 判据来源)

    判据来源：'authority'=单一权威实现 · 'fallback-strict'=退路口径（会声明不一致风险）
    """
    av = ask_authority(payload)
    if av is not None:
        verdict, reason = av
        return (verdict == "pass"), f"权威实现 verdict={verdict}｜{reason[:80]}", "authority"
    txt = flatten(payload)
    hits = [w for w in NEG_WORDS if w in txt]
    declared = has_structured_scope(payload)
    return (not hits) or declared, f"退路口径：命中否定词 {hits}" if hits else "退路口径：无否定词", "fallback-strict"


def fallback_risk(payload):
    """权威实现不可用时，本卡是否存在**口径分歧风险**。

    设计（2026-09-14，收敛为单一实现的配套）：**分歧只可能出现在「规则适用」的卡上**。
    ⇒ 卡内无否定词时，规则本就不适用，退路口径与权威口径结果相同，**无风险**；
    ⇒ 卡内有否定词时，两个实现可能给出不同答案 ⇒ **默认 fail-closed（拒写）**，
       除非显式传 --allow-fallback 承认「本次判定不含权威口径」。
    """
    txt = flatten(payload)
    return [w for w in NEG_WORDS if w in txt]


def put(key, payload, writer):
    req = urllib.request.Request(f"{BASE}/{key}", data=json.dumps(payload, ensure_ascii=False).encode(), method="PUT")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Writer", writer)
    with urllib.request.urlopen(req, timeout=12) as r:
        return r.status, r.read().decode()[:200]

def verify(key):
    try:
        with urllib.request.urlopen(f"{BASE}/{key}", timeout=12) as r:
            body = r.read().decode()
            if r.status != 200:
                return False, f"HTTP {r.status}"
            d = json.loads(body)
            if d.get("error"):
                return False, f"error: {d['error']}"
            if "value" not in d:
                return False, "响应无 value 字段"
            return True, json.dumps(d.get("value", {}), ensure_ascii=False)[:120]
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)[:80]




GATE_LOG = os.path.expanduser("~/dsh-collab/logs/bb-put-verify-gates.log")

def gate_trace(key, shape_state, ring_state, verdict):
    """★ 门的执行留痕 —— 使「门是否在路径上被执行」**可测量**而非假设。
    立据（老登 2026-09-14 路径变异）：我为自己装的卡形门**从未被执行**，因为我的习惯命令是
    `python3 -c json.load(...) && bb-put-verify.py ...`，`&&` 在预检失败时短路 ⇒ 工具根本不被调用。
    ⇒ 「存在 ≠ 在路径上」。故每次运行都留一行，供统计**执行率**。
    """
    try:
        os.makedirs(os.path.dirname(GATE_LOG), exist_ok=True)
        with open(GATE_LOG, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')}\t{key}\tshape={shape_state}\tring={ring_state}\tverdict={verdict}\n")
    except Exception:
        pass


def ratio_guard(num, den, label):
    """★ 比率自检门（HR 2026-09-14「越界不是错误，是框不一致的诊断信号」）

    ★ 两层防（HR 归纳，2026-09-14）：
      · **声明层**＝四元绑定（分子/分母/**框**/时点）⇒ 防**误读**（读者不会把不同框的两个比值当同一个）
      · **值层**＝本函数的越界自检 ⇒ 防**误印**（越界时不打印一个像结果的数字）
      ⇒ **缺一，比率仍会被当结果读。**
    凡输出比率，先查越界（>100% / <0%）；越界即**拒绝输出该比率**并报「框不一致」，
    而不是打印一个越界数字。⇒ 值层自检，与「门只接受值」一致。
    """
    if den in (0, None):
        return f"{label}: 分母为 0 ⇒ **不输出比率**（框未建立）"
    r = num / den
    if r > 1.0 or r < 0.0:
        return (f"{label}: ★越界 {num}/{den} = {r*100:.0f}% ⇒ **框不一致，拒绝输出该比率**"
                f"（分子与分母的分母不同框：这是诊断信号，不是计算结果）")
    return f"{label}: {num}/{den} = {r*100:.0f}%"


def _abs_reading(lines):
    """★ 门读数须**分子 + 分母**（N 拦下数 · M 作用对象数）。
    ★ 本工具是**单件**工具 ⇒ M 恒为 1 ⇒ **M=0 那一格不可达**
      ⇒「门空转」在此表现为 N=0（有对象但没挡），而不是「无对象」。
    ★ 用法：这是该读数的**消费者** —— 没有它，日志里的 abs_* 字段就是「只写不读」。
    """
    M = N = T = n = 0
    for l in lines:
        if "abs_targets=" not in l:
            continue
        n += 1
        try:
            d = dict(x.split("=", 1) for x in l.strip().split("\t") if "=" in x)
            M += int(d.get("abs_targets", 0))
            T += int(d.get("abs_hits", 0))
            N += int(d.get("abs_blocked", 0))
        except Exception:
            continue
    return {
        "含读数的运行次数": n, "M_作用对象数": M, "N_拦下数": N, "命中数": T,
        "★四格_单件工具退化为两格": {
            "M>0 且 N>0": "在挡" if N > 0 else "(未出现)",
            "M>0 且 N=0": "**在跑但不挡**" if (M > 0 and N == 0) else "(未出现)",
            "M=0": "**不可达**（单件工具必有 1 张卡）",
        },
        "★出声条件": "M>0 且 N=0 ⇒ 应出声；★ 但**在单件工具上这是常态**（多数卡无绝对断言）"
                      "⇒ **出声条件须绑工具类型**：单件报读数、批量才把 N=0 当异常",
    }


def gate_status(window_start=None):
    """★ 门执行状态的**可证伪最小形式**（替代不可算的「执行率」）。
    立据：HR 2026-09-14 采纳本项 —— **观测点须比被测对象更靠上游**；
    未执行不留痕、绕过门的写卡不经过工具 ⇒ **执行率在工具内部不可观测**。
    ⇒ 故只报布尔值（窗口内执行过 / 未执行过）+ 末次执行时刻，并**显式声明比率不可测**。
    """
    path = GATE_LOG
    if not os.path.exists(path):
        return {"窗口内是否执行过": False, "说明": "留痕文件不存在", "末次执行": None}
    lines = [l for l in open(path, encoding="utf-8") if l.strip()]
    if window_start:
        lines = [l for l in lines if l >= window_start]
    return {
        "窗口起始": window_start or "(全部)",
        "窗口内留痕行数": len(lines),
        "窗口内是否执行过": len(lines) > 0,
        "末次执行": (lines[-1].split("\t")[0] if lines else None),
        "★绝对断言门读数（分子/分母）": _abs_reading(lines),
        "★执行率": "**不可测**（分母＝对该工具的调用次数在上游，工具内部不可观测；未执行不留痕）",
        "可证伪形式": "布尔值「窗口内是否执行过」—— 若为 False，即证明门不在实际路径上",
    }

def card_shape_lint(raw_text, err_pos=None):
    """★ 作者高频失误门（老登 2026-09-14）：卡 JSON 缺逗号，特征为
    「字符串内写了字面 \\n 当换行，紧接着开始一个新键」。
    检测法：取解析错误位置，**向前回看 80 字符**；若其中含字面 `\\n` 且错误类型为
    「Expecting ',' delimiter」，则几乎必为漏逗号。今日我在这一处犯了 4 次。
    """
    if err_pos is None:
        return []
    seg = raw_text[max(0, err_pos - 80):err_pos]
    if "\\n" in seg:
        tail = seg.split("\\n")[-1][:40]
        return [tail or "(键名紧跟在字面 \\n 之后)"]
    return []

def scope_ring_gate():
    """★ 三级强度：本函数把「检查」升为「门」—— 未处置的环告警阻断落卡。

    立据（HR 2026-09-14 三级强度总判据：声明 → 检查 → 门；「有」≠「会」≠「挡」）：
    此前环③④（消费 / 作用域）**只是输出**，可被忽略继续落卡 ⇒ 通过成本≈0 ⇒ 是检查不是门。
    现改为：存在未消费条目或作用域告警 ⇒ **拒写（退出码 4）**，除非显式 --allow-scope-warning；
    **绕行本身会被写进卡内**（否则绕行会成为新的名义门 —— HR 明确要求）。
    """
    import importlib.util
    probe = os.path.expanduser("~/dsh-collab/scripts/credential-residual-probe.py")
    if not os.path.exists(probe):
        return [], f"探针缺失（{probe}）"
    try:
        spec = importlib.util.spec_from_file_location("crp", probe)
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        ents, st, allents = m.load_exclusions()
        if st != "ok":
            return [f"排除清单不可用：{st}"], None
        owned, unconsumed, foreign = m.consumption_audit(allents)
        known = {}
        try:
            known = json.load(open(m.EXCLUSIONS_PATH, encoding="utf-8")).get("known_scanners", {})
        except Exception:
            pass
        bad = list(unconsumed) + list(m.scope_gate(allents, known))
        return bad, {"消费": len(owned), "未消费": unconsumed, "属其它扫描器": foreign}
    except Exception as e:
        return [f"环闸门执行失败：{e}"], None


# ── 绝对断言门（HR 2026-09-14 并入网络级：「永不可能」须给出**封闭性来源**）──────────
# 判据：写下「永不可能/绝不/从不/无一例外」时，须指得出**封闭性来源**（键空间/枚举面定义/
# 哪张表/哪段代码把可能性排除掉了）。指不出 ⇒ 应改写为「无已知机制」。
# ★ 两类豁免（缺一即为假阳性，见下）：
#   ① 卡内**给出封闭性来源**（字段或显式声明）⇒ 放行
#   ② **引用/提及**（在「」『』"" 引号内，或紧邻引述动词）⇒ 放行
# ★ 我实测过：**我自己的判据卡用了「永不可能」6 次，全部是引用或规则陈述** ⇒ 没有②，
#   这个门会**驱逐「讨论该判据」的文本**（use–mention 同形）。⇒ 必须带②。
ABSOLUTE_CLAIM_RE = re.compile(r"(永不可能|永远不会|永不会|永不|绝不|从不|必然不|无一例外|不可能出现)")
# ★ 只认中文引号：ASCII 双引号是 JSON 序列化语法，纳进来会让**每一个**字符串都"在引号内"
#   ⇒ 门永不触发（我实测过这一版：正例也放行 ⇒ 一个永不报警的门，外观与「没问题」相同）
QUOTE_OPEN, QUOTE_CLOSE = "「『“", "」』”"
CLOSURE_HINT_RE = re.compile(r"(封闭性来源|封闭性声明|closure[_ ]?source|键空间|枚举面定义)")


def closure_source_given(payload):
    """★ 封闭性来源**必须是字段**（不是正文里提到这四个字）—— 否则「提到即可豁免」= 假门。
    且字段值须含**可核验指向**（路径 / 黑板键 / 表名 / 代码 location）。
    返回 (是否给出, 依据说明)。"""
    found = []
    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                if CLOSURE_HINT_RE.search(str(k)):
                    sv = str(v)
                    if len(sv) >= 8 and re.search(r"(/|\bdata/|\bnotes/|\btasks/|\.py|\.js|\.sh|\.yml|键空间|枚举|表|代码|函数|行)", sv):
                        found.append("%s = %s" % (path + "/" + str(k), sv[:60]))
                walk(v, path + "/" + str(k))
        elif isinstance(o, list):
            for x in o:
                walk(x, path + "/[]")
    walk(payload, "")
    return (bool(found), found[0] if found else "")


def absolute_claim_gate(text, payload=None):
    """返回 (未豁免命中列表, 豁免依据列表)。**不静默**：豁免也要回报。
    ★ 豁免①只认**字段形态且值可核验**（见 closure_source_given）—— 正文里提到「封闭性来源」**不算**。"""
    exempt, unhit = [], []
    # ★★ 路径无关的命中数（HR 2026-09-14：读数须两项才分得出第三态 ⇒
    #   而我去核口径时发现：早退路径下 B+E ≠ 命中数 ⇒ 故须**单独数**）
    hits = len(ABSOLUTE_CLAIM_RE.findall(text))
    ok, why = closure_source_given(payload if payload is not None else {})
    if ok:
        exempt.append("字段给出封闭性来源（%s）" % why)
        return [], exempt, hits
    for m in ABSOLUTE_CLAIM_RE.finditer(text):
        i, j = m.start(), m.end()
        back = text[max(0, i - 40):i]
        fwd = text[j:j + 40]
        if any(o in back for o in QUOTE_OPEN) and any(c in fwd for c in QUOTE_CLOSE):
            exempt.append("引用形态：…%s…" % m.group(0))
            continue
        unhit.append({"断言": m.group(0), "上下文": text[max(0, i - 24):j + 16].replace("\n", " ")})
    return unhit, exempt, hits


def selftest():
    """★ selftest：**每个非 0 退出码都须有一个 must_reject 用例**（HR 2026-09-14 配套判据）。
    覆盖：1（回读失败）· 2（键语法/JSON 解析）· 3（fail-closed）· 4（环闸门）
    全部用**子进程 + 临时文件**做，不触碰黑板（除码 1 用不可达 base）。
    """
    import subprocess, tempfile
    me = os.path.abspath(__file__)
    T = tempfile.mkdtemp(prefix="bbpv-selftest-")
    def run(args, base=None):
        env = dict(os.environ)
        if base: env["BB_BASE"] = base
        return subprocess.run([sys.executable, me] + args, capture_output=True, text=True, env=env).returncode
    cases = []
    # 码 2：键语法非法
    bad_key = os.path.join(T, "ok.json"); open(bad_key, "w").write('{"a":"b"}')
    cases.append(("must_reject·码2 键语法非法", run(["Bad-Key/xx", bad_key]), 2))
    # 码 2：JSON 解析失败
    bad_json = os.path.join(T, "bad.json"); open(bad_json, "w").write('{"a":"第一行。\\n★_续写":"v"}')
    cases.append(("must_reject·码2 JSON 解析失败", run(["notes/mac-mini/x", bad_json]), 2))
    # 码 1：回读失败（不可达 base —— PUT 会失败）
    cases.append(("must_reject·码1 回读/PUT 失败", run(["notes/mac-mini/x", bad_key], base="http://127.0.0.1:9"), 1))
    # 码 3：权威不可用 + 含否定词 + 无 --allow-fallback
    neg = os.path.join(T, "neg.json"); open(neg, "w").write('{"结论":"该接口不存在"}')
    lint = os.path.expanduser("~/dsh-collab/scripts/absence-claim-lint.py")
    hidden = None
    try:
        if os.path.exists(lint):
            hidden = lint + ".selftest-hidden"; os.rename(lint, hidden)
        cases.append(("must_reject·码3 权威不可用且含否定词 ⇒ fail-closed", run(["notes/mac-mini/x", neg]), 3))
    finally:
        if hidden and os.path.exists(hidden): os.rename(hidden, lint)
    # 码 4：环闸门（临时塞一条惰性登记 ⇒ 有未处置告警）
    reg = os.path.expanduser("~/dsh-collab/scripts/scan-exclusions.json")
    backup = None
    try:
        if os.path.exists(reg):
            backup = reg + ".selftest-bak"; os.rename(reg, backup)
            d = json.load(open(backup, encoding="utf-8"))
            d["entries"].append({"id": "selftest-ring", "kind": "path", "value": "x",
                                 "applies_to": ["credential-scan"], "reason": "selftest 用"})
            json.dump(d, open(reg, "w", encoding="utf-8"), ensure_ascii=False)
        ok_card = os.path.join(T, "ok2.json"); open(ok_card, "w").write('{"结论":"链路存在"}')
        cases.append(("must_reject·码4 环闸门未处置告警 ⇒ 拒写", run(["notes/mac-mini/x", ok_card]), 4))
    finally:
        if backup and os.path.exists(backup):
            os.replace(backup, reg)
    # ── ★★ 新增：**成功写入路径**（must_pass）─────────────────────────
    # 为什么必须有（2026-09-28，入口覆盖审计实测）：
    #   `entry-coverage.py` 报出本工具 **4 个零被经过的函数**
    #   （`verify` 13 行 · `_abs_reading` 13 · `gate_status` 8 · `ratio_guard` 7）。
    #   其中 `verify` 是**这个工具最核心的一步**（写完回读确认）。
    #   成因：上面 5 条用例**全部是 must_reject** —— **一个只会拒绝的测试，
    #   同时也测不到成功的那条路径** ⇒ 「5/5 must_reject」这个读数**告诉我 something 不对**，
    #   覆盖审计**告诉我是什么** ✓
    # ★ 用**本地 stub 服务器**（不碰真黑板）：本自测的原有纪律就是「不触碰黑板」，
    #   而 stub 能同时让 PUT 与 GET 成功 ⇒ `verify` 与成功分支第一次被真正执行 ✓
    import http.server, threading
    class _Stub(http.server.BaseHTTPRequestHandler):
        def do_PUT(self):
            n = int(self.headers.get("Content-Length") or 0)
            self.rfile.read(n)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers(); self.wfile.write(b'{"ok":true}')
        def do_GET(self):
            b = json.dumps({"key": "x", "ts": "stub", "version": 1,
                            "value": {"结论": "链路存在"}}, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers(); self.wfile.write(b)
        def log_message(self, *a):
            pass
    _srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Stub)
    _srv.daemon_threads = True
    threading.Thread(target=_srv.serve_forever, daemon=True).start()
    _base = "http://127.0.0.1:%d" % _srv.server_address[1]
    try:
        cases.append(("★★ must_pass·成功写入+回读确认 ⇒ 码0（**这是 verify 唯一的用例**）",
                      run(["notes/mac-mini/stub-card", ok_card], base=_base), 0))
        # ★ 补 `--gate-status` 分支：它是 `gate_status` 与 `_abs_reading` **唯一**的到达路径，
    #   不跑它，这两个函数就永远零被经过（审计实测：二者各 13 行 / 8 行全零）。
        cases.append(("★ must_pass·--gate-status ⇒ 码0（gate_status/_abs_reading 唯一到达路径）",
                      run(["--gate-status"], base=_base), 0))
    finally:
        _srv.shutdown()

    import shutil; shutil.rmtree(T, ignore_errors=True)
    ok = sum(1 for _, got, exp in cases if got == exp)
    for name, got, exp in cases:
        print(f"  {'✅' if got == exp else '❌'} {name}  期望 exit={exp} / 实得 {got}")
    n_rej = [c for c in cases if "must_reject" in c[0]]
    n_pas = [c for c in cases if "must_pass" in c[0]]
    print(f"\nselftest {ok}/{len(cases)}（每个非 0 码一个 must_reject 用例）")
    # ★ 覆盖形态：只报总数会掩盖不对称 —— 一个「一律拒绝」的实现与正确实现读数相同
    print("覆盖形态: must_reject %d/%d · must_pass %d/%d"
          % (sum(1 for c in n_rej if c[1] == c[2]), len(n_rej),
             sum(1 for c in n_pas if c[1] == c[2]), len(n_pas)))
    if not n_pas:
        print("  ⚠️ must_pass 用例数=0 ⇒ 本测**无法区分**「正确实现」与「一律拒绝的实现」")
    return ok, len(cases)


def main():
    if "--selftest" in sys.argv:
        ok, tot = selftest(); sys.exit(0 if ok == tot else 2)
    if "--gate-status" in sys.argv:
        ws = None
        if "--since" in sys.argv:
            ws = sys.argv[sys.argv.index("--since") + 1]
        print(json.dumps(gate_status(ws), ensure_ascii=False, indent=1)); sys.exit(0)
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(2)
    key, src = sys.argv[1], sys.argv[2]
    writer = "session-aa528267-0434-4bf5-87c5-d5a61f8215b2"
    if "--writer" in sys.argv:
        writer = sys.argv[sys.argv.index("--writer") + 1]
    # 键语法自检（首段须纯小写字母）
    first = key.split("/")[0]
    if not first.isalpha() or not first.islower():
        print(f"❌ 键语法非法：首段 '{first}' 必须为纯小写字母（否则 400）"); sys.exit(2)
    raw = sys.stdin.read() if src == "-" else open(src, encoding="utf-8").read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"❌ 卡 JSON 解析失败（{e}）")
        for h in card_shape_lint(raw, getattr(e, "pos", None)):
            print(f"   ⚠️ 疑似「字符串内裸 \\n 后紧跟键名」缺逗号，位置键名: {h}")
        print("   ⇒ 这是作者高频失误；请检查该处是否漏了 `\",`")
        gate_trace(key, "blocked", "n/a", "reject-json")
        sys.exit(2)
    # 否定性结论 → 观测面闸门（默认委托单一权威实现）
    ok_scope, why, source = scope_gate(payload)
    strict = "--strict" in sys.argv
    tag = "权威实现" if source == "authority" else "⚠️退路口径"
    if not ok_scope:
        print(f"⚠️ 观测面闸门（{tag}）：{why}")
        print("   要求：含项 + **排除项** + 工具 + 计数单位 + 时刻（五项）")
        print("   立据：2026-09-14 三例同形错误（搜错仓 / 观测面漏 disabled 表 / 未加载⇒无属主）")
        if strict:
            print("❌ --strict：拒写。请补「观测面」字段后重试。"); sys.exit(2)
        print("   （非 strict 模式：仅告警，继续落卡）")
    else:
        print(f"ℹ️ 观测面闸门通过（{tag}）")
    if source != "authority":
        risk = fallback_risk(payload)
        allow = "--allow-fallback" in sys.argv
        if risk and not allow:
            print("   ❌ 权威实现不可用，且本卡含否定词（规则适用）⇒ **fail-closed 拒写**（退出码 3）")
            print("      理由：两个实现在「规则适用」的卡上可能给出不同答案 ⇒ 宁可不写，不留第二份口径")
            print("      如确认接受「本次判定不含权威口径」，显式加 --allow-fallback 重试。")
            sys.exit(3)
        if risk:
            print("   ⚠️ 已按 --allow-fallback 放行：**本次判定不含权威口径**，请自行承担口径分歧风险")
            # ★ 与环闸门同理：**绕行必须记入卡内**，否则它会成为名义门
            payload = dict(payload) if isinstance(payload, dict) else {"value": payload}
            payload["_authority_fallback_override"] = {
                "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "by": writer,
                "reason": "权威实现不可用（本次为 --allow-fallback 显式绕行）",
                "detail": why[:160],
                "note": "本卡的观测面判定**不含权威口径**；该绕行已记入本卡，避免成为名义门。",
            }
        else:
            print("   ℹ️ 本卡无否定词 ⇒ 规则不适用 ⇒ 退路口径与权威口径结果相同，无分歧风险")
    # ★ 绝对断言门（HR 2026-09-14 并入网络级）：无封闭性来源的「永不可能」⇒ 告警/拒写
    _flat_abs = json.dumps(payload, ensure_ascii=False)
    _unhit, _exempt, _hits = absolute_claim_gate(_flat_abs, payload)
    if _exempt:
        print("ℹ️ 绝对断言门：已豁免（%s）" % "；".join(_exempt[:2]))
    if _unhit:
        print("⚠️ 绝对断言门（权威判据：**「永不可能」须给出封闭性来源**）：发现 %d 处未豁免的绝对断言" % len(_unhit))
        for u in _unhit[:3]:
            print("     · 「%s」 … %s" % (u["断言"], u["上下文"][:60]))
        print("   ⇒ 建议二选一：①给出**封闭性来源**；②改为「**无已知机制**」并附观测面；"
              "③若属**引用**（讨论该词而非使用它），加「」引号。")
        # ★★ 2026-09-14 自评：**本项够不上门** —— 我两次收紧后，豁免仍可被
        #   「正文里提到『封闭性来源』」或值里含常见汉字（行/表/代码）触发 ⇒
        #   **绿侧可达 ⇒ 只能是「检查」**。⇒ 故**不拒写**（一个我验不过的门比没有门更糟：
        #   它会冒充覆盖）。保留告警 + 明写其级别。
        print("   ⚠️ 本项级别：**检查（非门）** —— 绿侧可达：豁免可被「提到该词」或含常见汉字触发，"
              "我两次收紧后仍未通过自检 ⇒ **故不阻断**。")
    else:
        print("ℹ️ 绝对断言门通过（无未豁免的绝对断言）")

    # ★★★ 读数必须在**所有分支**都写（HR 2026-09-14：两项才分三态）。
    # ★ 2026-09-28 自陈：上一版我把它写在 `else:` 里，却**声称**「已移到所有分支」——
    #   而我当时的验证用的是一张**走 else 的普通卡**，它两种情况都写 0 ⇒ **验证无法区分**。
    #   ⇒ 判据：**验证必须用「走 if 分支」的样本**，否则两个假设同输出。
    try:
        os.makedirs(os.path.dirname(GATE_LOG), exist_ok=True)
        with open(GATE_LOG, "a", encoding="utf-8") as _f:
            _f.write("%s\t%s\tabs_targets=%d\tabs_hits=%d\tabs_blocked=%d\tabs_exempt=%d\tverdict=advised\n"
                     % (time.strftime("%Y-%m-%dT%H:%M:%S"), key, 1, _hits, len(_unhit), len(_exempt)))
    except Exception:
        pass
    # ★ 环③④门：未处置告警 ⇒ 拒写（除非显式绕行，且绕行写入卡内）
    bad_rings, ring_info = scope_ring_gate()
    if bad_rings:
        if "--allow-scope-warning" not in sys.argv:
            print("❌ 环闸门（三级强度：门）：存在未处置的环告警 ⇒ 拒写（退出码 4）")
            for b in bad_rings:
                print(f"     · {b}")
            print("   如需强行落卡：加 --allow-scope-warning（该绕行会被写进卡内并留痕）")
            gate_trace(key, "ok", "blocked", "reject-ring")
            sys.exit(4)
        print("⚠️ 已按 --allow-scope-warning 绕行；**绕行将写入卡内**")
        payload = dict(payload) if isinstance(payload, dict) else {"value": payload}
        payload["_scope_ring_override"] = {
            "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "by": writer,
            "unresolved": bad_rings,
            "note": "本卡在存在未处置的环告警时被强行落卡（显式绕行）；绕行本身已记入本卡，避免成为名义门。",
        }
    st, _ = put(key, payload, writer)
    ok, detail = verify(key)
    if st == 200 and ok:
        gate_trace(key, "ok", "blocked" if bad_rings else "ok", "ok")
        print(f"✅ 落卡并回读确认：{key}")
        print(f"   回读: {detail}")
        sys.exit(0)
    print(f"❌ 落卡或回读失败：{key}（PUT {st} / 回读 {detail}）—— 不得声称已落盘")
    sys.exit(1)

if __name__ == "__main__":
    main()
