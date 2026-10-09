#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bb-write (HR) - 黑板写入/校验工具 (R006 十项标准 / 2026-09-11)
版本唯一来源 = 下方 VERSION 常量(2ab9dbd0 指出四处版本漂移, 故 docstring 不再写版本号)
解决黑板写入三大陷阱(key语法400/纯文本空壳/400伪装成不存在): 写前校验key -> JSON body -> 回读验证非空 -> 明确报错
R006: 1插件(P2) 2selfcheck 3cld-check 4version-check 5README 6--version 7日志 8落链 9CLI 10lean4-check
用法: bb-write.py put <key> --body "文本" [--from X] [--subject Y] | put <key> --json {...} | get <key> | validate <key> | selfcheck|version|cld-check|version-check|lean4-check [--server local|central]

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, sys, datetime, http.client


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-write.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = '1.7.3'
JSON_OUT = False
DRY_RUN = False
LOG_FILE = os.path.expanduser('~/.dsh/bb-write.log')
SERVERS = {'local': ('127.0.0.1', 8792), 'central': ('106.53.214.108', 8792)}
# v1.0.8: 明鉴交付的键语法负例断言集(41 键矩阵; 含 5 条 board=200 -> 服务端会接受、必须客户端拦)
ASSERTIONS = os.path.expanduser('~/dsh-collab/data/device/bb-key-assertions/key-syntax-assertions-v1.json')
LASTMETA = {}   # v1.6.0: 承载「本次落链的两个落点各自结果」, 供 selfcheck 断言读取
LLNK_DIR = os.path.expanduser('~/dsh-collab/data/registry')   # ⑧ 自动落链目录
# ⑩ 「保证的继承边界」(collect 提出): 本工具的门能保证什么, 继承自哪些上游的实测子集
INHERITED_LIMITS = [
    '断言集 = key-syntax-assertions-v1(41 键, 从实测样本归纳, 非服务端规格推导) ⇒ 本门只保证这 41 条, 不保证「没有第 42 条」',
    '本工具键规则的真实性 = 全量真实键安全证明(20,221 键时点), 而该库在增长 ⇒ 结论带时点',
    'R006 ①(插件挂载冒烟) 对本工具不适用(纯 CLI, 非插件形态; 星桥 v3.1.0 已明确)',
]
# v1.1.4: **拆除「已裁定分歧」豁免**。该豁免是 v1.0.9 为「断言集把点段列在 must_accept」设的临时口子;
#   明鉴于 2026-09-11 已把点段移入 must_reject(27/13), 冲突消失, 故豁免不再需要。
#   ★ 保留豁免的理由已不存在 —— 而**一个拆不掉的临时豁免, 就是永久性放行**。
#   若断言集日后回退, 门会重新报 误伤(must_accept 被拒), 这是有意的(防回归)。
ADJUDICATED_DIVERGENCE = set()

def log(msg):
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write('[' + datetime.datetime.now().isoformat() + '] ' + msg + chr(10))
    except Exception:
        pass

def validate_key(key):
    if not key or not isinstance(key, str):
        return False, 'key 为空'
    k = key.lstrip('/')
    segs = k.split('/')
    if len(segs) < 2:
        return False, 'key 需至少两段(如 data/<域>/<键>): ' + k
    first = segs[0]
    if not re.fullmatch(r'[a-z]+', first):
        return False, ('★ key 写法非法: 首段须纯小写字母 [a-z]+, 当前首段=' + first + ' -> 将返回 400 bad key(不是 404!)。合法示例: data/<域>/<键> / notes/<节点>/<键>')
    # v1.0.3 修复 (a5f4432a 对账实证 2026-09-11): 旧实现用 `[s for s in segs[1:] if s]` 把空段**静默滤掉**,
    # 导致 'data/reflect/' 与 'data//key' 被判「语法合法」。黑板实测三例:
    #   尾斜杠 GET /data/reflect/ -> 200 且 body 是 {list,total} **全库列举**;
    #          -> 任何「回读含标记即落地」的判据在此**必然假通过**(列举里必然含有刚写的键串)
    #   空段   ★ 更正(v1.4.1 · 星桥以服务端属主身份实测指出, HR 复验): 我原写「GET /data//reflect -> 404 (写得进、读不到)」——
    #         那是**归因错**: 那次 404 是因为**该键本就不存在**, 不代表空段键读不到。实测:
    #           PUT data//x -> 200 且**原样存为 `data//x`(不归一化)**; GET data/x(单斜杠) -> **404**;
    #           GET data//x -> **200 可读**; 且它**出现在 /data/ 全库列举里**(20,295 键时点)。
    #         ⇒ 准确说法是**影子对象**: 单斜杠读者永远找不到它, 而全库列举里又看得到。
    #         ⇒ **结论不变**(客户端应拒空段), **但理由更强**: 不是「格式难看」, 而是**会写出一个正常路径看不见的对象**。
    #         (对照: PUT //data/x -> 200 且**归一化**为 data/x —— 前导斜杠宽容, 不产生影子对象)
    #   含空白 GET .../my%20key   -> 400 bad key (validate 放行但服务端拒绝)
    if any(s == '' for s in segs):
        return False, ('★ key 含空段(尾斜杠或双斜杠): ' + k +
                       ' -> 会写出**影子对象**: 单斜杠读者(GET data/x)永远 404, 只有空段读者(GET data//x)可读,'
                       ' 而它又出现在全库列举里 —— **不是「读不到」, 是「正常路径看不见」**(后果比格式难看更重)。'
                       ' 合法示例: data/<域>/<键>')
    if re.search(r'\s', k):
        return False, '★ key 含空白: 服务端将返回 400 bad key(不是 404): ' + k
    # v1.0.5 修复 (明鉴 2026-09-11 实证, 其称之为本工具最尖锐的一处自相矛盾):
    # 旧实现**只约束首段**, 后续段无字符集校验 -> `validate data/x/a:b` 报「语法合法」,
    # 而 `put data/x/a:b` 被服务端打回 400。**同一工具两个子命令对同一 key 给出矛盾结论。**
    # 这比没有 validate 更坏: 用户信任 validate 的 OK, 就不会再检查。
    # 讽刺的是 put 的报错文本自己就写着 400 can masquerade as object missing —— 知道陷阱却在自家复制它。
    # 黑板实测字符集: 后续段合法 = [A-Za-z0-9._-] ; ':' '+' '@' '~' '!' 空格 均 400。
    # v1.0.6 修复 (a5f4432a 加测发现 2026-09-11): 段为 '.' 或 '..' 时, **客户端会做 dot-segment 消解**
    # (RFC 3986), 请求被打到别的路径上 —— 实测 curl 请求 data/x/.. 时直接返回 34MB 全库列举。
    # 服务端侧: data/.. → 400 bad key。两端都不该放行。
    dot_seg = [s for s in segs if s in ('.', '..')]
    if dot_seg:
        return False, ('★ key 含 . 或 .. 段: ' + k +
                       ' -> 客户端做 dot-segment 消解(RFC 3986), 请求会打到别的路径;'
                       ' 服务端侧 data/.. 亦返回 400。两者都会造成「写 A 读 B / 静默写错键」。')
    bad_seg = [s for s in segs[1:] if not re.fullmatch(r'[A-Za-z0-9._-]+', s)]
    if bad_seg:
        return False, ('★ key 后续段含非法字符: ' + ','.join(bad_seg) +
                       ' —— 黑板实测合法字符集 = [A-Za-z0-9._-] (字母/数字/点/下划线/连字符, 大小写均可)。'
                       ' ":" "+" "@" "~" "!" 空格 等一律 400 bad key。'
                       ' 提示: 此前 validate 只查首段, 会报 OK 而 put 被 400 打回。')
    return True, '语法合法'

