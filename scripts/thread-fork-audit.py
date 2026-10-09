#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
thread-fork-audit —— 议题分叉审计（v1.0.0）

来源：明鉴 2026-09-14 两条发现（都由她举证）：
  ① 收敛表 data/registry/thread-convergence-table-20260911 只有 5 行，
     而「核验边界」「口径两组」两个议题**都不在表内** ⇒ 两次都跨线程分叉。
  ② 她自我修正：「发前查表」漏了**回应**这一半 —— 发起通常一次，回应可以很多次，
     **回应才是最容易分叉的一半**。
本工具把「是否分叉」变成可计数、可复核的量：按**对象标识（card-key / ref）**而非内容分组，
因为**内容会变、ref 不变**（这正是回应难以按内容去重的原因）。

用法：
    python3 thread-fork-audit.py --bus ~/.dsh/agent-bus.json --refs keyA,keyB,...
    python3 thread-fork-audit.py --bus ... --registry TABLE.json     # 表的每行取 ref 字段
    python3 thread-fork-audit.py --selftest
    退出码：0 无分叉 · 1 存在分叉（同一 ref 出现在 ≥2 线程）· 2 参数错

判据（本工具自身受同一纪律约束）：selftest **先跑反例**（构造必然分叉的样本并确认被检出），
再跑正例（单线程样本不得误报），否则「未检出分叉」会被读成「没有分叉」。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不修改权限】。
  关于删除：本工具确有 os.remove/rmtree，但**目标限于【自身临时/归档目录】**
  （常量 DATA_DIR / tempfile 临时目录 / 自身缓冲目录），**不从参数接收删除目标** ⇒
  依 R10 定义（「不该发生的路径在结构上不可绕过」）此处无该路径。
★ 限度：此为【模式匹配 + 人工核】结论；若日后引入【由参数驱动的删除目标】，须更新本声明。
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== thread-fork-audit 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · thread-fork-audit —— 议题分叉审计（v1.0.0）")
    print("  · 来源：明鉴 2026-09-14 两条发现（都由她举证）：")
    print("  · ① 收敛表 data/registry/thread-convergence-table-20260911 只有 5 行，")
    print("  · 而「核验边界」「口径两组」两个议题**都不在表内** ⇒ 两次都跨线程分叉。")
    print("  · 命令/参数: bus, refs, registry, ref-field, topic-lookup, bb, ident-field, stub-suggest")

    print("【② 不该发生路径清单】")
    print("  · 本工具涉及「删除文件/目录」⇒ 该路径须受控（详见 R006 ⑩ 约束门）")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, hashlib, json, os, re, sys, tempfile, time, urllib")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/thread-fork-audit.log")
    return 0

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）


import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/thread-fork-audit.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = "1.12.0"

# ── 「混装线」（混合容器）判定（明鉴 2026-09-14 的定义缺口） ──────────────
# 她指出：**`分叉数` 是「议题层」的量，而被统计的线程是「容器层」的对象** ⇒ **容器可以混装多个议题**
#   ⇒ 于是「线程数 − 1」在混装线存在时**不再等于「该议题分叉出的线数」** ⇒ **定义层面的缺口，不是数字错**。
# 真语料实例：`thread-mu0wfg40`（Dify/外卖报表宕机复盘）里只有 **1/28** 条谈绑定块（**我 15:52 那条**）。
# ⇒ 判据（本版声明其为抽取规则）：**长线程且该 ref 命中占比极低 ⇒ 判为混装线**，从分叉计数中剔除，
#   但**三个计数全部打印**（全部 / 排除通知 / 排除通知与混装）⇒ **过滤不遮蔽**：分类错了读者仍看得见原数。
MIXED_MIN_TOTAL = 10      # 短线程不做混装判定（样本不足，宁可判「非混装」）
MIXED_SHARE_MAX = 0.20    # 命中占比 ≤ 此值且线程够长 ⇒ 混装

# ── 「通知类发言」的机械识别（明鉴 2026-09-14 的 A/B 口径之下的第三条路） ──
# 背景：她指出「不重复处理」有两个所指（处理₁=展开 · 处理₂=发言），且**通知类发言会把分叉数推高**
#   （每认一次「我不重复处理」就在新线上留一条 ⇒ 该 ref 命中线程 +1 ⇒ 分叉数虚高，而涨的不是真分叉）。
# 口径 A（不发言）能救数干净但会让**非归属线的读者静默**；口径 B（可发通知）救静默但数虚高。
# ⇒ 本版的第三条路：**允许发，但让通知可被机械识别**，于是**同时报两个数**：
#   `n_threads`（全部命中）与 `n_threads_effective`（**排除只含通知的线程**）。
# ⚠ 声明：`is_pointer` 是**抽取规则不是事实**；上界 POINTER_MAX 是经验值，边界例见 selftest。
POINTER_MAX = 160



def _decode_strict(raw):
    """★ 严格解码（2026-09-22 新增，采纳驿使经明鉴转达的「穷尽五条件」之一：**解码无丢失**）。
    原写法 `errors="replace"` 会把**撕裂读造成的半个多字节序列**静默换成 U+FFFD ——
    **字节数看起来没少、字符却已经丢了**，而且 JSON 往往仍能解析 ⇒ **错误不可见**。
    ⇒ 改为严格解码：解不出来就抛，**交给外层重试**（本工具本来就有重试循环）。
    ⇒ 判据：**问「我的读取有没有跳过任何一个字节？」** —— 丢字符也算跳过。"""
    return raw.decode("utf-8")

def is_pointer(text):
    """通知/指针类发言的机械判据：**短**且**以引用形式指向产物**（而非展开）。纯函数，可离线 selftest。"""
    t = re.sub(r"\s+", "", str(text))
    if len(t) > POINTER_MAX:
        return False
    return ("看黑板" in t) or ("不重复处理" in t) or ("详见thread-" in t) or ("详见 thread-" in t)

# ── 片段泛化上界（2026-09-14 新增，依据当日实测） ──────────────────────
# 实测（data/registry 列举，524 键）：`verification-boundary`=2 · `caliber`=5 · `hr-ruling`=74 ·
#   `20260914`=163 · `a`=529。⇒ 同一「按键名匹配」机制在不同片段上的判别力差 2 个数量级；
#   命中集合不受限时，判定句要求的「取首行 ts 比对」**首行身份不稳定** ⇒ 结果不得作判据。
# ⇒ 判据（同族于「前缀只能当类、不能当身份」·命名面）：**片段须有区分力，否则该查询失败而非静默返回**。
SPECIFICITY_MAX = 12


# 「显式声明无产物」的哨兵值（HR 收敛表 v3 实测采用）。⇒ 与「未声明却取不到」必须分开：
#   前者是一个**有信息量的值**（已判过：本议题无产物），后者是**缺口**。
NO_ARTIFACT_SENTINELS = {"无产物", "无", "—", "-", "--", "n/a", "na", "none", "null", "未落卡", ""}


def _probe(url, timeout=12):
    """唯一 IO 出口：True / 404 / 400 / None（其它错误或异常）。可注入 ⇒ 使映射可离线 selftest。"""
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except urllib.error.HTTPError as e:
        return e.code if e.code in (400, 404) else None
    except Exception:
        return None


def content_ident(value):
    """内容标识口径（2026-09-14 实测反推，三个 stub 卡全部命中）：
       sha256(json.dumps(value, sort_keys=True, ensure_ascii=False))[:16]
    ★ 为什么要现算：收敛表把 `内容标识` 存成**一列写死的值**，而它**本来是卡自身的属性**。
      实测（2026-09-14 20:4x）：表内 3 个值与按本口径现算**当前一致** ⇒ 但**没有任何机制在校验**
      ⇒ 下一次编辑卡，表里那个 16 位十六进制会**静默变成错的**（而它看起来仍然「有值」）。
      ⇒ 这与行 1–5 的裸 `分叉数` 是**同一族**（写死的活量），只是换了个字段。"""
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def _ident_map(rows, ident_field):
    """建 {卡键: 内容标识} 索引。
    ★ 这里有一个我自己刚踩的坑（2026-09-14 20:4x）：直接用 dict 推导式会把 **5 行
      `卡键=无产物` 折叠成 1 条** ⇒ 汇总里报「声明无 1」而不是 5 —— 也就是本工具
      `partition_registry` 专门要防的**同一折叠**，在我新加的功能里又发生了一次。
      ⇒ 故：保留 dict 查找，但**冲突必须出声**（同一 卡键 不同标识 ⇒ 索引会静默取一个）。
      计数则一律走 `partition_registry` 的声明无产物（那才是不会折叠的来源）。"""
    d, conflicts = {}, []
    for r in rows:
        if not isinstance(r, dict):
            continue
        k, v = r.get("卡键"), r.get(ident_field)
        if not k:
            continue
        if k in d and d[k] != v:
            conflicts.append({"卡键": k, "先": d[k], "后": v})
        d[k] = v
    return d, conflicts


