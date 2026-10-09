#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-send-check.py — agent_send 发送前审查校验器（v3.0.0：新增「引用完整性」门禁）

在调用 agent_send 之前运行，判断该消息应该怎么发：
  ✅ 放行（短提示/紧急/已落黑板且引用可解析）
  ⚠️ 建议（全文未落黑板 → 先写黑板再发短提示）
  ❌ 拦截（**引用的键不存在或名非法**）
  ❓ 未知（黑板不可达 ⇒ 手段失败，**绝不读成通过**）

用法:
  python3 bb-send-check.py --text "看黑板 notes/mac-mini/xxx"
  python3 bb-send-check.py --text "..." --to session-xxx [--json]
  python3 bb-send-check.py --replay-bus        # 复盘历史：全总线上「看黑板 <key>」的解析率
  python3 bb-send-check.py --selftest | --version

v3.0.0（2026-09-14，采纳明鉴 ③「把约定变成机制」，并直指 HR 与明鉴同款缺陷）:
  新增【引用完整性】：把消息里的 `看黑板 <key>` / `notes/...` / `data/...` 引用逐个 GET。
  判据分工（HR 裁定）：200 = 存在 · 404 = 名合法但不存在 · 400 = 名非法（从未可能存在）。
  为什么必要（实测）：HR **21/37≈57%**、明鉴 **5/282≈1.8%** 的指针指向不存在的键，
  根因是同一个 —— **「发指针时从不 GET」**。这不是「谁更仔细」的问题：
  人记得 GET 与不记得 GET 的差别，就是这条规则**在不在流程里**的差别。
  把它写进一次调用内部，第二步就不靠记得（与 bb-put-both 的双写同构）。
  ★ 原则：手段失败不读成通过 —— 黑板不可达判 `unknown`，绝不判 pass。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-send-check.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = "3.1.0"  # ★ R006 ⑥ 唯一版本源（2026-10-08 合并：此前 __version__=1.0.0 与 VERSION=3.0.0 两处分叉 ⇒ 现只此一处）
__version__ = VERSION  # 兼容别名（引用同一值，非第二声明）
THRESHOLD = 200
DEFAULT_BB = os.environ.get("BB_URL", "http://127.0.0.1:8792")
# 两档抽取（★ 关键：枚举面必须比分类面更粗）
#   · 严格档（STRICT_RE）：符合命名规则（首段纯小写 [a-z]{2,}）⇒ 全文任意位置都算引用
#   · 宽松档（AFTER_MARK）：**紧跟在「看黑板」之后**的 token，任何形状都算引用
# ★ 为什么必须有两档（实测教训）：只留严格档时，**名非法的键根本抽不出来** ——
#   `看黑板 cld-health/foo` 因首段含连字符而不匹配 ⇒ 门禁放行，而它正是 HR 那个 400 实例的形状。
#   即：抽取面比「命名规则的违反空间」窄 ⇒ **非法名对门禁不可见** ⇒ 白名单式陷阱。
#   宽松档只在「看黑板」标记之后生效，故不会把 `HTTP/1.1` 之类误当引用。
# ★ 第三档修正（实测两次翻车的产物，见 selftest）：
#   服务端的合法键规则是 `^([a-z]+)/...` —— **任意纯小写词都是合法首段** ⇒ 光靠「形状合法」
#   无法区分「黑板键」与「散文里的路径/字段列表」。实测污染样本：
#   `id/name/version/mainlines/...`（字段列表）· `lib/monitor.js` · `scripts/build.mjs`
#   ⇒ 它们形状合法、GET 得 404 ⇒ 被计成「失效指针」⇒ 把失效率先报成 29.5%（几乎全是假阳性）。
#   故严格档加白名单：只有**已存在的黑板命名空间**才算引用；「看黑板」之后的 token 仍全算。
KNOWN_NS = ("data", "notes", "tasks", "health", "mbp", "alerts")
STRICT_RE = re.compile(r"(?<![A-Za-z0-9._\-/:])((?:" + "|".join(KNOWN_NS) +
                       r")/[A-Za-z0-9._\-/]+)")
