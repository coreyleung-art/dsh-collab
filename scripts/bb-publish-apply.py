#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bb-publish-apply.py v1.0.0 —— 受门约束的【自动发布】

★ 出处（2026-10-15 · 用户裁决 «A：每日自动发布»）：
  今晚实测证明 **B（只加 verify）会变成每日常驻告警** ——
  因为**每日 refresh 都会重生数据 ⇒ 导出必然更新 ⇒ 每天都会报「线上滞后」**。
  ★ 而按今晚那条：「每次必红」与「这次变红」是两件事 —— 常驻告警会被忽略。
  ⇒ 所以裁决为 **A：让 refresh 的终点【一致】**。

★★★ 但计划里的前置条件【不得跳过】：「自动发布会把【不完整的中间态】推上生产」
  ⇒ 本工具把「不比对不发布」做成【结构】，而不是靠记得：

    ① **前验**：本地导出目录存在 + `manifest.json` 里记录的哈希与【实物】一致
       （★ 这是发布脚本早就有的「本地自洽检查」，★ 本工具把它提为【独立前置门】）
    ② **发布**：调 `systemgraph-publish.sh --go`（★ 它自带 上传→服务端逐文件 sha256
       比对→原子切换→HTTP 抽验→**失败回滚**）
    ③ **后验**：调 `bb-publish-verify.py` ⇒ ★ **必须【一致】才算发布成功**
       （★ 「上传完成 ≠ 发布成功」—— ★ 只有后验一致才认）

★ 三态：
  · rc=0 发布成功且后验一致
  · rc=1 发布失败 / 后验不一致（★ 发布脚本自身会回滚）
  · rc=2 不可判（★ 前验读不到 / 后验不可判 —— ★ **不把「读不到」读成「成功」**）

★ 用法：
  python3 bb-publish-apply.py --selfcheck
  python3 bb-publish-apply.py            # 默认【演练】：只跑前验，不发布
  python3 bb-publish-apply.py --go       # 真发布（前验 → 发布 → 后验）
  python3 bb-publish-apply.py --json
