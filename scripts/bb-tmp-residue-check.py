#!/usr/bin/env python3
"""两件：
A) 读作者的新卡 notes/mac-mini/author-to-adjudicator-pit27-ordering-and-tmp-residue-20261008
B) 列出 /tmp 中与本次审计相关的残留（核实他说的「仍剩 12 件」）

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
import json, os, urllib.request, re


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-tmp-residue-check.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

LOCAL = "http://127.0.0.1:8792/"
KEY = "notes/mac-mini/author-to-adjudicator-pit27-ordering-and-tmp-residue-20261008"

print("=" * 74)
print("【A】作者新卡内容")
print("=" * 74)
try:
    d = json.load(urllib.request.urlopen(LOCAL + KEY, timeout=25))
    v = d["value"]
    print("ts =", d.get("ts"), "| version =", d.get("version"))
    print("subject:", v.get("subject"))
    c = v.get("content", v)
    for k, val in c.items():
        if k in ("subject",):
            continue
        if isinstance(val, (dict, list)):
            print(f"\n[{k}]")
            print("  " + json.dumps(val, ensure_ascii=False)[:1500])
        else:
            print(f"\n[{k}]\n  {str(val)[:1200]}")
except Exception as e:
    print("读取失败:", e)

print()
print("=" * 74)
print("【B】/tmp 中与本次审计相关的文件（核实「仍剩 12 件」）")
print("=" * 74)
PAT = re.compile(r"audit|rb_|idx_dump|pstd|bb_|card-|port_from|probe|\.sh$|\.py$|\.json$|\.txt$", re.I)
hits = []
try:
    for name in sorted(os.listdir("/tmp")):
        full = os.path.join("/tmp", name)
        if not os.path.isfile(full):
            continue
        if PAT.search(name):
            hits.append((name, os.path.getsize(full)))
except Exception as e:
    print("列目录失败:", e)

print(f"命中模式的文件数 = {len(hits)}")
for n, sz in hits:
    print(f"  {sz:>9}  {n}")
print(f"\n/tmp 顶层条目总数 = {len(os.listdir('/tmp'))}")
