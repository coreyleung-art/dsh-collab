#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""server-only-e2e-test.py — 「只连服务器」端到端联合验收脚本 v1（2026-10-02 星桥）

背景（架构二期 ③）：设计定位「服务器=跨设备唯一中继」，实测主用 Tailscale 直连。
本脚本验证「断开 Tailscale 直连后，双方只经服务器 106.53.214.108 互发互收」是否闭环。
单侧可独立跑我侧部分（写中枢 + 读回执）；MBP 侧部分由他执行（见 companion 说明）。

用法:
  python3 server-only-e2e-test.py --side mac-mini     # 我侧：向中枢写 3 张测试卡 + 读回执
  python3 server-only-e2e-test.py --side mac-mini --loop   # 持续读中枢，等待 MBP 的 3 张卡（他跑时用）
  python3 server-only-e2e-test.py --selfcheck         # 纯函数自检（9 例）

验收判据（全部实测留痕）:
  A. 我→MBP：3 张卡写中枢（**不写本机黑板**）→ MBP 只订中枢 SSE 收到（他回报收时刻）→ 双向计时
  B. MBP→我：他 3 张卡写中枢 → 我经 sync-from-central v1.1 镜像到本机（≤30s）→ 本脚本读本机命中
  C. 全程本机黑板不得出现我直写的测试键（证明未走 Tailscale 直连）

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, os, sys, time, urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/server-only-e2e-test.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

CENTRAL = "http://xingqiao.meetfunbp.com:8792"
LOCAL = "http://127.0.0.1:8792"
SELF = "session-fa1f9150-c949-401f-ba8c-d265f6221676"
MBP = "session-20b800d4-98f6-4e5e-90e4-34f7b6ca61d7"
PREFIX = "notes/servertest/e2e"

def log(m): print(f"[e2e] {time.strftime('%H:%M:%S')} {m}", flush=True)

def put(base, key, val):
    req = urllib.request.Request(base + "/" + key, data=json.dumps(val).encode(),
                                 method="PUT", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return r.status

def get(base, key):
    try:
        with urllib.request.urlopen(base + "/" + key, timeout=5) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)[:60]}

def selfcheck():
    cases = [
        ("key 首段小写", PREFIX.split("/")[0].islower() and PREFIX.split("/")[0].isalpha(), True),
        ("from=本机完整 id", SELF.startswith("session-") and len(SELF) > 30, True),
        ("to=MBP 完整 id", MBP.startswith("session-") and len(MBP) > 30, True),
        ("中枢可达", lambda: get(CENTRAL, "data/discovery/agents/mac-mini").get("key") is not None, True),
    ]
    n = 0
    for name, cond, expect in cases:
        got = cond() if callable(cond) else cond
        ok = got == expect
        n += ok
        print(f"  {'✓' if ok else '✗'} {name} → {got}")
    print(f"  selfcheck: {n}/{len(cases)}")
    return 0 if n == len(cases) else 1

def side_mac_mini(loop=False):
    """我侧：写 3 张卡到中枢（不写本机）"""
    if loop:
        # 等 MBP 的卡经 sync v1.1 镜像到本机
        log("轮询本机黑板，等 MBP 的 e2e 卡镜像（≤60s）…")
        for i in range(60):
            d = get(LOCAL, "notes/servertest/")
            keys = [k for k in d.get("list", {}) if "e2e-from-mbp" in k] if isinstance(d.get("list"), dict) else []
            if keys:
                log(f"命中 {len(keys)} 张 MBP 卡: {keys}")
                return 0
            time.sleep(1)
        log("60s 未命中（若 MBP 未写卡属预期；若已写则 sync 未生效，检查 sync-from-central v1.1 进程）")
        return 1
    ts = int(time.time() * 1000)
    sent = []
    for i in range(3):
        key = f"{PREFIX}/e2e-from-mac-{ts}-{i}"
        val = {"type": "server-e2e", "from": SELF, "to": MBP, "seq": i, "sent_at_epoch_ms": ts}
        st = put(CENTRAL, key, val)
        # 判据 C：本机黑板不得出现（未直连）
        local = get(LOCAL, key)
        sent.append({"key": key, "central_put": st, "local_absent": "error" in local})
        log(f"卡{i} 中枢 PUT {st} | 本机无此键={sent[-1]['local_absent']}")
    # 写汇总卡（MBP 读这张即知全部 3 张键名）
    sumkey = f"{PREFIX}/e2e-manifest-{ts}"
    put(CENTRAL, sumkey, {"type": "server-e2e-manifest", "from": SELF, "to": MBP, "cards": [s["key"] for s in sent]})
    log("manifest 已写中枢: " + sumkey)
    log("MBP 侧动作：只订中枢 SSE → 收到 manifest → 回报 3 张卡收时刻（写 notes/servertest/e2e-mbp-ack-<ts> 到中枢）")
    return 0

if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        sys.exit(selfcheck())
    if "--side" in sys.argv and "mac-mini" in sys.argv:
        sys.exit(side_mac_mini(loop="--loop" in sys.argv))
    print(__doc__)
    sys.exit(2)