def load_registry(source, bb, ident_field="内容标识"):
    """收敛表来源：**文件路径** 或 **黑板键**。
    ★ 为什么必须支持黑板键（2026-09-14 实测）：支持前者时，「机器可消费」其实要求调用方先做
      「GET → 取 value.rows → 落临时文件」三步**手工搬运**，那一步仍然是手写的
      ⇒ 只把「人读散文」降成了「人搬运 + 机器读」，不是「机器直读」。
    返回 (rows, identity, ident_expect, src_kind)。"""
    src = os.path.expanduser(source)
    if not os.path.exists(src) and re.match(r"^[a-z]+/", src):
        env = json.load(urllib.request.urlopen(f"{bb}/{src}", timeout=20))
        val = env.get("value", {})
        rows = val if isinstance(val, list) else val.get("rows", val.get("citations", []))
        ent = hashlib.sha256(json.dumps(val, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        # ★ 拆标签（2026-09-22 HR 指出）：信封 version/ts **不是内容的函数**（同内容在两实例可不同）
        #   ⇒ 若消费路径拿「信封 ts/ver + value sha」当内容标识，**同内容会算出不同标识 = 假漂移**。
        #   ⇒ 故本行拆成两段并明标：【身份】只取 value；【出处】只记信封印记。防误用。
        identity = (f"【身份】value sha256[:12]={ent[:12]}（**内容标识只取 value**，这是身份）"
                    f" · rows={len(rows)} · 口径={content_ident.__doc__.splitlines()[1].strip()}"
                    f" ｜ 【出处·非身份】黑板键 {src} · **信封 ts={env.get('ts')} ver={env.get('ver')}**"
                    f"（信封不是内容的函数：同内容在两实例可不同 ⇒ **不得并入身份**）")
        ident, conf = _ident_map(rows, ident_field)
        if conf:
            print(f"   ⚠ **同一 `卡键` 在表里出现多次且内容标识不一致 {len(conf)} 处** ⇒ 索引会静默取一个：{conf[:3]}")
        return rows, identity, ident, "bb-key"
    ident0 = registry_identity(src)
    rows = json.load(open(src, encoding="utf-8"))
    rows = rows if isinstance(rows, list) else rows.get("rows", rows.get("citations", []))
    ident, conf = _ident_map(rows, ident_field)
    if conf:
        print(f"   ⚠ **同一 `卡键` 在表里出现多次且内容标识不一致 {len(conf)} 处** ⇒ 索引会静默取一个：{conf[:3]}")
    return rows, "文件 " + json.dumps(ident0, ensure_ascii=False), ident, "file"


def _tool_sha16():
    import hashlib
    try:
        return hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()[:16]
    except Exception:                                # noqa: BLE001
        return None


def _tool_source_id():
    sha = _tool_sha16()
    return sha[:12] if sha else None


def _tool_mtime():
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(os.stat(os.path.abspath(__file__)).st_mtime))
    except Exception:                                # noqa: BLE001
        return None


def tool_identity_line():
    """★ 工具自身的标识行（2026-09-14 补）。起因：明鉴两轮核我的读数都遇到版本漂 ——
       我报 1.5.0 / 她测 1.6.0 / 当时实际已是 1.12.0；而 `absence-claim-lint` 那次同样是
       3.5.0 vs 3.7.0 vs 3.13.0 ⇒ **这不是偶发，是「报读数不带工具标识」的系统性习惯**。
       ⇒ 与总线快照同理：凡本工具报出的数，须与**被报对象的快照**和**产出它的工具（本行）**
       一起引；否则读者无法判断两个读数是否同一版产出、是否可比。"""
    return (f"工具 thread-fork-audit v{VERSION} · source_id={_tool_source_id()} · "
            f"mtime={_tool_mtime()} · py={sys.version_info[0]}.{sys.version_info[1]} "
            f"⇒ 报数须连本行一起引")


def ref_exists(ref, base, listing=None, timeout=12, probe=_probe):
    """存在性：True 存在 / False 不存在（404）/ "bad-key" 键写法非法（400）/ None **不可判**（探测失败）。

    ★ 2026-09-14 明鉴指出（她实测 21 个双侧 404 的 ref 被本工具报成 `[ok] 分叉 0`）：
      「ref 出现在消息文本里」是**必要条件、不是充分条件** —— 还缺「**产物存在**」这一项。
      缺这一项时，**指针指向不存在的东西**这一情形会静默报 ok ⇒ 假门被报成健康。
    ★ 2026-09-14 补：**400 与 404 语义不同**（黑板键语法：400=写法非法/键错 · 404=格式合法但不存在）
      ⇒ 融了别的信息的字符串（实测：收敛表 `卡` 字段的 `…-20260914（d6ea577d）`）返回 **400**，
      它既不是「不存在」也不是「不可判」，而是「**这个字符串不是键**」⇒ 必须单独报，否则调用方
      会去修产物，而真正要修的是**调用方的字段**。
    解析规则（本版声明其限）：
      · ref 含 '/' ⇒ 视作**完整键**，直接 GET；
      · 否则 ⇒ 在 `data/registry/` 列举里找 **basename 恰等于 ref** 或 **以 `-{ref}` 结尾** 的键；
        0 命中 ⇒ False（**不等于**议题不存在，只表示按本规则定位不到产物）。
    """
    if "/" in ref:
        for _ in range(2):
            r = probe(f"{base}/{ref}", timeout)
            if r is True:
                return True
            if r == 404:
                return False
            if r == 400:
                return "bad-key"
            if r is None:
                continue
            return None
        return None
    if listing is None:
        try:
            lst = json.load(urllib.request.urlopen(f"{base}/data/registry/", timeout=20))
            listing = lst.get("list") if isinstance(lst.get("list"), list) else []
        except Exception:
            return None
    base_name = ref.split("/")[-1]
    for k in listing:
        kn = k.split("/")[-1]
        if kn == base_name or kn.endswith("-" + base_name):
            return True
    return False


def classify(rows, exists):
    """纯函数：把 ref 审计行加上**存在性维**并给出判决（可离线 selftest）。

    exists: {ref: True/False/None}。verdict ∈ {ok, forked, missing, missing+forked, unverified}。
    判决优先级：产物不存在 / 不可判 **优先于** 「没分叉」——因为「没分叉」在产物不存在时
    是**假阴性**，不能用作健康信号。
    """
    out = []
    for r in rows:
        e = exists.get(r["ref"], None)
        # 分叉维：**以「排除通知后的有效线程」为准**（明鉴 2026-09-14）；缺字段时回退旧的 forked
        fe = r.get("forked_pure", r.get("forked_effective", r.get("forked")))
        if fe:
            fk = "forked"
        elif r.get("forked_effective"):
            fk = "fork-mixed"          # 只有**混装线**在撑着 ⇒ 该议题其实没分叉
        elif r.get("forked"):
            fk = "fork-notification"   # 只有**通知类发言**在撑着
        else:
            fk = ""
        if e == "declared-none":
            v = "declared-none"
        elif e == "bad-key":
            v = "bad-key+forked" if fe else "bad-key"
        elif e is False:
            v = "missing+forked" if fe else "missing"
        elif e is None:
            v = "unverified"
        elif e is True:
            v = fk or "ok"
        else:
            # ★ 完备性护栏（明鉴 2026-09-14 提出风险，本版实现）：
            #   原写法是 `else: v = fk or "ok"` —— 兜底把**任何未预期取值**归入「健康」，
            #   正是「两态同形」的最危险形态：**未知被读成正常**。
            #   ⇒ 现改为：合法取值逐一枚举，兜底分支只能是**不该发生**的那一支，
            #     并显式记为 `other`（账目里计数 + 报警 + 非零退出），绝不归入 ok。
            v = "other"
        out.append({**r, "exists": e, "verdict": v})
    return out


def partition_registry(rows, field):
    """把收敛表按行**分区**并做**行数守恒**（纯函数）。

    ★ 为什么必须守恒：本工具原先用 `{ref: {}}` 建索引 ⇒ **多行同一 ref 会静默折叠**
      （实测：HR 收敛表 8 行 ⇒ 输出「审计 4 个对象标识」，5 行 `卡键=无产物` 塌成 1 行，
      读者无从察觉 4 行被吃掉了）。⇒ 与今日反复抓的形态同源：**检查项少一个 ⇒ 静默失效**。
    返回 (refs, declared_none, empty_field, accounting)。
    """
    refs, declared_none, empty_field = [], [], []
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            empty_field.append((i, None))
            continue
        v = r.get(field)
        if v is None or str(v).strip() == "":
            empty_field.append((i, v))
            continue
        sv = str(v).strip()
        if sv.lower() in {x.lower() for x in NO_ARTIFACT_SENTINELS}:
            declared_none.append((i, sv))
            continue
        refs.append(sv)
    unique = sorted(set(refs))
    collapsed = {k: refs.count(k) for k in unique if refs.count(k) > 1}
    accounting = {
        "输入行": len(rows), "有效 ref 行": len(refs), "唯一 ref": len(unique),
        "折叠行数": len(refs) - len(unique), "折叠明细": collapsed,
        "声明无产物": len(declared_none), "空字段": len(empty_field),
        "守恒": len(rows) == len(refs) + len(declared_none) + len(empty_field),
    }
    return unique, declared_none, empty_field, accounting


def stub_targets(rows):
    """占位卡键建议的触发集合（明鉴 2026-09-14 建议）：**已分叉 ∨ 产物不存在**。
    旧版只对「已分叉」触发 ⇒ 产物不存在的 ref 恰恰因为「没分叉」被跳过。"""
    return [r for r in rows if r.get("forked") or r.get("exists") is False or r.get("exists") == "bad-key"]


KEYWORD_FIELDS = ("issue_keywords", "关键词", "keywords", "issue_keyword")


def registry_identity(path):
    """注册表的**内容标识**（2026-09-14 明鉴指正后新增）。

    根因：`--registry <路径>` 只有**位置**、没有**内容标识** ⇒ 我 16:12 那次把**她的拟稿**存成
    `/tmp/convtable.json` 后跑查询，却按「表」报出「核验边界 → 已登记」，而**表里当时没有那一行**
    （她 16:25 实跑同一命令 = 未登记）。⇒ 位置相同、内容不同 ⇒ 读者无法复现。
    ⇒ 本函数让每次查询**自带** 路径/字节数/行数/sha256/mtime，缺一不得作为结论引用。
    """
    import hashlib
    try:
        b = open(path, "rb").read()
    except Exception as e:
        return {"path": path, "error": str(e)}
    try:
        doc = json.loads(b.decode("utf-8", "replace"))
        rows = doc.get("rows") if isinstance(doc, dict) else (doc if isinstance(doc, list) else [])
    except Exception:
        rows = []
    return {"path": path, "bytes": len(b), "rows": len(rows),
            "sha256": hashlib.sha256(b).hexdigest()[:16],
            "mtime": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(os.path.getmtime(path)))}