# 第四档修正（实测：这一条曾造出 1289 个「取不到」= 全库 26%）
#   原写法把 token 定义成「除空白与中文标点外的任意字符」，但**漏排了全角左括号 `（`**
#   ⇒ 抽出的键被中文括号污染（`data/x/y（已监控`）⇒ 构造 URL 时 UnicodeEncodeError
#   ⇒ 26% 的键落进「取不到」桶。根因不是网络，是**抽取面太宽的第二次发作**（第一次是散文路径）。
#   ⇒ 收紧为「键合法字符集」：既能抓 `cld-health/foo` 这类**名非法**的键，又不会吞中文正文。
AFTER_MARK = re.compile(r"看黑板\s*[「『【\[(]?([A-Za-z0-9][A-Za-z0-9._\-/]*)")
TRAIL = ".,;:!?)]}>。，；：！？）】》、"



def _decode_strict(raw):
    """★ 严格解码（2026-09-22，采纳驿使经明鉴转达的「穷尽五条件」之一：**解码无丢失**）。
    原 `errors="replace"` 会把撕裂读的半个多字节序列静默换成 U+FFFD（字节数看似没少、字符已丢），
    且 JSON 往往仍能解析 ⇒ **错误不可见**。⇒ 改严格解码：解不出就抛，交给本来就有重试的调用方重试。"""
    return raw.decode("utf-8")

def extract_keys(text, with_suspicious=False):
    """抽出文本里引用的黑板键（去重、保序、剥尾随标点）。两档：严格档全文 + 宽松档限「看黑板」之后。

    ★ 第五次修正（2026-09-14，明鉴差异定位引出）：**以 `-` 或 `/` 结尾的候选是截断伪键**。
      实测：源卡正文里写着 `data/registry/hr-reply-mingjian-*`（**通配符**），正则会把
      `data/registry/hr-reply-mingjian-` 整个当成一个键 ⇒ 一个**从不存在的键**混进清单。
      ⇒ 处置不是「静默丢掉」（那是又一次静默收窄），而是**单列为「疑似截断」并打印**：
      它参与不了任何比率，但必须让人看见（未过滤量纪律）。
    ★ 更根本的教训（见 ⑥）：**抽取规则不能改写前缀**。改前缀会**保住基数** ⇒ 任何
      「数一数对不对」的检查都看不见它（丢弃型错误会改基数，因此可见；改写型不会）。
    """
    out, susp = [], []
    for m in list(STRICT_RE.finditer(text or "")) + list(AFTER_MARK.finditer(text or "")):
        raw = m.group(1).rstrip(TRAIL)
        if raw.endswith("-") or raw.endswith("/"):
            if raw not in susp:
                susp.append(raw)
            continue
        k = raw.rstrip("/")
        if k and "/" in k and k not in out:
            out.append(k)
    return (out, susp) if with_suspicious else out


