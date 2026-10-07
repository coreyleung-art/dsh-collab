#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-copy.py — 黑板**原样复制**唯一入口（回填/镜像专用）
版本：唯一来源 = 下方 VERSION 常量。**docstring 不写版本号** ——
  防「声明位漂移」（v1.0.1 自捕获：docstring 写 1.0.0 而常量已 1.0.1）；由 --check A7 断言。

为什么存在（先说清它不是什么）：
  2026-09-11 HR 对「已用结构堵两处」跑阳性对照的结论是 **③ 静默通过** ——
  `bb-write put --json '{"body":"重建文本"}'`（缺对象/范围）与 `put --body "重建文本"`
  （模板重建，正是回填事故的真实路径）**都 exit=0 静默成功，且静默丢掉源键全部字段**。
  ⇒ 当时那两处只是**约定**，不是结构；按「空通过」判据不能声称已堵。
  ⇒ 本工具是**把那条路径变没**的补丁：**不存在自由文本参数**，故「重建」在接口上无法表达。

结构性由三点构成（缺一即退化为约定）：
  ① 接口无自由文本：无 --body/--json/--subject；传了即 argparse 报错（重建路径不存在）
  ② 写入即带形状断言：把 **源键顶层键集合** 作为 bb-write `--expect-keys` ⇒ 少字段/多字段直接 exit 5
  ③ 写后先解包裹再语义逐字段比对：dst 必须与 src **字段对字段相等**，否则 exit 4 并列出差异字段
     （「HTTP 200 / 非空 / 自报一致」都不算完成判据 —— 完成判据只能是 dst==src 逐字段）

适用范围（★ v1.0.1 依明鉴 a190c54c 的边界补充：本工具**不是万能复制**，两条路径并列）：
  · **适用**：允许留存的键（能力/协议/流程/治理/登记卡）—— 原样复制 = 修复动作
  · **不适用**：**凭据/敏感键** —— 对凭据类信息「复制」本身就是**扩散动作**（Φ12 引用即复制），
    会在另一副本新增未受控副本。该场景应走**属主「不读只写」**路径：不读旧值 → 写新值 →
    两实例回读 + 只核对字段名、不打印值（该形态已被 HR 采纳）。
    ⇒ 本工具对含敏感字段的键**结构性硬拒**(exit 7)；键名疑似凭据类则**告警但仍允许**（防误拦）。
    ⇒ 越权须 `--allow-secret-fields`（明示决定 + 留痕），且差异输出**脱敏不打印值**。

四控的两极（★ 明鉴指出，勿把「四控」读成四个正控）：
  · **阳性对照**（样本已知不合规）：若仍报通过 ⇒ 抓**恒真/空通过** → 本工具 A1/A2/A4/A5/A6/A7/A9a
  · **阴性对照**（样本已知合规）：若仍报失败 ⇒ 抓**恒假/永远报警** → 本工具 A3/A9b
  · v1.0.1 增 A5（敏感硬拒必须真拒）+ A6（脱敏：输出中不得出现敏感值原文）
  · v1.0.2 增 A8（卡内语义锚点必须可解析）+ A9（引用核对正反控）
  ⇒ 两个对照缺一不可：只有正控会漏「永远报警」，只有负控会漏「空通过」。

引用纪律（★ v1.0.2 依明鉴 a190c54c 升级：行号不是「失效」，是「静默指错」）：
  · 行号随版本漂，且**漂后形式完好而指称已换** —— 本工具自身即一例：v1.0.1 的登记卡里
    `:111 / :160 / :300` 在加了 A7 之后落在**空行**上，读者看不出错。**断链会被发现，错指不会。**
  · ⇒ **引用以语义标识为主**（函数名/常量名/标记串），**行号只作辅助**；两者都要带被引对象的版本。
  · ⇒ 据此提供两件执行体（不是提醒）：
      ① **A8**：把**登记卡里声明的语义锚点**逐个在本源码中解析 ⇒ 改名/漂移即 FAIL；
         卡不可达 ⇒ `skipped`（三态，**不冒充通过**）
      ② **refcheck 子命令**：核对「引用」指向的字段是否真实存在（**字段名级引用**，不复制值）

三种传递形态（勿混为一谈）：
  ① **整值原样复制** → 本工具 `copy`（适用：允许留存的键）
  ② **字段名级引用** → 卡里列「来源键 + 字段名」让读者去读原键（安全）；可用 `refcheck` 校验字段名存在
  ③ **部分值复制**（摘字段值再组卡）→ **含选择=变形，本工具不支持**；应改为 ② 或请属主写一份

边界（诚实声明，勿越读）：
  · 对**采用者**是结构（用它就只剩原样复制一条路）；对**未采用者**仍只是可选工具 ——
    本工具**不强制任何人采用**，它只保证「经由本入口的复制一定是原样的」。
  · 敏感检测是**字段名模式匹配**（不是内容识别）⇒ 能证明「查出即拒」，**不能证明「没查出就一定安全」**。
  · 敏感硬拒可被 `--allow-secret-fields` 越过（同 bb-write 归属守卫 + --force 的形态）⇒ 级别是
    「默认拒 + 越权须明示 + 留痕」，**不是**「不可绕过」。
  · 读取源键失败/不可达 ⇒ exit 3（unknown，独立成项，**绝不并入一致**）
  · 不写黑板登记卡、不改他人键（沿用 bb-write 归属守卫；顶替需 --force 且此处默认不加）

用法：
  bb-copy.py copy <srcKey> <dstKey> [--src-server local|central] [--to local|central|both=默认]
                  [--from <身份>] [--force] [--dry-run]
  bb-copy.py verify <srcKey> <dstKey> [--src-server ...] [--to ...]     # 只比对不写
  bb-copy.py refcheck <key> <field...> [--src-server ...]                # 核对引用字段是否真实存在
  bb-copy.py --version | --check
退出码：0=全等 ｜ 2=本工具/参数错误 ｜ 3=无法判定(读失败) ｜ 4=内容不等/引用字段缺失(分叉)
        ｜ 5=写入被下游拒 ｜ 6=归属守卫 ｜ 7=敏感字段硬拒(凭据类键不该复制，见「适用范围」)
        ｜ 8=默认预检失败(版本声明位/语义锚点异常 —— 不进入写路径)
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, hashlib, json, os, re, subprocess, sys, urllib.request, urllib.error, datetime

VERSION = '1.0.109'
BB_WRITE = os.path.expanduser('~/dsh-collab/scripts/bb-write.py')
LOG_FILE = os.path.expanduser('~/dsh-collab/logs/external-link/bb-copy.log')
REPLICAS = {'local': '127.0.0.1:8792', 'central': '106.53.214.108:8792'}
TIMEOUT = 8
JSON_OUT = False          # R006 ⑨ 机器可读输出(--json-out, 任意位置)


def log(line):
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write('[' + datetime.datetime.now().isoformat() + '] ' + line + chr(10))
    except Exception:
        pass


# ★ HR 通则「排除即转交」的第②条：**排除须改分母并单独计数** ⇒ 各域扫描登记「已扫 / 共（未扫，另排除）」普查数。
# ★★ 实测缺陷（本次修复的由来，比「截断」更重）：
#   旧实现把分母写成 `len(ks)`，而 `ks` **已经是 `[:limit]` 之后的结果** ⇒ 分母**永远等于**分子
#   ⇒ 「未触上限」**恒真** ⇒ 这个读数**在结构上不可能报出「未扫 > 0」**。
#   即：它不是 HR 说的「会变坏的读数」，而是**恒真读数**（我此前命名的同一族）。
#   取证：本域真实键 40（服务端 total），而扫描自报「共 29」——**两个分母都对不上**，
#   差额正是被静默排除的 `_pc-*` 探针（排除项当时**没有单独计数**，违反通则第②条）。
SCAN_CENSUS = {}

# ★ HR③「上限阈值 40 本身是自由端点，须标依据，追到不能再追的那一格」：
SCAN_PAGE = 40        # **页大小**（★ 成本选择：每页一次 HTTP 请求）。★ 关键：**它与覆盖无关** ——
#                       ②的增量补扫使页大小不再决定漏判 ⇒ 所以它**不是**覆盖意义上的自由端点。
SCAN_MAX_PAGES = 25   # ★ **覆盖相关的自由端点**（真正的硬上限）。追到最后一格 = **「域规模上限假设」**：
#                       25 页 × 40 = 1000 键。换算成 HR 要的那个口径 = **「我容忍在多大概率下漏判」**：
#                       在「本域键数 ≤ 1000」这个假设成立时，漏判概率 **= 0**（不是「很小」）；
#                       **假设失效时（域涨过 1000）漏判概率未知** ⇒ 故这不是永久常数，
#                       **必须随域规模复核**（本域现 total=40 ⇒ 余量 25 倍；这正是「会变坏的读数」）。


def _scan_domain(domain=None, page=SCAN_PAGE, max_pages=SCAN_MAX_PAGES):
    """★ HR②「增量补扫」的执行体：**分页取全量**（`?limit=&offset=`，实测分页有效、页间无交集）。
    把「未扫 N」作为**下一轮输入**、每轮多扫一页，直到未扫 = 0 ⇒ 上限截断**有了接手方**。
    返回 (keys, total, err)：total 取**服务端信封的 `total`**（权威分母，不由本地切片推）。
    total 为 None ⇒ 未扫数**不可知** ⇒ 调用方须走「不合格」档。"""
    d = domain or SELF_DOMAIN
    keys, total, err = [], None, None
    for i in range(int(max_pages)):
        try:
            with urllib.request.urlopen('http://' + REPLICAS['local'] + '/' + d + '?limit=' + str(page)
                                        + '&offset=' + str(i * page), timeout=TIMEOUT) as r:
                j = json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            err = str(e)[:40]; break
        if total is None:
            try:
                total = int(j.get('total'))
            except Exception:
                total = None
        chunk = list((j.get('list') or {}).keys())
        keys.extend(chunk)
        if len(chunk) < int(page):
            break
    return keys, total, err


def _set_census(tag, scanned, total, excluded):
    """登记三档所需的三个数（**排除项单独计数** = 通则第②条）。"""
    SCAN_CENSUS[tag] = {'scanned': scanned, 'total': total, 'excluded': excluded}


def _census(tag):
    """★ HR①「上限截断三档处置」的报数体。返回 (文本, 档位)；档位 ∈ census / sampled / invalid。
      · 未扫 = 0                    ⇒ **普查**：结论可作「全部」（仍须报分母）
      · 未扫 > 0 且**已知**          ⇒ **降级为抽样**：**必须带未扫数**，且明写
                                      「结论**只对已扫部分成立**、未扫部分**未被判定**」
      · 未扫数**不可知**（拿不到服务端 total）⇒ **不合格**：结论不得引用
    ★ 并保留「这是会变坏的读数」：分母来自服务端，域一涨未扫就会非 0 ⇒ 三档长期有效，不是临时补丁。"""
    c = SCAN_CENSUS.get(tag)
    if not c:
        return '', 'invalid'
    sc, tot, exc = c.get('scanned'), c.get('total'), c.get('excluded')
    head = '已扫 ' + str(sc) + ' / 共 ' + str(tot) + ' · 另排除 ' + str(exc)
    if tot is None:
        return (head + ' · **未扫数不可知** ⇒ ★**不合格**（结论不得引用本行；须先修成可知）'), 'invalid'
    un = int(tot) - int(sc) - int(exc)
    if un <= 0:
        return (head + ' · **未扫 0** ⇒ **普查完成，结论可作「全部」**'), 'census'
    return (head + ' · **未扫 ' + str(un) + '** ⇒ ★**降级为抽样**：结论**只对已扫部分成立**，'
            '**未扫 ' + str(un) + ' 键未被判定**（接手方＝下一轮补扫，输入即此未扫数）'), 'sampled'


_TOUCHED = []


def _touch(kind, ref):
    """记录本进程**实际访问过**的目标（key/card/ns）—— 供 A21 审计「声明范围是否**过小**」（HR：过小=范围不足）。"""
    _TOUCHED.append(str(kind) + ':' + str(ref))


def get(server, key):
    """返回 (status, value)。status=None 表示不可达 —— 调用方须按 unknown 处理。"""
    _touch('key', key)
    try:
        with urllib.request.urlopen('http://' + REPLICAS[server] + '/' + key, timeout=TIMEOUT) as r:
            d = json.loads(r.read().decode('utf-8', 'replace'))
            return r.status, d.get('value')
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return None, None


def unwrap(o, depth=0):
    """先解包裹再比较：可解析为 JSON 的字符串按其语义参与比较（沿用 replica-consistency-check 的判据）。"""
    if depth < 4:
        if isinstance(o, str):
            s = o.strip()
            if s[:1] in '{[':
                try:
                    return unwrap(json.loads(s), depth + 1)
                except Exception:
                    return o
        if isinstance(o, dict):
            return dict((k, unwrap(v, depth + 1)) for k, v in o.items())
        if isinstance(o, list):
            return [unwrap(x, depth + 1) for x in o]
    return o


def canon(o):
    try:
        return json.dumps(unwrap(o), sort_keys=True, ensure_ascii=False)
    except Exception:
        return str(o)


# ---- v1.0.1 敏感字段硬拒（明鉴 a190c54c 提出：对凭据类信息，复制=扩散，不是修复）----
# ★ v1.0.2 修**误拦**（自捕获：用 refcheck 核自己的登记卡时，字段名「敏感硬拒.键名疑似凭据类」
#   因含「凭据」二字被硬拒命中 —— **字段名提及凭据 ≠ 字段值含凭据**。这正是负控要抓的「恒假」半边）
#   ⇒ 拆成两档：**硬拒**只认「标识符形凭据名」或「纯中文凭据词」，其余命中降级为**告警不阻断**。
SENSITIVE_FIELD_RE = re.compile(r'(secret|token|password|passwd|pwd|api[-_]?key|private[-_]?key|'
                                r'aeskey|credential|bearer|authorization|cookie|凭证|密码|密钥|令牌|凭据)', re.I)
# 硬拒档①：ASCII 标识符形的凭据名（含 api_token / feishu_secret 这类前后缀组合）
SECRET_IDENT_RE = re.compile(r'^[A-Za-z0-9_.\-]*(?:api[_-]?key|apikey|secret|token|password|passwd|pwd|'
                             r'aeskey|credential|private[_-]?key|bearer|authorization|cookie)'
                             r'[A-Za-z0-9_.\-]*$', re.I)
# 硬拒档②：中文名**以凭据词结尾** ⇒ 覆盖复词（主密钥 / 备份令牌 / 数据库凭据）
#   ★ v1.0.6 依明鉴 a190c54c 的边界补：原为「整名即」(^…$)，会漏复词；改为**后缀锚定**。
#   ★ 这是**取舍不是改进**（明鉴指出，判定权在我）：后缀锚定排除「令牌桶算法」「密码学笔记」（凭据词在**前缀/中缀**）
#     ⇒ 换来复词覆盖，代价是「主密钥备份」这类**词尾非凭据词**的漏检（漏检可接受：工具已声明不做内容识别）。
#   ★ 决定依据：先**实测**新规则的误拦面（本网 53 键真实数据扫描，命中 0）再改，改后加 A13a/A13b 双向锁住。
SECRET_CN_SUFFIX_RE = re.compile(r'(?:密码|密钥|令牌|凭据|凭证)$')
SENSITIVE_KEY_RE = re.compile(r'(secret|token|cred|password|passwd|apikey|private|凭据|密码|密钥|令牌)', re.I)


def _is_secret_name(name):
    n = str(name)
    return bool(SECRET_IDENT_RE.match(n) or SECRET_CN_SUFFIX_RE.search(n))


def sensitive_fields(o, prefix='', depth=0):
    """**硬拒档**：递归找出凭据形字段名（只按字段名判，不做内容识别 —— 该限界写进 docstring）。"""
    out = []
    if depth > 3:
        return out
    if isinstance(o, dict):
        for k, v in o.items():
            if _is_secret_name(k):
                out.append(prefix + str(k))
            out += sensitive_fields(v, prefix + str(k) + '.', depth + 1)
    elif isinstance(o, list):
        for i, x in enumerate(o[:20]):
            out += sensitive_fields(x, prefix + str(i) + '.', depth + 1)
    return out


def sensitive_mentions(o, prefix='', depth=0):
    """**告警档**：字段名提到凭据词但**不是**凭据形（如「凭据纪律」「键名疑似凭据类」）—— 只提示不阻断。"""
    out = []
    if depth > 3:
        return out
    if isinstance(o, dict):
        for k, v in o.items():
            if SENSITIVE_FIELD_RE.search(str(k)) and not _is_secret_name(k):
                out.append(prefix + str(k))
            out += sensitive_mentions(v, prefix + str(k) + '.', depth + 1)
    elif isinstance(o, list):
        for i, x in enumerate(o[:20]):
            out += sensitive_mentions(x, prefix + str(i) + '.', depth + 1)
    return out


def redact(o, depth=0):
    """差异输出用：敏感字段的值换成标记，**不打印值**。"""
    if depth > 4:
        return o
    if isinstance(o, dict):
        return dict((k, ('<已脱敏 len=' + str(len(canon(v))) + '>' if SENSITIVE_FIELD_RE.search(str(k))
                         else redact(v, depth + 1))) for k, v in o.items())
    if isinstance(o, list):
        return [redact(x, depth + 1) for x in o]
    return o


def diff_fields(src, dst):
    """逐字段差异。返回 (equal: bool, details: list[str])
    ★ 敏感字段的差异**只报字段名与长度**，绝不打印值（v1.0.1）。"""
    s = unwrap(src) if isinstance(src, dict) else src
    d = unwrap(dst) if isinstance(dst, dict) else dst
    if not (isinstance(s, dict) and isinstance(d, dict)):
        return (canon(s) == canon(d), ['<非对象: src=' + type(s).__name__ + ' dst=' + type(d).__name__ + '>'])
    det = []
    for k in sorted(set(s) | set(d)):
        if k not in s:
            det.append(k + ': dst 多出')
        elif k not in d:
            det.append(k + ': dst 缺失')
        elif canon(s[k]) != canon(d[k]):
            if SENSITIVE_FIELD_RE.search(str(k)):
                det.append(k + ': 值不同(已脱敏 src.len=' + str(len(canon(s[k]))) + ' dst.len=' + str(len(canon(d[k]))) + ')')
            else:
                det.append(k + ': ' + canon(s[k])[:40] + ' != ' + canon(d[k])[:40])
    return (not det, det)


def read_src(key, server, allow_secret=False):
    """返回 (value, err)。err 非 None 时调用方直接返回该退出码。"""
    st, v = get(server, key)
    if st == 404:
        print('[copy] X 源键不存在(404) ' + key + ' @' + server)
        return None, 3
    if st != 200 or v is None:
        print('[copy] ? 源键不可读(status=' + str(st) + ') ' + key + ' @' + server + ' —— unknown，不并入一致')
        return None, 3
    sf = sensitive_fields(v)
    if sf and not allow_secret:
        print('[copy] X 敏感字段硬拒(exit 7): 源键含 ' + ','.join(sf[:6]) + ' —— 对凭据类信息「复制」是**扩散动作**')
        print('      (Φ12 引用即复制：会在 ' + server + ' 与目标副本各留一份未受控副本)')
        print('      正确路径 = 属主「不读只写」：不读旧值 → 写新值 → 两实例回读 + 只核对字段名，不打印值')
        print('      若本键确实不含凭据（纯文档键），请改名去掉敏感词，或用 --allow-secret-fields 明示越权(留痕)')
        log('SENSITIVE-REFUSE ' + key + ' fields=' + ','.join(sf[:6]))
        return None, 7
    if sf:
        print('[copy] ! 你已用 --allow-secret-fields 越过敏感硬拒 | 字段=' + ','.join(sf[:6]) + ' | 差异输出将脱敏')
        log('SENSITIVE-OVERRIDE ' + key + ' fields=' + ','.join(sf[:6]))
    _mn = sensitive_mentions(v)
    if _mn:
        print('[copy] ! 字段名**提到**凭据词但非凭据形(' + ','.join(_mn[:4]) + ') ⇒ 仅告警不阻断（防误拦文档键）')
    if SENSITIVE_KEY_RE.search(str(key)):
        print('[copy] ! 键名疑似凭据类(' + key + ')：仅告警不阻断(防误拦纯文档键) —— 请自判该键是否允许留存')
    return v, None


def cmd_copy(args):
    _g = _preflight_gate(args)
    if _g is not None:
        return _g
    v_src, err = read_src(args.src, args.src_server, getattr(args, 'allow_secret_fields', False))
    if err is not None:
        return err
    src_keys = sorted(v_src.keys()) if isinstance(v_src, dict) else []
    dsts = ['local', 'central'] if args.to == 'both' else [args.to]
    if args.dry_run:
        print('[copy] DRY-RUN | src=' + args.src + '@' + args.src_server + ' | dst=' + args.dst
              + '@' + ','.join(dsts) + ' | 顶层键=' + str(src_keys) + ' | 零变更')
        return 0
    st = 0
    for srv in dsts:
        cmd = ['python3', BB_WRITE, 'put', args.dst,
               '--json', json.dumps(unwrap(v_src), ensure_ascii=False),   # ★ 原样值，非重建
               '--server', srv]
        if src_keys:                       # ② 形状断言：源键顶层集合即期望集合
            _comma = [k for k in src_keys if ',' in str(k)]
            if _comma:
                # ★ bb-write 的 --expect-keys 是**逗号分隔**（属主已裁定采纳「允许重复传 --expect-key」，尚未实施）
                #   ⇒ 本工具在此**明说并拒绝**，不让下游报出令人误解的 exit 5（否则使用者会去删 flag ⇒ 该卡失去形状断言）
                print('[copy] X 源键含逗号，形状断言无法表达: ' + ','.join(_comma))
                print('      bb-write 的 --expect-keys 以逗号分隔；属主已裁定将来支持重复 --expect-key（未实施）')
                print('      ⇒ 处置: 改键名（避免逗号），或等该裁定落地；**不要**因此去掉形状断言')
                log('comma-key refused: ' + args.src + ' keys=' + ','.join(_comma))
                return 2
            cmd += ['--expect-keys', ','.join(src_keys)]
        if args.from_agent:
            cmd += ['--from', args.from_agent]
        if args.force:
            cmd += ['--force']
        r = subprocess.run(cmd, capture_output=True, text=True)
        head = (r.stdout or '').strip().splitlines()
        print('[copy] ' + srv + ' 写入 exit=' + str(r.returncode) + ' | ' + (head[-1] if head else ''))
        if r.returncode != 0:
            st = r.returncode
            continue
        # ③ 写后逐字段验收（完成判据 = dst==src，不是 200）
        st2, v_dst = get(srv, args.dst)
        if st2 != 200 or v_dst is None:
            print('[copy] ? ' + srv + ' 回读不可读 status=' + str(st2) + ' —— unknown')
            st = st or 3
            continue
        ok, det = diff_fields(v_src, v_dst)
        if ok:
            print('[copy] OK ' + srv + ' 逐字段相等 | 字段数=' + str(len(v_dst)) + ' | 顶层键=' + str(sorted(v_dst.keys())))
        else:
            print('[copy] X ' + srv + ' 内容不等(分叉): ' + '; '.join(det[:6]))
            st = st or 4
    log(args.src + ' -> ' + args.dst + ' | src=' + args.src_server + ' | to=' + args.to + ' | exit=' + str(st))
    if JSON_OUT:
        print(json.dumps({'tool': 'bb-copy', 'cmd': 'copy', 'version': VERSION, 'src': args.src, 'dst': args.dst,
                          'src_server': args.src_server, 'to': args.to, 'dst_servers': dsts, 'src_keys': src_keys,
                          'exit': st, 'ok': st == 0}, ensure_ascii=False))
    return st


def cmd_verify(args):
    _g = _preflight_gate(args)
    if _g is not None:
        return _g
    v_src, err = read_src(args.src, args.src_server, getattr(args, 'allow_secret_fields', False))
    if err is not None:
        return err
    dsts = ['local', 'central'] if args.to == 'both' else [args.to]
    st = 0
    for srv in dsts:
        st2, v_dst = get(srv, args.dst)
        if st2 != 200 or v_dst is None:
            print('[verify] ? ' + srv + ' 不可读 status=' + str(st2) + ' —— unknown')
            st = st or 3
            continue
        ok, det = diff_fields(v_src, v_dst)
        print(('[verify] OK ' if ok else '[verify] X ') + srv + ' ' + args.src + ' == ' + args.dst
              + ('' if ok else ' | 差异: ' + '; '.join(det[:6])))
        if not ok:
            st = st or 4
    if JSON_OUT:
        print(json.dumps({'tool': 'bb-copy', 'cmd': 'verify', 'version': VERSION, 'src': args.src, 'dst': args.dst,
                          'src_server': args.src_server, 'to': args.to, 'exit': st, 'ok': st == 0}, ensure_ascii=False))
    return st


# ---------------------------------------------------------------- 预检 / 对照
def _anchors_ok():
    """解析登记卡声明的语义锚点。返回 (True|False|'skipped', 说明)。"""
    try:
        st, cv, note = _card_fetch()
        if st != 200:
            return 'skipped', note + '(不冒充通过)'
        anchors = (cv or {}).get('语义锚点_不随版本漂')
        if not isinstance(anchors, list) or not anchors:
            return 'skipped', '卡内未声明锚点列表(不冒充通过)'
        s = open(os.path.abspath(__file__), encoding='utf-8').read()
        bad = [str(x) for x in anchors if str(x) not in s]
        return (not bad), (('全部可解析 n=' + str(len(anchors))) if not bad else ('解析失败: ' + ','.join(bad[:4])))
    except Exception as e:
        return 'skipped', '读卡异常(' + str(e)[:40] + ')(不冒充通过)'


SELF_DOMAIN = 'data/external-link/'


def _domain_fp_scan(limit=40):
    """★ 明鉴通则的可执行形式：**凡收紧/放宽一条匹配规则，须在当前真实数据上实测误拦面(或漏检面)并把数报出来**。
    本函数在本域**真实键**上跑**当前**敏感规则，回报 **(实扫键数, 排除探针数, 自有卡命中, 他人卡命中)**。
    排除规则：前缀 `_pc-` 的**控制用探针键**（用途就是承载违规样本）—— 排除是**声明式**的，且回报排除数。
    ★ HR①（越权判定＝未经授权的裁决）：**度量对象是我自己的误拦面** ⇒ 他人卡的命中**只报不判**。"""
    _touch('ns', SELF_DOMAIN)
    _all, _tot, _err = _scan_domain()
    ks = [k for k in _all if k.startswith(SELF_DOMAIN)]
    if _err and _tot is None:
        return None, None, [], []
    real = [k for k in ks if not os.path.basename(k).startswith('_pc-')]
    probes = len(ks) - len(real)
    _set_census('A17', len(real), _tot, probes)
    hits, foreign_hits = [], []
    for k in real:
        st, v = get('local', k)
        if st != 200 or not isinstance(v, dict):
            continue
        _pr = str(v.get('producer') or v.get('from') or '').strip()
        _mine = (not _pr) or (_pr == CANONICAL_ID)
        for f in sensitive_fields(v):
            (hits if _mine else foreign_hits).append(k + ' :: ' + f)
    return len(real), probes, hits, foreign_hits


def _boundary_check(v):
    """★ HR 2026-09-11 定为**全网样板**的写法 → 契约（样板若无执行体，本身就落在 ⓪ 档）。
    要求**同时**给出：①保证什么 ②**不可保证什么**（反方向不可证） ③级别档(⓪①②③④)；
    档③(硬拒)还须声明**越权路径**与**越权是否留痕**。返回 (ok, 说明)。"""
    b = (v or {}).get('能力边界_样板格式')
    if not isinstance(b, dict):
        return False, '缺「能力边界_样板格式」'
    for k in ('保证', '不可保证', '级别档'):
        if not str(b.get(k) or '').strip():
            return False, '缺必填项: ' + k
    lv = str(b.get('级别档'))
    if '③' in lv:
        if not str(b.get('越权路径') or '').strip():
            return False, '档③未声明越权路径'
        if '越权是否留痕' not in b:
            return False, '档③未声明越权是否留痕'
    return True, '齐备(档=' + lv[:8] + ')'


def _fingerprint_cmp(fp, sz, md, mt):
    """纯函数：比对「卡内指纹」与「本地实测指纹」。返回 (ok, 不一致维列表)。"""
    bad = []
    if not isinstance(fp, dict) or not fp:
        return False, ['未声明']
    if str(fp.get('version') or '') != VERSION:
        bad.append('version')
    if str(fp.get('size') or '') != str(sz):
        bad.append('size')
    if str(fp.get('md5') or '') != md:
        bad.append('md5')
    try:
        if abs(float(fp.get('mtime')) - float(mt)) > 1.0:
            bad.append('mtime')
    except Exception:
        bad.append('mtime')
    return (not bad), bad


def _independent_fingerprint():
    """★ HR「**同源断言**」的应用：若断言两方**同源**（同一常量/同一定量/同一函数），该断言**恒真**。
    故此处用**独立实现**（外部 md5/stat 命令，不走本文件的 urllib/os.stat 路径）测同一文件，
    使「卡内指纹」与「实测指纹」**分离**；两者若一致，才构成非恒真的证据。
    返回 (size:int, md5:str, mtime:int) 或 None。"""
    fp = os.path.abspath(__file__)
    try:
        out_md5 = subprocess.run(['md5', '-q', fp], capture_output=True, text=True, timeout=10)
        md5 = out_md5.stdout.strip()
        if len(md5) != 32:
            md5 = subprocess.run(['md5sum', fp], capture_output=True, text=True, timeout=10).stdout.split()[0]
        st = subprocess.run(['stat', '-f%z', fp], capture_output=True, text=True, timeout=10)
        size = st.stdout.strip()
        if not size.isdigit():
            size = subprocess.run(['stat', '-c%s', fp], capture_output=True, text=True, timeout=10).stdout.strip()
        mt = subprocess.run(['stat', '-f%m', fp], capture_output=True, text=True, timeout=10).stdout.strip()
        if not mt.isdigit():
            mt = subprocess.run(['stat', '-c%Y', fp], capture_output=True, text=True, timeout=10).stdout.strip()
        return (int(size), md5, int(mt)) if (size.isdigit() and len(md5) == 32 and mt.isdigit()) else None
    except Exception:
        return None


def _local_fingerprint():
    p = os.path.abspath(__file__)
    with open(p, 'rb') as f:
        b = f.read()
    return os.path.getsize(p), hashlib.md5(b).hexdigest(), os.path.getmtime(p)


CARD_KEY = 'data/registry/bb-copy-tool-v1'
# ★ 制品身份 = **规范安装路径**（源码内常量）。为何不用卡内 artifact_path：
#   A28 首跑实测——副本 stamp **真的把自己的路径写进了卡**（历史 9→10）⇒ 以卡内字段为判据会被**污染**。
CANONICAL_PATH = '~/dsh-collab/scripts/bb-copy.py'


def _card_fetch(key=None):
    """统一读卡入口。返回 (status, value, note)。key 缺省=本工具登记卡。
    ★ 自查（明鉴第 28 例「回读未核状态码、把 body 当内容」的同族）：此前本工具用裸 urlopen，
      任何失败都标成「卡不可达」—— **把 404(卡不存在=登记缺失) 折进了「不可达(网络)」这个标签**，
      运维会被引去查网络。现按状态分档：200 读值 · 404 判「登记缺失」· 其它报 HTTP 码 · 异常才是不可达。
    非 200 **一律不解析 body**（明鉴的修法：200 才解析 body，非 200 显示为状态而非内容）。"""
    key = key or CARD_KEY
    _touch('card', key)
    try:
        with urllib.request.urlopen('http://' + REPLICAS['local'] + '/' + key, timeout=TIMEOUT) as r:
            if r.status != 200:
                return r.status, None, 'HTTP ' + str(r.status) + '(非200，不解析 body)'
            return 200, json.loads(r.read().decode('utf-8', 'replace')).get('value') or {}, 'ok'
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return 404, None, '卡不存在(404) —— **登记缺失，不是网络问题**'
        return e.code, None, 'HTTP ' + str(e.code) + '(非200，不解析 body)'
    except Exception as e:
        return None, None, '不可达(网络/连接): ' + str(e)[:40]


