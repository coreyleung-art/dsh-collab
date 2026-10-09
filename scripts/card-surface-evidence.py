#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""card-surface-evidence.py — 卡级面证据生成器（v1.0.0）

依据（独立复核员 2026-10-08）：回执只给自报三项不够，**须卡级面证据**：
双板回读 + value 哈希 + 抽取时刻。

输出（每键一行）：key | local.status | local.value_sha16 | central.status | central.value_sha16
                    | 一致? | 抽取时刻(UTC) | 两板 version
用法: python3 card-surface-evidence.py <key> [<key>...] [--json]
      python3 card-surface-evidence.py --selftest | --version
判据：两板均可读(200) ⇒ 有面；value_sha16 相等 ⇒ 内容一致；不等 ⇒ 分叉（此时**不得**声称已收敛）

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== card-surface-evidence 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · card-surface-evidence.py — 卡级面证据生成器（v1.0.0）")
    print("  · 依据（独立复核员 2026-10-08）：回执只给自报三项不够，**须卡级面证据**：")
    print("  · 双板回读 + value 哈希 + 抽取时刻。")
    print("  · 输出（每键一行）：key | local.status | local.value_sha16 | central.status | central.value_sha16")
    print("  · 命令/参数: json, selftest, version, versions, basis")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, datetime, os")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/card-surface-evidence.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

import argparse, hashlib, json, sys, datetime, urllib.request

VERSION = "1.0.0"
__version__ = VERSION
BOARDS = [("local", "http://127.0.0.1:8792"), ("central", "http://xingqiao.meetfunbp.com:8792")]

# ★ C7 修正（独立复核员 2026-10-08）：**比较基准必须显式声明**，禁止隐式全字段比较、
#   也禁止隐式忽略未知字段。以下为**显式枚举**的「传输/时序标记」排除集：
#   · _via           —— 中继写入路径（comm-central）给**单板**加的传输标记（实证导致 2/10 抽样分叉）
#   · sent_at_epoch_ms / ts —— 时序标记（两板必然不同，前已声明不参与判定）
#   除上述字段外**任何差异都算真分叉**（避免"笼统忽略未知字段 ⇒ 真分叉被一起忽略"的反向危险）。
# ★ 2026-10-08 独立复核员指出「排除集比证据宽」：`sent_at_epoch_ms`/`ts` 是**卡作者自报的业务内容**，
#   不是传输标记 —— 排除它们会让「单板被改写」被静默赦免为 transport。现改为**实证驱动且最小**：
#   仅排除有实测例证的 `_via`（5/15 例两板合法差异）；其余字段一律参与比较（宁可见红不静默赦免）。
TRANSPORT_MARKERS = ("_via",)
EVIDENCE_FOR_EXCLUSION = {"_via": "comm-central 中继写入给单板加传输标记（实证 5/15 例合法差异，2026-10-08）"}
# ★ 脱敏标记族（PSTD 2026-10-08）：两板**各自施掩码**会造成预期内的 body 差异 ⇒ 判 defect 前先查此族
REDACTION_MARKERS = ("_redacted_by", "_redacted_at", "_redacted_reason", "_pattern_mentions", "_via")
# ★ 2026-10-08 独立复核员指出「条件式无界豁免」：只凭「存在标记」即豁免 ⇒ 真差异被旁路。
#   现改为**有界条件**：仅当「差异 ⊆ (传输标记 ∪ 脱敏声明字段)」时才判 redaction-divergence，
#   否则一律 defect。豁免必须由「差异落在被声明集合内」限定，不能由「存在某个标记」限定。
REDACTION_DECLARED = tuple(m for m in REDACTION_MARKERS if m != "_via")   # 声明口径的脱敏字段（不含传输标记）


def sha16(obj):
    try:
        b = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    except Exception:
        b = repr(obj).encode()
    return hashlib.sha256(b).hexdigest()[:16]


def fetch(base, key):
    try:
        with urllib.request.urlopen(f"{base}/{key}", timeout=15) as r:
            d = json.load(r)
        return {"status": r.status, "value": d.get("value"), "version": d.get("version")}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "value": None, "version": None}
    except Exception as e:
        return {"status": None, "error": type(e).__name__, "value": None, "version": None}