def resolve(keys, bb=DEFAULT_BB, workers=12, timeout=15):
    """逐个 GET。返回 {key: ("exists"|"missing"|"illegal"|"error", detail)}。"""
    from concurrent.futures import ThreadPoolExecutor

    def one(k):
        url = f"{bb}/{k}"
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                body = r.read()
                # ★ 引用完整性还要看**被引对象是不是墓碑**（2026-09-14 实测：node 反复发
                #   「看黑板 notes/mac-mini/<自测卡>」，而那些卡 status=void ⇒ 读者点进去
                #   什么也拿不到 ⇒ 这类通知**无信息量**。指针能解析 ≠ 指针有意义。
                try:
                    st = str((json.loads(_decode_strict(body)).get("value") or {}).get("status", "")).strip().lower()
                except Exception:                    # noqa: BLE001
                    st = ""
                # ★★ 墓碑 ≠ 占位（2026-09-14 实测自我修正）：我原把 `stub` 与 `void` 并作「无内容」，
                #   但我**自己的占位卡是带内容的**（15 字段 + 活量快照对象）⇒ 「stub ⇒ 无信息量」是错的。
                #   ⇒ 只有 `void`（曾存在·已作废）走无信息量分支；`stub`（占位）**可能有内容，须继续读**。
                if st in ("void", "tombstone"):
                    return k, ("void", f"HTTP {r.status} · status={st}（作废/墓碑 ⇒ 无内容）")
                _stub = " · status=stub（占位卡：**可能有内容，须读**；不判为无信息量）" if st == "stub" else ""
                # ★ 引用时自动比对「活量快照」（明鉴 2026-09-14 ②：门要真成门，须在【引用时】自动比较；
                #   她的理由：过时只在被引用时才有害 ⇒ 门设在此处成本最低、正好挡住真危害）。
                _warn = _stale_snapshot_warn(k, body)
                return k, ("exists", f"HTTP {r.status}" + _stub + (_warn or ""))
        except urllib.error.HTTPError as e:
            code = e.code
            return k, ("missing" if code == 404 else ("illegal" if code == 400 else "error"),
                       f"HTTP {code}")
        except Exception as exc:                     # noqa: BLE001
            return k, ("error", f"{type(exc).__name__}")

    if not keys:
        return {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return dict(ex.map(one, keys))


def _bus_sha_prefix(n=22):
    try:
        import hashlib
        raw = open(os.path.expanduser("~/.dsh/agent-bus.json"), "rb").read()
        return hashlib.sha256(raw).hexdigest()[:n]
    except Exception:                                # noqa: BLE001
        return None


def _stale_snapshot_warn(k, body):
    """卡内若带「依据快照」（形如 `总线内容标识`: `sha256:<hex>`），引用时自动比对当前源。
    ★ 性质声明（明鉴 2026-09-14 ②）：**这仍然是【诊断】，不是【门】** —— 它只报「可能过期」，
      不阻断引用（因为「引用一个已知过期的值」有时是合法的：那正是它标注了截至时刻的用意）。
      ⇒ 判据：同一个比对放在不同位置，性质不同 —— **引用时 = 可阻断（门）· 读时 = 只报（诊断）**。
      本函数当前实现为诊断；若要升为门，须另立参数与退出码（未做，明示）。"""
    try:
        v = json.loads(_decode_strict(body)).get("value") or {}
    except Exception:                                # noqa: BLE001
        return None
    txt = json.dumps(v, ensure_ascii=False)
    import re as _re
    m = _re.search(r"sha256:([0-9a-f]{8,})", txt)
    if not m:
        return None
    rec = m.group(1)
    cur = _bus_sha_prefix(len(rec))
    if cur is None:
        return " · ⚠ 卡内含依据快照但**当前源取不到** ⇒ 未核（不得读成一致）"
    if rec != cur:
        return f" · ⚠**活量快照可能已过期**：卡内记录 {rec[:12]}… ≠ 当前总线 {cur[:12]}…"
    return " · 依据快照与当前总线一致"




# ============================================================================
# to 字段层闸门（v3.1.0 · 2026-10-08 · 采纳 MBP 五规则草案）
# ★ 层级声明（必须显式，否则误放行）：本闸门判的是 **agent-way 消息 to 字段层**
#   （会话查找 agentsSvc.get(to)），**不是**总线 target 层（服务器路由）。
#   实证：`bus:<node>` 在 target 层可达（服务器路由），在 to 字段层 21/21 不可达
#   ⇒ 入队即死。若按「可达」放行，这 21 条死信会被判合法（判据层错位）。
# ============================================================================
import re as _re

FULL_UUID = _re.compile(r'^session-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', _re.I)
SHORT_ID = _re.compile(r'(^|\s)session-[0-9a-f]{8}$', _re.I)
BUS_PREFIX = _re.compile(r'^bus:', _re.I)
TRUNC_UUID = _re.compile(r'^session-[0-9a-f]{8}-[0-9a-f]{0,11}$', _re.I)   # 截断/不完整


def classify_to(to, registered=None):
    """判 to 字段层可达性。返回 (klass, verdict, advice)。
    klass ∈ {registered, full-uuid, unreachable-form}；verdict ∈ {pass, warn, refuse, unknown}"""
    t = String_(to)
    reg = set(registered or [])
    if t in reg:
        return ('registered', 'pass', '命中本机已登记 agentId ⇒ 放行')
    if FULL_UUID.match(t):
        return ('full-uuid', 'pass', '当前无 TTL/无死信回收：'
                '该形态合法，目标离线时入队属「合法排队·未证消费」')
    if (' ' in t) or SHORT_ID.search(t) or BUS_PREFIX.match(t) or TRUNC_UUID.match(t):
        return ('unreachable-form', 'refuse',
                '该形态在**本层（agent-way to 字段层）不可解析** ⇒ 消息将永久滞留。'
                '跨机请写黑板 notes/collab/（或对方节点 notes/<node>/），不要用节点别名/裸名/bus: 前缀/截断 id')
    # 裸名字：非 session- 形态且不含空格
    if not t.startswith('session-'):
        return ('unreachable-form', 'refuse',
                f'裸名字「{t}」在 to 字段层不可解析（本层只认完整 session uuid 或已登记 agentId）'
                ' ⇒ 跨机改用黑板卡')
    return ('unknown', 'unknown', '形态未覆盖 ⇒ 不读成通过，请人工确认（手段失败≠通过）')


def String_(x):
    return '' if x is None else str(x)


def check(text, to=None, bb=DEFAULT_BB, verify=True):
    """返回 (verdict, reason, advice, refs)。verdict ∈ {pass, warn, refuse, unknown}"""
    length = len(text)
    has_bb_ref = "看黑板" in text
    has_urgent = "urgent" in text.lower()
    keys = extract_keys(text)
    refs = resolve(keys, bb) if (verify and keys) else {}

    bad = [k for k, (st, _d) in refs.items() if st in ("missing", "illegal")]
    err = [k for k, (st, _d) in refs.items() if st == "error"]

    # 引用完整性优先于一切（引用了不存在的键，无论长短都是硬缺陷）
    if bad:
        det = " · ".join(f"{k}（{refs[k][1]}）" for k in bad)
        return ("refuse", f"引用 {len(bad)}/{len(keys)} 个键无法解析：{det}",
                "先写卡并回读确认（PUT 后必须 GET），再发指针；400=名非法 ⇒ 该键从未可能存在",
                refs)
    if err:
        det = " · ".join(f"{k}（{refs[k][1]}）" for k in err)
        return ("unknown", f"黑板不可达 ⇒ {len(err)} 个引用未核（**不得读成通过**）：{det}",
                "改用 --bb 指定实例，或稍后重试；未核 ≠ 存在", refs)

    void = [k for k, (st, _d) in refs.items() if st == "void"]
    if void and len(void) == len(refs):
        return ("warn", f"引用的 {len(void)} 个键**全部是作废/墓碑卡**（status=void）⇒ 无信息量",
                "作废卡只保证「曾经存在」，点进去没有内容；若要通知请引用内容卡"
                "（注：`status=stub` 的**占位卡**不在此列 —— 它可能有内容，须读）", refs)
    if length <= THRESHOLD:
        return ("pass", f"短消息（{length} 字）" + (f" · 引用 {len(keys)} 个键全部存在" if keys else "")
                + (f"（其中 {len(void)} 个是墓碑卡）" if void else ""), None, refs)
    if has_bb_ref:
        return ("pass", f"含看黑板引用（{length} 字）" + (f" · 引用 {len(keys)} 个键全部存在" if keys else ""), None, refs)
    if has_urgent:
        return ("pass", f"紧急标记 urgent（{length} 字）", None, refs)
    if not keys:
        return ("warn", f"全文 {length} 字且无黑板引用",
                "请先写黑板（notes/mac-mini/<key> 或 data/<域>/<key>），再发『看黑板 <key>』", refs)
    return ("warn", f"全文 {length} 字（提及黑板路径，需确认已落盘）",
            "消息提到黑板路径，请确认内容已写入黑板；已写则改为发『看黑板 <key>』", refs)


def load_bus(path=None, tries=20, delay=0.35):
    """总线是 20MB 单文件就地重写 ⇒ 撕裂读必然发生，解析+重试是必需项。"""
    path = path or os.path.expanduser("~/.dsh/agent-bus.json")
    last = None
    for _ in range(tries):
        try:
            with open(path, "rb") as f:
                return json.loads(_decode_strict(f.read()))
        except Exception as exc:                     # noqa: BLE001
            last = exc
            time.sleep(delay)
    raise RuntimeError(f"总线解析失败（{tries} 次重试）: {last}")


def replay_bus(bb=DEFAULT_BB, path=None):
    """复盘：全总线上引用黑板的键，解析率是多少、按发送者分。
    ★ 未过滤量先打印（凡引入过滤/分组规则，须同时给出未过滤的量）。"""
    bus = load_bus(path)
    msgs = 0
    susp_all = set()
    per_sender = {}
    all_keys, per_sender_keys = set(), {}
    for t in bus.get("threads", []):
        for m in t.get("messages", []):
            msgs += 1
            ks, sp = extract_keys(str(m.get("text", "")), with_suspicious=True)
            susp_all.update(sp)
            if not ks:
                continue
            who = str(m.get("from") or "?")
            s = per_sender.setdefault(who, {"msgs": 0, "keys": set()})
            s["msgs"] += 1
            s["keys"].update(ks)
            all_keys.update(ks)
            per_sender_keys.setdefault(who, set()).update(ks)
    print(f"总消息 {msgs} 条（未过滤量）· 含黑板引用的消息 {sum(s['msgs'] for s in per_sender.values())} 条"
          f" · 发送者 {len(per_sender)} 个 · 唯一引用键 {len(all_keys)} 个")
    if susp_all:
        print(f"⚠ 疑似**截断伪键** {len(susp_all)} 个（以 `-`/`/` 结尾 ⇒ 多半是正文里的通配符被正则吃掉）"
              f"：{' · '.join(sorted(susp_all)[:6])}")
        print("   ⇒ 已从键集合中剔除（剔除是**出声**的，不是静默的）；它们**从不参与比率**。")
    res = resolve(sorted(all_keys), bb)
    tally = {"exists": 0, "void": 0, "missing": 0, "illegal": 0, "error": 0}
    for _k, (st, _d) in res.items():
        tally[st] = tally.get(st, 0) + 1
    ok = tally["exists"]
    print(f"全库解析：存在 {ok} · **墓碑/占位（status=void/stub）{tally['void']}** · 404（名合法但不存在）{tally['missing']} · "
          f"400（名非法）{tally['illegal']} · 取不到 {tally['error']} ⇒ 失效 "
          f"{tally['missing'] + tally['illegal']}/{len(all_keys)}"
          + (f" = {(tally['missing'] + tally['illegal']) / len(all_keys) * 100:.1f}%" if all_keys else ""))
    print("★ 对象声明（否则这三个数都会被误读）：本行测的是「**在某一个实例上可解析**」，"
          "不是「键存在」——\n  bb-put-both 已证两实例**独立可写、无自动同步** ⇒ 404 里含着"
          "「只写了另一侧」的那批。\n  要判「存在」须**两实例都 GET**；本行默认只打 --bb 那一个。")
    print("\n按发送者（键级去重；一个键被多人引用时各计一次）：")
    rows = []
    for who, s in per_sender.items():
        bad = sum(1 for k in s["keys"] if res.get(k, ("error",))[0] in ("missing", "illegal"))
        rows.append((bad / max(len(s["keys"]), 1), who, s["msgs"], len(s["keys"]), bad))
    for r, who, nm, nk, bad in sorted(rows, reverse=True):
        print(f"  {who[:46]:<48} 消息 {nm:>4} · 键 {nk:>4} · 失效 {bad:>3} = {r * 100:>5.1f}%")
    return {"messages": msgs, "unique_keys": len(all_keys), "tally": tally, "per_sender": rows}


SELFTEST = [
    ("抽键·data/registry/xxx", extract_keys("看黑板 data/registry/abc-20260914") == ["data/registry/abc-20260914"]),
    ("抽键·剥尾随标点", extract_keys("看黑板 notes/mac-mini/x-20260914。") == ["notes/mac-mini/x-20260914"]),
    ("抽键·不吃 URL 域名尾段", extract_keys("http://a.example.com/x/y 无键") == []),
    ("抽键·去重保序", extract_keys("data/a/x 和 data/a/x") == ["data/a/x"]),
    # ★ 负例（实测缺口）：名非法的键必须被抽出来，否则门禁对 400 类完全失明
    ("抽键·**名非法也要抽出**（cld-health/foo ⇒ 400）",
     extract_keys("看黑板 cld-health/foo") == ["cld-health/foo"]),
    ("抽键·**不误抽** URL/版本串（宽松档仅在『看黑板』之后生效）",
     extract_keys("见 HTTP/1.1 与 a.example.com/x") == []),
    # ★ 负例（实测：这一条曾把失效率先报成 29.5%）
    ("抽键·**散文里的字段列表/文件路径不算引用**（id/name/… · lib/x.js · scripts/y.mjs）",
     extract_keys("字段列表 id/name/version/stages/ts 与文件 lib/monitor.js、scripts/build.mjs") == []),
    # ★ 正例：但被「看黑板」显式标记的，任何形状都要抽出来
    ("抽键·『看黑板』之后的非常规名照样抽出（含名非法与非白名单命名空间）",
     extract_keys("看黑板 lib/monitor.js") == ["lib/monitor.js"]),
    # ★ 截断伪键必须被单列，而不是当成键（也不是静默丢掉）
    ("抽键·**通配符被吃掉产生的截断伪键**单列（`data/registry/hr-reply-mingjian-*`）",
     extract_keys("见 data/registry/hr-reply-mingjian-* 一族", with_suspicious=True)
     == ([], ["data/registry/hr-reply-mingjian-"])),
    # ★ 负例（实测：这一条曾造出 1289 个「取不到」= 全库 26%，根因是漏排全角左括号）
    ("抽键·**不吃中文括号正文**（`data/x/y（已监控）`）",
     extract_keys("看黑板 data/external-link/wecom-image-probe（已监控）") ==
     ["data/external-link/wecom-image-probe"]),
]


def selftest():
    ok = 0
    for name, good in SELFTEST:
        ok += 1 if good else 0
        print(f"  {'✅' if good else '❌'} {name}")
    return 0 if ok == len(SELFTEST) else 1


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--text")
    ap.add_argument("--to")
    ap.add_argument("--bb", default=DEFAULT_BB)
    ap.add_argument("--no-verify", action="store_true", help="跳过引用 GET（离线时用；会明确标注未核）")
    ap.add_argument("--replay-bus", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if args.version:
        import hashlib
        import datetime
        try:
            sha = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()[:16]
        except Exception:                            # noqa: BLE001
            sha = None
        print(json.dumps({"tool": "bb-send-check", "version": VERSION, "file_sha256": sha,
                          "reported_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"),
                          "gate": "引用完整性（看黑板 <key> ⇒ 逐个 GET）"},
                         ensure_ascii=False))
        return 0
    if args.replay_bus:
        r = replay_bus(args.bb)
        if args.json:
            print(json.dumps(r, ensure_ascii=False, default=str, indent=1))
        return 0
    if not args.text:
        ap.error("需要 --text（或 --selftest/--version/--replay-bus）")

    verdict, reason, advice, refs = check(args.text, args.to, args.bb, verify=not args.no_verify)
    if args.json:
        print(json.dumps({"verdict": verdict, "reason": reason, "advice": advice,
                          "len": len(args.text), "refs": {k: list(v) for k, v in refs.items()}},
                         ensure_ascii=False))
        return 0 if verdict == "pass" else (2 if verdict == "refuse" else (3 if verdict == "unknown" else 1))
    icon = {"pass": "✅", "warn": "⚠️", "refuse": "❌", "unknown": "❓"}[verdict]
    print(f"{icon} {reason}")
    if advice:
        print(f"   → {advice}")
    if refs:
        for k, (st, d) in refs.items():
            print(f"   · {k} ⇒ {st} ({d})")
    if args.to:
        print(f"   → 收件人: {args.to}")
    return 0 if verdict == "pass" else (2 if verdict == "refuse" else (3 if verdict == "unknown" else 1))


if __name__ == "__main__":
    sys.exit(main())