def _fingerprint_history():
    try:
        v = _card_value()
    except Exception:
        return []
    h = v.get('指纹历史')
    return h if isinstance(h, list) else []


def _assert_range_label():
    """★ 明鉴④：**编号范围必须动态生成**，不得硬编码。
    起因：`--stamp` 的自测串原写死 `' 项(A1–A28)'`，而断言编号已到 A37 ⇒ **卡内实测「35 项(A1–A28)」对不上**
    —— 这是「**覆盖范围小于职责**」形态的第 4 例（复用 A26 的手法：让范围由数据结构生成）。"""
    # ★ 首版用**字符串**比数字 ⇒ 最大项被算成 `A9b`（实测生成「A1–A9b」）⇒ 改为按**整数**取最值
    nums = [int(re.match(r'A(\d+)', t).group(1)) for t in ASSERT_SCOPE if re.match(r'A(\d+)', t)]
    return ('A' + str(min(nums)) + '–A' + str(max(nums))) if nums else 'A?'


def _natural_order_max(items):
    """★ 明鉴①的判据落地：**问「我排序用的这个序，和我要的那个序，是同一个序吗？」**
    实例：我按**字符串**排序取最值 ⇒ 最大项被算成 `A9b`（错），而我要的是**数值序**。
    本函数演示正确取法（按整数取最值）；`_str_order_max` 是**反例实现**，供合成样本使用。
    返回 (最大项, 对应整数)。"""
    nums = [(int(re.match(r'A(\d+)', t).group(1)), t) for t in items if re.match(r'A(\d+)', t)]
    return max(nums)[1], max(nums)[0] if nums else ('A?', 0)


def _str_order_max(items):
    """**反例实现**：按字符串序取最值 ⇒ 在 `A1/A9b/A10` 这类集合上必错（这是明鉴①的实例）。"""
    tags = sorted(str(t) for t in items)
    return tags[-1] if tags else 'A?'


def _range_literal_ok(text, label):
    """给定文本里**出现的编号范围字面量**是否都与实得范围一致（无字面量=不适用 ⇒ 通过）。
    ★ 只用于**真实生成路径**（如卡内自测串）；**不扫全源码** —— 合成样本里故意写错的范围（如 A1–A99）
      是**判据的一部分**，扫全源码会把它当成缺陷（A38 首版即如此误报）。"""
    lits = set(re.findall(r'A1[–-]A\w+', str(text or '')))
    return (not lits) or all(x.replace('-', '–') == label for x in lits)


def _put_card(card):
    r = subprocess.run(['python3', BB_WRITE, 'put', CARD_KEY, '--json', json.dumps(card, ensure_ascii=False),
                        '--from', 'external-link-agent', '--server', 'both'], capture_output=True, text=True)
    return r.returncode == 0, (r.stdout or '').strip().splitlines()[-1] if (r.stdout or '').strip() else ''


def cmd_stamp(args):
    """把当前指纹登记为一次快照（当前值 + 有界「指纹历史」）。
    ★ 两阶段（v1.0.33）：先写「计数+版本正确」的自测占位 ⇒ **再真跑 --check** ⇒ 最后把**判定**写回。
      为何两阶段：单阶段会在**跑 check 时**让卡停在旧值上 ⇒ A25（计数/版本守卫）判红 ⇒ 记录下来的判定**落后一拍**
      （v1.0.32 实测确实记成了 FAIL）。两阶段后，最终卡状态与判定**自洽**。
    ★ 本文件必须是「规范制品」（源码常量 CANONICAL_PATH）—— 首版用卡内字段判断，被副本污染过（见 A28 自陈）。
    """
    _real = os.path.realpath(os.path.abspath(__file__))
    if _real != os.path.realpath(os.path.expanduser(CANONICAL_PATH)):
        print('[stamp] X 拒绝登记：本文件不是**规范制品**')
        print('      本文件 realpath   = ' + _real)
        print('      规范路径(源码常量) = ' + os.path.realpath(os.path.expanduser(CANONICAL_PATH)))
        print('      ⇒ 疑似在**副本**上 stamp（会让历史记下副本指纹；首版用卡内字段判断，被污染过）')
        return 8
    sz, md, mt = _local_fingerprint()
    ind = _independent_fingerprint()
    if ind is not None and (ind[1] != md or ind[0] != sz):
        print('[stamp] X 独立实现与本实现不一致 ⇒ 拒绝登记: ' + str(ind) + ' vs ' + str((sz, md, int(mt))))
        return 4
    try:
        with urllib.request.urlopen('http://' + REPLICAS['local'] + '/' + CARD_KEY, timeout=TIMEOUT) as r:
            card = json.loads(r.read().decode('utf-8', 'replace')).get('value') or {}
    except Exception as e:
        print('[stamp] X 读卡失败: ' + str(e)[:60]); return 3
    ts = datetime.datetime.fromtimestamp(mt).astimezone().isoformat(timespec='seconds')
    snap = {'version': VERSION, 'size': str(sz), 'md5': md, 'mtime': str(int(mt)), 'time': ts}
    hist = [h for h in _fingerprint_history() if str(h.get('md5')) != md]
    hist.append(snap)
    hist = hist[-12:]
    card['artifact_path'] = _real
    card['writer'] = 'bb-copy v' + VERSION          # ★ 工具管理：随每次 stamp 刷新，不存在「过期值」状态
    card['ts'] = _now_iso()
    card['ts_epoch'] = str(int(datetime.datetime.now().timestamp()))
    card['version'] = VERSION
    card['指纹'] = dict(snap, 时点=ts,
                        语法='★ 时点限定断言（「截至 <时点> 为 <指纹>」），**不是现在时** ⇒ 只会变成「过期的真」，不会变假',
                        级别='**记录级：示例值（非现值）**；现值请跑 `--report`（单行 ASCII 锚定，无需 grep）')
    card['指纹历史'] = hist
    _N = len(ASSERT_SCOPE)
    _rng = _assert_range_label()
    # ★ 明鉴⑤1：「40 项(A1–A38)」把**项数**与**最大编号**并列 ⇒ 读者可能读成「38 项」或「40 号」⇒ 分列
    # ★ HR② 补：「两阶段写入的第一阶段须【**看上去就是未完成**】」⇒ 阶段1 用显式未完成标记
    # ★ HR①：完成标记 = 状态维 ＋ **时间维** ⇒ 阶段1 的**写入时刻**落成卡内独立字段，
    #   且**阶段2 不覆盖它**（这样终态也能回溯「阶段1 停留了多久」）。
    #   为什么不靠信封 ts：**信封 ts 每次 PUT 都刷新** ⇒ 它承担不了「阶段入口」这个角色。
    card['阶段1时点'] = _now_iso()
    card['自测'] = ('【未完成·阶段1/2 —— 本字段尚不可引用 · 进入阶段1 @ ' + card['阶段1时点'] + '】(v' + VERSION
                    + ') 项数 ' + str(_N) + ' · 编号范围 ' + _rng)
    ok1, _l1 = _put_card(card)
    if not ok1:
        print('[stamp] X 阶段1 写入失败: ' + _l1); return 1
    _chk = subprocess.run(['python3', os.path.abspath(__file__), '--check'], capture_output=True, text=True)
    _v = 'PASS' if _chk.returncode == 0 else 'FAIL'
    # ★ 终态时点独立成字段（不靠从文本里抠）：停留时长 = 阶段2时点 − 阶段1时点，**冻结**。
    card['阶段2时点'] = _now_iso()
    card['自测'] = ('--check 项数 ' + str(_N) + ' · 编号范围 ' + _rng + ' · 全 ' + _v
                    + '(v' + VERSION + ' 实跑 · 工具写 @ ' + _now_iso()
                    + ' · 阶段1 入口 ' + str(card.get('阶段1时点'))
                    + ') · **示例值（非现值；现值请跑 `--report`）**')
    ok2, _l2 = _put_card(card)
    print('[stamp] ' + ('OK ' if (ok1 and ok2) else 'X ') + 'v' + VERSION + ' size=' + str(sz) + ' md5=' + md[:8]
          + ' time=' + ts + ' | 历史深度=' + str(len(hist)) + ' | check=' + _v
          + (' | 双侧已写(两阶段)' if (ok1 and ok2) else ' | 阶段2失败: ' + _l2))
    return 0 if (ok1 and ok2) else 1


def _now_iso():
    """★ 明鉴指出的手写时点问题：`HH:Mx` / `:00` 整秒 / 未来 14 小时 都是**手写特征**。
    ⇒ 时点**由写入路径注入**，并带时区偏移（跨时区读者才可定绝对时刻）。"""
    return datetime.datetime.now().astimezone().isoformat(timespec='seconds')


def _ts_check(ts_str, ts_epoch=None, now=None, skew_sec=300):
    """纯函数（供 A27 双向断言）：校验时点字段。
    判据：可解析 · **带时区偏移** · 若给了 epoch 须与之一致 · **不得显著指向未来**（手写错值的典型形态）。
    返回 (ok, 说明)。"""
    t = str(ts_str or '').strip()
    if not t:
        return False, '缺时点'
    try:
        dt = datetime.datetime.fromisoformat(t.replace('Z', '+00:00'))
    except Exception:
        return False, '时点不可解析: ' + t[:30]
    if dt.tzinfo is None:
        return False, '**时点无时区偏移**（跨时区读者无法定绝对时刻）: ' + t[:30]
    now = now or datetime.datetime.now(dt.tzinfo)
    if (dt - now).total_seconds() > skew_sec:
        return False, '时点**指向未来** ' + str(int((dt - now).total_seconds())) + ' 秒（手写错值的典型形态）'
    if ts_epoch:
        try:
            if abs(int(float(ts_epoch)) - int(dt.timestamp())) > 2:
                return False, '时点与 ts_epoch 不一致（' + str(int(dt.timestamp())) + ' vs ' + str(ts_epoch) + '）'
        except Exception:
            return False, 'ts_epoch 不可解析'
    return True, 'OK(' + dt.isoformat(timespec='seconds') + ')'


def _card_value():
    st, v, note = _card_fetch()
    if st != 200:
        raise RuntimeError(note)
    return v


def _fingerprint_ok():
    """★ 明鉴指出：**规则对活跃对象不充分** —— 静态对象上「版本」足够，活跃对象上**版本在声明写出后立即过期**
    ⇒ 引用须带**版本 + 时点**。故本工具把指纹做成可执行契约：卡内记 version/size/md5/**mtime(时点)**，
    与本文件实测值比对 ⇒ **任何编辑未同步卡 ⇒ A16 FAIL**（时点用文件自身 mtime，是客观基准，非自报）。
    返回 (True|False|'skipped', 说明)。"""
    try:
        sz, md, mt = _local_fingerprint()
    except Exception as e:
        return 'skipped', '读本地指纹失败(' + str(e)[:30] + ')'
    try:
        v = _card_value()
    except Exception as e:
        return 'skipped', str(e)[:60] + '(不冒充通过)'
    fp = v.get('指纹')
    if not isinstance(fp, dict) or not fp:
        return 'skipped', '卡未声明「指纹」字段(不冒充通过)'
    ok, bad = _fingerprint_cmp(fp, sz, md, mt)
    return ok, ('一致 v=' + str(fp.get('version')) + ' size=' + str(sz) + ' md5=' + md[:8]
                + ' mtime=' + str(int(mt))) if ok else ('过期维: ' + ','.join(bad) + ' —— **编辑后未同步卡**')


# ★ 声称判定枚举的**单一来源**（明鉴②：卡内散文仍写「三态」而源码是四态 ⇒ 枚举必须只有一个来源）
CLAIM_VERDICTS = {0: 'PASS 当前仍匹配', 3: '过期的真（当时为真、现在过期）', 4: 'FAIL 假声称或自相矛盾', 5: '不可核（历史无该快照）'}
# ★ 明鉴③建议的推广：**卡内任何枚举（名字(N)）须与源码枚举集合一致** ⇒ 此处登记全部枚举的成员集合，
#   由 A37 断言「每个成员名都出现在卡内文本中」（成员缺失即点名）。
ENUM_SPECS = {
    '声称判定': list(CLAIM_VERDICTS.values()),
    '传递形态': ['整值原样复制', '字段名级引用', '部分值复制'],
    '对照链': ['分离操作数', '样本真违规', '样本真合规', '独立实现复跑', '入口可发现'],
    '数报格式': ['判据', '范围', '时点', '对象', '正反控', '受自身干预'],
    '时点政策分类': ['无时区偏移', '指向未来', '整分'],
}
CLAIM_RE = {
    'version': re.compile(r'v(\d+\.\d+\.\d+)'),
    'size': re.compile(r'size[=: ]+(\d+)', re.I),
    'md5': re.compile(r'md5[=: ]+([0-9a-fA-F]{32})', re.I),
    'mtime': re.compile(r'mtime[=: ]+(\d{9,11})', re.I),
    'time': re.compile(r'time[=: ]+(\d{4}-\d{2}-\d{2}T[\d:]+)', re.I),
}


def make_claim(with_check=False):
    sz, md, mt = _local_fingerprint()
    # ★ 依明鉴「宣言时态」：不再写「现在是 X」（一旦过 T 即成假陈述），改**时点限定**语法（永久为真，只会变成「过期的真」）
    _iso = datetime.datetime.fromtimestamp(mt).astimezone().isoformat(timespec='seconds')
    line = ('bb-copy CLAIM **截至 ' + _iso + ' 为** v' + VERSION + ' | size=' + str(sz) + ' | md5=' + md
            + ' | mtime=' + str(int(mt)) + ' | time=' + _iso)
    if with_check:
        r = subprocess.run(['python3', os.path.abspath(__file__), '--check'], capture_output=True, text=True)
        line += ' | check=' + ('PASS' if r.returncode == 0 else 'FAIL')
    else:
        line += ' | check=未跑'
    return line


ATTRIB_SELF = 'self-run-non-third-party'


def _attribution_line():
    return ('[check] 实测归属：**' + ATTRIB_SELF + '**（本会话自跑）｜ 第三方实测须另行标注（谁·何时·何结果）')


def _attribution_ok(text):
    """★ HR③「第三方实测不能自封」的执行体：归属标注必须**可判**——
    · 自跑 ⇒ 须含 `self-run-non-third-party`
    · 第三方 ⇒ **须含主体（谁）与时点**（只写「第三方」而无人名/时点 ⇒ 判缺失）
    返回 (ok, 说明)。"""
    t = str(text or '')
    if ATTRIB_SELF in t:
        return True, '自跑标注 ✓'
    if '第三方' in t:
        who = bool(re.search(r'第三方[:：]?\s*\S+', t))
        when = bool(re.search(r'\d{4}-\d{2}-\d{2}', t))
        if who and when:
            return True, '第三方标注完整（含主体与时点）✓'
        return False, '第三方标注**缺主体或时点**（不能自封）✗'
    return False, '缺归属标注 ✗'


def _falsifiability_kind(text):
    """★ 明鉴②：「**声明了可失败性证据**」与「**它真的能失败**」是两件事。
    判据：**问「这条断言的『可失败性证据』是一条【合成样本】还是一句【说明】？」**
    ⇒ 本函数按**声明关键词**分类：含「合成」⇒ 样本；含「反向/反例」⇒ 反向校验；否则 ⇒ **仅说明**（不算证据）。"""
    t = str(text or '')
    if '合成' in t:
        return '样本'
    if ('反向' in t) or ('反例' in t):
        return '反向校验'
    return '说明'


MIN_REPORT_KV = 12          # ★ 下限常量（**单一来源**，范围文本不写死数字）


def _report_ok(line):
    """★ 明鉴⑤：「**看输出**这一步也要能核」——把非空断言写进输出，否则「看了」仍是自述。
    判据：输出行须含 **MIN_REPORT_KV** 个 `k=v` 且**每个 v 非空**（否则视为「输出恒空化」）。"""
    t = str(line or '')
    kv = [x for x in t.split(' ') if '=' in x]
    vals_ok = all(x.split('=', 1)[1].strip() for x in kv)
    return (len(kv) >= MIN_REPORT_KV and vals_ok), ('键值对 ' + str(len(kv)) + '（下限 ' + str(MIN_REPORT_KV) + '）· 值全非空=' + str(vals_ok))


def make_report():
    """★ HR① 的「每跳须可复制」+ 他②的实测反馈（`grep 数报` 在他环境**未取到该行**）⇒
    提供**ASCII 锚定、单行、无 grep 依赖**的报告入口：`--report`。
    键为 ASCII ⇒ 任意 locale 下 `grep -F '[bb-copy-report]'` 均可定位。"""
    _sz, _md, _mt = _local_fingerprint()
    _pol = {}
    for _t in ASSERT_SCOPE:
        _l = CONTROL_POLARITY.get(_t, 'UNSET')
        _pol[_l] = _pol.get(_l, 0) + 1
    # ★ 明鉴②合并后的规则：**凡制品须声明【核到哪一级 · 是不是终态】**（缺则读者填成「最强/终态」）
    #   ⇒ 本行声明 level=content（值可比对级）· state=live-reading（**现场读数，非制品快照**）
    # ★ HR④「现场指纹 + 读取时刻」⇒ 一并报出**卡的信封 ver/ts**（读取时刻的现场值）
    # ★ HR④「现场指纹 + 读取时刻」⇒ 报出**卡的信封 ver/ts**（读取时刻的现场值，来源与我的计算不同）
    _cver = _cts = 'n/a'
    try:
        with urllib.request.urlopen('http://' + REPLICAS['local'] + '/' + CARD_KEY, timeout=TIMEOUT) as r:
            _env = json.loads(r.read().decode('utf-8', 'replace'))
        _cver = str(_env.get('version', 'n/a'))
        _cts = str(_env.get('ts', 'n/a'))
    except Exception:
        pass
    # ★ 明鉴②合并后的规则：**凡制品须声明【核到哪一级 · 是不是终态】**（缺则读者填成「最强 / 终态」）
    return ('[bb-copy-report] tool=~/dsh-collab/scripts/bb-copy.py version=' + VERSION + ' md5=' + _md[:8]
            + ' params=--report time=' + datetime.datetime.now().astimezone().isoformat(timespec='seconds')
            + ' judge=self-named-per-assertion range=per-assertion-output'
            + ' object=' + CARD_KEY + '+file+probes' + str(len(PROBE_KEYS))
            + ' polarity=' + '/'.join(k + str(v) for k, v in sorted(_pol.items()))
            + ' self_interference=self-run-non-third-party'
            + ' level=content state=live-reading'
            + ' card=' + CARD_KEY + ' card_ver=' + _cver + ' card_ts=' + _cts
            + ' read_at=' + datetime.datetime.now().astimezone().isoformat(timespec='seconds')
            + ' note=reference-this-line-with-its-time')


def verdict_label(v):
    return CLAIM_VERDICTS.get(v, '未登记')


def verify_claim(text):
    """核**对外声称**（判定四态见 `CLAIM_VERDICTS` 单一来源）。★ v1.0.19 依明鉴「两问」改造：**旧版只有「当前核」⇒ 把「过期」与「假」混为一谈**
    （任何带时点的旧 claim 都被判不一致 ⇒ 归入「拒」）。现分开报两问，而不是合成一个 OK/不一致：
      · **问① 在 claim 的时点上，制品是否匹配？**（需历史快照；无则报「不可核」，**不是「不一致」**）
      · **问② 当前制品是否仍匹配？**（新鲜度）
    判定**四态**（成员以 `CLAIM_VERDICTS` 为单一来源，卡内不得另写一套）：0/3/4/5。
    返回 (退出码, [时态行, 问①行, 问②行, 判定行])。"""
    sz, md, mt = _local_fingerprint()
    got = dict((k, (rx.search(text).group(1) if rx.search(text) else None)) for k, rx in CLAIM_RE.items())
    if not got['md5'] and not got['version']:
        return 4, ['文本里没有任何指纹声明(md5/版本)']
    limited = bool(re.search(r'(截至|CLAIM-AT|as of|as-of)', text, re.I))
    if got['mtime'] is None:
        return 4, ['缺时点(mtime) ⇒ 无法判断「曾经/现在」']
    cmt = int(got['mtime'])
    same_rev = abs(cmt - int(mt)) <= 1
    fp_match = ((got['md5'] or '').lower() == md) and (str(got['size'] or '') == str(sz)) \
        and (got['version'] or VERSION) == VERSION
    # 问①：在 claim 时点上是否匹配（查历史快照；当前修订也算一个快照）
    hist = _fingerprint_history() + [{'version': VERSION, 'size': str(sz), 'md5': md, 'mtime': str(int(mt))}]
    hit = None
    for e in hist:
        if str(e.get('md5', '')).lower() == (got['md5'] or '').lower() and str(e.get('size', '')) == str(got['size'] or ''):
            hit = e
            break
    if (not limited) and got['time']:
        _tense = '★ 时态未声明（带 time= 但无「截至」标记）⇒ **按现在时从严判定**；建议改用 `截至 <时点> 为`'
    elif limited:
        _tense = '时态: 时点限定'
    else:
        _tense = '时态: 现在时'
    if same_rev:
        q1 = '① claim 时点 == 当前修订 ⇒ 可核（' + ('匹配' if fp_match else '**与实测不符 ⇒ 自相矛盾**') + '）'
    elif hit:
        q1 = '① claim 时点为 ' + str(cmt) + ' ⇒ **当时为真**（与指纹历史快照 md5 ' + str(hit.get('md5'))[:8] + ' 一致）'
    else:
        q1 = '① claim 时点为 ' + str(cmt) + ' ⇒ **不可核**（历史无该时点快照；本工具仅保留最近 12 次、且不追补）'
    # 问②：当前是否仍匹配（新鲜度）
    if fp_match:
        q2 = '② 当前制品 **仍匹配**（新鲜）'
    else:
        q2 = '② 当前制品 **不匹配**（滞后 ' + str(int(mt) - cmt) + ' 秒；实测 md5 ' + md[:8] + '）'
    # 判定
    if fp_match:
        verdict, tail = 0, '判定: ' + str(verdict_label(0)) + '(0)'
    elif same_rev:
        verdict, tail = 4, '判定: ' + str(verdict_label(4)) + '(4) —— **自相矛盾**（声称时点就是当前修订，指纹却对不上）'
    elif not limited:
        verdict, tail = 4, '判定: ' + str(verdict_label(4)) + '(4) —— **假声称**（现在时声明，在当前为假）'
    elif hit:
        verdict, tail = 3, '判定: ' + str(verdict_label(3)) + '(3) —— **不是假声称**'
    else:
        verdict, tail = 5, '判定: ' + str(verdict_label(5)) + '(5) —— 时点限定、当前不匹配、历史无该快照'
    return verdict, [_tense, q1, q2, tail]


# ★ HR 四步链第四步「**入口可发现**」（否则第三条在外部等同于不存在）。
#   声明的豁免：源码里出现但**刻意不提供**或**属下游工具**的 token —— 豁免必须带理由并回报条数。
DISCOVERY_EXEMPT = {
    '--body': '刻意不提供（重建路径须不可表达）；仅出现在**测试**里（断言 copy 拒绝它）与调用 bb-write 的负控',
    '--json': '刻意不提供；作为 **bb-write 载荷旗标**被转传（本工具自身无自由文本入口）',
    '--subject': '刻意不提供（同 --body，重建路径须不可表达）',
    '--expect-keys': '属 **bb-write**（形状断言由本工具自动生成并转传）',
    '--server': '属 **bb-write**（双侧派发由本工具 --to 映射后转传）',
}


def _help_discovered_tokens():
    """收集 root + 各子命令 help 中**作为选项出现**的 token（排除散文里的提及 —— 判据: 只看行首选项与 usage 行）。"""
    disc = set()
    cmds = [[], ['copy'], ['verify'], ['refcheck']]
    for c in cmds:
        out = subprocess.run(['python3', os.path.abspath(__file__)] + c + ['--help'],
                             capture_output=True, text=True).stdout
        for line in out.splitlines():
            st = line.strip()
            if st.startswith('usage:'):
                disc |= set(re.findall(r'--[a-z][a-z0-9-]*', st))
            elif st.startswith('-'):
                disc |= set(re.findall(r'--[a-z][a-z0-9-]*', st.split('  ')[0]))
    return disc


def _flag_tokens_in_code(src_text):
    """只取**作为旗标使用**的 token：字符串字面量**去掉全部旗标后不剩内容**才算（如 `'--force'`）。
    ★ 这条区分是 A23 首版暴露的镜像坑：散文/docstring 里的**提及**（如我引用罗盘的 ``--samples``）
    若与「提供」混为一谈 ⇒ **把别人的旗标算成我的缺口**。判据：**提及 ≠ 提供**。"""
    import io as _io, tokenize as _tk
    toks = set()
    _lines = src_text.splitlines()
    try:
        for t in _tk.generate_tokens(_io.StringIO(src_text).readline):
            if t.type == _tk.STRING:
                # ★ 自指排除（A23 首版第二处误报）：比较/成员上下文里的字面量**不是旗标使用**
                #   （如 `_miss2 == ['--not-a-real-flag']`）⇒ 按**所在行的前缀**判别，不计入。
                _pre = (_lines[t.start[0] - 1][:t.start[1]] if t.start[0] - 1 < len(_lines) else '')
                _pre = _pre.rstrip()
                if _pre.endswith('==') or _pre.endswith('!=') or _pre.endswith(' in') or \
                   (_pre.endswith('[') and ('==' in _pre or '!=' in _pre)):
                    continue
                body = t.string
                m = re.match(r'^[a-zA-Z]{0,2}([\'\"]{3}|[\'\"])(.*)\1$', body, re.S)
                inner = m.group(2) if m else body
                found = re.findall(r'--[a-z][a-z0-9-]*', inner)
                if found and not re.sub(r'--[a-z][a-z0-9-]*', '', inner).strip(' \t\r\n\',\"[](){}:;,./|+='):
                    toks |= set(found)
    except Exception:
        toks = set(re.findall(r'--[a-z][a-z0-9-]*', src_text))
    return toks


def _argparse_defined_tokens(src_text=None):
    """★ HR 推广的「出现 ≠ 行使」：三种行使须分开 —— **定义 / 提供 / 使用**。
    本函数取【**定义**】：`add_argument(` 后**紧接的旗标字面量**（含别名）。
    ★ 首版按「行内含 add_argument(」+ 括号配平取整段 ⇒ **过度吸收后续行**，把 `--body`/`--json`/`--server`
      甚至合成假旗标都算成了我的定义（连带使 U 少算）。⇒ 改判据：**只取 add_argument( 之后的连续旗标字面量**，
      对后续内容免疫（形态手段解语义问题，边界要卡在「紧接」上）。"""
    src = src_text if src_text is not None else open(os.path.abspath(__file__), encoding='utf-8').read()
    toks = set()
    for grp in re.findall(r"add_argument\(\s*((?:['\"]--[a-z][a-z0-9-]*['\"]\s*,?\s*)+)", src):
        toks |= set(x.strip(chr(39) + chr(34)) for x in re.findall(r"--[a-z][a-z0-9-]*", grp))
    return toks


def _used_tokens(src_text=None):
    """取【**使用**】：作为旗标**被传出去**的字面量（`_run([...])` 之类），**排除 add_argument 里的定义**。"""
    src = src_text if src_text is not None else open(os.path.abspath(__file__), encoding='utf-8').read()
    return set(_flag_tokens_in_code(src)) - _argparse_defined_tokens(src)


def _discovery_missing(src_text=None):
    """返回 (missing, exempt_used)。missing = **作为旗标使用**、但既不在 help 选项里、也不在**声明豁免**里的 token。"""
    src = src_text if src_text is not None else open(os.path.abspath(__file__), encoding='utf-8').read()
    toks = set(_flag_tokens_in_code(src))
    disc = _help_discovered_tokens()
    exempt_used = sorted(t for t in toks if t in DISCOVERY_EXEMPT and t not in disc)
    missing = sorted(t for t in toks if t not in disc and t not in DISCOVERY_EXEMPT)
    return missing, exempt_used


HEARTBEAT_KEY = 'data/external-link/bb-copy-staleness'
# ★ 政策起点（明鉴④：「知道写进了注释，做不到没变成不可能」）——政策**生效后**新写入的卡不得含手工时点；
#   生效前的存量**列出不判红**（它们是对**过去**的记录，改写=伪造），**只准单调下降**（ratchet）。
TS_POLICY_SINCE = '2026-09-11T08:25:00+08:00'
# ★ HR 2026-09-22：「**心跳阈值须与检查周期同阶**，否则报警恒真 —— 恒真报警与恒假读数**对称**，同为无信息。」
#   ⇒ 单一来源：刷新周期与阈值**都由这里导出**（plist 的 StartInterval 与阈值不得各自硬编码而漂移）。
STALENESS_REFRESH_SECONDS = 1800          # = plist StartInterval
# ★ HR 2026-09-22 再推一格（裁定③）：「标自由端点须追到【不能再追的那一格】」。
#   我原写「系数 3 = 经验选择」，但**依据**给的是「容忍连续 2 次漏跑 ⇒ 第 3 次告警」——
#   那句依据**实际把 3 导出了** ⇒ 真正的自由端点是【容忍 2 次】那一格，**不是 3**。
#   ⇒ 不追到最后一格的危害：读者看到 3 有依据，就**不会去审「容忍 2 次」这条需求**（自由选择被掩盖）。
STALENESS_TOLERATED_MISSES = 2            # ★ **唯一自由端点**（真正未被导出的那一格）：容忍连续 2 次漏跑
#   依据（这一格为什么是 2 而不是 1 或 3）：周期 30min ⇒ 容忍 2 次 = 最多约 1h 静默不告警
#   （运维上「一次漏跑常见、两次仍可接受」），第 3 次 ≈ 1.5h 即告警。**这是选择，不是推导。**
STALENESS_MAX_AGE_FACTOR = STALENESS_TOLERATED_MISSES + 1   # **导出**（= 容忍次数 + 1），非独立选择
STALENESS_MAX_AGE = STALENESS_MAX_AGE_FACTOR * STALENESS_REFRESH_SECONDS
STALENESS_LABEL = 'com.dsh.cron.bb-copy-staleness'
STALENESS_PLIST = '~/dsh-collab/devices/com.dsh.cron.bb-copy-staleness.plist'
# ★ 解锁条件（**单一来源**，消三处重复）：把「需用户终端」从**假设**升级为【实测】——
#   2026-09-22T14:08+08:00 从**本 agent 会话**执行 `launchctl bootstrap gui/501 <plist>`：
#   ⇒ **exit 5 `Input/output error`**（同时 `plutil -lint` = OK · `launchctl print gui/501` 可达
#     ⇒ 排除了「plist 语法错」与「域不存在」两个候选，剩下的是**调用方上下文**）
#   ⇒ 故「需用户终端」不再是推测，有读数支撑；并已 `cp` 一份到 ~/Library/LaunchAgents
#     （按 launchd 约定**下次登录**由 launchd 装载 —— ★ 这一句是**约定、未实测**，别读成已验证）。
STALENESS_UNLOCK = ('装载触发器：plist 见 ' + STALENESS_PLIST
                    + ' · ★ 实测(2026-09-22T14:08+08:00, 对象=本 agent 会话)：`launchctl bootstrap gui/501` '
                      '⇒ exit 5 Input/output error（plutil OK · gui/501 可达）⇒「需用户终端」由**假设**变**有读数**；'
                      '已 cp 至 ~/Library/LaunchAgents（**下次登录**由 launchd 装载 · 约定未实测）')


