#!/usr/bin/env python3
"""binding-check —— 把「绑定」从声明级变成可机检（2026-09-14 老登 aa528267）

立据（HR 2026-09-14 认领）：**「我的绑定一直是声明级，从未做过对象变异」**——
绑定写了，但没有任何东西**验证它真的会随对象变化而失效**。

本工具做第五方向「对象变异」的**静态前件**：给定一张卡，找出它声明过的
`(文件路径, sha256-16)` 对，**重算该文件当前哈希并比对**：
  · 一致   ⇒ 该绑定目前有效
  · 不一致 ⇒ **结论已失效**（对象变了，绑定没跟上）
  · 只有哈希没有路径 ⇒ **无法绑定**（记为未知，不猜）

强度声明：**门**（任一「已失效」 ⇒ 退出码 1）· 类别：**正确性**（防「已失效的结论被当有效读」）

用法: binding-check.py <黑板 key> | --file <path> [--json]
退出码: 0=全部有效 · 1=存在已失效绑定 · 2=未发现任何绑定（无从检查）
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, hashlib, json, os, re, sys, urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/binding-check.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

BB = os.environ.get("BB_BASE", "http://127.0.0.1:8792")


class FetchError(Exception):
    """取卡失败。**按语义分类**，不把三种不同的事压成一个读数。

    ★ 为什么单建一类（2026-09-28 修）：原实现直接抛 urllib 的 HTTPError，
    于是「键不存在」「键写法非法」「黑板不可达」在调用方看来**完全一样**
    —— 都是 `HTTPError: HTTP Error 404` 或一段 traceback。
    这与黑板契约冲突：**400=写法非法（键错）· 404=格式合法但不存在（内容缺失）**。
    更关键的是**不可达 ≠ 不存在**：把前者报成后者，就是我自己编目的
    「把环境的性质当成对象的性质」那一族错误。
    """
    def __init__(self, kind, msg):
        self.kind = kind          # 不存在 / 键非法 / 不可达 / 其它
        Exception.__init__(self, msg)
HASH_RE = re.compile(r"\b[0-9a-f]{16}\b")
PATH_RE = re.compile(r"(~/[\w./\u4e00-\u9fff-]+|/Users/[\w./\u4e00-\u9fff-]+|[\w./-]+\.(?:sh|py|js|json|md|yml|yaml))")


def fetch(key, path):
    if path:
        return json.load(open(os.path.expanduser(path), encoding="utf-8"))
    try:
        with urllib.request.urlopen(f"{BB}/{key}", timeout=15) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise FetchError("不存在",
                             "键不存在：%s —— 格式合法但无内容（404）。"
                             "注意：这**不是**写法错误，也不代表该对象从未存在过。" % key)
        if e.code == 400:
            raise FetchError("键非法",
                             "键写法非法：%s —— 首段须为纯小写字母 [a-z]+（400）。"
                             "400=键错 ≠ 404=内容缺失，二者处置方不同。" % key)
        raise FetchError("其它", "黑板返回 HTTP %s：%s" % (e.code, key))
    except urllib.error.URLError as e:
        raise FetchError("不可达",
                         "黑板**不可达**（%s）：%s ⇒ 本次**取不到**，"
                         "与「键不存在」是两件事，不得互相顶替。" % (e.reason, BB))
    except ValueError as e:
        raise FetchError("其它", "响应不是合法 JSON（%s）：%s" % (e, key))


SEARCH_DIRS = ["~/dsh-collab/scripts", "~/dsh-plugin-research/sysops/automation",
               "~/meituan-multi/scripts", os.path.expanduser("~")]


def resolve(p):
    """解析路径：先按原样；若是裸文件名，则在已知目录里搜（并记录解析方式）"""
    e = os.path.expanduser(p)
    if os.path.exists(e):
        return e, "原样"
    base = os.path.basename(p)
    for d in SEARCH_DIRS:
        cand = os.path.join(os.path.expanduser(d), base)
        if os.path.exists(cand):
            return cand, f"按裸名在 {d} 解析"
    return e, "未找到"


def sha16(p):
    try:
        with open(os.path.expanduser(p), "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except Exception:
        return None



# ★ v2（2026-09-14 HR 准予）：第三个选项 —— 引述命名空间。
#   立据（老登 A/B/C 实测）：门的通过集里只有「删证据」（B ⇒ exit 0），
#   而「引述写在声明命名空间」（A ⇒ exit 1）与「放进 citations」（C ⇒ exit 1）同样失败
#   ⇒ 第三个选项**当时不存在** ⇒ 门会**稳定地优化掉证据**（且驱逐是自我隐藏的：被删过证据的卡
#   与从来没有证据的卡**外观完全相同**）。
#   ⇒ 本版把 C 做出来。★ 两条设计约束：
#     ① 豁免面**闭合且最小**：只认精确键名 `citations`（不认同义词），
#        否则「无意豁免」⇒ 陈旧绑定被放过 ⇒ 假绿（对门而言是最危险方向）；
#     ② **不静默**：报告里显式给出「引用区」条数与近义键告警，
#        否则排除本身会变成一个新的、看不见的机制。
CITATIONS_KEY = "citations"
NEAR_MISS_KEYS = ("引述", "引用", "references", "reference", "Citation", "Citations")


def _resolve_source(src):
    """解析「出处」：黑板键（data/notes/tasks…）或文件路径。返回 (文本|None, 方式)。"""
    s = str(src).strip()
    if not s:
        return None, "空出处"
    if s.startswith(("data/", "notes/", "tasks/", "health/")):
        url = "http://127.0.0.1:8792/" + s
        try:
            with urllib.request.urlopen(url, timeout=6) as r:
                return r.read().decode("utf-8", "replace"), "黑板键"
        except Exception as e:
            return None, "黑板键不可解析(%s)" % type(e).__name__
    p = os.path.expanduser(s)
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                return f.read(), "文件"
        except Exception as e:
            return None, "文件读失败(%s)" % type(e).__name__
    return None, "路径不存在"


def strip_citations(obj, strict=False):
    """把**已核验**的 `citations` 条目换成占位符（其内哈希 ⇒ 不计为声明）。
    ★ v3（HR 2026-09-14 邀请）：须带**可解析的出处**，且出处里**确实含该哈希** ⇒ 才豁免。
      理由：v2 只要换个字段名就豁免 ⇒ 把真实声明写进 citations 即得假绿（绿侧可达）。
      现在豁免需要「出处可解析 ∧ 其中含该值」 ⇒ 从「作者断言」升级为「可核验事实」。
    ★ v4（HR 2026-09-14 准予）：`strict=True` ⇒ **一律不豁免** ⇒ **绿侧不可达 ⇒ 该模式是门**。
      两档并存：默认档容引述（**读数/检查**）· strict 档不容（**门**）。**模式必打印（不静默）**。
    ★ 未核验的条目**原样保留** ⇒ 其哈希按**声明**处理（宁红勿绿）。"""
    info = {"字段": [], "哈希条数": 0, "已豁免": 0, "未豁免": [],
            "模式": "strict（citations 一律不豁免）" if strict else "默认（citations 须出处可核验才豁免）"}
    if strict:
        def walk(o, path):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k == CITATIONS_KEY:
                        hs = HASH_RE.findall(json.dumps(v, ensure_ascii=False))
                        info["哈希条数"] += len(hs)
                        info["字段"].append({"字段路径": path + "/" + k,
                                             "条目": [{"哈希条数": len(hs), "豁免": False,
                                                       "理由": "strict：一律不豁免"}]})
                        if hs:
                            info["未豁免"].append({"哈希": hs, "理由": "strict：一律不豁免"})
                    walk(v, path + "/" + str(k))
            elif isinstance(o, list):
                for x in o:
                    walk(x, path + "/[]")
        walk(obj, "")
        info["近义键未识别"] = []
        return obj, info          # ★ 原样返回 ⇒ 引述全部按声明处理

    def check_entry(e):
        """返回 (是否豁免, 哈希列表, 说明)"""
        hs = HASH_RE.findall(json.dumps(e, ensure_ascii=False))
        if not hs:
            return None, [], "无哈希可豁免"
        if not isinstance(e, dict):
            return False, hs, "无出处（非 dict 条目）"
        src = e.get("出处") or e.get("source") or e.get("evidence")
        if not src:
            return False, hs, "缺「出处」"
        text, how = _resolve_source(src)
        if text is None:
            return False, hs, "出处%s" % how
        missing = [h for h in hs if h not in text]
        if missing:
            return False, hs, "出处可解析(%s)但**其中不含** %s" % (how, ",".join(missing))
        return True, hs, "出处可解析(%s)且含全部 %d 个哈希" % (how, len(hs))

    def rec(o, path):
        if isinstance(o, dict):
            out = {}
            for k, v in o.items():
                if k == CITATIONS_KEY:
                    items = v if isinstance(v, list) else [v]
                    newitems, entries = [], []
                    for e in items:
                        ok, hs, why = check_entry(e)
                        info["哈希条数"] += len(hs)
                        entries.append({"哈希条数": len(hs), "豁免": bool(ok), "理由": why})
                        if ok:
                            info["已豁免"] += len(hs)
                            newitems.append("<CITATION-EXEMPTED>")
                        else:
                            if hs:
                                info["未豁免"].append({"哈希": hs, "理由": why})
                            newitems.append(rec(e, path + "/" + k + "/[]"))
                    info["字段"].append({"字段路径": path + "/" + k, "条目": entries})
                    out[k] = newitems
                else:
                    out[k] = rec(v, path + "/" + str(k))
            return out
        if isinstance(o, list):
            return [rec(x, path + "/[]") for x in o]
        return o

    near = []

    def scan_near(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in NEAR_MISS_KEYS:
                    near.append(path + "/" + k)
                scan_near(v, path + "/" + str(k))
        elif isinstance(o, list):
            for x in o:
                scan_near(x, path + "/[]")

    scan_near(obj, "")
    info["近义键未识别"] = near
    return rec(obj, ""), info


def selftest():
    """★ 自测（真语料形态边界例）：正例=哈希一致 · 反例=哈希已失效 · 边界=只有哈希无路径。
    全部在临时文件上做，不触碰真实对象。
    """
    import tempfile, shutil
    T = tempfile.mkdtemp(prefix="binding-check-selftest-")
    try:
        obj = os.path.join(T, "obj.sh")
        open(obj, "w").write("#!/bin/bash\necho hi\n")
        real = sha16(obj)
        stale = "0" * 16
        # ★ 第三个选项（citations）的验收：HR 要求 **C 须有一条 must_pass 用例**（C 从 exit 1 变 exit 0）
        #   ——否则「第三个选项」只是声称存在。
        # ★ 且须有两条 must_reject 反向案例，证明豁免是**有界**的、不是把门整个打开：
        #   ① 同一张卡里 citations **之外**的陈旧哈希仍须 exit 1（豁免不得外溢）
        #   ② 近义键（如「引述」）**不得**被当作引用区（豁免面闭合）
        cases = [
            ("正例·声明哈希与对象一致", {"对象": obj, "哈希": real}, 0, None),
            ("反例·声明哈希已失效", {"对象": obj, "哈希": stale}, 1, None),
            ("边界·只有哈希无路径 ⇒ **声明了但绑不上**，故 3（不是 2=未声明）",
             {"哈希": stale, "无路径": True}, 3, None),
            ("★ must_pass·卡里**完全没有**哈希 ⇒ 未声明，仍 2（与上一例须可区分）",
             {"空卡": True}, 2, None),
            ("must_reject·路径不可解析 ⇒ 无法判定(3)", {"对象": "/tmp/__no_such_obj__.sh", "哈希": stale}, 3, None),
            ("★ must_pass·citations 条目**带可解析且含该值的出处** ⇒ 从 1 变 0",
             {"对象": obj, "哈希": real, "citations": [{"旧哈希": stale, "出处": os.path.join(T, "prov.txt")}]},
             0, "引用区豁免", []),
            ("★★ must_reject·**strict 档**下同一张卡**不再豁免** ⇒ 绿侧不可达（该档是门）",
             {"对象": obj, "哈希": real, "citations": [{"旧哈希": stale, "出处": os.path.join(T, "prov.txt")}]},
             1, None, ["--strict-citations"]),
            ("★ must_reject·citations 条目**缺出处** ⇒ 不豁免，按声明处理",
             {"对象": obj, "哈希": real, "citations": [{"旧哈希": stale}]}, 1, None),
            ("★ must_reject·出处**不可解析**（路径不存在）⇒ 不豁免",
             {"对象": obj, "哈希": real,
              "citations": [{"旧哈希": stale, "出处": os.path.join(T, "no_such_prov.txt")}]}, 1, None),
            ("★ must_reject·出处可解析但**其中不含该哈希** ⇒ 不豁免",
             {"对象": obj, "哈希": real,
              "citations": [{"旧哈希": stale, "出处": os.path.join(T, "empty_prov.txt")}]}, 1, None),
            ("★ must_reject·citations **之外**的陈旧哈希仍须失败（豁免不得外溢）",
             {"对象": obj, "哈希": real, "其它": "旧值 %s 见 %s" % (stale, obj)}, 1, None),
            ("★ must_reject·近义键「引述」**不得**被当作引用区（豁免面闭合）",
             {"对象": obj, "哈希": real, "引述": {"旧值": stale, "对象": obj}}, 1, None),
        ]
        # 出处样本：prov.txt **含**该哈希；empty_prov.txt **不含**
        open(os.path.join(T, "prov.txt"), "w").write("历史记录：旧哈希为 %s\n" % stale)
        open(os.path.join(T, "empty_prov.txt"), "w").write("这里没有那个哈希。\n")
        detail, ok = [], 0
        for idx, tup in enumerate(cases):
            name, spec, expect, note = tup[0], tup[1], tup[2], tup[3]
            extra_args = tup[4] if len(tup) > 4 else []
            if spec.get("空卡"):
                card = {"结论": "绑定测试", "说明": "这张卡不含任何哈希声明。"}
            elif spec.get("无路径"):
                card = {"结论": "绑定测试", "哈希": spec["哈希"]}
            else:
                card = {"结论": "绑定测试 \u2014 对象为 %s" % spec["对象"], "声明": spec["哈希"]}
            for extra in ("citations", "其它", "引述"):
                if extra in spec:
                    card[extra] = spec[extra]
            # ★ 每个用例**唯一文件名**（与今晚第三类共享可变状态缺陷同形的堵法：
            #   同名文件会让 A 用例跑成 B 用例）
            f = os.path.join(T, "card-%02d-%s.json" % (idx, name[:8].replace("/", "_")))
            json.dump(card, open(f, "w", encoding="utf-8"), ensure_ascii=False)
            import subprocess
            r = subprocess.run([sys.executable, __file__, "--file", f] + list(extra_args),
                               capture_output=True, text=True)
            good = (r.returncode == expect)
            # 附加断言：C 的豁免必须**被报出来**（不静默）
            if good and note == "引用区豁免":
                good = ("引用区" in r.stdout and "已豁免" in r.stdout)
            ok += good
            detail.append((name, good, r.returncode, expect))

        # ── ★ 新增：**取卡路径**（fetch）─────────────────────────────
        # 为什么单列：上面所有用例都走 `--file`，**从未经过 fetch()/网络路径**。
        # 于是「三种取卡失败被压成同一个读数」这个缺陷能在 11 个用例全绿下存活。
        # 纪律：一条没有被任何用例经过的路径 = 一条**未被检查过**的宣称。
        #
        # ★ 用**本地 stub 服务器**而不是真黑板：自测不得依赖外部服务是否在线，
        #   否则「网络不通」会被读成「被测对象坏了」（正是本组要防的那族混淆）。
        import http.server, threading
        class _Stub(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path.startswith("/bad"):
                    self.send_response(400); self.end_headers(); self.wfile.write(b"bad key")
                else:
                    self.send_response(404); self.end_headers(); self.wfile.write(b"nope")
            def log_message(self, *a):
                pass
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Stub)
        srv.daemon_threads = True
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        stub = "http://127.0.0.1:%d" % srv.server_address[1]
        fetch_cases = [
            ("must_reject·码4 键**不存在**(404) ⇒ 须报「不存在」而非「不可达」",
             stub, "notes/x/nope", 4, "取卡失败（不存在）", ["取卡失败（不可达）"]),
            ("must_reject·码4 键**写法非法**(400) ⇒ 须报「键非法」，不复用码2",
             stub, "bad/key", 4, "取卡失败（键非法）", []),
            ("must_reject·码4 黑板**不可达** ⇒ 须报「不可达」而非「不存在」",
             "http://127.0.0.1:9", "notes/x/whatever", 4,
             "取卡失败（不可达）", ["取卡失败（不存在）"]),
        ]
        outs = {}
        for name, base, key, expect, must_have, must_not in fetch_cases:
            env = dict(os.environ); env["BB_BASE"] = base
            import subprocess as _sp
            r = _sp.run([sys.executable, __file__, key],
                        capture_output=True, text=True, env=env)
            good = (r.returncode == expect) and (must_have in r.stdout) \
                and not any(m in r.stdout for m in must_not)
            outs[name] = r.stdout
            ok += good
            detail.append((name, good, r.returncode, expect))
        # ★ 差分断言：三种失败的**输出必须互不相同** —— 否则「分了类」只是装饰
        keys = sorted(outs)
        if len(set(outs[k] for k in keys)) == len(keys):
            ok += 1
            detail.append(("★ 取卡·三种失败输出互不相同（分类非装饰）", True, "-", "-"))
        else:
            detail.append(("★ 取卡·三种失败输出互不相同（分类非装饰）", False, "-", "-"))
        srv.shutdown()
        n_rej = sum(1 for d in detail if "must_reject" in d[0])
        n_rej_ok = sum(1 for d in detail if "must_reject" in d[0] and d[1])
        n_pas = sum(1 for d in detail if "must_pass" in d[0])
        n_pas_ok = sum(1 for d in detail if "must_pass" in d[0] and d[1])
        return ok, len(cases) + len(fetch_cases) + 1, detail, (n_rej_ok, n_rej, n_pas_ok, n_pas)
    finally:
        shutil.rmtree(T, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("key", nargs="?")
    ap.add_argument("--file")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--window", type=int, default=200, help="哈希向前回溯多少字符找路径")
    ap.add_argument("--strict-citations", action="store_true",
                    help="★ 门档：citations 一律不豁免 ⇒ 绿侧不可达")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        ok, tot, detail, shape = selftest()
        for n, good, got, exp in detail:
            print(f"  {'✅' if good else '❌'} {n}  期望 exit={exp} / 实得 {got}")
        print(f"\nselftest {ok}/{tot}（正例=一致 · 反例=已失效 · 边界=仅有哈希）")
        # ★ 覆盖形态（不是总数）：只报总数会掩盖不对称 ——
        #   一个「什么都拒绝」的实现与正确实现读数完全相同。
        print("覆盖形态: must_reject %d/%d · must_pass %d/%d"
              % (shape[0], shape[1], shape[2], shape[3]))
        if shape[3] == 0:
            print("  ⚠️ must_pass 用例数=0 ⇒ 本测**无法区分**「正确实现」与「一律拒绝的实现」")
        sys.exit(0 if ok == tot else 2)
    if not a.key and not a.file:
        print(__doc__); sys.exit(2)
    try:
        d = fetch(a.key, a.file)
    except FetchError as e:
        # ★ 码 4：**取不到卡**。与码 2（拿到了卡但卡里没有绑定）语义不同，故不复用 2。
        #   判据：「我没拿到对象」与「对象里没有我要的东西」是两个不同的处置动作
        #   —— 前者去查键/查网络，后者去查那张卡本身。
        print("❌ 取卡失败（%s）：%s" % (e.kind, e))
        sys.exit(4)
    except FileNotFoundError as e:
        print("❌ 本地文件不存在（%s）：%s" % (e.__class__.__name__, e))
        sys.exit(4)
    except json.JSONDecodeError as e:
        print("❌ 卡不是合法 JSON：%s" % e)
        sys.exit(4)
    d_stripped, cit = strip_citations(d, strict=a.strict_citations)
    text = json.dumps(d_stripped, ensure_ascii=False)

    pairs, orphans = [], []
    for m in HASH_RE.finditer(text):
        h = m.group(0)
        seg = text[max(0, m.start() - a.window):m.start()]
        paths = PATH_RE.findall(seg)
        if not paths:
            orphans.append(h); continue
        p = paths[-1]
        rp, how = resolve(p)
        cur = sha16(rp)
        pairs.append({"声明哈希": h, "对象": p, "解析到": rp, "解析方式": how,
                      "当前哈希": cur, "一致": (cur == h) if cur else None})
    res = {"来源": a.file or a.key, "绑定对": pairs,
           "只有哈希无路径": orphans,
           "引用区": cit,
           "说明": "「只有哈希无路径」的项**无法绑定** ⇒ 记未知，不猜（符合「无确证即记未知」）；"
                   "`citations` 子树内的哈希为**引述**，不计为声明（第三个选项，HR 2026-09-14 准予）"}
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        print(f"绑定机检 · {res['来源']}")
        if cit["字段"]:
            print(f"  ℹ️ 引用区：{len(cit['字段'])} 处 · 哈希 {cit['哈希条数']} 个 · 模式 {cit['模式']} · "
                  f"**已豁免 {cit['已豁免']}**（须出处可解析且含该值）")
            for u in cit["未豁免"]:
                print(f"     ⚠️ **未豁免** {','.join(u['哈希'])} ⇒ 按**声明**处理（原因：{u['理由']}）")
            if cit["哈希条数"] == 0:
                print("     ★ 注意：citations 字段存在但**其内无哈希** ⇒ 本次豁免量为 0（0 条 ≠ 未测）")
        if cit["近义键未识别"]:
            print(f"  ⚠️ 近义键**未被识别**为引用区：{', '.join(cit['近义键未识别'])}"
                  f" ⇒ 其内哈希仍按声明处理（豁免面闭合，只认精确键 `{CITATIONS_KEY}`）")
        if not pairs and not orphans:
            print("  ⚠️ 未发现任何 `(路径, sha256-16)` 声明 ⇒ **无从检查**（本卡的绑定可能只是文字描述）")
        for p in pairs:
            if p["一致"] is True:
                print(f"  ✅ 有效   {p['解析到']}  声明 {p['声明哈希']} = 当前 {p['当前哈希']}")
            elif p["一致"] is False:
                print(f"  ❌ **已失效** {p['解析到']}  声明 {p['声明哈希']} ≠ 当前 {p['当前哈希']}")
            else:
                print(f"  ❓ **无法判定** {p['对象']}（{p['解析方式']}）声明 {p['声明哈希']}")
        for h in orphans:
            print(f"  ⚠️ 仅哈希无路径 ⇒ **无法绑定**：{h}")
    failed = [p for p in pairs if p["一致"] is False]
    undet = [p for p in pairs if p["一致"] is None]
    ok = [p for p in pairs if p["一致"] is True]
    if failed:
        sys.exit(1)                      # 存在已失效绑定
    if undet:
        sys.exit(3)                      # ★ 存在无法判定 ⇒ **不得当通过**（确定不了 ≠ 通过）
    if not pairs and not orphans:
        sys.exit(2)                      # 卡里**根本没声明**哈希 ⇒ 未发现任何绑定
    if not pairs:
        # ★ 卡里**声明了**哈希，只是没有可绑定的路径 ⇒ 这不是「未发现」，
        #   是「**已声明但无法判定**」（工具自己就把它们打成 ❓/无法绑定）。
        #   原实现与上一行共用一个码 2，于是把「你没声明」与「你声明了我绑不上」
        #   报成同一个读数 —— 同族错误（把两种不同语义压进一个读数）。
        sys.exit(3)
    sys.exit(0)                          # 至少一项验证通过且无失效/无无法判定


if __name__ == "__main__":
    main()