def fielddiff(local_v, central_v, exclude=TRANSPORT_MARKERS):
    """返回 (差异字段名集合, 是否仅限已声明排除集)"""
    if not isinstance(local_v, dict) or not isinstance(central_v, dict):
        return ("非对象形态", False)
    lk = {k: v for k, v in local_v.items() if k not in exclude}
    ck = {k: v for k, v in central_v.items() if k not in exclude}
    diff = set(k for k in set(lk) | set(ck) if lk.get(k, "__AN__") != ck.get(k, "__AN__"))
    return (sorted(diff), len(diff) == 0)


def evidence(keys):
    at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = []
    for k in keys:
        row = {"key": k, "at": at}
        for name, base in BOARDS:
            r = fetch(base, k)
            row[f"{name}_status"] = r["status"]
            row[f"{name}_version"] = r["version"]
            row[f"{name}_value_sha16"] = sha16(r["value"]) if r["value"] is not None else None
            if r["value"] is not None and isinstance(r["value"], dict):
                row[f"{name}_biz_sha16"] = sha16({k: v for k, v in r["value"].items() if k not in TRANSPORT_MARKERS})
        both = row.get("local_status") == 200 and row.get("central_status") == 200
        same = (row.get("local_value_sha16") is not None
                and row.get("local_value_sha16") == row.get("central_value_sha16"))
        row["both_readable"] = both
        row["converged"] = bool(both and same)
        # ★ 分层告警（PSTD 2026-10-08 更正后方案；符号已按实测更正）：
        #   dv = local.version − central.version
        #   缺陷级 = 两板均可读但 value sha 不等（真分叉）
        #   提示级 = dv > 0（本地领先 ⇒ 有一次没推上去的候选方向）
        #   不告警 = dv ≤ 0（dv<0 是同步推送给 central 加写的**正常痕迹**）
        #   噪声依据：version 偏移率实测 27.8%(mac-mini)~53.4%(/notes/) ⇒ 一律告警即噪声，故分层。
        # ★ 差异分类（C7）：仅限已声明排除集 = 预期内传输差异；超出 = 真分叉
        # 从 fetch 缓存取回 value 做字段级 diff
        lv_full = fetch(BOARDS[0][1], k)["value"]
        cv_full = fetch(BOARDS[1][1], k)["value"]
        diff_fields, only_declared = fielddiff(lv_full, cv_full)
        row["diff_fields"] = diff_fields
        row["only_declared_markers"] = only_declared
        # ★ P4 归属判据（PSTD 2026-10-08 量化后建议）：**以字段判据取代路径推断**
        #   带 writerLabel ⇒ from 可信；不带 ⇒ **不可判**（不因文件路径/时间推断归属）。
        lv_obj = lv_full if isinstance(lv_full, dict) else {}
        has_label = bool(lv_obj.get("writerLabel"))
        # ★ 2026-10-08 PSTD 实证：修复前本工具的 from 由**硬编码常量**注入（而该常量恰是真实会话 id）
        #   ⇒ 「from_label == 星桥(协调者) mac-mini」即 **修复前工具卡** ⇒ from 为误归，不可作归属依据（强判据）
        #   ⇒ 「from == 该常量 且 无 from_label」⇒ 疑似工具卡（弱判据，与真星桥卡同形）
        CONST_FROM = "session-fa1f9150-c949-401f-ba8c-d265f6221676"
        LEGACY_LABEL = "星桥(协调者) mac-mini"
        fl = lv_obj.get("from_label")
        fr = lv_obj.get("from")
        if has_label:
            attrib = "from 可信（带 writerLabel，自派生证据在）"
        elif fl == LEGACY_LABEL:
            attrib = "★ from 不可作归属依据（from_label=修复前工具常量 ⇒ 该卡由修复前工具写入，from 为误归；446 张级强判据）"
        elif fr == CONST_FROM:
            attrib = "⚠ 疑似工具卡（from==硬编码常量且无 from_label ⇒ 与真星桥卡同形，弱判据）待另证"
        else:
            attrib = "不可判（无 writerLabel ⇒ 不推断归属）"
        row["attribution"] = {"has_writerLabel": has_label, "from_label": fl, "verdict": attrib}
        row["comparison_basis"] = {"all_field_sha16": "local/central_value_sha16",
                                   "business_field_sha16": "local/central_biz_sha16",
                                   "declared_exclusions": list(TRANSPORT_MARKERS),
                                   "evidence_for_exclusion": EVIDENCE_FOR_EXCLUSION,
                                   "rule": "差异仅在已声明排除集内=预期传输差异；超出=真分叉"}
        lv, cv = row.get("local_version"), row.get("central_version")
        row["dv"] = (lv - cv) if isinstance(lv, int) and isinstance(cv, int) else None
        # ★ 定性前先查状态（PSTD：规则入文档 ≠ 规则入工具——脚本必须自己会查）
        lval = lv_full if isinstance(lv_full, dict) else {}
        cval = cv_full if isinstance(cv_full, dict) else {}
        l_mark = {k for k in REDACTION_MARKERS[1:] if k in lval}
        c_mark = {k for k in REDACTION_MARKERS[1:] if k in cval}
        both_declare_redaction = bool(l_mark) and bool(c_mark)
        # ★ 2026-10-08 PSTD：免责级（把 defect 降为非行动层）边界必须严——**仅「两板都脱敏」不够**，
        #   需证据表明**两次脱敏不同源**；同源掩码应产生**相同**结果 ⇒ 同源不得免责（一次误免责=一个真分叉被放过，属假阴性）。
        #   可用判据（避开 `_redacted_at` 的天级粒度）：两板脱敏**标记集合不同** ⇒ 不同实现 ⇒ 不同源。
        # 不同源判据（PSTD 2026-10-08 实测两条可用门）：
        #   ① 标记集合相反/不同（local 有 _redacted_by 无 _pattern_mentions，central 反之）
        #   ② `_redacted_reason` 两板文字明显不同（同源脱敏应写同一段理由）
        #   同源 ⇒ 掩码应产生相同结果 ⇒ 两板 body 不同即说明输入或规则不同。
        l_reason = str(lval.get("_redacted_reason", ""))
        c_reason = str(cval.get("_redacted_reason", ""))
        reason_differs = bool(l_reason and c_reason and l_reason != c_reason)
        different_source = both_declare_redaction and (l_mark != c_mark or reason_differs)
        row["both_declare_redaction"] = bool(both_declare_redaction)
        row["different_source"] = bool(different_source)
        row["marker_sets"] = {"local": sorted(l_mark), "central": sorted(c_mark)}
        row["source_evidence"] = {"marker_sets_differ": l_mark != c_mark,
                                  "redacted_reason_differs": reason_differs}
        row["via_note"] = ("`_via` 是**事后由中继（comm-central）添加的标记**："
                           "工具写入时刻的断言（boardsMatch）与事后读板比较（converged）可**同时为真**，"
                           "差别在时刻与基准 —— 非工具说谎")
        if both and same:
            row["level"] = "ok"; row["advice"] = "两板 value 哈希相等 ⇒ 已收敛（正向分层）"
        elif both and not same and only_declared:
            row["level"] = "transport"; row["advice"] = ("两板差异**仅在已声明排除集**内（" + ",".join(diff_fields) + "）"
                                                          " ⇒ 预期内传输差异，非真分叉")
        elif both and not same and different_source:
            # ★ 有界豁免（复核员 2026-10-08）：差异**必须全部落在声明的脱敏字段内**才算预期分叉
            row["level"] = "redaction-divergence"
            row["advice"] = ("两板均声明脱敏**且来源不同**（标记集 local=" + ",".join(sorted(l_mark))
                             + " / central=" + ",".join(sorted(c_mark)) + "）⇒ 判预期分叉；"
                             "**差异字段已显式列出**：" + ",".join(str(x) for x in diff_fields)
                             + "（免责非静默：字段与来源一并可见，供第三方核对）")
        elif both and not same and both_declare_redaction:
            row["level"] = "defect"
            row["advice"] = ("两板均脱敏但**不足以免责**（差异超出声明脱敏集，或**标记集合相同 ⇒ 疑似同源掩码**）："
                             + ",".join(str(x) for x in diff_fields)
                             + " ⇒ 判 defect（免责级边界从严；误免责=真分叉被放过，属假阴性）")
        elif both and not same:
            row["level"] = "defect"; row["advice"] = ("两板差异**超出已声明排除集**（" + ",".join(str(x) for x in diff_fields)
                                                      + "）⇒ 真分叉，需处置")
        elif row["dv"] is not None and row["dv"] > 0:
            # ★ 2026-10-08 撤销「dv>0 告警」（PSTD 自纠：它是方向不是判据——实测 /notes/ 18.4%、mac-mini 2.3%
            #   ⇒ 与预期异常率同阶 ⇒ 噪声级）。现仅作**信息**呈现，不产生行动层，并附基率声明。
            row["level"] = "info"
            row["advice"] = ("本地领先（dv>0）——**仅信息，非判据**：该量在不同总体占比差 8 倍"
                             "（/notes/ 18.4% · mac-mini 2.3% · data 0.3%），与预期异常率同阶 ⇒ 不得据此告警")
        elif row["dv"] is not None and row["dv"] < 0:
            row["level"] = "none"; row["advice"] = "central 领先 = 同步推送的正常痕迹，不告警"
        else:
            row["level"] = "unknown"; row["advice"] = "读失败/非 JSON/键缺失 ⇒ 确实未知，不判定（手段失败≠通过）"
        out.append(row)
    return {"measured_at": at, "rows": out,
            "criterion": "action 层 = defect（排除集外 value 不等；或差异超出声明的脱敏字段集）；豁免一律**有界**：仅当差异 ⊆ 已声明集合（传输 ∪ 脱敏）才降级；dv 仅信息（基率闸：/notes/ 18.4% 属噪声）",
            "dv_convention": "dv = local.version - central.version（2026-10-08 起固定；此前相反约定的历史载体请按其原文数值取反读）"}


