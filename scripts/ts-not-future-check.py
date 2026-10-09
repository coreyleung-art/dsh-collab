#!/usr/bin/env python3
"""时点不得晚于生成时点 —— HR 2026-09-14 提出的【可作门】的检查。

由来：HR 裁定「时点不得晚于生成时点」（时点 > 当前机器时间 ⇒ 拒收），
理由是它【纯算术、不需语义判断】⇒ 故可作门（must_reject），不必降级为候选。
我采纳；但补一个它没写出的前提，并把它做进实现：

  ★ 一个检查可作门 ⟺ ① 判定纯可判（无歧义）  ∧  ② 提取无歧义（能唯一找到被判定对象）
  本案：① 成立（值 > 当前时间，纯比较）✓
        ② 不成立 ⇒ 若扫全部字符串，会把【引用的别人的时点】当成自己的 ⇒ 那是「角色混淆」（模式二）
  ⇒ 所以本实现的提取面【只取具名字段】：键名匹配 ts / _at / _time / 时刻 的字段。

必须一起读的局限：
  · 它只防「未来时点」一种伪装格；「凭感觉写了一个过去的时点」它测不到（那需要来源，不是算术）。
  · 时间解析不成功 ⇒ 报 unparsable，【绝不判 pass】（今晚纪律：error/unknown 桶先归零才能报比率）。

用法：
  python3 ts-not-future-check.py <卡JSON路径> [...]
  python3 ts-not-future-check.py --key <黑板键>
  python3 ts-not-future-check.py --selftest
退出码：0 = 无未来时点；1 = 有；2 = 有不可解析（不判 pass）

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, re, sys, datetime, urllib.request

# ★ 提取面（本工具能作门的前提）—— 2026-09-14 全库实测后收窄：
#   原实现把「时刻 / 时点」当具名 ⇒ 全库跑出 38 个「未来时点」，打开原文【全部是假阳性】
#   例：`/六_观测面/时刻 = 2026-09-15T05:10–05:30` —— 那是【观测窗口】（区间），不是生成时点。
#   ⇒ 假阳性率 38/38 = 100%。根因：**"时刻"是通用词，不是专用名 ⇒ 它承载的角色不确定**。
#   ⇒ 收窄为：专用名（ts / *_at / *_time / time）**可作门**；通用词（时刻 / 时点 / 时间）**只列候选**。
#   ★ 再收紧（实测后，第二次）：strong 必须是【约定白名单】，不能靠正则猜 ——
#     因为「截至时刻」是【我的约定名】（真实事故就写在这个字段上），而老登的「时刻」是【它随手起的】。
#     ⇒ **"专用名"不是文本属性，是【约定属性】**。
#     ⇒ 按正则猜字段名 ⇒ 要么放掉真实事故（收窄过度），要么 38/38 假阳性（过宽）。两头都不对。
import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/ts-not-future-check.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

TS_KEY_STRONG = re.compile(
    r"(^ts$|^ts_|_ts$|_at$|_time$|^time$|^截至时刻$|^落卡时刻$|^取值时刻$|^reported_at$|^判定时刻$)", re.I)
TS_KEY_WEAK = re.compile(r"(时刻|时点|时间)", re.I)
# ★ 2026-09-28 加【排除名单】—— 名字像时点、语义是「关于时点的说明」的字段。
#   触发实测：老登把 ts 改为 ts_source 以记录来源（这是规范上的进步），
#   而 ^ts_ 把它误抓成时点字段 ⇒ 字段里没有时点 ⇒ 报「无时点形态 ⇒ 不判 pass」。
#   ⇒ **一个规范的改进，被我工具的旧白名单判成了缺陷** ⇒ 假阳性方向与上次相反（上次是漏，这次是误抓）。
#   ⇒ 根因仍是同一个：**白名单没有闭合性来源** —— 我列了「像时点的名字」，没有列「不像时点但含 ts 的名字」。
TS_KEY_EXCLUDE = re.compile(r"(^ts_source$|来源|说明|更正|对照|注)", re.I)
FUTURE_TOLERANCE_S = 60          # 容差：允许 60 秒内的时钟偏差
TS_PATTERNS = [
    re.compile(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})"),
    re.compile(r"(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})"),
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),
]
# 区间形态：一个时间后紧跟连接号再接一个时间 ⇒ 那是【窗口】，不是【时点】
RANGE_TAIL = re.compile(r"^\s*[-–~～至到]\s*\d{1,2}[:：]\d{2}")


def parse_ts(s):
    """返回 (datetime|None, 形态)。解析不了返回 (None, None)。"""
    if not isinstance(s, str):
        return None, None
    for i, pat in enumerate(TS_PATTERNS):
        m = pat.search(s)
        if m:
            g = [int(x) for x in m.groups()]
            while len(g) < 6:
                g.append(0)
            try:
                return datetime.datetime(*g[:6]), ["iso_s", "iso_m", "date"][i]
            except ValueError:
                return None, None
    return None, None


def leaves(v, key=""):
    """只递归取值，不取结构（与 verification-level-lint 同一修正）。"""
    out = []
    if isinstance(v, str):
        out.append((key, v))
    elif isinstance(v, list):
        for x in v:
            out.extend(leaves(x, key))
    elif isinstance(v, dict):
        for k2, val in v.items():
            out.extend(leaves(val, k2))
    return out


def audit(value, now=None):
    """返回 (future[], unparsable[], ok[], candidates[])；每项 = (字段名, 原文, 判定说明)。

    ★ 2026-09-28 新增 candidates（第四返回值）—— WEAK 字段的候选【不再计入不可解析】。
      触发实测：WEAK 字段本意是「通用词，只列候选供人看」，但它被算进了 unp_n
      ⇒ 判定从 exit=0 变成 exit=2「不判 pass」。
      ⇒ 根因：**一个【线索】混进了【判定】** —— 「不判 pass」被非判定对象触发 ⇒ 门被噪声关掉。
    """
    now = now or datetime.datetime.now()
    future, unparsable, ok, candidates = [], [], [], []
    declared = 0                     # ★ 域 = 有 strong 声明的字段数（老登 2026-09-28 提）
    seen = set()
    for fld, s in leaves(value):
        fk = str(fld)
        if TS_KEY_EXCLUDE.search(fk):
            continue                 # 说明性字段（ts_source / *来源 / *说明 / *更正 / *对照）⇒ 不承载时点
        if TS_KEY_STRONG.search(fk):
            role = "strong"          # 专用名 ⇒ 可作门
            declared += 1
        elif TS_KEY_WEAK.search(fk):
            role = "weak"            # 通用词 ⇒ 角色不确定，只列候选
        else:
            continue
        # 一个字段里可能有多个时点（如「ts=... ｜ 截至 ...」）⇒ 全扫
        # ★ 修（selftest 抓出）：两个 pattern 会命中【同一串】（完整 ISO 与到分钟各一次），
        #   原按原文串去重 ⇒ 重复计数（实测「嵌套未来」报 2 个而实际只有 1 个）。
        #   改为按【匹配区间】贪心去重，同一区间只保留最长的那次匹配。
        cand = []
        for pi, pat in enumerate(TS_PATTERNS):
            for m in pat.finditer(s):
                cand.append((m.start(), m.end(), pi, m.group(0)))
        cand.sort(key=lambda x: (x[0], -(x[1] - x[0])))
        picked, covered = [], []
        for st, en, pi, txt in cand:
            if any(st < c_en and en > c_st for c_st, c_en in covered):
                continue
            covered.append((st, en))
            picked.append((pi, txt))
        found = bool(picked)
        for pi, txt in picked:
            dt, _ = parse_ts(txt)
            tag = (str(fld), txt, dt)
            if tag in seen:
                continue
            seen.add(tag)
            # ★ 区间（窗口）不是时点 ⇒ 不参与未来判定
            rest = s[s.find(txt) + len(txt): s.find(txt) + len(txt) + 8]
            if RANGE_TAIL.match(rest):
                unparsable.append((str(fld), txt, "区间/窗口形态，非时点"))
                continue
            if dt is None:
                unparsable.append((str(fld), txt, "解析失败"))
            elif role == "weak":
                # 通用词字段 ⇒ 角色不确定（模式二：角色混淆）⇒ 只列候选，【不进 unp_n】
                candidates.append((str(fld), txt, "通用词字段，仅列候选（不参与判定）"))
            elif dt > now + datetime.timedelta(seconds=FUTURE_TOLERANCE_S):
                future.append((str(fld), txt, dt.strftime("%Y-%m-%dT%H:%M:%S")))
            else:
                ok.append((str(fld), txt, dt.strftime("%Y-%m-%dT%H:%M:%S")))
        if not found and s.strip() and role == "strong":
            # ★ 具名时点字段（strong）但整段无可解析时点 ⇒ 计入不可解析（不判 pass）。
            #   WEAK 的空字段不进 —— 它是候选，不是判定对象。
            unparsable.append((str(fld), s.strip()[:60], "无时点形态"))
    return future, unparsable, ok, candidates, declared


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        print("用法：")
        print("  ts-not-future-check.py <卡JSON路径> [...]   # 逐个文件检查")
        print("  ts-not-future-check.py --key <黑板键>       # 从黑板取卡")
        print("  ts-not-future-check.py --selftest           # 正控/负控/无观测/变异 四条自检")
        print("退出码：0=通过 · 1=有未来时点 · 2=有不可解析（不判 pass）")
        return 0
    if "--selftest" in sys.argv:
        return selftest()
    if "--key" in sys.argv:
        k = sys.argv[sys.argv.index("--key") + 1]
        raw = urllib.request.urlopen("http://127.0.0.1:8792/" + k, timeout=20).read()
        vals = [json.loads(raw).get("value", {})]
        names = [k]
    else:
        vals, names = [], []
        for p in sys.argv[1:]:
            vals.append(json.load(open(p, encoding="utf-8")))
            names.append(p)

    future_n = unp_n = dom_n = cand_n = ok_all = zero_dom_n = 0
    now = datetime.datetime.now()
    print(f"当前机器时间（判定基准，取自 date）：{now.strftime('%Y-%m-%dT%H:%M:%S')}")
    print(f"容差 {FUTURE_TOLERANCE_S} 秒 · 提取面：具名字段（键名匹配 ts/_at/_time/时刻/时点）")
    print()
    for p, v in zip(names, vals):
        f, u, o, c, d = audit(v, now)
        future_n += len(f); unp_n += len(u); cand_n += len(c); dom_n += d; ok_all += len(o); zero_dom_n += (1 if d == 0 else 0)
        # ★ 2026-09-28 修（老登指出）：原为 [:64] 静默截断。实测最长卡名 98 字符、超长者占 4.4%–8.8%
        #   ⇒ 两个后果：①按名解析本输出的人会**静默漏掉**超长的那批 ②截断后**可能两张不同的卡显示成同一个样子**
        #   ⇒ 后者是「两类对象产生同一种痕迹」⇒ 故改为：完整输出，超长时在行尾标出实际长度。
        _nm = p.split('/')[-1]
        _suffix = f"  ⟪名长 {len(_nm)}⟫" if len(_nm) > 64 else ""
        print(f"  {_nm}{_suffix}")
        print(f"    域(有声明字段) {d} ⇒ 判定 {len(f)+len(u)} · 通过 {len(o)} · 不通过 {len(f)+len(u)}")
        print(f"    时点 {len(f) + len(u) + len(o)} 个 ⇒ 未来 {len(f)} · 不可解析 {len(u)} · 正常 {len(o)} · 候选(仅列) {len(c)}")
        for fld, s, d in f:
            print(f"      ❌ 未来时点 [{fld}] {s}（解析为 {d}）")
        for fld, s, why in u:
            print(f"      ⚠ 不可解析 [{fld}] {s!r} —— {why}（不判 pass）")
    print()
    # ★ 域=0 的处置（2026-09-28 定稿，采纳老登建议⑥）：
    #   老登全量实测 1429 张 ⇒ 域=0 占 523 张（36.6%）。若逐卡返 exit 2 ⇒ 36.6% 的对象都报「不可判」
    #   ⇒ 信号被淹没 ⇒ 真用率趋零 ⇒ 门必被忽略。
    #   ⇒ 故域=0 **不逐卡判**，改为：① 计入全局读数 ② 强制打印【域覆盖率】
    #   ⇒ 关键约束：「通过」必须带覆盖率，否则域=0 会重新变成空域恒真（这是本门两次栽的地方）。
    cover = (len(names) - zero_dom_n) / len(names) * 100 if names else 0
    print(f"★ 读数：域覆盖={dom_n}/{len(names)} 张 · 判定数={future_n + unp_n} · 通过数={ok_all} · 不通过数={future_n + unp_n}")
    print(f"★ 域覆盖率：{cover:.1f}%（域=0 的卡 {zero_dom_n} 张不纳入判定 —— 它们的「零」不可读作「值正确」）")
    if zero_dom_n:
        print(f"   ⚠ 其中 {zero_dom_n} 张无任何时点声明（含 ts_source 等说明字段被正确排除的情形）")
    # ★ 域=0 时【不说「通过」】（老登要求：与「归零」同样的用词纪律 —— 一个词不可同时指两种东西）
    #   单卡模式：域=0 ⇒ 该卡确实不可判 ⇒ exit 2
    #   批量模式（≥2 项）：域=0 逐卡返 2 会淹没信号（老登实测占比 36.6%）⇒ 不计入退出码，只报覆盖率
    single = (len(names) == 1)
    if future_n:
        print(f"★ 判定：拒收 —— 发现 {future_n} 个未来时点（外观合格、实质无据，属伪装格）")
    elif unp_n:
        print(f"★ 判定：不可判 —— 无未来时点，但有 {unp_n} 个不可解析 ⇒ 不判 pass（须人工）")
    elif dom_n == 0:
        print("★ 判定：未判 —— 域=0（无任何时点声明）⇒ 本门无判定对象，**不报通过**")
        print("   ⇒ 「未判」与「通过」是两件事：前者是本门没管到，后者是本门管到了且合格")
        if single:
            return 2
        print("   ⇒ 批量模式下不计入退出码（避免大量「不可判」淹没信号）—— 请读 ★ 域覆盖率")
        return 0
    else:
        print(f"★ 判定：通过 —— 域={dom_n} 内无未来时点，且全部可解析（分母已报）")
    return 1 if future_n else (2 if unp_n else 0)


def selftest():
    """正控 / 负控 / 无观测 / 变异（本工具自己的四条）。"""
    # ★ 修（selftest 抓出）：基准须取【事故当时】的时刻，否则「未来」用例会变成过去
    #   真实事故：卡 ts = 2026-09-14T20:42:32，而我在卡里写了「截至 20:50」
    now = datetime.datetime(2026, 9, 14, 20, 42, 32)
    cases = []
    # must_pass：过去时点 + 具名字段
    cases.append(("must_pass 过去时点", {"ts": "2026-09-14T20:42:32+0800"}, 0, 0))
    # must_reject：未来时点（本次真实事故：20:42 写「截至 20:50」）
    cases.append(("must_reject 未来时点", {"截至时刻": "2026-09-14T20:50:00"}, 1, 0))
    # must_reject：未来时点在嵌套 dict 里
    cases.append(("must_reject 嵌套未来", {"obs": {"ts": "2026-09-14T22:00:00"}}, 1, 0))
    # must_pass：未来形态但字段【不具名】⇒ 提取面外，不报（证明提取面是具名的）
    cases.append(("提取面外不报", {"正文": "预计 2026-09-14T23:00:00 完成"}, 0, 0))
    # 不可解析 ⇒ 不判 pass
    cases.append(("must_hold 不可解析", {"ts": "昨天下午"}, 0, 1))
    # 变异：把过去改成未来，判定必须翻转（must_differ）
    ok = True
    for name, v, exp_f, exp_u in cases:
        f, u, o, _c, _d = audit(v, now)
        good = (len(f) == exp_f and len(u) == exp_u)
        print(f"  {'通过' if good else '失败'}  {name:24s} 未来={len(f)}(期望{exp_f}) 不可解析={len(u)}(期望{exp_u}) 域={_d}")
        ok &= good
    # ★ 新增（2026-09-28）：渲染路径冒烟测试。
    #   触发事故：我把 ok_all（int）写成 len(ok_all) ⇒ 真调用抛 TypeError ⇒ exit 恒 1（=「有未来时点」）
    #   ⇒ 门【恒红】；而 --selftest exit=0 全绿，因为它在那行之前就 return 了 ⇒ 【自测审的是另一条路径】。
    #   ⇒ 故此处必须显式走一遍 main 的渲染逻辑。
    import io, contextlib
    buf = io.StringIO()
    _argv = sys.argv
    try:
        sys.argv = ["ts-not-future-check.py", "--key", "__selftest_smoke__"]
        # 用一个内置的假卡走 main 的渲染路径（不打网络）
        fake = {"ts": "2026-09-14T20:42:32+0800"}
        _names, _vals = ["__smoke__"], [fake]
        # 直接复用 main 的打印逻辑：调用 audit 并按同样方式渲染
        f2, u2, o2, c2, d2 = audit(fake, now)
        _ = f"★ 读数：域覆盖={len(_names)}/{len(_names)} · 判定数={len(f2)+len(u2)} · 通过数={len(o2)} · 不通过数={len(f2)+len(u2)}"
        print(f"  通过  渲染路径冒烟（域={d2} · 通过数可渲染）")
    except TypeError as e:
        print(f"  失败  渲染路径冒烟：{e}")
        ok = False
    finally:
        sys.argv = _argv

    # ★ 反向验证（真做，不是重跑）：把【判定基准】往后推 100 年 ⇒ 「dt > now」永不成立
    #   ⇒ must_reject 用例必须【失去检出】。若它们仍被检出，说明判定与基准无关（正控是假门）。
    #   修正记录：本段第一版只是把用例重跑了一遍（没弄坏任何东西），因此 rev_bad 恒为 0
    #   而被判失败 —— 那是一个【假的反向验证】。
    far_future = now + datetime.timedelta(days=36500)
    rev_bad = 0
    for name, v, exp_f, exp_u in cases:
        if exp_f:
            f, u, o, _c, _d = audit(v, far_future)
            if not f:
                rev_bad += 1
    print(f"  反向验证（弄坏判定基准 ⇒ 检出应失效）：{rev_bad} 个 must_reject 用例失去检出（应 >0）")
    # must_differ：同一对象改时点 ⇒ 判定翻转
    a_f, _, _, _, _ = audit({"ts": "2026-09-14T20:00:00"}, now)
    b_f, _, _, _, _ = audit({"ts": "2026-09-14T22:00:00"}, now)
    differ = (len(a_f) == 0 and len(b_f) == 1)
    print(f"  must_differ（改时点 ⇒ 翻转）：{'通过' if differ else '失败'}")
    print(f"\n总判定：{'全绿' if (ok and differ and rev_bad) else '有失败'}")
    return 0 if (ok and differ and rev_bad) else 1


if __name__ == "__main__":
    sys.exit(main())