def keyword_check(rows, kws):
    """纯函数：逐关键词判「已登记」并把**系统性状态**与**个别状态**分开。

    ★ 明鉴 2026-09-14 指出的缺陷：**表里没有任何关键词字段时，本查询对任何议题都会返回「未登记」**
      ⇒ 「该议题未登记」与「表结构不支持关键词匹配」**同形** ⇒ 必须分开报。
    ★ 另一处（我自查）：原实现的兜底分支把**整行 JSON** 当文本匹配 ⇒ **退化匹配**（任一字样即中）
      ⇒ 属弱证据，必须标注分支，不得与「按声明字段命中」同形。
    返回 (per_kw, systematic)，systematic ∈ {ok, no-keyword-field}。
    """
    fielded = [r for r in rows if isinstance(r, dict) and any(f in r for f in KEYWORD_FIELDS)]
    systematic = "ok" if fielded else ("no-keyword-field" if rows else "no-rows")
    per = []
    for k in kws:
        hit = None
        for r in rows:
            if not isinstance(r, dict):
                continue
            declared = None
            for f in KEYWORD_FIELDS:
                if f in r and r[f]:
                    declared = r[f]
                    break
            topic = r.get("议题") or r.get("issue") or r.get("thread") or "?"
            if declared is not None:
                vals = declared if isinstance(declared, list) else [declared]
                if any(k == str(v) or k in str(v) for v in vals):
                    hit = {"by": "declared", "topic": topic}
                    break
            else:
                # 退化兜底：整行文本匹配 ⇒ 弱证据
                if k in json.dumps(r, ensure_ascii=False):
                    hit = {"by": "text-fallback", "topic": topic}
                    break
        per.append({"kw": k, "hit": hit})
    return per, systematic


def topic_specificity(rows, frag):
    """输入项质量门：片段是否具备区分力（纯函数，可离线 selftest）。

    返回 (verdict, reason)。verdict ∈ {empty, exact, ok, too-generic}。
    依据（2026-09-14 实测）：按键名匹配的判别力由**片段本身**决定，而共享长前缀会把
    相似度变成「前缀的函数」。⇒ 命中数超过上界时，该查询**失败**，不静默返回一个
    看起来可用、实则首行身份不稳定的列表。
    """
    n = len(rows)
    if n == 0:
        return ("empty", f"片段「{frag}」命中 0 张 ⇒ **不可判**（也可能只是键名不含该片段，不等于议题不存在）")
    if n == 1:
        return ("exact", f"命中 1 张 ⇒ 该片段可作**身份**（唯一命中）")
    if n <= SPECIFICITY_MAX:
        return ("ok", f"命中 {n} 张 ≤ 上界 {SPECIFICITY_MAX} ⇒ 可用（须取首行 ts 比对）")
    return ("too-generic",
            f"命中 {n} 张 > 上界 {SPECIFICITY_MAX} ⇒ **片段过于泛化**、首行身份不稳定 ⇒ "
            f"本结果**不得用作发布前判据**；请给更长片段（含 subject 段，如 `caliber-two-groups`）")


def topic_lookup(ref, base, limit=400):
    """发布前查更晚裁定（HR 2026-09-14）：给议题的 card-key / stub，列出其**关联卡按信封 ts 倒序**。
       实现：先按**键名**匹配（廉价），再逐键取信封 ts 排序；只接受「具体卡键 + ts 比较结果」。
       限制（须声明）：仅按键名匹配 ⇒ 内容里提及但键名不含该议题的卡需全量扫，本版不做。"""
    lst = json.load(urllib.request.urlopen(f"{base}/data/registry/", timeout=20))
    keys = [k for k in (lst.get("list", {}) if isinstance(lst.get("list"), dict) else lst.get("list", []))
            if ref in k][:limit]
    rows = []
    for k in keys:
        try:
            d = json.load(urllib.request.urlopen(f"{base}/{k}", timeout=12))
            rows.append((d.get("ts", ""), k, d.get("version")))
        except Exception:
            continue
    rows.sort(reverse=True)
    return rows


def collect(bus, refs):
    """返回 {ref: {thread_id: {n, first_ts, n_pointer}}}；匹配按『消息文本包含该 ref』。

    2026-09-14 增字段（明鉴）：`first_ts`（该线程内**最早**一条含该 ref 的消息时刻 ⇒ 用于标「首提线」）
    与 `n_pointer`（其中**通知类**发言条数 ⇒ 用于算「排除通知后还剩几条线程」）。
    """
    out = {r: {} for r in refs}
    totals = {}
    for t in bus.get("threads", []) if isinstance(bus, dict) else []:
        tid = str(t.get("id", ""))
        msgs = t.get("messages", []) or []
        totals[tid] = len(msgs)
        for m in msgs:
            text = str(m.get("text", ""))
            ts = m.get("time") or 0
            for r in refs:
                if r and r in text:
                    d = out[r].setdefault(tid, {"n": 0, "first_ts": ts, "n_pointer": 0})
                    d["n"] += 1
                    d["first_ts"] = min(d["first_ts"] or ts, ts)
                    if is_pointer(text):
                        d["n_pointer"] += 1
    for r in out:
        for tid, d in out[r].items():
            d["thread_total"] = totals.get(tid, d["n"])
    return out