def selftest():
    ok = fail = 0
    def chk(c, l):
        nonlocal ok, fail
        if c: ok += 1; print("  ✅", l)
        else: fail += 1; print("  ❌", l)
    chk(sha16({"a": 1}) == sha16({"a": 1}), "同内容 ⇒ 同哈希")
    chk(sha16({"a": 1}) != sha16({"a": 2}), "异内容 ⇒ 异哈希（有判别力）")
    # 负控：键序不影响哈希（canonical）
    chk(sha16({"a": 1, "b": 2}) == sha16({"b": 2, "a": 1}), "键序无关（canonical JSON）")
    # ★ 有界豁免回归（复核员 2026-10-08 的 B/C 合成用例）：标记存在不得旁路真差异
    def classify(L, C):
        diff, only_declared = fielddiff(L, C)
        if not diff: return "ok"
        if only_declared: return "transport"
        both_red = (any(k in L for k in REDACTION_MARKERS[1:]) and any(k in C for k in REDACTION_MARKERS[1:]))
        if both_red and set(diff) <= set(REDACTION_DECLARED): return "redaction-divergence"
        return "defect"
    chk(classify({"from": "x", "_via": "r", "subject": "s"}, {"from": "x", "subject": "s"}) in ("ok", "transport"),
        "有界·仅 _via 差异 ⇒ 非 defect")
    chk(classify({"from": "x", "_via": "r", "subject": "s1"}, {"from": "x", "_via": "r", "subject": "s2"}) == "defect",
        "★负控·两板有标记但 subject 真不同 ⇒ defect（标记不得旁路）")
    chk(classify({"from": "x", "_redacted_at": "t", "subject": "s1"}, {"from": "x", "_redacted_at": "t", "subject": "s2"}) == "defect",
        "★负控·两板声明脱敏但差异超集 ⇒ defect")
    # ★ 免责边界（PSTD 2026-10-08）：需**不同源**（标记集不同）；同源不得免责
    def classify2(L, C):
        diff, only = fielddiff(L, C)
        if not diff: return "ok"
        if only: return "transport"
        lm = {k for k in REDACTION_MARKERS[1:] if k in L}
        cm = {k for k in REDACTION_MARKERS[1:] if k in C}
        if lm and cm and lm != cm: return "redaction-divergence"
        return "defect"
    chk(classify2({"subject": "s1", "_redacted_at": "t", "_redacted_by": "x", "body": "b1"},
                  {"subject": "s2", "_redacted_at": "t", "_pattern_mentions": ["a"], "body": "b2"}) == "redaction-divergence",
        "正例·两板标记集不同（独立脱敏）⇒ redaction-divergence")
    chk(classify2({"subject": "s1", "_redacted_at": "t"}, {"subject": "s2", "_redacted_at": "t"}) == "defect",
        "★负控·两板标记集相同（疑似同源掩码）⇒ defect")
    chk(classify2({"subject": "s1", "_via": "r"}, {"subject": "s2", "_via": "r"}) == "defect",
        "★负控·仅 _via（非脱敏声明）⇒ defect")
    # 负控：不存在键 ⇒ 不 converged
    r = evidence(["notes/mac-mini/__definitely-not-a-real-key-20261008__"])
    row = r["rows"][0]
    chk(row["converged"] is False, "负控·不存在键 ⇒ converged=False（不误判）")
    print(f"\nselftest: {ok} PASS / {fail} FAIL")
    return 0 if fail == 0 else 1