def _trigger_installed():
    """触发器是否**已装载**（launchctl 在册）。★ 这一项决定报警**是否携带信息**：
    未装载 ⇒ 心跳必然陈旧 ⇒ **报警恒真 ⇒ 无信息**（HR 的对称判据）。返回 (installed: bool|None, 原文)。"""
    try:
        r = subprocess.run(['launchctl', 'list'], capture_output=True, text=True, timeout=10)
        hit = STALENESS_LABEL in (r.stdout or '')
        return hit, (STALENESS_LABEL + (' 已装载' if hit else ' 未装载'))
    except Exception as e:
        return None, 'launchctl 不可用(' + str(e)[:30] + ')'


def _ts_finding(ts_str, field='ts', policy=None, now=None):
    """纯函数：给一个时点值判「手工特征」类别 + 是否在**政策生效后**（须判红）。
    返回 (类别|None, 是否政策后, 说明)。类别：无时区偏移 / 指向未来 / 整点整分。"""
    s = str(ts_str or '').strip()
    if not s:
        return None, False, ''
    try:
        dt = datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
    except Exception:
        return '不可解析', None, s[:30]
    pol = datetime.datetime.fromisoformat(str(policy or TS_POLICY_SINCE))
    after = (dt >= pol) if dt.tzinfo else None
    now = now or datetime.datetime.now(dt.tzinfo if dt.tzinfo else None)
    if dt.tzinfo is None:
        return '无时区偏移', after, s[:30]
    if dt.tzinfo is not None and (dt - now).total_seconds() > 300:
        return '指向未来 ' + str(int((dt - now).total_seconds())) + 's', after, s[:30]
    # ★ 首版用 `s.endswith(':00')` 判「整点整分」⇒ **被时区偏移骗了**：`+08:00` 的尾巴本身就是 `:00`
    #   ⇒ 修复后的 20 张卡（带 `+08:00` 且有秒）全被误判为手写特征（实测报「存量 25」而实际只剩 5）。
    #   改判：**只看时间分量**（分=0 且 秒=0），与时区写法无关。
    # 判据取「**秒恰为 0**」（= 整分）——手写时点的稳定特征；只看时间分量，与时区写法无关。
    if dt.second == 0:
        return '整分(手写特征)', after, s[:30]
    return None, after, ''


def _domain_ts_scan(limit=40):
    """本域时点审计：返回 (实扫数, 政策后命中[(key,field,why)], 存量命中[(key,field,why)])。"""
    _all, _tot, _err = _scan_domain()
    if _err and _tot is None:
        return None, [], [], []
    ks = [k for k in _all if k.startswith(SELF_DOMAIN) and not os.path.basename(k).startswith('_pc-')]
    _set_census('A36', len(ks), _tot, len([k for k in _all if k.startswith(SELF_DOMAIN)
                                           and os.path.basename(k).startswith('_pc-')]))
    after_hits, legacy, foreign_legacy = [], [], []
    for k in ks:
        st, v = get('local', k)
        if st != 200 or not isinstance(v, dict):
            continue
        _pr = str(v.get('producer') or v.get('from') or '').strip()
        _mine = (not _pr) or (_pr == CANONICAL_ID)
        for f in ('ts', '时点', 'time'):
            if f not in v:
                continue
            kind, after, why = _ts_finding(v.get(f), f)
            if kind is None:
                continue
            if not _mine:
                foreign_legacy.append((k, f, kind))     # ★ 他人卡的存量**不计入我的棘轮**（我的闸门不该由他人打开）
            elif after is True:
                after_hits.append((k, f, kind))
            else:
                legacy.append((k, f, kind))
    return len(ks), after_hits, legacy, foreign_legacy


def _hb_age_seconds(ts_iso, now=None):
    """把心跳卡的时点转成「距现在多少秒」。解析失败返回 None（unknown，不并入新鲜）。"""
    try:
        t = datetime.datetime.fromisoformat(str(ts_iso))
        if t.tzinfo is not None:
            t = t.astimezone().replace(tzinfo=None)
        return (now or datetime.datetime.now()) - t
    except Exception:
        return None


def _hb_verdict(age_seconds, max_age):
    """纯函数（供 A24 双向断言）：(verdict, 说明)。age=None ⇒ unknown(3)；age>max ⇒ stale(3)；否则 fresh(0)。"""
    if age_seconds is None:
        return 3, 'unknown（时点不可解析）—— **不并入新鲜**'
    a = age_seconds.total_seconds()
    if a > max_age:
        return 3, ('**stale**: 心跳已 ' + str(int(a)) + ' 秒未更新（阈值 ' + str(int(max_age))
                   + '）⇒ **触发器疑似已死**')
    return 0, 'fresh: 心跳 ' + str(int(a)) + ' 秒前（阈值 ' + str(int(max_age)) + '）'


def _ts_offset_ok(s):
    """ts 是否带 **UTC 偏移**（可解析且 tzinfo 非空）。返回 (ok, 说明)。
    ★ 这是 TS_POLICY 里「无时区偏移 = 手工时点特征」那一条的**正向执行体**：
    工具**自己写**的时点也必须过它（否则规则只管别人不管自己）。"""
    t = str(s or '').strip()
    if not t:
        return False, '空'
    try:
        dt = datetime.datetime.fromisoformat(t.replace('Z', '+00:00'))
    except Exception:
        return False, '不可解析'
    if dt.tzinfo is None:
        return False, '无时区偏移'
    return True, '带偏移 ' + (dt.strftime('%z') or '')


def _phase_marker_ok(s, p1_ts, p2_ts=None):
    """★ 阶段标记的可核性 = **状态维 ∧ 时间维**（HR 2026-09-22 裁定①）。
    状态维：阶段1（未完成）/ 阶段2（终态）**可区分**；
    时间维：**阶段1 入口时点**存在且**带 UTC 偏移**且不在未来。
    ⇒ 缺时间维的后果：**「长期停在阶段1」与「刚进入阶段1」同形**（读者无法判该不该介入）。
    ★ 并声明承担者：**信封 `ts` 每次 PUT 都刷新 ⇒ 不得用它当阶段入口时点**；
      阶段入口由卡内 `阶段1时点` 字段承担（本函数即按此判）。
    ★ 终态须**冻结**停留时长：若终态仍用 `now − 阶段1入口`，则阶段1 早已结束而读数**随墙钟继续涨**
      ——那正是本工具刚命名并修掉的同一缺陷（**拿一个会变的量去表达一个已结束的状态**）。
      ⇒ 终态改由 `阶段2时点 − 阶段1时点` 计算（**冻结**），故 `阶段2时点` 字段为终态必需。
    返回 (ok, 说明, dwell_seconds|None)。"""
    t = str(s or '')
    p1 = ('未完成·阶段1/2' in t)
    p2 = ('全 PASS' in t) or ('全 FAIL' in t)
    if p1 == p2:
        return False, '**状态维**不足：阶段1/阶段2 两态不可区分', None
    tok, twhy = _ts_offset_ok(p1_ts)
    if not tok:
        return False, '**时间维**缺失：阶段1 入口时点' + twhy + ' ⇒ 长期停在阶段1 与 刚进入阶段1 同形', None
    dt = datetime.datetime.fromisoformat(str(p1_ts).replace('Z', '+00:00'))
    now = datetime.datetime.now(dt.tzinfo)
    if p1:
        # 阶段1 进行中：停留时长**随墙钟增长**是**正确**的（它确实还在阶段1）
        d = (now - dt).total_seconds()
        if d < 0:
            return False, '**时间维**异常：阶段1 入口时点在**未来**(' + str(int(-d)) + 's)', None
        return True, ('阶段1 未完成态 · 入口 ' + str(p1_ts) + ' · **仍在阶段1，已 ' + str(int(d))
                      + 's**（若长期不推进 ⇒ 读者可据此判断该介入）'), d
    # 终态：停留时长须**冻结**（由阶段2时点算），不得随墙钟增长
    tok2, twhy2 = _ts_offset_ok(p2_ts)
    if not tok2:
        return False, '**终态缺冻结量**：`阶段2时点`' + twhy2 + ' ⇒ 无法给出阶段1 的**已结束**停留时长', None
    dt2 = datetime.datetime.fromisoformat(str(p2_ts).replace('Z', '+00:00'))
    d = (dt2 - dt).total_seconds()
    if d < 0:
        return False, '**时间维**异常：阶段2 早于阶段1(' + str(int(-d)) + 's)', None
    return True, ('阶段2 终态 · 阶段1 入口 ' + str(p1_ts) + ' → 阶段2 ' + str(p2_ts)
                  + ' · 阶段1 停留 ' + str(int(d)) + 's（**冻结**：不随墙钟增长）'), d


def _hb_notinstalled(age, max_age, itext, ts):
    """★ 触发器**未装载**时的报文体 —— **先量 age，再断言**。
    存在理由（本函数替换掉的版本留下的自相矛盾样本）：
    改写前此处写死「未装载 ⇒ 心跳**必然**陈旧」，而同一屏的下一行就印着 `心跳 ts=…`。
    实测 `--stale-report` 后立刻跑 `--heartbeat-age`：age ≈ 秒级（阈值 5400），
    却仍印「必然陈旧」⇒ **同一份输出里，声明与它自己印出的读数互相否证** ✓
    （任何读者无需相信任何人即可复核。）⇒ 修正口径：
    **「未装载」只决定「有没有人按时刷」，不决定「此刻是否陈旧」** —— 后者是**可测量**，必须量。
      · 未装载 + 已陈旧 ⇒ 本报警恒真、不携带信息（HR 对称判据）
      · 未装载 + 仍新鲜 ⇒ **本读数携带信息**，但**新鲜度无来源保障**（未装载 ⇒ 它可能由手工或
        会话内替代循环刷新）⇒ **引用者须能说出刷新者**，否则不得读成「触发器在工作」
    返回 (lines, verdict, kind)；kind ∈ {'stale-noinfo' | 'fresh-unattributed'}。

    ★ 入参类型与 `_hb_verdict()` **对齐**（datetime.timedelta | None）—— 首版我按「秒数」写，
      接进调用点即 TypeError：`'>' not supported between 'datetime.timedelta' and 'int'`。
      ⇒ 根因是上游 `_hb_age_seconds()` **名实不符**（名叫 seconds、实返 timedelta）；改名会波及
      A24 与多处引用，本轮**不改**，列为**未闭**；此处改为**镜像 `_hb_verdict` 的既有约定**，
      使合成样本与真实调用**同型**（避免「样本与生产不同型」这一类假样本）。"""
    _ts = str(ts)
    _a = None if age is None else age.total_seconds()
    if _a is None:
        return (['[heartbeat-age] -  触发器**未装载** · 心跳 ts 不可解析(' + _ts[:30] + ')'
                 ' ⇒ **无法判定**（不要读成 fresh，也不要读成已死）',
                 '[heartbeat-age]    解锁条件: ' + STALENESS_UNLOCK],
                3, 'stale-noinfo')
    if _a > max_age:
        return (['[heartbeat-age] -  触发器**未装载** 且 心跳**已陈旧**(' + str(int(_a)) + 's > '
                 + str(max_age) + 's) ⇒ **本报警恒真、不携带信息**',
                 '[heartbeat-age]    （HR 判据：恒真报警与恒假读数对称，同为无信息 ⇒ 不重复报「疑似已死」）',
                 '[heartbeat-age]    实测: ' + itext + ' · 心跳 ts=' + _ts + ' · 阈值 ' + str(max_age) + ' 秒',
                 '[heartbeat-age]    解锁条件: ' + STALENESS_UNLOCK],
                3, 'stale-noinfo')
    return (['[heartbeat-age] -  触发器**未装载** 但 心跳**仍新鲜**(' + str(int(_a)) + 's ≤ '
             + str(max_age) + 's) ⇒ **本读数携带信息**，但**新鲜度无来源保障**',
             '[heartbeat-age]    ★ 未装载只说明「无人按时刷」，不说明「此刻陈旧」—— 不要读成「触发器在工作」',
             '[heartbeat-age]    实测: ' + itext + ' · 心跳 ts=' + _ts + ' · 阈值 ' + str(max_age) + ' 秒',
             '[heartbeat-age]    引用本行时须能说出**刷新者**（手工 / 会话内替代循环 / 其他）',
             '[heartbeat-age]    解锁条件: ' + STALENESS_UNLOCK],
            3, 'fresh-unattributed')


def cmd_heartbeat_age(args):
    """★ 读者侧的**触发器活体检查**（HR：①方案的风险是「**失效是静默的**」，
    且 `--stale-report` **只能报『卡过期』、报不出『触发器死了』**）。
    关键结构点：**死掉的触发器无法报告自己已死** ⇒ 这项检查必须由**读者**运行，不能由触发器自己做。
    ⇒ 本命令不依赖任何触发器存活：即使心跳停在数小时前，它照样能报「疑似已死」。"""
    st, v, note = _card_fetch(HEARTBEAT_KEY)
    if st != 200:
        print('[heartbeat-age] X 心跳卡不可读: ' + str(note) + ' ⇒ **无法判定触发器是否存活**（不要读成 fresh）')
        return 3
    age = _hb_age_seconds((v or {}).get('ts'))
    _inst, _itext = _trigger_installed()
    if _inst is False:
        # ★ A51：未装载 ⇒ 只能断言「无人按时刷」，**不能**断言「此刻陈旧」（后者须先量 age）。
        _lines, _v51, _k51 = _hb_notinstalled(age, args.max_age, _itext, (v or {}).get('ts'))
        for _l in _lines:
            print(_l)
        return _v51
    verdict, why = _hb_verdict(age, args.max_age)
    print('[heartbeat-age] ' + ('OK  ' if verdict == 0 else 'X  ') + why)
    print('[heartbeat-age] 依据: 读者侧运行(死触发器无法自报)；阈值 ' + str(args.max_age) + ' 秒可由 --max-age 覆盖')
    return verdict


SIX_ITEMS = ['判据', '范围', '时点', '对象', '正反控', '受自身干预']


def _six_items_check(text):
    """★ HR 2026-09-11 裁定：**方法卡正式格式 = 两层的六项** ——
    核心四项（**判据 · 范围 · 时点 · 对象** = 可复现最小集）+ 条件两项（**正反控**：凡判据皆须；
    **受自身干预**：凡该数在讨论窗口内变动者须）。三套表述归并到此。
    ⇒ 本函数是它的**执行体**：`--check` 每次输出「数报」行，必须含全六项。返回 (ok, 缺项)。"""
    t = str(text or '')
    miss = [x for x in SIX_ITEMS if x not in t]
    return (not miss), miss


CANONICAL_ID = 'external-link-agent'


def _producer_locks(producer):
    """★ **自锁死【形状】签名**（writer-agnostic）：
    bb-write 归属守卫在无 session-<8hex> 令牌时按**原串比较** ⇒ 若 producer 带**括号后缀**（展示名），
    写者以自己的规范 id 再写时会**被拦**（合法写入者被迫用 `--force` ⇒ 守卫被架空）。
    ★ 不判「必须等于我的 id」——**他人以自己身份写的键不算自锁死**（那是另一个议题：越域写入，只报不判）。
    返回 (是否带该形状: bool, 原因)。"""
    p = str(producer or '').strip()
    if not p:
        return False, '未声明 producer（守卫不介入）'
    if '(' in p:
        return True, 'producer 含括号后缀（展示名混入身份）: ' + p[:40]
    return False, 'ok'


def _writer_coverage(limit=40):
    """★ HR 裁定的**解锁条件**可测化：「若 writer 覆盖率提升，此项自动转为可判」。
    ★ HR 2026-09-22 通则（用集合作分母前须先判**成员同质性**）：本域真实键包含**自有卡与他人卡** ⇒
      **单一百分比会把两者混为一谈** ⇒ 现**按归属分层**返回：
      (全部键数, 全部命中, 全部%, 自有键数, 自有命中, 自有%)。"""
    _all, _tot, _err = _scan_domain()
    if _err and _tot is None:
        return None, None, None
    ks = [k for k in _all if k.startswith(SELF_DOMAIN) and not os.path.basename(k).startswith('_pc-')]
    _set_census('A31', len(ks), _tot, len([k for k in _all if k.startswith(SELF_DOMAIN)
                                           and os.path.basename(k).startswith('_pc-')]))
    have = mine = have_mine = 0
    for k in ks:
        st, v = get('local', k)
        if st != 200 or not isinstance(v, dict):
            continue
        _pr = str(v.get('producer') or v.get('from') or '').strip()
        _is_mine = (not _pr) or (_pr == CANONICAL_ID)
        _has_w = bool(str(v.get('writer') or '').strip())
        if _is_mine:
            mine += 1
            have_mine += 1 if _has_w else 0
        if _has_w:
            have += 1
    _p = lambda a, b: (round(100.0 * a / b, 1) if b else 0.0)
    return len(ks), have, _p(have, len(ks)), mine, have_mine, _p(have_mine, mine)


def _bypass_scan(limit=40):
    """★ HR 新族：「**绕过的不是规则，是入口**」——我的复制路径已堵，而**临时 heredoc 绕过了统一入口**。
    可观测的**绕过代理**：卡的写入时点**晚于政策起点**、却**没有 `writer` 字段** ⇒ 疑似未经统一入口写入。
    ★ 诚实边界：真正的绕过通道（哪个脚本写的）**不可观测**（与 writer 覆盖率同属「缺观测通道」）⇒ 本判据只是**代理**，不是判定。
    返回 (实扫数, 自有卡命中[(key,ts)], 他人卡命中数)。"""
    _all, _tot, _err = _scan_domain()
    if _err and _tot is None:
        return None, [], 0
    ks = [k for k in _all if k.startswith(SELF_DOMAIN) and not os.path.basename(k).startswith('_pc-')]
    _set_census('A39', len(ks), _tot, len([k for k in _all if k.startswith(SELF_DOMAIN)
                                           and os.path.basename(k).startswith('_pc-')]))
    pol = datetime.datetime.fromisoformat(TS_POLICY_SINCE)
    mine, foreign = [], 0
    for k in ks:
        st, v = get('local', k)
        if st != 200 or not isinstance(v, dict):
            continue
        if str(v.get('writer') or '').strip():
            continue
        try:
            t = datetime.datetime.fromisoformat(str(v.get('ts') or '').replace('Z', '+00:00'))
        except Exception:
            continue
        if t.tzinfo is None:
            t = t.replace(tzinfo=pol.tzinfo)
        if t < pol:
            continue                                  # 政策前的存量 ⇒ 不判
        prod = str(v.get('producer') or v.get('from') or '').strip()
        if prod and prod != CANONICAL_ID:
            foreign += 1
        else:
            mine.append((k, str(v.get('ts'))))
    return len(ks), mine, foreign


def _domain_producer_scan(limit=40):
    """扫本域真实键的 `producer`，找出**会被守卫拦**的（自锁死签名）。返回 (实扫数, 探针排除数, 命中列表)。"""
    _all, _tot, _err = _scan_domain()
    if _err and _tot is None:
        return None, None, [], [], []
    ks = [k for k in _all if k.startswith(SELF_DOMAIN)]
    real = [k for k in ks if not os.path.basename(k).startswith('_pc-')]
    probes = len(ks) - len(real)
    # ★ HR②：在真实键上**实测**身份字段（与执行用表对账；冲突时以实测为准）
    global IDENTITY_MEASURED
    IDENTITY_MEASURED = _identity_field_measured(real, get)
    _set_census('A31', len(real), _tot, probes)
    hits, foreign, foreign_locks = [], [], []
    for k in real:
        st, v = get('local', k)
        if st != 200 or not isinstance(v, dict):
            continue
        pr = v.get('producer') or v.get('from')
        lock, why = _producer_locks(pr)
        _is_mine = (not str(pr or '').strip()) or (str(pr).strip() == CANONICAL_ID)
        if lock and _is_mine:
            hits.append(k + ' :: ' + str(pr)[:30] + ' (' + why[:30] + ')')
        elif lock:
            # ★ 他人卡的形状命中**只报不判**：否则**他人的写入会打开我的闸门**（= 恒假/永远报警），
            #   且那属于**判别人的产物**（越权判定）。同一原则此前已用于「他人身份只报不判」。
            foreign_locks.append(k + ' :: ' + str(pr)[:24])
        elif pr and str(pr).strip() != CANONICAL_ID:
            foreign.append(k + ' :: ' + str(pr)[:30])
    return len(real), probes, hits, foreign, foreign_locks


VOLATILE_IN_TEXT = [
    ('版本号', re.compile(r'\bv\d+\.\d+\.\d+\b')),
    ('计数', re.compile(r'\d+\s*(项|键|个|条|次)')),
    # ★ 修正误判：纯数字（如日期 20260911）不是摘要片段 ⇒ 要求含 a-f 字母
    ('摘要片段', re.compile(r'\b(?=[0-9a-f]{8,}\b)(?=[0-9a-f]*[a-f])[0-9a-f]{8,}\b')),
    ('字节数', re.compile(r'\d{4,}\s*B\b')),
]


TS_NEARBY = re.compile(r'\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2})?')


def _card_strings(o, path=''):
    """递归收集卡内**全部字符串**（含嵌套/列表），返回 [(路径, 字符串)]。
    ★ 存在理由：A32 首版只扫顶层 ⇒ **声明「本卡字符串字段」而实现只覆盖顶层** = **声明范围大于实际覆盖**（声明不实）。"""
    out = []
    if isinstance(o, str):
        out.append((path, o))
    elif isinstance(o, dict):
        for kk, vv in o.items():
            out += _card_strings(vv, (path + '.' + str(kk)) if path else str(kk))
    elif isinstance(o, list):
        for i, vv in enumerate(o):
            out += _card_strings(vv, path + '[' + str(i) + ']')
    return out


def _volatile_in_text(text, with_ts_rule=True):
    """★ HR 定稿补条：「**静态文本里的计数：带时点的历史快照 = 合法；无时点的当前值 = 违规**」。
    理由（HR）：**能变的是「当前值」，不是「当时的记录」** ⇒ 两者在文本上**同形，只差时点**。
    ⇒ 返回 (违规, 放行)。**放行 = 命中但同一文本内伴随 ISO 时刻**（= 历史快照）。"""
    t = str(text or '')
    has_ts = bool(TS_NEARBY.search(t))
    viol, excused = [], []
    for name, rx in VOLATILE_IN_TEXT:
        for m in rx.finditer(t):
            item = (name, m.group(0))
            if with_ts_rule and has_ts:
                excused.append(item)
            else:
                viol.append(item)
    return viol, excused


def _ts_policy_check(scan, baseline):
    """纯函数（供双向断言）：政策判定 —— **值落于政策起点之后的命中必须为 0**；存量 ≤ 基线（**ratchet：只准降**）。
    scan = (实扫数, 政策后命中, 存量命中)。返回 (ok, 说明)。"""
    n, after, legacy = scan
    if n is None:
        return False, '本域不可读 ⇒ 不可判（不冒充通过）'
    bad = []
    if after:
        bad.append('政策后命中 ' + str(len(after)) + ' 项（须为 0）')
    if len(legacy) > int(baseline or 0):
        bad.append('存量 ' + str(len(legacy)) + ' > 基线 ' + str(baseline) + '（ratchet 被破）')
    return (not bad), ('实扫 ' + str(n) + ' 键 · 政策后 0 · 存量 ' + str(len(legacy)) + ' ≤ 基线 ' + str(baseline)
                       ) if not bad else '；'.join(bad)


def _handover_check(tmf, covered, form_exempt):
    """HR 通则「**排除即转交**」的执行体：被排除者须有接手方，且接手方**三层可核**
    （接手方 · 检查动作 · 检出读数）+ **同源声明** + **单独计数** + ★HR④**独立性栏**。
    ★ HR④：**接手（有人）与独立（他人）是两层** ⇒ 独立性取值须为
      `自接手·独立性缺失` 或 `他方·独立（**具名**）`；**写「他方」而不具名 ⇒ 视同缺项**（否则「独立」二字可白填）。
    返回 (ok, 缺接手, 缺层, 缺同源声明, 无单独计数, 缺/坏独立性栏)。"""
    layers = ('接手方', '检查动作', '检出读数')
    miss, miss_layer, miss_src, miss_cnt, miss_ind = [], [], [], [], []
    for name, ent in list(covered.items()) + list(form_exempt.items()):
        if not isinstance(ent, dict):
            miss.append(name); continue
        for L in layers:
            if not str(ent.get(L) or '').strip():
                miss_layer.append(name + ':' + L)
        if '同源' not in ent:
            miss_src.append(name)
        if not str(ent.get('单独计数') or '').strip():
            miss_cnt.append(name)
        _iv = str(ent.get('独立性') or '').strip()
        if _iv.startswith('自接手·独立性缺失'):
            pass
        elif _iv.startswith('他方·独立'):
            # 他方须**具名**：括号内须有非空名字（否则「他方」是可白填的两个字）
            if not re.search(r'[（(][^）)]{2,}[）)]', _iv):
                miss_ind.append(name + ':他方未具名')
        else:
            miss_ind.append(name)
    orphan = [f for f in (tmf or []) if f not in covered]
    return ((not orphan and not miss and not miss_layer and not miss_src and not miss_cnt and not miss_ind),
            orphan, miss_layer, miss_src, miss_cnt, miss_ind)


def _managed_coverage_check(tmf, covered):
    """明鉴④：**豁免掉的覆盖面必须有另一条判据接手**（否则并集 < 声称并集）。
    返回 (ok, 无人接手的豁免字段, 指向不存在判据的引用)。"""
    orphan = [f for f in (tmf or []) if f not in covered]
    bad_ref = [f + '→' + t for f, ts in covered.items() for t in ts if t not in ASSERT_SCOPE]
    return (not orphan and not bad_ref), orphan, bad_ref


def _conventions_check(conventions):
    """HR 新判据的执行体：每个发布项要么给出**真实存在的执行体断言**，要么**显式声明无执行体**（None）。
    返回 (ok, 指向不存在执行体的项, 显式无执行体的项)。"""
    bad, none_declared = [], []
    for name, tags in conventions.items():
        if tags is None:
            none_declared.append(name)
            continue
        for t in tags:
            if t not in ASSERT_SCOPE:
                bad.append(name + '→' + t)
    return (not bad), bad, none_declared


def _five_steps_check(steps, polarity_counts):
    """五步链的**执行体**：把 HR 裁定的五步映射到本工具对照集 —— 每步须有真实承载（标签存在 / 极性计数>0）。
    返回 (ok, 各步落地摘要, 落空步)。"""
    land, missing = [], []
    for name, kind, val in steps:
        if kind == 'tags':
            bad = [t for t in val if t not in ASSERT_SCOPE]
            if bad:
                missing.append(name + '→' + ','.join(bad))
            else:
                land.append(name + '(标签 ' + ','.join(val) + ')')
        else:
            n = polarity_counts.get(val, 0)
            if not n:
                missing.append(name + '→极性表中无「' + val + '」')
            else:
                land.append(name + '(' + val + ' ' + str(n) + ' 项)')
    return (not missing), land, missing


def _deps_check(deps_map, card):
    """HR「判据的依赖项，其自身必须是可检对象」的执行体。
    ★ 依赖类别须能表达【阶段性必需】（本函数修一个实测到的**断言互斥**）：
      A45 要求**终态**须有 `阶段2时点`，而本函数原来要求「已声明的 card_field 依赖**无条件存在**」
      ⇒ 两者各自都对，**合起来在阶段1 必然判红**（实测：缺依赖 ['A45:阶段2时点']）
      ⇒ 于是**任何「阶段性必需字段」都无法被无条件依赖声明表达**。
      ⇒ 新增 `card_field_when_terminal:`：**终态才必需**；阶段1 时该依赖尚未到必需时点，
        返回**第三态**（记入 pending，**不冒充通过**，也不判红）。
    判「终态」的口径与 A45 同一处：卡内「自测」出现 `全 PASS`/`全 FAIL` ⇒ 终态。
    返回 (ok, 未声明依赖, 缺失依赖, 尚未必需)。"""
    st = str((card or {}).get('自测') or '')
    terminal = ('全 PASS' in st) or ('全 FAIL' in st)
    miss_decl = [t for t in ASSERT_SCOPE if t not in deps_map]
    bad_kind = [t + ':' + d for t, ds in deps_map.items() for d in ds
                if not (d in DEP_KINDS or d.startswith('card_field:') or d.startswith('card_field_when_terminal:'))]
    miss_dep, pending = [], []
    for t, ds in deps_map.items():
        for d in ds:
            if d.startswith('card_field_when_terminal:'):
                f = d.split(':', 1)[1]
                if f in (card or {}):
                    continue
                (miss_dep if terminal else pending).append(t + ':' + f)
            elif d.startswith('card_field:'):
                f = d.split(':', 1)[1]
                if f not in (card or {}):
                    miss_dep.append(t + ':' + f)
            elif d == 'file' and not os.path.exists(os.path.abspath(__file__)):
                miss_dep.append(t + ':file')
    return (not miss_decl and not miss_dep and not bad_kind), miss_decl, miss_dep + bad_kind, pending


def _selftest_claim_check(text, n_expected, ver):
    """HR 通则「**凡会变的东西不得写进不变的容器**（声明文本/卡/样板）⇒ 容器只放口径，量由制品自身报出」。
    本函数是它的**守卫**：卡里若写了断言计数/版本，就必须与**本次运行实得**一致，否则报不平。
    返回 (ok, 说明)。**缺字段 ⇒ 视为「不写」，是合规的**（由调用方判 skipped）。"""
    t = str(text or '')
    m = re.search(r'项数\s*(\d+)', t) or re.search(r'(\d+)\s*项', t)
    mv = re.search(r'v(\d+\.\d+\.\d+)', t)
    bad = []
    if not m:
        bad.append('缺断言计数')
    elif int(m.group(1)) != n_expected:
        bad.append('计数 ' + m.group(1) + ' != 实得 ' + str(n_expected))
    if not mv:
        bad.append('缺版本')
    elif mv.group(1) != ver:
        bad.append('版本 ' + mv.group(1) + ' != ' + ver)
    return (not bad), bad


def preflight():
    """★ 默认预检 —— 出处：HR 四级阶梯「**待触发门须改默认：安全路径必须是默认路径**」。
    本工具的 A1–A11 此前只在**人记得跑 --check** 时才生效 ⇒ 整套自测属**待触发门**。
    故把**廉价且离线**的断言（版本声明位 / 语义锚点）提到**每次操作前默认跑**：
    失败即拒绝(exit 8)，不进入写路径；`--no-preflight` 可明示跳过（越权须明示，同 --force 形态）。
    返回 (ok: bool, msg: str)"""
    try:
        src = open(os.path.abspath(__file__), encoding='utf-8').read()
        decl = re.findall(r"^VERSION = '([^']+)'", src, re.M)
        if decl != [VERSION]:
            return False, '版本声明位异常 ' + str(decl) + ' (期望唯一且==' + VERSION + ')'
    except Exception as e:
        return False, '预检读源码失败: ' + str(e)[:40]
    ok8, why8 = _anchors_ok()
    if ok8 is False:
        return False, '语义锚点解析失败 ' + why8
    # ★ HR③：**契约交叉引用**在注册期（=每次操作前）就核 ⇒ 违规 exit 8，**不进写路径**。
    okc, badc = _contract_check()
    if not okc:
        return False, ('契约引用不一致（注册期 fail-fast，共 ' + str(len(badc)) + ' 项）: ' + '; '.join(badc[:5]))
    fpok, fpwhy = _fingerprint_ok()
    if fpok is False:
        # ★ 刻意**只告警不阻断**：卡过期说明**登记失真**，不影响 copy 本身是否安全 ⇒
        #   若在此阻断，就变成「恒假/永远报警」（见 docstring 两对照）。由 --check A16 判 FAIL。
        print('[preflight] ! 指纹告警(不阻断): ' + fpwhy)
    return True, ('版本声明位唯一 · 锚点 ' + why8 + ' · **契约交叉引用一致**（注册期核）')


