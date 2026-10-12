# 受控实验（只读，纯内存）：证明 read_alert_cards 对「目标消失」是结构盲的
import importlib.util, sys
spec = importlib.util.spec_from_file_location("bc", "/Users/coreyleung/dsh-collab/tools/beacon-check.py")
m = importlib.util.module_from_spec(spec); sys.modules["bc"] = m; spec.loader.exec_module(m)

print("== 生产 ALERT_DIRS 原样 ==")
print(m.ALERT_DIRS)
for d, r in m.read_alert_cards().items():
    print("  %-38s -> %s" % (d, r))

print()
print("== 负控：把目录名改成【绝不存在】的名字，看读者报什么 ==")
m.ALERT_DIRS = ["data/ops/zzz-audit-does-not-exist-xyz", "data/ops/another-bogus-ns"]
for d, r in m.read_alert_cards().items():
    verdict = "GREEN(0条)" if (r is not None and r[0] == 0) else ("UNDECIDABLE" if r is None else r)
    print("  %-38s -> %s   => %s" % (d, r, verdict))

print()
print("== 对照：用【键形】(无尾斜杠) 探测同一批不存在的名字 ==")
import urllib.request, json
for d in m.ALERT_DIRS + ["data/ops/bus-expired-alert"]:
    url = "http://127.0.0.1:8792/" + d + "/probe-nonexistent-key"
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            print("  %-38s HTTP=%s (键形)" % (d, r.status))
    except urllib.error.HTTPError as e:
        print("  %-38s HTTP=%s (键形) <-- 可与「空」区分" % (d, e.code))
