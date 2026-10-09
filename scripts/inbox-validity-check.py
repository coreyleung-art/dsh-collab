#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""inbox-validity-check.py —— 会话时效·空间 有效性审查器（v1.0.0 · 现为【参考实现】）

★ 替代关系声明（2026-10-08，防两份真相）：
  本脚本的判据已**移植进常驻插件** `~/dsh-collab/devices/dsh-plugin-item-validity-review-check/`
  （R006 十项交付形态，工具 `item_validity_*`）。
  ⇒ **形态与五态判据以该插件为准**；本脚本保留为：
     ① 判据的**可读参考实现**（Python，逻辑更直白）
     ② 插件不可用时的**降级通道**
  ⇒ 保留期内**二者判据必须一致**；若需要修改判据，**先改插件、再同步此处**，不得反向。

用途：对一批「跨会话条目」（卡 / 回执 / 待办。）快速判它【还要不要管】，
     并把「已关闭」的落成一份索引，使它们不再重复进入视野。

★ 它回答的唯一问题：「这条现在还有效吗？」
★ 三态（+ 一态）：closed（已关闭，不必再管）· stale（已过期/已被取代）
                  open（仍需处理）· unknown（判不了 —— 缺字段，不是「没有」）
★ 两个轴：时效（多久了 / 有效期） × 空间（管到哪 / 引用对象是否还在）

★ 判据全部来自 2026-10-08 实际踩到的坑，非凭空设计：
  ① 显式状态字（最强判据） ② 被取代（同主题有更新件） ③ 时效（超窗）
  ④ 引用对象是否仍存在   ⑤ 依赖是否已解决    ⑥ 缺时刻 ⇒ unknown（不是 open）

用法：
  python3 inbox-validity-check.py                    # 扫默认 inbox，出统计 + 分类
  python3 inbox-validity-check.py --list closed      # 只列某一类
  python3 inbox-validity-check.py --json             # 机读输出
  python3 inbox-validity-check.py --write-index      # 写 closed 索引（供以后先查）
  python3 inbox-validity-check.py --selftest         # 正/负例矩阵（自证）
  python3 inbox-validity-check.py --dir <path>       # 扫别的目录

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
    print("== inbox-validity-check 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · inbox-validity-check.py —— 会话时效·空间 有效性审查器（v1.0.0 · 现为【参考实现】）")
    print("  · ★ 替代关系声明（2026-10-08，防两份真相）：")
    print("  · 本脚本的判据已**移植进常驻插件** `~/dsh-collab/devices/dsh-plugin-item-validity-review-check/`")
    print("  · （R006 十项交付形态，工具 `item_validity_*`）。")
    print("  · 命令/参数: dir, list, json, write-index, max-age-days, selftest, version")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, datetime, json, os, re, sys, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/inbox-validity-check.log")
    return 0



import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/inbox-validity-check.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = "1.2.3"
DEFAULT_DIR = os.path.expanduser("~/.dsh/inbox")
CLOSED_INDEX = os.path.expanduser("~/dsh-collab/docs/inbox-closed-index.json")

# ── 判据①：显式「已关闭」状态字（最强：作者明确说过不必再管）
#   只在 status/state/verdict/reason/detail 等**状态类字段**里找，不在正文里找
#   （避免正文里出现「已完成」三个字就被误判——2026-10-08 的 pit：标签不能替代比对）
CLOSED_WORDS = ("不需再动", "不需处理", "无需处理", "已收讫", "已核验通过", "已通过",
                "已关闭", "已归档", "已解决", "已完成", "处理完毕", "已交付完毕",
                "closed", "done", "resolved", "passed", "no action needed")
# ── 判据④：显式「仍待处理」状态字
OPEN_WORDS = ("等你", "待你", "待处理", "仍在等", "待裁定", "待裁", "待回", "待其余方回",
              "pending", "awaiting your", "need your")

STATUS_FIELDS = ("status", "state", "verdict", "resolution", "result")

# ── 时效窗：不同类型条目的「有效期」不同（本日已证：一个数装两种东西是常见错法）
#   回执类（ack-*）：一旦确认即永久关闭 —— 无时效
#   征询/待办类：默认 7 天；超窗且无新活动 ⇒ stale（保守；可用 --max-age-days 调）
DEFAULT_MAX_AGE_DAYS = 7


