#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""inbound-log.py — 上下文插入 / 队列消息 全量记录器（v1.1.0）

v1.1.0 修正（2026-10-01，实测触发）：
  v1.0.0 用「已消费到最大 time(ms)」当游标 —— 这**假设到达顺序 = 时间顺序**。
  实测证伪：三条实际到达次序为 07:33:45(A1 v1) → 07:42:38(A1 v1.1) → 07:37:44(A2)，
  A2 的时间**夹在前两条中间**。游标一推进到 07:42:38，就把 07:37:44/07:37:50/
  07:37:57/07:39:09/07:41:28 这 5 条**静默吞掉**了（它们既没被消费，也不在待消费里）。
  这是「单调游标 over 非有序流」的典型丢件：丢得悄无声息。
  ⇒ 改为**已消费集合（键集合）**，单调游标只作参考显示；并新增「乱序件」显式告警。

用户指令（2026-10-01）：全量记录来自队列的消息，最后汇总，不回复任何会话。

为什么要有这个脚本：靠「记得记」一定漏。把记录做成可重复运行的命令，
而不是纪律。本脚本只读 agent-bus.json、只写本地磁盘，绝不写黑板 notes/。

子命令：
  sync            重建全量台账（队列全量正文 + 归属统计），报告相对上次的新增
  inject <text>   追加一条「实际插入到本会话」的观测 envelope（正文原样）
  status          只打印当前游标与待消费统计，不写文件

游标口径：state 里记住「已消费到的最大 time(ms)」，同时也记住已观测插入的
消息 key(from|time|len)，避免同一条被记两次。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）


import collections
import datetime
import json
import os
import sys

ME = 'session-fa1f9150-c949-401f-ba8c-d265f6221676'
BUS = os.path.expanduser('~/.dsh/agent-bus.json')
OUTDIR = os.path.expanduser('~/dsh-collab/logs/injection-log')
OUT = os.path.join(OUTDIR, 'inbound-20261001.md')
STATE = os.path.join(OUTDIR, 'inbound-state.json')

# 队列起点：日期 >= 2026-09-28 的发给我的消息即「172 条」那个队列。
# 用「地板时间 + 已消费集合」定义待消费，不用单调游标（见文件头 v1.1.0 说明）。
FLOOR = 1790524800000            # 2026-09-28 00:00:00
SEED_CONSUMED = [                # 已在本会话上下文中亲眼看到的（顺序=实际到达顺序）
    '74b5a9e6-06a1-4098-bcd1-83b94e26f322|1790552025367|43',   # A1 v1        07:33:45
    '74b5a9e6-06a1-4098-bcd1-83b94e26f322|1790552558227|46',   # A1 v1.1      07:42:38
    '649d6794-830b-48c6-afda-43ce565b5689|1790552264090|70',   # A2 报告      07:37:44
]


def ts(ms):
    return datetime.datetime.fromtimestamp(ms / 1000).strftime('%Y-%m-%d %H:%M:%S')


def load_bus():
    """严格解码：任何非法字节都不许静默替换成 U+FFFD（驿使的 decode-loss 教训）。"""
    raw = open(BUS, 'rb').read()
    return json.loads(raw.decode('utf-8', 'strict'))


def inbound():
    d = load_bus()
    rows = []
    for t in d.get('threads') or []:
        if not isinstance(t, dict):
            continue
        for m in t.get('messages') or []:
            if not isinstance(m, dict) or m.get('to') != ME:
                continue
            rows.append(dict(
                time=m.get('time') or 0,
                frm=m.get('from') or '?',
                status=m.get('status'),
                len=len(m.get('text') or ''),
                thread=t.get('id'),
                text=m.get('text') or '',
            ))
    rows.sort(key=lambda r: r['time'])
    return rows


def load_state():
    if os.path.exists(STATE):
        try:
            return json.load(open(STATE, encoding='utf-8'))
        except Exception:
            pass
    return {'consumed': list(SEED_CONSUMED), 'observed': list(SEED_CONSUMED),
            'runs': 0, 'seen_keys': []}


