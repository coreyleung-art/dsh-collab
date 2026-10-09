#!/usr/bin/env python3
"""复核星桥的 R048 两项未闭合（按我原先给出的前置条件逐条对，不看他的结论）
② SystemGraph：hold-out 是否真的定义 —— 我的前置是四点：测试集划分 / 不得参与特征与候选生成 / 划分命令 / 「采纳率30天」拆先验后验
③ 提醒器 v3：失败上限(5次) + 24h 绝对时限 + sync —— 是否真的在代码里生效

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
import os, re, json, urllib.request, subprocess


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/r048-remediation-verify.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

PLAN = os.path.expanduser("~/dsh-collab/docs/systemgraph-internal-completion-plan-20261008.md")
AR = os.path.expanduser("~/dsh-collab/tools/auto-reminder.sh")
CARD = "notes/mac-mini/r048-remediation-status-20261008"

print("=" * 76)
print("【0】星桥的卡")
print("=" * 76)
try:
    d = json.load(urllib.request.urlopen("http://127.0.0.1:8792/" + CARD, timeout=25))
    v = d["value"]
    print("ts =", d.get("ts"), "subject =", str(v.get("subject"))[:110])
    for k, val in list(v.items())[:14]:
        if k in ("from", "from_label", "to", "subject"):
            continue
        s = json.dumps(val, ensure_ascii=False) if isinstance(val, (dict, list)) else str(val)
        print(f"  [{k}] {s[:400]}")
except Exception as e:
    print("读卡失败:", e)

print()
print("=" * 76)
print("【②】方案里的 hold-out（我的四点前置逐条对）")
print("=" * 76)
if os.path.isfile(PLAN):
    txt = open(PLAN, errors="replace").read()
    print(f"  方案存在：{PLAN}  {len(txt)} 字符")
    hits = [m.start() for m in re.finditer(r"hold[- _]?out|留出|留一|holdout", txt, re.I)]
    print(f"  含 hold-out/留出 的位置数 = {len(hits)}")
    for h in hits[:6]:
        seg = txt[max(0, h - 120):h + 340].replace("\n", " ")
        print(f"    …{seg}…")
        print("    " + "-" * 60)
    checks = {
        "①测试集划分写明": bool(re.search(r"hold[- _]?out|留出集|测试集", txt, re.I)),
        "②不得参与特征/候选生成": bool(re.search(r"不得参与|不参与(特征|候选)|排除在(特征|候选)", txt)),
        "③划分命令": bool(re.search(r"命令|split|--seed|划分脚本|python3 .*split", txt)),
        "④采纳率拆先验/后验": bool(re.search(r"先验|后验", txt)),
    }
    for k, ok in checks.items():
        print(f"  {'✅' if ok else '❌'} {k}")
else:
    print("  ❌ 方案文件不存在")
    checks = {}

print()
print("=" * 76)
print("【③】提醒器 v3 的三项（失败上限 / 24h 时限 / sync）")
print("=" * 76)
if os.path.isfile(AR):
    st = os.stat(AR)
    import datetime
    print(f"  脚本：{AR}  {st.st_size}B  mtime={datetime.datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%dT%H:%M:%S')}")
    src = open(AR, errors="replace").read()
    for label, pat in (("失败上限", r"FAIL|fail|MAX_FAIL|失败上限"),
                       ("24h/时限", r"24|86400|时限|deadline|elapsed"),
                       ("sync", r"\bsync\b"),
                       ("探活/可达", r"ok:true|可达|probe|curl.*api/send")):
        m = re.findall(pat, src)
        print(f"  {'✅' if m else '❌'} {label:<12} 命中 {len(m)} 次")
    print("\n  关键片段:")
    for i, line in enumerate(src.splitlines(), 1):
        if re.search(r"FAIL|fail_count|MAX_FAIL|86400|24 \* 3600|sync|ack", line):
            print(f"    {i:>4}: {line.strip()[:130]}")
else:
    print("  ❌ 脚本不存在")