HANDOVER_LAYERS = ('接手方', '检查动作', '检出读数', '同源', '单独计数')


def _expand_assert_keys(k):
    """★ 展开复合键 `'A16/A22/…'` —— 它**一条登记覆盖多条断言**。
    必要性（A53 首跑抓到）：强度/无解表用复合键，而范围表是逐条 ⇒ 交叉引用对账会假报违约；
    更重的是**分母**：按「条目」数分布会把 13 条算成 1 条 ⇒ 分布被压缩（覆盖率报不准）。
    返回按键顺序展开后的断言列表。"""
    return [x for x in str(k).split('/') if x]


def _contract_check(maps=None):
    """★ HR③ 我侧对照物：**注册表之间的交叉引用 = 契约** ⇒ 须在【注册期】fail-fast，
    而不是等某人跑 `--check`（那正是「待调用才暴露」的待触发门）。
    纯函数：只读各注册表，不碰网络/磁盘 ⇒ 廉价到可以每次操作前跑。
    `maps` 可传入**故意损坏的副本**用于 A53 的合成样本。
    返回 (ok, 违约列表)。"""
    m = maps or {}
    scope = m.get('scope', ASSERT_SCOPE)
    pol = m.get('pol', CONTROL_POLARITY)
    deps = m.get('deps', ASSERT_DEPS)
    fals = m.get('fals', FALSIFIABILITY)
    strength = m.get('strength', STRENGTH)
    nosol = m.get('nosol', NO_SOLUTION)
    dead = m.get('dead', SELF_REPORT_DEAD_ZONE)
    cross = m.get('cross', CROSS_DOMAIN)
    covered = m.get('covered', TOOL_MANAGED_COVERED)
    formex = m.get('formex', FORM_EXEMPTIONS)
    idf = m.get('idf', IDENTITY_FIELDS)
    bad = []
    for t in scope:
        if t not in pol:
            bad.append('极性缺:' + t)
        if t not in deps:
            bad.append('依赖声明缺:' + t)
        if t not in fals:
            bad.append('可失败性缺:' + t)
    for name, tbl in (('强度', strength), ('无解', nosol), ('死区', dead), ('跨域', cross)):
        for t in tbl:
            for sub in _expand_assert_keys(t):
                if sub not in scope:
                    bad.append(name + '表引用了不存在的断言:' + sub)
    for name, tbl in (('字段豁免', covered), ('形态豁免', formex)):
        for n, ent in tbl.items():
            if not isinstance(ent, dict):
                bad.append(name + '条目非字典:' + n); continue
            for L in HANDOVER_LAYERS:
                if L not in ent:
                    bad.append(name + '缺层:' + n + ':' + L)
            iv = str(ent.get('独立性') or '')
            if not (iv.startswith('自接手·独立性缺失') or iv.startswith('他方·独立')):
                bad.append(name + '独立性栏非法或缺:' + n)
            elif iv.startswith('他方·独立') and not re.search(r'[（(][^）)]{2,}[）)]', iv):
                bad.append(name + '他方未具名:' + n)
    for d, fields in idf.items():
        if not isinstance(fields, tuple) or not fields or not all(isinstance(f, str) and f for f in fields):
            bad.append('身份字段声明非法:' + str(d))
    return (not bad), bad


def _preflight_gate(args):
    """返回 None=放行，或退出码。"""
    if getattr(args, 'no_preflight', False):
        return None
    ok, msg = preflight()
    print('[preflight] ' + ('OK  ' if ok else 'X   ') + msg)
    if not ok:
        log('preflight FAIL ' + msg)
        return 8
    return None


# ---------------------------------------------------------------- 阳性/阴性对照
def cmd_refcheck(args):
    """核对「引用」是否指向真实存在的字段（字段名级引用）。
    ★ 不复制值、**不输出任何值**；但会**读入**源键 —— 对敏感键这是「读而不印」，
      若你的纪律是「不读旧值」，请不要对本键用 refcheck（此不对称是刻意的，非疏漏）。"""
    _g = _preflight_gate(args)
    if _g is not None:
        return _g
    st, v = get(args.src_server, args.key)
    if st == 404:
        print('[refcheck] X 被引用键不存在(404) ' + args.key + ' @' + args.src_server
              + ' —— 引用指向空物（这一种会被发现）')
        return 3
    if st != 200 or v is None:
        print('[refcheck] ? 不可读(status=' + str(st) + ') —— unknown，不并入一致')
        return 3
    if sensitive_fields(v) or sensitive_mentions(v):
        _hs, _mn = sensitive_fields(v), sensitive_mentions(v)
        if _hs:
            print('[refcheck] ! 被引用键含**凭据形**字段(' + ','.join(_hs[:4]) + ') ⇒ 已读入以核对字段名，**未输出任何值**')
        else:
            print('[refcheck] ! 被引用键含**提到凭据词**的文档字段(' + ','.join(_mn[:4]) + ') ⇒ 非凭据形，仅提示，未输出值')
    u = unwrap(v)
    present, missing = [], []
    for f in args.field:
        cur, ok = u, True
        for part in str(f).split('.'):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            elif isinstance(cur, list):
                try:
                    cur = cur[int(part)]
                except Exception:
                    ok = False
                    break
            else:
                ok = False
                break
        (present if ok else missing).append(str(f))
    print('[refcheck] ' + args.key + ' @' + args.src_server + ' | 存在=' + str(len(present))
          + ' | 缺失=' + str(len(missing)) + ((' | 缺失项: ' + ','.join(missing)) if missing else ''))
    if JSON_OUT:
        print(json.dumps({'tool': 'bb-copy', 'cmd': 'refcheck', 'version': VERSION, 'key': args.key,
                          'src_server': args.src_server, 'present': present, 'missing': missing,
                          'exit': 0 if not missing else 4, 'ok': not missing}, ensure_ascii=False))
    log('refcheck ' + args.key + ' | missing=' + str(len(missing)))
    return 0 if not missing else 4


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


# ★ HR:「**把不可用条件写进输出**」—— 每条断言必须声明**它实际覆盖的范围**。
#   结构保障（不是提醒）：未声明的断言被打上 ★未声明范围★ **并让整个 --check 判红** ⇒ 无法静默通过。
ASSERT_SCOPE = {
    'A1': '本工具 CLI（--body/--json/--subject 在 copy 上不可表达）；不覆盖他人工具',
    'A2': '探针键 · 本机复本 · 逐字段',
    'A3': '探针键 · 本机复本',
    'A4': '探针键 · 本机复本',
    'A5': '探针键 · 本机复本',
    'A6': '探针键 · 本机复本（输出文本不出现敏感值）',
    'A7': '本文件源码文本（声明位）× 运行时常量',
    'A8': '本卡声明的锚点 × 本文件源码',
    'A9a': '探针键 · 本机复本',
    'A9b': '探针键 · 本机复本',
    'A10': '探针键 · 本机复本',
    'A11': '探针键 × 两侧复本（本地+中央）· 核效果非自报',
    'A12': '/tmp 副本 + 探针键 · 本机 · 核效果（被拦前后值未变）',
    'A13a': '探针键 · 本机复本',
    'A13b': '探针键 · 本机复本',
    'A14': '本卡（data/registry/bb-copy-tool-v1）文本',
    'A15': '★ **仅本卡**（不覆盖全网卡；全网需独立 lint，归属待裁定）',
    # ★ HR①（独立性须声明**共享面**）：外部 md5/stat 与本工具**同机·同钟·同文件系统** ⇒ 只排除单实现错，**不排除共因**
    'A16': '本卡 × 本文件 × 独立实现（外部 md5/stat）· ★ **共享面=同机/同钟/同文件系统** ⇒ 仅排除单实现错，不排除共因',
    # ★ 范围文本里**不放会变的数**（本行原写死「26 键」，而键数会随新建键变化 ⇒ 静态文本立刻过期）；
    #   数由断言自身报出（「实扫 N 键」），范围只声明**口径**。
    'A17': '★ **仅本域** data/external-link/* 真实键（排除 _pc-* 探针）· 键数以本行报数为准',
    'A18': '本工具声称路径（生成/核验）× 本文件；**不含**「过期的真(3)」该极（需真实历史，归 A22）',
    'A19': '本工具声称门禁 · /tmp 副本（天然不同步样本）',
    'A20': '范围强制机制本身（纯函数双向）',
    'A21': '★ 仅**本进程内**的 HTTP 读取（keys/card/ns）；**不覆盖**经子进程(bb-write)的写入、不覆盖他人工具',
    # ★ A32 首跑命中此处：原写「历史仅 **1 条**时…」= **静态文本里放会变的计数**（历史深度会变）⇒ 改为只声明口径
    'A22': '本工具声称两问/四态 × **指纹历史深度**（深度不足以构造「过期的真」时 ⇒ skipped，不冒充通过）',
    # ★ HR 通则「会变的东西不得写进不变的容器」：原文本写死「豁免 5 个」，豁免变化即过期 ⇒ 只留口径，条数由断言自报
    'A23': '三段式：**定义**(add_argument) × **提供**(root+3 子命令 help) × **使用**(传出字面量)；声明外部见本行报数',
    'A24': '心跳活体判定纯函数（不依赖心跳卡是否可读；真实读卡另由 --heartbeat-age 报 unknown）',
    'A25': '本卡「自测」字段 × 本次运行的断言计数/版本；**缺字段=不写=合规(skipped)**',
    'A26': '源码内 ASSERT_SCOPE × CONTROL_POLARITY 两表（极性表**以代码为准**，卡内不得再抄一份散文表）',
    'A27': '本卡 ts/ts_epoch × 注入路径；含三个合成样本（无偏移/指向未来/缺字段）',
    'A28': '/tmp 副本 × 本卡 artifact_path（realpath 比对）',
    'A29': '源码内 CONTAINER_SCOPED × SCOPE_ALLOW 两表（**无许可集的范围声明会被点名**）',
    'A30': '本次数报行文本 × SIX_ITEMS；合成缺项样本（只给四项）必须被判缺',
    'A31': '本卡 producer × 本域真实键 producer（排除 _pc-* 探针）× 合成「名字 (后缀)」样本',
    'A32': '源码文本 + **本卡全部字符串（递归，含嵌套；路径为字段名）**；豁免两类：**顶层字段声明为 tool_managed_fields** 与 **文本含 ISO 时刻**；两个合成样本双向必验',
    'A33': '源码内 ASSERT_DEPS × 本卡字段；**依赖须能表达【阶段性必需】**（`card_field_when_terminal:`，未到必需时点记**第三态**）；**三个合成样本**：删 `自测` ⇒ 必被点名 · 终态缺条件依赖 ⇒ 必被点名 · 终态带它 ⇒ 必**不**被点名（防条件依赖退化为恒真）',
    'A34': '源码内 PUBLISHED_CONVENTIONS × ASSERT_SCOPE 两表；**显式无执行体项会被列出**',
    # ★ 范围文本必须准确：首版写「合成去掉负控**步** ⇒ 必报落空」，而实测那种造法**报不出来**（步被删即不被检查）
    # ★ 范围文本必须与实际覆盖一致：A35 首版写「合成去掉负控**步** ⇒ 必报落空」，那种造法实际报不出来 ⇒ 已改
    'A35': '源码内 FIVE_STEPS × (ASSERT_SCOPE ∪ 极性计数)；合成样本为**保留该步但极性表无负控** ⇒ 必报落空',
    'A36': '本域真实键的 ts/时点/time，**棘轮只计自有卡**（他人卡存量只报不计，否则他人写入会打开我的闸门）× 卡内 `ts_audit_baseline`；含两个合成过线样本',
    'A37': '源码内 ENUM_SPECS × 本卡全文；**合成不存在的成员名必被判缺**',
    'A38': '**卡内自测串**里的编号范围 × `_assert_range_label()`（**不扫全源码**：合成样本里的故意错标签属判据自身）；合成不一致范围必被抓',
    # ★ HR② 裁定：此为【**线索**】非检查；形式要求=**显式声明拦得住谁**（否则读者读成「绕过已被防住」= 声明不实）
    'A39': '★ **线索（非检查）**：本域政策后写入的自有卡 × writer 字段；**拦得住谁**=遗漏 writer 的疏忽写入 · **拦不住谁**=故意填 writer 的绕过（内容可伪造）；**不覆盖**真正的写入通道（不可观测）· 他人卡只报不判',
    'A40': '★ 通则「**排除即转交**」（HR 准予升格）的执行体：字段排除 × 形态排除，接手方须**三层可核＋同源声明＋单独计数＋独立性两栏**'
           '（HR④：**接手有人/独立他人**是两层，他方**须具名**）；**三个合成样本**：无人接手必点名 · 「他方未具名」必判坏 · 「他方具名」必判好',
    'A41': '★ 常量关系（阈值 = (容忍次数+1)×周期 **导出**）· **自由端点须落在【容忍次数】那一格**（追到不能再追）· '
           '+ **plist 文件 StartInterval**；**不含** launchctl 实际装载态（那由 --heartbeat-age 读者侧报）；含合成样本（系数被写成独立常量 ⇒ 必判红）',
    # ★ 明鉴采纳我的表述并指出：他的原版是「症状描述」（会误伤「意图即字典序」的情形），我的版本是「来源对比」（无副作用）
    'A42': '**判据=意图序 ≠ 实现序 ⇒ 错**（不是「字典序本身错」）；以历史反例（整数序取 A38 / 字符串序得 A9b）作对照实现；**终止于可执行比较**',
    'A43': '源码内范围文本含「文本」的断言 × 排除方式登记表（**须同时声明三解法之①②③**）；**本条只查登记完整性**（不看正文语义）',
    # ★ 明鉴①：反向证据成立 ⟺ **搜索空间穷尽且可声明** ⇒ 本行**报出搜索空间字节数**以证穷尽；被排除的只有「字面值」这一形态
    # ★ 明鉴②补全：穷尽 ⟺ 五条件（截断/起点/范围/无缓存/解码）—— 本行逐条报出
    'A44': '★ 本文件**全文**（穷尽=**五条件**：读入字节数==文件字节数 ∧ 起点==0 ∧ 逐字节==全文件 ∧ 与外部实现现取一致（无缓存）∧ 解码无替换字符——**读取显式用 replace 模式使该条件可触发**）× 当前范围标签字面值（**反向证据**）；两个合成样本必被抓',
    'A45': '本卡「自测」阶段标记 × `阶段1时点` 字段 —— **状态维**（阶段1/阶段2 可区分）∧ **时间维**'
           '（阶段1 入口时点须在卡内、带偏移、不在未来）· **终态须由 `阶段2时点` 给冻结的停留时长**'
           '（否则读数随墙钟虚涨）；含合成样本（去掉时间维 / 终态缺冻结量 ⇒ 必判红）',
    'A46': '源码内 FALSIFIABILITY（每条断言的可失败性证据）× ASSERT_SCOPE；未声明者必被点名（本条自指）',
    'A47': '源码内 STRENGTH（堵/拦类机制的强度档与「对故意者是否有效」）× ASSERT_SCOPE；格式错必被点名',
    'A48': '★ **带分母的自核**（含**文本**探测）：检查项总数 × 涉跨域子集 × CROSS_DOMAIN（工具×对象域×档）；'
           '未登记者必被点名；★ 文本探测须**区分【域】【人】【否定语境】**（`_cd_texty()` 依次剥除）；'
           '**三个合成样本**：合成「他人卡」未登记 ⇒ 必被点名 · 合成「独立他人」（指人）⇒ 必不误判 · '
           '合成「排除说明自指」⇒ 必不误判',
    'A49': '归属标注串 × `_attribution_ok()`（自跑须带标记；第三方须含**主体+时点**）；**两个合成样本方向相反**（无主体必拒 / 有主体必过）',
    # ★ A32 首跑抓到此处：范围文本写了「≥12 键值对」= 静态文本放计数 ⇒ 改为**口径**（下限以本行报数为准）
    'A50': '报告行 × `_report_ok()`（键值对数量须达下限——**下限以本行报数为准**，值须全非空）；**两个合成样本**（空输出 / 有键无值）必被拒',
    # ★ A51 自身即缺陷样本的产物 —— 原本用「未装载」这一个条件去**无条件断言**另一个可测量的量。
    'A51': '心跳报文体 × `_hb_notinstalled()`（未装载时的**两态**：已陈旧 / 仍新鲜）；**两个合成样本方向相反**'
           '（陈旧必印「恒真·无信息」 / 新鲜**不得**印「必然陈旧」且须声明来源无保障），**且**须真被调用点接线',
    'A52': '写出的时点 × `_ts_offset_ok()`（须带 UTC 偏移）；**两个合成样本方向相反**（naive 必拒 / 带偏移必过），'
           '**且**写入点须真改用 `astimezone()`（F2：本工具自己审偏移而自己漏写偏移）',
    # ★ A53 = HR③「契约违规应在**注册期** fail-fast」的我侧对照物（承接自批准插件缺 output.render）
    'A53': '各注册表**交叉引用**（范围↔极性/依赖/可失败性；强度/无解/死区/`CROSS_DOMAIN`→范围；豁免两表五层+独立性；身份字段）'
           '—— ★本条判的是**我自己注册表之间的内部引用**，**不判他域对象**（故不属跨域断言）'
           '× `_contract_check()`；**默认预检每次操作前跑（注册期 fail-fast，违规 exit 8 不进写路径）**；'
           '**四个合成样本**：删极性登记 / 无解表引用不存在的断言 / 他方·独立不具名 / **网格缺一格** ⇒ 皆必被抓',
}
# ★ 明鉴的可执行建议：**给「极性」也建一张表** —— 未声明极性 ⇒ 标 ★未声明极性★ 并整体判红。
#   出处：他实测「源码 positive_controls 19 + negative_controls 4 = 23，而断言行 24 ⇒ **A8 两边都不在 ⇒ 未归类**」，
#   且卡内**散文极性表**比源码表落后（缺 A19/A20/A21/A22 + A9a 重复）⇒ **规则: 极性表以代码为准, 散文不得再抄一份**。
CONTROL_POLARITY = {
    'A1': '正控', 'A2': '正控', 'A3': '负控', 'A4': '正控', 'A5': '正控', 'A6': '正控',
    'A7': '正控', 'A8': '三态', 'A9a': '正控', 'A9b': '负控', 'A10': '负控',
    'A11': '正控', 'A12': '正控', 'A13a': '正控', 'A13b': '负控', 'A14': '三态',
    'A15': '两极(一条同除两极性)', 'A16': '两极(一条同除两极性)', 'A17': '正控',
    'A18': '两极(一条同除两极性)', 'A19': '正控', 'A20': '两极(一条同除两极性)',
    'A21': '正控', 'A22': '两极(一条同除两极性)', 'A23': '两极(一条同除两极性)',
    'A24': '两极(一条同除两极性)', 'A25': '两极(一条同除两极性)',
    'A26': '两极(一条同除两极性)', 'A27': '两极(一条同除两极性)', 'A28': '正控',
    'A29': '两极(一条同除两极性)', 'A30': '两极(一条同除两极性)', 'A31': '两极(一条同除两极性)', 'A32': '两极(一条同除两极性)', 'A33': '两极(一条同除两极性)', 'A34': '两极(一条同除两极性)', 'A35': '两极(一条同除两极性)', 'A36': '两极(一条同除两极性)', 'A37': '两极(一条同除两极性)', 'A38': '两极(一条同除两极性)', 'A39': '两极(一条同除两极性)', 'A40': '两极(一条同除两极性)', 'A41': '两极(一条同除两极性)', 'A42': '两极(一条同除两极性)', 'A43': '两极(一条同除两极性)', 'A44': '两极(一条同除两极性)', 'A45': '两极(一条同除两极性)', 'A46': '两极(一条同除两极性)', 'A47': '两极(一条同除两极性)', 'A48': '两极(一条同除两极性)', 'A49': '两极(一条同除两极性)', 'A50': '两极(一条同除两极性)', 'A51': '两极(一条同除两极性)', 'A52': '两极(一条同除两极性)', 'A53': '两极(一条同除两极性)',
}
# ★ HR 的结论性补充：「**范围不足可判定，当且仅当存在一个【显式的许可集】**」⇒ 许可集本身必须显式、可读、可核。
#   故把原先**藏在 A21 函数体内**的元组提升为模块级常量，并**分型**（键 / 卡 / 命名空间各自许可）—— 比单一前缀更严且更可读。
PROBE_KEYS = ['data/external-link/_pc-structural-block-20260911', 'data/external-link/_pc-owner-probe-20260911',
              'data/external-link/_pc-bbcopy-src-20260911', 'data/external-link/_pc-bbcopy-dst-20260911',
              'data/external-link/_pc-bbcopy-secret-20260911', 'data/external-link/_pc-bbcopy-docmention-20260911',
              'data/external-link/_pc-bbcopy-cnsecret-20260911', 'data/external-link/_pc-bbcopy-cnconcept-20260911']
TOUCH_ALLOW = {
    'key': {'规则': '本域前缀（A17 需全域名录扫描）', 'value': SELF_DOMAIN},
    'card': {'规则': '仅本卡与心跳卡', 'value': [CARD_KEY, HEARTBEAT_KEY]},
    'ns': {'规则': '仅本域命名空间列举', 'value': SELF_DOMAIN},
}
# ★ 「范围声明 → 显式许可集」的映射：**没有许可集的范围声明 = 不可机械判** ⇒ 由 A29 点名（不判它错，判它「未给许可集」）
SCOPE_ALLOW = {
    'A8': [CARD_KEY], 'A14': [CARD_KEY], 'A15': [CARD_KEY], 'A16': [CARD_KEY, 'file:' + CANONICAL_PATH],
    'A17': [SELF_DOMAIN], 'A21': ['TOUCH_ALLOW'], 'A25': [CARD_KEY], 'A27': [CARD_KEY],
    'A28': ['file:' + CANONICAL_PATH],
}
CONTAINER_SCOPED = ['A8', 'A14', 'A15', 'A16', 'A17', 'A21', 'A25', 'A27', 'A28']
# ★ HR 2026-09-11 采纳并推广：「**判据的依赖项，其自身必须是可检对象**」——否则判据会因依赖项不可见而落空。
#   执行体：每条断言**声明依赖项**（A33 断言覆盖齐）；且 **card_field 类依赖必须真实存在于本卡**（真检查）。
ASSERT_DEPS = {
    'A1': ['file'], 'A2': ['probe'], 'A3': ['probe'], 'A4': ['probe'], 'A5': ['probe'], 'A6': ['probe'],
    'A7': ['file'], 'A8': ['file', 'card_field:语义锚点_不随版本漂'], 'A9a': ['probe'], 'A9b': ['probe'],
    'A10': ['probe'], 'A11': ['probe'], 'A12': ['tmp', 'probe'], 'A13a': ['probe'], 'A13b': ['probe'],
    'A14': ['card'], 'A15': ['card_field:能力边界_样板格式'], 'A16': ['card_field:指纹', 'file', 'ext'],
    'A17': ['ns'], 'A18': ['file', 'ext'], 'A19': ['tmp', 'card_field:指纹'], 'A20': ['file'],
    'A21': ['file', 'ns', 'card'], 'A22': ['hist', 'file'], 'A23': ['file', 'help'], 'A24': ['file'],
    'A25': ['card_field:自测'], 'A26': ['file'], 'A27': ['card_field:ts', 'card_field:ts_epoch'],
    'A28': ['file', 'tmp'], 'A29': ['file'], 'A30': ['file'], 'A31': ['card_field:producer', 'ns'],
    'A32': ['file'],
    # ★ A33 首跑即把「自己」列为未声明依赖（覆盖检查的自指效应）⇒ 补上：它依赖本文件与**本卡整体**
    'A33': ['file', 'card'],
    # ★ A33 又一次点名新断言未声明依赖（覆盖检查的常态）⇒ 补上
    'A34': ['file'],
    'A35': ['file'],
    'A36': ['ns', 'card_field:ts_audit_baseline'],
    'A37': ['card'],
    'A38': ['file'],
    'A39': ['ns'],
    'A40': ['card_field:tool_managed_fields'],
    'A41': ['file'],
    'A42': ['file'],
    'A43': ['file'],
    'A44': ['file'],
    # ★ 阶段2时点 **只在终态必需** —— 用条件依赖表达；无条件声明会在阶段1 与 A45 互斥（实测）。
    'A45': ['card_field:自测', 'card_field:阶段1时点', 'card_field_when_terminal:阶段2时点'],
    'A46': ['file'],
    'A47': ['file'],
    'A48': ['file'],
    'A49': ['file'],
    'A50': ['file'],
    'A51': ['file'],
    'A52': ['file'],
    'A53': ['file'],
}
# ★ HR 的新判据（他自己自记 2 实例后升为判据档）：「**凡发布一个格式/样板，须同时给出执行体或显式声明『此项无执行体』**」。
#   执行体：把**我发布过的每一项**映射到它的执行体断言；`None` = **显式声明无执行体**（可见，不藏）。
PUBLISHED_CONVENTIONS = {
    '范围声明格式（每条断言带〔范围〕）': ['A20'],
    '极性声明表（以代码为准）': ['A26'],
    '数报行（两层六项）': ['A30'],
    '指纹字段（带时点）': ['A16', 'A27'],
    '自测字段（工具写 + 守卫）': ['A25'],
    '写者身份与展示名分离（producer/writer）': ['A31'],
    '声称语法（时点限定 + 两问四态）': ['A18', 'A22'],
    '范围许可集（显式、分型）': ['A21', 'A29'],
    '断言依赖声明': ['A33'],
    '静态文本不得含会变值': ['A32'],
    '入口可发现（定义/提供/使用）': ['A23'],
    '自锁死形状签名禁令': ['A31'],
    '三种传递形态（①整值复制 ②字段名引用 ③部分值复制不支持）': ['A1'],
    # ★ HR 2026-09-11 裁定五步并**撤回四步**（反例：恒假判据能过四步）⇒ 本项**已配执行体 A35**
    '对照链五步表述（分离操作数/正控/负控/独立复跑/入口可发现）': ['A35'],
}

# ★ HR 裁定（2026-09-11）：**五步** —— ①分离操作数 ②样本真违规=正控 ③样本真合规=负控 ④独立实现复跑 ⑤入口可发现。
#   其反例：**恒假判据（永远报警）能过 ①②④⑤** ⇒ 四步漏的正是另一极。⇒ 本表把五步映射到**本工具自己的对照集**。
FIVE_STEPS = [
    ('① 分离操作数', 'tags', ['A16', 'A18']),
    ('② 样本真违规=正控', 'polarity', '正控'),
    ('③ 样本真合规=负控', 'polarity', '负控'),
    ('④ 独立实现复跑', 'tags', ['A16']),
    ('⑤ 入口可发现', 'tags', ['A23']),
]
# ★ 明鉴④的一般形式：「**两条主张『合起来覆盖卡内文本』的断言，合起来恰好漏掉它**（覆盖面的并 ≠ 声称的并集）」。
#   他的实例：A37 只登记 5 组枚举（不含「断言编号集」）、A32 又豁免「工具管理字段」（自测正是其一）
#   ⇒ 两条合起来正好漏掉自测串里的编号范围。
#   ⇒ 执行体：**凡被豁免（tool_managed）的字段，必须由另一条判据接手**；无人接手即点名。
# ★ HR 2026-09-22 **准予升格**为通则，名词改为「**排除即转交**」（「豁免」暗示无需处理；「转交」才引得出那句问话）。
#   他补四条，本表按此结构登记：① **接手方须三层可核**（接手方·检查动作·检出读数）② **排除须改分母并单独计数**
#   ③ **接手方同源须声明「自接手·独立性缺失」** ④ 该条在他域也自查出两例（收敛表 5 数 · 队列 105 畸形地址）。
TOOL_MANAGED_COVERED = {
    'ts': {'接手方': 'A27', '检查动作': '卡内 ts 四判据（可解析/带偏移/与 epoch 一致/不指向未来）', '检出读数': 'A27 本行判定串', '同源': True, '单独计数': 'A36 报「存量/政策后命中」数'},
    'ts_epoch': {'接手方': 'A27', '检查动作': '与 ts 互校', '检出读数': 'A27 本行判定串', '同源': True, '单独计数': 'A36 报数'},
    '自测': {'接手方': 'A25 + A38', '检查动作': 'A25 比计数/版本；A38 比编号范围；A45 比阶段标记', '检出读数': 'A25/A38/A45 各本行', '同源': True, '单独计数': 'A25 报「实得 N 项」'},
    '指纹': {'接手方': 'A16', '检查动作': '与本文件及**独立实现**三方比对', '检出读数': 'A16 本行「一致/过期维」', '同源': True, '单独计数': 'A16 报逐维比对结果'},
    'version': {'接手方': 'A16', '检查动作': '与实测版本比对', '检出读数': 'A16 本行', '同源': True, '单独计数': 'A16 报逐维结果'},
    'writer': {'接手方': 'A31', '检查动作': '字段存在性 + 身份分离', '检出读数': 'A31 本行 writer 值', '同源': True, '单独计数': 'A31 报自有/他人分层覆盖率'},
    'path': {'接手方': 'A16', '检查动作': '与实测路径比对', '检出读数': 'A16 本行', '同源': True, '单独计数': 'A16 报逐维结果'},
    'artifact_path': {'接手方': 'A28', '检查动作': 'realpath 与规范路径比对', '检出读数': 'A28 本行（副本 stamp 必被拒）', '同源': True, '单独计数': 'A28 报历史深度变化'},
    '指纹历史': {'接手方': 'A22', '检查动作': '据此判「过期的真/不可核」', '检出读数': 'A22 四态判定', '同源': True, '单独计数': 'A22 报历史深度不足时的 skipped'},
    'ts_audit_baseline': {'接手方': 'A36', '检查动作': '棘轮比较（只准降）', '检出读数': 'A36 本行存量数 vs 基线', '同源': True, '单独计数': 'A36 报自有存量/他人存量分层数'},
    'writer_coverage_baseline': {'接手方': 'A31', '检查动作': '棘轮比较（只准升）', '检出读数': 'A31 分层覆盖率', '同源': True, '单独计数': 'A31 报自有/整体两个覆盖数'},
}
# ★ HR④：探针接手方与 A40 同源 ⇒ 标「自接手·独立性缺失」（**定义须在本表之前**，
#   否则 FORM_EXEMPTIONS 引用时该名字还不存在 —— 这是同型顺序错第 4 次）。
PROBE_TAKERS_INDEPENDENCE = '自接手·独立性缺失（接手方即本工具自己的 8 条断言，与 A40 的接手方**同源**）'
# ★ 另一类「排除」：**形态豁免**（不是字段豁免）——同样必须给出接手方三层
FORM_EXEMPTIONS = {
    '带 ISO 时点的历史计数': {'接手方': '时点政策', '检查动作': 'A36（政策后命中须为 0）+ A27（卡内 ts 校验）',
                              '检出读数': 'A36 政策后命中数 · A27 判定串', '同源': True,
                              '单独计数': 'A32 报「违规 N / 放行 M（带时点）」两数'},
    # ★ HR④（裁定）：这 8 个接手方与 A40 一样属**同源** ⇒ 须标「自接手·独立性缺失」（不靠缺省注入）
    '_pc-* 控制探针键（域扫描排除）': {'接手方': '使用它们的断言（A2/A3/A5/A6/A12/A13a/A19/A28）',
                                        '检查动作': '这些断言直接以探针键为主体', '检出读数': '各断言本行（探针键内容被逐条断言）',
                                        '同源': True, '单独计数': '各域扫描报「另排除探针 N 键」',
                                        '独立性': PROBE_TAKERS_INDEPENDENCE},
    # ★ HR② 裁定：**上限截断的接手方 = 下一轮的补扫动作** ⇒ 由「无人接手」升为**合格转交**。
    '扫描上限之外未扫的键': {'接手方': '**增量补扫**（`_scan_domain()` 分页取全量）',
                              '检查动作': '把「未扫 N」作为下一轮输入、每轮多扫一页直到未扫=0（HR②）',
                              '检出读数': '各扫描本行「已扫 X / 共 Y · 另排除 E · 未扫 N」+ 三档判定',
                              '同源': True, '单独计数': '未扫数 N **与**排除数 E 分列（通则第②条）',
                              '独立性': '自接手·独立性缺失'},
}
# ★ HR④ 裁定：**接手（有人）与独立（他人）是两层** ⇒ 登记须**两栏**：`接手方` / `独立性`；
#   取值为 `自接手·独立性缺失` 或 `他方·独立（**须具名**）`。
#   为免逐条漏写（漏写会让「独立性」形同虚设），缺省由本循环**注入**，需要他方独立者**显式覆盖**。
for _tbl in (TOOL_MANAGED_COVERED, FORM_EXEMPTIONS):
    for _n, _e in _tbl.items():
        if isinstance(_e, dict):
            _e.setdefault('独立性', '自接手·独立性缺失')
