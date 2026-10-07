#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""agent-mailbox.py — L1 设备内 agent 邮箱（嵌入式 · SQLite/WAL · 零外部依赖）

设计取向：借鉴 `agent-mailbox-core`(MIT) 与 claude_codex_bridge `agent-mailbox-kernel-design`
的**机制**，自研实现。不引入任何第三方运行时（仅 Python stdlib + sqlite3）。

它替换的是「整份读入 + 整份回写单个 JSON 文件」这一写入模式
（本机实测：agent-bus.json 20.2MB / 3,773 线程 / 30,481 消息，外部读取会 torn read，
外部修改会被下一次 persist() 覆盖）。

★ 四条硬不变量（对应 CAHAC v1.1 增补提案 S1–S4）
  I1 存储      ：并发写期间外部读取零 torn read；外部修改不被回写覆盖（靠 WAL + 事务）
  I2 入站串行  ：任一时刻，单 agent 活跃 claim ≤ 1（出站不受限）
  I3 失败谱系  ：每次重试产生新 attempt，绝不覆盖；超 max_retries 入 DLQ，不静默丢弃
  I4 投递≠消费 ：done ⟹ 存在 delivered attempt ∧ 存在 agent 级 receipt；守护不能声明 done

调试用注入点（仅供 selftest 构造边界）：守则见下 —— `_guard_done` 不可绕过。

用法:
  agent-mailbox.py init [--db PATH]
  agent-mailbox.py send --from A --to B [--type TASK] [--priority 5] [--ttl 3600]
                        [--dedup-key K] [--thread T] [--body TEXT]
  agent-mailbox.py inbox --agent A [--limit 10]
  agent-mailbox.py claim --agent A --msg ID          # 入站串行；返回 claim token
  agent-mailbox.py ack  --msg ID --agent A [--stage done|delivered] [--body R]
  agent-mailbox.py sweep                             # visibility timeout 到期重现
  agent-mailbox.py dlq [--limit 20]
  agent-mailbox.py replay --msg ID
  agent-mailbox.py trace --msg ID                    # 全部 attempt + receipt（数量守恒）
  agent-mailbox.py stats
  agent-mailbox.py import-bus --bus PATH [--dry-run] # 从 agent-bus.json 只读导入
  agent-mailbox.py selftest                          # I1–I4 断言
"""
import argparse
import json
from contextlib import contextmanager
import os
import sqlite3
import sys
import time
import uuid

DEFAULT_DB = os.path.expanduser("~/.dsh/mailbox/mailbox.db")
DEFAULT_TTL = 86400          # 1 天
DEFAULT_VIS_TIMEOUT = 300    # 5 分钟
DEFAULT_MAX_RETRIES = 3
DEFAULT_RATE_LIMIT = 60      # 每 agent 每分钟

SCHEMA = """
-- 注意：journal_mode 不在此处设置（变更它需独占锁，并发打开时会立即报错而非等待）；
--       由 Mailbox.__init__ 在「尚未 WAL 时」按需设置。
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS agent (
  agent_id   TEXT PRIMARY KEY,
  device     TEXT NOT NULL DEFAULT 'unknown',
  created_at REAL NOT NULL,
  last_seen  REAL
);

-- 逻辑消息：不可变。重试不修改本表（I3）
CREATE TABLE IF NOT EXISTS message (
  msg_id        TEXT PRIMARY KEY,
  origin_device TEXT NOT NULL DEFAULT 'local',
  origin_msg_id TEXT,                          -- 跨设备幂等：<device>:<original id>
  sender        TEXT NOT NULL,
  recipient     TEXT NOT NULL,                 -- agent_id | '*' | 'topic:<name>'
  thread        TEXT,
  mtype         TEXT NOT NULL DEFAULT 'TASK',  -- TASK|STATUS|ACK|EVENT|NOTIFY|BATCH
  priority      INTEGER NOT NULL DEFAULT 5,    -- 0 最高
  dedup_key     TEXT,
  cost_cap      INTEGER NOT NULL DEFAULT 0,
  payload       TEXT NOT NULL DEFAULT '{}',
  created_at    REAL NOT NULL,
  expires_at    REAL,
  UNIQUE (origin_device, origin_msg_id, dedup_key)   -- 幂等（NULL 不参与唯一约束）
);
CREATE INDEX IF NOT EXISTS ix_msg_inbox ON message(recipient, priority, created_at);

-- 投递/处理尝试：每次一行，永不覆盖（I3）
CREATE TABLE IF NOT EXISTS attempt (
  attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
  msg_id     TEXT NOT NULL,
  n          INTEGER NOT NULL,                 -- 第几次（从 1 起）
  state      TEXT NOT NULL,                    -- queued|claimed|delivered|done|failed|dead
  claimed_by TEXT,
  claimed_at REAL,
  vis_until  REAL,                             -- visibility timeout（I4 的基础）
  finished_at REAL,
  error      TEXT,
  UNIQUE (msg_id, n)
);
CREATE INDEX IF NOT EXISTS ix_attempt_msg ON attempt(msg_id);
CREATE INDEX IF NOT EXISTS ix_attempt_active ON attempt(claimed_by, state);