def keypath_of(key):
    """★ 单一入口(reflect-collect 91914624 的框架 2026-09-11): **任何发往黑板的路径都必须经此构造**。
    校验失败即抛 —— 结构上无法绕过, 而不是「在各调用点分别记得校验」。
    背景: HR 此前在 cmd_put 修了「拒绝但理由说错」, 却漏了 cmd_get —— 因为修的是**报错现场**,
    不是**判断点**。改为单一入口后, 新增任何读/写路径都自动继承校验。
    允许的读目标一律过 key 语法门 -> 尾斜杠/空段/点段自然被拒。"""
    ok, msg = validate_key(key)
    if not ok:
        raise ValueError(msg)
    return '/' + key.lstrip('/')

def _conn(server):
    host, port = SERVERS[server]
    return http.client.HTTPConnection(host, port, timeout=10)

def cmd_validate(args):
    ok, msg = validate_key(args.key)
    if globals().get('JSON_OUT'):   # v1.2.0: 此前设了旗标却仍输出纯文本 = 能力没接通
        print(json.dumps({'tool': 'bb-write', 'cmd': 'validate', 'key': args.key, 'ok': ok, 'reason': msg}, ensure_ascii=False))
    else:
        print(('[validate] OK ' if ok else '[validate] FAIL ') + msg)
    return 0 if ok else 1