# 他方·独立（**具名**）：确有第三方工具在核这些对象的清单
INDEPENDENT_TAKERS = {
    '指纹': '他方·独立（守灯 replica-consistency-check.py 跨副本核 · 明鉴 bb-put-both 四比）',
    'version': '他方·独立（守灯 replica-consistency-check.py 跨副本核）',
}
for _n, _v in INDEPENDENT_TAKERS.items():
    if _n in TOOL_MANAGED_COVERED:
        TOOL_MANAGED_COVERED[_n]['独立性'] = _v
DEP_KINDS = {'card_field_when_terminal': '卡内字段（**仅终态必需**；阶段1 记「尚未必需」第三态）',
             'file': '本文件（存在性可检）', 'card': '本卡整体（可读）', 'probe': '探针键（域内可检）',
             'ns': '本域命名空间（可列举）', 'ext': '独立实现 md5/stat', 'hist': '指纹历史（卡内可读）',
             'help': '子进程 --help 输出', 'tmp': '/tmp 副本'}
# ★ 明鉴②（元讨论污染）：**判据的作用域若包含「关于判据自身的材料」，必须显式排除**。
# ★ 明鉴③归纳的**三解法**（适用条件不同）：① 约定表（材料是别人的，我改不了）· ② 单用途位置（材料是我写的，但内容不该动）·
#   ③ **改造材料本身**（材料是我写的，且改它不影响用途 —— 最彻底，让冲突不存在）。判据：问「这份材料是谁的？我能改它吗？」
SOLUTION_CLASSES = {'① 约定表': '材料是别人的（我改不了）', '② 单用途位置': '材料是我写的但内容不该动', '③ 改造材料本身': '材料是我写的且改它不影响用途'}
TEXT_SCANNING_EXCLUSIONS = {
    'A23': '① 约定表：排除注释/散文与比较上下文（**提及 ≠ 提供 ≠ 使用**）',
    'A32': '① 约定表：ISO 时点豁免（历史快照合法）+ 声明的工具管理字段豁免',
    'A37': '① 约定表：只比对**枚举成员名**是否出现在卡内（卡内讨论该枚举属预期）',
    'A38': '② 单用途位置：**只查真实生成路径**（卡内自测串），**不扫全源码** —— 合成样本里故意写错的范围是判据的一部分',
    'A43': '② 单用途位置：本条只检查**登记表是否完整**，不看正文语义',
    # ★ A48 的范围文本含「文本」⇒ 按 A43 须登记排除方式（本轮新增：域/人区分）
    'A48': '② 单用途位置：只查**范围文本里的域词**，且先剥掉「指人」搭配（`CD_PERSON_PHRASES`）'
           '⇒ **同一批字在两种用法下被分开**，不误判「接手有人/独立他人」',
    # ★ A43 首跑点名这 4 条（范围文本含「文本」却未登记排除方式）⇒ 逐条补，且说明**它们如何处理「关于判据自身的材料」**
    'A6': '② 单用途位置：扫**子进程输出文本**找哨兵是否泄漏；不外扫制品文本（哨兵自造，无元讨论材料）',
    'A7': '② 单用途位置：只取**声明位那一行的字面量**（VERSION 常量赋值行的引号内内容），**不读散文/注释** ⇒ 讨论该规则的材料不会命中',
    'A14': '③ 改造材料本身（**三解法里最彻底**）：元讨论材料真实存在（卡内讨论过行号锚点）⇒ 处置不是豁免，而是**把卡内反例也改写成合规形式** ⇒ **让冲突不存在**（属结构层）',
    'A30': '② 单用途位置：只扫**本次运行生成的数报行**（工具产出），不扫制品文本',
}
# ★ A48 的文本探测须区分【域】与【人】（元讨论污染新实例，实测于 A40）：
#   裸词「他人」被当作跨域代理，而「接手有人 / **独立他人**是两层」里的「他人」指**检查者身份**，不是另一个域。
#   ⇒ 只排除「检查者身份」那类搭配（② 单用途位置），**不删词** ⇒ 真正的「他人卡 / 他人域」照旧被抓。
CD_PERSON_PHRASES = ('独立他人', '他方·独立', '他方', '接手有人')


# ★ 否定语境（第 3 次同形污染后升为一般处理）：A53 的范围文本**声明自己「不判他域对象」**，
#   而那句声明里**又出现了那个词** ⇒ 判据把自己的**排除说明**当成了命中。
#   （前两例：A40 的「独立他人」指人 · 本条的排除说明自指）⇒ 判据：**先剥否定语境，再查词**。
CD_NEGATION_RE = re.compile(r'[（(][^）)]*(?:不判|不属|排除|不涉|无关)[^）)]*[）)]|[^；;。\n]*(?:不判|不属|不涉)[^；;。\n]*')


def _cd_texty(scope_text):
    """范围文本是否指向**跨域对象**。三步（单用途位置：同一批字在不同用法下被分开）：
      ① 剥掉「指人」搭配（如「独立他人」= 检查者身份）
      ② 剥掉**否定语境**（如「不判他域对象」= 排除说明，不是命中）
      ③ 再查「指域」的词
    ⇒ 探测力不减（合成「他人卡…」仍必命中）。返回 bool。"""
    t = str(scope_text or '')
    for p in CD_PERSON_PHRASES:
        t = t.replace(p, '')
    t = CD_NEGATION_RE.sub('', t)
    return any(k in t for k in ('本域', '他人', '跨域'))


# ★ 明鉴①：「**声明条件的实现永不触发**」= 空检查的变体（检查体非空，但**前提永不成立** ⇒ 永不变红）。
#   判据：**问「这条判据有可能变红吗？」** ⇒ 执行体：**每条断言须声明如何能让它变红**（合成样本 / 反向校验）。
FALSIFIABILITY = {
    'A1': '合成：传 `--body` ⇒ argparse 拒绝(exit2)', 'A2': '合成：人为改 dst 值 ⇒ 逐字段比对必不等',
    'A3': '合成：把 dst 造成重建形态 ⇒ 必判不等(exit4)', 'A4': '合成：查不存在的键 ⇒ unknown(3)',
    'A5': '合成：含 api_token 的探针 ⇒ 必拒(exit7)', 'A6': '合成：哨兵必现的输入 ⇒ 输出含哨兵即判红',
    'A7': '**反向校验**：插重复声明行 ⇒ 判红(实测过)', 'A8': '**反向校验**：改名 `def cmd_refcheck` ⇒ 判红(实测过)',
    'A9a': '合成：不存在的字段名 ⇒ 必报缺(exit4)', 'A9b': '合成：存在的字段名 ⇒ 报缺即判红',
    'A10': '合成：提及凭据的文档字段 ⇒ 被硬拒即判红', 'A11': '合成：把 `--to` 改回 local ⇒ 两侧回读必缺一侧',
    'A12': '**反向校验**：破坏常量 ⇒ 预检拦下(实测过)', 'A13a': '合成：主密钥 ⇒ 不拒即判红', 'A13b': '合成：令牌桶算法 ⇒ 被拒即判红',
    'A14': '合成：卡内写行号式引用 ⇒ 必判红', 'A15': '合成：残缺能力边界 ⇒ 必判不合格',
    'A16': '合成：过期指纹(md5=deadbeef) ⇒ 必被判过期', 'A17': '合成：把某自有卡字段名改为 token ⇒ 误拦面必 >0',
    'A18': '合成：错 md5 / 缺时点 ⇒ 必拒', 'A19': '合成：/tmp 副本 ⇒ 必拒(exit8)',
    'A20': '合成：未登记标签 ⇒ 必判缺失', 'A21': '**反向校验**：注入越界读 ⇒ 报越界(实测过)',
    'A22': '合成：历史深度不足 ⇒ skipped 而非 pass', 'A23': '合成：假旗标 ⇒ 必被判 missing',
    'A24': '合成：超阈/不可解析 ⇒ 必 stale(3)', 'A25': '合成：999 项/v0.0.1 的过期串 ⇒ 必判不平',
    'A26': '合成：删掉某标签极性登记 ⇒ 必判红', 'A27': '合成：无偏移/指向未来 ⇒ 必不平',
    'A28': '合成：/tmp 副本 stamp ⇒ 必拒且历史不变', 'A29': '合成：A99 未配许可集 ⇒ 必被点名',
    'A30': '合成：只给四项 ⇒ 必判缺', 'A31': '合成：「名字 (后缀)」producer ⇒ 必判会被拦',
    'A32': '合成：无时点计数必违规 / 带时点必放行',
    'A33': '**三个合成样本**：删卡内 `自测` ⇒ 必被点名 · **终态缺 `阶段2时点`** ⇒ 必被点名 · **终态带 `阶段2时点`** ⇒ 必不被点名（两极；防条件依赖恒真）',
    'A34': '合成：指向 A99 ⇒ 必被判无执行体', 'A35': '合成：极性表无负控 ⇒ 必报落空',
    'A36': '合成：政策后有命中 / 破 ratchet ⇒ 必拒', 'A37': '合成：不存在的枚举成员 ⇒ 必被判缺',
    'A38': '合成：A1–A99 ⇒ 必判不一致', 'A39': '合成：政策后+无 writer ⇒ 必被判命中',
    'A40': '**三个合成样本**：无人接手的字段 ⇒ 必被点名 · 独立性写「他方」而不具名 ⇒ 必判坏 · '
            '「他方·独立（守灯某工具）」⇒ 必判好',
    'A41': '**两个合成样本**：plist 周期≠常量 ⇒ 必判红；系数不写成导出式（写成独立常量）⇒ 必判红',
    'A42': '**反例实现**：`_str_order_max` ⇒ 必得 A9b（错误值）', 'A43': '合成：未登记解法类别的断言 ⇒ 必被点名',
    'A44': '合成：源码含现值字面量 / 非法字节 ⇒ 必判红',
    'A45': '**三个合成样本**：①阶段1 与终态不可区分 ②**去掉时间维**（入口时点为空）③**终态缺冻结量**'
           '（终态而无 `阶段2时点`）⇒ 三者皆必判红',
        'A46': '**反向校验（合成样本方向相反）**：从注册表移除一条 ⇒ 必须被点名（实测移除后必被检出）；并分行报「样本/反向/仅说明」数',
    'A47': '合成：把某条强度档写成非法值 ⇒ 必被点名（格式校验可触发）',
    'A48': '**三个合成样本**：合成「他人卡…」未登记 ⇒ 必被点名；合成「独立他人」（指人非指域）⇒ 必**不**误判；'
           '合成「排除说明自指」（否定语境里出现该词）⇒ 必**不**误判',
    'A48': '合成：把某条跨域断言从 CROSS_DOMAIN 移除 ⇒ 必被点名（清单<总数可触发）',
    'A49': '**两个方向**：合成「第三方」无主体无时点 ⇒ 必拒；合成「第三方 HR 2026-09-22」⇒ 必过',
    'A50': '**两个合成样本**：空输出 ⇒ 必判不合格；有键无值 ⇒ 必判不合格',
    'A51': '**两个合成样本（方向相反）**：未装载+已陈旧 ⇒ 必印「恒真·无信息」；未装载+仍新鲜 ⇒ 必**不**印「必然陈旧」'
           '且须声明「来源无保障」；再以断接线做反向校验（调用点改名则必红）',
    'A52': '**两个合成样本（方向相反）**：naive 时点 ⇒ 必拒；带偏移时点 ⇒ 必过；再核写入点是否真用 `astimezone()`',
    'A53': '**四个合成样本**：删一条极性登记 ⇒ 必被抓 · 「无解」表引用不存在的断言 ⇒ 必被抓 · '
           '「他方·独立」写成不具名 ⇒ 必被抓 · **网格缺一格** ⇒ 必被判缺格（证明 fail-fast 不是空话）',
}
# ★ HR②：**判据强度阶梯 = 内容（可伪造）< 结构位置 < 凭据 < 通道** —— 只有后两级对**故意者**有效。
#   本表登记本工具每条**堵/拦**类机制的强度档与「对故意者是否有效」。★ 诚实：本域**无一条达到凭据/通道档**。
STRENGTH_LADDER = {'内容（可伪造）': 1, '结构位置': 2, '凭据': 3, '通道': 4}
STRENGTH = {
    'A1': ('结构位置', False, '接口无自由文本 ⇒ 重建不可表达（对故意者也需改代码，非改数据；但**仍可改** ⇒ 未达凭据/通道）'),
    'A5': ('内容（可伪造）', False, '默认硬拒可被 `--allow-secret-fields` 越过 ⇒ 对故意者无效'),
    'A11': ('结构位置', False, '改默认值：单写须显式声明（故意者仍可显式单写）'),
    'A12': ('结构位置', False, '预检拦下（故意者可 `--no-preflight` 越过）'),
    'A19': ('结构位置', False, '声称门禁：卡不同步即拒生成（故意者可 `--no-preflight` 越过）'),
    'A28': ('结构位置', False, '副本 stamp 拒绝：以**源码内常量**比对（故意者可改副本里的常量）'),
    'A39': ('内容（可伪造）', False, '**线索**：拦得住疏忽写入，拦不住故意填 writer ⇒ **本题无解**（真正的写入通道不可观测）'),
    'A16/A22/A25/A27/A31/A36/A38/A40/A41/A43/A44/A45/A46': ('内容（可伪造）', False, '检测类：**只对被检内容生效，内容本身可伪造** ⇒ 对**故意者无解**（不得用它们冒充「防住」）'),
}
# ★ HR 2026-09-22 裁定⑤（由我那句自陈升格为规则）：**无解时须明写无解，不得用弱机制冒充防住**
#   ⇒ 执行体：凡**已知无解**的堵/拦机制在此登记；A47 断言其档位**不得 ≥3**，且说明里须出现「无解 / 无效」字样。
NO_SOLUTION = {
    'A39': '绕过统一入口的写入**无解**：真正的写入通道不可观测 ⇒ 本判据只是**代理**（内容可伪造）',
    'A16/A22/A25/A27/A31/A36/A38/A40/A41/A43/A44/A45/A46': '检测类机制对**故意者无解**：判据读的是内容，内容本身可伪造',
}
# ★ HR 2026-09-22 裁定④（一般条，本轮增量）：**凡以【自报字段】为证据的判据，都属同一个死区**
#   —— 自报不是独立通道证据 ⇒ 不必每条各自声明，**在域级声明里合并统计**。
SELF_REPORT_DEAD_ZONE = {
    'A39': '绕过代理：证据是卡内 `writer` **自报**',
    'A31': 'writer 覆盖率：分子是卡内 `writer` **自报**',
    'A16': '指纹登记：数值由**工具自报**',
    'A47': '强度档登记：档位由**工具自报**',
}
# ★ HR 2026-09-22 裁定①②的**域级强度声明**（单一来源：A47 据此核并报出）
STRENGTH_DOMAIN_DECL = {
    '分布': '各档条数（见 A47 本行报数）',
    '对故意者无效': '本域最高档 < 3（无凭据/通道档）**且本域存在需防故意者的判据** ⇒ **本域对故意者无效**',
    '自报字段死区': '以自报字段为证据的判据**合并统计**（见 A47 本行）',
}
# ★ HR③ 升为跨域通则：**跨域判据须先声明各域的对应字段名**，否则在某些域**恒不触发**（与恒真报警对称，同为无信息）。
# ★ HR 2026-09-22 裁定②：两处是**跨域镜像**（我的执行用表 ↔ HR 的登记用台账）⇒ 须指定权威源，
#   否则同一事实两份会各自漂移。
IDENTITY_AUTHORITY = {
    '执行用': 'IDENTITY_FIELDS（本表）',
    '登记用': 'HR 域台账（data/registry/thread-convergence-table-20260911 相关栏）',
    '权威裁定': '**不一致时以【对该域键的实测】为准**（既不信表也不信台账）',
    '镜像标注': '本表**镜像自 HR 台账**；HR 侧台账请其自行标注镜像自本表 —— 两处各标一处，避免两份都沉默',
}
# ★ 实测优先的执行体：从真实键上数出该域**实际**用哪个身份字段（不猜、不碰运气）
def _identity_field_measured(keys, getter):
    """实测该域身份字段：返回 (dominant|None, 计数 dict)。只数不改判 —— 用于与执行用表对账。"""
    cnt = {}
    for k in keys:
        st, v = getter('local', k)
        if st != 200 or not isinstance(v, dict):
            continue
        got = [f for f in ('producer', 'from') if str(v.get(f) or '').strip()]
        if not got:
            cnt['(无)'] = cnt.get('(无)', 0) + 1
        for f in got:
            cnt[f] = cnt.get(f, 0) + 1
    if not cnt:
        return None, cnt
    return max(cnt.items(), key=lambda kv: kv[1])[0], cnt


IDENTITY_FIELDS = {
    'data/external-link/': ('producer', 'from'),   # 两者并用（实测 14 / 15）
    'notes/': ('from',),                            # 实测 38/40 用 from
    'data/registry/': ('from',),                    # 实测 27/40 用 from；producer 仅 1
}
STOCK_HITS = {}          # ★ HR④：新判据落地前须做【存量回放】并报存量命中数（>0 须给处置）
# ★ HR 2026-09-22 裁定③：回放行**须带分母**（回放了多少个存量对象）——
#   否则「0」与「**没回放**」同形。与合成阳性对照**作用不同**：合成对照防「跑不到」，分母防「静默不跑」。
STOCK_DENOM = {}
STRENGTH_DIST = {}     # ★ HR①：各档条数分布（域级强度声明的一部分）
IDENTITY_MEASURED = (None, {})   # ★ HR②：该域身份字段的**实测**（与执行用表对账；冲突时以实测为准）
# ★ HR① 升为**网络级约定**：**跨域对象只报不判** ⇒ 且自律须配【**可对账的计数**】：
#   输出报「**他人对象命中 N · 已判 0**」⇒ 使违约可被第三方发现（**自律若无见证只是声称**）。
# ★ HR③ 档位须声明为三元组：**（工具 × 对象域 × 档）** —— 自有卡「判红」、他人卡「只报」**可并存**。
CROSS_DOMAIN = {
    'A17': {'data/external-link/（自有卡）': ('判红', '误拦面 >0 即红'), 'data/external-link/（他人卡）': ('只报', '命中计入他人数，不判')},
    'A31': {'data/external-link/（自有卡）': ('判红', '形状签名 >0 即红'), 'data/external-link/（他人卡）': ('只报', '他人形状命中只列不判')},
    'A36': {'data/external-link/（自有卡）': ('判红', '棘轮只计自有'), 'data/external-link/（他人卡）': ('只报', '他人存量只列不计')},
    'A39': {'data/external-link/（自有卡）': ('线索·判红', '代理命中即红'), 'data/external-link/（他人卡）': ('只报', '他人不判')},
    # ★ A48 首跑点名这 3 条：它们的范围文本提到「他人」，但**真实情形是声明「不覆盖他人对象」**
    #   ⇒ 应**显式登记为「不适用」**（登记而非漏登）——这正是「清单==子集」的意义：**边界声明也要在册**。
    'A1': {'—': ('不适用', '声明：本工具 CLI 不可表达性；**不覆盖他人工具**（无跨域对象）')},
    'A21': {'—': ('不适用', '声明：仅本进程内读取；**不覆盖**子进程写入与他人工具（无跨域对象）')},
    'A48': {'—': ('不适用', '本条只读**本文件源码**做清单完备性核对（无跨域对象）')},
}
PROBE_TAKERS = 'A2/A3/A5/A6/A12/A13a/A19/A28'   # ★ HR④：被排除的探针键须声明**接手方**（排除即转交）
# ★ HR 2026-09-22 裁定④：探针接手方与 A40 一样是**自接手** ⇒ 须标「自接手·独立性缺失」（不靠缺省注入）
# ★ HR 2026-09-22 裁定③：**「不适用」必须是显式取值，不能靠「没登记」表达** ——
#   否则清单完备性会因**漏登边界声明**而假通过。
#   ⇒ 先声明**对象域宇宙**（否则「哪些格存在」本身没定义，缺格也就无从发现），再要求每格显式取值。
CROSS_DOMAINS = ('data/external-link/（自有卡）', 'data/external-link/（他人卡）')
CROSS_LANES = ('判红', '只报', '线索', '不适用')
# ★ HR 2026-09-22 裁定⑥：**新检查器上线后须报【它抓到的首例】** ——
#   零命中无法区分「对象干净」与「检查器沉默」；首例是它有效的证据。格式：(首例, 时点, 证据)。
FIRST_CATCH = {
    'A48': ('A40 范围文本因「独立他人」被判涉跨域未登记（3 条边界声明被点名）', '2026-09-22', 'A48 首跑报 unreg=3'),
    'A51': ('心跳未装载分支写死「必然陈旧」，而同屏读数 age=0s（自相矛盾输出）', '2026-09-22', '--heartbeat-age 实测'),
    'A52': ('本工具自己审时点偏移、自己的写入点却写 naive ts（落盘无偏移）', '2026-09-22', '心跳卡 ts 修前/修后对照'),
    'A53': ('强度表/无解表用复合键引用了不存在的断言 + 分布按条目数导致档1 低估 12', '2026-09-22', 'A53 首跑报真表违约'),
}
NEW_CHECKERS = ('A48', 'A51', 'A52', 'A53')


def _cross_cell_check(cross=None, domains=None):
    """★ HR③ 的执行体：**网格须先声明，每格须显式取值**（`不适用` 也是取值）。
    返回 (缺格列表, 四类档计数 dict, 总格数)。缺格非空 ⇒ 清单完备性不成立（不是「通过」）。"""
    cross = CROSS_DOMAIN if cross is None else cross
    domains = CROSS_DOMAINS if domains is None else domains
    miss, cnt, cells = [], {k: 0 for k in CROSS_LANES}, 0
    for t, spec in cross.items():
        inapp = any(str(lane).find('不适用') >= 0 for lane, _w in spec.values())
        if not inapp:
            for d in domains:
                if d not in spec:
                    miss.append(t + '×' + d)
        for lane, _w in spec.values():
            cells += 1
            for k in CROSS_LANES:
                if k == '判红' and str(lane).find('判红') >= 0:
                    cnt[k] += 1
                elif k != '判红' and str(lane).find(k) >= 0:
                    cnt[k] += 1
    return miss, cnt, cells
_MISSING_SCOPE = []


def _annotate_line(line):
    """给断言行追加**范围声明**；未声明 ⇒ 标注并记入缺失。返回 (新行, 缺失标签或 None)。"""
    m = re.match(r'^  (OK|X|-)  (A\d+[a-z]?)\b', line)
    if not m:
        return line, None
    tag = m.group(2)
    sc = ASSERT_SCOPE.get(tag)
    if not sc:
        return line + '  〔★未声明范围★〕', tag
    return line + '  〔范围: ' + sc + '〕', None


def selfcheck():
    """★ 包装层：把「范围声明」做成**结构性强制** —— 任何断言行若未在 ASSERT_SCOPE 里声明范围，
    追加 ★未声明范围★ 并使整体判红。出处：HR「把不可用条件写进输出」。"""
    global print
    _real = print

    def _p(*a, **k):
        line = ' '.join(str(x) for x in a)
        line, miss = _annotate_line(line)
        if miss:
            _MISSING_SCOPE.append(miss)
        _real(line, **k)

    del _MISSING_SCOPE[:]
    print = _p
    try:
        st = _selfcheck_impl()
    finally:
        print = _real
    if _MISSING_SCOPE:
        _real('[check] X 以下断言未声明范围: ' + ','.join(sorted(set(_MISSING_SCOPE))))
        return 1
    return st


