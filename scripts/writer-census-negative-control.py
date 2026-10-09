#!/usr/bin/env python3
"""补做阴性对照（对方指出我上一轮只落了一半）：
阳性 = 已知真例必须中；阴性 = 已知无关样本必须不中（或定量给基率）
本脚本测我 writer 计数判定的【四类边界】：有值 / 空串 / null / 字段缺失
⇒ 目的是把「0」的敏感性边界钉清楚：哪些形态会被我计入、哪些不会

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
    print("== writer-census-negative-control 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 补做阴性对照（对方指出我上一轮只落了一半）：")
    print("  · 阳性 = 已知真例必须中；阴性 = 已知无关样本必须不中（或定量给基率）")
    print("  · 本脚本测我 writer 计数判定的【四类边界】：有值 / 空串 / null / 字段缺失")
    print("  · ⇒ 目的是把「0」的敏感性边界钉清楚：哪些形态会被我计入、哪些不会")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: json, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/writer-census-negative-control.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

import json, tempfile, os

rows = [
    ("有值", {"op": "PUT", "key": "k1", "value": {"a": 1}, "writer": "mbp-ops"}),
    ("空串", {"op": "PUT", "key": "k2", "value": {"a": 2}, "writer": ""}),
    ("null", {"op": "PUT", "key": "k3", "value": {"a": 3}, "writer": None}),
    ("字段缺失", {"op": "PUT", "key": "k4", "value": {"a": 4}}),
]
td = tempfile.mkdtemp(prefix="writer-negctl-")
fp = os.path.join(td, "synthetic.jsonl")
with open(fp, "w") as f:
    for _, r in rows:
        f.write(json.dumps(r) + "\n")

print("=== 我的判定：`e.get(\"writer\") is not None` ===")
hit = []
for label, r in rows:
    v = r.get("writer")
    counted = v is not None
    if counted:
        hit.append(label)
    print(f"  {label:<8} writer={v!r:<12} ⇒ {'计入' if counted else '不计入'}")
print(f"\n  ⇒ 计入的形态 = {hit}")

print()
print("=== 另一条更严的判定（同时排除空串）：`bool(v)` ===")
hit2 = [label for label, r in rows if bool(r.get("writer"))]
print(f"  ⇒ 计入的形态 = {hit2}")
print("  ⇒ 与上面差 = 「空串」这一格 ⇒ **空串在宽松判定下会被计入**")

print()
print("=== 对本轮结论的意义 ===")
print("  实测 audit 46111 条：`is not None` 判定下 **0** 条")
print("  ⇒ 因为「空串」在宽松判定下**也会被计入**，而结果仍为 0")
print("  ⇒ 所以合格形态（非空值 / 空串）**都没有** ⇒ 「0」比“仅非空值为 0”更强一档")
print("  ⚠ 但仍取决于服务端：若服务端对空 header 返回 None（而非 Some(\"\")），则空串根本不会落盘 ⇒")
print("    该推论要成立，需确认 `header()` 对空串的行为（见另一路：读 http.rs 的 header 函数）")


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/writer-census-negative-control.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass
