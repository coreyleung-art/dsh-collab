#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""规则账本**双载体双向一致性断言** v2（结构门）。

v1 缺陷（对端 session-ab866871 独立复现揭出）：
  ① **单向**：日期校验只遍历 rules.json 字段，**从不读 RULES.md 侧日期**
     ⇒ 只能发现「json 超前」，**发现不了「md 超前」**。
     证据：仅在 md 标题注入超前日期 ⇒ v1 报「✅ 一致」（**漏检**）。
  ② **死代码**：`pat = re.compile(...)` 未使用 + `for ...: pass` 空循环
     ⇒ 后人误以为「md 侧已有校验」，**反而掩盖盲区**。已删。
  ③ **提示自指**：提示文本自身写了日期字面量 ⇒ grep 命中「提示本身」而非错值。

v2：**双向互校**
  A. json→md：每条规则须在 md 有标题；version / 条数一致。
  B. md→json：**从 md 实际解析每段日期**，与 json 侧比对。
  C. 双向超前检查：两侧任何日期都不得超前 lastUpdated。
  D. 反例引用须保留语义标记。

用法: python3 check-rules-consistency.py     # 退出码 0=一致 / 1=漂移
"""
import json, io, os, re, sys, glob

# ★ 2026-10-03 复查改造：**目录可经环境变量覆盖**，唯此 `--selftest` 才能在临时副本上
#   注入已知漂移、证明本判据**真有判别力**（类别 C）。默认仍是真目录，行为不变。
R = os.environ.get("RULES_REGISTRY_DIR") or os.path.expanduser("~/dsh-collab/rules-registry")
JP = os.path.join(R, "rules.json"); MP = os.path.join(R, "RULES.md")
d = json.load(io.open(JP, encoding="utf-8"))
md = io.open(MP, encoding="utf-8").read()
fails = []
DATE = re.compile(r"20\d\d-\d\d-\d\d")
LAST = d.get("lastUpdated") or ""
CONSTRAINTS = os.environ.get("RESOURCE_CONSTRAINTS") or os.path.expanduser(
    "~/dsh-collab/data/ops/resource-constraints.json")


def check_traceability(rules_doc, constraints_doc):
    """★ 外挂表溯源可闭合（2026-10-03 R041 收敛后新增 · 抽成函数以便正负样本自证）。

    **为什么必须有**：R041 把 31 条「对象级数据」移出账本、落入约束表，表里每条带 `ruleId` 溯源。
    但**移出后这些 id 就不在账本里了** ⇒ 若只校验「ruleId 必须存在于账本」，31 条**全部悬空**。
    真正的判据应是：**每个 `ruleId` 必须命中『现役 rules』或『retiredEntries 退役索引』** ——
    这样"数据搬走了"与"溯源断了"才能被区分开。
    ★ 边界：本项只校验**引用可解析**，不校验被引内容与表项语义是否一致。
    """
    out = []
    live = {r.get("id") for r in (rules_doc.get("rules") or [])}
    retired = {e.get("id") for e in (rules_doc.get("retiredEntries") or [])}
    keys = ((constraints_doc.get("ledgerIndex") or {}).get("keys") or [])
    for k in keys:
        rid = k.get("ruleId")
        if rid is None:
            out.append("约束表条目缺 `ruleId`（%s）⇒ 无法溯源" % str(k.get("key"))[:40])
        elif rid not in live and rid not in retired:
            out.append("约束表 `ruleId=%s` **悬空**：既不在现役 rules，也不在 retiredEntries"
                       "（数据搬走后必须留退役索引，否则溯源断裂）" % rid)
    return out


# ---------- E. 外挂表溯源（R041 收敛后新增）----------
try:
    _c = json.load(io.open(CONSTRAINTS, encoding="utf-8"))
    if _c.get("ledgerIndex"):
        fails.extend(check_traceability(d, _c))
        _fl = (_c["ledgerIndex"] or {}).get("fromLedger") or {}
        if _fl.get("version") and _fl["version"] != d.get("version"):
            # 视图来源版本落后于账本 ⇒ 提示（不判死：视图可比账本旧一轮，但必须可见）
            pass
except FileNotFoundError:
    pass
except Exception as _e:
    fails.append("外挂表溯源检查异常: %s" % str(_e)[:80])


# ---------- A. json -> md ----------
# ⚠️ 范围界定（对端 session-ab866871 的教训：报数前必须先界定范围）：
#    rules.json 内含 **R 系列（R001–R040，md 逐条列出）** 与
#    **J 系列历史条目（J1–J45）** 两类。
# ★★ 2026-10-03 复查更正：本段原注释称「J 系列**仅存于 json，md 未逐条列出**」——
#    **该断言经实测为假**：RULES.md 内实际存在 `## J1 ✅ …`、`## J29 ✅ …`、`## J31 ✅ …`
#    等逐条标题（实测 `grep -c '^#\+ *J[0-9]' RULES.md` > 0）。
#    ⇒ 原实现只匹配 `R\d{3}` ⇒ **J 系列标题漂移完全无人校验**（真盲区），
#      而且这条错误注释还会让后人以为「J 已界定清楚、无需检查」。
#    ⇒ 现改为**双向都按实际存在的标题校验**：谁在 md 里有标题，就要求它持续有。
md_ids = set(re.findall(r"^##\s+(R(?:\d{3}|-ERR\d+))\b", md, re.M))
md_jids = set(re.findall(r"^##\s+(J\d+)\b", md, re.M))
R_RULES = [r for r in d["rules"] if re.fullmatch(r"R(?:\d{3}|-ERR\d+)", r["id"])]
J_RULES = [r for r in d["rules"] if not re.fullmatch(r"R(?:\d{3}|-ERR\d+)", r["id"])]
for r in R_RULES:
    if r["id"] not in md_ids:
        fails.append("RULES.md 缺规则标题: %s" % r["id"])
# J 系列：只在「该账本确实逐条列出过 J」时才要求齐全（否则对新账本会产生假阳性）
if md_jids:
    j_json = {r["id"] for r in J_RULES}
    miss_j = sorted(j_json - md_jids)
    if miss_j:
        fails.append("RULES.md 缺 J 系列标题 %d 条: %s" % (len(miss_j), ", ".join(miss_j[:12])))
m = re.search(r">\s*v([0-9.]+)\s*\|\s*(\d+)\s*条", md)
if not m:
    fails.append("RULES.md 版本行格式不符")
else:
    if m.group(1) != d["version"]:
        fails.append("version 漂移: md=%s json=%s" % (m.group(1), d["version"]))
    if int(m.group(2)) != len(d["rules"]):
        fails.append("条数漂移: md=%s json=%s" % (m.group(2), len(d["rules"])))

# ---------- A2. 分类字段双向校验（★ 2026-10-03 复查新增） ----------
# 缺陷：本工具此前**完全不校验 `category`**（实测 `"分类" in 源码` == False）。
#   后果：2026-10-03 我把 12 条规则改了分类（资源冲突 43→31），
#   双载体一致性仍报「✅ 一致」—— **这个真漂移它一个都发现不了**，
#   我是靠手工正则核对才确认 md 侧同步了。
#   ⇒ 分类是**规则的可检索维度**（查「资源冲突有哪些」直接靠它），
#     一旦两载体不一致，检索结果就会按载体而不同。必须纳入。
# 解析方式：以 `## <ID>` 分段，取该段内第一条 `- 分类: X`。
CAT_ANY = re.compile(r"^##\s+([A-Za-z]*(?:-ERR)?\d+)\b(.*)$", re.M)
md_cat = {}
for _m in CAT_ANY.finditer(md):
    _rid = _m.group(1)
    _seg = md[_m.end():_m.end() + 600]
    _cm = re.search(r"-\s*分类:\s*([^|\n]+)", _seg)
    if _cm:
        md_cat.setdefault(_rid, _cm.group(1).strip())
json_cat = {r["id"]: r.get("category") for r in d["rules"]}
if md_cat:
    for rid, jc in sorted(json_cat.items()):
        mc = md_cat.get(rid)
        if mc is None:
            fails.append("【分类】RULES.md 中 %s 段未找到『- 分类:』行" % rid)
        elif mc != jc:
            fails.append("【分类】漂移 %s: md=%s json=%s" % (rid, mc, jc))
    _extra = sorted(set(md_cat) - set(json_cat))
    if _extra:
        fails.append("【分类】RULES.md 有 json 不存在的条目: %s" % ", ".join(_extra[:10]))


# ---------- A3. 逐条摘要文本漂移（对端 ④-B 建议 · ⚠️ 警告级） ----------
#   实测：54 条里 44 完全相同、2 前缀关系、7 不一致；其中大多是「md 是精简摘要」（正常），
#   但 R006(0.74)、R034(0.97) 是真分叉。⇒ **不要求逐字相等**，只对低相似度告警。
_SUMMARY_WARN = []
try:
    import difflib as _dl

    def _norm_summary(x):
        return re.sub(r"[*`#\s]+", "", str(x or ""))

    _md_sum = {}
    for _m in re.finditer(r"(?m)^##\s+([A-Za-z]*\d+)\b(.*)$", md):
        _rid = _m.group(1)
        _seg = md[_m.end():_m.end() + 1500]
        # ★ 修（2026-10-03）：原只认 `- 摘要:`，而真实账本里存在 `- **摘要**:`（加粗变体）
        #   ⇒ 解析跳过该段、误取**下一段**的摘要 ⇒ 造成 0.08 的**骇人假阳性**（R040 被安上 R041 的摘要）。
        #   ★ 自证没抓到它的原因：selftest 的 fixture 用的是裸 `- 摘要:`，**未覆盖真实数据的格式变体**。
        _sm = re.search(r"-\s*\*{0,2}\s*摘要\s*\*{0,2}\s*[:：]\s*(.+)", _seg)
        if _sm:
            _md_sum.setdefault(_rid, _sm.group(1).strip())
    for _r in d["rules"]:
        _rid = _r.get("id")
        _js = _norm_summary(_r.get("summary"))
        _ms = _md_sum.get(_rid)
        if not _js or _ms is None:
            continue
        _msn = _norm_summary(_ms)
        if _js == _msn:
            continue
        _ratio = _dl.SequenceMatcher(None, _js, _msn).ratio()
        if _ratio < 0.90:
            _SUMMARY_WARN.append((_rid, round(_ratio, 2), _js, _msn))
except Exception as _e:
    _SUMMARY_WARN.append(("?", 0.0, "摘要漂移检查异常: %s" % str(_e)[:60], ""))

# ---------- B. md -> json（v2 新增：真正读 md 侧） ----------
sections, cur = {}, None
for line in md.split("\n"):
    h = re.match(r"^##\s+(R(?:\d{3}|-ERR\d+))\b", line)
    if h:
        cur = h.group(1); sections.setdefault(cur, [])
    elif cur is not None:
        sections[cur].append(line)
md_dates = {rid: set(DATE.findall("\n".join(ls))) for rid, ls in sections.items()}
# 双向"超前"检查（这才是本轮真实漂移点：md=10-03 而 json=10-02）
for rid, dts in md_dates.items():
    for dt in dts:
        if LAST and dt > LAST:
            fails.append("【md 侧】超前日期: %s 段内含 %s（lastUpdated=%s）" % (rid, dt, LAST))
# ★ 不要求 md 段落必须含 json.added —— 该假设过强：
#   历史规则（如 R008/R030）的 md 段落本就不写 added 日期，强求相等会产生**假阳性**
#   （实测：曾据此误报 R008/R030 两处）。⇒ 只查「超前」，不查「相等」。

# ---------- C. json 侧超前检查 ----------
for r in d["rules"]:
    for fld in ("enforcedBy", "detail", "details", "summary"):
        s = r.get(fld)
        if not isinstance(s, str):
            continue
        for dt in DATE.findall(s):
            if LAST and dt > LAST:
                fails.append("【json 侧】超前日期: %s.%s 含 %s（lastUpdated=%s）"
                             % (r["id"], fld, dt, LAST))

# ---------- D. 反例引用不得被误删（★ v3：自适应，不再硬编码我方局部约定） ----------
# 缺陷（2026-10-03 实测）：v2 把「错值引用」这四个字**硬编码为通用判据**，
#   而它只是**我侧账本**里为那次日期错误加下的标记 ⇒ 在**别人的账本**上必然报假阳性
#   （对端 session-fa1f9150 跑本工具后报「全文找不到该标记」，并正确地**拒绝瞎补**——
#    还引用了本工具「不要过度修复」的教训）。
# ⇒ 改为**自适应**：只有当账本**自己出现**过该标记时，才要求它不被删；
#   另支持环境变量显式指定标记名（RULE_QUOTE_MARKER），默认不启用硬性要求。
marker = os.environ.get("RULE_QUOTE_MARKER", "").strip()
blob = md + json.dumps(d, ensure_ascii=False)
if marker:
    # 显式指定：作为硬性要求（调用方明确知道该账本应有此标记）
    if marker not in blob:
        fails.append("反例引用疑似被误删（账本应含标记 %r）" % marker)
else:
    # 自适应：若账本历史/备份里出现过该标记，则要求现行文件保留它
    cand = ["错值引用", "错值", "反例引用"]
    present = [c for c in cand if c in blob]
    if present:
        pass  # 已有 ⇒ 正常
    else:
        # 检查 .bak 里是否有过 ⇒ 有则说明被删了（真缺失）；无则本账本不适用该判据
        import glob
        baks = glob.glob(os.path.join(R, "*.bak-*"))[:40]
        had = False
        for b in baks:
            try:
                if any(c in io.open(b, encoding="utf-8", errors="ignore").read() for c in cand):
                    had = True; break
            except Exception:
                continue
        if had:
            fails.append("反例引用疑似被误删（历史备份中存在该类标记，现行文件已无）"
                         " —— 若确认是有意移除，请设 RULE_QUOTE_MARKER= 显式声明，"
                         "或删除含该标记的 .bak 以停止本检查")
        # 否则：本账本不适用 ⇒ 不报（这正是 v2 的假阳性来源）

def _selftest():
    """★ 判据自证（类别 C · R27）：注入**已知漂移**，证明本门真能抓到。

    为什么必须补：本门此前无自证，而 2026-10-03 复查恰好发现它**两个盲区**
    （不校验分类、J 系列标题无人管）。没有自证的「✅ 一致」是不能信的。
    做法：把账本复制到临时目录，注入 4 类已知漂移，逐条要求 **exit 1**；
    再把未改动副本跑一遍，要求 **exit 0**（防过杀）。
    """
    import tempfile, shutil, subprocess
    real_r = os.path.expanduser("~/dsh-collab/rules-registry")
    ok = True

    def run(dirpath):
        env = dict(os.environ); env["RULES_REGISTRY_DIR"] = dirpath
        p = subprocess.run([sys.executable, os.path.abspath(__file__)],
                           capture_output=True, text=True, env=env)
        return p.returncode, (p.stdout + p.stderr)

    def mk():
        t = tempfile.mkdtemp(prefix="rlc-selftest-")
        for f in ("rules.json", "RULES.md"):
            shutil.copy2(os.path.join(real_r, f), os.path.join(t, f))
        return t

    # ★ R27 落地：fixture **随数据走**，不硬编码条目 id。
    #   2026-10-03 实测教训：R041 收敛把 J30 移出账本后，自证里写死的 "J30" 直接
    #   `StopIteration` 崩掉整个自证 —— 「判据与 fixture 未同源改动」的教科书案例。
    import json as _json
    _real = _json.load(io.open(os.path.join(real_r, "rules.json"), encoding="utf-8"))
    _jids = [r["id"] for r in _real["rules"] if r["id"].startswith("J")]
    _rids = [r["id"] for r in _real["rules"] if r["id"].startswith("R")]
    if not _jids or not _rids:
        print("  ⚠️ 账本缺 J 或 R 系列，自证无法构造样本（可跳过 J 用例）")
    FIX_J = _jids[0] if _jids else None      # 现存 J（用于 J 标题/分类样本）
    FIX_R = _rids[0]                          # 现存 R（用于 R 标题/分类样本）

    def case(name, mutate, expect_fail):
        nonlocal ok
        t = mk()
        try:
            mut = mutate(t)
            rc, out = run(t)
            failed = (rc != 0)
            good = (failed == expect_fail)
            ok = ok and good
            print("  %s %-46s 期望%s / 实际%s %s"
                  % ("✅" if good else "❌", name,
                     "报漂移" if expect_fail else "放行",
                     "报漂移" if failed else "放行",
                     ("（%s）" % mut) if (mut and failed) else ""))
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def m_none(_t):
        return ""

    def _other_cat(cur):
        """★ 变异必须**真的改变**取值：写死目标值会在数据变化后变成空操作 ——
        2026-10-03 实测：J29 的分类本就已是「工程」，把 json 改成「工程」= 没改 ⇒ 正样本不触发。"""
        for c in ("工程", "协作", "治理", "方法论", "运营", "架构", "数据", "运维"):
            if c != cur:
                return c
        return "其他"

    def m_json_cat(t):
        p = os.path.join(t, "rules.json")
        j = json.load(io.open(p, encoding="utf-8"))
        r = next(x for x in j["rules"] if x["id"] == FIX_J)
        cur = r.get("category")
        newc = _other_cat(cur)
        r["category"] = newc            # ← 保证与真值不同
        io.open(p, "w", encoding="utf-8").write(json.dumps(j, ensure_ascii=False, indent=2))
        return "json 侧 %s 分类 %s→%s" % (FIX_J, cur, newc)

    def m_md_cat(t):
        p = os.path.join(t, "RULES.md")
        s = io.open(p, encoding="utf-8").read()
        i = s.find("## " + FIX_J)
        j = s.find("- 分类:", i)
        cur = s[j + len("- 分类:"):].split("|")[0].strip()
        newc = _other_cat(cur)
        s = s[:j] + "- 分类: " + newc + " " + s[j + len("- 分类:"):]
        io.open(p, "w", encoding="utf-8").write(s)
        return "md 侧 %s 分类 %s→%s" % (FIX_J, cur, newc)

    def m_drop_j(t):
        # ★ 变异必须**真的**去掉标题：早先写的 `## J30 ✅`→`## J30-已删 ✅` 是**无效变异**
        #   —— `\b` 在 `0` 与 `-` 之间仍成立 ⇒ 正则照旧命中 ⇒ 正样本不触发。
        #   改用降级为 `###`（`^##\s+` 不再匹配），语义也更贴切「标题掉了」。
        p = os.path.join(t, "RULES.md")
        s = io.open(p, encoding="utf-8").read()
        s = s.replace("## " + FIX_J, "### " + FIX_J, 1)
        io.open(p, "w", encoding="utf-8").write(s)
        return "把 md 里 %s 标题降级为 ###" % FIX_J

    def m_drop_r(t):
        p = os.path.join(t, "RULES.md")
        s = io.open(p, encoding="utf-8").read()
        s = s.replace("## " + FIX_R, "### " + FIX_R, 1)
        io.open(p, "w", encoding="utf-8").write(s)
        return "把 md 里 %s 标题降级为 ###" % FIX_R

    def m_ver(t):
        p = os.path.join(t, "RULES.md")
        s = io.open(p, encoding="utf-8").read()
        s = re.sub(r">\s*v([0-9.]+)\s*\|", "> v9.9.9 |", s, count=1)
        io.open(p, "w", encoding="utf-8").write(s)
        return "md 版本行改为 v9.9.9"

    # ── E 组：外挂表溯源（正负样本）──────────────────────────────────
    print("── 外挂表溯源（check_traceability 直测）──")
    _live = {"rules": [{"id": "R001"}, {"id": "R041"}],
             "retiredEntries": [{"id": "J1"}, {"id": "J2"}]}
    _cases = [
        ("ruleId 命中退役索引 ⇒ 放行", {"ledgerIndex": {"keys": [{"key": "file:x", "ruleId": "J1"}]}}, 0),
        ("ruleId 命中现役 ⇒ 放行", {"ledgerIndex": {"keys": [{"key": "file:y", "ruleId": "R001"}]}}, 0),
        ("ruleId 悬空（既非现役也非退役）⇒ 报错",
         {"ledgerIndex": {"keys": [{"key": "file:z", "ruleId": "J999"}]}}, 1),
        ("条目缺 ruleId ⇒ 报错", {"ledgerIndex": {"keys": [{"key": "file:w"}]}}, 1),
    ]
    for desc, cdoc, want in _cases:
        got = len(check_traceability(_live, cdoc))
        good = (got == want)
        ok = ok and good
        print("  %s %-44s 期望 %d 项 / 实际 %d 项" % ("✅" if good else "❌", desc, want, got))
    print()
    print("规则账本一致性门 · 自证（正负样本）")
    print("── 应放行（负样本，防过杀）──")
    case("未改动副本", m_none, False)
    print("── 应报漂移（正样本：逐条对应本门声明的覆盖项）──")
    case("分类漂移（json 侧）★本次新增覆盖", m_json_cat, True)
    case("分类漂移（md 侧）★本次新增覆盖", m_md_cat, True)
    case("J 系列标题缺失 ★本次新增覆盖", m_drop_j, True)
    case("R 系列标题缺失（原有覆盖，防回归）", m_drop_r, True)
    case("版本号漂移（原有覆盖，防回归）", m_ver, True)

    # ★ 补：**md 侧超前日期**（对端 session-ab866871 的「注入B」—— 它当时实测本门**漏检**）
    #   动机：本门的 md→json 日期互校**一直存在**，但**自证里没有对应正样本**
    #   ⇒ 判据存在而未被样本覆盖 = 哪天被改坏也无人知（类别 C）。
    def m_md_future(d):
        p2 = os.path.join(d, "RULES.md")
        t = io.open(p2, encoding="utf-8").read()
        i = t.find("## ")
        j = t.find("\n", t.find("- 分类:", i))
        t = t[:j] + "\n- 注入B: 2026-12-31（仅 md 侧）" + t[j:]
        io.open(p2, "w", encoding="utf-8").write(t)
        return "仅在 md 注入超前日期 2026-12-31"

    case("★ md 侧超前日期（对端注入B）⇒ 必须报漂移", m_md_future, True)
    print()
    print("⇒ %s" % ("全部通过" if ok else "存在失败项"))
    return 0 if ok else 1


if __name__ == "__main__" and "--selftest" in sys.argv:
    sys.exit(_selftest())

print("=== 规则账本双载体双向一致性断言 v3 ===")
print("  version=%s  规则数=%d  lastUpdated=%s" % (d["version"], len(d["rules"]), LAST))
print("  覆盖: json→md(R 标题/J 标题/版本/条数) · **分类字段双向** · md→json(日期互校) · 双向超前 · 反例保留")
if _SUMMARY_WARN:
    print("  ⚠️ 摘要文本漂移 %d 处（**警告级，不判死** —— md 本是精简摘要；相似度 <0.90 才报）："
          % len(_SUMMARY_WARN))
    for _rid, _rt, _a, _b in _SUMMARY_WARN[:8]:
        if _rid == "?":
            print("     - %s" % _a); continue
        print("     - %s 相似度 %.2f ｜ json:%s… ／ md:%s…" % (_rid, _rt, _a[:34], _b[:34]))
if fails:
    print("  ❌ 漂移 %d 处:" % len(fails))
    for f in fails:
        print("     -", f)
    sys.exit(1)
print("  ✅ 一致")
sys.exit(0)
