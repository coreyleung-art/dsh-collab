#!/usr/bin/env python3
"""put-card.py 的可失败性自测：3 个反控（必须被拒）+ 1 个正控（必须通过）。

由来（2026-09-28）：
  我把落卡闸门的三类失败一次性验过 —— 文件不存在 / 内容坏 / 非有限浮点 ——
  但那三条是【人工跑的命令】，没有封进工具。按老登那条：
  「贵的判断不落进工具，它就会被放弃 —— 不是因为不想做，是因为每次都要人工做」
  ⇒ 封成自测，并给出正控。

为什么必须有正控：**一个「什么都拒绝」的工具也能通过全部反控。**
  只有反控 ⇒ 无法区分「拦得对」与「见谁都拦」⇒ 那是假阳性。

命名与放置：兄弟文件 put-card-selftest.py（与既有的
  card-json-check-selftest.py / dup-skeleton-selftest.py 同约定）。

自测日志：三条反控会在 put-card-attempts.log 各留一行，键一律带
  `zz-selftest` 前缀 ⇒ 使「我造错了」与「我写错了」在账上可分。
  正控走 --dry-run ⇒ 不写日志、不落卡（无副作用）。

用法：python3 put-card-selftest.py    ·    或 python3 put-card.py --selftest
退出码：0 = 全部符合预期；1 = 有不符合项。
"""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PUT = os.path.join(HERE, "put-card.py")
LOG = os.path.expanduser("~/dsh-collab/logs/put-card-attempts.log")
import sys

# ★ 2026-10-03 约定点守卫（MBP 方法论：裸 grep 不是判据，在约定发生点断言）：
#   自测/探针键必须落在无人监听前缀；落入 notes/<节点>/ 或 notes/collab/ 会自注入/打扰对端。
# ★ 2026-10-03 修复（MBP 实跑铁证）：KEY 必须在守卫之前定义（原顺序 NameError→自测全死、
#   且 exit1 与守卫生效无法区分=R31）；另：守卫拒绝用独立退出码 3 + 唯一标记 GUARD-REFUSED，
#   崩溃(1)/用例失败(1)/环境错(2)/守卫拒绝(3) 四态可区分。
KEY = "notes/_selftest/zz-selftest-putcard-20260928"  # 移出被监听前缀（notes/mac-mini 会被自己 central-inbox 注入=自污染）

_LISTENED = ["notes/mac-mini/", "notes/collab/", "notes/mbp/", "notes/i9/"]
if any(KEY.startswith(p) for p in _LISTENED):
    print("GUARD-REFUSED: 自测键 %s 落在被监听前缀（会自注入/打扰对端）。请改用 notes/_selftest/。" % KEY)
    sys.exit(3)

TMP = tempfile.mkdtemp(prefix="putcard-selftest-")
MISSING = os.path.join(TMP, "does-not-exist.json")
BADJSON = os.path.join(TMP, "bad-json.json")
NANCARD = os.path.join(TMP, "nan-card.json")
GOOD = os.path.join(TMP, "good-card.json")
# catch-all 的可触发入口：不是 JSON 文本 ⇒ json.load 抛 UnicodeDecodeError（非 JSONDecodeError）
RAWBYTES = os.path.join(TMP, "not-utf8.bin")

open(BADJSON, "w", encoding="utf-8").write('{"a": "坏的" "b": 1}')
open(NANCARD, "w", encoding="utf-8").write(json.dumps({"a": float("nan")}))
open(GOOD, "w", encoding="utf-8").write(json.dumps(
    {"from": "put-card-selftest", "type": "正控：这份必须通过三道闸门"}, ensure_ascii=False))
open(RAWBYTES, "wb").write(b"\xff\xfe\x00\x01 not json at all")


