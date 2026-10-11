#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SystemGraph · A 组「数据实时化」—— 单一权威内存模型 + 三态取数 + 版本号

出件：明鉴 v3（session-a190c54c）· 2026-10-12 · 主源架构师
依据：docs/systemgraph-internal-completion-plan-20261008.md §十一（裁判 2026-10-08 有条件通过）

★ 裁定条件逐条落实位置：
  · 前置1 文件监听元组 = (mtime, size, ctime) ......... `ST._stat_tuple()`
      为什么必须有 ctime：`cp -a`/`cp -p`/`rsync -a` 会**保留 mtime**，
      但 **ctime（inode 变更时间）无法被保留** ⇒ 只盯 mtime 的监听对这类静默写失明。
  · 前置2 权威源单一 = 本模块的内存模型 ............... `ModelStore`
      文件变更与 SSE 事件 **只作「触发重读」信号**，**不以事件载荷直接改模型**
      （SSE 只用来触发 `reload()`；模型内容一律由重读源得到）。
  · 前置3 四路验收：黑板写 / 普通文件写 / cp -a 保 mtime 写 / 原子 rename
      —— 本模块只提供被验收的装置；验收编排见 `bb-model-accept.py`
  · 补1 轮询间隔 < 10s（含兜底路径）..................... `poll_interval` 默认 3.0s
      ★ 主路径事件驱动 ≠ 兜底路径免约束：SSE 与轮询**各自独立**且**都 < 10s**。
  · 补2 逐路记 pass/fail + 实测时延 ..................... 由 `bb-model-accept.py` 记录

★ 本模块同时修掉一个既有缺陷（实测 2026-10-12）：
  原 `bb-blueprint-gallery.py:fetch()` 是 `except Exception: return {}` ——
  **黑板不可达时静默返回空**，与「板上有这个键但内容为空」**不可区分**。
  本模块用三态（OK / EMPTY / UNREACHABLE）显式区分，并由 `/api/model-status` 暴露。
  判据：空 ≠ 无；不可判 ≠ 不成立。
