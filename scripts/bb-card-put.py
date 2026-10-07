#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-card-put.py —— 黑板**卡写入**的统一入口（供会话内临时脚本复用），v1.0.0
版本：唯一来源 = 下方 VERSION 常量（docstring 不写版本号，防声明位漂移）。

为什么存在（真实动机，非设计想象）：
  2026-09-11 我在 30 分钟内**两次**踩同一个坑：卡内**顶层键名含逗号** ⇒ `bb-write --expect-keys`
  是逗号分隔的 ⇒ 期望集合被切碎 ⇒ **exit 5（形状断言失败）**，而信息看起来像「写入失败」。
  ★ 我先前把拒绝逻辑写进了 `bb-copy.py` 的复制路径，**但一次性 heredoc 写卡脚本绕过了它**
    ⇒ 同一个缺陷在「工具路径已堵、临时路径未堵」之间复现。
  ⇒ 本入口把三类**必做**的事固化为默认行为（写卡脚本直接复用，别再手搓）：
    ① **拒绝含逗号的键名**（给出出路，而不是让下游报一个令人误解的 exit 5）
    ② **注入时点**（ts/ts_epoch 由写入路径写入，带时区偏移 —— 不手写）
    ③ **规范身份 + 双侧 + 形状断言 + 回读复核**（默认全开）

用法：
  python3 bb-card-put.py <key> < payload.json          # 从 stdin 读卡体
  python3 bb-card-put.py <key> --json '<json>'         # 或直接给
  [--keep-ts] 保留卡体内原有 ts（默认覆盖为注入值）
  [--dry-run] 只打印将写入的内容与校验结论，不写
退出码：0=成功且回读一致 ｜ 2=参数/键名问题 ｜ 3=回读不可读 ｜ 4=回读与写入不一致 ｜ 5=下游拒绝
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, subprocess, sys, datetime

VERSION = '1.0.3'
BB_WRITE = os.path.expanduser('~/dsh-collab/scripts/bb-write.py')
CANONICAL_ID = 'external-link-agent'
REPLICAS = {'local': '127.0.0.1:8792', 'central': '106.53.214.108:8792'}


