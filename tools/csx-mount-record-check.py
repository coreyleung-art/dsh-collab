#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""csx-mount-record-check.py — 挂载记录（mount record）的判据 + 负控（星桥批准 C5）。

★ 立据：P1 的根 —— 统一日志此前 1719 行**零行**记录「本进程加载的是哪一版」，于是在役版本
  只有「人去调一次 csx_status」**单通道**。本判据把那条留痕变成**可机械核**的一行。
★ 本判据**不替代** T3 的在役实测：它证「某进程在 ts 时刻以 pid 加载了这组哈希」，
  须与 `ps` 的 boot 时刻联合判读。

两档：
  默认（结构档）：日志里**至少一条** mount 记录，且字段齐全、ts 是 RFC3339、sha256 形态合法。
  `--expect-current`（对盘面）：额外要求记录里的 version / entrySha256 / bundleSha256
   与**当前盘面**一致 —— 不一致即红，并在输出里点明**最可能的两种解释**
   （① mount 之后盘面被改过 ⇒ 在役仍跑旧代码，即 P1 的形态；② 该记录非本机最新）。

★ 覆盖面（**显式声明不覆盖什么** —— 照 qk-structure-guard 的惯例）：
  · 覆盖：`mode=serve` 记录的**存在性**、字段完整性、ts(RFC3339) 可解析性，以及与当前盘面的**同源性**。
  · **不覆盖**：① 「该 serve 记录确属**此刻正在服务**的那个进程」—— 记录只证"某进程在 ts 以 pid 加载了这组哈希"，
    须与 `ps` 的 boot 时刻**联合判读**；② 服务**行为**是否正确（只核留痕，不核语义）；
    ③ 非本插件写入的 mount 记录（本门只认 `plugin=context-survival` 的记录，别的记录不参与判定）。

★★ 一条**不得违反**的使用规则（星桥 2026-10-10 批准时逐字给定）：
  `--expect-current` 在**没有任何 serve 记录**时报红 —— 那**不是**回归失败，**
  它就是 P1 本身**（在役与盘面不同源 / 在役尚无留痕）。
  ⇒ **不得**为了让它变绿而：① 给 `--expect-current` 加"无 serve 则退回 any"的兜底；
     ② 把 `unknown` 当 `serve`；③ 默认 `serve`。
  三条都属「调参使门通过」，本文件用 `--selftest` 把这三条钉成**可跑判据**（见下）。

退出码：0 = 通过 · 1 = 违例 · 2 = 用法/环境错误
用法：
  python3 tools/csx-mount-record-check.py [--log <日志路径>] [--expect-current] [--plugin <插件目录>] [--quiet]
