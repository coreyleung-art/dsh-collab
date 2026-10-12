# 找出「不可判」分支的【真实触发条件】——它到底什么时候才会触发？
import importlib.util, sys
spec = importlib.util.spec_from_file_location("bc", "/Users/coreyleung/dsh-collab/tools/beacon-check.py")
m = importlib.util.module_from_spec(spec); sys.modules["bc"] = m; spec.loader.exec_module(m)

CASES = [
    ("正常板",              None),
    ("板进程挂了（死端口）", "http://127.0.0.1:9"),
    ("超时（黑洞 IP）",      "http://10.255.255.1:8792"),
    ("非 HTTP 服务",        "http://127.0.0.1:8791"),
]
for name, url in CASES:
    r = m.read_alert_cards(board_url=url, timeout=3)
    vals = list(r.values())
    verdict = "UNDECIDABLE(不可判)" if any(v is None for v in vals) else "GREEN/实测"
    print("%-22s -> %-28s => %s" % (name, str(vals)[:28], verdict))