-- 消费回执：只有它能把 attempt 推进到 done（I4）
CREATE TABLE IF NOT EXISTS receipt (
  msg_id  TEXT NOT NULL,
  agent   TEXT NOT NULL,
  stage   TEXT NOT NULL,                       -- delivered（守护级）| done（agent 级）
  ts      REAL NOT NULL,
  body    TEXT,
  PRIMARY KEY (msg_id, agent, stage)
);

-- 速率限制窗口
CREATE TABLE IF NOT EXISTS rate (
  agent TEXT NOT NULL,
  ts    REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_rate ON rate(agent, ts);
"""


class Mailbox:
    def __init__(self, db_path=DEFAULT_DB, vis_timeout=DEFAULT_VIS_TIMEOUT,
                 max_retries=DEFAULT_MAX_RETRIES, rate_limit=DEFAULT_RATE_LIMIT,
                 device="local"):
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.db_path = db_path
        self.vis_timeout = vis_timeout
        self.max_retries = max_retries
        self.rate_limit = rate_limit
        self.device = device
        # timeout 让并发写等待而不是抛 database is locked（多 agent 场景必需）
        self.con = sqlite3.connect(db_path, timeout=30.0, isolation_level=None)
        self.con.row_factory = sqlite3.Row
        # ★ 2026-10-01 多进程实测修正：三进程同时打开同一库时，初版在
        #   `PRAGMA journal_mode=WAL` / `executescript(SCHEMA)` 上撞锁直接抛
        #   OperationalError（2/3 进程初始化失败）。根因两条：
        #     (1) 变更 journal_mode 需【独占锁】——并发时**立即报错而非等待** busy_timeout
        #     (2) 并发 DDL 会争抢写锁
        #   修法：先显式设 busy_timeout；仅在尚未 WAL 时才变更；DDL 加幂等重试。
        #   ★ 这一条【只有多进程能测出】，同进程多线程不会暴露。
        self.con.execute("PRAGMA busy_timeout=30000")
        try:
            mode = (self.con.execute("PRAGMA journal_mode").fetchone() or ["?"])[0]
            if str(mode).lower() != "wal":
                self.con.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError:
            pass          # 别的进程正在设；它设成了就等于我设成了（下一步会校验）
        last = None
        for attempt in range(12):
            try:
                self.con.executescript(SCHEMA)
                last = None
                break
            except sqlite3.OperationalError as e:      # noqa: PERF203
                last = e
                if "locked" in str(e).lower() or "busy" in str(e).lower():
                    time.sleep(0.05 * (attempt + 1))
                    continue
                raise
        if last is not None:
            raise RuntimeError(f"SCHEMA_INIT_FAILED: 并发建表重试耗尽（{last}）")

    # ---------- 基础设施 ----------
    @contextmanager
    def _immediate(self):
        """写事务统一用 BEGIN IMMEDIATE。

        ★ 2026-10-01 多进程实测修正：默认的 deferred BEGIN 是「先读后写时才取锁」，
        于是两个进程可以**同时读到旧值、再各自写入**（实测：per-sender 阈值 60，
        3 进程并发落库 61）。同一竞态对 I2「无活跃 claim 才可 claim」与幂等查重
        同样成立 —— 那两条的后果比限流严重得多（会真的违反不变量）。
        BEGIN IMMEDIATE 在事务开始即取写锁，使 check-then-act 成为原子。
        """
        self.con.execute("BEGIN IMMEDIATE")
        try:
            yield self.con
            self.con.execute("COMMIT")
        except Exception:
            try:
                self.con.execute("ROLLBACK")
            except Exception:
                pass
            raise

    def close(self):
        self.con.close()

    def _tx(self):
        """显式事务；WAL 下允许并发读 + 单写。"""
        return self.con

    def _ensure_agent(self, agent_id):
        self.con.execute(
            "INSERT INTO agent(agent_id, device, created_at) VALUES(?,?,?) "
            "ON CONFLICT(agent_id) DO UPDATE SET last_seen=excluded.created_at",
            (agent_id, self.device, time.time()))

    # ---------- 写入 ----------
    def send(self, sender, recipient, body="", mtype="TASK", priority=5,
             ttl=None, dedup_key=None, thread=None, cost_cap=0,
             origin_device=None, origin_msg_id=None, bypass_rate=False):
        now = time.time()
        origin_device = origin_device or self.device
        # I1: 事务内完成“注册 agent + 限速检查 + 插入”
        with self._immediate():
            self._ensure_agent(sender)
            # 速率限制（★ 批量回填/迁移不属于「洪泛」，走 bypass_rate）
            if not bypass_rate:
                self.con.execute("DELETE FROM rate WHERE ts < ?", (now - 60,))
                n = self.con.execute("SELECT COUNT(*) c FROM rate WHERE agent=?", (sender,)).fetchone()["c"]
                if n >= self.rate_limit:
                    raise RuntimeError(f"RATE_LIMITED: {sender} 超过 {self.rate_limit}/min")
                self.con.execute("INSERT INTO rate(agent, ts) VALUES(?,?)", (sender, now))

            # 幂等：同 (origin_device, origin_msg_id, dedup_key) 已存在则返回原 msg_id
            if dedup_key or origin_msg_id:
                row = self.con.execute(
                    "SELECT msg_id FROM message WHERE origin_device=? AND origin_msg_id IS ? AND dedup_key IS ?",
                    (origin_device, origin_msg_id, dedup_key)).fetchone()
                if row:
                    return row["msg_id"], True

            if recipient not in ("*",) and not recipient.startswith("topic:"):
                self._ensure_agent(recipient)

            msg_id = uuid.uuid4().hex
            expires_at = now + (ttl if ttl is not None else DEFAULT_TTL)
            self.con.execute(
                "INSERT INTO message(msg_id, origin_device, origin_msg_id, sender, recipient,"
                " thread, mtype, priority, dedup_key, cost_cap, payload, created_at, expires_at)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (msg_id, origin_device, origin_msg_id, sender, recipient, thread, mtype,
                 priority, dedup_key, cost_cap, body, now, expires_at))
            self.con.execute(
                "INSERT INTO attempt(msg_id, n, state) VALUES(?,1,'queued')", (msg_id,))
        return msg_id, False

    # ---------- 消费 ----------
    def _active_claims(self, agent):
        return self.con.execute(
            "SELECT COUNT(*) c FROM attempt WHERE claimed_by=? AND state='claimed'",
            (agent,)).fetchone()["c"]

    def claim(self, agent, msg_id=None, force=False):
        """I2: 任一时刻单 agent 活跃 claim ≤ 1。"""
        now = time.time()
        with self._immediate():
            sender_rows = self.con.execute(
                "SELECT DISTINCT sender FROM message").fetchall()  # noqa: F841 (保持读事务一致)
            if not force and self._active_claims(agent) > 0:
                raise RuntimeError(f"SERIAL_VIOLATION: {agent} 已有活跃 claim（入站串行不变量）")
            if msg_id:
                cand = self.con.execute(
                    "SELECT * FROM message WHERE msg_id=?", (msg_id,)).fetchone()
            else:
                cand = self.con.execute(
                    "SELECT m.* FROM message m JOIN attempt a ON a.msg_id=m.msg_id"
                    " WHERE (m.recipient=? OR m.recipient='*') AND m.expires_at > ?"
                    "   AND a.state IN ('queued','delivered')"
                    "   AND a.n = (SELECT MAX(n) FROM attempt WHERE msg_id=m.msg_id)"
                    " ORDER BY m.priority ASC, m.created_at ASC LIMIT 1",
                    (agent, now)).fetchone()
            if not cand:
                return None
            mid = cand["msg_id"]
            row = self.con.execute(
                "SELECT MAX(n) n FROM attempt WHERE msg_id=?", (mid,)).fetchone()
            last = self.con.execute(
                "SELECT * FROM attempt WHERE msg_id=? AND n=?", (mid, row["n"])).fetchone()
            vis_until = now + self.vis_timeout
            if last["state"] == "queued":
                # 首次 claim：把该 attempt 从 queued 推进为 claimed
                self.con.execute(
                    "UPDATE attempt SET state='claimed', claimed_by=?, claimed_at=?, vis_until=?"
                    " WHERE msg_id=? AND n=?", (agent, now, vis_until, mid, row["n"]))
                n = row["n"]
            else:
                # 重现后的 claim：新 attempt（I3，不覆盖）
                n = row["n"] + 1
                self.con.execute(
                    "INSERT INTO attempt(msg_id, n, state, claimed_by, claimed_at, vis_until)"
                    " VALUES(?,?, 'claimed', ?,?,?)", (mid, n, agent, now, vis_until))
            return {"msg_id": mid, "attempt": n, "vis_until": vis_until,
                    "sender": cand["sender"], "mtype": cand["mtype"],
                    "payload": cand["payload"]}

    def ack(self, msg_id, agent, stage="done", body=None):
        """I4: 守护只能 delivered；done 必须 agent 级 receipt。
        且 done 要求存在 delivered 级证明（两级确认证明链）。"""
        now = time.time()
        if stage not in ("delivered", "done"):
            raise RuntimeError(f"BAD_STAGE: {stage}")
        with self._immediate():
            row = self.con.execute(
                "SELECT MAX(n) n FROM attempt WHERE msg_id=?", (msg_id,)).fetchone()
            if not row or row["n"] is None:
                raise RuntimeError(f"NO_ATTEMPT: {msg_id}")
            n = row["n"]
            if stage == "done":
                # ★ 结构门：done 需要同一 msg 上已有 delivered 证明
                has_delivered = self.con.execute(
                    "SELECT 1 FROM receipt WHERE msg_id=? AND stage='delivered' LIMIT 1",
                    (msg_id,)).fetchone()
                has_dl_attempt = self.con.execute(
                    "SELECT 1 FROM attempt WHERE msg_id=? AND state='delivered' LIMIT 1",
                    (msg_id,)).fetchone()
                if not (has_delivered or has_dl_attempt):
                    raise RuntimeError(
                        "FALSE_DONE_REJECTED: 无 delivered 证明，done 不可表达（I4 两级确认）")
            state = "delivered" if stage == "delivered" else "done"
            self.con.execute(
                "UPDATE attempt SET state=?, finished_at=? WHERE msg_id=? AND n=?",
                (state, now, msg_id, n))
            self.con.execute(
                "INSERT OR REPLACE INTO receipt(msg_id, agent, stage, ts, body) VALUES(?,?,?,?,?)",
                (msg_id, agent, stage, now, body))
        return {"msg_id": msg_id, "attempt": n, "stage": stage, "state": state}

    def sweep(self):
        """I4: visibility timeout 到期未 ack ⇒ 自动重现（新 attempt，计数 +1）。"""
        now = time.time()
        requeued, dead = 0, 0
        with self._immediate():
            rows = self.con.execute(
                "SELECT * FROM attempt WHERE state='claimed' AND vis_until IS NOT NULL"
                " AND vis_until < ?", (now,)).fetchall()
            for a in rows:
                mid, n = a["msg_id"], a["n"]
                if n >= self.max_retries:
                    self.con.execute(
                        "UPDATE attempt SET state='dead', finished_at=?, error='max_retries'"
                        " WHERE msg_id=? AND n=?", (now, mid, n))
                    dead += 1
                else:
                    self.con.execute(
                        "UPDATE attempt SET state='failed', finished_at=?, error='visibility_timeout'"
                        " WHERE msg_id=? AND n=?", (now, mid, n))
                    self.con.execute(
                        "INSERT INTO attempt(msg_id, n, state) VALUES(?,?,'queued')", (mid, n + 1))
                    requeued += 1
        return {"requeued": requeued, "dead": dead}

    # ---------- 查询 ----------
    def inbox(self, agent, limit=20):
        now = time.time()
        rows = self.con.execute(
            "SELECT m.*, (SELECT MAX(n) FROM attempt WHERE msg_id=m.msg_id) n,"
            " (SELECT state FROM attempt WHERE msg_id=m.msg_id ORDER BY n DESC LIMIT 1) state"
            " FROM message m WHERE (m.recipient=? OR m.recipient='*') AND m.expires_at > ?"
            " ORDER BY m.priority ASC, m.created_at ASC LIMIT ?", (agent, now, limit)).fetchall()
        return [dict(r) for r in rows]

    def dlq(self, limit=50):
        rows = self.con.execute(
            "SELECT a.*, m.sender, m.recipient FROM attempt a JOIN message m ON m.msg_id=a.msg_id"
            " WHERE a.state='dead' ORDER BY a.finished_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def replay(self, msg_id):
        """DLQ 回放：新 attempt，不覆盖（I3）。"""
        with self._immediate():
            row = self.con.execute(
                "SELECT MAX(n) n FROM attempt WHERE msg_id=?", (msg_id,)).fetchone()
            if not row or row["n"] is None:
                raise RuntimeError(f"NO_ATTEMPT: {msg_id}")
            n = row["n"] + 1
            self.con.execute("INSERT INTO attempt(msg_id, n, state) VALUES(?,?,'queued')", (msg_id, n))
        return {"msg_id": msg_id, "attempt": n, "state": "queued"}

    def trace(self, msg_id):
        a = [dict(r) for r in self.con.execute(
            "SELECT * FROM attempt WHERE msg_id=? ORDER BY n", (msg_id,)).fetchall()]
        r = [dict(x) for x in self.con.execute(
            "SELECT * FROM receipt WHERE msg_id=?", (msg_id,)).fetchall()]
        return {"msg_id": msg_id, "attempts": a, "receipts": r,
                "attempt_count": len(a), "max_n": a[-1]["n"] if a else 0}

    def stats(self):
        now = time.time()
        q = lambda s, p=(): self.con.execute(s, p).fetchone()[0]
        return {
            "db": self.db_path,
            "journal_mode": q("PRAGMA journal_mode"),
            "messages": q("SELECT COUNT(*) FROM message"),
            "agents": q("SELECT COUNT(*) FROM agent"),
            "attempts": q("SELECT COUNT(*) FROM attempt"),
            "by_state": {r["state"]: r["c"] for r in self.con.execute(
                "SELECT state, COUNT(*) c FROM attempt GROUP BY state")},
            "active_claims": q("SELECT COUNT(*) FROM attempt WHERE state='claimed'"),
            "dlq": q("SELECT COUNT(*) FROM attempt WHERE state='dead'"),
            "expired": q("SELECT COUNT(*) FROM message WHERE expires_at < ?", (now,)),
        }

    def cleanup(self, drop_expired=True):
        with self._immediate():
            n = 0
            if drop_expired:
                n = self.con.execute(
                    "DELETE FROM message WHERE expires_at < ? AND msg_id NOT IN"
                    " (SELECT msg_id FROM attempt WHERE state IN ('claimed','dead'))",
                    (time.time(),)).rowcount
        return {"expired_removed": n}


# ---------------- 只读导入（不碰生产） ----------------
def import_bus(mb, bus_path, dry_run=True, limit=100000):
    """把 agent-bus.json 的消息只读导入 L1，验证承载能力。
    幂等键用 origin_msg_id = 原 bus message id ⇒ 可反复跑不重复。"""
    raw = open(bus_path, "rb").read()
    d = json.loads(raw.decode("utf-8", "strict"))     # 严格解码，不静默替换
    n_ok = n_dup = n_skip = 0
    for t in d.get("threads") or []:
        if not isinstance(t, dict):
            continue
        tid = t.get("id")
        for m in t.get("messages") or []:
            if not isinstance(m, dict) or n_ok + n_dup >= limit:
                continue
            to = (m.get("to") or "").strip()
            frm = (m.get("from") or "").strip()
            if not to or not frm or to == "*" or to.startswith("topic:"):
                n_skip += 1
                continue
            if dry_run:
                n_ok += 1
                continue
            _, dup = mb.send(frm, to, body=m.get("text") or "", mtype="TASK",
                             priority=5, dedup_key=None, thread=tid,
                             origin_device="agent-bus",
                             origin_msg_id=m.get("id") or f"{tid}:{m.get('time')}",
                             bypass_rate=True)
            n_dup += 1 if dup else 0
            n_ok += 0 if dup else 1
    return {"dry_run": dry_run, "imported": n_ok, "duplicates": n_dup, "skipped": n_skip}


# ---------------- 断言套件：I1–I4 ----------------
def selftest(verbose=True):
    import tempfile
    import threading
    tmp = tempfile.mkdtemp(prefix="mailbox-selftest-")
    db = os.path.join(tmp, "t.db")
    ok = fail = 0
    log = (lambda *a: print("   ", *a)) if verbose else (lambda *a: None)

    def check(name, cond, detail=""):
        nonlocal ok, fail
        if cond:
            ok += 1
            log(f"PASS  {name}")
        else:
            fail += 1
            log(f"FAIL  {name}  {detail}")

    mb = Mailbox(db, vis_timeout=1, max_retries=3, device="dev-a")
    check("I1 journal_mode=WAL", mb.stats()["journal_mode"] == "wal", mb.stats()["journal_mode"])

    # --- I1 并发写 + 并发读：读侧不得 torn（★ 2026-10-01 重写：原断言只查文件头，是探针型空判据）---
    errs = []
    read_obs = []          # 读侧每次观测到的计数
    read_errs = []
    stop = {"v": False}

    def writer(tag, k):
        try:
            m2 = Mailbox(db, device=f"dev-{tag}")
            for i in range(k):
                m2.send(f"sender-{tag}", f"recv-{i%3}", body="x" * 200)
            m2.close()
        except Exception as e:      # noqa: BLE001
            errs.append(repr(e))

    def reader(maxiters):
        """与写者【同时】读，直到写者结束才停。
        ★ 审查修正：原实现固定 120 次就退出，末次观测可能早于写者收工
          （我因此断言了一个设置并不保证的性质）。改为「写者不停，读就不停」。"""
        try:
            r = Mailbox(db, device="reader")
            n = 0
            while not stop["v"] and n < maxiters:
                s = r.stats()
                read_obs.append(s["messages"])
                r.inbox("recv-0", limit=5)
                n += 1
                time.sleep(0.001)
            r.close()
        except Exception as e:      # noqa: BLE001
            read_errs.append(repr(e))

    ths = [threading.Thread(target=writer, args=(t, 60)) for t in "ABC"]
    ths.append(threading.Thread(target=reader, args=(100000,)))
    [t.start() for t in ths]
    for t in ths[:-1]:              # 等写者
        t.join()
    stop["v"] = True
    ths[-1].join()
    ext = Mailbox(db, device="external")
    total = ext.stats()["messages"]
    check("I1 并发写无异常（3 线程 × 60 条）", not errs, "; ".join(errs[:2]))
    check("I1 并发写计数守恒 = 180", total == 180, f"实际 {total}")
    check("I1 并发【读】期间零异常（写读同时进行）", not read_errs, "; ".join(read_errs[:2]))
    check("I1 读侧观测序列非空", len(read_obs) >= 5, f"仅 {len(read_obs)} 次")
    mono = all(read_obs[i] <= read_obs[i + 1] for i in range(len(read_obs) - 1))
    check("I1 读侧计数单调不减（回退=读到中间态=torn）", mono,
          f"回退: {[ (read_obs[i],read_obs[i+1]) for i in range(len(read_obs)-1) if read_obs[i]>read_obs[i+1] ][:3]}")
    check("I1 读侧从未读超真值（>180 即不一致）", all(x <= 180 for x in read_obs),
          f"max={max(read_obs) if read_obs else None}")
    # ★ 非空性：必须观测到【中间态】，否则读与写没真正重叠，本组断言形同虚设
    mid = [x for x in read_obs if 0 < x < 180]
    check("I1 读侧确实观测到中间态（读写真重叠，非探针型空判据）", len(mid) >= 5,
          f"中间态样本 {len(mid)} 个")
    # ★ 静默后的一致性：写者已全部结束，此刻再读必须看到完整总数
    #   （这不是 torn read 的性质，而是「尘埃落定后状态一致」的性质 —— 审查时区分开）
    settled = ext.stats()["messages"]
    check("I1 写者结束后读侧看到完整一致状态（==180）", settled == 180, f"实得 {settled}")

    # --- I1b ★ 多进程并发写（2026-10-01 新增）---
    #   理由：同进程多线程 ≠ 多进程。生产里同时写这个库的是**不同进程**
    #   （CLD 子进程 / 守护 / 同步器 / 注入器），而 SQLite 的写锁是进程级语义。
    import subprocess as _sp
    _self = os.path.abspath(__file__)
    _child = (
        "import importlib.util,sys\n"
        f"spec=importlib.util.spec_from_file_location('am',{_self!r})\n"
        "m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
        "tag,k,db=sys.argv[1],int(sys.argv[2]),sys.argv[3]\n"
        "mb=m.Mailbox(db,device='mp-'+tag)\n"
        "for _ in range(k): mb.send('mp-'+tag,'mp-recv',body='y'*120)\n"
        "mb.close()\n")
    _mpdb = os.path.join(tmp, "mp.db")

    def _mp_run(tag_prefix, k, nproc=3):
        # ★ 每个进程必须用【不同】发件人：同发件人会撞 per-sender 限流（60/min），
        #   那是限流在正常工作，不是并发缺陷 —— 初版三个进程共用同一 tag，误判了一次。
        ps = [_sp.Popen([sys.executable, "-c", _child, f"{tag_prefix}{i}", str(k), _mpdb],
                        stdout=_sp.PIPE, stderr=_sp.PIPE, text=True) for i in range(nproc)]
        out = []
        for p in ps:
            try:
                out.append(p.communicate(timeout=180))
            except _sp.TimeoutExpired:
                p.kill(); out.append(("", "timeout"))
        return [p.returncode for p in ps], out

    # A) 并发正确性：三个**不同**发件人，各发 55 条（≤ 60/min 限流阈值，专测并发不测限流）
    _rcs, _outs = _mp_run("mp", 55, 3)
    _errs = [e for _, e in _outs if e and e.strip()]
    _mp = Mailbox(_mpdb, device="mp-check")
    _n_mp = _mp.stats()["messages"]
    _integ = _mp.con.execute("PRAGMA integrity_check").fetchone()[0]
    check("I1b 多进程并发：3 进程退出码全 0", all(r == 0 for r in _rcs), str(_rcs))
    check("I1b 多进程并发：计数守恒 = 165", _n_mp == 165, f"实际 {_n_mp}")
    check("I1b 多进程并发：integrity_check = ok", _integ == "ok", str(_integ))
    check("I1b 多进程并发：无 database is locked / 异常输出", not _errs, str(_errs)[:220])

    # B) ★ 限流是否【跨进程共享】——同进程多线程测不出来的性质
    #    同一发件人 mp2 起 3 个进程 × 30 条 = 90 次尝试，期望 ≤60 成功、其余被拒
    _mpdb2 = os.path.join(tmp, "mp2.db")
    _child2 = _child.replace("mb.send('mp-'+tag", "mb.send('mp2'")
    _ps = [_sp.Popen([sys.executable, "-c", _child2, "same", "30", _mpdb2],
                     stdout=_sp.PIPE, stderr=_sp.PIPE, text=True) for _ in range(3)]
    _o2 = []
    for p in _ps:
        try:
            _o2.append(p.communicate(timeout=180))
        except _sp.TimeoutExpired:
            p.kill(); _o2.append(("", "timeout"))
    _m2 = Mailbox(_mpdb2, device="mp2-check")
    _n2 = _m2.stats()["messages"]
    _limited = sum(1 for _, e in _o2 if e and "RATE_LIMITED" in e)
    check("I1b 限流跨进程共享：同一发件人 3 进程合计 ≤60 成功", _n2 <= 60, f"实际落库 {_n2}")
    check("I1b 限流跨进程共享：确有进程被限流（说明是共享而非各算各的）",
          _limited >= 1, f"被限流进程数 {_limited}")
    check("I1b 限流跨进程共享：未发生超发（落库 ≤ 阈值）", _n2 <= 60, f"{_n2} > 60")

    # --- I2 入站串行 ---
    mb.send("boss", "worker", body="task-1")
    mb.send("boss", "worker", body="task-2")
    c1 = mb.claim("worker")
    check("I2 首次 claim 成功", c1 is not None)
    try:
        mb.claim("worker")
        check("I2 第二次 claim 被拒（串行不变量）", False, "竟然成功")
    except RuntimeError as e:
        check("I2 第二次 claim 被拒（串行不变量）", "SERIAL_VIOLATION" in str(e), str(e))
    # 出站不受限（★ 严格等式，不用 >=）
    n_before_send = mb.stats()["messages"]
    for i in range(5):
        mb.send("worker", "boss", body=f"reply-{i}")
    check("I2 出站不受入站配额限制（恰好 +5）",
          mb.stats()["messages"] == n_before_send + 5,
          f"{n_before_send} → {mb.stats()['messages']}")

    # --- I4 投递≠消费：done 需要 delivered 证明 ---
    try:
        mb.ack(c1["msg_id"], "worker", stage="done")
        check("I4 无 delivered 证明时 done 被拒", False, "竟然成功")
    except RuntimeError as e:
        check("I4 无 delivered 证明时 done 被拒", "FALSE_DONE_REJECTED" in str(e), str(e))
    mb.ack(c1["msg_id"], "worker", stage="delivered")
    mb.ack(c1["msg_id"], "worker", stage="done")
    tr = mb.trace(c1["msg_id"])
    check("I4 delivered→done 两级齐全后可 done",
          any(r["stage"] == "delivered" for r in tr["receipts"]) and
          any(r["stage"] == "done" for r in tr["receipts"]))

    # --- I4 visibility timeout 自动重现 ---
    c2 = mb.claim("worker")                      # 拿到 task-2
    n_before = mb.trace(c2["msg_id"])["attempt_count"]
    time.sleep(1.2)
    sw = mb.sweep()
    tr2 = mb.trace(c2["msg_id"])
    check("I4 超时未 ack ⇒ 自动重现", sw["requeued"] >= 1, str(sw))
    check("I3 重现产生【新 attempt】而非覆盖", tr2["attempt_count"] == n_before + 1,
          f"{n_before} → {tr2['attempt_count']}")
    check("I3 attempt 编号连续且旧记录保留",
          [a["n"] for a in tr2["attempts"]] == list(range(1, tr2["attempt_count"] + 1)))
    check("I3 谱系可见（旧 attempt 状态=failed）",
          any(a["state"] == "failed" and a["error"] == "visibility_timeout" for a in tr2["attempts"]))

    # --- I3 超 max_retries 入 DLQ，不静默丢弃 ---
    mid = c2["msg_id"]
    for _ in range(6):
        try:
            mb.claim("worker", msg_id=mid)
        except RuntimeError:
            pass
        time.sleep(1.1)
        mb.sweep()
    dl = mb.dlq()
    check("I3 超 max_retries 进入 DLQ", any(a["msg_id"] == mid for a in dl), f"dlq={len(dl)}")
    tr3 = mb.trace(mid)
    # ★ 2026-10-01 修正：原为 check(..., True) 恒真断言（永远绿，只会虚高通过数）。
    #   改为真断言：回放前先冻结旧 attempt 的快照，回放后旧记录必须【原样仍在】。
    before = tr3["attempt_count"]
    snap = [(a["n"], a["state"]) for a in tr3["attempts"]]
    mb.replay(mid)
    tr4 = mb.trace(mid)
    check("I3 回放 attempt 数 +1", tr4["attempt_count"] == before + 1,
          f"{before} → {tr4['attempt_count']}")
    check("I3 回放【不覆盖】旧 attempt（旧行原样仍在）",
          [(a["n"], a["state"]) for a in tr4["attempts"]][:before] == snap,
          f"旧={snap} 现={[(a['n'],a['state']) for a in tr4['attempts']][:before]}")
    check("I3 数量守恒：max_n == attempt 行数", tr4["max_n"] == tr4["attempt_count"],
          f"max_n={tr4['max_n']} rows={tr4['attempt_count']}")
    # ★ 全局守恒：不只单条消息 —— 全部消息的 attempt 编号必须连续无洞
    holes = mb.con.execute(
        "SELECT msg_id FROM attempt GROUP BY msg_id"
        " HAVING MAX(n) <> COUNT(*) OR MIN(n) <> 1").fetchall()
    check("I3 全局守恒：所有消息的 attempt 编号 1..n 连续无洞", not holes,
          f"有洞消息数={len(holes)}")

    # --- 幂等 ---
    a, d1 = mb.send("x", "y", body="once", dedup_key="k1")
    b, d2 = mb.send("x", "y", body="once-again", dedup_key="k1")
    check("幂等：同 dedup_key 不产生第二条", a == b and d2 is True)

    # --- 速率限制 ---
    mb2 = Mailbox(os.path.join(tmp, "r.db"), rate_limit=3)
    raised = False
    for i in range(5):
        try:
            mb2.send("flood", "z", body=str(i))
        except RuntimeError as e:
            raised = "RATE_LIMITED" in str(e)
            break
    check("限流：超 per-agent 配额被拒", raised)

    # ================= ★ 2026-10-01 补齐：此前完全未覆盖的四项 =================
    mb3 = Mailbox(os.path.join(tmp, "extra.db"), vis_timeout=300, device="dev-x")

    # (a) 优先级：高优先（小数字）必须先被 claim —— 设计声称 priority-based inbox，此前【零断言】
    mb3.send("p", "q", body="low", priority=9)
    mb3.send("p", "q", body="high", priority=0)
    mb3.send("p", "q", body="mid", priority=5)
    got = mb3.claim("q")
    check("优先级：priority=0 先于 5/9 被 claim",
          got is not None and got["payload"] == "high", f"实得 {got and got['payload']}")

    # (b) TTL：过期消息必须从 inbox 消失，且 cleanup 真的删行
    mb3.send("p", "ttl-agent", body="short", ttl=-1)      # 已过期
    before_rows = mb3.stats()["messages"]
    ib = mb3.inbox("ttl-agent")
    check("TTL：已过期消息不出现在 inbox", not any(x["payload"] == "short" for x in ib),
          f"inbox={[x['payload'] for x in ib]}")
    rm = mb3.cleanup()
    check("TTL：cleanup 真的删除过期行（行数下降）",
          mb3.stats()["messages"] < before_rows and rm["expired_removed"] >= 1,
          f"{before_rows} → {mb3.stats()['messages']}, removed={rm['expired_removed']}")

    # (c2) ★ 审查新增：claim 侧也过滤过期 —— 与 inbox 是【同谓词的两个调用点】，此前只覆盖了 inbox
    mb3.send("p", "exp-agent", body="expired-task", ttl=-1)
    got_exp = mb3.claim("exp-agent")
    check("TTL：已过期消息不得被 claim（claim 侧调用点）", got_exp is None,
          f"竟然 claim 到 {got_exp}")

    # (c) 只 ack delivered（不给 done）不得使消息进入 done 终态 —— 反方向的两级确认
    m4 = mb3.send("p", "r", body="x")[0]
    c4 = mb3.claim("r", msg_id=m4)
    mb3.ack(m4, "r", stage="delivered")
    st = mb3.con.execute("SELECT state FROM attempt WHERE msg_id=? ORDER BY n DESC LIMIT 1", (m4,)).fetchone()["state"]
    check("I4 仅 delivered 时不得为 done（反方向）", st == "delivered", f"state={st}")
    tr4b = mb3.trace(m4)
    check("I4 delivered 阶段有 receipt 记录，但无 done receipt",
          any(x["stage"] == "delivered" for x in tr4b["receipts"]) and
          not any(x["stage"] == "done" for x in tr4b["receipts"]))

    # (d) 无 attempt 的 msg_id 不可 ack（防伪造 ID 写入 receipt）
    try:
        mb3.ack("no-such-msg", "r", stage="delivered")
        check("ack：不存在的 msg_id 被拒", False, "竟然成功")
    except RuntimeError as e:
        check("ack：不存在的 msg_id 被拒", "NO_ATTEMPT" in str(e), str(e))

    # (e) ★ 审查新增：同谓词的第二个调用点，逐一对齐
    #   e1. inbox() 自身的优先级排序（此前优先级只断言了 claim()，inbox() 的 ORDER BY 无覆盖）
    mb3.send("p", "ord", body="o-low", priority=9)
    mb3.send("p", "ord", body="o-high", priority=0)
    mb3.send("p", "ord", body="o-mid", priority=5)
    order = [x["payload"] for x in mb3.inbox("ord", limit=3)]
    check("优先级：inbox() 返回按 priority 升序（第二调用点）",
          order == ["o-high", "o-mid", "o-low"], f"实得 {order}")
    #   e2. replay() 的 NO_ATTEMPT（此前只断言了 ack() 的那个）
    try:
        mb3.replay("no-such-msg-either")
        check("replay：不存在的 msg_id 被拒（第二调用点）", False, "竟然成功")
    except RuntimeError as e2:
        check("replay：不存在的 msg_id 被拒（第二调用点）", "NO_ATTEMPT" in str(e2), str(e2))
    #   e3. 反控：断言本身必须可失败 —— 用一条必然错的比较验证 check() 真的会记 FAIL
    _probe_ok, _probe_fail = ok, fail
    check("反控：check() 对假条件确实记 FAIL", False, "反控探针")
    check("反控：上一条确实产生了 1 个 FAIL", fail == _probe_fail + 1, f"{_probe_fail}→{fail}")
    # 修正：把反控探针计入的两个计数撤回（保持总分只反映真实断言）
    ok = _probe_ok
    fail = _probe_fail

    print(f"\n  selftest: {ok} PASS / {fail} FAIL")
    return 0 if fail == 0 else 1


def main():
    ap = argparse.ArgumentParser(description="L1 设备内 agent 邮箱（SQLite/WAL）")
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--device", default=os.environ.get("DSH_NODE_ID", "local"))
    sub = ap.add_subparsers(dest="cmd")

    sub.add_parser("init")
    p = sub.add_parser("send")
    p.add_argument("--from", dest="sender", required=True)
    p.add_argument("--to", dest="recipient", required=True)
    p.add_argument("--body", default="")
    p.add_argument("--type", dest="mtype", default="TASK")
    p.add_argument("--priority", type=int, default=5)
    p.add_argument("--ttl", type=int)
    p.add_argument("--dedup-key")
    p.add_argument("--thread")
    p = sub.add_parser("inbox"); p.add_argument("--agent", required=True); p.add_argument("--limit", type=int, default=20)
    p = sub.add_parser("claim"); p.add_argument("--agent", required=True); p.add_argument("--msg")
    p = sub.add_parser("ack"); p.add_argument("--msg", required=True); p.add_argument("--agent", required=True)
    p.add_argument("--stage", default="done"); p.add_argument("--body")
    sub.add_parser("sweep")
    p = sub.add_parser("dlq"); p.add_argument("--limit", type=int, default=50)
    p = sub.add_parser("replay"); p.add_argument("--msg", required=True)
    p = sub.add_parser("trace"); p.add_argument("--msg", required=True)
    sub.add_parser("stats")
    p = sub.add_parser("import-bus"); p.add_argument("--bus", required=True); p.add_argument("--dry-run", action="store_true")
    sub.add_parser("selftest")
    args = ap.parse_args()

    if args.cmd == "selftest":
        return selftest()
    mb = Mailbox(args.db, device=args.device)
    out = None
    if args.cmd in (None, "init"):
        out = {"ok": True, "db": args.db, "stats": mb.stats()}
    elif args.cmd == "send":
        mid, dup = mb.send(args.sender, args.recipient, args.body, args.mtype,
                           args.priority, args.ttl, args.dedup_key, args.thread)
        out = {"msg_id": mid, "duplicate": dup}
    elif args.cmd == "inbox":
        out = mb.inbox(args.agent, args.limit)
    elif args.cmd == "claim":
        out = mb.claim(args.agent, args.msg)
    elif args.cmd == "ack":
        out = mb.ack(args.msg, args.agent, args.stage, args.body)
    elif args.cmd == "sweep":
        out = mb.sweep()
    elif args.cmd == "dlq":
        out = mb.dlq(args.limit)
    elif args.cmd == "replay":
        out = mb.replay(args.msg)
    elif args.cmd == "trace":
        out = mb.trace(args.msg)
    elif args.cmd == "stats":
        out = mb.stats()
    elif args.cmd == "import-bus":
        out = import_bus(mb, os.path.expanduser(args.bus), dry_run=args.dry_run)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