"""
import datetime
import hashlib
import json
import os
import re
import sys

DEFAULT_LOG = os.path.expanduser("~/dsh-collab/logs/dsh-plugin-context-survival.log")
HERE = os.path.expanduser("~/dsh-collab")


def ts():
    import datetime as _dt
    x = _dt.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    return x[:-2] + ":" + x[-2:]
DEFAULT_PLUGIN = os.path.expanduser("~/dsh-collab/devices/dsh-plugin-context-survival")
REQUIRED = ["mountId", "ts", "pid", "mode", "modeEvidence", "version", "entryModule", "entrySha256", "bundleSha256"]
# ★ mode 的三态语义（正证据判定，见 lib/meta.js::mountModeOf）：
#   serve   = Electron 宿主进程内加载（在役）· smoke = 本插件 CLI/冒烟路径 · unknown = 两者皆无正证据
#   ★ 检查器**绝不**把 unknown 当 serve —— 那正是"默认值即静默错误声明"的老病。
VALID_MODES = ("serve", "smoke", "unknown")
# `--mode any` 是**显式不过滤**（与"没给 --mode"的区别只在于写法，语义等价）；
# ★ 它存在是为了让"对盘面比较"这条路径可被单独测试：否则负控 M4/M5 会被 serve 筛选先拦下，
#   红是红了，但红的**不是被测的那条判据**（假红 = 另一种空转）。
ANY_MODE = "any"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def parse_args(argv):
    o = {"log": DEFAULT_LOG, "plugin": DEFAULT_PLUGIN, "expect_current": False, "quiet": False,
         "mode": None}   # None ⇒ 结构档不筛；--expect-current 时默认筛 serve（C4 强形式）
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--log":
            i += 1
            o["log"] = os.path.expanduser(argv[i])
        elif a == "--plugin":
            i += 1
            o["plugin"] = os.path.expanduser(argv[i])
        elif a == "--expect-current":
            o["expect_current"] = True
        elif a == "--mode":
            i += 1
            o["mode"] = argv[i]
        elif a == "--quiet":
            o["quiet"] = True
        else:
            print(f"用法错误：未知参数 {a}")
            return None
        i += 1
    return o


def last_mount_record(log_path, want_mode=None, prefer_serve=False):
    """从日志里取**最后一条** mount 记录（可选按 mode 过滤；坏行跳过并计数）。

    ★ 为什么要能按 mode 过滤（星桥审查位指出）：日志里**冒烟 pid 与服务 pid 混着**，
      直接取"最后一条"会给出一条**冒烟**记录，却让人以为证的是在役面 —— C4 的强形式要求**分清来源**。
    """
    if not os.path.isfile(log_path):
        return None, 0, f"日志不存在：{log_path}"
    rec, bad, matched = None, 0, 0
    total_lines = 0
    last_any, last_serve, fell_back = None, None, False
    with open(log_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            total_lines += 1
            if '"mounted"' not in line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                bad += 1
                continue
            if obj.get("line") != "mounted":
                continue
            matched += 1
            last_any = obj
            if obj.get("mode") == "serve":
                last_serve = obj
            if want_mode is not None and obj.get("mode") == want_mode:
                rec = obj
    # ★★ 判决新缺陷的修法：**默认（结构档）优先 serve** —— 否则会取到最后一条 **smoke** 记录，
    #   而 smoke 记录的 version 等于盘面 ⇒ 下游会报「同源 ⇒ 两半都已生效」，与同屏「夹具口径·不等于在役」**自相矛盾**。
    # ★ 三种情形分开（判决新缺陷的完整修法）：
    #   · 给了具体 mode（如 --expect-current ⇒ serve）⇒ 取**最后一条匹配**（循环里已设）
    #   · **未给 --mode**（结构档默认）⇒ **优先 serve**；无 serve 才回退 any，并标注回退
    #   · **显式 --mode any** ⇒ 老实取 last_any（否则它就不再是 any）
    if want_mode is None:
        if prefer_serve:
            if last_serve is not None:
                rec = last_serve
            else:
                rec, fell_back = last_any, (last_any is not None)
        else:
            rec = last_any
    picked_mode = None if rec is None else rec.get("mode")
    if fell_back:
        # 回退必须**显式标注**（否则读者以为拿到的就是服务记录）
        pass
    _surface = {"total_lines": total_lines, "mount_records": matched, "bad_lines": bad}
    return rec, bad, picked_mode, fell_back, _surface, (None if rec is not None or want_mode is None
                      else f"日志里有 {matched} 条 mount 记录，但**没有一条** mode={want_mode}"
                           f" ⇒ 不得据此声称在役面（这正是 C4 强形式要挡的：冒烟记录不能冒充服务记录）。"
                           f"★ 若在役尚未重启，**这条红是预期状态、就是 P1 的信号**："
                           f"不得为此放宽筛选、不得把 unknown 当 serve、不得默认 serve")


def find_serve_version(log_path=None):
    """取日志里**最后一条 serve 记录**的版本（供"所选非 serve 时"如实指出在役面凭据）。"""
    lp = log_path or DEFAULT_LOG
    if not os.path.isfile(lp):
        return None
    v = None
    with open(lp, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"mounted"' not in line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if obj.get("line") == "mounted" and obj.get("mode") == "serve":
                v = obj.get("version")
    return v


def sha_of(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def bundle_sha(plugin):
    lib = os.path.join(plugin, "lib")
    files = sorted(f for f in os.listdir(lib) if f.endswith(".js"))
    h = hashlib.sha256()
    h.update("\n".join(f"{f}:{sha_of(os.path.join(lib, f))}" for f in files).encode())
    return h.hexdigest(), len(files)


def want_mode(o):
    """结构档不筛；`--expect-current` 默认筛 serve（C4 强形式：冒烟记录不得冒充服务记录）。

    `--mode any` ⇒ 显式不过滤（供"只测对盘面比较"这条路径用）。
    """
    if o["mode"] is not None:
        return None if o["mode"] == ANY_MODE else o["mode"]
    return "serve" if o["expect_current"] else None


def check(o):
    bad = []
    want = want_mode(o)
    if want is not None and want not in VALID_MODES + (ANY_MODE,):
        return ([f"--mode 只接受 {VALID_MODES + (ANY_MODE,)}，收到 {want!r}"], None, {})
    if want == ANY_MODE:
        want = None
    _prefer = o.get("mode") is None          # 用户**没**显式给 --mode ⇒ 默认优先 serve
    _lmr = last_mount_record(o["log"], want, prefer_serve=_prefer)
    rec, bad_lines, err = _lmr[0], _lmr[1], _lmr[-1]
    _surface = _lmr[4] if len(_lmr) >= 6 else {}
    picked_mode = _lmr[2] if len(_lmr) >= 5 else (None if rec is None else rec.get("mode"))
    fell_back = _lmr[3] if len(_lmr) >= 5 else False
    if err:
        return [err], None, {}
    # ★★ 默认档（结构）**不得**在"没有 serve 记录"时静默回退并报通过 ——
    #   语料 INC-02 抓到：删掉 serve 记录的 `mode` 字段后，门会回退到别的（smoke）记录 ⇒ **假绿**。
    #   C4 强形式：**冒烟记录不得冒充服务记录**；无 serve 记录 ⇒ 如实判红（这正是 P1 的信号）。
    if o.get("mode") is None and (rec is None or rec.get("mode") != "serve"):
        bad.append("日志里**没有一条** mode=serve 记录（默认档要求 serve；无 serve 时**不得**回退并声称通过）"
                   " ⇒ 不得据此声称在役面（C4 强形式：冒烟记录不得冒充服务记录）")
    if bad_lines:
        bad.append(f"日志里有 {bad_lines} 行疑似 mount 记录但 JSON 解析失败（不可核 ⇒ 不算通过）")
    if rec is None:
        return ([f"日志里**没有任何** mount 记录（{o['log']}）⇒ 这条留痕缺失，在役版本仍无痕迹可查"], None, {})

    for k in REQUIRED:
        if rec.get(k) in (None, "", []):
            bad.append(f"记录缺必填字段 {k}（星桥 C2：版本 + 已加载模块 sha256 + mount 时刻 + pid）")
    if rec.get("mode") not in VALID_MODES:
        bad.append(f"mode 非法或缺：{rec.get('mode')!r}（须为 {VALID_MODES} 之一；unknown 是**诚实态**，不得省略）")
    if not isinstance(rec.get("modeEvidence"), str) or not rec.get("modeEvidence"):
        bad.append("缺 modeEvidence ⇒ mode 的判定依据不可核（不许只给结论不给依据）")
    if not isinstance(rec.get("pid"), int) or rec.get("pid", 0) <= 0:
        bad.append(f"pid 非正整数：{rec.get('pid')!r}")
    ts = rec.get("ts")
    if isinstance(ts, str):
        try:
            datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            bad.append(f"ts 不是 RFC3339：{ts!r}（C2 要求 mount 时刻可解析）")
    for k in ("entrySha256", "bundleSha256"):
        if isinstance(rec.get(k), str) and not HEX64.match(rec[k]):
            bad.append(f"{k} 不是 64 位十六进制：{rec.get(k)!r}")

    if o["expect_current"]:
        pkg = os.path.join(o["plugin"], "package.json")
        if not os.path.isfile(pkg):
            bad.append(f"对盘面检查失败：找不到 {pkg}")
        else:
            disk_ver = json.load(open(pkg, encoding="utf-8"))["version"]
            if rec.get("version") != disk_ver:
                bad.append(f"version 不一致：记录 {rec.get('version')} vs 盘面 {disk_ver}"
                           f" ⇒ 最可能是**盘面在 mount 之后被改过**（在役仍跑旧代码 —— 即 P1 的形态）；"
                           f"其次才是记录取自更早的一次 mount")
            disk_entry = sha_of(os.path.join(o["plugin"], "lib/index.js"))
            if rec.get("entrySha256") != disk_entry:
                bad.append(f"entrySha256 不一致：记录 {str(rec.get('entrySha256'))[:16]}… vs 盘面 {disk_entry[:16]}…"
                           f" ⇒ 同上：在役入口模块与当前盘面**不同源**")
            try:
                disk_bundle, n = bundle_sha(o["plugin"])
                if rec.get("bundleSha256") != disk_bundle:
                    bad.append(f"bundleSha256 不一致：记录 {str(rec.get('bundleSha256'))[:16]}… vs 盘面 {disk_bundle[:16]}…")
                elif rec.get("bundleFiles") is not None and rec.get("bundleFiles") != n:
                    bad.append(f"bundleFiles 不一致：记录 {rec.get('bundleFiles')} vs 盘面 {n}")
            except Exception as e:
                bad.append(f"对盘面复算 bundleSha256 失败：{e}")
    return bad, rec, {"picked_mode": picked_mode, "fell_back": fell_back, "surface": _surface}


def guard_switch_state():
    """读**段二授权的前置状态**：`enableGuard` 的当前值（从插件的 cordis.patch.yml 实读）。

    ★ 立据（短判决位 2026-10-10 判决 C）：「**解锁条件自己还有前置** —— 你写『宿主重启⇒应变绿』，
      而**重启本身卡在段二授权上**（`enableGuard` 属 profile 面）⇒ 读者会以为『只差一次重启』」
    ⇒ 解锁条件必须**自带它的前置**，且该前置**从盘面读出**（不写成作者的断言）。
    """
    import re as _re
    p = os.path.join(HERE, "devices/dsh-plugin-context-survival/cordis.patch.yml")
    import re as _re2
    # ★★ 判决方未核项①：原实现只有"读到 / 没读到"两态，异常覆盖是否穷尽无法判 ⇒
    #   现改**四态可判**，并把**判据面**（含项/排除项）写进返回说明里：
    #     ① 文件不存在 ② 读不到（异常，含类别） ③ 存在且可读但**没有该键** ④ 读到（值）
    #   ★ 判据面（如实声明）：**正则级**（`^\s*enableGuard\s*:\s*(\S+)`），
    #     **不是 YAML 解析** ⇒ 排除项：① 值写在**嵌套块**里（会被外层同名前缀匹配或漏掉）
    #     ② YAML 类型标注（`!!bool`）③ 多文档/锚点/别名 ④ 行内注释后的值形态异常。
    #     ★ 但**注释掉的行不会命中**（正则要求行首非 `#`）—— 这条已立断言。
    rel = os.path.relpath(p, HERE)
    if not os.path.isfile(p):
        return None, f"**状态①文件不存在**（{rel}）⇒ 本项不可判（不是「值为真/假」，是**无从读**）"
    try:
        txt = open(p, encoding="utf-8", errors="replace").read()
    except Exception as e:
        return None, f"**状态②读不到**（{rel}：{e.__class__.__name__}）⇒ 本项不可判"
    m = _re2.search(r"^\s*enableGuard\s*:\s*(\S+)", txt, _re.M)
    if m is None:
        return None, f"**状态③无该键**（{rel} 可读但没有 `enableGuard`）⇒ 不可判（不得默认成 false/true）"
    val = m.group(1).strip().strip('"\'')
    if val in ("", "#", None) or val.startswith("#"):
        return None, f"**状态④值非法**（`enableGuard: {val}` 取到空/注释）⇒ 不可判"
    return val, f"**状态④读到**（读自 {rel}；判据 = 正则级、**非 YAML 解析** ⇒ 嵌套块/类型标注/锚点不在判据面内）"


def classify(bad, rec, o):
    """把红**分类**并给出**解锁条件**。

    ★ 立据（短判决位 2026-10-10 判决 D 逐字要点）：正常路径的红**会一直挂到重启** ⇒ 风险是
      「**下一个读到的人去排查一个已知原因 ⇒ 正确的红退化成噪声**」；但**不能静音**（静音＝假绿）
      ⇒ 应带**解锁条件**（「宿主重启后须自动变绿」）+ 标注「本红＝段二阻塞的必然表现，非新缺陷」。
      ★ 这与给 EXEMPT_PERMANENT 加 `verify` 是**同一思路：让声明可失效**。
    """
    if rec is None:
        # 读不到 / 确实没有 —— 两者已在三态里分开（判决 A 验过），此处只归类
        if any("日志不存在" in b for b in bad):
            return ("不可判 —— **读不到**日志（不是「没有记录」）",
                    "解锁条件：给出正确日志路径后重跑；本类**不得**被读成「该插件没挂载」")
        return ("无记录 —— 日志可读但**没有任何 mount 记录**",
                "解锁条件：宿主启动并载入该插件后重现记录；此前在役面**不可判**")
    has_ver = any(b.startswith("version 不一致") for b in bad)
    sha_bad = [b for b in bad if "Sha256 不一致" in b or "bundleFiles 不一致" in b]
    if has_ver:
        gv, gw = guard_switch_state()
        # ★★ 措辞**随实读值分支**（判决规则：实算不写死）—— 授权已给时，门不得再指着已满足的前置喊"还差它"。
        _granted = str(gv).lower() in ("true", "yes", "1", "on")
        _pre = ("① **段二授权 —— 已给**"
                f"（**当前实读值 = `{gv}`**（{gw}）⇒ 该前置**已满足**）"
                "② **宿主重启 —— 唯一剩余前置** ⇒ 在役载入最新盘面版本 ⇒ 本门应**自动变绿**"
                if _granted else
                "① **段二授权** —— 属 profile/config 面，须用户裁决后由用户改；"
                f"**当前实读值 = `{gv if gv is not None else '未读到'}`**（{gw}）"
                "② **宿主重启** ⇒ 在役载入最新盘面版本 ⇒ 本门应**自动变绿**。"
                "⇒ **二者齐备才是「解锁」**（只说重启会让人以为「只差一次重启」）")
        return ("**已知原因（版本落后）** —— 盘面自 mount 之后被改过，在役仍跑旧代码；"
                "**本红＝段二阻塞的必然表现，非新缺陷**",
                f"★ 解锁条件（**含其前置**）：{_pre}；"
                "若重启后仍红 ⇒ 升级为真缺陷（可观测信号：**version 一致但 sha 不一致**）")
    if sha_bad:
        return ("★ **新缺陷** —— **version 一致却字节不同**：同版本不同源（例如重启后又在盘上直接改过、或记录被伪造）",
                "解锁条件：无（本类**不因重启而消失**）⇒ 须人工排查到字节级一致为止")
    return ("结构类违例（非版本落后）", "解锁条件：按上面逐条修；本类不因重启消失")


def selftest():
    _self_src_for_guard = open(os.path.abspath(__file__), encoding="utf-8").read()
    """★ 判据的判据：把「不许为消红而调参」钉成可跑断言（星桥批准时逐字要求）。"""
    fails = []
    def eq(name, got, want):
        if got != want:
            fails.append(f"{name}: got={got!r} want={want!r}")

    # ① --expect-current 默认必须筛 serve（不得退回 any）
    eq("expect-current 默认筛 serve", want_mode({"mode": None, "expect_current": True}), "serve")
    # ② 结构档不得筛（保持可读性：看最后一条即可）
    eq("结构档不筛", want_mode({"mode": None, "expect_current": False}), None)
    # ③ `--mode any` 是显式不过滤，且**不能**被当成 serve
    eq("--mode any ⇒ 不筛", want_mode({"mode": "any", "expect_current": True}), None)
    # ④ unknown 绝不能被当作 serve：构造只含 unknown 的日志 ⇒ 必须红
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False, encoding="utf-8") as fh:
        fh.write(json.dumps({"line": "mounted", "mountId": "x", "ts": "2026-10-10T00:00:00Z", "pid": 1,
                             "mode": "unknown", "modeEvidence": "无正证据", "version": "0.0.0",
                             "entryModule": "lib/index.js", "entrySha256": "0" * 64, "bundleSha256": "0" * 64},
                            ensure_ascii=False) + "\n")
        tmp = fh.name
    try:
        _r = last_mount_record(tmp, "serve")
        rec, err = _r[0], _r[-1]
        if rec is not None or err is None:
            fails.append("只含 unknown 的记录被当成了 serve（④ 假绿）")
    finally:
        os.unlink(tmp)

    # ★★ 分类器四态 + 一条反控（判决 D 的落实断言）——
    #    ★ 实测教训：这一段**第一版没进文件**（锚点没命中而我未核），于是"声称有断言"却是空的 ⇒ 现补上并核条数。
    c1, _ = classify(["version 不一致：记录 0.12.4 vs 盘面 0.12.9"], {"version": "0.12.4"}, {"expect_current": True})
    eq("分类①：版本落后 ⇒ 含『已知原因』", "已知原因" in c1, True)
    c2, _ = classify(["entrySha256 不一致：a vs b"], {"version": "0.12.9"}, {"expect_current": True})
    eq("分类②：**同版本不同字节** ⇒ 含『新缺陷』", "新缺陷" in c2, True)
    c3, _ = classify(["日志不存在：/nope"], None, {})
    eq("分类③：读不到 ⇒ 含『不可判』", "不可判" in c3, True)
    c4, _ = classify(["没有任何 mount 记录"], None, {})
    eq("分类④：确实没有 ⇒ 含『无记录』", "无记录" in c4, True)
    # ★★ 反控要判**标记词**，不能判裸子串 —— 实测：第一版用 `"新缺陷" in c1` 会**假红**，
    #    因为「已知原因」那句里含「**非**新缺陷」四字（子串命中）。⇒ 改用分类标记 `★ **新缺陷**` 与 `**已知原因`。
    eq("★ 反控：新缺陷分类**不得**带『已知原因』标记", "**已知原因" in c2, False)
    eq("★ 反控：已知原因分类**不得**带『★ **新缺陷**』标记", "★ **新缺陷**" in c1, False)
    # ★★ 解锁条件必须**自带前置**（判决 C）：用**标记词**「段二授权」判，不用裸子串
    _, unlock1 = classify(["version 不一致：记录 0.12.4 vs 盘面 0.12.10"], {"version": "0.12.4"}, {"expect_current": True})
    eq("★ 解锁条件自带前置：含『段二授权』标记", "段二授权" in unlock1, True)
    # ★ 判决 B：口径声明必须在**读者会看的输出**里（本件 = 挂载门 CLI）⇒ 用标记词判
    # ★★ 判决 C（第三次「查字符串」族）⇒ 这里**改成真跑**：不再是"源码里有这句话"，
    #   而是**运行本工具并核对它的输出**（顺带把"读者路径真的打印了那几行"也测了）。
    import subprocess as _sp

    def _run_out(args):
        _r = _sp.run([sys.executable, os.path.abspath(__file__)] + args, capture_output=True, text=True, timeout=120)
        return _r.returncode, (_r.stdout or "") + (_r.stderr or "")

    _rc1, _out1 = _run_out(["--log", "/definitely/not/here.log"])
    eq("真跑①读不到日志 ⇒ 非 0 且输出含『不可判』", (_rc1 != 0) and ("不可判" in _out1), True)
    eq("真跑①输出写明『读不到』而非『没有记录』", ("读不到" in _out1), True)

    _rc2, _out2 = _run_out(["--expect-current"])
    eq("真跑②正常路径 ⇒ 非 0（红灯照旧）", _rc2 != 0, True)
    eq("真跑②读者路径打印『口径』行", "口径" in _out2, True)
    eq("真跑②读者路径打印『生效条件（分别标）』", "生效条件（分别标）" in _out2, True)
    eq("真跑②解锁条件含『段二授权』且为实读值", ("段二授权" in _out2) and ("当前实读值" in _out2), True)
    eq("真跑②『不静音』声明在读者路径上", "不静音" in _out2, True)
    # ★ 我原来的断言**过度**了：`--expect-current` 只筛 serve ⇒ 输出里**只会**有「在役口径」；
    #   「夹具口径」要跑 smoke 才出现 ⇒ 分两次真跑，各自验证自己那一态（这是判据自身的精确化）。
    eq("真跑②(serve) ⇒ 输出含『在役口径』", "在役口径" in _out2, True)
    _rc3, _out3 = _run_out(["--mode", "smoke"])
    eq("真跑③(smoke) ⇒ 输出含『夹具口径』且写明『不等于在役』",
       ("夹具口径" in _out3) and ("不等于在役" in _out3), True)
    _, unlock2 = classify(["日志不存在：/nope"], None, {})
    eq("★ 反控：『不可判』的解锁**不得**牵扯段二授权（与授权无关的类别别乱加前置）", "段二授权" in unlock2, False)
    eq("★ 正控：两类标记各自出现（判据能分辨，不是都在绿）", ("**已知原因" in c1) and ("★ **新缺陷**" in c2), True)

    # ★★ 判决新缺陷的断言：① 默认（结构档）**优先 serve**；② 显式 `--mode any` ⇒ 取 any 且**不得**声称在役
    import tempfile as _tf2, json as _json2, subprocess as _sp2
    _l = _tf2.NamedTemporaryFile("w", suffix=".log", delete=False, encoding="utf-8")
    _l.write(_json2.dumps({"ts": "2026-10-10T00:00:00.000Z", "line": "mounted", "mode": "serve", "version": "0.0.1",
                           "pid": 1, "mountId": "s1", "entrySha256": "0" * 64, "bundleSha256": "0" * 64, "bundleFiles": 1}) + "\n")
    _l.write(_json2.dumps({"ts": "2026-10-10T00:01:00.000Z", "line": "mounted", "mode": "smoke", "version": "9.9.9",
                           "pid": 2, "mountId": "m1", "entrySha256": "0" * 64, "bundleSha256": "0" * 64, "bundleFiles": 1}) + "\n")
    _l.close()
    _rd = last_mount_record(_l.name, None, prefer_serve=True)
    eq("★ 默认优先 serve：末条是 smoke 也须取到 serve", (None if _rd[0] is None else _rd[0].get("mode")), "serve")
    _ra = last_mount_record(_l.name, None, prefer_serve=False)
    eq("★ 显式 any：老实取末条（smoke）", (None if _ra[0] is None else _ra[0].get("mode")), "smoke")
    _rr = _sp2.run([sys.executable, os.path.abspath(__file__), "--log", _l.name, "--mode", "any"],
                   capture_output=True, text=True, timeout=120)
    _oo = (_rr.stdout or "") + (_rr.stderr or "")
    eq("★ 显式 any 的产出：**须**出现『不能代表在役』", ("不能代表在役" in _oo), True)
    # ★★ 判决 2026-10-10：只查「新行在不在」**不够** —— 旧行（在役 / 同源⇒已生效）仍可能同屏
    #   ⇒ 判据必须是**缺席检查**（且固定串比对，不用正则 —— 星号会破坏正则语义）。
    eq("★★ 显式 any 的产出：**不得**出现『同源 ⇒ 两半都已生效』（旧行必须被跳过）",
       ("同源** ⇒ 两半都已生效" in _oo), False)
    _non_serve_ver = None if _ra[0] is None else _ra[0].get("version")
    # ★ 控制对：上面两条是**缺席检查**；这里合成一条「旧行」验证**检查本身对它敏感**。
    #   ★ 诚实记：我第一版的「有牙证明」是**沙箱环境导致的假红**（路径不同 ⇒ 红错了理由，无效）
    #     ⇒ 改成这条**对判据本身**做控制，而不是靠改环境。
    _sim = _oo + "  · ★ 实算版本：盘面 9.9.9 / 在役 9.9.9（**同源** ⇒ 两半都已生效）\n"
    eq("★ 控制对：把旧行合成回去 ⇒ 缺席检查**必须**对它敏感", ("同源** ⇒ 两半都已生效" in _sim), True)

    eq("★★ 显式 any 的产出：**不得**把所选（非 serve）记录的版本称作「在役」",
       (_non_serve_ver is not None) and (f"在役 **{_non_serve_ver}**" in _oo), False)
    os.unlink(_l.name)

    # ★★ 裁判 2026-10-10 的规矩（我采纳并机械化）：**配置注释里不得写死在役版本** ——
    #   「注释是文件的一部分，后人会当事实引用」⇒ 写死的数会过期；在役版本一律以实读为准。
    _cfg = os.path.join(HERE, "devices/dsh-plugin-context-survival/cordis.patch.yml")
    if os.path.isfile(_cfg):
        _txt = open(_cfg, encoding="utf-8").read()
        _hard = re.search(r"在役(仍是|版本仍是)?\s*\*{0,2}0\.\d+\.\d+", _txt)
        eq("★ 配置注释不得写死在役版本（裁判规矩：注释会被当事实引用）",
           None if _hard is None else _hard.group(0), None)

    # ★ 窄守卫（判决 2026-10-10 抓到孤立「上」字 ⇒ 编辑残留）：本件源码不得含「）上」这类断句残骸。
    #   ★ 用**拼接**构造被查字形，避免守卫自指命中（本文件里不出现连续的那两个字）。
    _junk = ("）" + "上") + '"'
    eq("★ 窄守卫：无编辑残留（「）上\"」这类断句残骸）", _junk in _self_src_for_guard, False)

    if fails:
        print("❌ --selftest 失败：")
        for f in fails:
            print("  " + f)
        return 1
    print("✅ --selftest 通过：默认筛 serve · unknown 不冒充 serve · any 仅显式启用 · "
          "分类四态（读不到/无记录/已知原因/新缺陷）+ 反控（标记词判据，不判裸子串）")
    return 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    o = parse_args(sys.argv)
    if o is None:
        return 2
    bad, rec, _meta = check(o)
    picked_mode = _meta.get("picked_mode", None if rec is None else rec.get("mode"))
    fell_back = bool(_meta.get("fell_back", False))
    if not o["quiet"]:
        print("csx-mount-record-check · 挂载留痕判据（**不改被核对象**；临时写面 = `guard/mutation-work/`）")
        # ★ 观测面**六要素**（判决采用的第六项：看不见的那部分**由谁兜着**）——本件同样适用：
        print("  观测面（六要素）：**含项** = ① 指定日志文件里**最后一条匹配 mode** 的 mount 记录"
              " ② 对盘面比对用的 package.json + lib/index.js + 整包 bundle（sha256）；"
              "**排除项** = ① 其它插件/其它目录 ② 未落盘的**运行期内存态**（如 guardStats，本件读不到）"
              " ③ 同一次 mount 之外的更早记录（只取最后一条）④ 非 tools/ 与插件目录的路径；"
              "**补偿控制** = ① 默认筛 serve（不把 smoke/unknown 当在役）② 读不到/无记录**都判红**（fail-closed）"
              " ③ 版本差与 sha 差**分类**、解锁条件**实读**配置（声明自身可失效）④ **不静音**：分类不改变判决；"
              f"**工具** = python3（读日志 + 对盘面复算 sha256）；**单位** = 记录 · 件；**时刻** = {ts()}")
        print(f"  日志：{o['log']}")
        if rec is not None:
            print(f"  最后一条 mount：ts={rec.get('ts')} · pid={rec.get('pid')} · version={rec.get('version')}"
                  f" · mountId={str(rec.get('mountId'))[:8]}…")
            print(f"    entrySha256={str(rec.get('entrySha256'))[:16]}… · bundleSha256={str(rec.get('bundleSha256'))[:16]}…"
                  f" · bundleFiles={rec.get('bundleFiles')}")
        w = want_mode(o)
        # ★★ 判决位 2026-10-10：「『0 命中』会被读成干净，是因为它在输出上和干净长得一样；
        #   把扫过的面打出来，两者才分得开。」⇒ 本门**必须**打印扫描面（行数 · mount 条数 · 解析失败行数）。
        _sf = _meta.get("surface", {}) or {}
        print(f"  · **扫描面**：日志 **{_sf.get('total_lines', '?')}** 行 · mount 记录 **{_sf.get('mount_records', '?')}** 条 · "
              f"JSON 解析失败 **{_sf.get('bad_lines', 0)}** 行 —— ★ **「0 条」与「读不到」在输出上必须可分**")
        # ★ 标签要反映**真实规则**（判决新缺陷：旧标签写 "mode=any"，而选择其实已改为"默认优先 serve"）
        if w is None:
            _rule = "**默认优先 serve**（无 serve 记录才回退 any）"
        else:
            _rule = f"mode={w}"
        print(f"  模式：{'结构 + 对盘面' if o['expect_current'] else '结构'} · 记录筛选：{_rule}"
              + (f" · **本次取到 mode={picked_mode}**" + ("（★ **回退**：日志里没有 serve 记录 ⇒ 不代表在役）" if fell_back else "")
                 if picked_mode is not None else ""))
        # ★★ 口径声明进**读者会看的那条输出**（短判决位 2026-10-10 判决 B：可以核但"这个具体位置没有"）：
        #   本判据读的是**挂载留痕**，而留痕的 `mode` 决定这条结论**属于哪种口径** ——
        #   只有 `mode=serve` 的记录才能支撑「在役面」的结论；`smoke` 记录**不等于在役**。
        _m = None if rec is None else rec.get("mode")
        _cal = {"serve": "**在役口径**（宿主启动时载入的版本）",
                "smoke": "**夹具口径** —— 真实进程内的假 ctx/假会话，**不等于在役**",
                "unknown": "**口径未证**（无正向证据 ⇒ 不得当作在役）",
                None: "**无记录**（无从谈口径）"}.get(_m, "**未知枚举值**")
        print(f"  · 口径：本判据读的是**挂载留痕**；所选记录的 `mode={_m}` ⇒ 结论成色 = {_cal}。"
              f"★ 若要判**在役面**，须只看 `mode=serve` 的记录（`--expect-current` 默认已筛 serve）")
        # ★★★★★ 判决（2026-10-10 最后一个递归）：**这个修复自身也需要一条口径声明** ——
        #   为防"读者误读口径"而加的口径行，**其中一半在真正需要它的在役面上看不到**（要看到它得先重启）。
        #   ⇒ 把「**哪半何时生效**」也算出来写在这里（读者唯一能同时看到两半的地方 = 本工具，因它读盘面 + 留痕）。
        try:
            _pkg = os.path.join(HERE, "devices/dsh-plugin-context-survival/package.json")
            _disk = json.load(open(_pkg, encoding="utf-8")).get("version")
        except Exception:
            _disk = None
        _served = None if rec is None else rec.get("version")
        # ★★ 判决新缺陷：**非 serve 记录不得声称在役**（否则与"夹具口径"那行自相矛盾）
        if picked_mode != "serve":
            print(f"  · **生效条件（分别标）**：★ 所选记录 `mode={picked_mode}`"
                  f"{'（**默认回退**：日志里没有 serve 记录）' if fell_back else ''}"
                  f" ⇒ **本行不能代表在役**；在役面须看 `mode=serve` 的记录"
                  f"（最近一条 serve 的版本 = **{_served if picked_mode == 'serve' else (find_serve_version() or '无')}**）。"
                  f"★ 实算版本：盘面 **{_disk}** / 所选记录 **{_served}** ⇒ **不得**由本条得出「已生效」")
        else:
            print(f"  · **生效条件（分别标）**：本行所属的**挂载门口径** = **盘面即生效**（新进程读盘面，无需重启）；"
                  f"而插件侧 `csx_status.caliber` 那段 = **须重启后**才在役可见。"
                  f"★ 实算版本：盘面 **{_disk}** / 在役 **{_served}**"
                  + ("（**同源** ⇒ 两半都已生效）" if _disk == _served and _disk is not None
                     else "（**不同源** ⇒ 插件侧那半**此刻在役不可见**）"
                          " ⇒ **报告两半时请分别标生效条件**，否则读者会以为都生效了；"
                          "★ 非死结：`csx_status` 一直报 `version`，读者可由版本自推「这不是新版」"))
    if bad:
        print("\n❌ 违例：")
        for b in bad:
            print("  " + b)
        cls, unlock = classify(bad, rec, o)
        print(f"\n  → **分类**：{cls}")
        print(f"  → {unlock}")
        print("  → ★ 本门**不静音**（静音＝假绿）：红灯照旧、退出码仍为 1；分类只改变**读者该做什么**，不改变判决。")
        return 1
    print("\n✅ 通过：mount 留痕字段齐全、ts 可解析；" + ("与当前盘面**同源**" if o["expect_current"] else "（未对盘面）"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