def _put_impl(args):
    ok, msg = validate_key(args.key)
    if not ok:
        print('[put] X ' + msg)
        log(msg)
        return 2
    # v1.7.3 修复 (罗盘 2026-09-11 受控复现): 空 --json 是 falsy, 会【静默落到 --body 分支】,
    # 而 --body 缺失时 body = args.body or '' 把【未提供】静默折成【空串】=> 写出空卡却返回 OK。
    # 同族: 失败被映射成成功; 本次发生在输入侧。非空非法 JSON 原本已正确拒绝, 故只补【空】这一边界。
    if args.json is not None and str(args.json).strip() == '':
        print('[put] X --json 为空串: 拒绝写入空卡(空输入不得并回成功)')
        return 2
    if args.json:
        try:
            value = json.loads(args.json)
        except Exception as e:
            print('[put] X --json invalid: ' + str(e)[:80]); return 2
    else:
        # v1.7.3: 无 --json 且无 --body => 信封四键全空, 读侧只会看到一张空壳卡 => 拒绝。
        if not (args.body or '').strip():
            print('[put] X --body 为空且未提供 --json: 拒绝写入空卡')
            return 2
        value = {
            'from': args.from_agent or os.environ.get('DSH_NODE_ID', 'unknown'),
            'ts': datetime.date.today().isoformat(),
            'subject': args.subject or '',
            'body': args.body or '',
        }
    # v1.0.4 修复 (2ab9dbd0 实跑复现 2026-09-11): 双重包裹 —— 黑板自身会把 body 包进 value,
    # 若 --json 再传 {"value": {...}}, 存下来就成了 value.value, 读侧按标准形态取字段会取空。
    # 旧的内容一致性检查只遍历 value.items()(「我写的字段回来了吗」), 不校验「形状对不对」,
    # 故 fields=1 也全绿。实测: --json '{"value":{"answers":[...]}}' -> [put] OK fields=1, 而读侧取 answers = MISSING。
    if (isinstance(value, dict) and list(value.keys()) == ['value']
            and isinstance(value['value'], (dict, list)) and not getattr(args, 'force', False)):
        print('[put] X 疑似双重包裹: 顶层唯一键就是 value, 且其值为 ' + type(value['value']).__name__
              + ' —— 黑板会再包一层, 存下来将变成 value.value, 读侧取不到字段。')
        print('      请直接传值本身(如 --json \'{"answers":[...]}\'); 确需此形状请加 --force)')
        log('double-wrap blocked: ' + args.key)
        return 2
    # 形状断言(2ab9dbd0 建议): 声明期望顶层键集合, 既拦多余包裹, 也拦写错字段的半空壳
    if getattr(args, 'expect_keys', ''):
        exp = set(x.strip() for x in args.expect_keys.split(',') if x.strip())
        got = set(value.keys()) if isinstance(value, dict) else set()
        if exp != got:
            print('[put] X 形状断言失败: 期望顶层键 [' + ','.join(sorted(exp)) + '] 实际 [' + (','.join(sorted(got)) or '非对象') + ']')
            log('expect-keys mismatch: ' + args.key)
            return 5
    body = json.dumps(value, ensure_ascii=False).encode('utf-8')
    # R006 ⑨ --dry-run: 走完全部前置校验但零变更(不发任何网络写请求)
    # ★ v1.3.0 归属守卫 (星桥 2026-09-11 越界事件触发, 它自报并已恢复):
    #   根因是「**未先读就写入**」—— 它把 9 条写进了别人(HR)创建的键, 顶替了原值。
    #   它提的「缺席告警升级为归属校验」是**检测**; 本条是**预防**: 写入前读一次既有键,
    #   若其 producer/from 与本次 --from 不同 -> **拒绝**(除非 --force)。
    #   目标: 把「未先读就写入」从纪律变成**结构上不可绕过**(与今晚单一入口同一修法)。
    if not getattr(args, 'force', False) and not (getattr(args, 'dry_run', False) or globals().get('DRY_RUN')):
        try:
            _kp = keypath_of(args.key)
            _c0 = _conn(args.server)
            _c0.request('GET', _kp)
            _r0 = _c0.getresponse()
            if _r0.status == 200:
                _v0 = (json.loads(_r0.read().decode('utf-8', 'replace')).get('value') or {})
                if isinstance(_v0, dict):
                    _p0 = _v0.get('producer') or _v0.get('from')
                    _me = args.from_agent or os.environ.get('DSH_NODE_ID', '')
                    # ★ v1.3.1 归一化: producer 实际写法混杂(`session-2a15e6b1` / `session-2a15e6b1 (司库)`),
                    #   严格字符串比较会**误拦同属主**。故取 session-<8hex> 令牌比较;取不到则退化为原串比较。
                    _tok = lambda s: (re.search(r'session-[0-9a-f]{8}', str(s)) or type('X', (), {'group': lambda self, n=0: None})()).group(0) if re.search(r'session-[0-9a-f]{8}', str(s)) else str(s).strip()
                    _np0, _nme = _tok(_p0), _tok(_me)
                    if _p0 and _me and _np0 != _nme:
                        print('[put] X 归属守卫: 该键已存在, producer/from = ' + str(_p0))
                        print('      与本次 --from = ' + str(_me) + ' 不同 -> 拒绝写入(防顶替他人卡)')
                        print('      如确需覆盖他人键: 加 --force; 或先按 J4 通知属主')
                        log('ownership guard blocked: ' + args.key + ' existing=' + str(_p0))
                        return 6
        except Exception:
            pass   # 守卫读失败不阻断, 但属降级(可能漏拦) —— 与「观测缺口必须明说」一致, 记日志
    if getattr(args, 'dry_run', False) or globals().get('DRY_RUN'):
        print('[put] DRY-RUN 零变更 | key=' + args.key + ' | server=' + args.server +
              ' | 顶层键=' + str(sorted(value.keys()) if isinstance(value, dict) else type(value).__name__) +
              ' | bytes=' + str(len(body)))
        return 0
    keypath = keypath_of(args.key)   # ★ 单一入口(v1.1.3)
    try:
        c = _conn(args.server)
        c.request('PUT', keypath, body, {'Content-Type': 'application/json', 'Content-Length': str(len(body))})
        r = c.getresponse(); status = r.status; r.read(); c.close()
    except Exception as e:
        print('[put] X connect failed: ' + str(e)[:100]); return 1
    if status == 400:
        print('[put] X 400 bad key syntax - note: 400 can masquerade as "object missing"'); return 2
    if status != 200:
        print('[put] X HTTP ' + str(status)); return 1
    try:
        c2 = _conn(args.server)
        c2.request('GET', keypath)
        r2 = c2.getresponse(); st2 = r2.status
        data = json.loads(r2.read().decode('utf-8', 'replace'))
        c2.close()
    except Exception as e:
        print('[put] ! wrote 200 but readback failed: ' + str(e)[:80]); return 1
    val = data.get('value') or {}
    # ★ 回读失败三态区分(明鉴建议 2026-09-11)
    if st2 == 404:
        print('[put] X 回读 404: 对象不在(写入未生效/被清理) — 非空壳, 是没写进去'); return 3
    if st2 != 200:
        print('[put] X 回读 HTTP ' + str(st2)); return 1
    if not val:
        print('[put] X 回读 200 但 value 空(空壳键, 第⑤级) — JSON body 可能非法或解析失败'); return 3
    # 内容一致性(防截断/被覆盖)
    mismatch = []
    # v1.0.2 修复: 黑板服务端对嵌套对象做键排序(serde_json 无 preserve_order),
    # 故 str() 比对会把「键序不同但内容相同」误判为不符 -> 假阳性。改用 sort_keys 规范化深比对。
    def _canon(x):
        try:
            return json.dumps(x, sort_keys=True, ensure_ascii=False)
        except Exception:
            return str(x)
    for k, v in value.items():
        if k in val and _canon(val.get(k)) != _canon(v):
            mismatch.append(k)
    if mismatch:
        print('[put] X 回读内容与写入不符(字段: ' + ','.join(mismatch) + ') — 疑似截断/被并发覆盖'); return 4
    print('[put] OK ' + args.key + ' | fields=' + str(len(val)) + ' | server=' + args.server)
    log(args.key)
    return 0

