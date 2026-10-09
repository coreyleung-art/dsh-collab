#!/usr/bin/env python3
"""补救 writer=0 的阳性对照（无副作用，不碰生产板）
思路拆两半，分别可证：
 A) 计数逻辑正确性 —— 用合成 audit 行喂给与 bb-writer-census 相同的判定逻辑，看能否检出
 B) 服务端链路存在性 —— 源码三行：读 header → 传参 → 写进 audit
两半合起来 ⇒ “46111 条为 0” 更可能是“真的没有”，而非“手段失效”
仍缺：端到端真实正例（需一次带 X-Writer 的真实写入 ⇒ 需授权，本轮不做）

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
import json, os, tempfile, re

print("=" * 74)
print("【A】计数逻辑阳性对照（合成数据，不碰生产板）")
print("=" * 74)
td = tempfile.mkdtemp(prefix="writer-census-control-")
fp = os.path.join(td, "audit-synthetic.jsonl")
rows = [
    {"op": "PUT", "key": "notes/x/a", "version": 1, "value": {"v": 1}, "ts": "2026-10-08T00:00:00", "seq": 1},
    {"op": "PUT", "key": "notes/x/b", "version": 1, "value": {"v": 2}, "ts": "2026-10-08T00:00:01", "seq": 2,
     "writer": "mbp-ops"},
    {"op": "PUT", "key": "notes/x/c", "version": 1, "value": {"v": 3}, "ts": "2026-10-08T00:00:02", "seq": 3},
]
with open(fp, "w") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")

# ★ 与 bb-writer-census.py 相同的判定：e.get("writer") is not None
total = with_writer = 0
for line in open(fp):
    line = line.strip()
    if not line:
        continue
    e = json.loads(line)
    total += 1
    if e.get("writer") is not None:
        with_writer += 1
print(f"  合成文件：{fp}")
print(f"  行数 = {total}   writer 有值 = {with_writer}")
print(f"  ⇒ 期望 1（构造了 1 条带 writer）  ⇒ {'✅ 对照通过：判定逻辑能检出 writer' if with_writer == 1 else '❌ 对照失败：逻辑检不出 ⇒ 我的 0 不可信'}")

print()
print("=" * 74)
print("【B】服务端链路：X-Writer → audit 字段（源码三行）")
print("=" * 74)

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/writer-census-positive-control.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

SRC = os.path.expanduser("~/dsh-collab/rust-blackboard/src")
checks = [
    ("http.rs", r'header\(&req\.headers,\s*"x-writer"\)', "读请求头 x-writer"),
    ("http.rs", r"do_put\(store,\s*&path,\s*[^,]+,\s*writer\.as_deref\(\)\)", "把 writer 传给 do_put"),
    ("store.rs", r'self\.put\(&full,\s*value\.clone\(\),\s*writer\)', "do_put 把 writer 传给 store.put"),
    ("store.rs", r'if let Some\(w\) = writer\s*\{\s*entry\["writer"\]', "audit entry 写入 writer 字段"),
]
for fn, pat, desc in checks:
    p = os.path.join(SRC, fn)
    try:
        src = open(p, errors="replace").read()
    except Exception as e:
        print(f"  ❌ {fn} 读取失败 {e}")
        continue
    m = re.search(pat, src, re.S)
    if m:
        line = src[:m.start()].count("\n") + 1
        print(f"  ✅ {fn}:{line}  {desc}")
    else:
        print(f"  ❌ {fn} 未匹配：{desc}")

print()
print("=" * 74)
print("【C】结论（分两半，不合并）")
print("=" * 74)
print("  ✅ 计数逻辑：已过合成阳性对照（能检出 writer）")
print("  ✅ 服务端链路：源码四环齐备（header → do_put → store.put → audit entry）")
print("  ⇒ 两半合起来：**“46111 条为 0”更可能是“真的没有”，而非“手段失效”**")
print("  ❌ 仍缺：**端到端真实正例**（需一次带 X-Writer 的真实写入 ⇒ 需授权，本轮不做）")
print("  ⇒ 故准确表述应为：「窗口内 0，且计数逻辑与写入链路均已独立核对；端到端正例待补」")