def _load(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _txt(v, limit=4000):
    """把任意字段压成可搜索的短文本（不 dump 整个对象）。"""
    if v is None:
        return ""
    if isinstance(v, str):
        return v[:limit]
    if isinstance(v, (int, float, bool)):
        return str(v)
    if isinstance(v, list):
        return " ".join(_txt(x, 400) for x in v[:10])[:limit]
    if isinstance(v, dict):
        return " ".join(_txt(x, 400) for x in list(v.values())[:10])[:limit]
    return ""


def _status_text(d):
    """只取状态类字段（判据①/④的载体）。"""
    parts = []
    for k in STATUS_FIELDS:
        if k in d:
            parts.append(_txt(d[k]))
    # 明确的「还在等你」类字段
    for k in ("still_pending_user", "awaiting_user", "needs_user"):
        if k in d:
            parts.append(_txt(d[k]))
    return " ".join(parts)


def _age_days(d, now_ms):
    """条目年龄（天）。缺时刻 ⇒ None（unknown，不是 0）。"""
    for k in ("sent_at_epoch_ms", "ts_epoch_ms", "created_at_epoch_ms"):
        v = d.get(k)
        if isinstance(v, (int, float)) and v > 1e11:   # ms 量级
            return (now_ms - v) / 86400000.0
    for k in ("ts", "at", "measured_at", "created_at"):
        v = d.get(k)
        if isinstance(v, str) and len(v) >= 10:
            m = re.match(r"(\d{4})-(\d{2})-(\d{2})", v)
            if m:
                try:
                    t = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                                 tzinfo=timezone.utc).timestamp() * 1000
                    return (now_ms - t) / 86400000.0
                except Exception:
                    pass
    return None


def shape_of(d):
    """条目形态 —— **先分形态，再判有效性**（v1.1.0 修正）：
       数据实测 2642 条里 58% 属「记录体」，对它们谈「有效性」没有意义（它们不是动作项）。
       · action  动作项：有 awaiting / still_pending_user / reply_required=true  ⇒ 需判有效性
       · ack     回执：有 subject 且无 awaiting                              ⇒ 只需知「已读过」
       · record  记录体：有 content/body 且无 awaiting / 无 status 字          ⇒ 它是资料，不是待办
       · unknown 判不了：连形态都认不出
    """
    if not isinstance(d, dict):
        return "unknown"
    if any(k in d for k in ("awaiting", "still_pending_user", "awaiting_user")):
        return "action"
    if d.get("reply_required") is True:
        return "action"
    st = _status_text(d)
    if any(w in st for w in CLOSED_WORDS):
        return "ack"
    if any(k in d for k in ("content", "body", "body_md", "title", "subject")):
        return "record"
    return "unknown"


def classify(path, d, now_ms, max_age_days=DEFAULT_MAX_AGE_DAYS):
    """→ (状态, 理由)。状态 ∈ closed / stale / open / unknown。"""
    if not isinstance(d, dict):
        return "unknown", "非 JSON 对象（读失败或格式不符）⇒ 判不了"

    st = _status_text(d)
    name = os.path.basename(path)

    # ① 显式关闭（最强）
    hit = [w for w in CLOSED_WORDS if w in st]
    if hit:
        return "closed", "状态字命中「%s」⇒ 作者已声明不必再管" % hit[0]

    # ④ 显式待处理
    hit_open = [w for w in OPEN_WORDS if w in st]
    age = _age_days(d, now_ms)

    if hit_open:
        if age is None:
            return "open", "有待处理标记（「%s」），但**无时刻** ⇒ 无法判时效" % hit_open[0]
        if age > max_age_days:
            return "stale", ("待处理标记（「%s」）已存在 %.1f 天（> %g 天窗）⇒ "
                             "**疑似过期**；须核其依赖是否已解决后才可关闭"
                             % (hit_open[0], age, max_age_days))
        return "open", "待处理标记（「%s」）· 距今 %.1f 天 ⇒ 仍在窗内" % (hit_open[0], age)

    # ⑤ ★ v1.2.0 修正：**时效只适用于动作项**。
    #    记录体（record）与回执（ack）是【历史事实】，**本身无时效** ——
    #    拿年龄去判它们 = 用「会变的量」去判「不该变的东西」（本日已落同一纪律：
    #    统计量现算 / 历史事实冻结；记录体的年龄不构成它失效的理由）。
    shp = shape_of(d)
    if shp == "unknown":
        # ★ v1.2.1（由 selftest 负例抓出）：**形态判不了 ≠ 不适用** ——
        #   「不知道它适不适用哪种判据」与「不适用」是两个结论；前者只能报 unknown。
        return "unknown", ("**形态判不了** ⇒ 连它适不适用有效性判据都不知道"
                           "（这不是「不适用」，是「判不了」）")
    if shp != "action":
        return "n/a", ("形态=%s：**不是动作项 ⇒ 不对它谈有效性**"
                       "（记录体/回执是历史事实，其年龄不构成失效理由）" % shp)
    if age is None:
        return "unknown", "是动作项，但**缺时刻** ⇒ 无法判时效（不是「没有」）"
    return "open", "动作项（无显式状态字）· 距今 %.1f 天 ⇒ 仍需你确认" % age