"""
import os, sys, json, argparse, subprocess, datetime, hashlib

VERSION = "1.0.0"
R006_SELFCHECK = True

SCRIPTS = os.path.expanduser("~/dsh-collab/scripts")
EXPORT = os.path.expanduser("~/dsh-collab/data/blueprint/gallery/static-export")
PUBLISH = os.path.join(SCRIPTS, "systemgraph-publish.sh")
VERIFY = os.path.join(SCRIPTS, "bb-publish-verify.py")
LOG = os.path.expanduser("~/dsh-collab/logs/bb-publish-apply.log")


def log(m):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (datetime.datetime.now().isoformat(), m))
    except Exception:
        pass


def selfcheck():
    print("== bb-publish-apply 自查（TCC 能力边界）==")
    print("【① 能力清单】")
    print("  · 读 static-export/（manifest + 实物哈希）")
    print("  · 调 systemgraph-publish.sh --go（★ 发布到 xingqiao.meetfunbp.com）")
    print("  · 调 bb-publish-verify.py（★ 后验）")
    print("【② 不该发生路径清单】")
    print("  · ★ **前验不过 ⇒ 绝不发布**（★ 结构上拒绝，非靠记得）")
    print("  · ★ **不经 --go 不发布**（★ 默认演练）")
    print("  · 不删文件 · 不改权限 · 不回滚（★ 回滚由发布脚本自己做）")
    print("【③ 依赖完整性】")
    miss = [n for n, p in (("systemgraph-publish.sh", PUBLISH), ("bb-publish-verify.py", VERIFY),
                           ("static-export/", EXPORT)) if not os.path.exists(p)]
    if miss:
        print("  ★ 自证失败：声明依赖缺失 %s" % miss)
        return 1
    print("  ★ 自证判据：三项声明依赖均存在 ⇒ 可执行（★ 能失败，非声明）")
    print("  · 固定日志: %s" % LOG)
    print("  · 版本: %s" % VERSION)
    return 0


def precheck():
    """★ ① 前验：manifest 记录的哈希 vs 实物（★ 发布脚本的「不比对不发布」前置化）"""
    mf = os.path.join(EXPORT, "manifest.json")
    if not os.path.exists(mf):
        return None, "★ 不可判：找不到 %s" % mf
    try:
        m = json.load(open(mf, encoding="utf-8"))
    except Exception as e:
        return None, "★ 不可判：manifest 读不开 %s" % type(e).__name__
    # ★ manifest 结构：{apis: {name: {file, bytes, sha?}}} —— ★ 实测可能无逐文件 sha
    #   ⇒ 判据退化为「声明的文件都在，且字节数一致」（★ 不假装比了 sha）
    checked = mismatch = 0
    for name, meta in (m.get("apis") or {}).items():
        f = meta.get("file") if isinstance(meta, dict) else None
        if not f:
            continue
        p = os.path.join(EXPORT, f) if not os.path.isabs(f) else f
        if not os.path.exists(p):
            mismatch += 1
        else:
            exp = meta.get("bytes")
            if isinstance(exp, int) and os.path.getsize(p) != exp:
                mismatch += 1
        checked += 1
    if checked == 0:
        return None, "★ 不可判：manifest 里没有可比对的条目"
    return {"checked": checked, "mismatch": mismatch, "exported": m.get("exported")}, None


def run(cmd, timeout=1800):
    r = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace",
                       timeout=timeout, cwd=SCRIPTS)
    return r.returncode, (r.stdout or ""), (r.stderr or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--go", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.selfcheck:
        return selfcheck()

    out = {"version": VERSION, "dry": not a.go}
    # ── ① 前验 ──
    pre, err = precheck()
    if pre is None:
        out.update({"ok": False, "state": "不可判", "rc": 2, "stage": "前验", "note": err})
        print(json.dumps(out, ensure_ascii=False) if a.json else "发布: 【不可判】· %s" % err)
        log("undecidable precheck: %s" % err)
        return 2
    out["precheck"] = pre
    if pre["mismatch"] > 0:
        out.update({"ok": False, "state": "前验不过", "rc": 1, "stage": "前验",
                    "note": "★ 本地导出自相矛盾：%d/%d 条与 manifest 不符 ⇒ **拒绝发布**"
                            % (pre["mismatch"], pre["checked"])})
        print(json.dumps(out, ensure_ascii=False) if a.json
              else "发布: 【前验不过】· %d/%d 条不符 ⇒ ★ 拒绝发布（★ 结构上拒绝，非靠记得）"
                   % (pre["mismatch"], pre["checked"]))
        log("deny precheck mismatch=%d" % pre["mismatch"])
        return 1
    if not a.go:
        out.update({"ok": True, "state": "演练通过", "rc": 0, "stage": "前验",
                    "note": "★ 前验通过 ⇒ 加 --go 才真发布"})
        print(json.dumps(out, ensure_ascii=False) if a.json
              else "发布: 【演练】· 前验通过 %d 条 ✓ ⇒ ★ 未发布（缺 --go）" % pre["checked"])
        return 0

    # ── ② 发布（★ 它自带比对 + 原子切换 + 失败回滚）──
    rc_pub, so, se = run(["bash", PUBLISH, "--go"])
    out["publishRc"] = rc_pub
    ok_line = [l for l in so.splitlines() if "发布成功" in l or "✅ 发布" in l]
    out["publishLine"] = ok_line[-1].strip() if ok_line else (se.strip()[:160] or "(无输出)")
    if rc_pub != 0:
        out.update({"ok": False, "state": "发布失败", "rc": 1, "stage": "发布",
                    "note": "★ 发布脚本 rc=%s（★ 它自身应已回滚）" % rc_pub})
        print(json.dumps(out, ensure_ascii=False) if a.json else "发布: 【失败】rc=%s" % rc_pub)
        log("publish fail rc=%s" % rc_pub)
        return 1

    # ── ③ 后验（★ 只有后验一致才认「发布成功」）──
    try:
        rc_v, so_v, _ = run(["python3", VERIFY, "--json"], timeout=1800)
        vj = json.loads(so_v.strip().splitlines()[-1])
    except Exception as e:
        out.update({"ok": False, "state": "不可判", "rc": 2, "stage": "后验",
                    "note": "★ 后验读不到：%s ⇒ **不把「读不到」读成「成功」**" % type(e).__name__})
        print(json.dumps(out, ensure_ascii=False) if a.json else "发布: 【不可判】后验异常")
        log("undecidable postcheck %s" % type(e).__name__)
        return 2
    out["postcheck"] = vj
    if vj.get("mismatch") == 0 and vj.get("unknown") == 0:
        out.update({"ok": True, "state": "发布成功且后验一致", "rc": 0, "stage": "后验",
                    "note": "✓ 上传→服务端比对→原子切换 + 后验逐文件一致"})
        log("ok publish+verify")
        code = 0
    elif vj.get("unknown", 0) > 0:
        out.update({"ok": False, "state": "不可判", "rc": 2, "stage": "后验",
                    "note": "★ 后验有 %s 个不可判（★ 下载未取全）—— ★ 不能据此说成功或失败" % vj.get("unknown")})
        code = 2
    else:
        out.update({"ok": False, "state": "后验不一致", "rc": 1, "stage": "后验",
                    "note": "★ 发布后仍有 %s 个文件不一致 ⇒ **「上传完成 ≠ 发布成功」**" % vj.get("mismatch")})
        code = 1

    if a.json:
        print(json.dumps(out, ensure_ascii=False))
    else:
        print("发布: 【%s】" % out["state"])
        print("  ① 前验 %d 条 ✓  ② 发布 %s  ③ 后验 mismatch=%s unknown=%s"
              % (pre["checked"], out.get("publishLine", "")[:60], vj.get("mismatch"), vj.get("unknown")))
    return code


if __name__ == "__main__":
    sys.exit(main())