def _selfcheck_impl():
    """真跑正反控（不造假通过；任一断言失败即 FAIL）。"""
    print('[check] bb-copy v' + VERSION + ' 阳性对照 + 阴性对照')
    # ★ HR③：「**第三方实测不能自封**」⇒ 凡称「已实测」须标注**谁测的**。
    #   本行为**自测归属标注**：本报告的全部实测由本会话自跑 ⇒ **非第三方**；第三方实测须另行标注。
    print(_attribution_line())
    ok_all = True
    probe_src = 'data/external-link/_pc-bbcopy-src-20260911'
    probe_dst = 'data/external-link/_pc-bbcopy-dst-20260911'
    seed = json.dumps({'producer': 'bb-copy-check', 'subject': '源键种子', 'ts': '2026-09-11',
                       'v': 1, 'answers': [1, 2, 3], 'note': '原样值'}, ensure_ascii=False)
    probe_seed_value = lambda: json.loads(seed)

    # A1 正控：重建路径在接口上不存在（传 --body 必须被拒）
    rc, out = _run(['python3', os.path.abspath(__file__), 'copy', probe_src, probe_dst, '--body', '重建'])
    a1 = (rc == 2 and 'unrecognized arguments' in out)
    print('  ' + ('OK' if a1 else 'X') + '  A1 自由文本参数不可表达(重建路径不存在) exit=' + str(rc))
    ok_all &= a1

    # A2 正控：真复制一次，须逐字段相等
    _run(['python3', BB_WRITE, 'put', probe_src, '--json', seed, '--from', 'bb-copy-check', '--server', 'local'])
    _run(['python3', BB_WRITE, 'put', probe_src, '--json', seed, '--from', 'bb-copy-check', '--server', 'central'])
    rc, out = _run(['python3', os.path.abspath(__file__), 'copy', probe_src, probe_dst,
                    '--src-server', 'local', '--to', 'local', '--from', 'bb-copy-check'])
    a2 = (rc == 0 and '逐字段相等' in out)
    print('  ' + ('OK' if a2 else 'X') + '  A2 原样复制后 dst==src 逐字段相等 exit=' + str(rc))
    ok_all &= a2

    # A3 阴性对照：人为把 dst 造成重建形态 ⇒ 比较器必须报不等（证明 A2 不是空通过）
    _run(['python3', BB_WRITE, 'put', probe_dst, '--body', '重建文本', '--from', 'bb-copy-check',
          '--server', 'local', '--force'])
    rc, out = _run(['python3', os.path.abspath(__file__), 'verify', probe_src, probe_dst,
                    '--src-server', 'local', '--to', 'local'])
    a3 = (rc == 4 and '差异' in out)
    print('  ' + ('OK' if a3 else 'X') + '  A3 阴性对照: 重建形态 dst 被判不等 exit=' + str(rc))
    ok_all &= a3

    # A4 正控：源键不存在 ⇒ unknown(3)，不并入一致
    rc, out = _run(['python3', os.path.abspath(__file__), 'verify',
                    'data/external-link/_pc-bbcopy-absent-20260911', probe_dst, '--to', 'local'])
    a4 = (rc == 3)
    print('  ' + ('OK' if a4 else 'X') + '  A4 源不存在 ⇒ unknown(3) 独立成项 exit=' + str(rc))
    ok_all &= a4

    # A5 正控：敏感字段硬拒必须真拒（默认不得复制凭据类键）
    probe_sec = 'data/external-link/_pc-bbcopy-secret-20260911'
    canary = 'CANARY-NOT-A-REAL-SECRET'
    _run(['python3', BB_WRITE, 'put', probe_sec,
          '--json', json.dumps({'producer': 'bb-copy-check', 'api_token': canary, 'note': 'x'}, ensure_ascii=False),
          '--from', 'bb-copy-check', '--server', 'local', '--force'])
    rc, out = _run(['python3', os.path.abspath(__file__), 'copy', probe_sec, probe_dst,
                    '--to', 'local', '--from', 'bb-copy-check'])
    a5 = (rc == 7 and '硬拒' in out)
    print('  ' + ('OK' if a5 else 'X') + '  A5 敏感字段默认硬拒(exit 7) exit=' + str(rc))
    ok_all &= a5

    # A6 正控(脱敏)：明示越权后须成功，且输出中不得出现敏感值原文
    rc, out = _run(['python3', os.path.abspath(__file__), 'copy', probe_sec, probe_dst,
                    '--to', 'local', '--from', 'bb-copy-check', '--allow-secret-fields'])
    a6 = (rc == 0 and canary not in out)
    print('  ' + ('OK' if a6 else 'X') + '  A6 越权后可复制且输出脱敏(不含敏感值原文) exit=' + str(rc))
    ok_all &= a6

    # A7 正控(自指)：版本声明位唯一且等于 VERSION（防 docstring/常量漂移；同类缺陷 bb-write 曾以 ok5 断言）
    _decl = []
    try:
        _src = open(os.path.abspath(__file__), encoding='utf-8').read()
        _decl = re.findall(r"^VERSION = '([^']+)'", _src, re.M)
        a7 = (_decl == [VERSION])
    except Exception:
        a7 = False
    print('  ' + ('OK' if a7 else 'X') + '  A7 版本声明位唯一且==VERSION(实得 ' + str(_decl) + ')')
    ok_all &= a7

    # A8 正控(跨产物, 三态)：登记卡声明的**语义锚点**必须在源码中可解析
    #   —— 行号会静默指错，语义标识不会；卡不可达 ⇒ skipped，**不冒充通过**
    a8, _d8 = _anchors_ok()
    print('  ' + ('OK' if a8 is True else ('-' if a8 == 'skipped' else 'X')) + '  A8 卡内语义锚点在源码可解析: ' + _d8)
    ok_all &= (a8 is not False)

    # A9 引用核对：a=正控(不存在的字段名必须被报缺) b=负控(存在的字段名必须不被报缺)
    rc, out = _run(['python3', os.path.abspath(__file__), 'refcheck', probe_src,
                    'note', 'no_such_field_xyz', '--src-server', 'local'])
    a9a = (rc == 4 and 'no_such_field_xyz' in out)
    print('  ' + ('OK' if a9a else 'X') + '  A9a 引用核对-正控: 不存在字段必须报缺 exit=' + str(rc))
    ok_all &= a9a
    rc, out = _run(['python3', os.path.abspath(__file__), 'refcheck', probe_src,
                    'note', 'answers', '--src-server', 'local'])
    a9b = (rc == 0 and '缺失=0' in out)
    print('  ' + ('OK' if a9b else 'X') + '  A9b 引用核对-负控: 存在字段不得报缺 exit=' + str(rc))
    ok_all &= a9b

    # A10 负控：**字段名提到凭据词但非凭据形**的文档键不得被硬拒（抓「恒假/永远报警」）
    #   —— 由自捕获触发：用 refcheck 核本工具自己的登记卡时，字段「敏感硬拒.键名疑似凭据类」
    #      因含「凭据」二字被硬拒命中 ⇒ 假阳性 ⇒ 拆两档后必须不再误拦。
    probe_doc = 'data/external-link/_pc-bbcopy-docmention-20260911'
    _run(['python3', BB_WRITE, 'put', probe_doc,
          '--json', json.dumps({'producer': 'bb-copy-check', '凭据纪律': '只写不读，不打印值',
                                '键名疑似凭据类仅告警': 'x'}, ensure_ascii=False),
          '--from', 'bb-copy-check', '--server', 'local', '--force'])
    rc, out = _run(['python3', os.path.abspath(__file__), 'copy', probe_doc, probe_dst,
                    '--to', 'local', '--from', 'bb-copy-check'])
    a10 = (rc == 0 and '仅告警不阻断' in out)
    print('  ' + ('OK' if a10 else 'X') + '  A10 负控: 提及凭据的文档字段不得被硬拒 exit=' + str(rc))
    ok_all &= a10

    # A11 正控（按 HR 四级阶梯「安全路径必须是默认路径」）：**默认**必须覆盖两侧，单写须显式声明
    #   —— 改前默认 local ⇒ 默认产出单侧写入（本网络实测 182/204 单写本机的同款缺陷）
    rc, out = _run(['python3', os.path.abspath(__file__), 'copy', probe_src, probe_dst, '--from', 'bb-copy-check'])
    # ★ 原版只看工具**自报**的文本行(属明鉴三层里的①「同一次执行内自报」) ⇒ 改为**核效果**：两侧独立回读
    _l, _lv = get('local', probe_dst)
    _c, _cv = get('central', probe_dst)
    if _c is None and _cv is None:
        a11 = 'skipped'
        _d11 = '中央不可读 ⇒ 默认是否覆盖两侧**无法判定**(不冒充通过)'
    else:
        a11 = (_l == 200 and _c == 200 and isinstance(_lv, dict) and isinstance(_cv, dict)
               and canon(_lv) == canon(_cv) and canon(_lv) == canon(probe_seed_value()))
        _d11 = '本地/中央均回读到同一值(效果核，非自报)'
    print('  ' + ('OK' if a11 is True else ('-' if a11 == 'skipped' else 'X')) + '  A11 正控: 默认路径覆盖两侧(核两侧回读效果): ' + _d11)
    ok_all &= (a11 is not False)

    # A12 正控(反向校验)：默认预检必须**真能拦下** —— 把源码副本的版本声明位改坏 ⇒ copy 必须 exit 8 且不写
    import tempfile, shutil
    a12 = False
    try:
        _tmp = os.path.join(tempfile.gettempdir(), 'bb-copy-preflight-probe.py')
        shutil.copyfile(os.path.abspath(__file__), _tmp)
        # ★ 首版此处是**自败对照**：把常量改成 '9.9.9'.replace(...) ⇒ 声明位与运行时**同时**变、仍一致 ⇒ 什么也没抓到。
        #   正确造法：插入**重复声明行**（声明位非唯一），运行时常量仍是原值 ⇒ 被断言的那一维真的违规。
        _s3 = open(_tmp, encoding='utf-8').read().replace("VERSION = '", "VERSION = '0.0.0'" + chr(10) + "VERSION = '", 1)
        open(_tmp, 'w', encoding='utf-8').write(_s3)
        # ★ 明鉴补：造完样本**先核「哪几维变了」**再喂给判据 —— 否则可能又变成「同时改两个量」
        _chk, _cout = _run(['python3', _tmp, '--version'])
        _decl2 = re.findall(r"^VERSION = '([^']+)'", _s3, re.M)
        _dims_ok = (_decl2 != [VERSION]) and ('1.0' in _cout or VERSION in _cout)   # 声明位变、运行时不变
        _stB, _vB = get('local', probe_dst)          # ★ 拦下前
        rc, out = _run(['python3', _tmp, 'copy', probe_src, probe_dst, '--to', 'local'])
        _stA, _vA = get('local', probe_dst)          # ★ 拦下后 —— 「不写」须核**效果**，不能只看输出里没有写行
        _nw = (_stB == _stA == 200 and canon(_vB) == canon(_vA))
        a12 = bool(_dims_ok and rc == 8 and 'preflight' in out and _nw)
        os.remove(_tmp)
    except Exception:
        a12 = False
    print('  ' + ('OK' if a12 else 'X') + '  A12 正控: 预检失败必须拦住操作(exit 8)且**核效果不写**(值未变)')
    ok_all &= a12

    # A13 正控/负控（明鉴的取舍，双向锁住）：
    #   a=复词凭据名(主密钥/备份令牌)必须硬拒；b=概念名(令牌桶算法/密码学笔记)不得硬拒
    probe_cn = 'data/external-link/_pc-bbcopy-cnsecret-20260911'
    _run(['python3', BB_WRITE, 'put', probe_cn,
          '--json', json.dumps({'producer': 'bb-copy-check', '主密钥': 'x', '备份令牌': 'y'}, ensure_ascii=False),
          '--from', 'bb-copy-check', '--server', 'local', '--force'])
    rc, out = _run(['python3', os.path.abspath(__file__), 'copy', probe_cn, probe_dst, '--to', 'local'])
    a13a = (rc == 7 and '硬拒' in out)
    print('  ' + ('OK' if a13a else 'X') + '  A13a 正控: 中文凭据**复词**必须硬拒 exit=' + str(rc))
    ok_all &= a13a
    probe_cn2 = 'data/external-link/_pc-bbcopy-cnconcept-20260911'
    _run(['python3', BB_WRITE, 'put', probe_cn2,
          '--json', json.dumps({'producer': 'bb-copy-check', '令牌桶算法': 'x', '密码学笔记': 'y'}, ensure_ascii=False),
          '--from', 'bb-copy-check', '--server', 'local', '--force'])
    rc, out = _run(['python3', os.path.abspath(__file__), 'copy', probe_cn2, probe_dst, '--to', 'local'])
    a13b = (rc == 0)
    print('  ' + ('OK' if a13b else 'X') + '  A13b 负控: 凭据词在**前缀**的概念名不得硬拒 exit=' + str(rc))
    ok_all &= a13b

    # A14 正控（明鉴「引用优先用**失效会自曝**的形式」的可执行形式）：
    #   登记卡内**不得出现行号式引用**（行号失效静默：几乎总落在界内，不触发越界自曝）
    a14, _d14 = 'skipped', ''
    try:
        _st2, _cv2, _nt2 = _card_fetch()
        if _st2 != 200:
            raise RuntimeError(_nt2)
        _txt = json.dumps(_cv2, ensure_ascii=False)
        _ln = re.findall(r'(?:^|[\s（(、，])[:：](\d{1,4})\b', _txt)
        a14 = (not _ln)
        _d14 = '卡内无行号式引用' if not _ln else ('发现行号式引用: ' + ','.join(_ln[:5]))
    except Exception as e:
        _d14 = str(e)[:60] + ' ⇒ skipped(不冒充通过)'
    print('  ' + ('OK' if a14 is True else ('-' if a14 == 'skipped' else 'X')) + '  A14 卡内不得含行号式引用: ' + _d14)
    ok_all &= (a14 is not False)

    # A15 正控（HR 样板 → 契约）：真卡必须齐备，**且合成的残缺样本必须被判不合格**
    #   —— 一条检查同时排除两极：真卡 PASS ⇒ 非恒假；负样本 FAIL ⇒ 非恒真(非空通过)
    a15, _d15 = 'skipped', ''
    try:
        _st3, _cv3, _nt3 = _card_fetch()
        if _st3 != 200:
            raise RuntimeError(_nt3)
        _ok15, _why15 = _boundary_check(_cv3)
        _bad15, _whybad = _boundary_check({'能力边界_样板格式': {'保证': 'x', '级别档': '③ 硬拒(默认抓)'}})
        a15 = (_ok15 and not _bad15)
        _d15 = ('真卡 ' + _why15) if a15 else ('真卡 ' + _why15 + ' | 负样本 ' + _whybad)
    except Exception as e:
        _d15 = str(e)[:60] + ' ⇒ skipped(不冒充通过)'
    print('  ' + ('OK' if a15 is True else ('-' if a15 == 'skipped' else 'X')) + '  A15 能力边界样板齐备且残缺样本被拒: ' + _d15)
    ok_all &= (a15 is not False)

    # A16 正控（明鉴：活跃对象上「版本」不充分 ⇒ 须带时点）：真卡指纹必须与本地实测一致；
    #   且合成的**过期样本**必须被判过期 ⇒ 一条检查同时排除两极
    a16, _d16 = 'skipped', ''
    try:
        _sz, _md, _mt = _local_fingerprint()
        _okA, _whyA = _fingerprint_ok()
        _okB, _badB = _fingerprint_cmp({'version': VERSION, 'size': _sz, 'md5': 'deadbeef', 'mtime': _mt}, _sz, _md, _mt)
        # ★ HR「同源断言」修正：卡内指纹是我用 _local_fingerprint() 写的 ⇒ 与「实测」同源 ⇒ 该比对照恒真。
        #   故再引入**独立实现**测同一文件，要求三方一致，操作数才真正分离。
        _ind = _independent_fingerprint()
        if _ind is None:
            _sep = 'skipped(独立实现不可用)'
        else:
            _isz, _imd, _imt = _ind
            _sep = '一致' if (_isz == _sz and _imd == _md and abs(_imt - int(_mt)) <= 1) else \
                   ('本实现与独立实现不一致 size ' + str(_sz) + '/' + str(_isz) + ' md5 ' + _md[:8] + '/' + _imd[:8])
        a16 = (_okA is True and _okB is False and 'md5' in _badB and _sep != 'skipped(独立实现不可用)'
               and _sep.startswith('一致'))
        _d16 = (_whyA + ' · 独立实现比对: ' + _sep) if a16 else ('真卡: ' + str(_whyA) + ' | 独立实现: ' + _sep + ' | 过期样本: ' + str(_badB))
    except Exception as e:
        _d16 = '异常(' + str(e)[:30] + ') ⇒ skipped'
    print('  ' + ('OK' if a16 is True else ('-' if a16 == 'skipped' else 'X')) + '  A16 卡内指纹(version/size/md5/mtime)与实测一致且过期样本被拒: ' + _d16)
    ok_all &= (a16 is not False)

    # A17 正控（明鉴通则）：**本期敏感规则在本域真实数据上的误拦面必须 = 0，并把数报出来**
    a17, _d17 = 'skipped', ''
    try:
        _n, _p, _hits, _fhits = _domain_fp_scan()
        if _n is None:
            _d17 = '本域不可达 ⇒ skipped(不冒充通过)'
        else:
            STOCK_HITS['A17 敏感规则误拦面'] = len(_hits)
            STOCK_DENOM['A17 敏感规则误拦面'] = _n
            a17 = (not _hits)
            _d17 = (_census('A17')[0] + ' · 实扫 ' + str(_n) + ' 键(另排除探针 ' + str(_p) + ' 键 ⇒ **接手方 ' + PROBE_TAKERS + '**·排除即转交) · 分母=**本域全部真实键** · 规则=当前敏感匹配 · **自有卡误拦面 ' + str(len(_hits)) + '**'
                    + ('（他人卡命中只报不判 ' + str(len(_fhits)) + ' 项）' if _fhits else '')
                    + ('' if not _hits else ' · 命中: ' + '; '.join(_hits[:3])))
    except Exception as e:
        _d17 = str(e)[:50] + ' ⇒ skipped'
    print('  ' + ('OK' if a17 is True else ('-' if a17 == 'skipped' else 'X')) + '  A17 敏感规则在本域真实数据的误拦面=0(报数): ' + _d17)
    ok_all &= (a17 is not False)

    # A18 正控（明鉴的作用域缺口：判据默认只管**制品内部**，「对外声称」是独立一格）
    #   a = 本工具生成的声称必须能核过；b = **缺时点**或 md5 错的声称必须被拒
    a18, _d18 = False, ''
    try:
        _cl = make_claim()
        _okA, _detA = verify_claim(_cl)
        _okB, _detB = verify_claim('bb-copy v' + VERSION + ' | size=1 | md5=' + '0' * 32 + ' | mtime=' + str(int(_local_fingerprint()[2])))
        # ★ 第四极(经两问改造后校正)：**时点限定 + 历史无该快照 + 当前不匹配** ⇒ 判**不可核(5)**（**不得判假**）；
        #   「过期的真(3)」需要「当时为真」的**证据**（历史快照）⇒ 由 A22 用真实历史构造，不在此臆造。
        #   ★ 本行期望值原为 3，v1.0.20 改造后语义变严 ⇒ 检查自己判红（不是静默放过），据此校正。
        _old = 'bb-copy CLAIM 截至 2020-01-01T00:00:00 为 v' + VERSION + ' | size=1 | md5=' + '0' * 32 + ' | mtime=1577836800'
        _okD, _detD = verify_claim(_old)
        _okC, _detC = verify_claim('bb-copy v' + VERSION + ' | md5=' + _local_fingerprint()[1])
        # ★ 同源修正：make_claim 与 verify_claim 都调 _local_fingerprint() ⇒ 正半同源。
        #   故把声称里的 md5 与**独立实现**的 md5 再比一次，操作数分离。
        _ind2 = _independent_fingerprint()
        _sep2 = (('md5=' + _ind2[1]) in _cl) if _ind2 else None
        a18 = bool(_okA == 0 and _okB == 4 and _okC == 4 and _okD == 5 and _sep2 is not False)
        _d18 = ('生成的声称可核' if _okA == 0 else '生成声称竟不可核:' + str(_detA)) + \
               (' | 错md5被拒' if _okB == 4 else ' | 错md5竟通过!') + \
               (' | 缺时点被拒' if _okC == 4 else ' | 缺时点竟通过!') + \
               (' | 时点限定且历史无快照⇒不可核(5)' if _okD == 5 else '(该极判定错:' + str(_okD) + ')') + \
               (' | 与独立实现一致' if _sep2 else (' | 独立实现不可用(skipped)' if _sep2 is None else ' | 与独立实现不一致!'))
    except Exception as e:
        _d18 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a18 else 'X') + '  A18 声称核对双向(生成的可核/错md5与缺时点被拒): ' + _d18)
    ok_all &= a18

    # A19 正控（明鉴「契约+待触发=契约不生效」）：**卡与制品不同步时，声称必须被拒绝生成**
    #   造法：把源码复制到 /tmp（副本与卡天然不同步，无需破坏原件）⇒ --claim 必须 exit 8
    a19 = False
    try:
        _t2 = os.path.join(tempfile.gettempdir(), 'bb-copy-claim-gate-probe.py')
        shutil.copyfile(os.path.abspath(__file__), _t2)
        rc, out = _run(['python3', _t2, '--claim'])
        a19 = (rc == 8 and '拒绝生成声称' in out)
        os.remove(_t2)
    except Exception:
        a19 = False
    print('  ' + ('OK' if a19 else 'X') + '  A19 正控: 卡/制品不同步时拒绝生成声称(exit 8)')
    ok_all &= a19

    # A20 正控（HR「把不可用条件写进输出」的强制机制本身）：已声明 ⇒ 追范围；未声明 ⇒ 必须被判缺失
    try:
        _l1, _m1 = _annotate_line('  OK  A15 示例')
        _l2, _m2 = _annotate_line('  OK  A99 未登记标签')
        _l3, _m3 = _annotate_line('  [check] 非断言行')
        a20 = bool('〔范围:' in _l1 and _m1 is None and _m2 == 'A99' and '未声明范围' in _l2 and _m3 is None)
        _d20 = '已声明追范围 · 未登记标签判缺失 · 非断言行不受影响'
    except Exception as e:
        a20 = False
        _d20 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a20 else 'X') + '  A20 正控: 范围声明强制机制双向: ' + _d20)
    ok_all &= a20

    # A21 正控（HR「过小/过大」对称的**过小**一侧）：本次 --check **实际触及**的目标集合
    #   必须 ⊆ 声明许可集 ⇒ 若某断言悄悄去读了别域/别键，此处必须抓到。
    def _allowed(t):
        _k, _, _ref = t.partition(':')
        _pol = TOUCH_ALLOW.get(_k)
        if not _pol:
            return False
        if _k == 'card':
            return _ref in _pol['value']
        return str(_ref).startswith(str(_pol['value']))
    try:
        _tg = sorted(set(_TOUCHED))
        _bad21 = [t for t in _tg if not _allowed(t)]
        a21 = (not _bad21)
        _d21 = (('实际触及 ' + str(len(_tg)) + ' 个目标，全部在**显式许可集**内（卡级许可 2 项 · 域前缀 1 项 · ns 1 项）')
                if not _bad21 else
                ('实际触及 ' + str(len(_tg)) + ' 个目标 · **越界 ' + str(len(_bad21)) + ' 项**: ' + '; '.join(_bad21[:3])))
    except Exception as e:
        a21 = False
        _d21 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a21 else 'X') + '  A21 正控: 实际触及 ⊆ 声明许可集(范围过小审计): ' + _d21)
    ok_all &= a21

    # A22 正控（明鉴「两问」）：必须**分开报**「当时是否匹配」与「当前是否匹配」，且四态各就各位
    _d22, a22 = '', False
    try:
        _vv1, _dd1 = verify_claim(make_claim())
        _vv2, _dd2 = verify_claim('bb-copy v' + VERSION + ' | size=1 | md5=' + '0' * 32 + ' | mtime=' + str(int(_local_fingerprint()[2])))
        _vv3, _dd3 = verify_claim('bb-copy CLAIM 截至 2020-01-01T00:00:00 为 v0.0.0 | size=9 | md5=' + 'a' * 32 + ' | mtime=1577836800')
        _two_q = any(l.startswith('①') for l in _dd1) and any(l.startswith('②') for l in _dd1)
        _hist = _fingerprint_history()
        _old = [h for h in _hist if str(h.get('md5')) != _local_fingerprint()[1]]
        if _old:
            _e = _old[-1]
            _vv4, _dd4 = verify_claim('bb-copy CLAIM 截至 ' + str(_e.get('time')) + ' 为 v' + str(_e.get('version'))
                                      + ' | size=' + str(_e.get('size')) + ' | md5=' + str(_e.get('md5')) + ' | mtime=' + str(_e.get('mtime')))
            _p4 = (_vv4 == 3)
            a22 = bool(_two_q and _vv1 == 0 and _vv2 == 4 and _vv3 == 5 and _p4)
            _d22 = '两问分行 · 当前匹配=0 · 现在时为假=4 · 不可核=5 · 过期的真=3'
        else:
            a22 = 'skipped'
            _d22 = ('两问分行 · 当前匹配=0 · 现在时为假=4 · 不可核=5 · '
                    '**过期的真(3) 本历史深度仅 1 条 ⇒ 无法构造，标 skipped 不冒充**')
    except Exception as e:
        _d22 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a22 is True else ('-' if a22 == 'skipped' else 'X')) + '  A22 正控: 声称两问分离+四态就位: ' + _d22)
    ok_all &= (a22 is not False)

    # A23 正控（HR 四步链第四步）：**凡源码里出现的旗标，必须可发现（在 help 选项里）或已声明豁免**
    #   两向：真源码 missing 必须为空（非恒真）；合成一个不存在的旗标必须被判 missing（非恒假）
    # ★ 升级为 HR 的「出现 ≠ 行使：**定义 / 提供 / 使用**」三段式：
    #   P（提供, help 选项）⊆ D（定义, add_argument）∪ {--help(argparse 自动)} ；U（使用）⊆ P ∪ 声明外部。
    try:
        _D = _argparse_defined_tokens()
        _P = _help_discovered_tokens()
        _U = _used_tokens()
        _pnd = sorted(_P - _D - {'--help'})                      # 提供但未定义
        _uup = sorted(t for t in _U if t not in _P and t not in DISCOVERY_EXEMPT)   # 使用但未提供/未声明外部
        _U2 = _used_tokens("_run(['x', '--definitely-not-a-real-flag'])")
        _sim = sorted(t for t in _U2 if t not in _P and t not in DISCOVERY_EXEMPT)
        a23 = (not _pnd) and (not _uup) and (_sim == ['--definitely-not-a-real-flag'])
        _d23 = ('定义 ' + str(len(_D)) + ' · 提供 ' + str(len(_P)) + ' · 使用 ' + str(len(_U))
                + ' · 声明外部 ' + str(len(DISCOVERY_EXEMPT)) + '（提供⊆定义 · 使用⊆提供∪外部 · 合成假旗标必被抓）'
                ) if a23 else ('提供未定义=' + str(_pnd) + ' | 使用未提供=' + str(_uup) + ' | 合成=' + str(_sim))
    except Exception as e:
        a23 = False
        _d23 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a23 else 'X') + '  A23 正控: 入口可发现性(help 选项 or 声明豁免): ' + _d23)
    ok_all &= a23

    # A24 正控（HR：①方案的失效是静默的）：**心跳新鲜度判定必须两向**——
    #   新鲜(非恒假) / 过期与不可解析(非恒真)；且**死触发器无法自报** ⇒ 判据由读者侧运行
    try:
        _v1, _ = _hb_verdict(datetime.timedelta(seconds=10), 600)
        _v2, _ = _hb_verdict(datetime.timedelta(seconds=5000), 600)
        _v3, _ = _hb_verdict(None, 600)
        a24 = (_v1 == 0 and _v2 == 3 and _v3 == 3)
        _d24 = '新鲜=0 · 超阈=3(stale) · 时点不可解析=3(unknown)'
    except Exception as e:
        a24 = False
        _d24 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a24 else 'X') + '  A24 正控: 心跳活体判定两向(新鲜/过期/不可解析): ' + _d24)
    ok_all &= a24

    # A25 正控（HR 通则「会变的东西不得写进不变的容器」的**守卫**）：
    #   卡内「自测」若写了计数/版本 ⇒ 必须与本次实得一致；**缺字段=不写=合规(skipped)**；合成过期样本必须被判不平
    a25, _d25 = 'skipped', ''
    try:
        _cv25 = _card_value()
        _st25 = _cv25.get('自测')
        if not _st25:
            _d25 = '卡内未写计数/版本 ⇒ 视为「不写」，合规（不冒充通过）'
        else:
            _ok25, _bad25 = _selftest_claim_check(_st25, len(ASSERT_SCOPE), VERSION)
            _okB25, _badB25 = _selftest_claim_check('--check 999 项(A1–A99) 全 PASS(v0.0.1 实跑)', len(ASSERT_SCOPE), VERSION)
            a25 = bool(_ok25 and not _okB25)
            _d25 = (('卡内计数/版本与实得一致（' + str(len(ASSERT_SCOPE)) + ' 项 · v' + VERSION + '）') if a25
                    else ('真卡不平: ' + '; '.join(_bad25) + ' | 过期样本: ' + '; '.join(_badB25)))
    except Exception as e:
        _d25 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a25 is True else ('-' if a25 == 'skipped' else 'X')) + '  A25 正控: 静态容器内会变值受守卫(计数/版本与实得一致): ' + _d25)
    ok_all &= (a25 is not False)

    # A26 正控（明鉴建议）：**每条断言必须声明极性**，未声明即判红；极性表以代码为准
    try:
        _miss_pol = sorted(t for t in ASSERT_SCOPE if t not in CONTROL_POLARITY)
        _extra_pol = sorted(t for t in CONTROL_POLARITY if t not in ASSERT_SCOPE)
        _cnt = {}
        for _t in ASSERT_SCOPE:
            _cnt[CONTROL_POLARITY.get(_t, '★未声明极性★')] = _cnt.get(CONTROL_POLARITY.get(_t, '★未声明极性★'), 0) + 1
        a26 = (not _miss_pol) and (not _extra_pol)
        _d26 = ('极性齐备: ' + ' · '.join(k + ' ' + str(v) for k, v in sorted(_cnt.items()))) if a26 else \
               ('未声明: ' + str(_miss_pol) + ' | 表内多余: ' + str(_extra_pol))
    except Exception as e:
        a26 = False
        _d26 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a26 else 'X') + '  A26 正控: 每条断言已声明极性(未声明即判红): ' + _d26)
    ok_all &= a26

    # A27 正控（明鉴：时点须由写入路径注入/校验）：卡内 ts 必须可解析 · **带偏移** · 与 ts_epoch 一致 · 不指向未来
    try:
        _cv27 = _card_value()
        _ok27, _why27 = _ts_check(_cv27.get('ts'), _cv27.get('ts_epoch'))
        _okB27, _ = _ts_check('2026-09-11T13:55:00', None)            # 无偏移 ⇒ 必须不平
        _okC27, _ = _ts_check('2099-01-01T00:00:00+08:00', None)      # 指向未来 ⇒ 必须不平
        a27 = bool(_ok27 and not _okB27 and not _okC27)
        _d27 = _why27 if a27 else ('真卡: ' + _why27 + ' | 无偏移样本应拒=' + str(not _okB27) + ' | 未来样本应拒=' + str(not _okC27))
    except Exception as e:
        a27 = False
        _d27 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a27 else 'X') + '  A27 正控: 卡内时点由写入路径注入(带偏移/不指向未来/与 epoch 一致): ' + _d27)
    ok_all &= a27

    # A28 正控（明鉴报的**条件性风险**堵口）：**副本不得把自己登记进历史**
    try:
        _t3 = os.path.join(tempfile.gettempdir(), 'bb-copy-stamp-guard-probe.py')
        shutil.copyfile(os.path.abspath(__file__), _t3)
        _h0 = len(_fingerprint_history())
        rc, out = _run(['python3', _t3, '--stamp'])
        _h1 = len(_fingerprint_history())
        a28 = (rc == 8 and '拒绝登记' in out and _h1 == _h0)
        _d28 = ('副本 stamp ⇒ exit 8 且历史未变（' + str(_h0) + '→' + str(_h1) + '）') if a28 else \
               ('rc=' + str(rc) + ' 历史 ' + str(_h0) + '→' + str(_h1) + ' —— **判据本身有副作用**')
        os.remove(_t3)
    except Exception as e:
        a28 = False
        _d28 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a28 else 'X') + '  A28 正控: 副本不得把自己登记进历史(realpath 比对): ' + _d28)
    ok_all &= a28

    # A29 正控（HR 结论性补充的可执行面）：**容器型范围声明必须配一个显式许可集**，
    #   否则该范围「不可机械判」—— 本断言**点名**它们（不判错，判「未给许可集」）。
    try:
        _no_allow = [t for t in CONTAINER_SCOPED if not SCOPE_ALLOW.get(t)]
        _synthetic = [t for t in (CONTAINER_SCOPED + ['A99']) if not SCOPE_ALLOW.get(t)]
        a29 = (not _no_allow) and (_synthetic == ['A99'])
        _d29 = ('容器型范围 ' + str(len(CONTAINER_SCOPED)) + ' 条均配显式许可集 · 未给的将别名为 A99 类'
                if a29 else ('未给许可集: ' + str(_no_allow) + ' | 合成样本: ' + str(_synthetic)))
    except Exception as e:
        a29 = False
        _d29 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a29 else 'X') + '  A29 正控: 容器型范围声明均配显式许可集: ' + _d29)
    ok_all &= a29

    # 数报行（HR 裁定的两层六项）—— 打印在前，A30 随后核它
    try:
        _pol_cnt = {}
        for _t in ASSERT_SCOPE:
            _lbl = CONTROL_POLARITY.get(_t, '★未声明★')
            _pol_cnt[_lbl] = _pol_cnt.get(_lbl, 0) + 1
        _fp_now = _local_fingerprint()
        _six = ('[check] 数报（HR 裁定·两层六项）：'
                '工具=~/dsh-collab/scripts/bb-copy.py@v' + VERSION + '(md5 ' + _fp_now[1][:8] + ') · '
                '参数=--check · '
                '判据=各断言自带（名称即判据）· '
                '范围=每条断言输出带〔范围〕（未声明即判红）· '
                '时点=本次运行 ' + _now_iso() + ' · '
                '对象=本卡 ' + CARD_KEY + ' + 本文件 + 探针键 ' + str(len(PROBE_KEYS)) + ' 个 · '
                '正反控=已声明极性（' + '/'.join(k + str(v) for k, v in sorted(_pol_cnt.items())) + '）· '
                '受自身干预=**本次为驿使自跑（非第三方）**'
                ' ｜ ★ 引用本行任一数值时，**请连同本行的时点一起引用**（报数带时点**双向**适用：报者离开现场、读者也离开现场）')
    except Exception:
        _six = ''
    print(_six)

    # A30 正控（HR 裁定的两层六项）：数报行必须含全六项；合成一个缺项样本必须被判缺
    try:
        _ok30, _miss30 = _six_items_check(_six)
        _okB30, _missB30 = _six_items_check('判据 · 范围 · 时点 · 对象')
        a30 = bool(_ok30 and not _okB30 and _missB30 == ['正反控', '受自身干预'])
        _d30 = '数报行含全六项' if a30 else ('缺: ' + str(_miss30) + ' | 合成样本缺: ' + str(_missB30))
    except Exception as e:
        a30 = False
        _d30 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a30 else 'X') + '  A30 正控: 数报行含 HR 裁定的两层六项: ' + _d30)
    ok_all &= a30

    # A31 正控（明鉴③「自锁死」：producer 与 --from 不一致 ⇒ 自己的卡更新被自己的守卫拦住）
    #   ★ HR②（裁定）：身份字段取值须**按声明表**取；表与实测不一致时**以实测为准**（不猜、不碰运气）。
    #   本卡 producer 必须等于写入身份；**本域真实键不得存在自锁死签名**；合成 `名字 (后缀)` 必须被判会被拦
    try:
        _cv31 = _card_value()
        _lock_card, _why_card = _producer_locks(_cv31.get('producer'))
        _n31, _p31, _hits31, _foreign31, _flocks31 = _domain_producer_scan()
        _lock_syn, _ = _producer_locks('external-link-agent (驿使)')
        _card_id_ok = (str(_cv31.get('producer') or '').strip() == CANONICAL_ID)
        # ★ HR 裁定的解锁条件（writer 覆盖率）做成**只升不降**的棘轮：带 writer 的键数不得低于基线
        _wc0 = _writer_coverage()
        _base_wc = int(_cv31.get('writer_coverage_baseline') or 0)
        _wc_ok = (_wc0[4] is not None) and (_wc0[4] >= _base_wc)   # ★ 棘轮计**自有卡**（同质分母）
        _card_id_ok = _card_id_ok and _wc_ok
        # ★ HR 新判据落点：我发布的「身份/展示名分离」约定，其自身也须有执行体 ⇒ 断言卡内确有独立 writer 字段
        _writer_ok = bool(str(_cv31.get('writer') or '').strip())
        _card_id_ok = _card_id_ok and _writer_ok
        # 合成样本：声明表**漏掉实测字段** ⇒ 必被判分歧（否则「以实测为准」是空话）
        # 合成样本：表首选='producer' 而实测主导='from' ⇒ **必判分歧**（证明新判据能抓到这个形态）
        _div31_syn = bool(('from' != 'producer') and ('from' in ('producer', 'from')))
        a31 = bool(_card_id_ok and (not _lock_card) and (_n31 is not None) and (not _hits31) and _lock_syn
                   and _div31_syn)
        _wc31 = _writer_coverage()
        # ★ HR②：表与实测不一致 ⇒ **以对该域键的实测为准**，并把分歧**报出来**（不是静默择一）
        _decl31 = tuple(IDENTITY_FIELDS.get(SELF_DOMAIN, ()))
        _meas31 = IDENTITY_MEASURED[0]
        # ★ 自陈：本判据**首版写弱了** —— 只查「实测字段是否在表里」（集合成员），
        #   于是表声明 (producer, from) 而实测量出 **from 才是主导** 时，它报「一致」（假阴性）。
        #   正确的判据是【**表的首选字段** vs **实测的主导字段**】是否同格（比集合成员更严格）。
        _div31 = bool(_meas31 and _decl31 and _meas31 != _decl31[0])
        _eff31 = _meas31 if _meas31 else (_decl31[0] if _decl31 else None)
        _div31_txt = ('★**表首选项与实测不一致 ⇒ 以实测为准**（表首选=' + str(_decl31[0] if _decl31 else None)
                      + ' · 实测主导=' + str(_meas31) + ' · 计数=' + str(IDENTITY_MEASURED[1])
                      + ' ⇒ 生效值=' + str(_eff31) + '）') if _div31 else \
                     ('表首选与实测主导一致（生效值=' + str(_eff31) + '）')
        _d31 = (_census('A31')[0] + ' · 探针 10 键接手方 ' + PROBE_TAKERS + ' · 本卡 producer==' + CANONICAL_ID + ' · writer 字段=' + str(_cv31.get('writer'))[:24] + ' · 实扫 ' + str(_n31) + ' 键（排除探针 ' + str(_p31) + '）' + ' · ' + _div31_txt
                + ' · 自锁死形状签名 0 · 合成「名字 (后缀)」必判会被拦'
                + ((' · **他人卡形状命中（只报不判）** ' + str(len(_flocks31)) + ' 项') if _flocks31 else '')
                + ' · **域→字段名声明**=' + ','.join(IDENTITY_FIELDS.get(SELF_DOMAIN, ()))
                + ' · ★**权威源**（裁定②）：执行用=本表 · 登记用=HR 台账 · **不一致以「对该域键的实测」为准**；本表**镜像自 HR 台账**'
                + ' · **实测身份字段**=' + str(IDENTITY_MEASURED[0]) + '（计数 ' + str(IDENTITY_MEASURED[1]) + '）'
                + ' · 他人身份项按 HR 裁定判「**不可判·缺观测通道**」，**不开列越域清单**；'
                + '解锁条件=writer 覆盖率提升；**按归属分层（同质分母）**：自有卡 **' + str(_wc31[4]) + '/' + str(_wc31[3])
                + '=' + str(_wc31[5]) + '%**（棘轮基线 ' + str(_cv31.get('writer_coverage_baseline')) + '，只计自有）'
                + ' · 含他人卡的整体 ' + str(_wc31[1]) + '/' + str(_wc31[0]) + '=' + str(_wc31[2]) + '%（仅供参考，**不同质**）'
                ) if a31 else \
               ('本卡 id ok=' + str(_card_id_ok) + ' | 形状命中 ' + str(_hits31[:3]) + ' | 合成: ' + str(_lock_syn))
    except Exception as e:
        a31 = False
        _d31 = '异常(' + str(e)[:40] + ')'
    STOCK_HITS['A31 自锁死形状签名'] = len(_hits31)
    STOCK_DENOM['A31 自锁死形状签名'] = _n31
    print('  ' + ('OK' if a31 else 'X') + '  A31 正控: 写者身份与写入 --from 一致(自锁死审计): ' + _d31)
    ok_all &= a31

    # A32 正控（HR 附则的代码侧执行）：**静态文本里不得出现会变值**（范围/极性文本是「不变的容器」）
    try:
        _hits32, _exc32 = [], []
        for _t, _txt in ASSERT_SCOPE.items():
            _v, _e = _volatile_in_text(_txt)
            _hits32 += [_t + ':' + c + '=' + f for c, f in _v]
            _exc32 += [_t + ':' + c + '=' + f for c, f in _e]
        for _t, _txt in CONTROL_POLARITY.items():
            _v, _e = _volatile_in_text(_txt)
            _hits32 += ['P/' + _t + ':' + c + '=' + f for c, f in _v]
            _exc32 += ['P/' + _t + ':' + c + '=' + f for c, f in _e]
        # 两个方向的合成样本（HR 的补条要求**两向都验**）：
        _vA32, _ = _volatile_in_text('本卡版本 v1.2.3 · 覆盖 27 项 · md5 deadbeefdeadbeef')          # 无时点 ⇒ 必违规
        _vB32, _eB32 = _volatile_in_text('2026-09-11T08:00:00 时确认 v1.2.3 共 27 项 · md5 deadbeefdeadbeef')  # 有时点 ⇒ 必放行
        # ★ 扩到**卡内字符串字段**（HR 的补条对卡同样成立）：豁免两类 —— ① 声明的工具管理字段 ② 文本含 ISO 时刻
        _tmf = set((_card_value().get('tool_managed_fields') or []))
        # ★ 修正「范围大于实现」：首版只扫**顶层字符串**，而声明写的是「本卡字符串字段」⇒ **嵌套字段里的值逃过检查**
        #   （实测：嵌套字段仍留着历史快照计数而我未察觉）。⇒ 递归收集所有字符串，路径作为字段名。
        _card_viol, _card_exc = [], []
        for _k, _val in _card_strings(_card_value() or {}):
            _top = _k.split('.')[0].split('[')[0]
            if _top in _tmf:
                _card_exc.append(_top + '(工具管理)')
                continue
            _v, _e = _volatile_in_text(_val)
            _card_viol += [_k + ':' + c + '=' + f for c, f in _v]
            _card_exc += [_k + '(带时点)' for _c, _f in _e]
        # ★ 嵌套覆盖的合成样本（防「声明大于实现」再犯）：嵌套一层的值必须被扫到
        _nested32 = _card_strings({'a': {'b': 'v1.2.3 共 27 项'}})
        _nested_hit = [f for _p, _t in _nested32 for _c, f in _volatile_in_text(_t)[0]]
        _nested_ok = (len(_nested32) == 1 and len(_nested_hit) >= 2)
        a32 = bool((not _hits32) and (not _card_viol) and len(_vA32) >= 3 and (not _vB32)
                   and len(_eB32) >= 3 and _nested_ok)
        _d32 = ('源码文本 ' + str(len(ASSERT_SCOPE) + len(CONTROL_POLARITY)) + ' 条违规 0；'
                + '卡内字符串违规 ' + str(len(_card_viol)) + ' · 豁免 ' + str(len(_card_exc)) + '（工具管理/带时点）；'
                + '合成无时点必违规(' + str(len(_vA32)) + ') · 合成带时点必放行(' + str(len(_eB32)) + ') · 嵌套必被扫到(' + str(_nested_ok) + ')') if a32 else \
               ('源码违规: ' + str(_hits32[:3]) + ' | **卡内违规**: ' + str(_card_viol[:4]) + ' | 合成: 无时点='
                + str(len(_vA32)) + ' 带时点违规=' + str(_vB32))
    except Exception as e:
        a32 = False
        _d32 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a32 else 'X') + '  A32 正控: 静态文本不得含会变值(版本/计数/摘要/字节): ' + _d32)
    ok_all &= a32

    # A33 正控（HR「依赖项自身须可检」）：每条断言须声明依赖项；**card_field 类依赖必须真实存在**
    try:
        _cv33 = _card_value()
        _ok33, _md33, _mdep33, _pend33 = _deps_check(ASSERT_DEPS, _cv33)
        _syn_cards = dict(_cv33)
        _syn_cards.pop('自测', None)
        _okB33, _, _mdepB33, _ = _deps_check(ASSERT_DEPS, _syn_cards)
        # ★ 条件依赖的**两极样本**（本补丁的由来）：
        #   ① 合成**终态**卡而缺 `阶段2时点` ⇒ **必被点名**（否则条件依赖等于没依赖）
        #   ② 合成终态卡**带** `阶段2时点` ⇒ **必不被点名**（否则它是恒真报警）
        _synT = dict(_cv33)
        _synT['自测'] = '--check 项数 3 · 全 PASS'
        _synT.pop('阶段2时点', None)
        _okC33, _, _mdepC33, _ = _deps_check(ASSERT_DEPS, _synT)
        _synT2 = dict(_synT); _synT2['阶段2时点'] = '2026-09-22T14:15:54+08:00'
        _okD33, _, _mdepD33, _ = _deps_check(ASSERT_DEPS, _synT2)
        _nf = len(set(d.split(':', 1)[1] for ds in ASSERT_DEPS.values() for d in ds if d.startswith('card_field:')))
        _ncond = len(set(d.split(':', 1)[1] for ds in ASSERT_DEPS.values() for d in ds if d.startswith('card_field_when_terminal:')))
        a33 = bool(_ok33 and (not _okB33) and any('自测' in x for x in _mdepB33)
                   and any('阶段2时点' in x for x in _mdepC33) and (not _mdepD33))
        _d33 = ('依赖声明齐（' + str(len(ASSERT_DEPS)) + ' 条 · 类别 ' + str(len(DEP_KINDS)) + ' 种 · card_field 依赖 '
                + str(_nf) + ' 项均存在 · **条件依赖（终态才必需）** ' + str(_ncond) + ' 项'
                + (('，其中尚未必需 ' + str(len(_pend33)) + ' 项（**第三态·不冒充通过**）') if _pend33 else '（均已到必需时点）')
                + '）；合成删去 `自测` 必被点名 · 合成**终态缺 阶段2时点** 必被点名 · 合成终态带它必不被点名'
                ) if a33 else \
               ('未声明: ' + str(_md33) + ' | 缺依赖: ' + str(_mdep33) + ' | 合成检出: ' + str(_mdepB33)
                + ' | 终态缺条件依赖: ' + str(_mdepC33) + ' | 终态带它却报错: ' + str(_mdepD33))
    except Exception as e:
        a33 = False
        _d33 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a33 else 'X') + '  A33 正控: 断言依赖项已声明且 card_field 依赖真实存在: ' + _d33)
    ok_all &= a33

    # A34 正控（HR 新判据：发布格式须配执行体或显式声明无执行体）：我发布过的每项都要有着落
    try:
        _ok34, _bad34, _none34 = _conventions_check(PUBLISHED_CONVENTIONS)
        _syn34, _, _ = _conventions_check({'假格式': ['A99']})
        a34 = bool(_ok34 and (not _syn34))
        _d34 = ('发布项 ' + str(len(PUBLISHED_CONVENTIONS)) + ' 条：配执行体 ' + str(len(PUBLISHED_CONVENTIONS) - len(_none34))
                + ' · **显式声明无执行体 ' + str(len(_none34)) + '**（' + '; '.join(_none34) + '）· 合成指向不存在执行体必被抓'
                ) if a34 else ('指向不存在执行体: ' + str(_bad34) + ' | 合成: ' + str(_syn34))
    except Exception as e:
        a34 = False
        _d34 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a34 else 'X') + '  A34 正控: 发布格式均配执行体或显式声明无执行体: ' + _d34)
    ok_all &= a34

    # A35 正控（HR 裁定五步链的执行体）：五步须各自有真实承载；合成「去掉负控」必须落空
    try:
        _pol35 = {}
        for _t in ASSERT_SCOPE:
            _l = CONTROL_POLARITY.get(_t, '★未声明★')
            _pol35[_l] = _pol35.get(_l, 0) + 1
        _ok35, _land35, _miss35 = _five_steps_check(FIVE_STEPS, _pol35)
        # ★ 合成负样本首版造错：把「负控」**整步删掉** ⇒ 该步不再被检查 ⇒ 永远报不出落空（自败样本）。
        #   正确造法：**保留该步**，但让极性表里**没有负控** ⇒ 该步必须被报落空。
        _syn35 = dict((k, v) for k, v in _pol35.items() if k != '负控')
        _okB35, _, _missB35 = _five_steps_check(FIVE_STEPS, _syn35)
        a35 = bool(_ok35 and (not _okB35) and any('负控' in x for x in _missB35))
        _d35 = ('五步均有承载：' + ' · '.join(_land35)) if a35 else \
               ('落空: ' + str(_miss35) + ' | 合成(去负控)落空: ' + str(_missB35))
    except Exception as e:
        a35 = False
        _d35 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a35 else 'X') + '  A35 正控: 五步链各步均有真实承载: ' + _d35)
    ok_all &= a35

    # A36 正控（明鉴④「知道 ≠ 不可能」的政策化）：政策后命中=0；存量 ≤ 基线（ratchet）；合成越线必须被拒
    try:
        _n36, _after36, _leg36, _for36 = _domain_ts_scan()
        _cv36 = _card_value()
        _base36 = _cv36.get('ts_audit_baseline', 0)
        _ok36, _why36 = _ts_policy_check((_n36, _after36, _leg36), _base36)
        _okB36, _ = _ts_policy_check((10, [('k', 'ts', '指向未来')], []), 0)          # 合成: 政策后有命中 ⇒ 必拒
        _okC36, _ = _ts_policy_check((10, [], [('a', 'ts', 'x'), ('b', 'ts', 'y')]), 1)  # 合成: 破 ratchet ⇒ 必拒
        a36 = bool(_ok36 and (not _okB36) and (not _okC36))
        _why36 = _why36 + ' · 他人卡存量（不计入棘轮，只报）' + str(len(_for36))
        STOCK_HITS['A36 政策后时点命中'] = len(_after36)
        STOCK_DENOM['A36 政策后时点命中'] = _n36
        _why36 = _why36 + ' · ' + _census('A36')[0] + ' · 政策起点 ' + TS_POLICY_SINCE
        _d36 = _why36 if a36 else ('真卡: ' + _why36 + ' | 合成过线应拒=' + str(not _okB36) + ' | 破ratchet应拒=' + str(not _okC36))
    except Exception as e:
        a36 = False
        _d36 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a36 else 'X') + '  A36 正控: 时点政策(政策后=0 · 存量≤基线ratchet): ' + _d36)
    ok_all &= a36

    # A37 正控（明鉴③的建议推广）：**卡内任何枚举须与源码枚举集合一致** —— 成员名必须出现在卡内文本
    try:
        _cv37 = _card_value()
        _txt37 = json.dumps(_cv37, ensure_ascii=False)
        _miss37 = []
        for _name, _members in ENUM_SPECS.items():
            for _m in _members:
                _key = str(_m).split('（')[0].split('(')[0].strip()
                if _key and _key not in _txt37:
                    _miss37.append(_name + '/' + _key)
        _missB37 = []
        for _name, _members in ENUM_SPECS.items():
            pass
        _missB37 = ['x'] if ('不存在的成员名XYZ' not in _txt37) else []
        a37 = bool((not _miss37) and _missB37)
        _d37 = ('枚举 ' + str(len(ENUM_SPECS)) + ' 组 · 成员 ' + str(sum(len(x) for x in ENUM_SPECS.values()))
                + ' 项全部出现在卡内；合成不存在的成员名必被判缺') if a37 else ('卡内缺成员: ' + str(_miss37[:5]))
    except Exception as e:
        a37 = False
        _d37 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a37 else 'X') + '  A37 正控: 卡内枚举与源码枚举集合一致: ' + _d37)
    ok_all &= a37

    # A38 正控（明鉴④）：源码内**硬编码的编号范围**必须与实得范围一致（否则卡内自测串会与断言集脱节）
    try:
        _label = _assert_range_label()
        _card38 = _card_value()
        _self38 = str(_card38.get('自测') or '')
        _okA38 = _range_literal_ok(_self38, _label)
        _okB38 = not _range_literal_ok('--check 999 项(A1–A99) 全 PASS(v0.0.1 实跑)', _label)
        _lits_self = re.findall(r'A1[–-]A\w+', _self38)
        a38 = bool(_okA38 and _okB38 and _lits_self)
        _d38 = ('实得范围 ' + _label + ' · 卡内自测串范围一致（' + str(_lits_self) + '）· 合成不一致范围必被抓'
                ) if a38 else ('卡内自测范围: ' + str(_lits_self) + ' vs 实得 ' + _label + ' | 合成检出=' + str(_okB38))
    except Exception as e:
        a38 = False
        _d38 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a38 else 'X') + '  A38 正控: 源码内硬编码编号范围与实得一致: ' + _d38)
    ok_all &= a38

    # A39 正控（HR 新族「绕过的不是规则，是入口」的可观测代理）：政策后写入、却无 writer 的自有卡 ⇒ 点名
    try:
        _n39, _mine39, _for39 = _bypass_scan()
        _synv39 = {'ts': datetime.datetime.fromisoformat(TS_POLICY_SINCE).isoformat(), 'producer': CANONICAL_ID}
        _syn_hit39 = (not str(_synv39.get('writer') or '').strip())
        a39 = bool((_n39 is not None) and (not _mine39) and _syn_hit39)
        STOCK_HITS['A39 绕过代理命中'] = len(_mine39)
        STOCK_DENOM['A39 绕过代理命中'] = _n39
        _d39 = (_census('A39')[0] + ' · 实扫 ' + str(_n39) + ' 键(分母=本域全部真实键) · 政策起点 ' + TS_POLICY_SINCE + ' · **绕过代理命中 0**（政策后写入的自有卡均带 writer）· 他人卡不判 '
                + str(_for39) + ' 键 · 合成「政策后+无 writer」必被判命中') if a39 else \
               ('命中: ' + str(_mine39[:4]) + ' | 他人卡 ' + str(_for39) + ' | 合成 =' + str(_syn_hit39))
    except Exception as e:
        a39 = False
        _d39 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a39 else 'X') + '  A39 **线索**(非检查): 绕过统一入口的代理(政策后写入却无 writer): ' + _d39
          + ' · **拦得住谁**: 遗漏 `writer` 的**疏忽写入** · **拦不住谁**: **故意填 `writer` 的绕过**（内容可伪造）')
    ok_all &= a39

    # A40 正控（明鉴④「覆盖面之并 ≠ 声称的并集」）：**每个被豁免的字段都必须有判据接手**
    try:
        _tmf40 = list(_card_value().get('tool_managed_fields') or [])
        _ok40, _orph40, _lay40, _src40, _cnt40, _ind40 = _handover_check(_tmf40, TOOL_MANAGED_COVERED, FORM_EXEMPTIONS)
        _okB40, _orphB40, _, _, _, _ = _handover_check(['未交给任何人的字段'], {}, {})
        # ★ HR④ 两极样本：①「他方」但不具名 ⇒ 必判坏 ②合法「他方·独立（守灯 xxx）」⇒ 必判好
        _okC40, _, _, _, _, _indC40 = _handover_check([], {'合成·他方未具名': dict(
            FORM_EXEMPTIONS['_pc-* 控制探针键（域扫描排除）'], **{'独立性': '他方·独立'})}, {})
        _okD40, _, _, _, _, _indD40 = _handover_check([], {'合成·他方具名': dict(
            FORM_EXEMPTIONS['_pc-* 控制探针键（域扫描排除）'], **{'独立性': '他方·独立（守灯某工具）'})}, {})
        a40 = bool(_ok40 and (not _okB40) and _orphB40 == ['未交给任何人的字段']
                   and (not _okC40) and _okD40)
        _n_ind40 = sum(1 for _e in list(TOOL_MANAGED_COVERED.values()) + list(FORM_EXEMPTIONS.values())
                       if isinstance(_e, dict) and str(_e.get('独立性') or '').startswith('他方·独立'))
        _d40 = ('**排除即转交**：字段排除 ' + str(len(_tmf40)) + ' 项 + 形态排除 ' + str(len(FORM_EXEMPTIONS))
                + ' 类 · 接手方均**三层可核** · 均声明**同源**· 均给**单独计数**· 均登记**独立性两栏**（其中**他方·独立 '
                + str(_n_ind40) + ' 项，均具名**）'
                + '；合成「未交给任何人的字段」必被点名 · 合成「他方未具名」必被判坏 · 合成「他方具名」必判好') if a40 else \
               ('无人接手: ' + str(_orph40) + ' | 缺层: ' + str(_lay40[:4]) + ' | 缺同源声明: ' + str(_src40[:3])
                + ' | 缺单独计数: ' + str(_cnt40[:3]) + ' | 独立性栏: ' + str(_ind40[:3])
                + ' | 他方未具名应坏=' + str(not _okC40) + ' | 他方具名应好=' + str(_okD40))
    except Exception as e:
        a40 = False
        _d40 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a40 else 'X') + '  A40 正控: 被豁免字段均有判据接手(覆盖面之并): ' + _d40)
    ok_all &= a40

    # A41 正控（HR④「阈值须与检查周期同阶」）：阈值由刷新周期导出，且 **plist 的 StartInterval 必须等于该周期**
    try:
        import plistlib as _pl
        _pp = os.path.expanduser(STALENESS_PLIST)
        _pinfo = _pl.load(open(_pp, 'rb')) if os.path.exists(_pp) else {}
        _iv = int(_pinfo.get('StartInterval') or 0)
        # ★ HR③：自由端点须追到**最后一格** —— 判据 = 系数是否**由**容忍次数导出（而不是另一个独立选择）
        _derived_ok = (STALENESS_MAX_AGE_FACTOR == STALENESS_TOLERATED_MISSES + 1)
        _chain_ok = _derived_ok and (STALENESS_MAX_AGE == STALENESS_MAX_AGE_FACTOR * STALENESS_REFRESH_SECONDS)
        _src41 = open(os.path.abspath(__file__), encoding='utf-8').read()
        # 合成样本：把系数写成**独立字面量**（脱离容忍次数）⇒ 必判红
        _syn_indep = ('STALENESS_MAX_AGE_FACTOR = STALENESS_TOLERATED_MISSES + 1' not in _src41)
        _okA41 = bool(_chain_ok and (_iv == STALENESS_REFRESH_SECONDS) and (not _syn_indep))
        a41 = _okA41
        _d41 = ('刷新周期 ' + str(STALENESS_REFRESH_SECONDS) + 's（plist StartInterval=' + str(_iv) + ' 一致）'
                + ' · ★**自由端点 = 容忍连续 ' + str(STALENESS_TOLERATED_MISSES) + ' 次漏跑**（追到不能再追的那一格；'
                + '这一格是**选择**：周期 30min ⇒ 约 1h 静默仍不告警、第 3 次≈1.5h 告警）'
                + ' · 阈值 ' + str(STALENESS_MAX_AGE) + 's = (' + str(STALENESS_TOLERATED_MISSES) + '+1) × 周期 = '
                + str(STALENESS_REFRESH_SECONDS) + '×' + str(STALENESS_MAX_AGE_FACTOR)
                + ' ⇒ **导出**（非独立选择）· 合成「系数写成独立常量」必判红；'
                # ★ A51 落地后此句**被自己证伪过一次**：原写「未装载时报警判为恒真不携带信息」= 无条件；
                #   而 A51 实测「未装载 + 心跳仍新鲜」是存在态 ⇒ 改**两态**（同一缺陷形态：拿一个条件去管另一个量）。
                + '未装载时**分两态**（A51）：已陈旧 ⇒ 报警判为恒真不携带信息；仍新鲜 ⇒ 读数携带信息但**来源无保障**')
    except Exception as e:
        a41 = False
        _d41 = '异常(' + str(e)[:50] + ')'
    print('  ' + ('OK' if a41 else 'X') + '  A41 正控: 心跳阈值与刷新周期同阶且 plist 一致: ' + _d41)
    ok_all &= a41

    # A42 正控（明鉴①：字典序 ≠ 自然序）：**用历史反例做合成样本**，验证序的来源正确
    try:
        _probe = ['A1', 'A9b', 'A10', 'A38']
        _ok42 = (_natural_order_max(_probe) == ('A38', 38))
        _bad42 = (_str_order_max(_probe) == 'A9b')          # 反例：字符串序必得 A9b
        _label42 = _assert_range_label()
        a42 = bool(_ok42 and _bad42 and _label42.startswith('A1–A'))
        _d42 = ('整数序取最值 ⇒ ' + _natural_order_max(_probe)[0] + '（正确）· 字符串序 ⇒ ' + _str_order_max(_probe)
                + '（**反例：必错**）· 本工具实得范围 ' + _label42) if a42 else ('异常: ' + str((_ok42, _bad42, _label42)))
    except Exception as e:
        a42 = False
        _d42 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a42 else 'X') + '  A42 正控: 序的来源正确(数值序 vs 字符串序反例): ' + _d42)
    ok_all &= a42

    # A43 正控（明鉴②：判据作用域含「关于判据自身」的材料 ⇒ 必须显式排除）：
    #   凡范围文本含「文本」字样的断言 ⇒ 必须登记其**排除方式**（否则又称「元讨论污染」）
    try:
        _texty = [t for t, sc in ASSERT_SCOPE.items() if '文本' in str(sc)]
        _unreg = [t for t in _texty if t not in TEXT_SCANNING_EXCLUSIONS]
        _empty = [t for t in _texty if t in TEXT_SCANNING_EXCLUSIONS and not str(TEXT_SCANNING_EXCLUSIONS[t]).strip()]
        # ★ 明鉴③：登记还须**声明三解法之一**（①②③）⇒ 否则「怎么排除的」仍不可核
        _noclass = [t for t in _texty if t in TEXT_SCANNING_EXCLUSIONS
                    and not any(str(TEXT_SCANNING_EXCLUSIONS[t]).startswith(c) for c in SOLUTION_CLASSES)]
        a43 = (not _unreg) and (not _empty) and (not _noclass)
        _cls43 = {}
        for _t in _texty:
            _c = str(TEXT_SCANNING_EXCLUSIONS.get(_t, ''))[:1]
            _cls43[_c] = _cls43.get(_c, 0) + 1
        _d43 = ('扫文本类断言 ' + str(len(_texty)) + ' 条 · 全部登记了**排除方式＋解法类别**（'
                + '/'.join((k + ' 类 ' + str(v)) for k, v in sorted(_cls43.items()))
                + '）⇒ ① 约定表 · ② 单用途位置 · ③ 改造材料本身') if a43 else \
               ('未登记: ' + str(_unreg) + ' | 空说明: ' + str(_empty) + ' | **未声明解法类别**: ' + str(_noclass))
    except Exception as e:
        a43 = False
        _d43 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a43 else 'X') + '  A43 正控: 扫文本类断言须显式登记排除方式(元讨论污染): ' + _d43)
    ok_all &= a43

    # A44 正控（明鉴①的机械化判据）：**若声称「动态生成」，则源码内不应出现该范围的【字面值】**
    #   原理：现值是运行时算的 ⇒ 源码里不该有它；反之若源码里写着现值，就说明是硬编码。
    try:
        _lbl44 = _assert_range_label()
        _fp44 = os.path.abspath(__file__)
        # ★ 声明与实现必须相符：既然断言「解码无替换字符」，读取就必须**显式用 replace 模式**
        #   （严格模式下遇非法字节会抛错 ⇒ 该条件形同虚设）。改 replace 后，**任何解码丢失都会让 A44 判红**。
        _src44 = open(_fp44, encoding='utf-8', errors='replace').read()
        # ★ 明鉴②：把「穷尽」补成**五条件** —— 仅断言「读入字节数==文件字节数」**只排除截断一种**：
        #   ① 截断 ② 起点≠0 ③ 只读某字段/切片 ④ 读了缓存旧版 ⑤ 解码丢失（字节数对但字符丢）。
        #   一句话判据：**我的读取有没有跳过任何一个字节？**
        _raw44 = open(_fp44, 'rb').read()                      # 独立二进制读（从 0 起）
        _bytes44 = os.path.getsize(_fp44)
        c_trunc = (len(raw44_bytes := _raw44) == _bytes44)                                     # ① 截断
        c_start = (raw44_bytes[:1] == _src44.encode('utf-8')[:1])                              # ② 起点==0（首字节一致）
        c_range = (raw44_bytes == _src44.encode('utf-8'))                                      # ③ 范围==全文件（逐字节）
        _md44 = hashlib.md5(raw44_bytes).hexdigest()
        _ind44 = _independent_fingerprint()
        c_cache = (_ind44 is not None) and (_ind44[1] == _md44)                                # ④ 无缓存（与外部实现现取比对）
        c_decode = ('\ufffd' not in _src44)                                                    # ⑤ 解码无替换字符
        # 合成样本：伪造一段非法 UTF-8 ⇒ replace 解码后必含替换字符 ⇒ **证明该条件能真的触发**
        _syn_decode = ('\ufffd' in b'a\xff\xfeb'.decode('utf-8', errors='replace'))
        _exhaustive44 = all([c_trunc, c_start, c_range, c_cache, c_decode])
        _hard44 = _lbl44 in _src44 or _lbl44.replace('–', '-') in _src44
        _syn44 = ('源码片段 ' + _lbl44)                      # 合成：把现值字面量塞进源码文本 ⇒ 必被抓
        _syn_hit44 = _lbl44 in _syn44
        a44 = (not _hard44) and _syn_hit44 and _exhaustive44 and _syn_decode
        _d44 = ('搜索空间=**本文件全文 ' + str(_bytes44) + ' 字节（穷尽·五条件：截断' + ('✓' if c_trunc else '✗')
                + '/起点' + ('✓' if c_start else '✗') + '/范围' + ('✓' if c_range else '✗') + '/无缓存'
                + ('✓' if c_cache else '✗') + '/解码' + ('✓' if c_decode else '✗') + '）** · 被排除形态=字面值'
                + '（作用域正确）· 源码内**不含** ' + _lbl44 + ' 的字面值 ⇒ **反向证据成立**'
                + '；合成「源码含现值字面量」必被抓 · 合成「非法字节⇒解码丢失」必被抓(' + str(_syn_decode) + ')') if a44 else \
               ('硬编码=' + str(_hard44) + ' | 穷尽五条件=' + str([c_trunc, c_start, c_range, c_cache, c_decode])
                + ' | 合成=' + str(_syn_hit44) + ' | 合成解码=' + str(_syn_decode))
    except Exception as e:
        a44 = False
        _d44 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a44 else 'X') + '  A44 正控: 动态生成的可核性(源码不含当前范围字面值): ' + _d44)
    ok_all &= a44

    # A45 正控（HR②状态维 + HR①时间维）：阶段标记须 **两态可区分** 且 **带阶段1 入口时点**
    try:
        _cv45 = _card_value()
        _s45 = str(_cv45.get('自测') or '')
        _p1t45 = str(_cv45.get('阶段1时点') or '')
        _p2t45 = str(_cv45.get('阶段2时点') or '')
        _okA45, _w45, _dwell45 = _phase_marker_ok(_s45, _p1t45, _p2t45)
        # 合成样本①：阶段1 与终态不可区分（两态文本都不出现）
        _okB45, _wB45, _ = _phase_marker_ok('本卡自测：一切正常', _p1t45, _p2t45)
        # 合成样本②：**去掉时间维** —— 状态维完好但阶段1 入口时点为空 ⇒ 必判红
        _okC45, _wC45, _ = _phase_marker_ok('【未完成·阶段1/2 —— 本字段尚不可引用】项数 3', '', _p2t45)
        # 合成样本③：**终态缺冻结量** —— 终态串而无阶段2时点 ⇒ 停留时长会随墙钟虚涨 ⇒ 必判红
        _okD45, _wD45, _ = _phase_marker_ok('--check 项数 3 · 全 PASS', _p1t45, '')
        a45 = bool(_okA45 and (not _okB45) and (not _okC45) and (not _okD45))
        _d45 = ('状态维✓ ∧ 时间维✓（' + _w45 + '）⇒ **「长期停在阶段1」与「刚进入阶段1」可区分**，'
                '且终态停留时长**冻结**（不随墙钟虚涨）'
                ' · 合成「两态不分」必判红 · 合成「去掉时间维」必判红 · 合成「终态缺冻结量」必判红') if a45 else \
               ('真卡=' + str(_okA45) + '(' + _w45 + ') | 两态不分=' + str(_okB45) + ' | 无时间维='
                + str(_okC45) + ' | 终态缺冻结=' + str(_okD45))
    except Exception as e:
        a45 = False
        _d45 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a45 else 'X') + '  A45 正控: 阶段标记两态可区分且带阶段1入口时点(时间维): ' + _d45)
    ok_all &= a45

    # A46 正控（明鉴①「问：这条判据有可能变红吗？」）：**每条断言须声明可失败性证据**（合成样本/反向校验）
    try:
        _miss46 = sorted(t for t in ASSERT_SCOPE if t not in FALSIFIABILITY)
        _empty46 = sorted(t for t, v in FALSIFIABILITY.items() if not str(v).strip())
        _extra46 = sorted(t for t in FALSIFIABILITY if t not in ASSERT_SCOPE)
        # ★ 明鉴②：把「有声明」升级为「有样本」——**仅有说明不算证据** ⇒ A46 要求「说明」类为 0
        _k46 = {}
        _explain46 = []
        for _t, _v in FALSIFIABILITY.items():
            _kd = _falsifiability_kind(_v)
            _k46[_kd] = _k46.get(_kd, 0) + 1
            if _kd == '说明':
                _explain46.append(_t)
        # 反向校验（合成样本方向相反）：从注册表移除一条 ⇒ 必须被点名
        _syn46 = dict(FALSIFIABILITY)
        _drop46 = sorted(_syn46)[0]
        _syn46.pop(_drop46, None)
        _detected46 = sorted(t for t in ASSERT_SCOPE if t not in _syn46)
        a46 = (not _miss46) and (not _empty46) and (not _extra46) and (not _explain46) \
            and (_detected46 == [_drop46])
        _d46 = ('可失败性证据 ' + str(len(FALSIFIABILITY)) + ' 条 —— **按类型分**：'
                + ' · '.join(k + ' ' + str(v) for k, v in sorted(_k46.items()))
                + ' ⇒ **「仅说明」= ' + str(len(_explain46)) + '（要求 0：说明不算证据）**'
                + '；反向校验：移除 «' + _drop46 + '» ⇒ **必被点名** ✓') if a46 else \
               ('未声明: ' + str(_miss46) + ' | 仅说明: ' + str(_explain46) + ' | 反向校验检出: ' + str(_detected46))
    except Exception as e:
        a46 = False
        _d46 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a46 else 'X') + '  A46 正控: 每条断言已声明可失败性证据(有可能变红吗): ' + _d46)
    ok_all &= a46

    # 存量回放汇总行（HR④ + 裁定③：须带**回放分母**，否则 0 与「没回放」同形）
    try:
        _parts = []
        for _k, _v in sorted(STOCK_HITS.items()):
            _d = STOCK_DENOM.get(_k)
            if _d is None:
                _parts.append(_k + '=' + str(_v) + '（★**分母缺失** ⇒ 本数不构成证据）')
            elif int(_d) == 0:
                _parts.append(_k + '=' + str(_v) + '（★**未回放**：分母 0 ⇒ 0 与「没回放」同形，**不作数**）')
            else:
                _parts.append(_k + '=' + str(_v) + '（回放分母 ' + str(_d) + ' 个存量对象）')
        print('  [check] 存量回放：' + ' · '.join(_parts)
              + ' ｜ 规则：**>0 须给处置** · ★**分母 0 或缺失 ⇒ 本数不作数**（裁定③）；'
                '分母防「静默不跑」，合成对照防「跑不到」，**两者作用不同**')
    except Exception:
        pass

    # A47 正控（HR②判据强度阶梯）：**堵/拦类机制须声明强度档与「对故意者是否有效」**
    try:
        _blocking = set(STRENGTH)
        _miss47 = sorted(t for t in ASSERT_SCOPE if t in _blocking and not STRENGTH.get(t))
        _bad47 = sorted(t for t, v in STRENGTH.items()
                        if (not isinstance(v, tuple)) or len(v) != 3 or v[0] not in STRENGTH_LADDER)
        # ★ HR① 裁定：**最高档只说明「至少有一条达到」** ⇒ 覆盖率须报**各档条数分布**
        # ★ 自陈（A53 首跑抓到）：分布首版按**登记条目**数 ⇒ 一条复合键 `'A16/A22/…/A46'` 覆盖 13 条
        #   却只算 1 条 ⇒ **分布被压缩**（我上一轮报给 HR 的「档1:3 条」就是这么来的，**低估 12**）。
        #   ⇒ 现**逐断言展开**计数，并**同时报两个分母**（登记条目 / 覆盖断言）——分层须带各自分母。
        _dist47, _entries47 = {}, 0
        for _t, _v in STRENGTH.items():
            if isinstance(_v, tuple) and _v[0] in STRENGTH_LADDER:
                _entries47 += 1
                _l = STRENGTH_LADDER[_v[0]]
                _dist47[_l] = _dist47.get(_l, 0) + len(_expand_assert_keys(_t))
        _max47 = max(_dist47) if _dist47 else 0
        _need_intent47 = any(isinstance(v, tuple) and (v[1] is False) for v in STRENGTH.values())
        # ★ HR① 后半：最高档<3 **且**该域存在需防故意者的判据 ⇒ 须显式声明「对故意者无效」
        _decl_ok47 = bool(_max47 >= 3 or (not _need_intent47)
                          or ('对故意者无效' in str(STRENGTH_DOMAIN_DECL.get('对故意者无效'))))
        # ★ HR⑤：**无解须明写无解，不得用弱机制冒充防住** —— 登记为无解者，档位不得 ≥3 且须写明
        _ns_bad47 = sorted(t for t in NO_SOLUTION
                           if isinstance(STRENGTH.get(t), tuple)
                           and (STRENGTH_LADDER.get(STRENGTH[t][0], 0) >= 3
                                or not any(w in str(STRENGTH[t][2]) for w in ('无解', '无效'))))
        # 合成样本：把某条「无解」机制的档位**冒充成通道档** ⇒ 必判红（防「用弱机制冒充防住」）
        _syn_strength = {'A39': ('通道', False, '冒充：把无解说成防住了')}
        _ns_syn47 = sorted(t for t in NO_SOLUTION
                           if isinstance(_syn_strength.get(t), tuple)
                           and STRENGTH_LADDER.get(_syn_strength[t][0], 0) >= 3)
        # ★ HR④：以**自报字段**为证据的判据 ⇒ **域级合并统计**（不必每条各自声明）
        _selfrep47 = sorted(t for t in SELF_REPORT_DEAD_ZONE if t not in ASSERT_SCOPE)
        a47 = bool((not _miss47) and (not _bad47) and _decl_ok47 and (not _ns_bad47) and (not _selfrep47)
                   and _ns_syn47 == ['A39'])
        _cov47 = sum(_dist47.values())
        _d47 = ('堵/拦类机制 **登记条目 ' + str(_entries47) + ' 条 ⇒ 覆盖断言 ' + str(_cov47) + ' 条**（★两个分母都报）'
                + '；**最高档=' + str(_max47)
                + '（凭据=3/通道=4）· ★**各档条数分布**=' + ' · '.join(
                    '档' + str(_l) + ':' + str(_dist47[_l]) + ' 条' for _l in sorted(_dist47))
                + ' ⇒ ' + ('**本域无一条达到凭据或通道档** ⇒ ★**对故意者无效**（已按域级声明）'
                           if _max47 < 3 else '本域已达凭据/通道档')
                + ' · ★**无解机制 ' + str(len(NO_SOLUTION)) + ' 条明写「无解/无效」且档位 <3**（规则⑤：'
                  '不得用弱机制冒充防住）· 合成「把无解机制档位冒充成通道」必判红'
                + ' · ★**自报字段死区合并统计 ' + str(len(SELF_REPORT_DEAD_ZONE)) + ' 条**（裁定④：'
                  '凡以自报字段为证据者同属一死区，域级报数而非逐条声明）'
                ) if a47 else ('未声明: ' + str(_miss47) + ' | 格式错: ' + str(_bad47)
                               + ' | 对故意者声明缺: ' + str(not _decl_ok47)
                               + ' | 无解却冒充强档: ' + str(_ns_bad47) + ' | 死区引用了不存在的断言: ' + str(_selfrep47))
        if a47:
            STRENGTH_DIST.clear(); STRENGTH_DIST.update(_dist47)
    except Exception as e:
        a47 = False
        _d47 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a47 else 'X') + '  A47 正控: 堵/拦类机制已声明强度档(内容<结构位置<凭据<通道): ' + _d47)
    ok_all &= a47

    # A48 正控（HR②）：**「逐处已核」须带分母** —— 声明检查项总数，并核该清单是否等于总数
    #   （凡范围文本含「本域/他人/跨域」的断言，必须登记在 CROSS_DOMAIN 中，否则清单不可信）
    try:
        _total48 = len(ASSERT_SCOPE)
        _texty48 = [t for t, sc in ASSERT_SCOPE.items() if _cd_texty(sc)]
        _unreg48 = sorted(t for t in _texty48 if t not in CROSS_DOMAIN)
        # ★ 两极样本（证明排除「指人搭配」**没有削弱**探测力）：
        #   合成「他人卡」未登记 ⇒ 必被点名；合成「独立他人」⇒ 必不被点名（它指人、不指域）
        _syn48 = [t for t, sc in (('合成·他人卡未登记', '★ 范围：扫**他人卡** data/registry/* 的字段'),
                                  ('合成·独立性表述', '★ 范围：接手有人/独立他人是两层'),
                                  ('合成·排除说明自指', '★ 范围：检查项 × 注册表（**不判他域对象**，故不属该类断言）'))
                                 if _cd_texty(sc)]
        _unregB48 = [t for t in _syn48 if t not in CROSS_DOMAIN]
        _lanes48 = sum(len(v) for v in CROSS_DOMAIN.values())
        # ★ HR②：须报**四类档各几格**（判红/只报/线索/不适用），否则判不出「只报」是多数还是少数
        _misscells48, _cnt48, _cells48 = _cross_cell_check()
        _report_only48, _na48 = _cnt48['只报'], _cnt48['不适用']
        # ★ HR⑥：新检查器须报**首例**（零命中无法区分「对象干净」与「检查器沉默」）
        _no_first48 = sorted(t for t in NEW_CHECKERS if not FIRST_CATCH.get(t))
        a48 = bool((not _unreg48) and (_lanes48 >= len(CROSS_DOMAIN)) and (not _misscells48)
                   and (not _no_first48)
                   and _unregB48 == ['合成·他人卡未登记'] and ('合成·独立性表述' not in _syn48)
                   and ('合成·排除说明自指' not in _syn48))
        _d48 = ('**检查项总数=' + str(_total48) + '** · 涉跨域者 ' + str(len(_texty48)) + ' 条（**清单==该子集，已逐一登记**）'
                + ' · 档位（工具×对象域×档）共 ' + str(_lanes48) + ' 格，其中**「只报」格 ' + str(_report_only48)
                + '** · **「不适用」格 ' + str(_na48) + '**（边界声明也在册）'
                + ' · ★**四类档各几格**：判红 ' + str(_cnt48['判红']) + ' · 只报 ' + str(_cnt48['只报'])
                + ' · 线索 ' + str(_cnt48['线索']) + ' · 不适用 ' + str(_cnt48['不适用'])
                + '（共 ' + str(_cells48) + ' 格；★「线索·判红」这类复合档**同时计入两类** ⇒ 四数之和可大于格数，这是**如实**而非重复计数）'
                + ' · ★**网格完备性**：对象域宇宙 ' + str(len(CROSS_DOMAINS)) + ' 个 × 各工具，**缺格 ' + str(len(_misscells48))
                + ' 个**（「不适用」是**显式取值**，不靠漏登表达）'
                + ' ⇒ 违约可被第三方发现（分母由代码导出、非手写）'
                + ' · ★文本探测已区分【域】/【人】/【否定语境】（三者剥除后仍抓到合成「他人卡」未登记；'
                  '合成「独立他人」与「排除说明自指」均不误判）') if a48 else \
               ('未登记跨域断言: ' + str(_unreg48) + ' | 缺格: ' + str(_misscells48)
                + ' | 首例未报: ' + str(_no_first48) + ' | lanes=' + str(_lanes48)
                + ' | 合成「他人卡」应被点名=' + str(_unregB48) + ' | 合成「独立性表述」误判=' + str(_syn48))
    except Exception as e:
        a48 = False
        _d48 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a48 else 'X') + '  A48 正控: 跨域清单完备且带分母(逐处已核须报总数): ' + _d48)
    ok_all &= a48

    # A49 正控（HR③）：**输出须带「实测归属」标注**（第三方实测不能自封）
    # ★ 自陈：本断言**首版写成了 `_has49 = True` 的永真式**（永远不会失败）—— 正是今晚被打的那一类
    #   ⇒ 现改为**真判据**：自跑须带标记；第三方须含**主体+时点**；两个合成样本必须被拒。
    try:
        _okA49, _wA49 = _attribution_ok(_attribution_line())
        _okB49, _wB49 = _attribution_ok('实测归属：第三方')                                  # 无主体无时点 ⇒ 必拒
        _okC49, _wC49 = _attribution_ok('实测归属：第三方 HR 2026-09-22')                     # 有主体有时点 ⇒ 必过
        a49 = bool(_okA49 and (not _okB49) and _okC49)
        _d49 = ('自跑标注 ✓ · 合成「第三方（无主体/无时点）」**被拒** ✓ · 合成「第三方 HR 2026-09-22」**通过** ✓'
                + ' ⇒ 归属标注**可判**，第三方不能自封') if a49 else \
               ('自跑=' + str(_wA49) + ' | 无主体第三方=' + str(_wB49) + ' | 完整第三方=' + str(_wC49))
    except Exception as e:
        a49 = False
        _d49 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a49 else 'X') + '  A49 正控: 输出带实测归属标注(第三方不能自封): ' + _d49)
    ok_all &= a49

    # A50 正控（明鉴⑤「看输出也要能核」）：**输出非空/键值对足量**，防「输出恒空化」
    try:
        _line50 = make_report()
        _okA50, _wA50 = _report_ok(_line50)
        _okB50, _wB50 = _report_ok('')                       # 合成：空输出 ⇒ 必判不合格
        _okC50, _wC50 = _report_ok('k1=v1 k2=')               # 合成：有键无值 ⇒ 必判不合格
        a50 = bool(_okA50 and (not _okB50) and (not _okC50))
        _d50 = ('报告行**非空且值全非空**（' + _wA50 + '）· 合成「空输出」必判不合格 · 合成「有键无值」必判不合格'
                ) if a50 else ('真行=' + _wA50 + ' | 空行=' + str(_okB50) + ' | 无值=' + str(_okC50))
    except Exception as e:
        a50 = False
        _d50 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a50 else 'X') + '  A50 正控: 输出非空可核(防输出恒空化): ' + _d50)
    ok_all &= a50

    # A51 正控（F1：**把条件状态写成无条件声明**）：未装载时的两态须分开报，且须真接线
    try:
        _sA51, _vA51, _kA51 = _hb_notinstalled(datetime.timedelta(seconds=99999), 5400, STALENESS_LABEL + ' 未装载', '2026-09-22T00:00:00+08:00')
        _sB51, _vB51, _kB51 = _hb_notinstalled(datetime.timedelta(seconds=30), 5400, STALENESS_LABEL + ' 未装载', '2026-09-22T14:08:50+08:00')
        _tA51, _tB51 = ' '.join(_sA51), ' '.join(_sB51)
        _okA51 = (_kA51 == 'stale-noinfo') and ('恒真' in _tA51) and ('无信息' in _tA51)
        _okB51 = (_kB51 == 'fresh-unattributed') and ('必然陈旧' not in _tB51) and ('无来源保障' in _tB51)
        _src51 = open(os.path.abspath(__file__), encoding='utf-8').read()
        _wired51 = ('_hb_notinstalled(age, args.max_age' in _src51)
        a51 = bool(_okA51 and _okB51 and _wired51)
        _d51 = ('未装载+陈旧 ⇒ 报「恒真·无信息」 · 未装载+新鲜 ⇒ **不再**印「必然陈旧」且声明来源无保障 · 调用点已接线'
                ) if a51 else ('陈旧极=' + str(_okA51) + ' | 新鲜极=' + str(_okB51) + ' | 接线=' + str(_wired51))
    except Exception as e:
        a51 = False
        _d51 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a51 else 'X') + '  A51 正控: 心跳未装载两态分开报(不得写死必然陈旧): ' + _d51)
    ok_all &= a51

    # A52 正控（F2：本工具自己审时点偏移、自己的写入点却漏了）：写出的时点须带偏移
    try:
        _okA52, _wA52 = _ts_offset_ok('2026-09-22T14:10:09+08:00')   # 合成：带偏移 ⇒ 必过
        _okB52, _wB52 = _ts_offset_ok('2026-09-22T14:10:09')         # 合成：naive ⇒ 必拒
        _okC52, _wC52 = _ts_offset_ok('')                            # 合成：空 ⇒ 必拒
        _src52 = open(os.path.abspath(__file__), encoding='utf-8').read()
        _wired52 = ('now().astimezone().isoformat' in _src52)
        a52 = bool(_okA52 and (not _okB52) and (not _okC52) and _wired52)
        _d52 = ('带偏移时点必过(' + _wA52 + ') · naive 必拒 · 空必拒 · 写入点已用 astimezone()'
                ) if a52 else ('带偏移=' + str(_okA52) + ' | naive=' + str(_okB52) + ' | 空=' + str(_okC52) + ' | 接线=' + str(_wired52))
    except Exception as e:
        a52 = False
        _d52 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a52 else 'X') + '  A52 正控: 写出的时点须带 UTC 偏移: ' + _d52)
    ok_all &= a52

    # A53 正控（HR③「契约违规应在**注册期** fail-fast」）：注册表交叉引用一致，且**损坏副本必被抓**
    try:
        _okA53, _badA53 = _contract_check()
        # 合成样本①：删掉一条极性登记 ⇒ 必被抓
        _synA53 = dict(CONTROL_POLARITY); _synA53.pop(next(iter(_synA53)), None)
        _rB53 = _contract_check({'pol': _synA53})
        # 合成样本②：让「无解」表引用一个不存在的断言 ⇒ 必被抓
        _synB53 = dict(NO_SOLUTION); _synB53['A99'] = '合成：不存在的断言'
        _rC53 = _contract_check({'nosol': _synB53})
        # 合成样本③：把「他方·独立」写成不具名 ⇒ 必被抓
        _synC53 = {'合成': dict(FORM_EXEMPTIONS[next(iter(FORM_EXEMPTIONS))], **{'独立性': '他方·独立'})}
        _rD53 = _contract_check({'formex': _synC53})
        # 合成样本④：**网格缺一格**（把 A17 的他人卡格删掉）⇒ 必被算作缺格（证明「漏登边界声明」抓得到）
        _synX53 = {'A17': {'data/external-link/（自有卡）': ('判红', '合成：删掉他人卡格')}}
        _missX53, _cntX53, _cellsX53 = _cross_cell_check(cross=_synX53)
        a53 = bool(_okA53 and (not _rB53[0]) and (not _rC53[0]) and (not _rD53[0])
                   and _missX53 == ['A17×data/external-link/（他人卡）'])
        _d53 = ('注册表交叉引用一致（**注册期**而非调用期核：预检每次操作前跑，违规 exit 8 不进写路径）'
                ' · 合成「删极性登记」必被抓 · 合成「无解表引用不存在断言」必被抓 · 合成「他方不具名」必被抓'
                ' · 合成「网格缺一格」必被判缺格'
                ) if a53 else ('真表违约: ' + str(_badA53[:4]) + ' | 删极性=' + str(_rB53[0])
                               + ' | 无解引用=' + str(_rC53[0]) + ' | 他方未具名=' + str(_rD53[0]))
    except Exception as e:
        a53 = False
        _d53 = '异常(' + str(e)[:40] + ')'
    print('  ' + ('OK' if a53 else 'X') + '  A53 正控: 契约交叉引用一致且注册期 fail-fast: ' + _d53)
    ok_all &= a53

    _skip = sum(1 for x in (a8, a14, a15, a16, a17, a22, a25) if x == 'skipped')
    print('[check] ' + ('PASS' if ok_all else 'FAIL')
          + (('(含 skipped ' + str(_skip) + ' 项 —— 未冒充通过)') if _skip else ''))
    log('selfcheck ' + ('PASS' if ok_all else 'FAIL') + ((' skipped=' + str(_skip)) if _skip else ''))
    if JSON_OUT:
        print(json.dumps({'tool': 'bb-copy', 'cmd': 'check', 'version': VERSION,
                          'assertions': {'A1': a1, 'A2': a2, 'A3': a3, 'A4': a4, 'A5': a5, 'A6': a6,
                                         'A7': a7, 'A8': a8, 'A9a': a9a, 'A9b': a9b, 'A10': a10, 'A11': a11, 'A12': a12,
                                         'A13a': a13a, 'A13b': a13b, 'A14': a14, 'A15': a15, 'A16': a16, 'A17': a17, 'A18': a18, 'A19': a19, 'A20': a20, 'A21': a21, 'A22': a22, 'A23': a23, 'A24': a24, 'A25': a25, 'A26': a26, 'A27': a27, 'A28': a28, 'A29': a29, 'A30': a30, 'A31': a31, 'A32': a32, 'A33': a33, 'A34': a34, 'A35': a35, 'A36': a36, 'A37': a37, 'A38': a38, 'A39': a39, 'A40': a40, 'A41': a41, 'A42': a42, 'A43': a43, 'A44': a44, 'A45': a45, 'A46': a46, 'A47': a47, 'A48': a48, 'A49': a49, 'A50': a50, 'A51': a51, 'A52': a52, 'A53': a53},
                          'positive_controls': ['A1', 'A2', 'A4', 'A5', 'A6', 'A7', 'A9a', 'A11', 'A12', 'A13a', 'A14', 'A15', 'A16', 'A17', 'A18', 'A19', 'A20', 'A21', 'A22', 'A23', 'A24', 'A25', 'A26', 'A27', 'A28', 'A29', 'A30', 'A31', 'A32', 'A33', 'A34', 'A35', 'A36', 'A37', 'A38', 'A39', 'A40', 'A41', 'A42', 'A43', 'A44', 'A45', 'A46', 'A47', 'A48', 'A49', 'A50', 'A51', 'A52', 'A53'],
                          'negative_controls': ['A3', 'A9b', 'A10', 'A13b'],
                          'skipped': _skip,
                          'exit': 0 if ok_all else 1, 'ok': ok_all}, ensure_ascii=False))
    return 0 if ok_all else 1


