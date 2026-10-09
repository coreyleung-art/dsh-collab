#!/usr/bin/env python3
"""独立复核独立复核员的两个地平线公式与比值
他给：audit 地平线 = 10×5MB ÷ (rate × mean)；timeline 地平线 = 20000 ÷ rate
      ⇒ 两者之比 = mean ÷ 2621 B
实测参数（他）：10 份归档 50.0MB / 20941 条 ⇒ mean ≈ 2505 B ⇒ 比值 0.96

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
import os, glob, json

DD = os.path.expanduser("~/dsh-collab/token-monitor/blackboard")
files = sorted(glob.glob(os.path.join(DD, "audit-*.jsonl")))   # 只算轮转归档（10 份）
tot_b = 0
tot_n = 0
for f in files:
    tot_b += os.path.getsize(f)
    with open(f, errors="replace") as fh:
        tot_n += sum(1 for l in fh if l.strip())

mean = tot_b / tot_n if tot_n else 0
print("=== 实测参数 ===")
print(f"  轮转归档份数 = {len(files)}")
print(f"  总字节 = {tot_b} = {tot_b/1048576:.2f} MB")
print(f"  总条数 = {tot_n}")
print(f"  ★ 平均条目 = {mean:.1f} B     （他称 ≈2505 B）")

CAP = 10 * 5 * 1024 * 1024
TL = 20000
K = TL / CAP
print(f"\n=== 比值推导 ===")
print(f"  20000 / (10×5MB) = {K:.8f}  ⇒  1/K = {1/K:.1f} B")
print(f"  ⇒ 比值 = mean ÷ {1/K:.1f} B = {mean/(1/K):.4f}     （他称 0.96）")

print("\n=== 反推（若 mean=2505）===")
print(f"  比值 = 2505 / {1/K:.1f} = {2505/(1/K):.4f}")

print("\n=== 速率相关 ===")
for rate, label in ((71.1, "他实测（seq 解码当前窗口）"), (105.0, "他上轮用的代理值")):
    a = CAP / (rate * mean) / 3600
    t = TL / rate / 60
    print(f"  rate={rate:>6} /min ({label}): audit 地平线 = {a:.2f}h · timeline 地平线 = {t:.2f}h")
print("\n  ⇒ 同一 mean 下，rate 越高两条都越短；audit 还额外受 mean 放大")
print("  ⇒ 他称 'storm 后 ≈97min' 应可用 rate 反算：")
for rate in (105.0, 150.0):
    rem = TL - 13205
    print(f"     rate={rate}: 剩余 {rem} 事件 ÷ {rate} = {rem/rate:.1f} min（他说 95.6min ⇒ 对应 rate≈71.1）")