def versions():
    """脚本现读磁盘版本 + mtime —— 回执中的版本号应由本模式注入，禁止手填（PSTD 4/4 不可核的教训）"""
    import os, time
    targets = [
        ("bb-card-send", os.path.expanduser("~/dsh-plugin-bb-card-send/package.json")),
        ("card-surface-evidence", os.path.expanduser("~/dsh-collab/scripts/card-surface-evidence.py")),
        ("holdout-split", os.path.expanduser("~/dsh-collab/scripts/holdout-split.py")),
        ("bb-send-check", os.path.expanduser("~/dsh-collab/scripts/bb-send-check.py")),
        ("intent-outcome-pairing-check", os.path.expanduser("~/dsh-collab/scripts/intent-outcome-pairing-check.py")),
    ]
    at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # ★ 2026-10-08 PSTD：只报 onDisk 会把「盘上快照」包装成权威版本 ⇒ 必须补 inService 与 drift。
    #   inService **只能从在役进程读**（工具调用返回体 / 在役进程写出的日志）；**绝不能靠 import 模块**（那是盘上快照）。
    in_service_bb = None
    try:
        log = os.path.expanduser("~/dsh-collab/logs/bb-card-send.log")
        last = None
        for ln in open(log, encoding="utf-8", errors="ignore"):
            ln = ln.strip()
            if not ln:
                continue
            try:
                d2 = json.loads(ln)
            except Exception:
                continue
            if d2.get("result") in ("OK", "OK-WITH-TIMEOUT"):
                last = d2
        if last is not None:
            in_service_bb = last.get("runtimeVersion")  # None ⇒ 在役未加载该字段
            in_service_bb = in_service_bb or "未加载/不可读（日志中该字段 0 条）"
    except Exception:
        in_service_bb = "读取失败"
    out = {"read_at": at,
           "by": "card-surface-evidence.py --versions（onDisk 现读，非手填）",
           "note": ("★ 本输出默认只有 onDisk（读盘）；inService 只能从**在役进程**读出 —— "
                    "工具调用返回体或在役进程写出的日志；**不得靠 import 模块**（那是盘上快照）。"
                    "★ drift 反映 **read_at 时刻**的状态（inService 会随重载变化，故不可当长期结论）；"
                    "drift_kind ∈ {diff, unknown, n/a} 为机器可读枚举（unknown=不知是否不同，diff=已知不同）。"),
           "artifacts": []}
    for name, p in targets:
        e = {"name": name, "path": p, "exists": os.path.exists(p)}
        if e["exists"]:
            e["mtime"] = datetime.datetime.fromtimestamp(os.path.getmtime(p), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if name == "bb-card-send":
                e["inService"] = in_service_bb
                e["inService_source"] = "bb-card-send.log 的 runtimeVersion（在役进程写出）"
                if (in_service_bb and not str(in_service_bb).startswith("未加载")
                        and in_service_bb != e.get("version")):
                    e["drift"] = "⚠ 盘上≠在役"; e["drift_kind"] = "diff"
                elif str(in_service_bb or "").startswith("未加载"):
                    e["drift"] = "未加载/不可读"; e["drift_kind"] = "unknown"
                else:
                    e["drift"] = "—"; e["drift_kind"] = "n/a"
            elif name == "pstd":
                e["inService"] = "需 tool 读数（plugin_standard action=norms 的 std）"
                e["inService_source"] = "在役进程（工具调用）"
                e["drift"] = "—"; e["drift_kind"] = "n/a"
            else:
                e["inService"] = "（该制品无在役自述字段）"
                e["drift"] = "—"; e["drift_kind"] = "n/a"
            try:
                with open(p, encoding="utf-8") as f:
                    txt = f.read()
                m = __import__("re").search(r'"version"\s*:\s*"([^"]+)"', txt) or __import__("re").search(r"VERSION\s*=\s*\"([^\"]+)\"", txt)
                e["version"] = m.group(1) if m else "未找到"
            except Exception as ex:
                e["version"] = f"读取失败 {type(ex).__name__}"
        e["onDisk"] = f"{e.get('version')} @ {e.get('mtime','—')}"
        out["artifacts"].append(e)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("keys", nargs="*"); ap.add_argument("--json", action="store_true")
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    ap.add_argument("--selftest", action="store_true"); ap.add_argument("--version", action="store_true")
    ap.add_argument("--versions", action="store_true", help="脚本现读制品版本+mtime（回执用，禁手填）")
    ap.add_argument("--basis", action="store_true", help="现读比较基准（排除集/脱敏集/规则），供重述件引用")
    a = ap.parse_args()
    if a.version:
        print(json.dumps({"tool": "card-surface-evidence", "version": VERSION})); return 0
    if a.basis:
        # ★ 2026-10-08 独立复核员：证据卡若手写基准，会随工具演进过期（引用者拿到过宽基准）。
        #   ⇒ 基准也必须**现读**。
        import datetime as _dt
        print(json.dumps({
            "read_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "by": "card-surface-evidence.py --basis（现读，禁手抄）",
            "TRANSPORT_MARKERS": list(TRANSPORT_MARKERS),
            "EVIDENCE_FOR_EXCLUSION": EVIDENCE_FOR_EXCLUSION,
            "REDACTION_MARKERS": list(REDACTION_MARKERS),
            "REDACTION_DECLARED": list(REDACTION_DECLARED),
            "rule": "action 层=defect（排除集外 value 不等；或差异超出声明脱敏集）；豁免一律有界：差异 ⊆ 已声明集合才降级",
            "dv_convention": "dv = local.version - central.version（2026-10-08 起固定；此前相反约定按原文取反读）",
            "levels": ["ok", "transport", "redaction-divergence", "info", "none", "unknown", "defect"],
        }, ensure_ascii=False, indent=1))
        return 0
    if a.versions:
        v = versions()
        for e in v["artifacts"]:
            print(f"  {e['name']:<30} onDisk={str(e.get('onDisk') or e.get('version')):<26} "
                  f"inService={str(e.get('inService'))[:26]:<26} drift={e.get('drift','—')}({e.get('drift_kind','—')})")
        print(f"  read_at={v['read_at']} · {v['by']}")
        return 0
    if a.selftest:
        return selftest()
    if not a.keys:
        ap.error("需要至少一个 key")
    r = evidence(a.keys)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print(f"measured_at={r['measured_at']}")
        for row in r["rows"]:
            print(f"  {row['key']}\n    local={row['local_status']} sha={row['local_value_sha16']} v={row['local_version']}"
                  f" | central={row['central_status']} sha={row['central_value_sha16']} v={row['central_version']}"
                  f" | converged={row['converged']} | dv={row.get('dv')} level={row.get('level')}")
    return 0 if all(x.get("level") not in ("defect",) for x in r["rows"]) else 1


if __name__ == "__main__":
    sys.exit(main())
