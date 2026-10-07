#!/usr/bin/env python3
"""双写双回读落卡：PUT 到本机与中央两个黑板实例，再各自回读核对。

用法：
  python3 put-card.py <纯内容JSON路径> <黑板键>

输入 JSON 必须是【纯内容】（即 value 本身），外层 key/ts 由黑板生成。
由来：2026-09-14 曾把整卡当 body 提交 ⇒ 黑板把整卡存为 value ⇒ 两层。

★ 2026-09-22 加：落卡尝试日志（让失败留痕）。
  起因：我报过「写卡引号错成功率约 1/8」，而那个分母是【估的】—— 我从没为拦截记过账。
  HR 2026-09-22 把这条提为规则：纪律类措施须报成功率，否则无法判断是否该换成结构解；
  而「成功率也有分母，分母要能核」（同「通过也有分母」）。
  ⇒ 本脚本每次【尝试落卡】都记一行（成功/失败都记）⇒ 分母自动存在。
  日志：~/dsh-collab/logs/put-card-attempts.log（TSV：时刻 · 结果 · 键 · 文件 · 备注）
"""
import json, sys, os, math, datetime, urllib.request

LOG = os.path.expanduser("~/dsh-collab/logs/put-card-attempts.log")

if len(sys.argv) >= 2 and sys.argv[1] in ("-h", "--help"):
    print(__doc__)
    sys.exit(0)

# ★ 2026-09-28 加 --selftest / --dry-run：
#   起因：今天的三类失败对照（文件不存在 / 内容坏 / NaN）是**我人工跑的一次性命令**，
#   没有封进工具 ⇒ 按「贵的判断不落进工具就会被放弃」，它们下次改代码时不会自动重跑。
#   正控必需：一个「什么都拒绝」的工具也能通过三个拒绝对照 ⇒ 必须有 must_pass 那一例。
#   dry-run = 走到内联检查之后、PUT 之前就停，不落卡、不写日志 ⇒ 正控不产生副作用。
if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
    import subprocess, os as _os
    _st = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "put-card-selftest.py")
    if not _os.path.exists(_st):
        sys.exit("找不到 put-card-selftest.py（约定：兄弟文件，同 card-json-check-selftest.py）")
    sys.exit(subprocess.run([sys.executable, _st], text=True).returncode)

if len(sys.argv) < 3:
    sys.exit("用法: put-card.py <纯内容JSON路径> <黑板键> [--dry-run]\n"
             "      put-card.py --selftest        # 跑兄弟自测文件（含 4 反控 + 1 正控）")

# ★ 2026-09-28 加：未知选项必须有声拒绝。
#   起因（实测）：`--dryrun`（把 --dry-run 打错一个字）会被【静默忽略】⇒ 脚本**照常落卡**
#   —— 实测命令 `put-card.py <good.json> <key> --dryrun` ⇒ exit=0 · 日志新增 1 行（真落了一张卡）。
#   ⇒ 一个拼错的安全旗标，会静默地做危险的事。这正是老登那条一般化的形态：
#     **探针要测的是【不认识的输入】这一类，不是一个特定参数**。
#   ★ 同时把位置参数改为「过滤掉 - 开头者」⇒ 旗标可放在任意位置（原先只认 argv[1]/[2]）。
# ★ 2026-09-28：加旗标必须同时登记进 _FLAGS —— 否则被下面那道守卫当场拦下。
#   实测：我加了 --allow-missing-checker 却忘了登记 ⇒ 路 2 直接报「不认识的参数」⇒
#   与今天那条「加标签前先查重」同型：**加旗标前先注册**。
_FLAGS = {"--dry-run", "--allow-missing-checker"}
_unknown = [a for a in sys.argv[1:] if a.startswith("-") and a not in _FLAGS]
if _unknown:
    print(f"❌ 不认识的参数: {' '.join(_unknown)}")
    print(f"   本工具接受的旗标: {' '.join(sorted(_FLAGS))}")
    print("   ★ 这道检查的起因：`--dryrun` 曾被静默忽略 ⇒ 脚本照常落卡（拼错的安全旗标会静默失效）")
    sys.exit(2)
_pos = [a for a in sys.argv[1:] if not a.startswith("-")]
if len(_pos) < 2:
    sys.exit("用法: put-card.py <纯内容JSON路径> <黑板键> [--dry-run]")