def save_state(s):
    os.makedirs(OUTDIR, exist_ok=True)
    json.dump(s, open(STATE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def key(r):
    return f"{r['frm']}|{r['time']}|{r['len']}"


def split_queue(rows, st):
    """把 to=me 的消息按「已消费集合」切成三段。

    返回 (queue, consumed, pending, late):
      queue    地板时间之后进入队列的全部消息（=172 那位数）
      consumed 已亲眼在上下文看到的（键命中 consumed 集合）
      pending  地板后且未消费的
      late     **乱序件**：未消费，但其 time 早于已消费件的最新 time
               —— v1.0.0 的单调游标会把这批静默吞掉，这里显式列出来。
    """
    q = [r for r in rows if r['time'] >= FLOOR]
    cons = set(st.get('consumed') or [])
    consumed = [r for r in q if key(r) in cons]
    pending = [r for r in q if key(r) not in cons]
    newest = max((r['time'] for r in consumed), default=0)
    late = [r for r in pending if r['time'] < newest]
    return q, consumed, pending, late


def render(rows, st, new_since):
    q, consumed, pending, late = split_queue(rows, st)
    newest = max((r['time'] for r in consumed), default=0)
    L = []
    w = L.append
    w("# 上下文插入 / 队列消息 全量记录")
    w("")
    w(f"- 记录人：星桥（session `{ME}`）")
    w(f"- 本次刷新：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}（第 {st['runs']} 次 sync）")
    w("- 用户指令：**全量记录来自队列的消息，最后汇总；不回复任何会话**")
    w("- 本文件只落本地磁盘，**未写入黑板 notes/ 命名空间**（写卡会额外产生注入）")
    w("- 数据源：`~/.dsh/agent-bus.json`，utf-8 **strict** 解码（无 errors=replace）")
    w("- 重放本文件：`python3 ~/dsh-collab/scripts/inbound-log.py sync`")
    w("")
    w("## 0. 观测口径（v1.1.0：集合而非游标）")
    w("")
    w(f"- 发给本 session 的消息总量：**{len(rows)}** 条，status "
      f"{dict(collections.Counter(r['status'] for r in rows))}，发信人 "
      f"{len(set(r['frm'] for r in rows))} 个")
    w(f"- **队列（time >= {ts(FLOOR)}）**：**{len(q)}** 条")
    w(f"- 已亲眼插入本会话：**{len(consumed)}** 条；未消费（待消费）：**{len(pending)}** 条 "
      f"/ {sum(r['len'] for r in pending)} 字节")
    w(f"- 参考量（非判据）：已消费件最新时间 {ts(newest) if newest else '-'}")
    w("")
    w(f"### ⚠️ 乱序件（{len(late)} 条）——v1.0.0 单调游标会静默吞掉的就是这一批")
    w("")
    if late:
        w("这些**尚未消费**，但其时间早于已消费件的最新时间。到达顺序 != 时间顺序，")
        w("所以「推进到最大时间」= 把它们删掉而不自知。")
        w("")
        for r in late:
            w(f"- `{ts(r['time'])}` · {r['frm']} · {r['len']}B · `{r['thread']}`")
    else:
        w("无。")
    w("")
    if new_since:
        w(f"- ⚠️ 本次相对上次 sync 新增 **{len(new_since)}** 条（按时间）：")
        for r in new_since:
            w(f"  - {ts(r['time'])} · {r['frm']} · {r['len']}B")
    else:
        w("- 本次相对上次 sync 无新增。")
    w("")
    w(f"## 1. 已实际插入到本会话的观测 envelope（{len(consumed)} 条，**按实际到达顺序**）")
    w("")
    w("判定口径：这些是在本会话上下文中**亲眼看到**的注入，不只是存在于 bus 里。")
    w("顺序即我在上下文里收到它们的先后 —— 这就是「到达顺序 != 时间顺序」的证据本身。")
    w("")
    for i, m in enumerate(consumed, 1):
        w(f"### 到达第 {i} 条 · 时间戳 {ts(m['time'])} · {m['frm']}")
        w(f"- thread `{m['thread']}` · status `{m['status']}` · {m['len']} 字节")
        w("```")
        w(m['text'])
        w("```")
    w("")
    w(f"## 2. 队列全量正文（待消费 {len(pending)} 条，按时间升序，逐条不截断）")
    w("")
    byday = collections.Counter(ts(r['time'])[:10] for r in pending)
    w(f"按日：{dict(sorted(byday.items()))}；总字节 {sum(r['len'] for r in pending)}")
    w("")
    for i, r in enumerate(pending, 1):
        w(f"### [{i:03d}] {ts(r['time'])} · {r['frm']} · {r['len']}B · `{r['thread']}`")
        w("```")
        w(r['text'])
        w("```")
    w("")
    w("## 3. 归属统计（待消费）")
    w("")
    w("| 条数 | 发信人 |")
    w("|---:|---|")
    for k, v in collections.Counter(r['frm'] for r in pending).most_common():
        w(f"| {v} | `{k}` |")
    return "\n".join(L) + "\n"


def cmd_sync():
    st = load_state()
    st['runs'] = st.get('runs', 0) + 1
    rows = inbound()
    q, consumed, pending, late = split_queue(rows, st)
    seen = set(st.get('seen_keys') or [])
    new_since = [r for r in pending if key(r) not in seen]
    st['seen_keys'] = sorted(seen | {key(r) for r in pending})
    os.makedirs(OUTDIR, exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(render(rows, st, new_since))
    save_state(st)
    newest = max((r['time'] for r in consumed), default=0)
    print(f"OUT  {OUT} ({os.path.getsize(OUT)} B)")
    print(f"bus→me {len(rows)} | 队列 {len(q)} | 已消费 {len(consumed)} | "
          f"待消费 {len(pending)} / {sum(r['len'] for r in pending)}B")
    print(f"参考: 已消费件最新时间 {ts(newest) if newest else '-'} | 新增 {len(new_since)}")
    if late:
        print(f"⚠️ 乱序件 {len(late)} 条（未消费但早于已消费件最新时间）：")
        for r in late:
            print(f"    {ts(r['time'])} {r['frm']} {r['len']}B")
    return 0


def cmd_inject(args):
    """追加一条实际插入观测。用法：inject "<from>|<time_ms>" "<text>" 或 inject - 读 stdin 的 JSON。"""
    st = load_state()
    if args and args[0] == '-':
        payload = json.load(sys.stdin)
        frm, t, text = payload['from'], int(payload['time']), payload['text']
    elif len(args) >= 2:
        frm, t = args[0].split('|', 1)
        t = int(t)
        text = args[1]
    else:
        print("用法: inject '<from>|<time_ms>' '<text>'  或  inject -  < payload.json")
        return 2
    rows = inbound()
    match = [r for r in rows if r['frm'] == frm and r['time'] == t]
    if match:
        k = key(match[0])
    else:
        print(f"⚠️ bus 里没有这条（from={frm} time={ts(t)}）—— 可能是非 bus 通道（黑板注入器）。")
        k = f"{frm}|{t}|{len(text)}"
    if k not in (st.get('consumed') or []):
        st.setdefault('consumed', []).append(k)
        st.setdefault('observed', []).append(k)
        # 注意：**不推进游标**。到达顺序 != 时间顺序，单调游标会静默吞掉乱序件。
        save_state(st)
        print(f"REC  {ts(t)} {frm} {len(text)}B  (bus match: {bool(match)})")
    else:
        print(f"DUP  {ts(t)} {frm} 已记录过")
    return cmd_sync()


def cmd_status():
    st = load_state()
    rows = inbound()
    q, consumed, pending, late = split_queue(rows, st)
    newest = max((r['time'] for r in consumed), default=0)
    print(f"bus→me {len(rows)} | 队列 {len(q)} | 已消费 {len(consumed)} | "
          f"待消费 {len(pending)} / {sum(r['len'] for r in pending)} B")
    print(f"参考: 已消费件最新时间 {ts(newest) if newest else '-'}")
    if late:
        print(f"⚠️ 乱序件 {len(late)} 条:")
        for r in late:
            print(f"    {ts(r['time'])} {r['frm']} {r['len']}B")
    for k, v in collections.Counter(r['frm'] for r in pending).most_common(8):
        print(f"  {v:5d}  {k}")
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if cmd == 'sync':
        return cmd_sync()
    if cmd == 'inject':
        return cmd_inject(sys.argv[2:])
    if cmd == 'status':
        return cmd_status()
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main())