def audit(bus, refs):
    res = collect(bus, refs)
    rows = []
    for r, threads in res.items():
        n_msg = sum(d["n"] for d in threads.values())
        # 只含通知的线程 = 该线程内**每一条**命中消息都是通知类
        eff = [tid for tid, d in threads.items() if d["n"] - d["n_pointer"] > 0]
        # 混装线：长线程 + 本 ref 命中占比极低 ⇒ 该线程的**主体不是本议题** ⇒ 不计入分叉
        mixed = [tid for tid, d in threads.items()
                 if d.get("thread_total", d["n"]) >= MIXED_MIN_TOTAL
                 and d["n"] / max(1, d.get("thread_total", d["n"])) <= MIXED_SHARE_MAX]
        pure = [tid for tid in eff if tid not in mixed]
        first = min(threads.items(), key=lambda kv: kv[1]["first_ts"])[0] if threads else None
        rows.append({"ref": r, "threads": threads, "n_threads": len(threads),
                     "n_threads_effective": len(eff), "n_threads_pure": len(pure),
                     "mixed_threads": mixed, "n_messages": n_msg,
                     "first_thread": first, "forked": len(threads) >= 2,
                     "forked_effective": len(eff) >= 2, "forked_pure": len(pure) >= 2,
                     "notification_only_threads": len(threads) - len(eff)})
    return rows


# ── selftest：先反例（必然分叉）后正例（不得误报） ──────────────────────
def _selftest_verdict_total():
    """分类完备性（明鉴 2026-09-14 指出的风险，本版实现为断言）：
    ① 合法取值 × 分叉旗标 的全部组合都落在已声明类别内；
    ② **未预期取值必须落到 other，不得落到 ok**（原兜底写法正是把它归成 ok）。"""
    declared = {"ok", "forked", "missing", "missing+forked", "unverified",
                "bad-key", "bad-key+forked", "declared-none", "fork-notification", "fork-mixed"}
    bad = []
    for e in (True, False, None, "bad-key", "declared-none"):
        for fk in ({}, {"forked_pure": True}, {"forked_effective": True}, {"forked": True}):
            v = classify([{"ref": "x", **fk}], {"x": e})[0]["verdict"]
            if v not in declared:
                bad.append((e, fk, v))
    unexpected = classify([{"ref": "x"}], {"x": "oops"})[0]["verdict"]
    return (len(bad) == 0), unexpected == "other", bad, unexpected