def scan(directory, max_age_days=DEFAULT_MAX_AGE_DAYS):
    now_ms = time.time() * 1000
    rows = []
    if not os.path.isdir(directory):
        return rows
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".json"):
            continue
        p = os.path.join(directory, name)
        if not os.path.isfile(p):
            continue
        d = _load(p)
        state, why = classify(p, d, now_ms, max_age_days)
        rec = {"file": name, "state": state, "shape": shape_of(d), "why": why}
        if isinstance(d, dict):
            for k in ("subject", "sent_at_epoch_ms", "awaiting", "from"):
                if k in d:
                    rec[k] = _txt(d[k], 200)
        rows.append(rec)
    return rows


# ── 自证矩阵：正例 + 负例（本日纪律：判据须双向对照，只给正例不算）
def selftest():
    now = time.time() * 1000
    day = 86400000
    cases = [
        # (名称, 条目, 期望状态)
        ("正例·显式关闭", {"status": "已核验通过，不需再动。", "sent_at_epoch_ms": now - 30 * day}, "closed"),
        ("正例·已收讫", {"status": "已收讫", "sent_at_epoch_ms": now - 1 * day}, "closed"),
        ("负例·正文含关闭词【不得】判 closed", {"body": "我之前已完成过一次", "sent_at_epoch_ms": now - 1 * day}, "n/a"),
        ("正例·窗内待处理", {"still_pending_user": "审批单仍在等你", "sent_at_epoch_ms": now - 1 * day}, "open"),
        ("负例·超窗待处理⇒降为 stale", {"still_pending_user": "审批单仍在等你", "sent_at_epoch_ms": now - 30 * day}, "stale"),
        ("负例·无状态无时刻【不得】判 open", {"subject": "某事"}, "n/a"),
        ("负例·非 JSON 对象", None, "unknown"),
        ("正例·带时刻无状态⇒unknown", {"ts": "2026-10-08T00:00:00Z", "sent_at_epoch_ms": now - 1 * day}, "unknown"),
        ("负例·记录体年龄再大也不判 stale", {"content": "一份旧资料", "sent_at_epoch_ms": now - 300 * day}, "n/a"),
        ("负例·动作项无状态字⇒open 而非 unknown", {"awaiting": "x", "sent_at_epoch_ms": now - 2 * day}, "open"),
    ]
    ok = bad = 0
    for name, d, want in cases:
        got, why = classify("t.json", d, now)
        flag = "✅" if got == want else "❌"
        if got == want:
            ok += 1
        else:
            bad += 1
        print("  %s %-38s 期望=%-8s 实得=%-8s  %s" % (flag, name, want, got, why[:44]))
    print("\n  selftest: %d PASS / %d FAIL" % (ok, bad))
    return 0 if bad == 0 else 1