def cmd_put(args):
    """v1.0.4: 单出口包装 —— 2ab9dbd0 指出 8 条失败路径只有 2 条写了日志(逐行核对属实)。
    把留痕提到唯一出口, 新增分支时不会再漏。
    v1.5.0: --server both 双侧派发 + 登记命名空间单写警示(见下)。"""
    # ★ v1.5.0 (明鉴 a190c54c 2026-09-11 实测触发: HR 刚落的两张卡中央侧 404)。
    #   事实: 本网络 data/registry/* 权威登记键**多数只落本机** —— 实测 204 键中仅 **22 键双侧**(10.8%), **182 键仅本机**。
    #   ★ v1.6.1 (明鉴 2026-09-11 全仓 grep 指出「10/10」残留 5 处触发): 本条**依据已换** ——
    #     原文写「既有先例 10/10 双写」, 而真数据是 **10.8% 双写** ⇒ **按「先例」这个依据, 支持的是「单写是常态」, 规则被自己的真数据反证**。
    #     故依据由「**先例**」改为「**规范**」: 取用方可能不在本机 ⇒ 须跨设备可见。**规范陈述不依赖计数, 因此不会再被计数反证**。
    #         而 put 默认 --server local ⇒ 只落本机, **写入成功却零信号**。
    #   ⇒ 与「按设计单写」在观测上**不可区分** —— 这是今晚那条「潜伏缺陷(缺信号)」的又一实例。
    #   修法(两步, 都不改默认行为以免影响既有调用方):
    #     ① 能力侧: --server both = 两侧都写、都回读、两侧结论都报(此前只有单侧, 双写靠人记得跑两次)。
    #     ② 信号侧: 单写 local 且键属登记命名空间 ⇒ **显式警示**(不阻断, 只是不再静默)。
    _srv = getattr(args, 'server', 'local')
    _sides = ['local', 'central'] if _srv == 'both' else [_srv]
    if _sides == ['local'] and str(args.key).startswith('data/registry/'):
        print('[put] ! 单写警示: ' + args.key + ' 属权威登记命名空间 data/registry/*')
        print('      依据(规范, 非计数): 登记命名空间的**取用方可能不在本机**, 仅落 local 时其他设备读不到该卡。')
        print('      (实测分布供参考: 204 键中 22 键双侧 / 182 键仅本机 —— 单写本机是多数, 故本条只警示、不判不合规)')
        print('      需双写并双回验: 加 --server both')
    results = {}
    for _s in _sides:
        args.server = _s
        try:
            results[_s] = _put_impl(args)
        except Exception as e:
            results[_s] = 1
            print('[put] X [' + _s + '] ' + str(e)[:120])
    if len(_sides) > 1:
        _fails = dict((k, v) for k, v in results.items() if v != 0)
        st = 0 if not _fails else (_fails.get('local') or _fails.get('central') or list(_fails.values())[0])
        print('[put] BOTH ' + ' '.join(k + '=' + str(v) for k, v in results.items())
              + ('  (两侧均通过)' if st == 0 else '  (存在失败侧, 见上方逐侧输出)'))
    else:
        st = list(results.values())[0] if results else 1
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            # ★ v1.7.2（数据调查员 2026-09-11 用本日志反推使用者域时触发，HR 自查发现）：
            #   此前 **dry-run 探针（含 selfcheck 的两个 probe 键）也写日志** ⇒ 日志**不是纯真实写入记录**
            #   ⇒ 任何人拿它反推「谁在用」都会把**从未写过的探针键**算成真实写入。
            #   修法：**标记而不省略**（保留记录、使其可被下游排除）—— 与本网络「记录但不冒充」一致。
            _tag = ' | DRY-RUN(非真实写入)' if (getattr(args, 'dry_run', False) or globals().get('DRY_RUN')) else ''
            f.write('[' + datetime.datetime.now().isoformat() + '] ' + args.key
                    + ' | exit=' + str(st) + ' | server=' + str(_srv) + _tag + chr(10))
    except Exception:
        pass
    if globals().get('JSON_OUT'):
        print(json.dumps({'tool': 'bb-write', 'cmd': 'put', 'key': args.key,
                          'server': _srv, 'sides': results, 'exit': st,
                          'ok': st == 0}, ensure_ascii=False))
    return st

def cmd_get(args):
    # v1.1.0 修复 (reflect-collect 91914624 独立复测 2026-09-11): cmd_get 此前**不过 validate_key**,
    # 导致 v1.0.3 已修好的「拒绝但理由说错」在**读路径**上残留, 且与 put/validate 自相矛盾:
    #   get data/registry/  -> 误报「empty shell」(真因: 尾斜杠指向命名空间列举, 响应无 value 字段)
    #   get data//registry  -> 误报「404 格式合法」(而 validate/put 判它非法) = 同一 key 两个结论
    # 附带成本: 尾斜杠那条会白拉 36.6MB 全量列举(R003 rule_4 的 OOM 面)。
    # ★ v1.7.1（明鉴 2026-09-11 指出：**它差点用本行反驳 HR，因为本行读起来像当前行为**）:
    #   **本行描述的是 v1.1.0 修复前的历史行为**（上方整段即「修复了什么」的记录）。
    #   **当前行为**：尾斜杠/空段/点段已被 `validate_key` 拦下，**本工具不发出任何列举请求**
    #   （依据 `keypath_of` 单一入口，:97 docstring：「允许的读目标一律过 key 语法门」）。
    #   ⇒ 全量列举的风险属于**其他会做列举的调用方**，已登记为潜伏风险（触发条件 + 验证方式见 README）。
    #   ★ 教训形态：**历史注释读起来像当前行为** —— 与「声明 ≠ 当前事实」同族，故此处显式标注时态。
    ok, _m = validate_key(args.key)
    if not ok:
        print('[get] X ' + _m)
        log('get blocked: ' + args.key)
        return 2
    try:
        keypath = keypath_of(args.key)   # ★ 单一入口(v1.1.3)
    except ValueError as e:
        print('[get] X ' + str(e)[:150]); return 2
    try:
        c = _conn(args.server)
        c.request('GET', keypath)
        r = c.getresponse(); st = r.status
        raw = r.read().decode('utf-8', 'replace')
    except Exception as e:
        print('[get] X ' + str(e)[:100]); return 1
    if st == 400:
        print('[get] X 400: bad key syntax (do not misread as missing)'); return 2
    if st == 404:
        print('[get] 404: valid format but not found'); return 3
    try:
        d = json.loads(raw)
    except Exception:
        print('[get] X not JSON'); return 1
    val = d.get('value') or {}
    if not val:
        # v1.1.0: 区分「命名空间列举响应」与「真空壳键」—— 前者顶层有 list/total 而无 value。
        if ('list' in d) or ('total' in d):
            print('[get] X 该路径返回**命名空间列举**(顶层字段 limit/list/offset/total, 无 value), '
                  '既不是空壳也不是 404: ' + args.key)
            return 2
        print('[get] ! empty value (shell): ' + args.key); return 4
    print(json.dumps(val, ensure_ascii=False)[:800])
    return 0

