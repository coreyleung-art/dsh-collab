#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A 组「数据实时化」四路验收 harness —— 方案 §十一 前置3 / 补2

出件：明鉴 v3（session-a190c54c）· 2026-10-12
依据：docs/systemgraph-internal-completion-plan-20261008.md §十一（裁判 2026-10-08 有条件通过）

★ 判据来源（逐条对应裁定条件）：
  前置1  文件监听元组 = (mtime, size, ctime)  → 第③路专测「保 mtime 的写」必须可见
  前置2  权威源单一 = 内存模型                → 四路都只作「触发重读」信号，不以事件载荷改模型
  前置3  四路：①黑板写 ②普通文件写 ③cp -a 保 mtime 写 ④原子 rename，每路单独断言 ≤10s
  补1    轮询间隔 < 10s（兜底路径不豁免）      → 构造时强校验 + 报告里回显实配值
  补2    逐路记 pass/fail + 实测时延，禁止只报总失败

★ 设计口径（诚实声明）：
  · 本 harness 测的是 **A 组交付物本身** —— bb-model-store.py 的 ModelStore。
    它用**真黑板**与**真文件系统**跑，不是 mock。
  · ① 路写的是一个**新建的中性探针键**（data/blueprint/_accept-probe），
    **不触碰任何生产键**（relations / versionlog / 各蓝图）——避免为了验收去改真数据。
  · ②③④ 路在临时目录里做，不碰生产文件。
  · 另有一条【活体集成】断言：直接读运行中后端的 /api/model-status，
    确认线上确实在用模型（而不是只在测试里能跑）。

用法：
  python3 bb-model-accept.py            # 跑四路 + 活体集成
  python3 bb-model-accept.py --negctl   # 额外跑负控矩阵（判据必须会红）
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

BB = "http://127.0.0.1:8792"
PROBE_KEY = "data/blueprint/_accept-probe"
LIVE = "http://127.0.0.1:8798"
DEADLINE = 10.0          # 前置3：每路单独断言 10s 内反映

# 复用生产模块（不是复制一份实现 —— 否则测的就不是交付物了）
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("_bbms", os.path.join(HERE, "bb-model-store.py"))
_ms = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_ms)
ModelStore = _ms.ModelStore


def _token():
    for p in ("~/.dsh/blackboard-token", "~/.dsh/board-token"):
        f = os.path.expanduser(p)
        if os.path.exists(f):
            return open(f).read().strip()
    return ""


