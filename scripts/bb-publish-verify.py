#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bb-publish-verify.py v1.0.0 —— 线上发布一致性【判据包装】

★ 出处（2026-10-14 · 用户批准的计划 A1）：
  计划要把 `systemgraph-publish.sh --verify` 接进 `bb-gallery-refresh.py` 流水线。
  但 refresh 的 runner **硬编码 `["python3", path]`** ⇒ 跑不了 .sh
  ⇒ 由本工具**包一层**（★ 也更符合 R006 的 `--selfcheck` 范式）。

★★ 三态（★ 本工具的核心，不是二态）：
  · **rc=0** 不一致 0 且 不可判 0          ⇒ 线上与本地一致 ✓
  · **rc=1** 有确认不一致                  ⇒ ★ 发现真问题（★ 那是履行职责，非工具失败）
  · ★ **rc=2 有「不可判」**                ⇒ ★★ **既不能说一致，也不能说不一致**
      ★ 为什么必须单列：`--verify` 的「不可判」= **下载没取全**（超时截断），
        与「内容不一致」是两件事。★ 若把它并进任一态，就会产生
        **假阳性**（说线上坏了）或 **假阴性**（说线上好的）。

★★★ 依赖的前置修复（2026-10-14 同日，本线）：
  1. `--verify` 原用 `curl -m 20` 固定超时 ⇒ 3.57 MB 的资产 **20s 只下到 27%**
     ⇒ **永远报不一致**（假阳性）。已改为**按大小自适应超时**。
  2. 完整性判据改为 **服务器自报的 Content-Length**（★ 不是本地大小）
     ⇒ 否则真差异（大小会变）会被误判成「不可判」（假阴性）。
  3. 缓存该服务器 **不支持 HEAD**（405）+ **BSD awk 不支持 IGNORECASE** 两个坑。
  4. 覆盖度 **19 → 42 个文件（15.1% → 33.3%）**。

★ 用法：
  python3 bb-publish-verify.py --selfcheck   # R006 ② 能力边界自检
  python3 bb-publish-verify.py               # 跑验证（默认就是判据语义）
  python3 bb-publish-verify.py --json
"""
import os, sys, json, subprocess, argparse, datetime

VERSION = "1.0.0"
R006_SELFCHECK = True

SCRIPTS = os.path.expanduser("~/dsh-collab/scripts")
PUBLISH = os.path.join(SCRIPTS, "systemgraph-publish.sh")
LOG = os.path.expanduser("~/dsh-collab/logs/bb-publish-verify.log")
TIMEOUT = 900          # ★ 42 个文件含 3.5 MB 资产 ⇒ 给足；超时按 §自适应


def log(msg):
    """★ R006 ⑦ 统一日志"""
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (datetime.datetime.now().isoformat(), msg))
    except Exception:
        pass


def selfcheck():
    print("== bb-publish-verify 自查（TCC 能力边界）==")
    print("【① 能力清单】")
    print("  · 调用 systemgraph-publish.sh --verify（★ 只读：只 GET 线上并比对 sha256）")
    print("  · 读本地 static-export/ 的 manifest 与文件")
    print("【② 不该发生路径清单】")
    print("  · ★ **不发布、不上传、不改服务端**（--verify 是只读模式）")
    print("  · 不删除文件 · 不修改权限 · 不终止进程")
    print("【③ 依赖完整性】")
    print("  · 依赖: systemgraph-publish.sh（%s）" % ("存在 ✓" if os.path.exists(PUBLISH) else "★ 缺失"))
    print("  · 标准库: subprocess/json/argparse · python %s" % sys.version.split()[0])
    print("  · 固定日志: %s" % LOG)
    print("  · 版本: %s" % VERSION)
    return 0


def run_verify():
    # ★★ 坑（本线实测）：`text=True` 用【严格 UTF-8】解码 ⇒ 该脚本的 stderr 里
    #   含非 UTF-8 字节（shasum/curl 的输出）⇒ **整个调用抛 UnicodeDecodeError**
    #   ⇒ ★ 修法：显式 `encoding='utf-8', errors='replace'`（★ 不因解码而丢判据）
    r = subprocess.run(["bash", PUBLISH, "--verify", "--json"],
                       capture_output=True, encoding="utf-8", errors="replace",
                       timeout=TIMEOUT, cwd=SCRIPTS)
    out, err, rc = r.stdout or "", r.stderr or "", r.returncode
    mism = unk = None
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("{") and "mismatch" in line:
            try:
                j = json.loads(line)
                mism, unk = j.get("mismatch"), j.get("unknown")
            except Exception:
                pass
    return rc, mism, unk, out, err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.selfcheck:
        return selfcheck()
    if not os.path.exists(PUBLISH):
        print("★ 找不到 %s" % PUBLISH, file=sys.stderr)
        return 2
    try:
        rc, mism, unk, out, err = run_verify()
    except subprocess.TimeoutExpired:
        log("timeout")
        print("★ 超时（%ss）—— 判【不可判】" % TIMEOUT, file=sys.stderr)
        return 2

    # ★★★ 三态归一：不可判优先于「不一致」，因为「取不到」不能推出「不一致」
    if unk is None or mism is None:
        state, code, note = "不可判", 2, "★ 解析不到 --verify 的 JSON 计数（★ 不猜）"
    elif unk > 0:
        state, code, note = "不可判", 2, "★ %d 个文件下载未取全 ⇒ **既不能判一致，也不能判不一致**" % unk
    elif mism > 0:
        state, code, note = "滞后", 1, "★ %d 个文件确认不一致 ⇒ 线上滞后于本地导出" % mism
    else:
        state, code, note = "一致", 0, "✓ 线上与本地导出逐文件一致"

    if a.json:
        print(json.dumps({"ok": code == 0, "state": state, "rc": code,
                          "mismatch": mism, "unknown": unk, "note": note,
                          "version": VERSION}, ensure_ascii=False))
    else:
        print("发布一致性: 【%s】· 不一致=%s · 不可判=%s" % (state, mism, unk))
        print("  %s" % note)
    log("state=%s rc=%d mismatch=%s unknown=%s" % (state, code, mism, unk))
    return code


if __name__ == "__main__":
    sys.exit(main())
