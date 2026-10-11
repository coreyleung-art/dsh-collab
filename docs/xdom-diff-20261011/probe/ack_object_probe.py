#!/usr/bin/env python3
"""取 cmd_ack **将会**写出的对象，但不落板、不写真台账。
手法：把 put_verified / append_ledger 换成捕获器 ⇒ 观测与写完全分离（E20/E23）。
★ 直接加载**仓库里那份**工具（不复制副本 —— 副本会漂移，见 skill「不落规则副本」同族教训）。
★ 只读板（定位最新一条 log）、只读本机凭据；**不产生任何写入**。"""
import importlib.util, json, sys, os

TOOL = "/Users/coreyleung/dsh-collab/tools/xdom-mail.py"
spec = importlib.util.spec_from_file_location("xm", TOOL)
xm = importlib.util.module_from_spec(spec); spec.loader.exec_module(xm)

captured = {}
def fake_put(key, value, boards=None, timeout=20):
    captured["key"] = key
    captured["value"] = json.loads(json.dumps(value))
    return {"ok": True, "why": None,
            "put": {n: {"http": 200, "err": None} for n, _ in xm.BOARDS},
            "get": {n: {"http": 200, "err": None} for n, _ in xm.BOARDS},
            "match": {n: True for n, _ in xm.BOARDS}}
xm.put_verified = fake_put
xm.append_ledger = lambda rec, path=None: None

sys.argv = ["xdom-mail.py", "ack", "--as", "ext",
            "--cred", os.path.expanduser("~/.dsh/xdom-keys/ext.key"), "--latest"]
rc = xm.main()
print("cmd rc =", rc)
print("捕获到的键 :", captured.get("key"))
print("★ ack 路径将会写出的对象（未落板）:")
print(json.dumps(captured.get("value"), ensure_ascii=False, indent=1))