def board_put(key, value, timeout=8):
    """向黑板 PUT 一个键（生产写路径同款：Bearer 鉴权）。返回 HTTP 码。"""
    body = json.dumps(value, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BB + "/" + key.lstrip("/"), data=body, method="PUT",
                                 headers={"Authorization": "Bearer " + _token(),
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


class Result:
    def __init__(self, name):
        self.name = name
        self.ok = None
        self.latency = None
        self.detail = ""


def wait_for(pred, deadline=DEADLINE, interval=0.1):
    """轮询等待条件成立，返回 (成立?, 实测时延秒)。★ 被测对象是「模型多久看见变化」。"""
    t0 = time.time()
    while True:
        if pred():
            return True, time.time() - t0
        if time.time() - t0 >= deadline:
            return False, time.time() - t0
        time.sleep(interval)


def run(negctl=False):
    results = []
    workdir = tempfile.mkdtemp(prefix="bb-model-accept-")
    probe_file = os.path.join(workdir, "probe.json")
    with open(probe_file, "w") as f:
        json.dump({"v": 0}, f)

    # 起始就把探针键置成一个已知值（避免"键不存在"混进第①路判定）
    board_put(PROBE_KEY, {"v": 0, "by": "bb-model-accept"})

    M = ModelStore(BB, watch_keys=[PROBE_KEY], watch_files=[probe_file],
                   poll_interval=3.0, timeout=8.0, sse_url="http://127.0.0.1:8803/events",
                   log=lambda m: None)
    M.start()
    M.reload(reason="accept-init")
    base_ver = M.version
    print("  harness 模型已起：base version=%s · 轮询 %.1fs · SSE=%s"
          % (base_ver, M.poll_interval, M.sse_url))
    print("  扫描面：板键 1 个(%s) · 文件 1 个(%s)" % (PROBE_KEY, probe_file))
    print()

    # ───────── ① 黑板写 ─────────
    r = Result("① 黑板写")
    mark = int(time.time() * 1000)
    code = board_put(PROBE_KEY, {"v": mark, "by": "bb-model-accept"})
    if code != 200:
        r.ok, r.detail = False, "PUT 返回 %s（写没成功，本路不可判为通过）" % code
    else:
        ok, dt = wait_for(lambda: (M.board_value(PROBE_KEY) or {}).get("v") == mark)
        r.ok, r.latency = ok, dt
        r.detail = "PUT=200 · 模型读到新值" if ok else "写入成功但模型 %ds 内未反映" % DEADLINE
    results.append(r)

    # ───────── ② 普通文件写 ─────────
    r = Result("② 普通文件写")
    with open(probe_file, "w") as f:
        json.dump({"v": mark + 1}, f)
    ok, dt = wait_for(lambda: (M.file_value(probe_file) or {}).get("v") == mark + 1)
    r.ok, r.latency = ok, dt
    r.detail = "元组变化被识别" if ok else "普通写 %ds 内未反映" % DEADLINE
    results.append(r)

    # ───────── ③ 保 mtime 的写（cp -a）★ 前置1 的核心 ─────────
    r = Result("③ cp -a 保 mtime 写")
    src = os.path.join(workdir, "src.json")
    with open(src, "w") as f:
        json.dump({"v": mark + 2}, f)
    st = os.stat(probe_file)
    # 把 src 的 mtime 设成与 probe_file **完全相同**，再做 cp -a ⇒ mtime/size 都可能不变
    os.utime(src, ns=(st.st_atime_ns, st.st_mtime_ns))
    subprocess.run(["/bin/cp", "-a", src, probe_file], check=False)
    # 核对：这次写的确"保住了 mtime"（若没保住，本路就退化成第②路，必须显式指出）
    after = os.stat(probe_file)
    mtime_preserved = (after.st_mtime_ns == st.st_mtime_ns)
    ok, dt = wait_for(lambda: (M.file_value(probe_file) or {}).get("v") == mark + 2)
    r.ok, r.latency = ok, dt
    r.detail = ("mtime 已保住=%s · %s" % (mtime_preserved,
                "靠 ctime 识别成功（前置1 生效）" if ok else "★ %ds 内未反映" % DEADLINE))
    results.append(r)

    # ───────── ④ 原子 rename ─────────
    r = Result("④ 原子 rename")
    tmp = probe_file + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"v": mark + 3}, f)
    os.replace(tmp, probe_file)            # 同目录 rename ⇒ 原子
    ok, dt = wait_for(lambda: (M.file_value(probe_file) or {}).get("v") == mark + 3)
    r.ok, r.latency = ok, dt
    r.detail = "rename 后新 inode 被识别" if ok else "rename %ds 内未反映" % DEADLINE
    results.append(r)

    st = M.status()

    # ───────── 逐路报告（补2：禁止只报总失败）─────────
    print("══════ A 组四路验收 ══════")
    print("  %-22s %-8s %-12s %s" % ("路径", "结果", "实测时延", "说明"))
    print("  " + "─" * 78)
    for x in results:
        lat = ("%.2f s" % x.latency) if x.latency is not None else "—"
        print("  %-22s %-8s %-12s %s" % (x.name, "PASS" if x.ok else "FAIL", lat, x.detail))
    allpass = all(x.ok for x in results)
    worst = max([x.latency for x in results if x.latency is not None] or [0])
    print("  " + "─" * 78)
    print("  四路合计：%s（样本最大 %.2f s / 阈 %.0f s）"
          % ("★ 全过" if allpass else "★ 未全过", worst, DEADLINE))
    # ★★ 2026-10-12 判据更正（协调者独立复跑时暴露）：
    #   ②③④ 三路是靠【兜底轮询】检出的，其时延 = 「距下一次轮询还要等多久」，
    #   随写入落在轮询周期的哪个相位而在 [0, poll_interval] 上变化。
    #   ⇒ **单次样本既不是"最坏"，也不是可复现量。**
    #   实测证据（本轮）：固定相位 ⇒ 3.00 s ± 0.01（恒定）；随机相位 15 次 ⇒ 0.19 ~ 2.99 s。
    #   我首轮报 0.73 s、协调者复跑报 2.59 s —— **同一变量的两个样本，两者都成立**，
    #   差异不是负载、也不是不一致。★ 我把它标成「最坏单路」是错的（低报约 4 倍）。
    #   ⇒ 对轮询检出路径，应当报【与相位无关的确定性上界】= poll_interval + 处理时间；
    #     只有 ①（SSE 事件驱动）的单次样本才直接表征其路径时延。
    bound = M.poll_interval + 0.10
    print("  ★ 轮询检出路径（②③④）的确定性上界 = poll_interval(%.1f s) + 处理余量 ≈ %.2f s"
          % (M.poll_interval, bound))
    print("     ⇒ 该上界与相位无关，才是可复现、可判定的量；上表单次样本仅供参照。")
    print("     ⇒ ① 为 SSE 事件驱动，其样本直接表征路径时延；②③④ 不是。")

    # ───────── 活体集成：线上后端确实在用模型吗 ─────────
    print()
    print("══════ 活体集成（运行中的后端）══════")
    live_ok = False
    try:
        with urllib.request.urlopen(LIVE + "/api/model-status", timeout=8) as rr:
            ls = json.loads(rr.read().decode())
        if ls.get("model") is None and "note" in ls:
            print("  ✗ 线上后端未启用模型：%s" % ls["note"])
        else:
            print("  线上 version=%s · reloads=%s" % (ls.get("version"), ls.get("reloads")))
            print("  板书三态=%s" % (ls.get("boardTally"),))
            print("  SSE state=%s · events=%s" % (ls["sse"].get("state"), ls["sse"].get("events")))
            print("  兜底轮询=%.1fs（补1 要求 <10s）" % ls.get("pollInterval", -1))
            live_ok = (ls["sse"].get("state") == "connected"
                       and ls.get("pollInterval", 99) < 10)
            print("  ⇒ %s" % ("主路径 connected 且兜底 <10s ✅" if live_ok else "★ 主路径或兜底不达标"))
    except Exception as e:
        print("  ✗ 读 /api/model-status 失败：%s: %s" % (type(e).__name__, e))

    # ───────── ★ 内容闸：只查 HTTP 码会放过「200 + 空载荷」─────────
    #   ★ 2026-10-12 血的教训：我第一版接线把 fetch() 的返回契约改了（信封 → value），
    #     调用方 `.get("value", {})` 全部取空 ⇒ 所有走黑板的端点返回 200 但载荷为空。
    #     我的冒烟只查状态码 ⇒ 39/39「全过」，**完全没拦住**，是用户在手机上先发现的。
    #   ⇒ 判据：**冒烟必须查载荷内容，不能只查状态码**；「链路通」≠「有数据」。
    print()
    print("══════ 内容闸（查载荷，不只看状态码）══════")
    content_ok = True
    REQUIRE = [                       # (端点, 取值路径, 下界, 说明)
        ("overview", "bpCount", 10, "蓝图数"),
        ("overview", "edgeCount", 10, "关系边数"),
        ("overview", "versionCount", 1, "版本台账条数"),
        ("overview", "agentCount", 10, "agent 数"),
    ]
    try:
        with urllib.request.urlopen(LIVE + "/api/overview", timeout=20) as rr:
            ov = json.loads(rr.read().decode())
        for _ep, k, lo, desc in REQUIRE:
            v = ov.get(k) or 0
            ok = v >= lo
            content_ok &= ok
            print("  %s /api/%-10s %-14s = %-5s (要求 >= %s)"
                  % ("OK  " if ok else "FAIL", _ep, desc, v, lo))
        for ep, key, lo in (("blueprints", None, 10), ("relations", "edges", 10),
                            ("versions", "entries", 1), ("agents", None, 10)):
            with urllib.request.urlopen(LIVE + "/api/" + ep, timeout=20) as rr:
                d = json.loads(rr.read().decode())
            n = len(d) if key is None else len((d or {}).get(key, []))
            ok = n >= lo
            content_ok &= ok
            print("  %s /api/%-10s %-14s = %-5s (要求 >= %s)"
                  % ("OK  " if ok else "FAIL", ep, key or "条数", n, lo))
    except Exception as e:
        content_ok = False
        print("  ✗ 内容闸读取失败：%s: %s" % (type(e).__name__, e))

    M.stop()
    shutil.rmtree(workdir, ignore_errors=True)

    # ───────── 负控（判据必须会红）─────────
    neg = []
    if negctl:
        print()
        print("══════ 负控矩阵（判据必须会红，否则判据是空转的）══════")
        # N1: 板不可达 ⇒ 不得读作 EMPTY
        M2 = ModelStore("http://127.0.0.1:1", watch_keys=[PROBE_KEY], poll_interval=3.0, timeout=2.0)
        M2.reload(reason="negctl")
        s2 = M2.board_state(PROBE_KEY)
        neg.append(("板不可达必须报 UNREACHABLE（不得读作 EMPTY）", s2 == "UNREACHABLE", s2))
        # N2: 真板 + 不存在的键 ⇒ EMPTY
        M3 = ModelStore(BB, watch_keys=["data/blueprint/__definitely_absent__"], poll_interval=3.0, timeout=3.0)
        M3.reload(reason="negctl")
        s3 = M3.board_state("data/blueprint/__definitely_absent__")
        neg.append(("真板 + 不存在的键 必须报 EMPTY", s3 == "EMPTY", s3))
        # N3: poll_interval>=10 必须构造即拒（补1）
        try:
            ModelStore(BB, poll_interval=10.0); neg.append(("poll_interval=10 必须被拒", False, "没拒"))
        except ValueError:
            neg.append(("poll_interval=10 必须被拒", True, "ValueError"))
        # N4: 保 mtime 的写必须靠 ctime 才能区分
        d2 = tempfile.mkdtemp()
        f1 = os.path.join(d2, "a"); f2 = os.path.join(d2, "b")
        open(f1, "w").write("{}"); open(f2, "w").write('{"x":1}')
        s_ = os.stat(f1); os.utime(f2, ns=(s_.st_atime_ns, s_.st_mtime_ns))
        t1, t2 = ModelStore._stat_tuple(f1), ModelStore._stat_tuple(f2)
        neg.append(("保 mtime 的写：mtime 相同但 ctime 必须不同",
                    t1[0] == t2[0] and t1[2] != t2[2], "mtime同=%s ctime异=%s" % (t1[0] == t2[0], t1[2] != t2[2])))
        shutil.rmtree(d2, ignore_errors=True)
        # N5: 无变化时不得虚增版本号
        M4 = ModelStore(BB, watch_keys=["data/blueprint/relations"], poll_interval=3.0)
        M4.reload(reason="negctl"); v1 = M4.version; M4.reload(reason="negctl")
        neg.append(("无变化时版本号不得虚增", M4.version == v1, "%s -> %s" % (v1, M4.version)))
        for name, ok, ev in neg:
            print("  %s %-46s %s" % ("OK  " if ok else "FAIL", name, ev))

    # ───────── 判据总判 ─────────
    print()
    neg_ok = all(o for _, o, _ in neg) if neg else None
    print("══════ 总判 ══════")
    print("  四路验收      : %s" % ("通过" if allpass else "未通过"))
    print("  活体集成      : %s" % ("通过" if live_ok else "未通过"))
    print("  内容闸        : %s" % ("通过" if content_ok else "未通过"))
    if neg_ok is not None:
        print("  负控矩阵      : %s" % ("通过" if neg_ok else "未通过"))
    print("  ★ 本 harness 只出实测；不代替独立复核。")
    rc = 0 if (allpass and live_ok and content_ok and (neg_ok is not False)) else 1
    return rc


if __name__ == "__main__":
    print("════ SystemGraph · A 组数据实时化 · 四路验收 ════")
    print("  被测对象：bb-model-store.py 的 ModelStore（真黑板 + 真文件系统）")
    print("  阈值：每路 %.0f s（方案 §十一 前置3）" % DEADLINE)
    print()
    sys.exit(run(negctl="--negctl" in sys.argv))