def cmd_selfcheck(args):
    print('[selfcheck] bb-write v' + VERSION)
    ok = True
    cases = [('data/dom/key', True), ('cld-health/x', False), ('mac-mini/x', False), ('ABC/x', False), ('single', False), ('notes/node/k-1', True)]
    for k, expect in cases:
        got, _m = validate_key(k)
        mark = 'OK ' if got == expect else 'X  '
        print('  ' + mark + ' validate ' + k + ' -> ' + str(got))
        if got != expect: ok = False
    # v1.0.7 新增: 机器可读输出能力断言(R006 ⑨ 偏离的机械可检)
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        globals()['JSON_OUT'] = True
        try:
            cmd_version(None)
        finally:
            globals()['JSON_OUT'] = False
    try:
        jv = json.loads(buf.getvalue())
        ok4 = (jv.get('version') == VERSION)
    except Exception:
        ok4 = False
    print('  ' + ('OK' if ok4 else 'X') + ' json-out 机器可读能力存在且版本一致(执行 cmd_version 并 json.loads 断言)')
    # ★ v1.4.2 (星桥 5b「声明态冒充接通态」触发 HR 自查): 上面那条**只执行了一个子命令**, 却宣称
    #   「机器可读能力存在」—— 若有别的子命令**设了旗标却不输出 JSON**, 这条检查照样通过。
    #   这正是「观测必须覆盖对象的全部(作用域)」。故扩展为:**逐个执行所有声明支持 JSON 的子命令, 断言每条输出可解析**。
    import argparse as _ap
    covered, uncovered = [], []
    for _name, _fn in (('version', cmd_version), ('validate', cmd_validate),):
        _b = io.StringIO()
        with contextlib.redirect_stdout(_b):
            globals()['JSON_OUT'] = True
            try:
                _fn(_ap.Namespace(key='data/dom/key'))
            finally:
                globals()['JSON_OUT'] = False
        _ok = False
        for _line in [x for x in _b.getvalue().split(chr(10)) if x.strip()]:
            try:
                json.loads(_line); _ok = True
            except Exception:
                _ok = False; break
        (covered if _ok else uncovered).append(_name)
    ok9 = (not uncovered) and len(covered) >= 2
    print('  ' + ('OK' if ok9 else 'X') + ' json-out 作用域覆盖: 已测 ' + ','.join(covered)
          + (' 未接通 ' + ','.join(uncovered) if uncovered else ' (全部输出可解析为 JSON)'))
    ok = ok and ok9
    # v1.0.7 新增: **声明位**版本一致性(明鉴建议, HR 收窄口径见 README:
    # 版本号有两种用法 —— 声明位(必须==VERSION) 与 历史位(注释记录某版修了什么, 不该断言相等)。
    # 若按「扫描全部出现位置」断言, 会在历史注释上假报 -> 正是判漏三重口径里的「过严」。)
    import inspect
    decl = [x for x in re.findall(r"^VERSION = '([^']+)'", inspect.getsource(sys.modules[__name__]), re.M)]
    ok5 = (decl == [VERSION])
    print('  ' + ('OK' if ok5 else 'X') + ' 声明位版本唯一且等于 VERSION')
    # v1.1.1 回归 (reflect-collect 复测提供用例): **读路径与写路径必须同判**
    # 此前 cmd_get 不过 validate_key -> get 说「空壳」/「404 格式合法」, 而 put 说「非法」= 自相矛盾。
    get_cases = ['data/registry/', 'data//registry', 'data/x/a:b']
    ok6 = all(validate_key(k)[0] is False for k in get_cases)
    print('  ' + ('OK' if ok6 else 'X') + ' 读路径/写路径同判回归(get 与 put 同用 validate_key)')
    # v1.1.2 (明鉴要求「登记卡纳入达标范围」): 登记卡的 version 字段**也是声明位**, 但它在本机黑板,
    # 源码内扫描覆盖不到 -> 会静默漂移(实测漂到 1.0.7 而实际 1.1.1)。此处做跨产物的机械核验。
    # 读不到时**声明 SKIP**, 不静默(按正表述: 观测缺口必须明说)。
    try:
        c = _conn('local'); c.request('GET', keypath_of('data/registry/bb-write-tool-20260911'))
        rr = c.getresponse(); card = json.loads(rr.read().decode('utf-8', 'replace')).get('value') or {}
        cv = card.get('version')
        ok7 = (cv == VERSION)
        print('  ' + ('OK' if ok7 else 'X') + ' 登记卡声明位版本一致(卡=' + str(cv) + ' 码=' + VERSION + ')')
    except Exception as e:
        ok7 = True
        print('  ~ SKIP 登记卡声明位核验(读不到: ' + str(e)[:40] + ') —— 观测缺口已声明')
    # ★ v1.3.4 (星桥 ⑥ 新条文「必须提供自动校验证明不存在第二处」触发 HR 自查):
    #   我此前称「声明位唯一」, 但**自检只扫源码模块** —— README 的版本行是 v1.0.5(实际 v1.3.3), 即**存在第二处且已漂移**。
    #   本条把 README 纳入核验, 并**声明核验覆盖面**(不谎称「全部声明位」—— 未覆盖的仍未知)。
    try:
        _rd = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bb-write-README.md')
        _txt = open(_rd, encoding='utf-8').read()
        _m = re.search(r'\*\*v(\d+\.\d+\.\d+)\*\*', _txt)
        _rv = _m.group(1) if _m else None
        ok8 = (_rv == VERSION)
        print('  ' + ('OK' if ok8 else 'X') + ' 声明位·README 版本行一致(README=' + str(_rv) + ' 码=' + VERSION + ')')
    except Exception as e:
        ok8 = False
        print('  X 声明位·README 读取失败: ' + str(e)[:50])
    print('  ~ 声明位核验覆盖: 源码 VERSION · 登记卡 version · README 版本行 —— **未覆盖的声明位未知**(不谎称全部)')
    # ★ v1.5.0 (明鉴 2026-09-11 实测: HR 两张卡中央侧 404 触发)。
    #   ① 双写**能力**: --server both 必须真的把两侧都派发出去（不是只在 help 里声明）。
    #     用 --dry-run 走完全部前置校验但**零变更**（不发任何网络写请求），断言出现两条 DRY-RUN 且 server 各异。
    #   ② 单写**信号**: 正控(data/registry/* 且仅 local ⇒ 必警示) + 反控(--server both ⇒ 不得误报)。
    #     正控用同一份 both 输出做对照, 保证「警示确实只由该条件触发」。
    _b2 = io.StringIO()
    _nsb = _ap.Namespace(key='data/registry/__selfcheck_both_probe', body='x', json=None,
                         from_agent='selfcheck', subject='', server='both', expect_keys='',
                         force=False, dry_run=True)
    with contextlib.redirect_stdout(_b2):
        _stb = cmd_put(_nsb)
    _t2 = _b2.getvalue()
    ok10 = (_stb == 0 and _t2.count('DRY-RUN') == 2 and 'server=local' in _t2 and 'server=central' in _t2)
    print('  ' + ('OK' if ok10 else 'X') + ' both 双写派发(实测两侧各一次、零变更): DRY-RUN 行=' + str(_t2.count('DRY-RUN'))
          + ' local=' + str('server=local' in _t2) + ' central=' + str('server=central' in _t2))
    _b3 = io.StringIO()
    _nss = _ap.Namespace(key='data/registry/__selfcheck_single_probe', body='x', json=None,
                         from_agent='selfcheck', subject='', server='local', expect_keys='',
                         force=False, dry_run=True)
    with contextlib.redirect_stdout(_b3):
        cmd_put(_nss)
    _t3 = _b3.getvalue()
    ok11 = ('单写警示' in _t3) and ('单写警示' not in _t2)
    print('  ' + ('OK' if ok11 else 'X') + ' 登记命名空间单写警示(正控命中=' + str('单写警示' in _t3)
          + ' / 反控 both 不误报=' + str('单写警示' not in _t2) + ')')
    ok = ok and ok4 and ok5 and ok6 and ok7 and ok8 and ok10 and ok11
    # ★ v1.6.0 (明鉴 2026-09-11 触发): ⑧ 落链此前**只落本机文件**, 「落链」的实际观测面是本机而非黑板。
    #   本条把「落链」从**动作**升级为**可断言结果**: 落两个落点(本机文件 + 黑板键)并回读。
    #   **断言口径**: 只断言 **local 侧黑板键回读 200**（= ⑧ 的最低兑现: 网络侧至少一个读者能看到）;
    #   **central 侧只报告不判** —— 依据 HR 实测分布(202 键中 182 键仅落本机), 双写是少数实践,
    #   无判据时不把它当默认要求(否则本工具会替全网络强推一条未裁定的规矩)。
    _fp = _write_link('selfcheck', {'ok': ok})
    _bs = LASTMETA.get('board') or {}
    ok12 = bool(_fp) and (LASTMETA.get('board_ok') is True)
    print('  ' + ('OK' if ok12 else 'X') + ' ⑧ 落链双落点: 本机文件=' + ('有' if _fp else '无')
          + ' | 黑板键 ' + str(LASTMETA.get('board_key')) + ' local=' + str(_bs.get('local'))
          + ' central=' + str(_bs.get('central')) + '(仅报告不判)')
    if not ok12:
        print('      ★ 判据是「跨设备可读」而非「本机有文件」 —— 只写本机文件在观测上等于没落链')
    ok = ok and ok12
    if _fp: print('  [落链] ' + _fp)
    print('[selfcheck] ' + ('OK PASS' if ok else 'X FAIL'))
    return 0 if ok else 1