def _now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec='seconds')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('key')
    ap.add_argument('--json', dest='payload', default=None)
    ap.add_argument('--keep-ts', dest='keep_ts', action='store_true')
    ap.add_argument('--dry-run', dest='dry_run', action='store_true')
    # ★ HR③ 幂等键：追加天然不幂等（重试会重复追加）⇒ 调用方给一个 marker，若卡内已有则**拒绝重写**
    ap.add_argument('--once-marker', dest='once_marker', default=None,
                    help='幂等键：卡内文本已含该 marker 时拒绝写入（防中断后重试造成重复追加）')
    ap.add_argument('--allow-repeat', dest='allow_repeat', action='store_true')
    args = ap.parse_args()

    # ① 键名守卫：逗号会切碎 --expect-keys（bb-write 的接口限制，属主已裁定将支持重复 --expect-key，未实施）
    if ',' in args.key:
        print('[card-put] X 键名含逗号，形状断言无法表达: ' + args.key)
        print('      `--expect-keys` 以逗号分隔 ⇒ 期望集合会被切碎 ⇒ 下游报令人误解的 exit 5')
        print('      ⇒ 出路: 改键名（用「·」或「；」代替逗号），**不要**因此去掉形状断言')
        return 2

    raw = args.payload if args.payload is not None else sys.stdin.read()
    try:
        card = json.loads(raw)
    except Exception as e:
        print('[card-put] X 卡体不是合法 JSON: ' + str(e)[:80]); return 2
    if not isinstance(card, dict):
        print('[card-put] X 卡体必须是对象（顶层字段）'); return 2

    bad = sorted(k for k in card if ',' in str(k))
    if bad:
        print('[card-put] X 顶层键名含逗号（同样会切碎 --expect-keys）: ' + ', '.join(bad))
        print('      ⇒ 出路: 改键名（用「·」代替逗号）')
        return 2
    # ★ 「生成前检查」（明鉴⑧ 同族：他以 ASI 双引号写在**字段名**里 ⇒ Python 语法错，检查器在 JSON 层**拦不住**）：
    #   本入口在**写入之前**扫键名中的引号/控制字符 ⇒ 把「记得写对」搬到「写入前必检」。
    _quote_bad = sorted(k for k in card if any(ch in str(k) for ch in ('"', "'", chr(10), chr(13), chr(9))))
    if _quote_bad:
        print('[card-put] X 键名含引号或控制字符（应在**生成前**就避免）: ' + str(_quote_bad[:3]))
        print('      ⇒ 出路: 键名只用汉字/字母/数字/「·」（引号请用中文引号「」）')
        print('      ⇒ 更稳的做法（结构性）: **卡体写成 JSON 文件**（由 write 工具落盘）再 `bb-card-put <key> < file.json`')
        print('        —— 那样卡体**不经过 Python 字面量层**，整类转义错从根上消失')
        return 2

    # ①b 写者标注：让「谁写的」可判（HR 裁定：越域写入当前不可判，**缺的是观测通道**；
    #     解锁条件 = writer 覆盖率提升 ⇒ 本入口把自己的身份写进 `writer`，覆盖率随新写入单调上升）
    card.setdefault('writer', 'bb-card-put v' + VERSION)

    # ①c 幂等键（HR③ 第 2 条）：marker 已存在 ⇒ 判定为重复执行
    if args.once_marker and not args.allow_repeat:
        try:
            import urllib.request as _u
            _cur = json.loads(_u.urlopen('http://127.0.0.1:8792/' + args.key, timeout=8).read().decode())
            _ctxt = json.dumps(_cur.get('value') or {}, ensure_ascii=False)
        except Exception:
            _ctxt = ''
        if args.once_marker and args.once_marker in _ctxt:
            print('[card-put] X 幂等键已存在（' + args.once_marker[:40] + '）⇒ 判定为**重复执行**，拒绝写入')
            print('      ⇒ 依据 HR③：追加天然不幂等；重试前先读回，并用幂等键识别重复（--allow-repeat 可明示覆盖）')
            return 2

    # ② 时点由写入路径注入
    if not args.keep_ts:
        card['ts'] = _now_iso()
        card['ts_epoch'] = str(int(datetime.datetime.now().timestamp()))

    keys = ','.join(sorted(card.keys()))
    if args.dry_run:
        print('[card-put] DRY-RUN key=' + args.key + ' | 顶层键=' + str(sorted(card.keys()))
              + ' | ts=' + str(card.get('ts')) + ' | 零变更')
        return 0

    # ③ 规范身份 + 双侧 + 形状断言
    r = subprocess.run(['python3', BB_WRITE, 'put', args.key, '--json', json.dumps(card, ensure_ascii=False),
                        '--expect-keys', keys, '--from', CANONICAL_ID, '--server', 'both'],
                       capture_output=True, text=True)
    tail = (r.stdout or '').strip().splitlines()[-1] if (r.stdout or '').strip() else (r.stderr or '').strip()[-120:]
    print('[card-put] 写入 exit=' + str(r.returncode) + ' | ' + tail)
    if r.returncode != 0:
        return 5 if r.returncode == 5 else r.returncode

    # ④ 回读复核（逐字段；失败即报，不静默）
    try:
        import urllib.request
        d = json.loads(urllib.request.urlopen('http://' + REPLICAS['local'] + '/' + args.key, timeout=8).read().decode())
        got = d.get('value') or {}
    except Exception as e:
        print('[card-put] ? 回读不可读: ' + str(e)[:60]); return 3
    diff = [k for k in card if json.dumps(got.get(k), sort_keys=True, ensure_ascii=False)
            != json.dumps(card[k], sort_keys=True, ensure_ascii=False)]
    if diff:
        print('[card-put] X 回读与写入不一致(字段): ' + ','.join(diff[:6])); return 4
    print('[card-put] OK ' + args.key + ' | 字段=' + str(len(got)) + ' | 回读逐字段一致')
    return 0


if __name__ == '__main__':
    sys.exit(main())
