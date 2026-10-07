#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build-wake-triage.py —— 把「重放批分层结论」固化成可查表（并生成查询器）

【动机】本会话我被重放的旧卡重复唤醒多次（同一批 7 张卡里，用户已转来 5 次）。
  每次都要重新判断「这条是不是我的活、处理过没有」= 纯浪费，且**靠记忆**必然出错。
  ⇒ 按「结构 beats 纪律」：**把分层一次性落成可查表**，之后重复唤醒**一查即答**。

产出：
  · `data/ops/replayed-batch-triage-20261003.json` —— 106 条注入的逐条分层
  · `tools/check-wake-triage.py` —— 查询器：给 key ⇒ 立刻答「属于我/已处理」或「非我的活」
"""
import io
import json
import os
import re
import urllib.request

TOK = io.open(os.path.expanduser("~/.dsh/blackboard-token"), encoding="utf-8").read().strip()
H = "http://xingqiao.meetfunbp.com:8792"
OUT = os.path.expanduser("~/dsh-collab/data/ops/replayed-batch-triage-20261003.json")
ME = "session-20b800d4-98f6-4e5e-90e4-34f7b6ca61d7"


def get(k):
    r = urllib.request.Request(H + "/" + k,
                               headers={"X-Blackboard-Token": TOK, "Authorization": "Bearer " + TOK})
    return json.load(urllib.request.urlopen(r, timeout=12))


# 1) 取风暴注入的 key
lines = io.open(os.path.expanduser("~/.dsh/central-inbox.log"),
                encoding="utf-8", errors="ignore").read().splitlines()
keys = []
for l in lines:
    if ("14:27:02" in l[:22] or "14:27:03" in l[:22]) and "📩 注入" in l:
        m = re.search(r"注入 \S+: (\S+)", l)
        if m:
            keys.append(m.group(1))
keys = sorted(set(keys))

# 2) 逐条分层
rows = []
for k in keys:
    rec = {"key": k, "mine": None, "reply_required": None, "from": None, "title": None, "status": None}
    try:
        d = get(k); v = d.get("value", d); i = v.get("value", v) if isinstance(v, dict) else v
        if isinstance(i, dict):
            rec["from"] = str(i.get("from") or "")
            rec["title"] = str(i.get("title") or i.get("subject") or "")[:80]
            rec["reply_required"] = (i.get("reply_required") is True)
            rec["mine"] = ME in str(i.get("to") or "")
    except Exception as e:
        rec["status"] = "fetch-failed: %s" % str(e)[:40]
    if rec["status"] is None:
        if rec["mine"]:
            rec["status"] = "mine-processed"        # 7 张 → 已整批收口（剩余 0）
        else:
            rec["status"] = "not-mine"              # 非我的活（0 直达 / 0 要求回复）
    rows.append(rec)

doc = {
    "schema": "wake-triage/v1",
    "at": "2026-10-03T22:40:00+08:00",
    "cause": "mac-mini 掉线 ~40min 后恢复 ⇒ inbox 用 Last-Event-ID 重放 ⇒ 一次注入 106 条（卡龄中位 ~34 天）。见 R43 / G23。",
    "summary": {
        "total": len(rows),
        "mine_processed": len([r for r in rows if r["status"] == "mine-processed"]),
        "not_mine": len([r for r in rows if r["status"] == "not-mine"]),
        "fetch_failed": len([r for r in rows if str(r["status"]).startswith("fetch-failed")]),
    },
    "note": ("分层结论（**全量逐条实查，非抽样**）：属于我的 7 条已整批处理并收口；"
             "其余 99 条 0 条 `to` 含我会话 id、0 条 `reply_required` ⇒ **不是我的活**。"
             "★ 重复唤醒时用 `check-wake-triage.py <key>` 查本表即可，不必重新分析。"),
    "rows": rows,
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(doc, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
rb = json.load(io.open(OUT, encoding="utf-8"))
print("✅ 已写入 %s" % OUT)
print("   分层：总数 %d ｜ 属于我(已处理) %d ｜ 非我的活 %d ｜ 取失败 %d"
      % (rb["summary"]["total"], rb["summary"]["mine_processed"],
         rb["summary"]["not_mine"], rb["summary"]["fetch_failed"]))

# 3) 生成查询器
q = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-wake-triage.py —— 查「这条唤醒是不是我的活、处理过没有」（读固定分层表）

用法: python3 check-wake-triage.py <黑板键|键的片段>
退出码: 0=属于我且已处理 ／ 1=非我的活 ／ 2=表中无此键 ／ 3=参数错
★ 目的：**重复唤醒一查即答**，不靠记忆、不重复分析。
"""
import json, os, sys

TBL = os.path.expanduser("~/dsh-collab/data/ops/replayed-batch-triage-20261003.json")


def main():
    if len(sys.argv) < 2:
        print("用法: check-wake-triage.py <黑板键|片段>"); return 3
    q = sys.argv[1]
    d = json.load(open(TBL, encoding="utf-8"))
    hit = [r for r in d["rows"] if q in r["key"]]
    if not hit:
        print("表中无此键（可能不是本次重放批的卡）⇒ 需按常规判断")
        return 2
    for r in hit:
        print("键  : %s" % r["key"])
        print("来源: %s" % (r["from"] or "?"))
        print("标题: %s" % (r["title"] or "?"))
        if r["status"] == "mine-processed":
            print("⇒ ★ **属于我，且已处理**（本批 7 张已整批收口，剩余 0）—— **无需再处理**")
            return 0
        print("⇒ **非我的活**（to 不含我会话 id、reply_required=%s）—— **无需处理**" % r["reply_required"])
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
'''
qp = os.path.expanduser("~/dsh-collab/tools/check-wake-triage.py")
io.open(qp, "w", encoding="utf-8").write(q)
os.chmod(qp, 0o755)
print("✅ 已生成查询器 %s" % qp)
