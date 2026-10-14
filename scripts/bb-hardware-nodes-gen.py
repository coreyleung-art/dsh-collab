#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bb-hardware-nodes-gen.py v1.0.0 —— 硬件节点图【生成器】

★ 出处（2026-10-14 · 用户裁决「补生成器，也补元信息」）：
  `hardware-nodes.json` 实测 mtime 36 天陈旧，而 `bb-gallery-refresh.py` 声明的
  produces 只有 3 项 ⇒ **它从未接入任何自动更新路径**，且**无任何人工元信息**
  （只有 nodes/relations/groups，没有 version/updated）。
  ⇒ 用户裁决：**补生成器 + 补元信息**。

★★ 设计：人写 / 机器写【分工】
  · `hardware-nodes.core.json` = **人工核心**（设备事实：device/os/ip/role/spec）
  · 本脚本 = **机器派生**（探测每个节点的可达性 ⇒ status；注入 version/updated/generatedAt）
  ⇒ **两份文件职责分明**：改设备事实改 core；跑生成器刷新 live 字段。

★ 探测方式（★ 复用而非新建）：对 core 里声明的 `_probe` 类型做 TCP 连接测试
  · tailscale ⇒ 探 100.x 主机的 8792（黑板）
  · 其它      ⇒ 探 127.0.0.1:8792
  ★ 三态：**可达 / 不可达 / 不可判（未声明探测目标）** —— ★ 不把「没探」读成「不可达」。

★ 用法：
  python3 bb-hardware-nodes-gen.py --selfcheck   # R006 ② 能力边界自检
  python3 bb-hardware-nodes-gen.py               # 默认演练（零变更）
  python3 bb-hardware-nodes-gen.py --go          # 真写
  python3 bb-hardware-nodes-gen.py --json
"""
import os, sys, json, socket, argparse, datetime, time

VERSION = "1.0.0"           # ★ R006 ⑥ 唯一版本声明处
R006_SELFCHECK = True       # ★ R006 ②

GALLERY = os.path.expanduser("~/dsh-collab/data/blueprint/gallery")
CORE = os.path.join(GALLERY, "hardware-nodes.core.json")
OUT = os.path.join(GALLERY, "hardware-nodes.json")
LOG = os.path.expanduser("~/dsh-collab/logs/bb-hardware-nodes-gen.log")


def log(msg):
    """★ R006 ⑦ 统一日志：固定路径，失败也留痕"""
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (datetime.datetime.now().isoformat(), msg))
    except Exception:
        pass


def selfcheck():
    print("== bb-hardware-nodes-gen 自查（TCC 能力边界）==")
    print("【① 能力清单】")
    print("  · 读 hardware-nodes.core.json（人工核心）")
    print("  · TCP 连接测试（★ 只 connect，不发数据）")
    print("  · 写 hardware-nodes.json（★ 仅 --go）")
    print("【② 不该发生路径清单】")
    print("  · 不删除任何文件 · 不修改权限 · 不终止进程 · 不访问非探测端口")
    print("【③ 依赖完整性】")
    print("  · 标准库: socket/json/argparse/datetime · python %s" % sys.version.split()[0])
    print("  · 固定日志: %s" % LOG)
    print("  · 版本: %s" % VERSION)
    # ★★★ 2026-10-15（应用 H5d）：加【能失败】的判据 —— core 缺失 ⇒ exit 1
    if not os.path.exists(CORE):
        print("  ★ 自证失败：找不到人工核心 %s" % CORE)
        return 1
    print("  ★ 自证判据：core 存在 ⇒ 可执行（★ 能失败，非声明）")
    return 0


def probe(host, port=8792, timeout=2.0):
    """★ 三态：'ok' / 'fail' / 'unknown'"""
    if not host:
        return "unknown"
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return "ok"
    except Exception:
        return "fail"


def build():
    with open(CORE, encoding="utf-8") as f:
        core = json.load(f)
    nodes = []
    reached = unreached = unknown = 0
    for n in core.get("nodes") or []:
        ip = n.get("ip")
        kind = n.get("_probe")
        host = ip if (kind == "tailscale" and ip) else ("127.0.0.1" if kind else None)
        if host is None:
            st, unknown = "不可判（未声明探测目标）", unknown + 1
        else:
            r = probe(host)
            if r == "ok":
                st, reached = "运行", reached + 1
            elif r == "fail":
                st, unreached = "不可达", unreached + 1
            else:
                st, unknown = "不可判", unknown + 1
        node = {k: v for k, v in n.items() if not k.startswith("_")}
        node["status"] = st
        node["probedAt"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        nodes.append(node)
    return {
        "version": core.get("version", "1.0.0"),
        "updated": datetime.date.today().isoformat(),
        "generatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "generatedBy": "bb-hardware-nodes-gen.py v" + VERSION,
        "sourceOfTruth": "hardware-nodes.core.json（人工核心）",
        "probeSummary": {"可达": reached, "不可达": unreached, "不可判": unknown},
        "groups": core.get("groups") or {},
        "nodes": nodes,
        "relations": core.get("relations") or [],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--go", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.selfcheck:
        return selfcheck()
    if not os.path.exists(CORE):
        print("★ core 不存在: %s" % CORE, file=sys.stderr)
        return 2
    t0 = time.time()
    d = build()
    txt = json.dumps(d, ensure_ascii=False, indent=1)
    if a.json:
        print(json.dumps({"ok": True, "dry": not a.go, "nodes": len(d["nodes"]),
                          "probe": d["probeSummary"], "bytes": len(txt),
                          "seconds": round(time.time() - t0, 1)}, ensure_ascii=False))
    else:
        print("节点 %d · 探测 %s · 产出 %d B" % (len(d["nodes"]), d["probeSummary"], len(txt)))
    if a.go:
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(txt)
        log("go nodes=%d probe=%s" % (len(d["nodes"]), d["probeSummary"]))
        if not a.json:
            print("✅ 已写 %s" % OUT)
    else:
        log("dry nodes=%d" % len(d["nodes"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