def main():
    ap = argparse.ArgumentParser(description="会话时效·空间 有效性审查器 v" + VERSION)
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    ap.add_argument("--list", choices=["closed", "stale", "open", "unknown"])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write-index", action="store_true")
    ap.add_argument("--max-age-days", type=float, default=DEFAULT_MAX_AGE_DAYS)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="version", version="inbox-validity-check " + VERSION)
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    rows = scan(a.dir, a.max_age_days)
    if not rows:
        print("  目录不存在或为空: %s" % a.dir)
        return 2

    tally = {}
    for r in rows:
        tally[r["state"]] = tally.get(r["state"], 0) + 1

    if a.json:
        print(json.dumps({"version": VERSION, "dir": a.dir, "total": len(rows),
                          "tally": tally, "rows": rows}, ensure_ascii=False, indent=2))
        return 0

    if a.list:
        show = [r for r in rows if r["state"] == a.list]
        print("  %s：%d 条" % (a.list, len(show)))
        for r in show[:40]:
            print("    · %-52s %s" % (r["file"][:50], r["why"][:78]))
        if len(show) > 40:
            print("    … 另有 %d 条（用 --json 取全量）" % (len(show) - 40))
        return 0

    print("  ── 会话时效·空间 有效性审查（%s）──" % a.dir.replace(os.path.expanduser("~"), "~"))
    print("    总条目 %d" % len(rows))
    for k in ("closed", "stale", "open", "unknown", "n/a"):
        print("      %-8s %4d" % (k, tally.get(k, 0)))
    print()
    shp = {}
    for r in rows:
        shp[r.get("shape", "unknown")] = shp.get(r.get("shape", "unknown"), 0) + 1
    print()
    print("    ── 形态（v1.1.0：先分形态再谈有效性）──")
    print("      action  动作项（awaiting / reply_required=true）  %4d  ← **只有这类才需判有效性**" % shp.get("action", 0))
    print("      ack     回执（有状态字）                        %4d" % shp.get("ack", 0))
    print("      record  记录体（是资料，不是待办）              %4d" % shp.get("record", 0))
    print("      unknown 形态判不了                              %4d" % shp.get("unknown", 0))
    print()
    na = tally.get("n/a", 0)
    print("      %-8s %4d  ← 非动作项，**不对它谈有效性**" % ("n/a", na))
    print()
    act = shp.get("action", 0)
    print("    ⇒ **需判有效性的只有动作项：%d 条**（记录体/回执 %d 条无时效，不应拿年龄判它们）"
          % (act, na))
    print("    ⇒ 形态判不了的 %d 条单列 —— 它们既不能算「需处理」，也不能算「不适用」"
          % shp.get("unknown", 0))
    print("    ★ 盲区（必须声明）：本工具**只看卡本身**，看不到「它是否已在会话线程里被回复」")
    print("      ⇒ 故 `open` 的含义是【无显式关闭声明】，**不等于【仍有未决待办】**。")
    print("    ⇒ closed + stale = 可不再重复查看的：%d"
          % (tally.get("closed", 0) + tally.get("stale", 0)))
    print("    ⇒ open = 【无显式关闭声明】的：%d —— **不等于【仍有未决待办】**（见上方盲区）"
          % tally.get("open", 0))
    print("      ⇒ 要判「是否真待办」，须再看它的 thread 里有没有回复 —— **本工具看不到，故标未证**")
    print("    ⚠ unknown 不是「没有」：它是【判不了】（缺状态字或缺时刻）⇒ 须补字段，不得当已关闭")

    if a.write_index:
        closedish = [r for r in rows if r["state"] in ("closed", "stale")]
        idx = {"version": VERSION,
               "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "dir": a.dir, "total": len(rows),
               "tally": tally,
               "note": ("本索引用途：**以后先查此处** —— 命中者不必再逐条查看。"
                        "stale 不是「已关闭」而是「疑似过期，须核依赖后才能关闭」。"),
               "items": [{"file": r["file"], "state": r["state"], "why": r["why"]} for r in closedish]}
        os.makedirs(os.path.dirname(CLOSED_INDEX), exist_ok=True)
        with open(CLOSED_INDEX, "w", encoding="utf-8") as f:
            json.dump(idx, f, ensure_ascii=False, indent=2)
        print("    ✅ 已写索引 → %s（%d 条）" % (CLOSED_INDEX.replace(os.path.expanduser("~"), "~"), len(closedish)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