"""

import json
import os
import threading
import time
import urllib.error
import urllib.request

# ── 三态（★ 不允许把 UNREACHABLE 读作 EMPTY） ──
OK = "OK"
EMPTY = "EMPTY"
UNREACHABLE = "UNREACHABLE"

# 监听哪一"面"：只记录状态迁移，不参与判定
_EPOCH = time.time()


class ModelStore:
    """单一权威内存模型。

    用法（后端）：
        M = ModelStore(BB, AGENTS_FILE, watch_keys=[...], watch_files=[...])
        M.start()
        v = M.board_value("data/blueprint/relations")   # 取缓存值，不再每次打 HTTP
        st = M.status()                                  # /api/model-status 的载荷
    """

    def __init__(self, bb_url, watch_keys=None, watch_files=None,
                 poll_interval=3.0, timeout=6.0, sse_url=None, log=None):
        if poll_interval >= 10.0:
            # 补1：轮询是兜底路径，兜底路径同样须 <10s，不因主路径事件驱动而豁免
            raise ValueError("poll_interval 必须 < 10s（补1：兜底路径不豁免）")
        self.bb_url = bb_url.rstrip("/")
        self.poll_interval = float(poll_interval)
        self.timeout = float(timeout)
        # SSE 是主路径（事件驱动）；poll 是兜底路径。两者独立，互不豁免。
        self.sse_url = sse_url or ""
        self.log = log or (lambda *_a, **_k: None)

        self.watch_keys = list(watch_keys or [])
        self.watch_files = list(watch_files or [])

        self._lk = threading.RLock()
        self._board = {}      # key       -> {"state","value","version","detail","seenAt"}
        self._files = {}      # path      -> {"state","tuple","value","detail","seenAt"}
        self._version = 0     # ★ 版本号：任一路（板/文件）发生变化即自增
        self._reloads = 0
        self._last_change = None
        self._last_poll = None
        self._changed = []

        # 事件驱动的触发计数 + SSE 状态（供 status 如实上报"哪条路径在工作"）
        self._sse_state = "disabled" if not self.sse_url else "init"
        self._sse_events = 0
        self._sse_error = ""
        self._stop = threading.Event()
        self._threads = []

    # ─────────────────────────── 源读取（三态） ───────────────────────────
    @staticmethod
    def _stat_tuple(path):
        """前置1：文件监听元组 = (mtime, size, ctime)。

        ★ ctime 是这一条的关键：`cp -a` 保留 mtime、保留 size，
          但 **ctime 一定会变**（inode 元数据被改写，且 ctime 不可被用户态设置）。
          ⇒ 只比 (mtime, size) 会漏掉「保 mtime 的静默写」。
        """
        try:
            st = os.stat(path)
            return (st.st_mtime_ns, st.st_size, st.st_ctime_ns)
        except OSError:
            return None

    def _read_board(self, key):
        """读黑板一个键。返回 (state, payload)。

        ★ 三态严肃区分：HTTP 404 ⇒ EMPTY（板可达，键不存在）；
          任何异常 ⇒ UNREACHABLE（**不可判**，不得读作 EMPTY）。
        """
        url = self.bb_url + "/" + key.lstrip("/")
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as r:
                obj = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return EMPTY, {"value": None, "version": None, "detail": "HTTP 404"}
            return UNREACHABLE, {"value": None, "version": None, "detail": "HTTP %s" % e.code}
        except Exception as e:
            return UNREACHABLE, {"value": None, "version": None,
                                 "detail": "%s: %s" % (type(e).__name__, e)}
        if not isinstance(obj, dict):
            return UNREACHABLE, {"value": None, "version": None, "detail": "非对象响应"}
        val = obj.get("value")
        # 板可达但值为空 ⇒ EMPTY（这是"真无"，与不可达是两件事）
        state = OK if val not in (None, "", {}, []) else EMPTY
        return state, {"value": val, "version": obj.get("version"),
                       "ts": obj.get("ts"), "detail": ""}

    # ─────────────────────────── 重读（唯一改模型的入口） ───────────────────────────
    def reload(self, reason="poll"):
        """重读所有源，按差异更新模型并自增版本号。

        ★ 前置2：**只有这里**能改模型。SSE 事件、文件监听、轮询都只是"叫这里一声"，
          绝不携带足以直接改模型的载荷。
        """
        changed = []
        now = time.time()
        with self._lk:
            for k in self.watch_keys:
                state, payload = self._read_board(k)
                prev = self._board.get(k)
                pb = (prev or {}).get("boardVersion")
                if (prev is None
                        or state != prev.get("state")
                        or payload.get("version") != pb):
                    changed.append({"kind": "board", "key": k,
                                    "from": (prev or {}).get("state"), "to": state})
                    payload["state"] = state
                    payload["boardVersion"] = payload.get("version")
                    payload["seenAt"] = now
                    payload["reason"] = reason
                    self._board[k] = payload
            for p in self.watch_files:
                tup = self._stat_tuple(p)
                prev = self._files.get(p)
                if prev is None or tup != prev.get("tuple"):
                    if tup is None:
                        state, val = EMPTY, None
                    else:
                        state, val = OK, self._load_json(p)
                    changed.append({"kind": "file", "path": p,
                                    "from": (prev or {}).get("state"), "to": state})
                    self._files[p] = {"state": state, "tuple": tup, "value": val,
                                      "seenAt": now, "reason": reason}
            self._last_poll = now
            if changed:
                self._version += 1
                self._reloads += 1
                self._last_change = now
                self._changed = changed
        return changed

    @staticmethod
    def _load_json(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    # ─────────────────────────── 取数（模型侧，不再打网络） ───────────────────────────
    def board_value(self, key, default=None):
        """取黑板键的模型值。★ 语义与旧 fetch() 的差异：这里不吞"不可达"。

        调用方可只取 value（兼容旧签名），但要判"到底是空还是不可达"就用 board_state()。
        """
        with self._lk:
            rec = self._board.get(key)
        if not rec:
            return default
        return rec.get("value") if rec.get("value") is not None else default

    def board_envelope(self, key):
        """返回与黑板**原始响应同形**的信封 {key, ts, value, version(, state)}。

        ★★ 为什么必须有这个方法（2026-10-12 实测事故）：
          调用方（bb-blueprint-gallery 的 get_registry / get_relations / get_versions）
          是按【信封】解包的 —— 它们写的是 `fetch(key).get("value", {})`。
          而 `fetch()` 改造前返回的就是黑板原始响应（信封）。
          我第一版改造让 fetch() 直接返回**已解包的 value** ⇒ 调用方 `.get("value")`
          在 value 里找不到 "value" 键 ⇒ 静默得到 {} ⇒ **所有走黑板的端点全空**
          （bpCount/edgeCount/versionCount 全 0、blueprints/relations/entries 全 []）。
          ★ 而我的冒烟测试只查 HTTP 状态码（200 + 空载荷照样通过）⇒ 没拦住。
          ⇒ 结论：**改函数返回契约时，必须核所有调用点的解包方式**；
             **冒烟必须查载荷内容，不能只查状态码**。
        """
        with self._lk:
            rec = self._board.get(key)
        if not rec:
            return {}
        return {"key": key, "ts": rec.get("ts"),
                "value": rec.get("value"), "version": rec.get("boardVersion"),
                # state 是额外字段（旧契约没有），便于调用方判三态；不影响旧解包
                "state": rec.get("state")}

    def board_state(self, key):
        with self._lk:
            rec = self._board.get(key)
        return (rec or {}).get("state") or "UNWATCHED"

    def file_value(self, path, default=None):
        with self._lk:
            rec = self._files.get(path)
        if not rec:
            return default
        return rec.get("value") if rec.get("value") is not None else default

    def file_state(self, path):
        with self._lk:
            rec = self._files.get(path)
        return (rec or {}).get("state") or "UNWATCHED"

    @property
    def version(self):
        with self._lk:
            return self._version

    # ─────────────────────────── 兜底路径：轮询 ───────────────────────────
    def _poll_loop(self):
        # 兜底路径独立于 SSE：SSE 死了它照样把变更捞回来（这正是它存在的理由）
        while not self._stop.wait(self.poll_interval):
            try:
                self.reload(reason="poll")
            except Exception as e:
                self.log("model poll 异常: %s: %s" % (type(e).__name__, e))

    # ─────────────────────────── 主路径：SSE 订阅 ───────────────────────────
    def _sse_loop(self):
        """订阅黑板 SSE。★ 只做一件事：收到任何事件就叫一次 reload()。

        不以事件载荷改模型（前置2）。断连按指数退避重连，但**不超过 poll_interval 的
        兜底能力**——因为兜底路径一直在跑，所以断了也不丢变更，只是退回轮询粒度。
        """
        backoff = 1.0
        while not self._stop.is_set():
            try:
                req = urllib.request.Request(self.sse_url, headers={"Accept": "text/event-stream"})
                with urllib.request.urlopen(req, timeout=90) as r:
                    self._sse_state = "connected"
                    self._sse_error = ""
                    self.log("SSE 已订阅 %s" % self.sse_url)
                    backoff = 1.0
                    for raw in r:
                        if self._stop.is_set():
                            break
                        line = raw.decode("utf-8", "replace").strip()
                        if not line or line.startswith(":"):
                            continue
                        # 事件载荷只用来"叫一声"，不入模型
                        if line.startswith("data:"):
                            self._sse_events += 1
                            self.reload(reason="sse")
            except Exception as e:
                self._sse_state = "disconnected"
                self._sse_error = "%s: %s" % (type(e).__name__, e)
                self.log("SSE 断开(%s)，%.1fs 后重连（兜底轮询仍在跑）" % (self._sse_error, backoff))
            if self._stop.is_set():
                break
            self._stop.wait(backoff)
            backoff = min(backoff * 2, 30.0)

    # ─────────────────────────── 生命周期 ───────────────────────────
    def start(self):
        self.reload(reason="init")          # 初始化时由源全量加载（前置2）
        t1 = threading.Thread(target=self._poll_loop, name="model-poll", daemon=True)
        t1.start()
        self._threads.append(t1)
        if self.sse_url:
            t2 = threading.Thread(target=self._sse_loop, name="model-sse", daemon=True)
            t2.start()
            self._threads.append(t2)
        return self._version

    def stop(self):
        self._stop.set()

    def touch(self, reason="external"):
        """外部（如文件监听器）请求一次重读。★ 只触发，不传值。"""
        return self.reload(reason=reason)

    def add_watch(self, key):
        """把一个先前未纳入的黑板键加入监听面（下一次 reload 生效）。

        用途：`fetch()` 遇到未监听的键时，先按旧路径取一次值保证不空窗，
        同时把它登记进来，使得**后续请求就不再打网络**（收敛而非长期双轨）。
        """
        k = key.lstrip("/")
        with self._lk:
            if k not in self.watch_keys:
                self.watch_keys.append(k)
                return True
        return False

    # ─────────────────────────── 自述 ───────────────────────────
    def status(self):
        with self._lk:
            board = {k: {"state": v.get("state"), "boardVersion": v.get("boardVersion"),
                         "detail": v.get("detail", ""), "reason": v.get("reason")}
                     for k, v in self._board.items()}
            files = {p: {"state": v.get("state"),
                         "tuple": list(v["tuple"]) if v.get("tuple") else None,
                         "reason": v.get("reason")}
                     for p, v in self._files.items()}
            n_ok = sum(1 for v in board.values() if v["state"] == OK)
            n_empty = sum(1 for v in board.values() if v["state"] == EMPTY)
            n_unreach = sum(1 for v in board.values() if v["state"] == UNREACHABLE)
            return {
                "version": self._version,
                "reloads": self._reloads,
                "lastChange": self._last_change,
                "lastPoll": self._last_poll,
                "pollInterval": self.poll_interval,
                "uptime": time.time() - _EPOCH,
                "board": board,
                "boardTally": {"OK": n_ok, "EMPTY": n_empty, "UNREACHABLE": n_unreach,
                               "watched": len(board)},
                "files": files,
                "sse": {"state": self._sse_state, "events": self._sse_events,
                        "error": self._sse_error, "url": self.sse_url},
                "lastChanged": self._changed,
            }


# ─────────────────────────── 自检（正负控） ───────────────────────────
def _selftest():
    """★ 负控必红项：判据不能只测"能跑"，要测"错了会不会红"。"""
    fails = []

    def ck(name, cond, detail=""):
        print("  %s %s %s" % ("OK " if cond else "FAIL", name, detail))
        if not cond:
            fails.append(name)

    # ① 补1：轮询必须是 <10s，否则构造即拒
    try:
        ModelStore("http://127.0.0.1:8792", poll_interval=10.0)
        ck("负控 poll_interval=10.0 应被拒", False, "没拒")
    except ValueError:
        ck("负控 poll_interval=10.0 被拒", True)
    try:
        M0 = ModelStore("http://127.0.0.1:8792", poll_interval=3.0)
        ck("正控 poll_interval=3.0 通过", True)
    except Exception as e:
        ck("正控 poll_interval=3.0 通过", False, str(e))

    # ② 前置1：元组必须是三元且含 ctime —— 用「保 mtime 的写」做负控
    import tempfile
    d = tempfile.mkdtemp()
    fp = os.path.join(d, "t.json")
    with open(fp, "w") as f:
        f.write('{"a":1}')
    t1 = ModelStore._stat_tuple(fp)
    ck("元组是三元素", isinstance(t1, tuple) and len(t1) == 3, str(t1))
    st = os.stat(fp)
    # 造一个「mtime 不变、内容变」的写：写新文件再 os.utime 回旧 mtime
    fp2 = os.path.join(d, "t2.json")
    with open(fp2, "w") as f:
        f.write('{"a":2}')
    os.utime(fp2, ns=(st.st_atime_ns, st.st_mtime_ns))
    t2 = ModelStore._stat_tuple(fp2)
    ck("保 mtime 的写：mtime 相同", t1[0] == t2[0], "mtime %s vs %s" % (t1[0], t2[0]))
    ck("保 mtime 的写：★ ctime 必须能区分", t1[2] != t2[2],
       "ctime %s vs %s" % (t1[2], t2[2]))
    import shutil
    shutil.rmtree(d, ignore_errors=True)

    # ③ 三态：不可达不得读作空
    M = ModelStore("http://127.0.0.1:8792", watch_keys=["definitely/not/a/real/key/xyz"],
                   poll_interval=3.0, timeout=3.0)
    M.reload(reason="selftest")
    s = M.board_state("definitely/not/a/real/key/xyz")
    ck("404 ⇒ EMPTY（板可达但键不在）", s == EMPTY, s)

    M2 = ModelStore("http://127.0.0.1:1", watch_keys=["data/blueprint/relations"],
                    poll_interval=3.0, timeout=2.0)
    M2.reload(reason="selftest")
    s2 = M2.board_state("data/blueprint/relations")
    ck("★ 板不可达 ⇒ UNREACHABLE（不得读作 EMPTY）", s2 == UNREACHABLE, s2)
    # ★ 语义说明：version 记的是「模型状态发生过几次迁移」，不是「成功加载过几次」。
    #   从「无记录」到「UNREACHABLE」也是一次迁移 ⇒ 这里 version==1 是【正确】的，
    #   不代表取到了数据。判「到底有没有数据」要看 board_state()，不看 version。
    ck("状态迁移也计数 ⇒ 首次 reload 后 version=1（不代表有数据）",
       M2.version == 1, "version=%s board_state=%s" % (M2.version, s2))

    # ④ 真板：可达且能取到值 + 版本号只在变化时自增
    M3 = ModelStore("http://127.0.0.1:8792",
                    watch_keys=["data/blueprint/relations"], poll_interval=3.0)
    M3.reload(reason="selftest")
    ck("真板 relations 状态 = OK", M3.board_state("data/blueprint/relations") == OK,
       M3.board_state("data/blueprint/relations"))
    ck("真板 relations 取到值", isinstance(M3.board_value("data/blueprint/relations"), dict))
    v1 = M3.version
    M3.reload(reason="selftest")
    ck("无变化时不虚增版本号", M3.version == v1, "%s -> %s" % (v1, M3.version))
    st3 = M3.status()
    ck("status 三态计数自洽",
       st3["boardTally"]["OK"] + st3["boardTally"]["EMPTY"]
       + st3["boardTally"]["UNREACHABLE"] == st3["boardTally"]["watched"],
       str(st3["boardTally"]))

    print("\n%s" % ("全部通过 (%d)" % 0 if not fails else "失败项: %s" % ", ".join(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)
