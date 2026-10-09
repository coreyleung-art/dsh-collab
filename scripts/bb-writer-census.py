#!/usr/bin/env python3
"""独立复核「X-Writer 只记不验 / writer 有值者=0」——作者：裁判（自测，不引用他人读数）"""

#
# ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
# 依据：r006-debt-assess.py 机械扫描未检出以下原语：
#       subprocess / os.system / eval / exec / os.remove / rmtree /
#       os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
# ★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
#
import json, os, glob, collections


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-writer-census.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

DD = "/Users/coreyleung/dsh-collab/token-monitor/blackboard"
print("data_dir =", DD, "exists =", os.path.isdir(DD))
if os.path.isdir(DD):
    for f in sorted(os.listdir(DD)):
        p = os.path.join(DD, f)
        print(f"  {f}  {os.path.getsize(p) if os.path.isfile(p) else '<dir>'}")

files = sorted(glob.glob(os.path.join(DD, "audit*.jsonl")))
print(f"\naudit 文件数 = {len(files)}（**含轮转**）:")
for f in files:
    print("   ", os.path.basename(f), os.path.getsize(f))
per_file = {}

total = 0
with_writer = 0
bare = 0
ops = collections.Counter()
writers = collections.Counter()
put_valueless = 0
put_with_val = 0
for f in files:
    ftotal = fwriter = 0
    with open(f, "r", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                bare += 1
                continue
            total += 1
            ftotal += 1
            ops[e.get("op")] += 1
            w = e.get("writer")
            if w is not None:
                with_writer += 1
                fwriter += 1
                writers[str(w)] += 1
            if e.get("op") == "PUT":
                if e.get("value") is None:
                    put_valueless += 1
                else:
                    put_with_val += 1
    per_file[os.path.basename(f)] = (ftotal, fwriter)
print("\n=== 逐文件（行数, writer有值）===")
for k, (t, w) in per_file.items():
    print(f"  {k}  {t}  {w}")

print("\n=== 统计（读取时刻 = 现在；对象 = 上述文件全部行）===")
print("总条目            =", total)
print("writer 有值       =", with_writer)
print("writer 缺失       =", total - with_writer)
print("无法解析行        =", bare)
print("op 分布           =", dict(ops))
print("PUT 且 value=null =", put_valueless, "（镜像/空写特征）")
print("PUT 且有 value    =", put_with_val)
print("writer 取值 top5  =", writers.most_common(5))

print("\n=== 结论式读数（只陈述我测到的）===")
print(f"writer 有值占比   = {with_writer}/{total} = {(with_writer/total*100 if total else 0):.4f}%")
print("⇒ 「writer 有值者 = 0」在我这份载体上：", "复现 ✅" if with_writer == 0 else f"**未复现** ❌（实测 {with_writer} 条有值）")