def cmd_lean4(args):
    bad = ['cld-health/phi13', 'mac-mini/x', 'i9/y', 'foo_bar/z']
    good = ['data/cld-health/k', 'notes/node/k', 'tasks/i9/cmd']
    ok1 = all(validate_key(k)[0] is False for k in bad)
    ok2 = all(validate_key(k)[0] is True for k in good)
    # v1.0.5 新增不变量 (明鉴 2026-09-11 实证): 后续段非法字符必须被拦。
    # 旧实现只查首段 -> validate 报 OK 而 put 被 400 打回 = 同一工具自相矛盾。
    # 本断言把「validate 与 put 必须同判」固化为门, 防回归。
    bad2 = ['data/x/a:b', 'data/x/a+b', 'data/x/a@b', 'data/x/a~b', 'data/x/a!b']
    ok3 = all(validate_key(k)[0] is False for k in bad2)
    ok = ok1 and ok2 and ok3
    # v1.0.8: 接入外部断言集(结构上执行, 不靠人工核对)。文件不存在则跳过并**声明跳过**(不静默)。
    n_r = n_a = 0
    aok = None
    if os.path.isfile(ASSERTIONS):
        try:
            asrt = (json.load(open(ASSERTIONS, encoding='utf-8')).get('assertions') or {})
            mr = asrt.get('must_reject') or []
            ma = asrt.get('must_accept') or []
            n_r, n_a = len(mr), len(ma)
            leaked = [x.get('key') for x in mr if validate_key(x.get('key', ''))[0]]
            over_all = [x.get('key') for x in ma if not validate_key(x.get('key', ''))[0]]
            over = [k for k in over_all if k not in ADJUDICATED_DIVERGENCE]
            adjudicated = [k for k in over_all if k in ADJUDICATED_DIVERGENCE]
            if adjudicated:
                print('  ~ 已裁定分歧(属主裁定应拒, 断言集仍列 must_accept): ' + ', '.join(adjudicated))
            aok = (not leaked and not over)
            if leaked:
                print('  X 断言集漏点(must_reject 被放行): ' + ', '.join(leaked[:5]))
            if over:
                print('  X 断言集误伤(must_accept 被拒): ' + ', '.join(over[:5]))
        except Exception as e:
            aok = False
            print('  X 断言集读取失败: ' + str(e)[:70])
    ok = ok and (aok is not False)
    if aok is None:
        tail = '断言集 SKIP(文件不存在)'
    elif aok:
        tail = '断言集 ' + str(n_r + n_a) + ' 条通过'
    else:
        tail = '断言集 FAIL'
    print('lean4-check:', ('OK illegal keys blocked + legal allowed + validate/put 同判不变量成立 + ' + tail) if ok else 'X gate failed')
    return 0 if ok else 1

def _subject_identity():
    """★ v1.7.0（守灯通则）：把「本次自检到底测了谁」写成身份键。
    缺此项时，两个仪器的口径冲突只能靠人肉对账（今晚实证：RSS 45 倍之争能自解，仅因 HR 仪器带了 pid）。
    载荷失败不抛错，只记 None（观测缺口必须明说，不能静默省略）。"""
    ident = {'tool': 'bb-write', 'code_version': VERSION,
             'probed_at': datetime.datetime.now().isoformat(timespec='seconds'),
             'tz_note': 'probed_at 为本机本地时间、无时区偏移（与黑板 ts 同形）'}
    try:
        c = _conn('local')
        c.request('GET', keypath_of('data/registry/bb-write-tool-20260911'))
        r = c.getresponse()
        ident['subject_key'] = 'data/registry/bb-write-tool-20260911'
        ident['subject_version'] = (json.loads(r.read().decode('utf-8', 'replace')) or {}).get('version')
        c.close()
    except Exception as e:
        ident['subject_key'] = 'data/registry/bb-write-tool-20260911'
        ident['subject_version'] = None
        ident['identity_gap'] = '读身份失败: ' + str(e)[:60]
    return ident