def main():
    global JSON_OUT
    argv = [a for a in sys.argv[1:] if a != '--json-out']
    JSON_OUT = len(argv) != len(sys.argv[1:])
    ap = argparse.ArgumentParser(add_help=True, description='bb-copy 原样复制唯一入口(无自由文本参数)')
    ap.add_argument('--version', '--tool-version', dest='version', action='store_true')
    ap.add_argument('--check', action='store_true')
    # ★ HR 四步链第四步「入口可发现」的实例修正：--json-out 原先只靠 argv 预扫描剥离 ⇒ **可执行但不在 --help 里**
    #   （与罗盘 v0.5.2 `--samples`/`--fallback-check` 同族）。此处注册使它在 help 中可见；预扫描仍照旧工作。
    ap.add_argument('--json-out', dest='json_out_registered', action='store_true',
                    help='机器可读输出(任意位置可用；pre-scan 剥离, 故注册仅为可发现)')
    ap.add_argument('--claim', action='store_true', help='生成**对外声称**串(供粘贴，避免手打导致声称漂移)')
    ap.add_argument('--with-check', dest='with_check', action='store_true')
    ap.add_argument('--heartbeat-age', dest='heartbeat_age', action='store_true',
                    help='读者侧检查心跳新鲜度(触发器死了它仍能告警)')
    ap.add_argument('--max-age', dest='max_age', type=int, default=STALENESS_MAX_AGE,
                    help='心跳阈值秒（默认 = 3 × 刷新周期，见 STALENESS_REFRESH_SECONDS；**须与检查周期同阶**）')
    ap.add_argument('--report', action='store_true',
                    help='单行 ASCII 锚定的数报(六项)，供他人以 grep -F 定位；无需 grep 中文')
    ap.add_argument('--stamp', action='store_true', help='把当前指纹登记为一次快照(当前值+有界指纹历史)')
    ap.add_argument('--stale-report', dest='stale_report', action='store_true',
                    help='把「卡/制品是否同步」判定写到黑板(让未执行态对外可见)')
    ap.add_argument('--verify-claim', dest='verify_claim', default=None,
                    help='核对外部文本里的指纹声称(缺时点判不合格)')
    sub = ap.add_subparsers(dest='cmd')
    for name in ('copy', 'verify'):
        p = sub.add_parser(name)
        p.add_argument('src')
        p.add_argument('dst')
        p.add_argument('--src-server', dest='src_server', default='local', choices=['local', 'central'])
        # ★ v1.0.4（按 HR 四级阶梯的「待触发门须改默认：安全路径必须是默认路径」）
        #   默认原为 local ⇒ **默认路径产出单侧写入**（正是本网络实测 182/204 单写本机的同款缺陷）。
        #   现默认 `both`：单写必须**显式** `--to local` 声明，不再是默认。
        p.add_argument('--to', default='both', choices=['local', 'central', 'both'])
        p.add_argument('--no-preflight', dest='no_preflight', action='store_true',
                       help='明示跳过默认预检(版本声明位/语义锚点)；越权须明示，同 --force 形态')
        # copy 与 verify 都要: verify 也会读到源值并打印差异，同样是扩散面
        p.add_argument('--allow-secret-fields', dest='allow_secret_fields', action='store_true',
                       help='明示越过敏感字段硬拒(凭据类键不该复制；越权留痕且输出脱敏)')
        if name == 'copy':
            p.add_argument('--from', dest='from_agent', default=None)
            p.add_argument('--dry-run', dest='dry_run', action='store_true')
            p.add_argument('--force', action='store_true')
    p_ref = sub.add_parser('refcheck', help='核对引用字段是否真实存在(字段名级引用，不输出值)')
    p_ref.add_argument('key')
    p_ref.add_argument('field', nargs='+', help='字段名或点号路径，如 answers / body.items')
    p_ref.add_argument('--src-server', dest='src_server', default='local', choices=['local', 'central'])
    p_ref.add_argument('--no-preflight', dest='no_preflight', action='store_true')
    args = ap.parse_args(argv)
    if args.version:
        print(('{"tool": "bb-copy", "version": "' + VERSION + '", "source": "VERSION 常量"}')
              if JSON_OUT else ('bb-copy ' + VERSION + ' (VERSION 常量为唯一来源)'))
        return 0
    if args.check:
        return selfcheck()
    if args.claim:
        # ★ 明鉴硬结论「**契约 + 待触发 = 契约不生效**」的处置：把「契约」提到**声称生成的那一刻**自动触发。
        #   契约只在人跑 --check 时才生效 ⇒ 声称仍可能带着过期状态出门；现改为：
        #   **卡与制品不同步时，本工具拒绝生成声称**(exit 8)，除非 --no-preflight 明示越权。
        #   ⇒ 声称路径上「产出过期声明」这件事变成**不可表达**（HR 阶梯第④档），不再依赖谁记得跑判据。
        if not getattr(args, 'no_preflight', False):
            _fpok, _fpwhy = _fingerprint_ok()
            if _fpok is not True:
                print('[claim] X 拒绝生成声称：卡与制品不同步 —— ' + str(_fpwhy))
                print('      依据=明鉴「契约+待触发=契约不生效」：契约必须在**声称生成时**触发，而不是等人跑 --check')
                print('      请先同步卡内指纹；确需带过期状态出门请加 --no-preflight（明示越权，留痕）')
                log('claim REFUSED (card out of sync): ' + str(_fpwhy)[:80])
                return 8
        line = make_claim(args.with_check)
        print(line)
        if JSON_OUT:
            print(json.dumps({'tool': 'bb-copy', 'cmd': 'claim', 'claim': line, 'ok': True}, ensure_ascii=False))
        return 0
    if args.report:
        _line = make_report()
        print(_line)
        if JSON_OUT:
            print(json.dumps(dict(x.split('=', 1) for x in _line.split(' ', 1)[1].split(' ') if '=' in x),
                              ensure_ascii=False))
        return 0
    if args.heartbeat_age:
        return cmd_heartbeat_age(args)
    if args.stamp:
        return cmd_stamp(args)
    if args.stale_report:
        sz, md, mt = _local_fingerprint()
        ind = _independent_fingerprint()
        fpok, fpwhy = _fingerprint_ok()
        okv, detv = _anchors_ok()
        # ★ 自锁死修复：producer 必须是**与 --from 完全一致**的规范身份。
        #   原写 'external-link-agent (bb-copy)' 而 --from 是 'external-link-agent' ⇒ bb-write 归属守卫
        #   按原串比较（无 session-<8hex> 令牌）⇒ **后续自己更新自己的心跳卡被 exit 6 拦住**。展示名另立 writer 字段。
        rep = {'producer': 'external-link-agent', 'writer': 'bb-copy v' + VERSION,
               'subject': 'bb-copy 卡/制品一致性心跳（让「未执行」态对外可见）',
               # ★ A52（F2 自然实验）：此处原为 `now().isoformat()` ⇒ **naive（无偏移）**，
               #   而本工具自己的 `_ts_finding()` 正把「无时区偏移」列为手工时点特征 ⇒ **自己违规**。
               #   `astimezone()` 补本地偏移（+08:00），使读者无需猜写入者时区即可定位瞬间。
               'ts': datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
               'ts_epoch': str(int(datetime.datetime.now().timestamp())),
               'version': VERSION, 'size': str(sz), 'md5': md, 'mtime': str(int(mt)),
               'independent_impl': (str(ind[0]) + '/' + ind[1] + '/' + str(ind[2])) if ind else 'unavailable',
               'card_fingerprint_in_sync': bool(fpok is True), 'card_note': str(fpwhy)[:200],
               'anchors_ok': okv if okv != 'skipped' else 'skipped', 'anchors_note': str(detv)[:200],
               '依据': '明鉴：「契约 + 待触发 = 契约不生效」；三态除恒真/恒假外还有「**未执行**」⇒ 定时上报可消除未执行态。'}
        r = subprocess.run(['python3', BB_WRITE, 'put', 'data/external-link/bb-copy-staleness',
                            '--json', json.dumps(rep, ensure_ascii=False), '--from', 'external-link-agent',
                            '--server', 'both'], capture_output=True, text=True)
        print('[stale-report] 写入 exit=' + str(r.returncode) + ' | ' + (r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ''))
        print('[stale-report] 同步=' + str(fpok is True) + ' | ' + str(fpwhy)[:120])
        return 0 if fpok is True else 4
    if args.verify_claim is not None:
        _v, det = verify_claim(args.verify_claim)
        for _ln in det:
            print('[verify-claim] ' + _ln)
        if JSON_OUT:
            print(json.dumps({'tool': 'bb-copy', 'cmd': 'verify-claim', 'verdict': _v,
                              'verdict_label': {0: 'pass', 3: 'unverifiable', 4: 'fail'}[_v],
                              'details': det}, ensure_ascii=False))
        return _v
    if args.cmd == 'copy':
        return cmd_copy(args)
    if args.cmd == 'verify':
        return cmd_verify(args)
    if args.cmd == 'refcheck':
        return cmd_refcheck(args)
    ap.print_help()
    return 2


if __name__ == '__main__':
    sys.exit(main())