DRY = "--dry-run" in sys.argv
path, key = _pos[0], _pos[1]
now = datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def log_attempt(result, note=""):
    """每次尝试落卡都记一行 —— 成功与失败都记，分母才完整。"""
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("\t".join([now, result, key, os.path.basename(path), note.replace("\t", " ")]) + "\n")
    except Exception as e:
        print("  （日志写入失败:", str(e)[:50], "）")


# ── 解析（失败即记一条 ⇒ 这就是「引号错」这类拦截的分母）
# ★ 2026-09-28 改：把【输入文件不存在】从 PARSE_FAIL 里分出来，标签 INPUT_MISSING。
#   起因（实测，2026-09-28 08:41）：我全天报「今日 8 次失败全是 JSON 语法错」，
#   而逐条核账本发现是 10 条 —— 两条的 note 是 `[Errno 2] No such file or directory`，
#   即【生成脚本先失败了、JSON 文件从未存在】，被下面的 `except Exception` 兜住记成 PARSE_FAIL。
#   ⇒ 一个标签对应两类对象（内容坏 / 文件不存在）⇒ 不可区分 ⇒ 读数错一整天而不自知。
#   ⇒ 且那一支的出路提示「重写整份 JSON」把排查方向指向不存在的内容，是【死路】。
#   ★ 加标签前先查重：`READ_FAIL` 已在下文（二次 PUT 前的回读）使用 ⇒ 不能复用，故取 INPUT_MISSING。
try:
    card = json.load(open(path, encoding="utf-8"))
except FileNotFoundError as e:
    msg = str(e)[:120].replace("\n", " ")
    log_attempt("INPUT_MISSING", msg)
    print("❌ 输入文件不存在（已记入日志）：", msg)
    print("   ⇒ 真正的失败在【更早一步】：生成脚本没写成功（Python 报错 / 路径写错）")
    print("   ⇒ 出路：去看生成脚本自己的报错，不要去改 JSON 内容（它根本不存在）")
    sys.exit(2)
except json.JSONDecodeError as e:
    msg = str(e)[:120].replace("\n", " ")
    log_attempt("PARSE_FAIL", msg)
    print("❌ JSON 解析失败（已记入日志）：", msg)
    print("   ⇒ 出路：用 write 重写整份 JSON（内容里用汉字引号「」，不要用 ASCII 双引号）")
    sys.exit(2)
except Exception as e:
    # ★ 2026-09-28 改：catch-all 必须【报出它吞的是哪一类】。
    #   起因（实测）：老登那条判据「我这一档的计数，会不会把另一类东西也数进来了？」
    #   ⇒ 我量了自己的历史账本：**17 行 PARSE_FAIL 里实际混了 5 类**——
    #     12× Expecting ',' delimiter · 2× FileNotFoundError · 1× Expecting property name ·
    #     1× Expecting ':' delimiter · 1× Invalid \escape ⇒ 而它**从没报过自己吞了几类**。
    #   修法：解析失败收窄到 json.JSONDecodeError，其余一律进本支并【把异常类名写进标签】。
    #   ⇒ 此后「这个 catch-all 吞了几类」是一个可查询的数：
    #     awk -F'\t' '$2 ~ /^READ_OTHER/ {print $2}' 日志 | sort -u
    #   ★ 历史 17 行仍是混合标签 —— 改标签不能修历史读数（对历史只能按 note 字段二次分类）。
    cls = type(e).__name__
    msg = str(e)[:110].replace("\n", " ")
    log_attempt(f"READ_OTHER:{cls}", msg)
    print(f"❌ 读卡失败 · catch-all 吞的是【{cls}】（已记入日志，标签带类名）：", msg)
    print("   ⇒ 本支现在是唯一的兜底：它每次都会写明类名，所以「吞了几类」可查")
    sys.exit(2)

# ★ 2026-09-28 加：非有限浮点闸门（NaN / Infinity）。
#   起因：json.dumps 对 float('nan') 产出 `NaN` 这个 token —— 不是合法 JSON，
#   而 Python 的 json.load 默认放行 ⇒ 上面那道解析闸门对它是【盲的】
#   （card-json-check.py 同样只用 json.loads，第 11 行，也盲）。
#   实测（2026-09-28 08:41，一次性键 probe-nan-json-gate-20260928，测完已删）：
#   服务端返回 400 `invalid body: expected JSON` + `expected value at line 1 column 35`
#   ⇒ 接住它的是服务端，不是我的闸门。本段把接住的位置提前到【提交前】。
#   对应结论：结构层可【消除】（产出物由 json.dumps 序列化，不经过我的手），
#   而值层只能【设防】—— 设防清单原来只列了引号/换行/反斜杠，漏了【非有限浮点】。


def _nonfinite(o, p="$"):
    if isinstance(o, float):
        return None if math.isfinite(o) else p
    if isinstance(o, dict):
        for k, v in o.items():
            r = _nonfinite(v, f"{p}.{k}")
            if r:
                return r
    elif isinstance(o, list):
        for i, v in enumerate(o):
            r = _nonfinite(v, f"{p}[{i}]")
            if r:
                return r
    return None


# ★ 2026-09-28 改（第二版）：判定权交给【序列化器自己】，遍历降级为【诊断】。
#   起因：我原先让 `_nonfinite()` 自己 sys.exit —— 而它的闭合性来源依赖一条关于输入的断言
#   （「card 只可能来自 json.load，其取值域无 tuple」）。老登那条统一说：自检优先【调用它自己】，
#   无法调用才退回复刻；退回复刻时必须承认它只是【检查】。
#   而我上一卡又说过：`allow_nan=False` 加进来会「永远不会触发」⇒ 宁可不加。
#   ⇒ 两者其实不冲突，只要【替换而不是新增】：
#     · 判定层 = `json.dumps(..., allow_nan=False)` —— 依赖 **0 条**关于输入的断言，且**可达**
#       （NaN 会走到这里 ⇒ 它会抛 ⇒ 可触发，不是死代码）
#     · 诊断层 = `_nonfinite()` —— 仍在，但**只用来构造报错消息里的路径**，不参与放行/拦截
#   ⇒ 通则：**当「前提更少」与「可证明会触发」冲突时，不要让两层都做判定 ——
#     让前提少的那层判定，把前提多的那层降级为诊断（其输出只影响消息，不影响放行）。**
_nf = _nonfinite(card)

# ── ★ 2026-09-22 加：把检查【内联进落卡流程】。
#   起因：HR 要求报两项 —— 【拦截数】与【流出数】。我有拦截数的账，但没有流出数的账；
#   而根因是【「跳过检查」与「一次过」在我的日志里同形】：
#     一次过 ⇒ 只有 put-card 的 OK；跳过检查 ⇒ 也只有 put-card 的 OK ⇒ 无法区分。
#   ⇒ 修法不是"记得每次先跑检查"（那是纪律层），而是【让跳过检查不可能】：检查成为本流程的一步。
#   而这正是 HR 那一层的做法（让错误不产生），高于我原来那层（让错误被拦住）。
# ★ 2026-09-28 改：CHECKER 可经环境变量注入 —— 好让自测能覆盖「检查器缺失」这条入口。
#   起因（入口覆盖审计）：我【手工】验过「检查器缺失 ⇒ 拒落」与「--allow-missing-checker ⇒ 放行」，
#   但两条都【不在自测里】⇒ 按老登那条通则（覆盖率的单位是被经过的入口数），它们计数为零覆盖。
#   手法照抄他的 binding-check.py：`BB` 改为 `os.environ.get("BB_BASE", …)` 为自测可注入 stub。
CHECKER = os.environ.get("PUT_CARD_CHECKER",
                         os.path.expanduser("~/dsh-collab/scripts/card-json-check.py"))
if os.path.exists(CHECKER):
    import subprocess
    r = subprocess.run(["python3", CHECKER, path], capture_output=True, text=True)
    first = (r.stdout or r.stderr).strip().split("\n")[0][:100]
    print("  内联检查:", first, f"(exit={r.returncode})")
    if r.returncode != 0:
        log_attempt("CHECK_FAIL", first)
        print("❌ 内联检查未通过 ⇒ 拒绝落卡（已记入日志）")
        sys.exit(3)
elif "--allow-missing-checker" in sys.argv:
    print("  ⚠ 找不到检查器，跳过内联检查 —— 但这是【调用方显式放行】的（--allow-missing-checker）")
    log_attempt("NO_CHECKER_ALLOWED", CHECKER)
else:
    # ★ 2026-09-28 改：从「报警并继续」改成「报警并停下」。
    #   起因（实测）：我把副本的 CHECKER 指向不存在的路径 ⇒ 它打「⚠ 找不到检查器，跳过内联检查」
    #   并【继续走到落卡】⇒ 即 **有声但放行** ⇒ 而按今天新立的那个 2×2（声/哑 × 停下/继续），
    #   **「声 + 继续」是最危险的一格**：它看起来是可观测的，实际放行了。
    #   修法：默认拒落；要跳过必须显式给出 --allow-missing-checker（把「纪律」变成「结构」）。
    log_attempt("NO_CHECKER", CHECKER)
    print("❌ 找不到内联检查器 ⇒ 拒绝落卡（检查没跑过）")
    print(f"   缺的是: {CHECKER}")
    print("   ⇒ 若要显式跳过：加 --allow-missing-checker（并会在日志里留下 NO_CHECKER_ALLOWED）")
    sys.exit(2)