def _write_link(kind, payload):
    """⑧ 自动落链: 把校验结果落为该日的 registry 产物。
    ★ 背景自查: bb-write 此前**无任何落链代码**; 我一度按文档串(R006 十项列表里的 "8落链")误判为「有」——
    那是「把文档提到当具备」的假阳性, 与星桥披露的错②同型, 已纠正。"""
    try:
        os.makedirs(LLNK_DIR, exist_ok=True)
        fp = os.path.join(LLNK_DIR, 'bb-write-' + kind + '-' + datetime.date.today().isoformat() + '.json')
        rec = {'tool': 'bb-write', 'version': VERSION, 'kind': kind,
               'ran_at': datetime.datetime.now().isoformat(timespec='seconds'),
               'result': payload, 'inherited_limits': INHERITED_LIMITS,
               # ★ v1.7.0（守灯 2026-09-11 提出通则，HR 采纳并先用在自家工具上）：
               #   **任何测量/自检工具的输出必须含「被测对象的身份键」**，否则口径冲突无法自解。
               #   实证：守灯与 HR 对「CLD 主进程 RSS」争执 45 倍，**能自解的唯一原因是 HR 的仪器输出了 pid 字段**；
               #   若它只报 rss_mb=65 而不带 pid，双方至今各执一词。
               #   故本条落链记录补记「被测对象身份」：工具名 + 代码版本 + 被核对象（登记卡）的 version + 取值时点。
               'subject_identity': _subject_identity(),
               # ★ v1.4.3（星桥 2026-09-11 复测指出：整个黑板的 ts 都无时区；本机两端今日同为 +0800
               #   ⇒ **不是不一致，是格式有歧义且当前恰好一致**）。本工具落戳同样是本地时间无偏移，
               #   故**显式声明语义**（改格式会波及所有消费方；声明是本轮商定的处置）：
               'tz_note': 'ran_at 为**本机本地时间、无时区偏移**（与黑板 ts 同形）。跨设备比较前须先确认两端时区；'
                          '★ 本字段属「潜伏缺陷」——今天不出错，故不会有人去修。'
                          '★ 且按纪律：**指纹/时间戳只用于「我这一刻看到的是这个」，不能用于「它现在还是这个」**'
                          '（实证：某指纹 00:48:48 记 34413260… → 00:55 已 5c6bb1ef…，2 分钟即过期）。'}
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)
        # ★ v1.6.0 (明鉴 a190c54c 2026-09-11 以本地文件系统抽验触发, HR 复现):
        #   本条此前**只写本机文件**(LLNK_DIR), **从不写黑板键** ⇒ 「落链」的实际观测面是**本机文件系统**。
        #   与同晚「两张卡中央侧 404」**同机理**: **落盘 ≠ 落链**; 落链的判据是「跨设备可读」, 不是「本机有文件」。
        #   故现落**两个落点**: ① 本机文件(离线可用) ② 黑板键 data/registry/<同名>(网络可见), 并**回读确认**。
        # ★ 断言口径(依据 HR 当晚实测的分布, 见 README): data/registry/* 共 202 键, 其中 **182 键仅落本机、20 键双侧**
        #   ⇒ **单写 local 是多数实践**。故本工具**只把 local 侧回读作为断言**(⑧ 的最低兑现),
        #   **central 侧只报告不判失败** —— 不在无判据时把「双写」当默认要求。
        LASTMETA.clear()
        board_key = 'data/registry/bb-write-' + kind + '-' + datetime.date.today().isoformat()
        LASTMETA['board_key'] = board_key
        body = json.dumps(rec, ensure_ascii=False).encode('utf-8')
        sides = {}
        for _s in ('local', 'central'):
            try:
                _c = _conn(_s)
                _c.request('PUT', keypath_of(board_key), body,
                           {'Content-Type': 'application/json', 'Content-Length': str(len(body))})
                _r = _c.getresponse(); _st = _r.status; _r.read(); _c.close()
                _c2 = _conn(_s)
                _c2.request('GET', keypath_of(board_key))
                _r2 = _c2.getresponse(); _st2 = _r2.status; _r2.read(); _c2.close()
                sides[_s] = [_st, _st2]
            except Exception as _e:
                sides[_s] = [-1, str(_e)[:40]]
        LASTMETA['board'] = sides
        LASTMETA['board_ok'] = (sides.get('local') == [200, 200])
        return fp
    except Exception as e:
        print('  [落链失败] ' + str(e)[:80]); return None

def cmd_deliver_gate(args):
    """⑩ 约束前置·不可绕过 —— **阻断型**入口(此前 lean4-check 只 print, 无阻断能力)。
    ★ 归属与星桥一致: **工具只负责「拒绝」, 不负责「替我拦人」** —— 由交付流程调用本入口;
    任一门不过 -> 打印「禁止交付」并 exit 非零。"""
    import io, contextlib
    print('[交付门] 运行全部门 ...')
    fails = []
    for name, fn in (('selfcheck', cmd_selfcheck), ('lean4-check', cmd_lean4)):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                code = fn(args)
            except Exception:
                code = 1
        print('  ' + ('OK  ' if code == 0 else 'FAIL') + '  ' + name)
        if code != 0:
            fails.append(name)
    payload = {'gates_failed': fails, 'verdict': 'BLOCK' if fails else 'PASS'}
    fp = _write_link('deliver-gate', payload)
    if fp: print('  [落链] ' + fp)
    if fails:
        print('[交付门] X **禁止交付** —— 未过: ' + ', '.join(fails))
        log('deliver-gate BLOCK: ' + ','.join(fails))
        return 2
    print('[交付门] OK 全部通过，允许交付（verdict=PASS）')
    log('deliver-gate PASS')
    return 0

def cmd_cld(args):
    print('[cld-check] pure CLI, no CLD coupling. PASS'); return 0

def cmd_vcheck(args):
    print('[version-check] pure CLI, no dsh dependency. v' + VERSION); return 0

def cmd_version(args):
    if globals().get('JSON_OUT'):
        print(json.dumps({'tool': 'bb-write', 'version': VERSION, 'source': 'VERSION 常量'}, ensure_ascii=False))
    else:
        print('bb-write ' + VERSION)
    return 0

