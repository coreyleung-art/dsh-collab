#!/usr/bin/env python3
"""双写 + 双回读 + 三比 —— 把「两处各做一次」写成一次调用内部的循环。

为什么需要它（来自 2026-09-14 的实测）：
  黑板两个实例（本机 127.0.0.1:8792 · 中央 106.53.214.108:8792）【独立可写、无自动同步】。
  实测只写中央 ⇒ 中央 200 / 本机 404；只写本机 ⇒ 本机 200 / 中央 404。
  而 data/registry/ 的单侧率按作者双峰分布：有的作者 ≈0%（写两侧），有的 ≈100%（只写本机）。
  根因不是「第二步失败」，而是【有些写入流程里根本没有第二步】——
  凡靠人记得做第二次的动作，一定会有一批只做了第一次。
  ⇒ 所以第二步不能靠记得，必须写进一次调用内部。

它做的事（一次调用，调用者不需要记得任何第二步）：
  1. PUT 到两个实例（各自独立记录状态码与耗时）
  2. 各自回读一次
  3. 比三条：字段数 / 键集合 / value 的 sha256
  4. 任一步失败时【明确报是哪一个实例的哪一步】—— 因为「某侧缺失」有三个可能值：
     没做该环节 / 做了但失败 / 做了但目标已存在；三者的外观相同，必须靠这里的记录分开。

用法：
  python3 bb-put-both.py <key> <value.json>          # value.json 是纯内容（不含 key/ts/value 外壳）
  python3 bb-put-both.py <key> --from <other-host>   # 从另一实例读回内容再双写（补写用）
  退出码：0=两侧一致且都成功；1=有失败或两侧不一致
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, sys, time, hashlib, urllib.request, urllib.error

LOCAL = "127.0.0.1:8792"
CENTRAL = "106.53.214.108:8792"
HOSTS = (LOCAL, CENTRAL)


def _req(url, data=None, timeout=25):
    req = urllib.request.Request(url, data=data, method="PUT" if data is not None else "GET",
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return (r.status, round((time.time() - t0) * 1000), r.read())
    except urllib.error.HTTPError as e:
        body = e.read()[:200]
        try:
            err = json.loads(body).get("error", "")
        except Exception:
            err = body[:80].decode("utf-8", "replace")
        return (e.code, round((time.time() - t0) * 1000), err)
    except Exception as e:
        return (-1, round((time.time() - t0) * 1000), f"{type(e).__name__}: {e}")


def put_both(key, content):
    body = content if isinstance(content, bytes) else json.dumps(content, ensure_ascii=False).encode()
    print(f"key = {key} · payload {len(body)} B")
    puts = {}
    for h in HOSTS:
        st, ms, extra = _req(f"http://{h}/{key}", data=body)
        puts[h] = st
        flag = "✅" if st == 200 else "★"
        print(f"  {flag} PUT {h:22} ⇒ {st} ({ms} ms)" + (f"  {extra}" if st != 200 else ""))
    reads = {}
    for h in HOSTS:
        st, ms, body2 = _req(f"http://{h}/{key}")
        item = {"status": st}
        if st == 200:
            try:
                d = json.loads(body2)
                v = d.get("value")
                item["ver"] = d.get("version")
                item["n"] = len(v) if isinstance(v, dict) else -1
                item["keys"] = sorted(v.keys()) if isinstance(v, dict) else None
                item["sha"] = hashlib.sha256(json.dumps(v, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
            except Exception as e:
                item["parse_error"] = str(e)[:60]
        reads[h] = item
        print(f"  READ  {h:22} ⇒ {st}" + (f" · ver={item.get('ver')} · 字段数={item.get('n')} · sha={item.get('sha')}" if st == 200 else ""))
    # 三比
    a, b = reads[LOCAL], reads[CENTRAL]
    print("  三比（内容级对照）：")
    ok = True
    if a.get("status") != 200 or b.get("status") != 200:
        print(f"    ★ 存在但读不全：本机 {a.get('status')} / 中央 {b.get('status')} —— 按「某侧缺失三值」需先判：没做该环节 / 做了但失败 / 目标已存在")
        ok = False
    else:
        for label, x, y in (("字段数", a.get("n"), b.get("n")),
                            ("键集合", a.get("keys"), b.get("keys")),
                            ("value sha256", a.get("sha"), b.get("sha"))):
            same = (x == y)
            ok = ok and same
            print(f"    {'✅' if same else '★'} {label}: {'一致' if same else f'不一致（{x} vs {y}）'}")
    # ★ 第四比：读回的值 vs 我打算写的值 ——「两侧一致」不等于「写对了」
    print("  第四比（与源内容对照 —— 两侧一致 ≠ 写入正确）：")
    # ★ 必须 sort_keys=True：黑板【会重排 JSON 键顺序】（2026-09-14 实测：
    #   PUT 顺序 from·reply_to·to·type·title… 读回变成 from·reply_to·title·to·ts·type…），
    #   所以按键序算 sha 会得到「内容其实相同却报不一致」的假阳性。
    def _fp(x):
        return hashlib.sha256(json.dumps(x, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    want = json.loads(body.decode()) if body else None
    want_sha = _fp(want) if want is not None else None
    for h in HOSTS:
        r = reads[h]
        got = r.get("sha")
        same = (got == want_sha)
        ok = ok and same
        print(f"    {'✅' if same else '★'} {h:22} 读回 {got} · 期望 {want_sha} {'一致' if same else '★不一致 —— 写进去的不是你打算写的'}")
    if want is not None and not isinstance(want, type(a.get('keys')) if False else object):
        pass
    print(f"  判定：{'✅ 两侧一致、且读回等于源内容（内容级已核）' if ok else '★ 未通过 —— 不要按「已写入」记'}")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(2)
    key = sys.argv[1]
    if sys.argv[2] == "--from":
        src = sys.argv[3]
        st, _, body = _req(f"http://{src}/{key}")
        if st != 200:
            print(f"  ★ 源实例读取失败 {st}"); sys.exit(1)
        env = json.loads(body)
        content = env.get("value")            # ★ 取 value，不把整卡当 body（否则会双层）
    else:
        raw = open(sys.argv[2], encoding="utf-8").read()
        # ★ 必须解析：否则字符串会被 json.dumps 二次编码，
        #   结果「格式合法、两侧一致，但 value 是一段带引号的文本」——
        #   正是「两侧一致 ≠ 写入正确」那个坑。
        try:
            content = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"  ★ 输入不是合法 JSON：{e.msg} at line {e.lineno} col {e.colno}")
            print("    （不静默当字符串写入 —— 那会得到一个两侧一致但内容错的卡）")
            sys.exit(2)
    sys.exit(put_both(key, content))
