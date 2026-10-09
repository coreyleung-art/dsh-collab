#!/usr/bin/env python3
"""★ 按【内容】而非文件名判定归属（比文件名硬）
判据：文件内容含裁判 session id `session-1ffded95` ⇒ 与裁判有关；
      含作者的 `session-b250bf9d` ⇒ 与作者有关；都不含 ⇒ 归属未定。
只扫文本类扩展名且 < 2MB 的文件。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
import os, re


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-tmp-ownership-by-content.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

ME = "session-1ffded95"
AUTHOR = "session-b250bf9d"
XQ = "session-fa1f9150"          # 星桥
REVIEWER = "session-4d0e75cf"    # 独立复核员
EXTS = {".sh", ".py", ".json", ".jsonl", ".txt", ".md", ".out", ".rc", ".log", ".err", ".yml", ".yaml", ".mjs"}

rows = []
skipped = 0
for name in sorted(os.listdir("/tmp")):
    p = os.path.join("/tmp", name)
    if not os.path.isfile(p):
        continue
    if os.path.splitext(name)[1].lower() not in EXTS:
        skipped += 1
        continue
    try:
        if os.path.getsize(p) > 2 * 1024 * 1024:
            skipped += 1
            continue
        with open(p, "rb") as f:
            txt = f.read().decode("utf-8", "replace")
    except Exception:
        skipped += 1
        continue
    who = []
    if ME in txt:
        who.append("裁判")
    if AUTHOR in txt:
        who.append("作者")
    if XQ in txt:
        who.append("星桥")
    if REVIEWER in txt:
        who.append("复核员")
    if who:
        rows.append((name, os.path.getsize(p), who))

print("=== 按内容归属扫描 /tmp（文本类，<2MB）===")
print(f"跳过（非文本类或过大）={skipped}")
print(f"命中归属标记的文件 = {len(rows)}\n")
print(f"{'大小B':>9}  {'归属':<22} 文件")
mine = []
for name, sz, who in rows:
    tag = "+".join(who)
    print(f"{sz:>9}  {tag:<22} {name}")
    if "裁判" in who:
        mine.append(name)

print(f"\n★ 含裁判 session id 的文件 = {len(mine)}")
for n in mine:
    print("   ", n)
print(f"\n★ 含作者 session id 的文件 = {sum(1 for r in rows if '作者' in r[2])}")
print(f"★ 含星桥 session id 的文件 = {sum(1 for r in rows if '星桥' in r[2])}")