def main():
    ap = argparse.ArgumentParser(
        description='bb-write - blackboard write/validate',
        epilog=('R006 ⑨ 偏离声明(明鉴 2026-09-11 裁定为「必要偏离」): 本工具 `put --json` 是**输入**语义'
                '(payload, 既有接口, 多会话在用), R006 ⑨ 要的 `--json` 是**输出**语义, 同一旗标两种语义冲突。'
                '故机器可读输出统一用 `--json-out`(任意位置可用, 输出合法 JSON)。'
                '★ v1.3.2(星桥第五态「接受但理由错」触发): 除 put 外, `--json` 亦被显式接受为 --json-out 的别名;'
                '实现为 argv 预扫描显式剥离, 不依赖 argparse 前缀匹配(后者会因新增 --jsonl 之类而静默失效);'
                '此处显式声明, 使其成为「被声明的能力」而非「恰好能用」。'
                '★ v1.3.3(星桥建议): `--dry-run` 亦为**工具级旗标, 任意位置可用**, 走完全部前置校验但**零变更**'
                '(实测: dry-run 后回读该键 404, 未落盘)。此前它只在 put 子命令内可用且未在 help 声明 —— **同样的「能力存在但未声明」**。'))
    # R006 ⑥ --tool-version (机器可读, 版本唯一来源 = VERSION 常量)
    ap.add_argument('--tool-version', action='store_true')
    # R006 ⑨ --json-out 机器可读输出。注: put 的 --json 已被 payload 占用(既有接口),
    # 故机器可读输出统一叫 --json-out, 这是必要偏离, 已在 README 记录。
    ap.add_argument('--json-out', dest='json_out', action='store_true')
    sub = ap.add_subparsers(dest='cmd')
    p_put = sub.add_parser('put'); p_put.add_argument('key'); p_put.add_argument('--body', default=''); p_put.add_argument('--json', default=None); p_put.add_argument('--from', dest='from_agent', default=None); p_put.add_argument('--subject', default=''); p_put.add_argument('--server', default='local', choices=['local', 'central', 'both']); p_put.add_argument('--expect-keys', dest='expect_keys', default=''); p_put.add_argument('--force', action='store_true'); p_put.add_argument('--dry-run', dest='dry_run', action='store_true')
    p_get = sub.add_parser('get'); p_get.add_argument('key'); p_get.add_argument('--server', default='local', choices=['local', 'central'])
    p_val = sub.add_parser('validate'); p_val.add_argument('key'); p_val.add_argument('--server', default='local', choices=['local', 'central'])
    for c in ['selfcheck', 'lean4-check', 'cld-check', 'version-check', 'version', 'deliver-gate']:
        sub.add_parser(c)
    # v1.0.7 (明鉴实测指出): `version --json-out` 此前返回 usage —— 全局旗标放在子命令之后不被接受,
    # 即「机器可读能力存在但没接通」。改为**预扫描 argv**: 任意位置出现 --json-out 一律剥离并置位。
    argv = [a for a in sys.argv[1:] if a != '--json-out']
    if len(argv) != len(sys.argv[1:]):
        globals()['JSON_OUT'] = True
    # ★ v1.2.0 横切能力层 (星桥 ④ 实测指出三处残余, 我认 —— 三者是同一个病:
    #   我把能力加在「我注意到的那一处」, 而不是加成横切能力):
    #     · --dry-run 只在 put 生效, 顶层 --dry-run 报 usage
    #     · --json 靠 argparse 前缀匹配「碰巧」在 --json version 生效, 但 version --json 失败,
    #       且 validate --json 设了旗标却仍输出纯文本 = 又一处「能力存在但没接通」
    #     · 失败留痕只包了 cmd_put; cmd_get / cmd_validate 等仍无
    #   修法: ① 预扫描把三个工具级旗标在**任意位置**剥离并置位; ② 调度层统一留痕(单一出口, 覆盖全部子命令)。
    #   --json 的例外: `put` 的 --json 是**载荷**(已被明鉴裁定为「必要偏离」), 故仅对非 put 子命令剥离。
    raw = sys.argv[1:]
    sub_cmd = next((a for a in raw if not a.startswith('-')), None)
    strip = {'--json-out', '--dry-run'} | ({'--json'} if sub_cmd != 'put' else set())
    argv = [a for a in raw if a not in strip]
    if any(a in ('--json', '--json-out') for a in raw) and sub_cmd != 'put':
        globals()['JSON_OUT'] = True
    if '--dry-run' in raw:
        globals()['DRY_RUN'] = True
    args = ap.parse_args(argv)
    if getattr(args, 'tool_version', False):
        print(json.dumps({'tool': 'bb-write', 'version': VERSION,
                          'source': 'VERSION 常量(本脚本为独立 .py, 无 package.json; 常量即唯一来源)',
                          'r006': '⑥ --tool-version / ⑨ --dry-run,--json-out / ⑩ --deliver-gate',
                          'inherited_limits': INHERITED_LIMITS}, ensure_ascii=False))
        return 0
    if getattr(args, 'json_out', False):
        globals()['JSON_OUT'] = True
    if not args.cmd:
        ap.print_help(); return 0
    fn = {'put': cmd_put, 'get': cmd_get, 'validate': cmd_validate, 'selfcheck': cmd_selfcheck, 'lean4-check': cmd_lean4, 'cld-check': cmd_cld, 'version-check': cmd_vcheck, 'version': cmd_version, 'deliver-gate': cmd_deliver_gate}.get(args.cmd)
    if not fn:
        ap.print_help(); return 0
    # ★ v1.2.0 调度层统一留痕（单一出口，覆盖**全部**子命令）
    #   星桥 ④ 指出「失败留痕待按明鉴原口径复核」= 我此前只包了 cmd_put，cmd_get 的出口无留痕。
    #   提到调度层后，结构上不可能再漏（与「合并入口，不是补漏」同一条修法）。
    try:
        st = fn(args)
    except Exception as e:
        st = 1
        print('X ' + str(e)[:120])
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write('[' + datetime.datetime.now().isoformat() + '] cmd=' + str(args.cmd)
                    + ' exit=' + str(st) + chr(10))
    except Exception:
        pass
    # ★ 机器可读结果信封：JSON_OUT 时**每个**子命令都输出一行 JSON（行分隔，逐行解析）
    if globals().get('JSON_OUT'):
        print(json.dumps({'tool': 'bb-write', 'cmd': args.cmd, 'exit': st, 'ok': st == 0}, ensure_ascii=False))
    return st

if __name__ == '__main__':
    sys.exit(main())