def run(args, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    r = subprocess.run([sys.executable, PUT] + args, capture_output=True, text=True, env=e)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def last_log_label():
    if not os.path.exists(LOG):
        return None
    rows = [l.rstrip("\n").split("\t") for l in open(LOG, encoding="utf-8") if l.strip()]
    for r in reversed(rows):
        if len(r) > 2 and r[2] == KEY:
            return r[1]
    return None


def label_is(got, want):
    """want 以 ':' 结尾表示前缀匹配（catch-all 的标签带异常类名，类名不写死在自测里）。"""
    if got is None:
        return False
    return got.startswith(want) if want.endswith(":") else got == want


def log_lines():
    if not os.path.exists(LOG):
        return 0
    return sum(1 for l in open(LOG, encoding="utf-8") if l.strip())


CASES = [
    ("反控·输入文件不存在", [MISSING, KEY], 2, "INPUT_MISSING", "文件不存在"),
    ("反控·JSON 内容坏", [BADJSON, KEY], 2, "PARSE_FAIL", "JSON 解析失败"),
    ("反控·非有限浮点 NaN", [NANCARD, KEY], 2, "NONFINITE", "非有限浮点"),
    ("反控·catch-all（非 JSON 文本）", [RAWBYTES, KEY], 2, "READ_OTHER:", "catch-all 吞的是"),
    ("反控·未知选项（拼错的 --dry-run）", [GOOD, KEY, "--zzz-bogus-flag"], 2, None, "不认识的参数"),
    # ★ 2026-09-28 加：把两条【只手工验过】的入口补进覆盖（入口覆盖审计的结果）
    ("反控·检查器缺失（默认拒落）", [GOOD, KEY, "--dry-run"], 2, "NO_CHECKER", "找不到内联检查器",
     {"PUT_CARD_CHECKER": "/tmp/definitely-missing-checker.py"}),
    ("正控·检查器缺失 + 显式开关（放行）", [GOOD, KEY, "--dry-run", "--allow-missing-checker"], 0,
     "NO_CHECKER_ALLOWED", "显式放行", {"PUT_CARD_CHECKER": "/tmp/definitely-missing-checker.py"}),
    ("正控·--help（打印用法即退）", ["--help"], 0, None, "用法"),
    ("正控·合法卡（--dry-run，不落卡）", [GOOD, KEY, "--dry-run"], 0, None, "DRY-RUN"),
]

# ★ 标题的数字也必须由 CASES 算出来 —— 写死的数字在加用例后会撒谎。
#   （实测：我加了 3 条用例后，标题仍写「5 反控 + 1 正控」⇒ 它当场变成假的）
_n_neg = sum(1 for c in CASES if c[0].startswith("反控"))
_n_pos = sum(1 for c in CASES if c[0].startswith("正控"))
print(f"put-card 闸门自测（{_n_neg} 反控 + {_n_pos} 正控 · 共 {len(CASES)} 例）")
print("被测工具:", PUT)
print()
fails = []
for case in CASES:
    name, args, want_exit, want_label, want_text = case[:5]
    extra_env = case[5] if len(case) > 5 else None
    before = log_lines()
    code, out = run(args, extra_env)
    grew = log_lines() - before
    ok_exit = code == want_exit
    ok_text = want_text in out
    if want_label:
        got = last_log_label()
        ok_label = label_is(got, want_label) and grew == 1
        label_info = f"日志新增 {grew} 行 · 标签={got}（期望 {want_label}）"
    else:
        ok_label = grew == 0          # 正控不得写日志（无副作用）
        label_info = f"日志新增 {grew} 行（期望 0 —— 正控不落卡、不留痕）"
    ok = ok_exit and ok_text and ok_label
    print(f"  {'✅' if ok else '❌'} {name}")
    print(f"      exit={code}（期望 {want_exit}）· 命中输出={ok_text} · {label_info}")
    if not ok:
        print("      输出首行:", out.strip().split("\n")[0][:120])
        fails.append(name)

print()
pass_n = len(CASES) - len(fails)
# ★ 机器可读标识拆成【反控/正控两组】，不只报合计：
#   老登那条 ——「5/5 却没有 must_pass」本身就是一个「看起来正常」的读数 ⇒
#   只报合计会掩盖「全是反控、没有正控」这个缺口（而那个缺口等于没有正控）。
neg = [c for c in CASES if c[0].startswith("反控")]
pos = [c for c in CASES if c[0].startswith("正控")]
neg_ok = sum(1 for c in neg if c[0] not in fails)
pos_ok = sum(1 for c in pos if c[0] not in fails)
print(f"结果：{pass_n}/{len(CASES)} 符合预期（反控 {neg_ok}/{len(neg)} · 正控 {pos_ok}/{len(pos)}）")
marker = f"SELFTEST put-card 反控 {neg_ok}/{len(neg)} 正控 {pos_ok}/{len(pos)}"
# ★ 通过条件里必须含「正控数 > 0」：全是反控的自测，一个「什么都拒绝」的工具也能通过。
if not fails and len(pos) > 0:
    print(marker)
    print("★ 反控与正控都成立 ⇒ 放行路径与拒绝路径都被这次自测走到")
    sys.exit(0)
print(marker.replace("SELFTEST put-card ", "SELFTEST put-card FAIL "))
if fails:
    print("不符合项:", " · ".join(fails))
if not pos:
    print("★ 缺口：本次自测【没有任何正控】⇒ 全是反控 ⇒ 一个「什么都拒绝」的工具也能通过 ⇒ 不合格")
sys.exit(1)