card["ts"] = now

# 判定层：序列化器自己（依赖 0 条关于输入的断言）—— 这一层可达，不是死代码。
try:
    body = json.dumps(card, ensure_ascii=False, allow_nan=False).encode("utf-8")
except ValueError as e:
    where = _nf or "（诊断层未定位到路径）"
    log_attempt("NONFINITE", f"{where} · {e}")
    print(f"❌ 含非有限浮点（NaN / Infinity）⇒ 不是合法 JSON：{where}")
    print(f"   判定者 = json.dumps(allow_nan=False)（{e}）")
    print("   ⇒ 出路：把该值改成字符串（'NaN' / 'null'）或删掉该字段")
    sys.exit(2)

if DRY:
    print("DRY-RUN：全部闸门（含序列化器自己的非有限浮点判定）都过 ⇒ 到此为止，"
          "不 PUT、不写日志（正控用，无副作用）")
    sys.exit(0)

HOSTS = ("127.0.0.1:8792", "106.53.214.108:8792")


def put(b):
    out = []
    for host in HOSTS:
        req = urllib.request.Request(
            f"http://{host}/{key}", data=b, method="PUT",
            headers={"Content-Type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                out.append((host, r.status))
        except Exception as e:
            out.append((host, "ERR", str(e)))
    return out


print("payload bytes:", len(body), "| ts =", card["ts"])
print("  PUT:", put(body))

reads = []
for host in HOSTS:
    try:
        with urllib.request.urlopen(f"http://{host}/{key}", timeout=20) as r:
            if r.status != 200:
                reads.append((host, f"非200({r.status})，不解析")); continue
            raw = r.read()
            d = json.loads(raw)
            # ★ 2026-09-22 修：此处原写 ver={d.get('version')} —— 用【我打的标签 ver=】显示
            #   【对象上的字段 version】⇒ 我每次看输出都读到 "ver=2"，就以为字段名叫 ver，
            #   于是在跨会话里长期报「收敛表 ver=38」（值对、字段名错）。
            #   ⇒ 根因是【显示层标签 ≠ 对象上的字段名】。修法是让标签就是字段名。
            reads.append((host, f"HTTP 200 | {len(raw)} B | env ts={d.get('ts')} version={d.get('version')} | 字段数={len(d.get('value', {}))}"))
    except urllib.error.HTTPError as e:
        reads.append((host, f"HTTP {e.code}（非200，不解析）"))
    except Exception as e:
        reads.append((host, f"ERROR {e}"))

for x in reads:
    print("  READ", x)

all_ok = all("HTTP 200" in s for _, s in reads)
log_attempt("OK" if all_ok else "READ_FAIL", "二次PUT前")

card["★ 本卡自身回执"] = " ｜ ".join(f"{h}: {s}" for h, s in reads)
put(json.dumps(card, ensure_ascii=False).encode("utf-8"))
print("二次 PUT（写入回执）完成")

# ★ 二次 PUT 会改内容（加回执字段）⇒ 内容标识必变。
#   此前我报的标识是【第一次 PUT 之前算的】⇒ 外人读到的永远是 ver=2 ⇒ 该标识永不可复现。
#   （驿使 2026-09-22 在我一张卡上实测抓到：他算得 181e05283c2852b8，而我报的是 931494d408b3f0f1。）
#   ⇒ 落卡完成后【重算并打印最终标识 + ver + 读取时刻】，我以后报的就是这个值。
import hashlib
print("★ 最终内容标识（两次 PUT 之后，此值才可被他人复现）：")
for host in HOSTS:
    try:
        with urllib.request.urlopen(f"http://{host}/{key}", timeout=20) as r:
            d = json.loads(r.read())
            h = hashlib.sha256(json.dumps(d.get("value", {}), sort_keys=True,
                                          ensure_ascii=False).encode()).hexdigest()[:16]
            print(f"    {host}: {h} (version={d.get('version')} ts={d.get('ts')})")
    except Exception as e:
        print(f"    {host}: ERR {str(e)[:40]}")