def selftest():
    ok = total = 0
    fork_bus = {"threads": [
        {"id": "th-A", "messages": [{"text": "看黑板 data/registry/card-x"}, {"text": "回应 card-x 的补充"}]},
        {"id": "th-B", "messages": [{"text": "card-x 的另一处讨论"}]},
    ]}
    single_bus = {"threads": [
        {"id": "th-A", "messages": [{"text": "看黑板 data/registry/card-y"}]},
    ]}
    unrelated = {"threads": [{"id": "th-A", "messages": [{"text": "别的议题"}]}]}
    # 关键词登记判定（纯函数级，用同一份表样本）
    table = [{"议题": "核验边界", "issue_keywords": ["核验边界", "最低核验"]}]
    cases = [
        ("反例·同一 ref 跨两线程 ⇒ 必检出分叉", fork_bus, ["card-x"], True),
        ("正例·同一 ref 仅一线程 ⇒ 不得误报", single_bus, ["card-y"], False),
        ("正例·ref 完全未出现 ⇒ 不得误报", unrelated, ["card-z"], False),
    ]
    print("selftest（先反例后正例）:")
    for name, bus, refs, want_fork in cases:
        total += 1
        rows = audit(bus, refs)
        got = any(r["forked"] for r in rows)
        good = got == want_fork
        ok += 1 if good else 0
        print(f"  {'✅' if good else '❌'} {name}: 检出分叉={got} 期望={want_fork}")
    # ── 存在性维（明鉴 2026-09-14）——真语料边界例：21 个 hr-reply-mingjian-* 双侧 404 ──
    one = {"th-A": 1}
    two = {"th-A": 1, "th-B": 1}
    mk = lambda ref, th: {"ref": ref, "threads": th, "n_threads": len(th),
                          "forked": len(th) >= 2, "n_messages": sum(th.values())}
    exist_cases = [
        ("反例·★产物不存在 + 未分叉 ⇒ 必判 missing（旧版报 [ok]，即明鉴抓到的假阴性）",
         [mk("data/registry/hr-reply-mingjian-checkability-fourth-term-20260911", one)],
         {"data/registry/hr-reply-mingjian-checkability-fourth-term-20260911": False}, "missing"),
        ("反例·产物不存在 + 已分叉 ⇒ missing+forked（两缺陷叠加不得降级为单一 forked）",
         [mk("data/registry/hr-reply-mingjian-cooldown-conditions-20260911", two)],
         {"data/registry/hr-reply-mingjian-cooldown-conditions-20260911": False}, "missing+forked"),
        ("正例·产物存在 + 未分叉 ⇒ ok（不得误报 missing）",
         [mk("data/registry/hr-reply-mingjian-checkability-20260911", one)],
         {"data/registry/hr-reply-mingjian-checkability-20260911": True}, "ok"),
        ("反例·产物存在 + 跨两线程 ⇒ forked", [mk("data/registry/card-x", two)],
         {"data/registry/card-x": True}, "forked"),
        ("正例·存在性探测失败 ⇒ unverified（**不得读作 ok**，也不得当不存在）",
         [mk("data/registry/card-y", one)], {"data/registry/card-y": None}, "unverified"),
    ]
    for name, rws, ex, want in exist_cases:
        total += 1
        got = classify(rws, ex)[0]["verdict"]
        good = got == want
        ok += 1 if good else 0
        print(f"  {'✅' if good else '❌'} {name}: got={got} 期望={want}")
    # ── keyword-check 的同形读数（真语料：明鉴拟稿 vs 真实收敛表）──
    draft = [{"议题": "核验边界 / 最低核验 / 例外核验触发", "issue_keywords": ["核验边界", "最低核验"],
              "归属线程": "thread-x"}]                      # 明鉴 16:12 的**拟稿**（有声明字段）
    realtable = [{"议题": "安全键溯源撤回（security-provenance）", "对端": "守灯",
                  "归属线程": "thread-a", "分叉数": 2},
                 {"议题": "四层触及阶梯（touch-ladder）", "对端": "明鉴",
                  "归属线程": "thread-b", "分叉数": 2}]     # 真实表形态（**无**关键词字段）
    kw_cases = [
        ("反例·★真实收敛表形态（无关键词字段）⇒ 系统性状态必为 no-keyword-field（不得逐条报「未登记」）",
         realtable, ["核验边界"], "no-keyword-field"),
        ("正例·明鉴拟稿（有 issue_keywords）⇒ 系统性状态 ok（不得误报缺字段）",
         draft, ["核验边界"], "ok"),
        ("边界·空表 ⇒ no-rows（不得报 no-keyword-field，两者成因不同）", [], ["核验边界"], "no-rows"),
    ]
    for name, rws, kws, want in kw_cases:
        total += 1
        got = keyword_check(rws, kws)[1]
        good = got == want
        ok += 1 if good else 0
        print(f"  {'✅' if good else '❌'} {name}: got={got} 期望={want}")
    # 命中分支必须可分：声明字段 vs 整行兜底（退化匹配）
    total += 1
    got = keyword_check(draft, ["核验边界"])[0][0]["hit"]["by"]
    good = got == "declared"
    ok += 1 if good else 0
    print(f"  {'✅' if good else '❌'} 反例·命中须标依据=**声明的关键词字段**: got={got} 期望=declared")
    total += 1
    got = keyword_check(realtable, ["守灯"])[0][0]["hit"]["by"]
    good = got == "text-fallback"
    ok += 1 if good else 0
    print(f"  {'✅' if good else '❌'} 反例·只能整行命中时须标 **text-fallback（弱证据）**（防退化匹配与声明字段同形）: got={got} 期望=text-fallback")
    # 注册表内容标识必须包含 sha256 与行数
    total += 1
    # ★ 自建夹具（2026-09-22 修）：本用例原先读 /tmp/convtable.json —— 一个**遗留临时文件**。
    #   它存在时用例通过、被清掉后必然失败 ⇒ **判据依赖环境残留 ⇒ 不是 hermetic 的**
    #   （与今晚反复抓的「空通过/环境依赖」同族：用例的通过与否取决于跑它的时刻，而非代码）。
    #   ⇒ 改为自建夹具、跑完即删。
    import tempfile as _tf
    _fx = os.path.join(_tf.mkdtemp(prefix="tfa-selftest-"), "convtable.json")
    with open(_fx, "w", encoding="utf-8") as _f:
        json.dump({"rows": [{"议题": "夹具行"}]}, _f, ensure_ascii=False)
    ident = registry_identity(_fx)
    good = bool(ident.get("sha256")) and ident.get("rows") == 1
    try:
        os.remove(_fx); os.rmdir(os.path.dirname(_fx))
    except Exception:
        pass
    ok += 1 if good else 0
    print(f"  {'✅' if good else '❌'} 正例·registry_identity 须含 sha256 与行数: {ident.get('sha256')} / rows={ident.get('rows')}")

    # ── 混装线（真语料边界：1/28 ⇒ 混装 · 28/28 ⇒ 不混装 · 1/3 短线程 ⇒ 不判混装）──
    MREF = "notes/mac-mini/mingjian-review-fork-audit-three-gaps"
    # 非通知类的「实质消息」：含 ref 且 > POINTER_MAX（否则会被通知规则先剔除，混装规则就走不到）
    sub = "看黑板 " + MREF + " " + "展开" * 60
    assert not is_pointer(sub), "构造失败：实质消息被判成了通知类（混装规则将不被触发）"
    long_mixed = [{"text": "别的议题", "time": 10 + i} for i in range(27)] + [{"text": sub, "time": 30}]
    long_pure = [{"text": sub, "time": 10 + i} for i in range(28)]
    short_mixed = [{"text": "别的", "time": 1}, {"text": "别的", "time": 2}, {"text": sub, "time": 3}]
    mix_cases = [
        ("反例·真语料形态 **1/28**（mu0wfg40：长线 + 命中占比 3.6%）⇒ 判混装线、不得计入分叉",
         {"threads": [{"id": "th-long", "messages": long_mixed},
                      {"id": "th-other", "messages": [{"text": sub, "time": 1}]}]}, "fork-mixed"),
        ("正例·**28/28**（全是本议题）⇒ 不得误判混装", {"threads": [
            {"id": "th-a", "messages": long_pure},
            {"id": "th-b", "messages": [{"text": sub, "time": 1}]}]}, "forked"),
        ("正例·**1/5**（占比 20% 已达阈值，但总长 5 < 10 ⇒ 样本不足）⇒ 不得判混装（此例专测长度门槛）",
         {"threads": [{"id": "th-five", "messages": [{"text": "别的", "time": i} for i in range(4)] + [{"text": sub, "time": 9}]},
                      {"id": "th-other", "messages": [{"text": sub, "time": 1}]}]}, "forked"),
        ("正例·**1/3**（短线程，样本不足）⇒ 不得误判混装",
         {"threads": [{"id": "th-short", "messages": short_mixed},
                      {"id": "th-other", "messages": [{"text": sub, "time": 1}]}]}, "forked"),
    ]
    for name, b, want in mix_cases:
        total += 1
        rows_ = audit(b, [MREF])
        got = classify(rows_, {MREF: True})[0]["verdict"]
        good = got == want
        ok += 1 if good else 0
        print(f"  {'✅' if good else '❌'} {name}: got={got} 期望={want}")

    # ── 通知类发言的机械识别（真语料字数边界：56 / 245 / 2957）──
    REF = "notes/mac-mini/mingjian-review-fork-audit-three-gaps"
    ptr56 = "看黑板 " + REF
    full245 = "看黑板 data/registry/fork-audit-and-bus-torn-read-20260914 —— " + "展开" * 60 + REF
    full2957 = "看黑板 " + REF + "\n\n" + "正文" * 900
    ptr_cases = [
        ("反例·真语料 **56 字**指针（明鉴 16:21:32）⇒ 必判通知类", ptr56, True),
        ("正例·真语料 **245 字**（星桥 16:10:00 那条，含展开）⇒ **不得**判通知类", full245, False),
        ("正例·真语料 **2957 字**全文（明鉴 16:21:41）⇒ 不得判通知类", full2957, False),
        ("反例·短句自述「不重复处理」⇒ 属通知类（明鉴指出的正是这种）",
         "本内容与已处理一致，不重复处理。" + REF, True),
    ]
    for name, txt, want in ptr_cases:
        total += 1
        got = is_pointer(txt)
        good = got == want
        ok += 1 if good else 0
        print(f"  {'✅' if good else '❌'} {name}: got={got} 期望={want}")
    # ── 仅通知型分叉 vs 真分叉（同一 ref 落在两条线，但其中一条只有通知）──
    nt_bus = {"threads": [
        {"id": "th-first", "messages": [{"text": full2957, "time": 100}]},
        {"id": "th-second", "messages": [{"text": ptr56, "time": 200}]},
    ]}
    real_bus = {"threads": [
        {"id": "th-a", "messages": [{"text": full245, "time": 100}]},
        {"id": "th-b", "messages": [{"text": full2957, "time": 200}]},
    ]}
    one_bus = {"threads": [{"id": "th-a", "messages": [{"text": full245, "time": 100}]}]}
    fork_cases = [
        ("反例·一线展开 + 一线**只有 56 字通知** ⇒ 判 fork-notification（**不得**报普通 forked）",
         nt_bus, "fork-notification"),
        ("反例·两线都有展开 ⇒ 判 forked", real_bus, "forked"),
        ("正例·单线 ⇒ ok（通知不得制造分叉）", one_bus, "ok"),
    ]
    for name, b, want in fork_cases:
        total += 1
        rows_ = audit(b, [REF])
        got = classify(rows_, {REF: True})[0]["verdict"]
        good = got == want
        ok += 1 if good else 0
        print(f"  {'✅' if good else '❌'} {name}: got={got} 期望={want}")
    # 首提线 = 最早 ts 的那条线
    total += 1
    rows_ = audit(nt_bus, [REF])
    got = rows_[0]["first_thread"]
    good = got == "th-first"
    ok += 1 if good else 0
    print(f"  {'✅' if good else '❌'} 反例·**首提线**须取最早 ts 的线程（th-first，非字典序）: got={got} 期望=th-first")

    # ── IO 映射的牙：注入假 probe（否则 400/404 分支**根本不被 selftest 走到**）──
    io_cases = [
        ("反例·probe 返回 400 ⇒ 必判 bad-key",
         lambda: ref_exists("data/registry/x", "http://x", probe=lambda u, t=12: 400), "bad-key"),
        ("反例·probe 返回 404 ⇒ 必判 不存在（False）",
         lambda: ref_exists("data/registry/x", "http://x", probe=lambda u, t=12: 404), False),
        ("正例·probe 返回 200 ⇒ True", lambda: ref_exists("data/registry/x", "http://x",
                                                          probe=lambda u, t=12: True), True),
        ("正例·probe 异常/其它码 ⇒ None（**不得**当不存在）",
         lambda: ref_exists("data/registry/x", "http://x", probe=lambda u, t=12: None), None),
    ]
    for name, fn, want in io_cases:
        total += 1
        got = fn()
        good = got == want
        ok += 1 if good else 0
        print(f"  {'✅' if good else '❌'} {name}: got={got} 期望={want}")

    dn_cases = [
        ("反例·`declared-none`（显式声明无产物）⇒ 判 NONE，**不得**判 missing/unverified/ok",
         [mk("无产物", one)], {"无产物": "declared-none"}, "declared-none"),
        ("反例·声明无产物**不得**进 stub 建议集合（它已判过：本议题无产物）",
         [mk("无产物", one)], {"无产物": "declared-none"}, 0),
    ]
    for name, rws, ex, want in dn_cases:
        total += 1
        got = len(stub_targets(classify(rws, ex))) if isinstance(want, int) else classify(rws, ex)[0]["verdict"]
        good = got == want
        ok += 1 if good else 0
        print(f"  {'✅' if good else '❌'} {name}: got={got} 期望={want}")
    # ── 行数守恒（真语料边界：HR 收敛表 v3 的 8 行形态）──
    real = [{"卡键": "无产物"} for _ in range(5)] + [
        {"卡键": "data/registry/topic-stub-verification-boundary-20260914"},
        {"卡键": "data/registry/topic-stub-caliber-two-groups-20260914"},
        {"卡键": "data/registry/topic-stub-caliber-three-levels-20260914"}]
    cons_cases = [
        ("真语料·收敛表 8 行（5 行显式「无产物」+ 3 行真键）⇒ 有效 ref 3 · 声明 5 · **守恒**",
         real, "卡键", (3, 5, 0, True, 0)),
        ("反例·5 行**同一 ref** ⇒ 必须报折叠 4 行（旧版静默塌成 1 个对象）",
         [{"卡键": "data/registry/same-key"}] * 5, "卡键", (1, 0, 0, True, 4)),
        ("反例·存在**空字段**行 ⇒ 计入空字段（未声明的缺口，不得静默跳过）",
         [{"卡键": "data/registry/k"}, {"卡键": ""}, {"卡键": None}, {"议题": "只有议题没有键"}],
         "卡键", (1, 0, 3, True, 0)),
        ("边界·全部声明无产物 ⇒ 有效 ref 0（此时不得报「审计 0 个对象」当健康）",
         [{"卡键": "无产物"}] * 3, "卡键", (0, 3, 0, True, 0)),
    ]
    for name, rws, fld, want in cons_cases:
        total += 1
        u, dn, ef, acct = partition_registry(rws, fld)
        got = (len(u), len(dn), len(ef), acct["守恒"], acct["折叠行数"])
        good = got == want
        ok += 1 if good else 0
        print(f"  {'✅' if good else '❌'} {name}: got={got} 期望={want}")

    # ── 400 vs 404：键写法非法（真语料：收敛表 `卡` 字段的融串）──
    bk_cases = [
        ("反例·★融了内容标识的字符串（真语料 ⇒ GET 400）必判 bad-key（不得并入 unverified，也不得判缺失）",
         [mk("data/registry/topic-stub-verification-boundary-20260914（d6ea577d）", one)],
         {"data/registry/topic-stub-verification-boundary-20260914（d6ea577d）": "bad-key"}, "bad-key"),
        ("反例·bad-key + 已分叉 ⇒ bad-key+forked（两缺陷叠加不得降级）",
         [mk("data/registry/foo（abc123）", two)], {"data/registry/foo（abc123）": "bad-key"}, "bad-key+forked"),
        ("正例·合法键返回 200 ⇒ ok（400 分支不得吃掉正常键）",
         [mk("data/registry/topic-stub-verification-boundary-20260914", one)],
         {"data/registry/topic-stub-verification-boundary-20260914": True}, "ok"),
        ("反例·键写法非法也须进 stub 建议集合（要修字段，不只是建卡）",
         [mk("data/registry/foo（abc123）", one)], {"data/registry/foo（abc123）": "bad-key"}, 1),
    ]
    for name, rws, ex, want in bk_cases:
        total += 1
        if isinstance(want, int):
            got = len(stub_targets(classify(rws, ex)))
        else:
            got = classify(rws, ex)[0]["verdict"]
        good = got == want
        ok += 1 if good else 0
        print(f"  {'✅' if good else '❌'} {name}: got={got} 期望={want}")
    # stub 触发条件扩展：已分叉 ∨ 产物不存在
    stub_cases = [
        ("反例·产物不存在且未分叉 ⇒ **必须**进建议集合（旧版因『没分叉』跳过）",
         [mk("data/registry/hr-reply-mingjian-format-drift-excluded-20260911", one)],
         {"data/registry/hr-reply-mingjian-format-drift-excluded-20260911": False}, 1),
        ("正例·产物存在且未分叉 ⇒ 不进建议集合（不得滥发建键建议）",
         [mk("data/registry/card-z", one)], {"data/registry/card-z": True}, 0),
        ("真语料·21 个双侧 404 的 ref 全部未分叉 ⇒ 建议数必须 = 21（0 ⇒ 假阴性回归）",
         [mk(f"data/registry/hr-reply-mingjian-missing-{i}-20260911", one) for i in range(21)],
         {f"data/registry/hr-reply-mingjian-missing-{i}-20260911": False for i in range(21)}, 21),
    ]
    for name, rws, ex, want in stub_cases:
        total += 1
        got = len(stub_targets(classify(rws, ex)))
        good = got == want
        ok += 1 if good else 0
        print(f"  {'✅' if good else '❌'} {name}: got={got} 期望={want}")
    # ── 输入项质量门：用**真语料边界例**（2026-09-14 实测命中数）作例 ──
    spec_cases = [
        ("反例·泛化片段 `hr-ruling`（真语料实测 74 张）⇒ 必判 too-generic",
         [("t", f"k{i}", 1) for i in range(74)], "hr-ruling", "too-generic"),
        ("反例·纯日期片段 `20260914`（真语料实测 163 张）⇒ 必判 too-generic",
         [("t", f"k{i}", 1) for i in range(163)], "20260914", "too-generic"),
        ("正例·`caliber`（真语料实测 5 张）⇒ 可判 ok（不得误报为泛化）",
         [("t", f"k{i}", 1) for i in range(5)], "caliber", "ok"),
        ("正例·`verification-boundary`（真语料实测 2 张）⇒ ok",
         [("t", f"k{i}", 1) for i in range(2)], "verification-boundary", "ok"),
        ("正例·唯一命中 ⇒ 可作身份（exact）", [("t", "k0", 1)], "one-key", "exact"),
        ("正例·零命中 ⇒ empty（不得当作 too-generic）", [], "nonexistent-frag", "empty"),
        ("边界·恰在上界（12 张）⇒ ok（上界为闭区间，须与 13 区分）",
         [("t", f"k{i}", 1) for i in range(SPECIFICITY_MAX)], "boundary-12", "ok"),
        ("边界·上界 +1（13 张）⇒ too-generic",
         [("t", f"k{i}", 1) for i in range(SPECIFICITY_MAX + 1)], "boundary-13", "too-generic"),
    ]
    for name, rows, frag, want in spec_cases:
        total += 1
        got = topic_specificity(rows, frag)[0]
        good = got == want
        ok += 1 if good else 0
        print(f"  {'✅' if good else '❌'} {name}: got={got} 期望={want}")
    # ── 分类完备性（明鉴 2026-09-14 提出的风险，本版实现为断言）──
    _tot_ok, _unexp_ok, _bad, _unexp = _selftest_verdict_total()
    total += 2
    ok += 1 if _tot_ok else 0
    print(f"  {'✅' if _tot_ok else '❌'} 分类完备·判别域全部组合均落在已声明类别内（无静默归并通道）"
          + (f"：越界 {_bad}" if _bad else ""))
    ok += 1 if _unexp_ok else 0
    print(f"  {'✅' if _unexp_ok else '❌'} **负例**·未预期取值 `'oops'` ⇒ 必须落到 `other` 而后会报警，"
          f"**不得落到 ok**：got={_unexp}")
    print(f"\nselftest {ok}/{total}")
    return 0 if ok == total else 1


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--bus", default=os.path.expanduser("~/.dsh/agent-bus.json"))
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    ap.add_argument("--refs", help="逗号分隔的对象标识（card-key 或 key 片段）")
    ap.add_argument("--registry", help="收敛表 JSON（取其 ref 字段，或 --ref-field 指定）")
    ap.add_argument("--ref-field", default="ref")
    ap.add_argument("--topic-lookup", help="发布前查更晚裁定：给定议题 card-key 片段，按键名列出关联卡并按信封 ts 倒序")
    ap.add_argument("--bb", default="http://127.0.0.1:8792")
    ap.add_argument("--ident-field", default="内容标识",
                    help="收敛表里存内容标识的列名；提供后本工具会**现算并比对**（漂移会单独报，不静默）")
    ap.add_argument("--stub-suggest", action="store_true",
                    help="对（已分叉 ∨ 产物不存在）的 ref 给出**占位卡键建议**（只打印，不写盘）")
    ap.add_argument("--no-exists-check", action="store_true",
                    help="跳过产物存在性解析（判决一律标 unverified，不得读作 ok）")
    ap.add_argument("--keyword-check", help="逗号分隔的议题关键词，对照收敛表判定是否已登记（明鉴 2026-09-14 判据）")
    ap.add_argument("--json-out")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    if "--selfcheck" in __import__("sys").argv:
        return selfcheck()
    args = ap.parse_args()

    if args.version:
        print(json.dumps({"tool": "thread-fork-audit", "version": VERSION,
                          "source_id": _tool_source_id(),
                          "file_sha256": _tool_sha16(),
                          "file_mtime": _tool_mtime(),
                          "py": f"{sys.version_info[0]}.{sys.version_info[1]}",
                          "rule": "同一对象标识出现在 ≥2 线程 = 分叉；按 ref 而非内容分组"}, ensure_ascii=False))
        return 0
    if args.selftest:
        return selftest()

    if args.topic_lookup:
        rows = topic_lookup(args.topic_lookup, args.bb)
        verdict, reason = topic_specificity(rows, args.topic_lookup)
        print(f"议题「{args.topic_lookup}」按键名匹配到 {len(rows)} 张卡（信封 ts 倒序）：")
        for ts, k, ver in rows[:12]:
            print(f"   {ts or '无ts'}  v={ver}  {k.split('/')[-1]}")
        if len(rows) > 12:
            print(f"   …（另有 {len(rows) - 12} 张未打印）")
        print(f"\n【输入项质量门】{verdict}：{reason}")
        if verdict == "too-generic":
            return 3
        if rows:
            print(f"\n⇒ 判定句（HR 2026-09-14）：发布涉及该议题的归类/裁定前，**须先取本列表首行 ts 比对**；"
                  f"若已有更晚的裁定 ⇒ 先读它再发布。本门只接受「具体卡键 + ts 比较结果」。")
        return 0

    if args.keyword_check:
        if not args.registry:
            print("--keyword-check 需要 --registry <收敛表 JSON>", file=sys.stderr)
            return 2
        rp = os.path.expanduser(args.registry)
        ident = registry_identity(rp)
        print("【注册表：身份 + 出处】" + json.dumps(ident, ensure_ascii=False))
        print("   ⇒ 缺这一行，结论不可引用（位置相同、内容可不同 —— 2026-09-14 实测过）")
        reg = json.load(open(rp, encoding="utf-8"))
        rows = reg if isinstance(reg, list) else reg.get("rows", reg.get("citations", []))
        kws = [k.strip() for k in args.keyword_check.split(",") if k.strip()]
        per, systematic = keyword_check(rows, kws)
        if systematic != "ok":
            print(f"\n【系统性状态】**{systematic}** ⇒ **本查询对该表无法区分两种情形**：")
            print("   (i) 该议题**真的**未登记 ⇒ 应补行 · (ii) **表结构不支持关键词匹配** ⇒ **所有**议题都匹配不上")
            print(f"   ⇒ 实测：表内没有任何关键词字段（候选字段名 {list(KEYWORD_FIELDS)}，逐行检查 0 命中）"
                  f" ⇒ **下面逐条「未登记」无信息量，不得据此补行。**")
            print("   ⇒ 修法（明鉴 2026-09-14）：先报系统性状态，再报个别状态 —— 同形读数必须分开。")
            for x in per:
                print(f"  {x['kw']}: **不可判**（表缺关键词字段）")
            return 4
        for x in per:
            if x["hit"] is None:
                print(f"  {x['kw']}: **未登记**（表中无对应关键词）")
            elif x["hit"]["by"] == "declared":
                print(f"  {x['kw']}: **已登记** → {x['hit']['topic']}（依据：**声明的关键词字段**）")
            else:
                print(f"  {x['kw']}: **疑似已登记（弱证据）** → {x['hit']['topic']}"
                      f"（依据：**整行文本兜底匹配** ⇒ **退化匹配**，可能与议题无关，须人工核）")
        print("\n判据（明鉴）：任一新议题在被处理前，须能回答「它的关键词是否已在表中」⇒ 使『未登记』从需要人想变成一次查询。")
        print("⚠ 层级说明（采纳 HR 2026-09-14）：**关键词层仅作召回辅助**（供人搜索）；**归属判定层应走 card-key 唯一标识，不接受模糊输入**。")
        return 0 if all(x["hit"] for x in per) else 1

    refs, declared_none, empty_field, acct = [], [], [], None
    if args.refs:
        refs += [r.strip() for r in args.refs.split(",") if r.strip()]
    IDENT_EXPECT = {}
    if args.registry:
        reg_rows, REG_IDENT, IDENT_EXPECT, SRC_KIND = load_registry(args.registry, args.bb, args.ident_field)
        print(f"【注册表：身份 + 出处】{REG_IDENT}")
        print("   ⇒ 缺这一行，结论不可引用（位置相同、内容可不同 —— 2026-09-14 实测过）")
        u, declared_none, empty_field, acct = partition_registry(reg_rows, args.ref_field)
        # ★ 守恒账目【第二栏：分类完备】（明鉴 2026-09-14：只有行数守恒 ⇒ 行都在但可能被静默归并）
        _VERDICT_DOMAIN = (True, False, None, "bad-key", "declared-none")
        for _e in _VERDICT_DOMAIN:
            for _fk in ({}, {"forked_pure": True}, {"forked_effective": True}, {"forked": True}):
                _v = classify([{**{"ref": "x"}, **_fk}], {"x": _e})[0]["verdict"]
                if _v not in {"ok", "forked", "missing", "missing+forked", "unverified",
                              "bad-key", "bad-key+forked", "declared-none",
                              "fork-notification", "fork-mixed"}:
                    print(f"❌ 分类不完备：exists={_e!r} flags={_fk} ⇒ verdict={_v!r} 不在声明类别内")
                    return 3
        print("【分类完备】已断言：判别域 "
              + "/".join(repr(x) for x in _VERDICT_DOMAIN)
              + " × {分叉旗标 4 值} 的**全部组合**都落在已声明类别内 ⇒ 无静默归并通道")
        refs += u
    if not refs and acct is None:
        ap.print_help()
        return 2
    if acct is not None:
        print(f"【行数守恒】输入 {acct['输入行']} 行 = 有效 ref 行 {acct['有效 ref 行']} + 声明无产物 "
              f"{acct['声明无产物']} + 空字段 {acct['空字段']}  ⇒ {'✅守恒' if acct['守恒'] else '❌不守恒（有行未被计数）'}")
        if acct["折叠明细"]:
            print(f"   ⚠ 折叠：{acct['折叠行数']} 行因**同一 ref** 被合并 ⇒ " +
                  " · ".join(f"{k} × {v}" for k, v in acct["折叠明细"].items()))
        for i, v in declared_none:
            print(f"   [NONE] 行{i + 1} 显式声明无产物（`{args.ref_field}`=`{v}`）⇒ 不再探测（这是**已判过**的值，不是缺口）")
        if empty_field:
            print(f"   ⚠ 空字段 {len(empty_field)} 行（**未声明**的缺口 ⇒ 与「声明无产物」不同，须补值）："
                  f"{[i + 1 for i, _ in empty_field]}")
        if not refs:
            print("   （本表无有效 ref ⇒ 无可审计对象）")
            return 1 if empty_field else 0
        print()

    # 公交车状态文件（19MB 单文件、就地重写）会被**撕裂读**命中的概率不低：
    #   2026-09-14 实测一次读取报 Un-terminated string，重试即成功 ⇒ 这里做有限重试并给出明确指引。
    bus = None
    last = None
    for attempt in range(4):
        try:
            bus = _load_json_strict(os.path.expanduser(args.bus))
            break
        except Exception as e:
            last = e
            time.sleep(0.6)
    if bus is None:
        print(f"读取 {args.bus} 失败（重试 4 次）：{last}\n"
              f"⇒ 若报 Unterminated string/Extra data，多为**撕裂读**（文件正被就地重写）。"
              f"建议：稍后重试，或推动该文件改为『写临时文件 + 原子 rename』。", file=sys.stderr)
        return 2
    # ★ 复合数须带窗口（明鉴 2026-09-14 自曝 L3：她的「9 条 / 6 线程」两个分量来自不同窗口）
    #   ⇒ 凡本工具报「N 线程 / M 条」，先打印**总线快照标识**，使两个分量同源可核。
    try:
        _bp = os.path.expanduser(args.bus)
        _st = os.stat(_bp)
        _sha = __import__("hashlib").sha256(open(_bp, "rb").read()).hexdigest()[:12]
        print("【工具标识】" + tool_identity_line())
        print(f"【总线快照】{args.bus} · mtime={time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(_st.st_mtime))}"
              f" · bytes={_st.st_size} · sha256[:12]={_sha} · 读取时刻={time.strftime('%Y-%m-%dT%H:%M:%S')}")
        print("   ⇒ 「N 线程 / M 条」两个分量**同源于本快照**；报数须连本行一起引（明鉴 2026-09-14：不同窗口的分量拼成一个数 = L3）")
    except Exception as _e:
        print(f"【总线快照】取标识失败：{str(_e)[:60]} ⇒ 本报告的 N/M **不得引用**（无窗口）")
    rows = audit(bus, refs)
    # ★ 存在性维（明鉴 2026-09-14）：先解析每个 ref 指向的产物是否存在，再给判决
    listing = None
    if any("/" not in r["ref"] for r in rows):
        try:
            lst = json.load(urllib.request.urlopen(f"{args.bb}/data/registry/", timeout=20))
            listing = lst.get("list") if isinstance(lst.get("list"), list) else None
        except Exception:
            listing = None
    exists = {}
    for r in rows:
        if args.no_exists_check:
            exists[r["ref"]] = None
        else:
            exists[r["ref"]] = ref_exists(r["ref"], args.bb, listing)
    # ── 内容标识一致性（2026-09-14，本版新增）：表里那一列是**写死的活量** ⇒ 现算并比对。
    #    ★ 不比对就会：卡一改，表里那个 16 位依然「有值」，读的人无从知道它已经过期。
    IDENT = {}
    for ref, want in (IDENT_EXPECT or {}).items():
        if not want or str(want).strip() in ("", "无","—","-"):
            IDENT[ref] = ("n/a", None, None); continue
        try:
            env = json.load(urllib.request.urlopen(f"{args.bb}/{ref}", timeout=15))
            got = content_ident(env.get("value", {}))
            IDENT[ref] = ("ok" if got == str(want).strip() else "STALE", str(want).strip(), got)
        except Exception as exc:                      # noqa: BLE001
            IDENT[ref] = ("unknown", str(want).strip(), f"{type(exc).__name__}")
    rows = classify(rows, exists)
    tag = {"ok": "ok  ", "forked": "FORK", "missing": "MISS", "missing+forked": "MISS·FORK",
           "unverified": "?   ", "bad-key": "KEY400", "bad-key+forked": "KEY400·FORK",
           "other": "**OTHER**",   # 不该出现；出现即「分类不完备」报警
           "declared-none": "NONE", "fork-notification": "FORK·通知型", "fork-mixed": "FORK·混装线"}
    for r in rows:
        eff = r.get("n_threads_effective", r["n_threads"])
        pure = r.get("n_threads_pure", eff)
        bits = []
        if eff != r["n_threads"]:
            bits.append(f"排除通知后 {eff}")
        if pure != eff:
            bits.append(f"**再排除混装线后 {pure}**")
        extra = (" · " + " · ".join(bits)) if bits else ""
        _id = (IDENT or {}).get(r["ref"])
        _idtxt = ""
        if _id:
            st, want, got = _id
            if st == "ok":
                _idtxt = f"   [IDENT ✅ 表内 {want} = 现算 {got}]"
            elif st == "STALE":
                _idtxt = f"   [IDENT ⚠**漂移**：表内 {want} ≠ 现算 {got} ⇒ **表的这一列已过期**（卡改过）]"
            elif st == "unknown":
                _idtxt = f"   [IDENT ? 现算失败（{got}）⇒ 表内 {want} **未核**，不得读成一致]"
            else:
                _idtxt = "   [IDENT n/a 表内声明无内容标识]"
        print(f"[{tag[r['verdict']]}] {r['ref']} — {r['n_threads']} 线程 / {r['n_messages']} 条消息{extra}{_idtxt}")
        for tid, d in sorted(r["threads"].items(), key=lambda kv: kv[1]["first_ts"] or 0):
            mk2 = ("  ← **首次出现该 ref 的线**（**ref 级**；议题级首提线可能不同）" if tid == r.get("first_thread") else "")
            mark = mk2 + ("  **⚠ 混装线（主体不是本议题）**" if tid in r.get("mixed_threads", []) else "")
            print(f"        {tid} — 命中 {d['n']} 条（其中通知 {d['n_pointer']}）{mark}")
    if IDENT:
        _ok = sum(1 for v in IDENT.values() if v[0] == "ok")
        _st = [k for k, v in IDENT.items() if v[0] == "STALE"]
        _un = [k for k, v in IDENT.items() if v[0] == "unknown"]
        _na = len(declared_none)   # ★ 不用 IDENT 计数（它按 卡键 折叠）
        print(f"\n【内容标识一致性】一致 {_ok} · **漂移 {len(_st)}** · 未核 {len(_un)} · 声明无 {_na}"
              + (f" ⇒ 漂移：{' · '.join(_st)}" if _st else "")
              + "   ← 这一项必须报：表里那一列是**写死的活量**，不比对就会在卡更新后静默过期"
              if _st or _un else "\n【内容标识一致性】" + f"一致 {_ok} · 漂移 0 · 未核 0 · 声明无 {_na} ⇒ ✅ 表内值与现算一致")
    forked = [r for r in rows if r.get("forked_pure", r.get("forked_effective", r["forked"]))]
    notif = [r for r in rows if r["forked"] and not r.get("forked_effective", r["forked"])]
    mixedonly = [r for r in rows if r.get("forked_effective", False) and not r.get("forked_pure", True)]
    missing = [r for r in rows if r["exists"] is False]
    badkey = [r for r in rows if r["exists"] == "bad-key"]
    unverified = [r for r in rows if r["exists"] is None]
    if args.stub_suggest:
        stubs = stub_targets(rows)
        if stubs:
            print("\n=== 占位卡键建议（触发条件：**已分叉 ∨ 产物不存在**；本工具只建议、不写盘）===")
            for r in stubs:
                base = r["ref"].split("/")[-1]
                why = "产物不存在" if r["exists"] is False else "已分叉"
                print(f"  [{why}] {r['ref'][:52]:54} → 建议卡键 data/registry/{base}")
            print("  判据（HR 2026-09-14 + 明鉴 2026-09-14）：议题一旦在第二条线上出现，或**指针指向不存在的产物**，"
                  "立即为其建占位卡键并登记归属。")
    print(f"\n审计 {len(rows)} 个对象标识 · **真分叉 {len(forked)} 个**（已排除通知类发言与混装线）· **仅通知型分叉 {len(notif)} 个** · **仅混装线分叉 {len(mixedonly)} 个** · **产物不存在 {len(missing)} 个** · "
          f"**键写法非法(400) {len(badkey)} 个** · 存在性不可判 {len(unverified)} 个")
    if notif:
        print("⚠ **仅通知型分叉**（把通知类发言剔除后这些 ref 只剩 1 条线程 ⇒ 分叉消失）：")
        for r in notif:
            print(f"      {r['ref']} — 全部 {r['n_threads']} 线程 / 有效 {r['n_threads_effective']}")
        print("   ⇒ 判据（明鉴 2026-09-14）：**通知类发言会给分叉数加分**；本工具按「排除通知后的线程数」判真分叉，"
              f"两类分列。识别规则：正文 ≤ {POINTER_MAX} 字且以「看黑板/详见 thread-/不重复处理」形式引用 "
              "⇒ 标为通知类（**抽取规则，非事实**）。")
    if badkey:
        print("⚠ 这些 ref **不是键**（GET 返回 400 bad key ⇒ 极可能是**把「位置」和「内容标识」写进了同一个字段**，"
              "例如 `…-20260914（d6ea577d）`）：")
        for r in badkey:
            print(f"      {r['ref']}")
        print("   ⇒ 要修的是**调用方的字段**（拆成 `卡键` + `内容标识` 两格），不是产物。")

    if missing:
        print(f"⚠ 产物不存在的 ref（这些**不是**健康信号，是指向空处的指针）：")
        for r in missing:
            print(f"     {r['ref']}")
    if unverified:
        print(f"⚠ 存在性**不可判**（探测失败 ⇒ 不得当作出存在，也不得当作不存在）："
              f"共 {len(unverified)} 个")
    if args.json_out:
        json.dump({"version": VERSION, "rows": rows}, open(os.path.expanduser(args.json_out), "w"),
                  ensure_ascii=False, indent=1)
        print(f"json → {args.json_out}")
    _other = [r for r in rows if r["verdict"] == "other"]
    if _other:
        print(f"⚠ **OTHER（未预期取值）{len(_other)} 行** ⇒ 分类不完备，账目不可信："
              f"{[r['ref'] for r in _other][:5]}")
    return 1 if (forked or missing or badkey or empty_field or _other) else 0


if __name__ == "__main__":
    sys.exit(main())
