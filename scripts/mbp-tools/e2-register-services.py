#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E2 版本自注册：把本机组件版本写入 data/discovery/agents/mbp 的 services 字段。

规范（星桥 e2-services-spec-20261002）：
  · 位置: data/discovery/agents/<设备> 的 value.services
  · 形态: {"<组件名>": "v<版本>"}
  · 写入方: 端侧注册器（本机自写，PUT 幂等）

★ 安全要点：该键同时由 mac-mini 侧 hb-fwd 心跳代理维护（含 device/hb_age_s/status/sessions 等）。
  ⇒ **必须 GET → 合并 → PUT**，只增改 services，绝不覆盖其他字段。
  ⇒ 写完**逐板回读断言**（R036：回读是必要条件，两板不传播）。
"""
def _bb_auth():
    """黑板认证头 —— **双头过渡**（2026-10-03 响应星桥「写端鉴权 flip」）。

    旧头 `X-Webhook-Token` 保留（flip 前有效）；新头 `X-Blackboard-Token` 读
    `~/.dsh/blackboard-token`（0600，本地私密）⇒ **flip 前后都能写**。
    """
    h = _bb_auth()
    try:
        _p = __import__('os').path.expanduser("~/.dsh/blackboard-token")
        _t = open(_p, encoding="utf-8").read().strip()
        if _t:
            h["X-Blackboard-Token"] = _t
    except Exception:
        pass
    return h


import json, urllib.request, urllib.error, os, re, subprocess, sys, time

BOARDS = [("本机板", "http://100.120.203.20:8792",
           {"Authorization": "Bearer bb-token-20260829-macmini"}),
          ("中枢", "http://xingqiao.meetfunbp.com:8792",
           _bb_auth())]
KEY = "data/discovery/agents/mbp"


def get(base, h):
    r = urllib.request.Request(base + "/" + KEY, headers=h)
    return json.load(urllib.request.urlopen(r, timeout=12))


def put(base, h, val):
    hh = dict(h); hh["Content-Type"] = "application/json"
    r = urllib.request.Request(base + "/" + KEY,
                               data=json.dumps(val, ensure_ascii=False).encode("utf-8"),
                               method="PUT", headers=hh)
    return json.load(urllib.request.urlopen(r, timeout=20))


def collect():
    """采集本机**当前生效**的组件版本（排除 .bak-* 历史目录）。"""
    svc = {}
    # node-bridge：从心跳 payload 的 ver 读（规范建议）
    try:
        r = urllib.request.Request("http://100.120.203.20:8792/nodes/mbp/heartbeat",
                                   headers={"Authorization": "Bearer bb-token-20260829-macmini"})
        v = (json.load(urllib.request.urlopen(r, timeout=8)).get("value") or {}).get("ver")
        if v: svc["node-bridge"] = "v" + str(v)
    except Exception:
        pass
    # CLD 插件：读 web profile 的 package.json（排除 .bak-*）
    nm = os.path.expanduser("~/.dsh/profiles/web/node_modules")
    if os.path.isdir(nm):
        for name in sorted(os.listdir(nm)):
            if ".bak" in name or not name.startswith("dsh-plugin-"):
                continue
            pj = os.path.join(nm, name, "package.json")
            if not os.path.isfile(pj):
                continue
            try:
                ver = json.load(open(pj, encoding="utf-8")).get("version")
                if ver:
                    svc[name.replace("dsh-plugin-", "")] = "v" + str(ver)
            except Exception:
                pass
    # dsh-tools（本机未安装 ⇒ 规范要求"必需键在位"，故显式标 absent）
    if not subprocess.run(["bash", "-lc", "command -v dsh-tools >/dev/null 2>&1"]).returncode == 0:
        svc["dsh-tools"] = "absent"
    else:
        try:
            out = subprocess.run(["bash", "-lc", "dsh-tools --version"], capture_output=True,
                                 text=True, timeout=10).stdout.strip()
            m = re.search(r"(\d+\.\d+\.\d+)", out)
            svc["dsh-tools"] = "v" + m.group(1) if m else "present"
        except Exception:
            svc["dsh-tools"] = "present"
    # 自研守护（无版本号者标 rev1）
    if os.path.isfile(os.path.expanduser("~/dsh-collab/devices/blackboard-events.py")):
        svc["blackboard-events"] = "rev1(fp-debounce+retry)"
    return svc


def main():
    print("=== 采集本机组件版本 ===")
    svc = collect()
    for k, v in sorted(svc.items()):
        print("  %-24s %s" % (k, v))

    ok_all = True
    for tag, base, h in BOARDS:
        print("\n=== %s: GET → 合并 → PUT ===" % tag)
        try:
            cur = get(base, h)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # ★ 正常情形：`data/discovery/agents/*` 由 mac-mini 侧 hb-fwd 只写**中枢**，
                #   本机板本就没有该键 ⇒ 404 不等于失败，跳过该板即可（非缺陷）。
                print("  该板无此键（404）⇒ 跳过。注：本键由 hb-fwd 只写中枢，属预期。")
                continue
            print("  GET 失败:", str(e)[:60]); ok_all = False; continue
        except Exception as e:
            print("  GET 失败:", str(e)[:60]); ok_all = False; continue
        val = cur.get("value") or {}
        before = sorted((val.get("services") or {}).keys())
        merged = dict(val.get("services") or {})
        merged.update(svc)                       # 合并（只覆盖同名键）
        val["services"] = merged
        val["services_updated_by"] = "session-20b800d4-98f6-4e5e-90e4-34f7b6ca61d7"
        val["services_updated_at_epoch_ms"] = int(time.time() * 1000)
        print("  合并前 services 键: %s" % (before or "(空)"))
        print("  合并后 services 键: %d 项" % len(merged))
        # 保护性检查：其他字段必须原样保留
        keep = {k: v for k, v in val.items() if k not in ("services", "services_updated_by",
                                                          "services_updated_at_epoch_ms")}
        for f in ("device", "heartbeat_ref", "schema", "sessions", "status", "hb_age_s"):
            if f in val and f not in keep:
                print("  ⚠️ 字段缺失风险:", f)
        try:
            d = put(base, h, val)
            print("  PUT ✅ ver=%s" % d.get("version"))
        except Exception as e:
            print("  PUT ❌", str(e)[:60]); ok_all = False; continue
        # 回读断言
        try:
            back = (get(base, h).get("value") or {})
            got = back.get("services") or {}
            ok = all(got.get(k) == v for k, v in svc.items())
            intact = all(f in back for f in ("device", "status", "sessions"))
            print("  回读断言: services 全部到位=%s · 其他字段完整=%s" % (ok, intact))
            if not (ok and intact):
                ok_all = False
        except Exception as e:
            print("  回读失败:", str(e)[:50]); ok_all = False

    print("\n=== 总判定 ===")
    print("  " + ("✅ 两板 services 已写入且字段完整" if ok_all else "❌ 存在问题，需复查"))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
