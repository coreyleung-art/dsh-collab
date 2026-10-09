#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
absence-claim-lint —— 「否定性结论须附观测面声明」的可机械核验门（v2.0.0）

规则（2026-09-14 与 HR/老登共同定稿，来自当日同形状三例）：
    否定性结论（不存在 / 未提供 / 从未 / 零调用 / 未加载 / 无远端 …）
    必须同卡附「观测面声明」：查了哪些**路径**、哪条**命令**、哪些**扩展名**。
    缺声明 ⇒ 降格为「在我所查范围内未发现」。HR 裁定：**条件必填**（非全卡必填）。

判级：
    🔴 fail  有否定性结论，但全卡无任何观测面证据
    🟡 warn  有否定性结论 + 有观测面证据但无显式「观测面」字段；**或含引用/转述特征**
    ✅ pass  无否定性结论，或结论附有显式观测面声明

v2.0.0 两项方法学修正（均采纳 HR 2026-09-14 裁定）：
    ① **--coverage v1.0|v1.1|v1.2**：三代判据集可切换 ⇒ 可在**同一份库快照**上重放三代，
       把「工具归因差分」与「库变化分量」分离（此前 277→258→259 的差被单一归因是错的）。
    ② **结构性排除**取代「引用类 FP 率点估计」：含引用/转述特征的卡一律封顶为 warn、永不阻断，
       阻断域收缩到「无引用特征 ∩ 🔴 fail」⇒ FP 风险被结构排除，无需等引用问题解决。

用法：
    python3 absence-claim-lint.py --ns data/registry [--coverage v1.2] [--limit N] [--json-out F]
    python3 absence-claim-lint.py --dir SNAPSHOT_DIR [--coverage v1.2]
    python3 absence-claim-lint.py --snapshot --dir OUTDIR        # 冻结同库快照供重放
    python3 absence-claim-lint.py --sample N | --selftest | --version
    退出码：0 全部通过 · 1 存在 🔴/🟡 · 2 参数错误

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）


import argparse
import ast
import hashlib
import inspect
import json
import os
import re
import sys
import textwrap
import urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/absence-claim-lint.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = "3.13.0"
DEFAULT_BB = os.environ.get("BB_URL", "http://127.0.0.1:8792")

# ── 三代判据集（可重放，用于同快照差分） ──────────────────────────────────
CLAIM_V10 = [
    r"不存在", r"未提供", r"找不到", r"未发现", r"从未", r"无任何", r"没有任何",
    r"零调用", r"未调用", r"均为空", r"未接线", r"未加载", r"无远端", r"未扩散",
    r"未被使用", r"没有使用", r"无调用点", r"未注册", r"未挂载",
]
CLAIM_V11_ADD = [
    r"(?:全部|均|都|并)不在", r"没找到", r"未见", r"尚未", r"尚未见", r"缺少",
    r"为空", r"空值", r"无消费者", r"未命中", r"不匹配", r"未覆盖", r"无人读取",
    r"未生效", r"没在跑", r"未在跑", r"零次", r"0 次调用", r"无调用", r"未实现", r"未接上",
]
COVERAGE = {
    "v1.0": {"patterns": CLAIM_V10, "guards": False},
    "v1.1": {"patterns": CLAIM_V10 + CLAIM_V11_ADD, "guards": False},
    "v1.2": {"patterns": CLAIM_V10 + CLAIM_V11_ADD, "guards": True},
}

# 命中即忽略的复合词（避免「不存在性」「无人值守」这类假阳性）
FALSE_FRIENDS = [
    r"不存在性", r"无人值守", r"无人区", r"无头",
    r"未发现异常", r"未见异常", r"不匹配也无妨", r"未覆盖到也无妨",
]
META_FIELD_RE = re.compile(r"规则|示例|判据|关键词|keyword|定义", re.IGNORECASE)
# ★ 不可逆条款（老登 2026-09-14 建议）：**warn 永久不阻断**。
#   理由（他的实测）：我 v3.2.0 的精度修复是「**移**」不是「**消除**」 —— 被他判为假阳性的 5 张里，
#   仍有 2 张（`blackboard-write-format-bug` · `g3-procure-archaeo`）**仍是假阳性**，只是从 fail 层
#   **降到**了 warn 层。⇒ 分层后：**fail 层 precision 无定义（空域）· warn 层 precision = 0/2（该样本）**。
#   ⇒ 若将来把 warn 纳入阻断 ⇒ **立即把那 2 张假阳性重新纳入**（它们从未消失，只是被降级）。
#   ⇒ 故写入**条款**而非「当前设计」，使该决定不可随实现漂移。
WARN_NEVER_BLOCKS_CLAUSE = (
    "warn 永久不阻断（不可逆条款）：warn 层当前 precision = 0/2（老登人工标注样本）⇒ "
    "把 warn 纳入阻断会立即把已知假阳性重新纳入。若将来要改此条款，须先给出 warn 层的 precision 证据。")

NEGATED_BEFORE = ("非", "不", "不是", "并非", "没有", "无此")

# v2.0.0：引用/转述特征 ⇒ 结构性不阻断（HR 裁定）
QUOTATION_RE = re.compile(
    r"[「『].{2,40}[」』]"                                    # 引号包裹的引用块
    r"|(?:引用|转述|据|摘|原文|对方|他人|老登|HR|守灯|明鉴|星桥|协调者)\s*(?:说|称|指出|主张|报告|认为|的卡|卡里)"
    r"|已作废|撤回|更正|被引"
)
SCOPE_FIELD_RE = re.compile(r"观测面|范围|scope|检索|扫描|命令|查了|观测|手段")
# v3.2.0：两类由老登人工标注（5 张）暴露的盲点
#   ① 检查动词是「观测面痕迹」的一种表述（他实测这些词在我的源码里 0 次出现 ⇒「已自查」不可见）
CHECK_VERB_RE = re.compile(r"自查|已查|逐条|对照|复核|核过|查过")
#   ② 「无X / 没有X」若邻近检查动词，属「已检且未见」的自述，不当作否定性结论
EXEMPT_NEAR_CHECK = re.compile(r"(无|没有|未见|未发现)[^。；\n]{0,24}(自查|已查|逐条|对照|复核|核过|查过)")
# v2.1.0：老登判据 —— 观测面声明须含「排除项」，只列含项会让读者默认其余已覆盖
EXCLUSION_RE = re.compile(r"未查|未扫|未覆盖|未含|不含|不在此|没查|排除|未验证|未列|未观测|待查")
# v2.7.0：老登判据 —— 凡结论为「0/未发现」，同卡须附「已知非零对照」实测值；
#   无对照的 0 降格为「命令未证实有效」。（他自陈：复测时把标签并进搜索串得 0，还当场为这个 0 编了机制）
# v3.7.0（老登 2026-09-14 标定 9 例）：
#   旧式样要求「数字 0 紧跟量词」⇒ 漏掉**裸数字 0**（最危险且最常见的写法）
#   放宽到裸 0 会立刻假阳性 ⇒ 故**裸 0 须带邻近守卫**（前有 得/为/是/共/计/命中数/计数为，或后接 命中/量词）
#   他的真语料负例集（须保持不触发）：127.0.0.1 · v2.0.0 · 20260914 · 0/380
ZERO_RE = re.compile(
    r"(?:=|＝|为|计)?\s*0\s*(?:行|次|个|张|条|处|%|次调用)"
    r"|未命中|未发现(?:任何|该|此|匹配|命中|相关|相应)|命中\s*0|计数为\s*0"
    r"|(?:得|为|是|共|计|命中数(?:为)?|计数为)\s*0(?![\d.])"   # 裸 0 + 邻近守卫
    r"|0\s*命中|零命中|没有命中"
)
# ★★ v3.9.0（老登 2026-09-14 的类别守卫建议）：**「为 0」的语义由主语的名词类别决定**。
#   他实测三类**语义相反**的假阳性：
#     · `该命令退出码为 0` ⇒ 我们整套制品里「退出码为 0」**＝成功**，是**最强形式的肯定断言**，
#        却被判成「需要非零对照的零值断言」⇒ **语义完全反了**
#     · `数组下标为 0` ⇒ **位置**语义 · `该渠道占比为 0` ⇒ **比率**语义（按比率族该走分子/分母/框/时点）
#   且存在写法敏感：`退出码为 0` 被抓、`exit = 0` 不抓 ⇒ 判据对写法敏感而非对语义敏感。
#   ⇒ 判据（他给的）：**主语类别是【封闭集】，而「0 前面的动词」不是** ⇒ 锚在主语类别上。
ZERO_SUBJECT_CLASSES = (
    ("status_code", re.compile(r"(退出码|状态码|返回码|错误码|exit[_ ]?code|exitcode|status[_ ]?code|return[_ ]?code|\brc\b|exit\s*=|=\s*exit)")),
    ("position",    re.compile(r"(下标|索引|索引值|序号|行号|偏移|位置|index|offset|position)")),
    ("ratio",       re.compile(r"(占比|比率|比例|百分比|率\b|rate|ratio|percent|百分点)")),
    ("count",       re.compile(r"(命中数|命中|计数|个数|数\b|张|条|处|次|行数|文件数|调用数|出现)")),
)


def zero_subject_class(text):
    """返回 zero 的主语类别：status_code / position / ratio / count / None（未判）。

    ★ 只对**含 0 的文本**调用；在 0 之前的一段窗口里找主语名词 ⇒ **类别是封闭集**（老登 2026-09-14）。
    """
    if not text:
        return None
    for m in re.finditer(r"0", str(text)):
        win = str(text)[max(0, m.start() - 24): m.start()]
        for name, rx in ZERO_SUBJECT_CLASSES:
            if rx.search(win):
                return name
    return None


CONTROL_RE = re.compile(r"对照|正控|阳性对照|已知非零|控制组|反例")
SCOPE_TOKEN_RE = re.compile(
    r"~/|/Users/|/var/|\b(?:grep|rg|curl|find|ls|sqlite3|launchctl|ps|lsof|git|ssh|python3|node)\b"
    r"|\.(?:py|sh|js|json|md|plist|db|log|yml|yaml)\b|\*\.[a-z0-9]{2,5}\b|--limit|--maxdepth|-maxdepth",
    re.IGNORECASE,
)


def flatten(obj, out, prefix=""):
    """v2.5.0：path 保留**祖先路径**（老登实测：丢祖先会惩罚结构化写法——嵌套/数组声明观测面被判「没写」）。
       path 语义 = 祖先键名以 . 连接 + 叶子键名；无键名（数组元素/顶层标量）时沿用父路径。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, str):
                out.append((p, v))
            elif isinstance(v, (dict, list)):
                flatten(v, out, p)
            else:
                out.append((p, str(v)))
    elif isinstance(obj, list):
        for v in obj:
            if isinstance(v, str):
                out.append((prefix, v))
            else:
                flatten(v, out, prefix)
    else:
        out.append((prefix, str(obj)))


def strip_false_friends(text):
    t = text
    for ff in FALSE_FRIENDS:
        t = t.replace(ff, " ")
    return t


def is_negated_mention(text, start):
    seg = text[max(0, start - 3):start]
    return any(seg.endswith(n) for n in NEGATED_BEFORE)


def find_claims(pairs, patterns, guards):
    hits = []
    for path, text in pairs:
        if guards and META_FIELD_RE.search(path or ""):
            continue
        t = strip_false_friends(text or "")
        t = EXEMPT_NEAR_CHECK.sub(" ", t)     # v3.2.0 ②：「无X + 检查动词」豁免
        for pat in patterns:
            for m in re.finditer(pat, t):
                if guards and is_negated_mention(t, m.start()):
                    continue
                s = max(0, m.start() - 40)
                hits.append({"field": path, "claim": pat, "snippet": t[s:m.end() + 40].strip()})
    return hits


def find_scope(pairs):
    field_hits, token_hits = [], []
    for path, text in pairs:
        if SCOPE_FIELD_RE.search(path or ""):
            field_hits.append(path)
        t = text or ""
        m = SCOPE_TOKEN_RE.search(t) or CHECK_VERB_RE.search(t)
        if m:
            token_hits.append({"field": path, "sample": m.group(0)})
    return field_hits, token_hits


def has_quotation(pairs):
    for _, text in pairs:
        if text and QUOTATION_RE.search(text):
            return True
    return False


VOID_STATUS = {"void", "superseded", "tombstone", "retracted"}


def void_kind(card):
    """区分三类卡（明鉴 2026-09-14 指出的必须分开）：

    · **`tombstone`（墓碑）**：**曾存在、已作废**（它**有过实体**）—— 例：老登的「保留作墓碑、不删，
      避免引用方拿 404」
    · **`stub`（占位）**：**尚未有实体、占位待填**（`status: stub` / `type: topic-stub`）
    · **`active`**：正常卡

    ★ 为什么必须分开：她指出 **3a/3b/3c 的区分恰好需要「曾存在」这一位** ——
      3a「曾存在后被换/删」与 3c「从未存在」判别的唯一线索就是它 ⇒ 若两者共用同一谓词，**该信息会丢**。
    """
    if not isinstance(card, dict):
        return "active"
    st = str(card.get("status", "")).strip().lower()
    ty = str(card.get("type", "")).strip().lower()
    blob = json.dumps(card, ensure_ascii=False)[:400]
    if st == "stub" or ty == "topic-stub":
        return "stub"
    if st in VOID_STATUS or "墓碑" in blob or "已作废" in blob[:200]:
        return "tombstone"
    return "active"


def is_void_card(card):
    """作废卡/墓碑卡不适用新规则：不追溯已声明作废的对象（邻接原则的推论）。

    ⚠ 本谓词是 **tombstone ∪ stub** 的并（对 lint 而言两者都不判），
      **要区分两者须用 `void_kind()`**（明鉴 2026-09-14）。
    """
    return void_kind(card) in ("tombstone", "stub")


def is_blockable(r):
    """可阻断域 = 无引用特征 ∩ 🔴 fail（HR 2026-09-14 裁定）。warn 永不阻断。"""
    return r["verdict"] == "fail" and not r.get("scope", {}).get("quoted", False)


def exit_code(results, severity="advisory", exit_on="blocking"):
    """退出码契约（v2.2.0）：
       severity=advisory（默认）⇒ 永不非零（只报告，不阻断）
       severity=blocking        ⇒ 非零 当且仅当「可阻断域」非空
       exit_on=any（显式选用）  ⇒ 非零 当且仅当存在 fail/warn（供分诊，不等于阻断）
    """
    if exit_on == "any":
        return 1 if any(r["verdict"] in ("fail", "warn") for r in results) else 0
    if severity == "blocking":
        return 1 if any(is_blockable(r) for r in results) else 0
    return 0


def lint_card(card, coverage="v1.2", quotation_cap=True):
    cfg = COVERAGE[coverage]
    pairs = []
    flatten(card, pairs)
    claims = find_claims(pairs, cfg["patterns"], cfg["guards"])
    field_hits, token_hits = find_scope(pairs)
    quoted = has_quotation(pairs)
    scope = {"fields": field_hits, "tokens": len(token_hits), "quoted": quoted}
    # ★ v3.9.0：类别守卫 —— 只有**计数量主语**的 0 才按「零值断言」处理；
    #   状态码/位置/比率三类**语义不同**，不按计数零值告警（老登 2026-09-14 实测假阳性三类）。
    zero_raw = [(pth, t) for pth, t in pairs if ZERO_RE.search(t or "")]
    zero_claims, zero_skipped, zero_unclassified = [], [], []
    for pth, t in zero_raw:
        cls = zero_subject_class(t)
        if cls == "count":
            zero_claims.append({"field": pth, "claim": "零值断言", "subject_class": cls, "snippet": (t or "")[:80]})
        elif cls in ("status_code", "position", "ratio"):
            zero_skipped.append({"field": pth, "subject_class": cls, "snippet": (t or "")[:80]})
        else:
            # ★ 未判类别 ⇒ **保持旧行为（告警）**，即「只豁免已命名的非计数类别」。
            #   理由：豁免表是**封闭集**（status_code/position/ratio），表外保持原判 ⇒ 变更最小；
            #   否则「得 0」这类**真语料负例**会从 warn 掉成 pass（我实测已发生一次，FN）。
            zero_unclassified.append({"field": pth, "snippet": (t or "")[:80]})
            zero_claims.append({"field": pth, "claim": "零值断言", "subject_class": "unclassified", "snippet": (t or "")[:80]})
    if zero_claims and not any(CONTROL_RE.search(t or "") for _, t in pairs):
        return {"verdict": "warn",
                "reason": "零值断言缺「已知非零对照」（老登 2026-09-14 判据：无对照的 0 降格为「命令未证实有效」）",
                "claims": claims + zero_claims, "scope": scope, "coverage": coverage,
                "zero_skipped": zero_skipped, "zero_unclassified": zero_unclassified}
    if zero_skipped or zero_unclassified:
        scope = dict(scope)
        scope["zero_skipped_classes"] = [x["subject_class"] for x in zero_skipped]
        scope["zero_unclassified"] = len(zero_unclassified)
    if not claims:
        return {"verdict": "pass", "reason": "无否定性结论", "claims": [], "scope": scope, "coverage": coverage}
    if field_hits and not quoted:
        # v2.5.0：排除项判定须同时看**键名与值**——「未查」常写在键名上（观测面:{已查:…,未查:…}）
        scope_text = " ".join(f"{pth} {t}" for pth, t in pairs if SCOPE_FIELD_RE.search(pth or ""))
        if not EXCLUSION_RE.search(scope_text):
            return {"verdict": "warn", "reason": "观测面只列含项、缺排除项（老登 2026-09-14 判据：最小完整形态=含项+排除项+工具+计数单位+时刻）", "claims": claims, "scope": scope, "coverage": coverage}
        return {"verdict": "pass", "reason": f"否性结论附显式观测面（含排除项）{field_hits}", "claims": claims, "scope": scope, "coverage": coverage}
    if quoted and quotation_cap:
        return {"verdict": "warn", "reason": "含引用/转述特征 ⇒ 结构性不阻断（HR 2026-09-14 裁定）", "claims": claims, "scope": scope, "coverage": coverage}
    if token_hits:
        return {"verdict": "warn", "reason": f"有观测面痕迹但无显式声明字段（{len(token_hits)} 处，不可复核）", "claims": claims, "scope": scope, "coverage": coverage}
    return {"verdict": "fail", "reason": "否定性结论无任何观测面声明 ⇒ 应降格为「在我所查范围内未发现」", "claims": claims, "scope": scope, "coverage": coverage}


def corpus_fingerprint(items):
    """语料指纹：绑定信息的一部分。同一指纹 = 格内可比；不同指纹 = 格间不可比。"""
    h = hashlib.sha256()
    for k, v in sorted(items, key=lambda x: x[0]):
        h.update(k.encode())
        h.update(json.dumps(v, ensure_ascii=False, sort_keys=True).encode())
    return h.hexdigest()[:16]


# v3.4.0（明鉴 2026-09-14 复核出的假阴性）：只哈希**函数源码**会漏掉**被这些函数读取的模块级常量**
#   ⇒ 改常量（如删一个判定词、改一条正则）判定变了而 id 不动 ⇒ 被判「可比」= 假阴性。
#   故 id 同时纳入以下常量：正则取 .pattern、集合/序列排序后 join、dict 排序 items。
DECISION_CONSTS = [
    "CLAIM_V10", "CLAIM_V11_ADD", "COVERAGE", "FALSE_FRIENDS",
    "META_FIELD_RE", "NEGATED_BEFORE", "CHECK_VERB_RE", "EXEMPT_NEAR_CHECK",
    "QUOTATION_RE", "SCOPE_FIELD_RE", "SCOPE_TOKEN_RE", "ZERO_RE", "CONTROL_RE",
    "EXCLUSION_RE", "VOID_STATUS",
    # v3.13.0：由本工具自己的「名单完备性守门」抓出 —— ZERO_SUBJECT_CLASSES 影响判定
    #   （status_code/position/ratio ⇒ 不抓；count ⇒ 抓；unclassified ⇒ 不豁免），
    #   却既不在 DECISION_CONSTS 也不在 EXCLUDE_CONSTS ⇒ **改它 id 不动 = 假阴性**。
    "ZERO_SUBJECT_CLASSES",
]


def _const_repr(g, name):
    v = g.get(name)
    if v is None:
        return f"{name}=<absent>"
    if hasattr(v, "pattern"):
        return f"{name}={v.pattern}"
    if isinstance(v, dict):
        return f"{name}=" + ";".join(f"{k}:{_const_repr({'x': w}, 'x')}" for k, w in sorted(v.items(), key=lambda kv: str(kv[0])))
    if isinstance(v, (set, frozenset)):
        return f"{name}=" + ",".join(sorted(map(str, v)))
    if isinstance(v, (list, tuple)):
        return f"{name}=" + ",".join(map(str, v))
    return f"{name}={v}"


DECISION_FUNCS = ["flatten", "strip_false_friends", "is_negated_mention", "find_claims",
                  "find_scope", "has_quotation", "is_blockable", "exit_code", "lint_card", "is_void_card"]


def _walk_decision_ctx(node, mode="text", out=None):
    """收集字符串常量并标出它处于哪一种上下文：`dec`（判定）/ `key`（字段名）/ `text`（反馈文案）。

    ★ 三态是必要的（实测教训）：第一版只有 dec/text 两态，把比较子树的**全部后代**当判定上下文
    ⇒ `card.get("verdict") == "fail"` 里的 `"verdict"`（字典**键**）被误报成判定字面量：
    实测 15 处「违规」里有 6 处其实是字段名 ⇒ 误报率 40%。字段名与判定词性质不同（前者改动
    属结构变更、后者属判据变更），故单独一档。

    判定上下文 = if/while/ifexp 的条件 · 比较 · 布尔运算 · 一元 not · 断言 · `re.*` 的实参。
    已知漏报方向（显式声明）：`text.startswith("x")` 这类**非 re** 的字符串方法实参不标记
    ⇒ 对上它们是漏报（哨兵宁少响不恒响，故保守）。"""
    if out is None:
        out = []
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        out.append((node.value, node, mode))
    elif isinstance(node, (ast.If, ast.While)):
        _walk_decision_ctx(node.test, "dec", out)
        for c in list(getattr(node, "body", []) or []) + list(getattr(node, "orelse", []) or []):
            _walk_decision_ctx(c, mode, out)
        return out
    elif isinstance(node, ast.IfExp):
        # ★ 坑（实测）：IfExp 的 .body/.orelse 是**表达式**不是语句列表 ⇒
        #   与 If/While 合并处理会 TypeError；而 skeleton_audit 里当时是 `except: continue`
        #   ⇒ **静默少审了 2/10 个函数**（正是今晚反复抓的「手段失败 ⇒ 读成跑过且无结果」）。
        _walk_decision_ctx(node.test, "dec", out)
        _walk_decision_ctx(node.body, mode, out)
        _walk_decision_ctx(node.orelse, mode, out)
        return out
    elif isinstance(node, (ast.Compare, ast.BoolOp, ast.UnaryOp, ast.Assert)):
        for c in ast.iter_child_nodes(node):
            _walk_decision_ctx(c, "dec", out)
        return out
    elif isinstance(node, ast.Call):
        f = node.func
        attr = f.attr if isinstance(f, ast.Attribute) else ""
        base = f.value.id if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) else ""
        for a in node.args:
            if attr == "get" and isinstance(a, ast.Constant) and isinstance(a.value, str):
                out.append((a.value, a, "key"))
            else:
                _walk_decision_ctx(a, "dec" if base == "re" else "text", out)
        for kw in getattr(node, "keywords", []) or []:
            if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                out.append((kw.value.value, kw.value, "key"))
            else:
                _walk_decision_ctx(kw.value, "text", out)
        return out
    elif isinstance(node, ast.Subscript):
        _walk_decision_ctx(node.value, mode, out)
        _walk_decision_ctx(node.slice, "key", out)
        return out
    else:
        for c in ast.iter_child_nodes(node):
            _walk_decision_ctx(c, mode, out)
    return out


def _skeleton(fn_or_src):
    """AST 骨架（v3.13.0）：把函数体里【所有字符串常量】替换为空串，保留数字与结构。
    返回 (骨架文本, 被剥掉的字符串字面量清单)。

    为什么弃用正则（v3.12.0 及以前）：顺序 5 条正则（# 注释 → 三引号 → 双引号 → 单引号）
    在含 f-string / 嵌套引号 / 含 `#` 的字符串上会【失同步】——实测 `lint_card` 的骨架里
    **残留 178 个引号字符** ⇒ 「剥掉字符串」这个承诺只兑现了一部分：一部分反馈文案仍在
    参与 id。AST 天然不含注释、字符串常量定位精确 ⇒ 无失同步。
    ★ 判据要写准：剥净的判据不是「骨架里没有引号」（`ast.unparse` 会把占位渲染成 `''`，必然有引号），
    而是**原始字符串内容不残留**——我第一版就是拿「残留引号=0」当判据，结果是我的判据错、代码是对的。
    残余风险（**收窄**，采纳明鉴 2026-09-14 ②）：被剥的是【字符串】字面量，**数字不剥**
    ⇒ 改函数体内一个数字仍会改 id（selftest 有对照）；故规则应写成
    「判定用的【字符串】字面量一律放模块级常量」。
    另：骨架由 `ast.unparse` 产出，故 id 含 Python 版本分量（见 decision_rule_id）。"""
    src = fn_or_src if isinstance(fn_or_src, str) else inspect.getsource(fn_or_src)
    try:
        node = ast.parse(textwrap.dedent(src)).body[0]
    except Exception:
        return re.sub(r"\s+", " ", src), []
    stripped = [v for v, _n, _d in _walk_decision_ctx(node) if v.strip()]
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            n.value = ""
    try:
        return re.sub(r"\s+", " ", ast.unparse(node)), stripped
    except Exception:
        return re.sub(r"\s+", " ", src), stripped


def skeleton_audit():
    """明鉴 2026-09-14 ★★★：把「剥掉了什么」暴露出来 ⇒ 约定变机制。
    ★ 我与她原判据的差别：她建议「剥出非空清单 ⇒ 报警」。实测 DECISION_FUNCS 体内共
    **104 个**字符串字面量，其中绝大多数是反馈文案/输出标记 ⇒ 「非空即报警」会**恒响**，
    哨兵就失效了（今晚已记：恒响的哨兵等于没有哨兵）。
    故收窄为：**只在【判定上下文】里出现字符串字面量才报警**；反馈用字符串只计数、列出供人核。
    返回 {"violations": [...], "field_keys": [...], "counts": {fn: (全部, 判定上下文)},
          "errors": {...}, "audited": n, "expected": m, "total_strings": N}。
    ★ `field_keys` 单列的必要性（实测）：第一版把比较子树全部后代当判定上下文 ⇒
    `card.get("verdict") == "fail"` 的**字典键** `"verdict"` 被误报 ⇒ 15 处「违规」里 6 处是字段名
    ⇒ 误报率 40%。字段名改动属结构变更、判定词改动属判据变更，性质不同，故分档不合并。"""
    g = globals()
    viol, fieldkeys, counts, errors = [], [], {}, {}
    for name in DECISION_FUNCS:
        fn = g.get(name)
        if fn is None:
            errors[name] = "函数不存在"
            continue
        try:
            node = ast.parse(textwrap.dedent(inspect.getsource(fn))).body[0]
            found = _walk_decision_ctx(node)
        except Exception as exc:                      # noqa: BLE001
            # ★ 不静默跳过：本检查自己踩过这个坑（IfExp 分支 TypeError ⇒ 静默少审 2/10 个函数）。
            #   手段失败必须与「审了且无违规」可区分，否则就是今晚那个形态的复制品。
            errors[name] = f"{type(exc).__name__}: {exc}"
            continue
        allc = [v for v, _n, _m in found if v.strip()]
        dec = [(v, getattr(n, "lineno", 0)) for v, n, m in found if m == "dec" and v.strip()]
        keys = [(v, getattr(n, "lineno", 0)) for v, n, m in found if m == "key" and v.strip()]
        counts[name] = (len(allc), len(dec))
        for v, ln in dec:
            viol.append({"fn": name, "literal": v[:60], "line": ln})
        for v, ln in keys:
            fieldkeys.append({"fn": name, "literal": v[:60], "line": ln})
    return {"violations": viol, "field_keys": fieldkeys, "counts": counts, "errors": errors,
            "audited": len(counts), "expected": len(DECISION_FUNCS),
            "total_strings": sum(c[0] for c in counts.values())}


EXCLUDE_CONSTS = {"VERSION", "DEFAULT_BB", "HASH_LEN", "PAIRS", "SELFTEST", "EXIT_SELFTEST",
                  "DECISION_FUNCS", "DECISION_CONSTS", "EXCLUDE_CONSTS", "CLAIM_PATTERNS",
                  "_skeleton", "_walk_decision_ctx", "re", "os", "sys", "json", "argparse",
                  "hashlib", "inspect", "ast", "textwrap",
                  "time", "tempfile", "urllib", "plistlib", "collections", "Counter",
                  # 文本条款：仅用于输出声明，**不参与判定**（故排除出 decision_rule_id）
                  "WARN_NEVER_BLOCKS_CLAUSE",
                  # 分层真实样本（selftest 用）：样本字面量，不影响判定
                  "LAYERED_SAMPLES"}


def source_id(path=None):
    # 整文件 sha256（明鉴 2026-09-14）：零假阴性（任何字节改动都变），代价是假阳性
    p = path or os.path.abspath(__file__)
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:12]


def uncovered_constants():
    # 名单完备性守门（明鉴 2026-09-14）：模块级 ALL_CAPS 赋值若既不在 DECISION_CONSTS
    # 也不在显式排除清单里 ⇒ 可能属于「判定相关但未被覆盖」⇒ 出声提醒（不阻断）。
    g = globals()
    out = []
    for name, val in list(g.items()):
        if not re.match(r"^[A-Z][A-Z0-9_]+$", name):
            continue
        if name in EXCLUDE_CONSTS or name in DECISION_CONSTS:
            continue
        if isinstance(val, (str, int, float, list, tuple, set, frozenset, dict)) or hasattr(val, "pattern"):
            out.append(name)
    return sorted(out)


def comparability(source_unchanged, decision_unchanged):
    # 四象限判定（明鉴 2026-09-14）：source_id 与 decision_rule_id 并列使用
    if source_unchanged and decision_unchanged:
        return "完全未改 ⇒ 可比 ✅"
    if not source_unchanged and not decision_unchanged:
        return "名单内判定已改 ⇒ 不可比 ✅"
    if not source_unchanged and decision_unchanged:
        return "⚠️ 待人工判一次（装饰改动 ⇒ 可比 / 名单外判定改动 ⇒ 不可比）；默认按不可比"
    return "❌ 实现异常（source 未变而判定 id 变）⇒ 应报错"


def decision_rule_id():
    """判定规则标识（采纳明鉴 2026-09-14）：对**决定判定的函数源文本**取哈希。
       ⇒ 装饰性改动（打印/注释/格式）不改 id；判定逻辑一改 id 必变。
       ⇒ 判定句因此可机器判：id 不同 ⇒ 不可比（须重注/重跑），不依赖人对「这版改没改逻辑」的自我判断。"""
    g = globals()
    h = hashlib.sha256()
    # 骨架由 ast.unparse 产出 ⇒ 输出随 Python 版本规范化 ⇒ id 必须带 Python 分量，
    # 否则「同一份源码在两个 Python 上跑出两个 id」会被误判成判定逻辑改动。
    h.update(f"py={sys.version_info[0]}.{sys.version_info[1]};skeleton=ast-v1".encode("utf-8"))
    for name in DECISION_FUNCS:
        fn = g.get(name)
        if fn is None:
            continue
        try:
            skel, _ = _skeleton(fn)
            h.update(skel.encode("utf-8"))
        except Exception:
            h.update(name.encode())
    for name in DECISION_CONSTS:
        h.update(_const_repr(g, name).encode("utf-8"))
    return h.hexdigest()[:12]


def binding(coverage, quotation_cap, items):
    """绑定块（v2.4.0，采纳明鉴的两组拆分）：
       【对象组】= 测的是谁/哪一部分 + 变换 ⇒ 指纹不同 = 不可比，必须重测
       【观测组】= 工具/单位/口径/时刻      ⇒ 仅这些不同 = 可比，只需补标注
    """
    import datetime
    return {
        "object": {
            "corpus_fingerprint": corpus_fingerprint(items) if items else None,
        },
        "observation": {
            "unit": "张（卡计数）",
            "tool_version": VERSION,
            "decision_rule_id": decision_rule_id(),
            "source_id": source_id(),          # 整文件 sha256：零假阴性，与 decision_rule_id 并列
            "input_cards": len(items),      # 原始量：输入集（含作废卡）
            "void_cards": None,             # 原始量：作废卡数（运行时填）
            # judged_cards = input_cards − void_cards：**派生量，运行时算出后具名输出**。
            # ★ 明鉴 2026-09-14：我 v3.x 只给两个数分了名，**第三个数仍以「扫描 N 张」的无名形式**
            #   出现在输出行 ⇒ **同名两物只修了一半**（冲突源之一是无名数）。
            # ⇒ 修法：派生量**不另存**（避免两份对不上），但**必须以同一个名字出现在输出里**。
            "judged_cards": None,           # 派生量：运行时填 = input_cards − void_cards
            "coverage": coverage,
            "quotation_cap": quotation_cap,
            "ts": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"),
        },
    }


# ── 取卡 ────────────────────────────────────────────────────────────────
def load_file(path):
    with open(os.path.expanduser(path), encoding="utf-8", errors="replace") as f:
        return json.load(f)


def load_dir(path):
    out = []
    d = os.path.expanduser(path)
    for name in sorted(os.listdir(d)):
        if name.endswith(".json"):
            try:
                out.append((name[:-5].replace("__", "/"), load_file(os.path.join(d, name))))
            except Exception as e:  # noqa: BLE001
                out.append((name, {"_read_error": str(e)}))
    return out


def load_ns(ns, base, limit):
    lst = json.load(urllib.request.urlopen(f"{base}/{ns}/", timeout=10))
    keys = lst.get("list") or []
    if isinstance(keys, dict):
        keys = list(keys)
    keys = sorted(keys)
    if limit:
        keys = keys[:limit]
    out = []
    for k in keys:
        try:
            d = json.load(urllib.request.urlopen(f"{base}/{k}", timeout=10))
            out.append((k, d.get("value", d)))
        except Exception as e:  # noqa: BLE001
            out.append((k, {"_read_error": str(e)}))
    return out


def ns_is_valid(ns):
    """命名空间合法性（纯函数，可离线 selftest）。

    ★ 明鉴 2026-09-14：非法 ns 时本工具曾**静默审 0 张**并输出「不一致 = 0 张」
      ⇒「干净」与「什么都没审」**同形**（空通过族的新实例）。⇒ 把合法性抽成纯函数，
      使其可被正反例覆盖。
    规则（黑板 key 语法）：**首段必须为纯小写字母 `[a-z]+`**；后续段自由（连字符/数字允许）。
    """
    import re as _re2
    if not ns or not isinstance(ns, str):
        return False
    return bool(_re2.fullmatch(r"[a-z]+", ns.split("/")[0]))


def do_snapshot(ns, base, outdir, limit=0):
    """冻结同库快照：键名 → 文件名（/ → __），供多代判据重放。"""
    items = load_ns(ns, base, limit)
    od = os.path.expanduser(outdir)
    os.makedirs(od, exist_ok=True)
    for k, v in items:
        with open(os.path.join(od, k.replace("/", "__") + ".json"), "w", encoding="utf-8") as f:
            json.dump(v, f, ensure_ascii=False)
    print(f"快照 {len(items)} 张 → {od}")
    return 0


# ── selftest ────────────────────────────────────────────────────────────
SELFTEST = [
    ("正例：否性结论+观测面字段（含排除项）", {"观测面": "grep -rl app-Qys ~/dsh-collab；未查 ~/.dsh 全量", "结论": "该键未扩散"}, "pass"),
    ("反例：观测面只列含项（缺排除项）", {"观测面": "grep -rl app-Qys ~/dsh-collab", "结论": "该键未扩散"}, "warn"),
    ("反例：否性结论无观测面", {"结论": "该键从未扩散", "影响": "无任何调用点"}, "fail"),
    ("反例：只有零散命令痕迹", {"结论": "该服务未加载", "备注": "我用 launchctl 看了一眼"}, "warn"),
    ("假阳性守卫：不存在性", {"结论": "这是不存在性问题", "detail": "x"}, "pass"),
    ("假阳性守卫：无人值守", {"结论": "该任务无人值守", "detail": "x"}, "pass"),
    ("正例：无否性结论", {"结论": "备份已恢复，integrity ok", "范围": "本机"}, "pass"),
    ("假阳性守卫：未发现异常", {"结论": "巡检未发现异常", "detail": "x"}, "pass"),
    ("反例：否性结论在嵌套字段", {"f": {"deep": {"v": "实现未提供该能力"}}}, "fail"),
    ("新覆盖：全部不在…", {"结论": "16 项守护全部不在运行"}, "fail"),
    ("新覆盖：无消费者", {"结论": "失败记录无消费者"}, "fail"),
    ("新覆盖：尚未/未见", {"结论": "该键尚未被写入"}, "fail"),
    ("假阳性守卫：不在少数", {"结论": "这类情况不在少数", "detail": "x"}, "pass"),
    ("假阳性守卫：否定修饰（非空壳）", {"结论": "这是非空壳键"}, "pass"),
    ("假阳性守卫：否定修饰（不是空壳）", {"结论": "它不是空壳键"}, "pass"),
    ("假阳性守卫：元语言字段（规则）", {"规则": "含否定性结论须带观测面，如 不存在/未提供/从未"}, "pass"),
    ("正例：真否性结论仍需命中", {"结论": "该实现并不存在调用点"}, "fail"),
    ("裸 0+邻近守卫（得 0）⇒ warn", {"结论": "搜 Dify 卷，得 0"}, "warn"),
    ("裸 0+邻近守卫（命中数为 0）⇒ warn", {"结论": "该串命中数为 0"}, "warn"),
    ("真语料负例 127.0.0.1 ⇒ 不触发", {"命令": "curl 127.0.0.1:8792/clock"}, "pass"),
    ("真语料负例 v2.0.0 ⇒ 不触发", {"版本": "v2.0.0"}, "pass"),
    ("真语料负例 20260914 ⇒ 不触发", {"日期": "20260914"}, "pass"),
    ("真语料负例 0/380 ⇒ 不触发", {"结论": "该比值 0/380"}, "pass"),
    ("零值断言·无对照 ⇒ warn", {"结论": "该串在 transcript 中出现 0 行"}, "warn"),
    ("零值断言·有对照 ⇒ 不因本条告警", {"结论": "该串 0 行；已知非零对照：另一串 38 行"}, "pass"),
    ("形状A 顶层观测面+字符串", {"观测面": "查了 ~/dsh-collab；未查其它目录", "结论": "该键未扩散"}, "pass"),
    ("形状B 顶层观测面+嵌套dict", {"观测面": {"已查": "~/dsh-collab", "未查": "其它设备"}, "结论": "该键未扩散"}, "pass"),
    ("形状C 顶层观测面+数组", {"观测面": ["~/dsh-collab 已查", "其它设备未查"], "结论": "该键未扩散"}, "pass"),
    ("形状D 嵌套叶子键名=范围", {"证据": {"范围": "查了 ~/dsh-collab；未查其它设备"}, "结论": "该键未扩散"}, "pass"),
    ("形状E 顶层范围+dict", {"范围": {"查了": "~/dsh-collab", "未查": "其它设备"}, "结论": "该键未扩散"}, "pass"),
    ("形状F 顶层范围+字符串", {"范围": "查了 ~/dsh-collab；未查其它设备", "结论": "该键未扩散"}, "pass"),
    ("形状D' 有形状但缺排除项 ⇒ 仍 warn", {"证据": {"范围": "查了 ~/dsh-collab"}, "结论": "该键未扩散"}, "warn"),
    ("引用特征：引用他人 ⇒ 封顶 warn", {"结论": "老登说该实现未提供能力"}, "warn"),
    ("引用特征：撤回语境 ⇒ 封顶 warn", {"结论": "该键已被撤回，其从未接线判断作废"}, "warn"),
]


EXIT_SELFTEST = [
    ("advisory：warn 不阻断", [{"verdict": "warn", "scope": {}}], "advisory", "blocking", 0),
    ("advisory：fail 也不阻断", [{"verdict": "fail", "scope": {}}], "advisory", "blocking", 0),
    ("blocking：可阻断域非空", [{"verdict": "fail", "scope": {"quoted": False}}], "blocking", "blocking", 1),
    ("blocking：引用类 fail 不算", [{"verdict": "fail", "scope": {"quoted": True}}, {"verdict": "warn", "scope": {}}], "blocking", "blocking", 0),
    ("blocking：仅 warn", [{"verdict": "warn", "scope": {}}], "blocking", "blocking", 0),
    ("exit-on=any：仅 warn 也非零", [{"verdict": "warn", "scope": {}}], "advisory", "any", 1),
]


def selftest(coverage="v1.2"):
    ok = 0
    for name, rs, sev, eo, want in EXIT_SELFTEST:
        got = exit_code(rs, sev, eo)
        m = "✅" if got == want else "❌"
        if got == want:
            ok += 1
        print(f"{m} [退出码] {name}: expect={want} got={got}")
    print()
    for name, card, expect in SELFTEST:
        got = lint_card(card, coverage)["verdict"]
        mark = "✅" if got == expect else "❌"
        if got == expect:
            ok += 1
        print(f"{mark} {name}: expect={expect} got={got}")
    total = len(SELFTEST) + len(EXIT_SELFTEST)
    # ── 命名空间合法性（真语料正反例：黑板 key 语法）──
    for name, v, want in [
        ("正例·`data` / `notes` / `tasks`（纯小写字母）⇒ 合法", "data", True),
        ("正例·`data/registry`（首段合法即可，后续段自由）⇒ 合法", "data/registry", True),
        ("反例·★`mac-mini`（真语料：明鉴复现空通过的取值）⇒ 非法", "mac-mini", False),
        ("反例·`i9`（含数字）⇒ 非法", "i9", False),
        ("反例·`foo_bar`（含下划线）⇒ 非法", "foo_bar", False),
        ("反例·`ABC`（大写）⇒ 非法", "ABC", False),
        ("反例·空字符串 ⇒ 非法", "", False)]:
        total += 1
        got = ns_is_valid(v)
        ok += 1 if got == want else 0
        print(f"  {'✅' if got == want else '❌'} {name}: got={got} 期望={want}")
    # ── 分层真实样本（老登 2026-09-14：真实样本须按「违规明显度」分层，否则只证明了最明显那层）──
    layered = [
        ("明显·否定结论 + 零观测面", {"结论": "接口确实不存在"}, "fail"),
        ("中等·否定 + 零值断言无对照", {"结论": "该串在日志中未发现"}, "fail"),
        ("隐晦·间接表述（「均已清理/未见残留」）", {"结论": "本轮排查后，相关调用点均已清理，未见残留"}, "fail"),
        ("★已知漏检·更隐晦（「已确认它不会生效」）—— 本用例**钉住当前漏检**，将来若抓到会变红以示需要一次有意的改动",
         {"结论": "无需再关注该路径：已确认它不会生效"}, "pass"),
        ("合规·有观测面", {"结论": "接口确实不存在", "观测面": "含项：全仓 grep 该符号（12 文件命中）· 排除项：未查 node_modules"}, "pass"),
    ]
    for name, card, want in layered:
        total += 1
        r = lint_card(card, coverage=coverage)
        got = r.get("verdict") if isinstance(r, dict) else str(r)
        good = got == want
        ok += 1 if good else 0
        print(f"  {'✅' if good else '❌'} {name}: got={got} 期望={want}")
    # ── 零值守卫·**按分支覆盖**（老登 2026-09-14 ⑤：负例集须按守卫的每个分支各配 ≥1 例）──
    branch_cases = [
        ("分支 status_code·中文形态 `退出码为 0` ⇒ pass（**成功语义**，不是零值缺口）",
         {"结论": "该命令退出码为 0，全链通过。"}, "pass"),
        ("分支 status_code·英文形态 `exit = 0` ⇒ pass（**与中文形态同判** ⇒ 修掉写法敏感）",
         {"结论": "exit = 0 ⇒ 脚本成功。"}, "pass"),
        ("分支 position·`数组下标为 0` ⇒ pass（位置语义）",
         {"结论": "数组下标为 0 的元素即默认项。"}, "pass"),
        ("分支 ratio·`该渠道占比为 0` ⇒ pass（比率语义，转比率族）",
         {"结论": "该渠道占比为 0，本日无成交。"}, "pass"),
        ("分支 count·`命中数为 0` ⇒ **warn**（计数零值，须非零对照）",
         {"结论": "全仓命中数为 0"}, "warn"),
        ("分支 unclassified·`得 0`（主语未命名）⇒ **保持旧行为 warn**（豁免表是封闭集，表外不豁免）",
         {"结论": "搜 Dify 卷，得 0"}, "warn"),
    ]
    for name, card, want in branch_cases:
        total += 1
        r = lint_card(card, coverage=coverage)
        got = r.get("verdict") if isinstance(r, dict) else str(r)
        ok += 1 if got == want else 0
        print(f"  {'✅' if got == want else '❌'} {name}: got={got} 期望={want}")
    # ── 墓碑 vs 占位（明鉴 2026-09-14：共用谓词会丢「曾存在」这一位）──
    kind_cases = [
        ("反例·墓碑卡（曾存在·已作废）⇒ tombstone（**有过实体**）",
         {"status": "void", "note": "保留作墓碑（不删，避免引用方拿到 404）"}, "tombstone"),
        ("反例·占位卡（尚未有实体）⇒ stub（**无实体**）",
         {"status": "stub", "type": "topic-stub", "note": "占位卡：供收敛表归属行引用"}, "stub"),
        ("正例·正常卡 ⇒ active", {"结论": "正常卡", "观测面": "含项：x"}, "active"),
        ("反例·**两者必须可分**：同为「不判」，但 void_kind 不同",
         {"status": "stub"}, "stub"),
    ]
    for name, card, want in kind_cases:
        total += 1
        got = void_kind(card)
        ok += 1 if got == want else 0
        print(f"  {'✅' if got == want else '❌'} {name}: got={got} 期望={want}")
    total += 1
    good = is_void_card({"status": "stub"}) and is_void_card({"status": "void"}) and not is_void_card({"结论": "x"})
    ok += 1 if good else 0
    print(f"  {'✅' if good else '❌'} 正例·`is_void_card` 保持并集语义（stub ∨ tombstone 均不判），兼容旧调用: {good}")
    # ── 骨架剥离（v3.13.0）：AST 剥离彻底性 + 数字不剥 + 判定上下文分类器 ──
    _sk, _stripped = _skeleton("def f(x):\n    return re.match('a#b', x) or (x == \"cc\")\n")
    total += 1
    # 判据改为「原内容不残留」：ast.unparse 会把空串渲染成 '' ⇒ 残留引号本身是**正常**的，
    # 我曾把「残留引号=0」当判据 ⇒ 是我的判据错，不是代码错（第 N 次：判据须对着性质写）。
    _ok = ("a#b" not in _sk) and ("cc" not in _sk)
    ok += 1 if _ok else 0
    print(f"  {'✅' if _ok else '❌'} 骨架·含 `#` 与嵌套引号的字符串内容不残留（正则版会在此失同步）: skeleton={_sk[:60]!r}")
    total += 1
    _ok = len(_stripped) == 2
    ok += 1 if _ok else 0
    print(f"  {'✅' if _ok else '❌'} 骨架·剥出清单条数=2（`a#b` 与 `cc`）: got={_stripped}")
    total += 1
    _ok = "1" in _skeleton("def f(x):\n    return x[1:] + 1\n")[0]
    ok += 1 if _ok else 0
    print(f"  {'✅' if _ok else '❌'} 骨架·**数字不剥**（改函数体内数字仍会改 id，故规则只收窄到字符串）: {_ok}")
    # ★ 这里原有 `total += 1` + 一行 `_ok = ... if False else ...` 的死代码：
    #   它**在计数里充数但不打印任何判据** ⇒ 分母 71、输出只有 70 条 ✅、无 ❌
    #   ⇒ 「少了一条判据」表现成「分母虚高」而非红灯。已删除（空检查比没有更坏）。
    _aud = skeleton_audit()
    # 判定上下文分类器：正例（if 条件里的字符串）与负例（print 里的字符串）必须分开
    _n = ast.parse('def f(x, msg):\n    print("反馈文案")\n    if x == "VOID":\n        return 1\n    return msg.split(",")[0]\n').body[0]
    _found = _walk_decision_ctx(_n)
    # ★ 三态改造后这里必须比 `== "dec"`：第一版仍写 `if _d` ⇒ 字符串 "text" 为真
    #   ⇒ **三个字面量全被判成判定上下文**，测试红了而代码是对的（判据随字段语义变更未同步更新）。
    _dec = [v for v, _nn, _d in _found if _d == "dec" and v.strip()]
    _all = [v for v, _nn, _d in _found if v.strip()]
    total += 1
    ok += 1 if _dec == ["VOID"] else 0
    print(f"  {'✅' if _dec == ['VOID'] else '❌'} 骨架守门·判定上下文只认出 `VOID`（print 文案与 split 实参不算）: got={_dec}")
    total += 1
    ok += 1 if "反馈文案" in _all and "反馈文案" not in _dec else 0
    print(f"  {'✅' if ('反馈文案' in _all and '反馈文案' not in _dec) else '❌'} 骨架守门·**负例**：反馈文案只计数、不报警（明鉴原判据「非空即报警」会恒响）")
    _n2 = ast.parse('def f(card):\n    if card.get("verdict") == "fail":\n        return 1\n').body[0]
    _f2 = _walk_decision_ctx(_n2)
    _dec2 = [v for v, _n, _m in _f2 if _m == "dec" and v.strip()]
    _key2 = [v for v, _n, _m in _f2 if _m == "key" and v.strip()]
    total += 1
    ok += 1 if (_dec2 == ["fail"] and _key2 == ["verdict"]) else 0
    print(f"  {'✅' if (_dec2 == ['fail'] and _key2 == ['verdict']) else '❌'} 骨架守门·**负例**：`card.get(\"verdict\") == \"fail\"` 的**字典键不算判定字面量**（第一版误报，15 处违规里 6 处是键）: dec={_dec2} key={_key2}")
    total += 1
    _ok = (isinstance(_aud["counts"], dict) and all(len(v) == 2 for v in _aud["counts"].values())
           and _aud["audited"] == _aud["expected"] and not _aud["errors"])
    ok += 1 if _ok else 0
    print(f"  {'✅' if _ok else '❌'} 骨架守门·**覆盖面守恒**：审了 {_aud['audited']}/{_aud['expected']} 个 DECISION_FUNCS、异常 {_aud['errors']}"
          f"（这不是形式检查：本检查第一版正因 `except: continue` 静默少审 2/10）")
    print(f"\nselftest {ok}/{total} (coverage={coverage})")
    return 0 if ok == total else 1


def _snapshot_hint():
    """本版是否已有冻结快照。★ 没有快照时，「两个 id 不同 ⇒ 时点差」这个结论**只能靠 mtime 推断、
    不能复核**（除非有一方保留了当时那份文件）⇒ 报读数时应连快照路径一起报。"""
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".snapshots")
    try:
        hits = sorted(f for f in os.listdir(d) if f.startswith(VERSION + "--"))
    except Exception:                                # noqa: BLE001
        return "无 .snapshots 目录"
    if not hits:
        return f"未冻结（运行 --archive 可得 {VERSION}--<sha12>.py）"
    # ★★ 两个坑，都踩过：
    #   ① 快照名的 sha12 是**冻结那一刻**的 source_id ⇒ 必须与当前 source_id 比对，
    #      否则「有快照」会被读成「就是这一版的快照」（自指指纹过期）。
    #   ② 取「最后一个」不能按文件名排序 —— 我第一次就是 `hits[-1]`，于是在刚冻结出
    #      6fcbacf5baac 之后仍然显示旧的 7c31aa2c4030（字典序恰好更大）⇒ **排序键选错**。
    #      正确做法：先找与当前 source_id 一致的那个；找不到再按 mtime 取最新。
    cur = source_id()
    match = [f for f in hits if f.rsplit("--", 1)[-1].replace(".py", "") == cur]
    if match:
        return os.path.join(d, match[0]) + "（✅ 与当前 source_id 一致）"
    last = max(hits, key=lambda f: os.path.getmtime(os.path.join(d, f)))
    tag = last.rsplit("--", 1)[-1].replace(".py", "")
    return os.path.join(d, last) + f"（⚠ 是编辑前的快照：名 {tag} ≠ 当前 {cur} ⇒ 复现须重新 --archive）"


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--file")
    ap.add_argument("--dir")
    ap.add_argument("--ns")
    ap.add_argument("--bb", default=DEFAULT_BB)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--coverage", default="v1.2", choices=sorted(COVERAGE))
    ap.add_argument("--quotation-cap", default="on", choices=["on", "off"], help="引用特征封顶为 warn（结构性排除）[分母=已读 {fetched} 张]")
    ap.add_argument("--snapshot", action="store_true", help="把 --ns 的库冻结到 --dir 供重放")
    ap.add_argument("--json-out")
    ap.add_argument("--archive", action="store_true",
                    help="把当前源文件按 <version>--<sha12>.py 存进 .snapshots/（供他人独立验证「某次改动前后」）")
    ap.add_argument("--severity", default="advisory", choices=["advisory", "blocking"],
                    help="advisory=只报告（退出码恒 0）；blocking=可阻断域非空则退出码 1")
    ap.add_argument("--exit-on", default="blocking", choices=["blocking", "any"],
                    help="blocking=按可阻断域；any=任一 fail/warn 即非零（分诊用，不等于阻断）[分母=已读 {fetched} 张]")
    ap.add_argument("--ts-audit", action="store_true",
                    help="审计卡内 ts 字段与信封 ts 是否一致（命名面双源，HR 2026-09-14）[分母=已读 {fetched} 张]")
    ap.add_argument("--skeleton-audit", action="store_true",
                    help="列出 DECISION_FUNCS 内被 _skeleton 剥掉的字符串字面量，并报出处于【判定上下文】的违规（明鉴 2026-09-14 ③：把剥离结果暴露出来 ⇒ 约定变机制）")
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    args = ap.parse_args()

    if args.version:
        import datetime as datetime_mod              # noqa: N806
        import hashlib as _h
        try:
            _sha = _h.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()[:16]
        except Exception:
            _sha = None
        import datetime as _dtv
        # 明鉴 2026-09-14：「四项配套、同一时刻」⇒ 接收方才能判「是不是同一版」。
        # ★ 我补第五、六项的理由：**排除四象限④（实现异常）需要「同文件」的证据** ——
        #   只看 source_id 不同，无法区分「文件变了」与「实现坏了」；mtime+size 是那份证据。
        try:
            _st = os.stat(os.path.abspath(__file__))
            _mt = datetime_mod.datetime.fromtimestamp(_st.st_mtime).strftime("%Y-%m-%dT%H:%M:%S")
            _sz = _st.st_size
        except Exception:                            # noqa: BLE001
            _mt, _sz = None, None
        print(json.dumps({"tool": "absence-claim-lint", "version": VERSION,
                          "file_sha256": _sha,           # 明鉴 2026-09-14：报版本须带文件级标识
                          "file_mtime": _mt, "file_size": _sz,   # 排除④的「同文件」证据
                          "snapshot": _snapshot_hint(),          # 该版是否已冻结快照（否则「时点差」只能推断）
                          "reported_at": _dtv.datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"),
                          # 明鉴 2026-09-14 ①：报 id 必须与「版本 + 时刻」同时出现，
                          # 否则读者会拿两个不同版本的 id 相比（她实测我报 3.5.0/9b9c…，
                          # 而当时已是 3.7.0/a12f… ⇒ 两处「漂移」实为时点差）。
                          "decision_rule_id": decision_rule_id(),
                          "source_id": source_id(),
                          "py": f"{sys.version_info[0]}.{sys.version_info[1]}",   # 骨架含 py 分量
                          "rule": "否定性结论须附观测面声明（条件必填）",
                          "coverage": args.coverage}, ensure_ascii=False))
        return 0
    if args.archive:
        import shutil as _sh
        d = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".snapshots")
        os.makedirs(d, exist_ok=True)
        dst = os.path.join(d, f"{VERSION}--{source_id()[:12]}.py")
        _sh.copyfile(os.path.abspath(__file__), dst)
        print(f"快照 → {dst}")
        print("  用途（明鉴 2026-09-14）：**她无旧版快照 ⇒ 只能判「成立」不能判「验证」**；"
              "有快照后可对 version/decision_rule_id/source_id 逐项比对。")
        return 0
    if args.selftest:
        return selftest(args.coverage)
    if args.snapshot:
        if not (args.ns and args.dir):
            print("--snapshot 需要 --ns 与 --dir", file=sys.stderr)
            return 2
        return do_snapshot(args.ns, args.bb, args.dir, args.limit)

    if args.skeleton_audit:
        a = skeleton_audit()
        print(f"骨架审计（明鉴 2026-09-14 ③：把剥离结果暴露出来 ⇒ 约定变机制）")
        print(f"  覆盖面：审 {a['audited']}/{a['expected']} 个 DECISION_FUNCS · 异常 {a['errors'] or '无'}"
              f" · 体内字符串字面量 {a['total_strings']} 个（全部已被 _skeleton 剥掉、不参与 id）")
        for fn, (allc, dec) in sorted(a["counts"].items()):
            print(f"    {fn:<20} 字符串 {allc:>3} · 其中处于判定上下文 {dec:>3}")
        print(f"  另：字典**字段名**字面量 {len(a['field_keys'])} 个（不算违规，单列供人核）："
              + " · ".join(f"{v['fn']}:{v['literal']}" for v in a["field_keys"][:8]) if a["field_keys"] else "  另：字典字段名字面量 0 个")
        if a["violations"]:
            print(f"  ⚠ 判定上下文中出现字符串字面量 {len(a['violations'])} 处 ⇒ 应移入模块级常量（否则 id 会漏掉该变化）：")
            for v in a["violations"]:
                print(f"      {v['fn']}:{v['line']} {v['literal']!r}")
        else:
            print("  ✅ 无：约定「判定用的【字符串】字面量一律放模块级常量」已被机械核验（此前只在注释里声明）")
        if a["errors"]:
            print(f"  ❌ 有函数未被审计（手段失败，不等于无违规）：{a['errors']}")
            return 2
        return 0

    if args.ts_audit:
        import datetime as _dt, re as _re
        ns = args.ns or "data/registry"
        # ★★ v3.8.0（明鉴 2026-09-14 两处指正）：
        #   ① **非法命名空间**（黑板 key 语法：首段必须纯小写字母 `[a-z]+`）⇒ 之前静默审 0 张、
        #      输出「不一致 = 0 张」，读起来像「没有不一致」⇒ **「干净」与「什么都没审」同形**。
        #   ② **声明的范围必须等于实际覆盖的对象**：默认 ns 是 `data/registry`，而我此前把它
        #      标成「全库」⇒ 读者会以为是全网比例（绝对量差 18 倍：444 vs notes 14166）。
        if not ns_is_valid(ns):
            print(f"【ns-invalid】命名空间「{ns}」**非法**：黑板 key 语法要求首段为纯小写字母 `[a-z]+`"
                  f"（如 `data`/`notes`/`tasks`；含连字符或数字即非法）[分母=已读 {fetched} 张]")
            print("⇒ **本次审了 0 张** ⇒ 这**不是**「没有不一致」，而是**什么都没审**（空通过的同一形态）。")
            print("⇒ 请改用合法命名空间（可多段，如 `data/registry`）。")
            return 4
        try:
            lst = json.load(urllib.request.urlopen(f"{args.bb}/{ns}/", timeout=20))
        except Exception as e:
            print(f"【ns-unreachable】命名空间「{ns}」列举失败：{str(e)[:80]} ⇒ **审了 0 张，不是「干净」**")
            return 4
        keys = list(lst.get("list", {}) if isinstance(lst.get("list"), dict) else lst.get("list", []))
        if args.limit:
            keys = keys[: args.limit]
        print(f"【范围】namespace = **{ns}**"
              f"{'（默认值；**不是全库**，全库须显式跨命名空间）' if not args.ns else ''} · 待审 {len(keys)} 张")
        if not keys:
            print("【zero-scope】该命名空间列举为空 ⇒ **审了 0 张** ⇒ 下面的「不一致 = 0」**不得读作干净**")
            return 4
        bad = early = late = 0
        fetched = 0
        failed = []
        for k in keys:
            try:
                env = json.load(urllib.request.urlopen(f"{args.bb}/{k}", timeout=15))
                fetched += 1
            except Exception as e:
                failed.append((k, type(e).__name__))
                continue
            v = env.get("value", {})
            if not isinstance(v, dict):
                continue
            inner = v.get("ts_machine") or v.get("ts")
            if not inner:
                continue
            def norm(x):
                m = _re.search(r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2})", str(x))
                return m.group(1).replace(" ", "T") if m else None
            a, b = norm(inner), norm(env.get("ts"))
            if a and b and a != b:
                bad += 1
                # v3.3.0（HR 2026-09-14）：先定口径再判 —
                #   卡内 ts 口径 = **作者声明的内容时点**（origin）；信封 ts = 写入时点。
                #   ⇒ 早于信封 = 内容陈旧但**合法**；**晚于信封 = 不可能**（真缺陷，与明鉴「未来时点」同族）。
                early += 1 if a < b else 0
                late += 1 if a > b else 0
                print(f"[TS-{'LATE' if a>b else 'EARLY'}] {k} :: 卡内={a} 信封={b}")
        # ★ v3.8.1：**分母必须是「成功读取数」，不是「列举数」** —— 否则读取失败会被静默跳过，
        #   而汇总仍拿列举数当分母（我 19:04 那次就报出「分母 161」而列举实为 584 ⇒ 同族缺陷第三例）。
        if fetched < len(keys):
            print(f"\n【partial】列举 {len(keys)} 张 · **成功读取 {fetched} 张 · 失败 {len(keys) - fetched} 张** "
                  f"⇒ **下列比率的分母 = {fetched}（已读数），不是 {len(keys)}（列举数）**")
            from collections import Counter as _C
            print("   失败类型分布：" + " · ".join(f"{k}={v}" for k, v in _C(t for _, t in failed).items()))
        print(f"\n审计 {len(keys)} 张（**已读 {fetched} 张**）· 卡内 ts ≠ 信封 ts = {bad} 张"
              f"（早于={early} 张【内容时点声明，合法】· **晚于={late} 张【不可能的时点 ⇒ 真缺陷】**）[分母=已读 {fetched} 张]")
        print("口径（HR 2026-09-14）：卡内 ts = 作者声明的内容时点（origin）；信封 ts = 写入时点 ⇒ 先定口径再判，"
              "不得把「早于」一律当错误。")
        return 1 if bad else 0

    if args.file:
        items = [(args.file, load_file(args.file))]
    elif args.dir:
        items = load_dir(args.dir)
    elif args.ns:
        items = load_ns(args.ns, args.bb, args.limit)
    else:
        ap.print_help()
        return 2

    BIND = binding(args.coverage, args.quotation_cap == "on", items)
    results, voids = [], []
    for k, c in items:
        if is_void_card(c):
            voids.append(k)
            continue
        results.append({"key": k, **lint_card(c, args.coverage, args.quotation_cap == "on")})
    bad = [r for r in results if r["verdict"] in ("fail", "warn")]
    blockable = [r for r in results if is_blockable(r)]
    for r in bad:
        print(f"[{r['verdict'].upper()}] {r['key']} — {r['reason']}")
        for c in r["claims"][:3]:
            print(f"    · {c['claim']}: {c['snippet'][:90]}")
    n = lambda v: sum(1 for r in results if r["verdict"] == v)  # noqa: E731
    # v2.6.0：比率**自绑定**（采纳明鉴 L3 判据：分子与分母须同一次运行、同一快照、同一口径，
    #   跨口径拼接出的数在任何单一口径下都不成立 ⇒ 故把 num/den/口径/快照指纹**同结构产出**）
    judged = len(results)
    claim_cards = [r for r in results if r["claims"]]
    with_field = [r for r in results if r["scope"]["fields"]]
    with_field_in_claims = [r for r in claim_cards if r["scope"]["fields"]]
    fp = BIND["object"]["corpus_fingerprint"]
    _scope_ns = (args.ns or "data/registry")   # ★ 口径里的范围必须显式（明鉴 2026-09-14）
    RATIOS = {
        "field_adoption_all_library": {"num": len(with_field), "den": judged, "unit": "张（卡）", "den_kind": "judged",
                                       "caliber": f"input_scope={_scope_ns}", "corpus_fingerprint": fp, "run_ts": BIND["observation"]["ts"]},
        "field_adoption_claim_bearing": {"num": len(with_field_in_claims), "den": len(claim_cards), "unit": "张（卡）", "den_kind": "judged",
                                         "caliber": "有主张卡口径", "corpus_fingerprint": fp, "run_ts": BIND["observation"]["ts"]},
        "blockable_share": {"num": len(blockable), "den": judged, "unit": "张（卡）", "den_kind": "judged",
                            "caliber": "可阻断域占判卡", "corpus_fingerprint": fp, "run_ts": BIND["observation"]["ts"]},
    }
    print("【条款】" + WARN_NEVER_BLOCKS_CLAUSE)
    print("比率（自绑定：分子/分母/口径/快照指纹/运行时刻同源产出）[分母=已读 {fetched} 张]")
    for k, r in RATIOS.items():
        pct = (r["num"] / r["den"] * 100) if r["den"] else 0.0
        print(f"  {k} = {r['num']}/{r['den']} = {pct:.1f}%  [{r['caliber']} · snap={r['corpus_fingerprint']} · ts={r['run_ts']}]")
    BIND["observation"]["void_cards"] = len(voids)
    BIND["observation"]["judged_cards"] = len(items) - len(voids)   # 派生量：具名输出，与「扫描 N 张」同源
    print("绑定[对象]：" + " · ".join(f"{k}={v}" for k, v in BIND["object"].items())
          + " ｜ 绑定[观测]：" + " · ".join(f"{k}={v}" for k, v in BIND["observation"].items()))
    unc = uncovered_constants()
    if unc:
        print(f"⚠ 名单完备性守门：模块级常量未纳入 id 且未排除 = {unc} ⇒ 若其中之一影响判定，decision_rule_id 会漏（请加进 DECISION_CONSTS 或 EXCLUDE_CONSTS）")
    _aud = skeleton_audit()
    print(f"骨架守门（v3.13.0）：审 {_aud['audited']}/{_aud['expected']} 个 DECISION_FUNCS"
          + (f" ❌异常={_aud['errors']}" if _aud["errors"] else "")
          + f" · 体内字符串字面量 {_aud['total_strings']} 个（已剥、不参与 id）"
          f" · 处于【判定上下文】的 {len(_aud['violations'])} 个 ⇒ "
          + ("**应移入模块级常量**：" + " · ".join(f"{v['fn']}:{v['literal']}" for v in _aud["violations"][:5])
             if _aud["violations"] else "✅ 无（约定已被机械核验）"))
    print("可比性判定（明鉴 2026-09-14）：对象组任一不同 ⇒ **不可比（须重测）**；")
    print("判定逻辑两读数（并列，不替代）：source_id=" + str(BIND["observation"].get("source_id"))
          + " · decision_rule_id=" + str(BIND["observation"].get("decision_rule_id")))
    print("四象限：①source 同 & decision 同 ⇒ 可比；②source 变 & decision 变 ⇒ 不可比；"
          "③**source 变 & decision 同 ⇒ 待人工判一次**（装饰⇒可比 / 名单外判定改动⇒不可比）；"
          "④source 同 & decision 变 ⇒ 实现异常，应报错")
    if voids:
        print(f"\n作废卡/墓碑卡 {len(voids)} 张（不判、不计入阻断域）：" + " · ".join(v.split("/")[-1][:34] for v in voids[:6]))
    print(f"\n可阻断域 = {len(blockable)} 张（无引用特征 ∩ fail）；本行数不随 severity 变化")
    print(f"退出码契约：severity={args.severity} · exit-on={args.exit_on} ⇒ 本次退出码 = "
          f"{exit_code(results, args.severity, args.exit_on)}")
    _judged = len(items) - len(voids)
    print(f"\n判卡 judged_cards={_judged}（= input_cards {len(items)} − void_cards {len(voids)}）"
          f" · coverage={args.coverage} · pass={n('pass')} · warn={n('warn')} · fail={n('fail')}")
    print("   ⇒ 上一行是**同一个数**：绑定块里的 `judged_cards` 与这里的判卡数**同名同源**（明鉴 2026-09-14：数须具名，否则同名两物只修一半）")
    print("⚠ 上界声明：fail/warn 为**上界**（不区分自述与引用——v2.0.0 起引用特征已结构性降为 warn）；"
          "pass 为**上界**（关键词覆盖未证明完备）。⇒ 本版默认 advisory，**不得据此阻断**。")
    print("ℹ 条件必填：含否定性结论的卡须带「观测面」字段；纯肯定/纯记录卡不要求（HR 裁定）。")
    print("ℹ 可阻断域（若升阻断）：无引用特征 ∩ 🔴 fail；🟡 warn 一律不阻断（结构性排除）。")
    if args.sample:
        print(f"\n=== 供人工标注的前 {args.sample} 张非 pass 卡（真值请人工判） ===")
        for r in bad[: args.sample]:
            c = r["claims"][0] if r["claims"] else {"claim": "-", "snippet": ""}
            print(f"{r['verdict']:5} | {r['key']}\n       主张={c['claim']} 摘要={c['snippet'][:80]}")
    if args.json_out:
        with open(os.path.expanduser(args.json_out), "w", encoding="utf-8") as f:
            json.dump({"version": VERSION, "binding": BIND, "scanned": len(results), "ratios": RATIOS, "results": results},
                      f, ensure_ascii=False, indent=1)
        print(f"json → {args.json_out}")
    return exit_code(results, args.severity, args.exit_on)


if __name__ == "__main__":
    sys.exit(main())
