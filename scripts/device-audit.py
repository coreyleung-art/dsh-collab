#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""device-audit v0.1 — 设备资产全景 + 能力/健康矩阵 (audit 工具族·骨架)
域: 跨设备资产 (mac-mini / MBP / PC-i9 / 手机) — 适用角色: 罗盘/守灯塔
模式: 域全景扫描 → 分类 + 兼容/可用矩阵 → 判断输入 (Φ10)
数据源: 黑板 data/discovery/agents/<device> (R-ERR4) + 本地资产文档兜底
输出:
  A. 设备资产全景 (各设备: 能力/健康/在线)
  B. 能力×可用矩阵 (跨设备任务路由判断输入)
用法:
  device-audit.py scan              # 设备全景 (黑板 discovery)
  device-audit.py matrix            # 能力可用矩阵
  device-audit.py --lean4-check     # 自检
  device-audit.py --version
注: 骨架——黑板 discovery 未全注册时输出本地推断; 罗盘接入后可扩充
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/device-audit.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = "0.6.0"
# discovery 注册表在星桥服务器 (CENTRAL_BB) —— 与 bb-gate registry 同源
BLACKBOARD = os.environ.get("CENTRAL_BB", "http://xingqiao.meetfunbp.com:8792")
# 本地黑板 (nodes/<device> 真实能力上报)
LOCAL_BB = os.environ.get("LOCAL_BB", "http://127.0.0.1:8792")
# 设备 key 对齐 discovery 实际注册 (小写 mac-mini/i9/mbp + E2 store-<id>)
DEVICES = ["mac-mini", "i9", "mbp", "store-2", "store-7", "store-8", "phone"]
# 能力清单 (跨设备可路由任务类型)
CAPABILITIES = ["web_ui", "waimai", "voice", "vision", "design", "document",
                "research", "compute_gpu", "compute_cpu", "comm"]
# 各来源的【不可用条件】—— 2026-09-11 与 HR 对齐的通则：
#   「判据/门的输出里应含它的不可用条件」（与「缺 claim_target 即不得作为决策依据」同族）
SOURCE_CAVEAT = {
    "measure": "节点实测上报（映射）—— 可直接作为可行性依据；业务维度不含在内",
    "measure+infer": "实测（执行环境维度）+ 推断（业务维度）合并 —— 【推断那部分】不得作为实测依据",
    "register": "来源为 discovery 注册（非节点实测）—— 不得作为容量/性能依据",
    "infer_unreachable": "★ discovery 不可达 ⇒ 本行能力取自【本地兜底常量 FALLBACK】，"
                         "既非注册数据也非实测 —— 【不得作为设备状态/容量/在线性依据】",
    "infer": "纯本地推断，无实测支撑 —— 【不可作为容量/性能/在线性决策依据】",
}
# 节点原生能力 → 矩阵维度映射 (nodes/<device>.capabilities 实测上报)
NATIVE_MAP = {
    "gpu-cuda": ["compute_gpu"],
    "ollama": ["compute_gpu", "research"],   # 本地推理引擎 → 可跑分析任务
    "dsh": ["compute_cpu"],
    "python3": ["compute_cpu"],
    "shell": ["compute_cpu"],
    "rust-bridge": ["comm", "compute_cpu"],
    "file-e-drive": ["document"],
    "scan": ["document"],
    "info": [],
}
# 本地兜底能力推断 (远程 discovery 未注册/能力空时)
FALLBACK = {
    "mac-mini": ["web_ui", "waimai", "voice", "vision", "document", "research", "compute_cpu"],
    "i9": ["web_ui", "compute_gpu", "compute_cpu", "design", "research", "comm"],
    "mbp": ["web_ui", "design", "document", "research", "vision", "comm"],
    "store-2": ["waimai"], "store-7": ["waimai"], "store-8": ["waimai"],
    "phone": ["comm", "voice"],
}


def _read_node_caps(device: str) -> list:
    """读本地黑板 nodes/<device>.capabilities (节点实测上报, 非推断)"""
    try:
        with urllib.request.urlopen(f"{LOCAL_BB}/nodes/{device}", timeout=3) as r:
            v = json.loads(r.read()).get("value") or {}
        return v.get("capabilities", []) or []
    except Exception:
        return []


def _map_native(native: list) -> list:
    """节点原生能力 → 矩阵维度映射"""
    out = []
    for c in native:
        for m in NATIVE_MAP.get(c, []):
            if m not in out:
                out.append(m)
    return out


def _ts_age_sec(ts) -> tuple:
    """解析 ts → (年龄秒数, 时区语义说明)；无法解析返回 (-1, reason)

    时区处理（2026-09-11 修正 bug）：
      带 Z             → UTC（此前误当本地解析 → 年龄系统性多算 +08:00 = 8 小时）
      带 +HH:MM/-HH:MM → 对应偏移
      无标记(naive)     → 按本地解释，但标注 tz=local(无标记) 表示不确定
    """
    try:
        if isinstance(ts, (int, float)):
            return max(0.0, time.time() - float(ts)), "epoch"
        s = str(ts).strip()
        if not s:
            return -1, "empty"
        tz, tz_note = None, "local(无标记)"
        if s.endswith("Z"):
            base = s[:-1]
            tz, tz_note = datetime.timezone.utc, "UTC(Z)"
        else:
            m = re.search(r"([+-]\d{2}):?(\d{2})$", s)
            if m:
                sign = 1 if m.group(1)[0] == "+" else -1
                off = sign * (int(m.group(1)[1:]) * 60 + int(m.group(2)))
                tz = datetime.timezone(datetime.timedelta(minutes=off))
                tz_note = f"offset({m.group(1)}:{m.group(2)})"
                base = s[:m.start()]
            else:
                base = s
        base = base.strip()
        fmt = "%Y-%m-%dT%H:%M:%S" if len(base) <= 19 else "%Y-%m-%dT%H:%M:%S.%f"
        dt = datetime.datetime.strptime(base[:26], fmt)
        if tz is not None:
            dt = dt.replace(tzinfo=tz)
        return max(0.0, time.time() - dt.timestamp()), tz_note
    except Exception:
        return -1, "unparsable"


G5_MAX_AGE = 90.0   # 心跳新鲜度阈值（秒）


def _read_device(device: str) -> dict:
    """读黑板 data/discovery/agents/<device> (R-ERR4 注册表)

    消费侧防御（hazard-proxy-fallback-liveness-misreport 对策）：
      **不只看 status** —— 同时读 via（真实心跳 self vs 代理兜底 hb-fwd-*）
      + ts 新鲜度（G5）。因为 status 声明的对象是「设备在线」，
      但其实际指称可能是「代理链路活性」——字段适用对象 ≠ 声称对象。
    """
    try:
        with urllib.request.urlopen(f"{BLACKBOARD}/data/discovery/agents/{device}", timeout=3) as r:
            resp = json.loads(r.read())
            v = resp.get("value") or {}
            if not v:
                return {"registered": False, "device": device,
                        "capabilities": FALLBACK.get(device, []),
                        "note": "黑板未注册, 本地兜底推断"}
            v["registered"] = True
            v["device"] = v.get("device", device)
            # ★ 身份键四元组（实例 + 键 + 版本 + 时点）—— 2026-09-11 与 HR/守灯合并的通则
            _key = f"data/discovery/agents/{device}"
            v["source_instance"] = BLACKBOARD
            v["key"] = _key
            v["key_version"] = resp.get("version")
            v["envelope_ts"] = resp.get("ts")
            v["value_ts"] = v.get("ts")
            v["identity_key"] = (f"{BLACKBOARD}|{_key}|v{resp.get('version')}|"
                                 f"env:{resp.get('ts')}|val:{v.get('ts')}")
            # —— 消费侧防御①：via 区分真实 vs 代理 ——
            via = str(v.get("via", "") or "")
            if re.search(r"fwd|proxy|fallback", via, re.I):
                v["liveness"] = "proxied"
                v["liveness_note"] = f"status 系代理兜底(via={via})，不代表设备真实在线"
            else:
                v["liveness"] = "real" if (via == "self" or not via) else f"unknown({via})"
            # —— 消费侧防御②：ts 新鲜度（G5）——
            age, tz_note = _ts_age_sec(v.get("ts"))
            v["ts_field_read"] = "value.ts"   # 声明读哪个 ts（信封 ts 时区语义可能不同）
            v["tz_note"] = tz_note
            v["ts_age_sec"] = round(age, 1) if age >= 0 else None
            if age >= 0 and age > G5_MAX_AGE:
                v["liveness_stale"] = True
                v["liveness_note"] = (v.get("liveness_note", "") +
                                      f" | ts 陈旧 {age/3600:.1f}h（超 G5 {G5_MAX_AGE}s, tz={tz_note}）").strip(" |")
            return v
    except urllib.error.HTTPError as e:
        # ★ 2026-09-11 自查修复【不存在 vs 无法验证 混淆】：
        #   原实现把 HTTPError(404=可达但键不存在) 与 URLError(不可达) 一起吞进
        #   「黑板不可达」⇒ 与黑板语义（400=键非法 / 404=合法但不存在）冲突，
        #   也与本工具自己主张的消费侧纪律冲突。
        #   ⇒ 现分四态：可达+有值 / 可达+未注册(404) / 可达+其他HTTP错 / 不可达。
        if e.code == 404:
            return {"registered": False, "device": device,
                    "capabilities": FALLBACK.get(device, []),
                    "note": "黑板可达但未注册(404), 本地兜底推断",
                    "source_status": "absent"}
        return {"registered": False, "device": device,
                "capabilities": FALLBACK.get(device, []),
                "note": f"黑板可达但返回 HTTP {e.code}, 本地兜底推断",
                "source_status": "http_error"}
    except Exception:
        return {"registered": False, "device": device,
                "capabilities": FALLBACK.get(device, []),
                "note": "黑板不可达, 本地兜底推断",
                "source_status": "unreachable"}


def _stale_manifest_check() -> list:
    """清单陈旧自检（2026-09-11 与 HR 对齐的【零成本陈旧可检性】）

    背景：手工维护的常量（DEVICES 清单 / FALLBACK 推断）只在【被调用时】才可能暴露陈旧，
    而未调用的工具永不暴露 ⇒ 须让工具【主动自检清单是否陈旧】。
    做法：对比 discovery 实际注册的设备 vs 本地 DEVICES 清单。
    """
    notes = []
    try:
        with urllib.request.urlopen(f"{BLACKBOARD}/data/discovery/agents/", timeout=5) as r:
            lst = json.loads(r.read()).get("list", {}) or {}
        actual = {k.rsplit("/", 1)[-1] for k in lst if k.startswith("data/discovery/agents/")}
        # 方向1：discovery 有、清单无（清单缺漏）
        extra = actual - set(DEVICES)
        if extra:
            notes.append(f"★ DEVICES 清单可能陈旧：discovery 已注册但未列入 → {sorted(extra)}")
        # 方向2：清单有、discovery 无（清单可能含已移除/不存在项）
        # ★ 2026-09-11 变异测试发现：此前只检方向1 ⇒ 单向缺陷（补方向2，排除已知未注册白名单）
        KNOWN_UNREGISTERED = {"phone"}   # 已知未注册（离线/未部署代理）
        stale_in_list = set(DEVICES) - actual - KNOWN_UNREGISTERED
        if stale_in_list:
            notes.append(f"⚠️ DEVICES 含 discovery 未注册项（非已知离线）→ {sorted(stale_in_list)}")
        if not actual:
            notes.append("discovery 列表为空，无法校验 DEVICES 清单")
        else:
            notes.append(f"清单核对（discovery {len(actual)} 项 · DEVICES {len(DEVICES)} 项 · "
                         f"缺漏 {len(extra)} · 多余 {len(stale_in_list)}）")
    except Exception as e:
        notes.append(f"清单陈旧校验跳过（discovery 不可达: {str(e)[:40]}）")
    return notes


def _env_facts() -> dict:
    """环境维（2026-09-11 HR 指出：produced_how ≠ 环境 E 的全部）

    与明鉴『A 在环境 E 下核实了对象 O』同构——produced_by=A · source_instance=O · ts=时点，
    而【环境 E】需单列（沙箱/权限/可达性）。未探测的项如实标注，不假装已知。
    """
    return {
        "cwd": os.getcwd(),
        "python": sys.version.split()[0],
        "sandbox": "未探测（本工具不探测自身沙箱模式）",
        "notes": "可达性见各设备条目（逐条 GET 结果）；权限未探测",
    }


def _declaration() -> dict:
    """声明块（2026-09-11 补齐第五项 env；并确保【失败路径也写声明】）

    HR 判据：凡声明字段只在成功路径写入 ⇒ 属『失效路径机制』⇒ 被动扫描看不见。
    失败时不写会被读成『旧版本工具』（无名归因）⇒ 故声明与 status 一同输出。
    """
    return {
        "produced_by": f"device-audit v{VERSION}",
        "produced_how": "黑板 GET → 消费侧防御（via/ts 双读 + 时区感知）",
        "scan_ts": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "source_instance": BLACKBOARD,
        "env": _env_facts(),
        # ★ 样板已知缺口清单（2026-09-11 HR 指出：样板须附缺口清单，否则照抄者会把缺陷一并复制
        #   —— 共因失效：一致性上升的同时缺陷复制面也上升。这是「判据含不可用条件」的样板层版本）
        "known_gaps": [
            "sandbox 未探测（本工具不探测自身沙箱模式）",
            "权限未探测（不声称具备任何写权限）",
            "env 不含网络可达性的独立探测（可达性体现在各设备条目 GET 结果上）",
            "produced_how 是【手段摘要】非环境全部——环境另见 env 字段",
        ],
    }


def scan() -> dict:
    """A: 设备资产全景（声明含 env 维；失败路径同样携带完整声明）"""
    decl = _declaration()
    try:
        devices = []
        for d in DEVICES:
            info = _read_device(d)
            devices.append(info)
        # ★ 2026-09-11 自查修复【status 恒真】：原实现无条件写 "ok"，
        #   即使 discovery 完全不可达、全部设备走本地兜底推断也报 ok
        #   ⇒ status 不携带任何信息（三问之「恒假/门永不触发」的同族：
        #   字段存在、永不为另一态 ⇒ 读它的人得到虚假保证）。
        unreach = [str(d.get("device")) for d in devices
                   if "黑板不可达" in str(d.get("note", ""))]
        if unreach:
            status = "degraded"
            degraded_reason = (f"discovery 不可达 ⇒ {len(unreach)}/{len(devices)} 条走"
                               f"本地兜底推断（{','.join(unreach)}）；该批数据【非实测】，"
                               f"不得作为设备状态证据")
        else:
            status, degraded_reason = "ok", None
        return {**decl,
                "status": status,
                "degraded_reason": degraded_reason,
                "devices": devices,
                "registered": sum(1 for d in devices if d.get("registered")),
                "manifest_check": _stale_manifest_check()}
    except Exception as e:
        # ★ 失败路径不静默省略声明（否则读者把「无声明」读成「旧版本工具」）
        return {**decl,
                "status": "failed",
                "reason": str(e)[:200],
                "devices": [],
                "registered": 0,
                "manifest_check": []}


def matrix() -> dict:
    """B: 能力×设备可用矩阵
    合并策略: nodes/<device> 实测能力(映射, 优先) + FALLBACK 业务维度补充
    _source: measure(纯实测) / measure+infer(实测+推断补充) / register / infer
    """
    rows = {}
    for d in DEVICES:
        info = _read_device(d)
        native = _read_node_caps(d)
        mapped = set(_map_native(native))
        fallback = set(FALLBACK.get(d, []))
        # ★ 2026-09-11 自查修复【归属错】：discovery 不可达时 _read_device 会把
        #   FALLBACK 常量放进 capabilities，原逻辑据此标 source="register"
        #   ⇒ 数据是兜底常量，却标注「来源为 discovery 注册」——**指向一个没有产出它的源**。
        #   属今晚「数值/词义/人称归属错」家族的【数值归属】维（值对、绑定的来源错）。
        unreachable = "黑板不可达" in str(info.get("note", ""))
        if mapped:
            caps = mapped | fallback        # 实测优先 + 推断补充业务维度
            source = "measure+infer"
            # 纯实测(推断无新增)时标 measure
            if not (fallback - mapped):
                source = "measure"
        elif unreachable:
            caps = set(info.get("capabilities") or fallback)
            source = "infer_unreachable"
        elif info.get("capabilities"):
            caps = set(info["capabilities"])
            source = "register"
        else:
            caps = fallback
            source = "infer"
        row = {c: (c in caps) for c in CAPABILITIES}
        row["_source"] = source
        row["_source_caveat"] = SOURCE_CAVEAT.get(source, "未定义来源 —— 不可作为决策依据")
        row["_produced_by"] = f"device-audit v{VERSION}"   # 声明来源（谁测的）
        if native:
            row["_native"] = native
        rows[d] = row
    return rows


def _ast_write_ops(src: str) -> tuple:
    """AST 语义级检测写入操作（2026-09-11 替换文本正则）

    为什么换：文本正则会命中【注释/字符串里的模式描述】——包括检测器自己写的模式字面
    （实测自匹配假阳性）。AST 只看代码结构，天然避开注释与字符串。
    返回 (has_write: bool, evidence: str)
    """
    import ast as _ast
    try:
        tree = _ast.parse(src)
    except SyntaxError as e:
        return True, f"源码无法解析: {e}"
    # ★ 按「模块+方法」精确匹配（2026-09-11 修正：只按方法名会误判 str.replace/datetime.replace）
    WRITE_CALLS = {
        ("os", "remove"), ("os", "unlink"), ("os", "rmdir"), ("os", "mkdir"),
        ("os", "makedirs"), ("os", "system"), ("os", "rename"), ("os", "replace"),
        ("shutil", "rmtree"), ("shutil", "move"), ("shutil", "copy"), ("shutil", "copy2"),
        ("subprocess", "run"), ("subprocess", "call"), ("subprocess", "check_call"),
        ("subprocess", "check_output"), ("subprocess", "Popen"),
    }
    PATHLIB_WRITE = {"write_text", "write_bytes", "unlink", "rmdir", "mkdir", "touch"}
    for node in _ast.walk(tree):
        if not isinstance(node, _ast.Call):
            continue
        f = node.func
        if isinstance(f, _ast.Attribute):
            # 提取 mod：可为 Name（os/shutil/subprocess）或 Call（Path("f").write_text）
            # ★ 2026-09-11 修复：原写法只取 .id，导致 Path("f").write_text() 检测失效
            #   （由 --samples 独立复跑抓出）
            _v = f.value
            if isinstance(_v, _ast.Name):
                mod = _v.id
            elif isinstance(_v, _ast.Call) and isinstance(_v.func, _ast.Name):
                mod = _v.func.id
            else:
                mod = "?"
            if (mod, f.attr) in WRITE_CALLS:
                return True, f"{mod}.{f.attr}() @L{node.lineno}"
            if f.attr in PATHLIB_WRITE and mod in ("Path", "p"):
                return True, f"{mod}.{f.attr}() @L{node.lineno}"
        elif isinstance(f, _ast.Name) and f.id == "open":
            modes = []
            for a in node.args[1:]:
                if isinstance(a, _ast.Constant) and isinstance(a.value, str):
                    modes.append(a.value)
            for kw in node.keywords:
                if kw.arg == "mode" and isinstance(kw.value, _ast.Constant):
                    modes.append(str(kw.value.value))
            if any(("w" in m or "a" in m or "+" in m) for m in modes):
                return True, f"open(mode={modes}) @L{node.lineno}"
    return False, "无写入调用（AST 语义检查）"


def _samples_check() -> int:
    """对照样本独立复跑（2026-09-11 HR 判据：读者能否在【不改工具】前提下独立复跑对照）

    输出每个样本的 期望/实际/一致性 —— 期望值在样本表内【硬编码声明】，
    故读者可独自核验：若工具行为变了，本命令会报不一致。
    """
    samples = [
        ("正控 · 含 os.system 调用", 'import os\nos.system("x")\n', True),
        ("反控 · 注释里的 os.system（无调用）", '# os.system("x")\nx = 1\n', False),
        ("自指控 · 模式字面落在字符串里", 'PAT = "os.system"\n', False),
        ("反控2 · pathlib.write_text 调用", 'from pathlib import Path\nPath("f").write_text("x")\n', True),
        ("反控3 · 字符串里的 rm -rf（无调用）", 'S = "rm -rf /tmp"\n', False),
    ]
    ok = True
    print(f"== 对照样本独立复跑 (device-audit v{VERSION}) ==")
    print("说明：本命令可独立运行核验检测器行为——期望值硬编码在下表，工具行为变化即报不一致。")
    for name, code, expect in samples:
        got, ev = _ast_write_ops(code)
        same = (got == expect)
        ok = ok and same
        print(f"  [{'✅' if same else '❌'}] {name}")
        print(f"       期望={expect} · 实际={got} · {ev}")
    print(f"  结果: {'✅ 全部一致（检测器行为符合声明）' if ok else '❌ 存在不一致'}")
    print("  适用范围：仅【模式匹配类判据】的正/反控核验；不适用于语义一致性类判据")
    return 0 if ok else 1


def _fallback_check() -> int:
    """FALLBACK 失效路径【主动检出】（2026-09-11 HR 命名『失效路径机制』）

    为何不能被动检出：FALLBACK 是「discovery 失败时才走的路」⇒ discovery 不失败就永远测不到
    ⇒ 故：主动制造失效 + 断言兜底行为（与三问的阳性对照同一手法）。

    检查：
      ① 制造失效（黑板指向必然不可达地址）→ 断言确实走了兜底分支
      ② 断言兜底提供能力（非空）
      ③ 断言兜底覆盖清单（DEVICES ⊆ FALLBACK）—— 否则报「FALLBACK 静默陈旧」
    """
    global BLACKBOARD
    ok = True
    print(f"== FALLBACK 失效路径主动检出 (device-audit v{VERSION}) ==")
    print("  机制说明：只在 discovery 失败时生效 ⇒ 被动扫描看不到 ⇒ 本检查主动制造失效")
    orig = BLACKBOARD
    try:
        BLACKBOARD = "http://127.0.0.1:1"      # 必然不可达（制造失效）
        info = _read_device("i9")
        went = (not info.get("registered")) and bool(info.get("capabilities"))
        ok = ok and went
        print(f"  [{'✅' if went else '❌'}] ① 制造失效后走到兜底分支"
              f"（registered={info.get('registered')} · caps={len(info.get('capabilities') or [])} 项）")
        print(f"        证据：{info.get('note','')} · 能力={info.get('capabilities')}")
    finally:
        BLACKBOARD = orig
    missing = [d for d in DEVICES if d not in FALLBACK]
    covered = not missing
    ok = ok and covered
    print(f"  [{'✅' if covered else '❌'}] ② FALLBACK 覆盖 DEVICES 清单"
          f"{'' if covered else f' —— ★ 静默陈旧：缺 {missing}'}")
    risky = [d for d in FALLBACK if d not in DEVICES]
    if risky:
        print(f"  ⚠️ 提示：FALLBACK 含清单外设备 {risky}（可能反向陈旧）")
    print("  范围声明：本检查仅覆盖【本地 FALLBACK 分支】；不覆盖 discovery 侧真实故障场景")
    print(f"  结果: {'✅ 兜底行为符合声明' if ok else '❌ 兜底行为不符合声明'}")
    return 0 if ok else 1


def _lean4_check() -> int:
    ok = True
    out = [f"== Lean4 约束门自检 (device-audit v{VERSION}) =="]
    src = open(__file__).read()
    has_write, write_ev = _ast_write_ops(src)
    checks = [
        ("① 只读无破坏写（AST 语义检测调用节点；不受注释/字符串干扰）", not has_write),
        ("② scan 返回结构", "devices" in scan()),
        ("③ matrix 返回 dict", isinstance(matrix(), dict)),
    ]
    for label, cond in checks:
        out.append(f"  [{'✅' if cond else '❌'}] {label}")
        ok = ok and cond
    # —— 三问自检（2026-09-11 与 HR 对齐：模式匹配类判据上线前必问）——
    #   ① 自指（判据命中自己）② 空通过（看的层≠声称的层）③ 恒假（永不响）
    _pos = _ast_write_ops('import os\nos.system("x")\n')        # 正控：含写入调用 → 应 True
    _neg = _ast_write_ops('# os.system("x") 仅注释\nx = 1\n')    # 反控：注释/字符串 → 应 False
    _q1 = not has_write                                          # 自指：自身扫描不因模式字面而命中
    _q2 = (_pos[0] is True and _neg[0] is False)                 # 空通过：能区分调用 vs 注释（层对齐）
    _q3 = _pos[0] is True                                        # 恒假：存在必然触发的输入
    out.append("  三问自检（模式匹配类判据上线前必问）:")
    out.append(f"    [{'✅' if _q1 else '❌'}] ① 自指——判据会命中它自己吗"
               f"（AST 只看调用节点，模式字面不在扫描对象集内）")
    out.append(f"    [{'✅' if _q2 else '❌'}] ② 空通过——它看的层 = 声称的层吗"
               f"（正控 os.system→True · 反控 注释→False，证明层对齐）")
    out.append(f"    [{'✅' if _q3 else '❌'}] ③ 恒假——存在必然响的输入吗（正控可触发）")
    # ★ 三问自身的适用范围（2026-09-11 HR 指出：三问本身也是判据，须含不可用条件）
    out.append("    适用范围：仅【模式匹配类判据】—— 不适用于语义一致性类判据"
               "（如「声明与实现是否一致」）；域外误用请勿套用")
    out.append("    对照可复跑：运行 `device-audit.py --samples` 可独立核验上述正/反控"
               "（无需修改本工具）")
    ok = ok and _q1 and _q2 and _q3
    out.append(f"  结果: {'✅ GATE OK' if ok else '❌ GATE FAIL'}")
    # —— 作用域声明（2026-09-11 与 HR 对齐：声称的作用域须与实际覆盖的域一致）——
    out.append(f"  作用域声明：本自检仅【AST 语义检测 + 结构检查 {os.path.basename(__file__)} 自身源码】——"
               f"不覆盖运行时行为、不覆盖被调用的外部工具与依赖库、不覆盖网络响应内容")
    print("\n".join(out))
    return 0 if ok else 1


def _exit_for(doc: dict) -> int:
    """退出码承载可用性（修「把失败映射成成功」的同族缺陷）。

    ★ 2026-09-11 自查发现：原实现任何时候都 exit 0，而 status 恒为 "ok"
    ⇒ 调用方 `device-audit.py scan || 告警` 永不触发；只看 $? 的消费者
    把「降级/失败」读成「成功」。
    现约定：0=ok / 2=degraded / 1=failed。**降级不并回 ok**（否则等于没有降级态）。
    """
    st = str(doc.get("status", "ok"))
    return {"ok": 0, "degraded": 2, "failed": 1}.get(st, 2)


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--samples" in args:
        raise SystemExit(_samples_check())
    if "--fallback-check" in args:
        raise SystemExit(_fallback_check())
    if "--lean4-check" in args:
        raise SystemExit(_lean4_check())
    if "--version" in args:
        print(f"device-audit v{VERSION}")
        raise SystemExit(0)
    if not args or args[0] == "scan":
        _s = scan()
        print(json.dumps(_s, ensure_ascii=False, indent=2))
        raise SystemExit(_exit_for(_s))
    elif args[0] == "matrix":
        _m = matrix()
        print(json.dumps(_m, ensure_ascii=False, indent=2))
        # matrix 输出形状为「设备→行」不设顶层 status；按行 _source 聚合可用性，
        # 不改输出形状（改形状会破坏既有消费者）。
        bad = sum(1 for r in _m.values()
                  if isinstance(r, dict) and r.get("_source") in ("infer_unreachable",))
        raise SystemExit(2 if bad else 0)
    else:
        # ★ 2026-09-11 修复【闭门残留】：新命令此前未列入 help ⇒ 可执行但不可发现
        #   （HR 命名「闭门对照」的残留形态：对照存在但外部不可达）
        print(f"""device-audit v{VERSION} — 设备资产全景 + 能力×可用矩阵（只读）

用法:
  device-audit.py scan              设备资产全景（含清单陈旧自检）
  device-audit.py matrix            能力×设备可用矩阵（含来源与不可用条件）
  device-audit.py --lean4-check     约束门自检（含三问 + 作用域声明）
  device-audit.py --samples         ★ 对照样本独立复跑（读者可核验检测器行为，无需改工具）
  device-audit.py --fallback-check  ★ 失效路径主动检出（制造失效 → 断言兜底行为）
  device-audit.py --version         版本
  device-audit.py --help            本帮助

退出码（2026-09-11 起，承载可用性）:
  0 = ok        全部输入可达
  2 = degraded  部分/全部输入不可达（数据走本地兜底推断，详见 degraded_reason）
  1 = failed    未捕获失败
  ★ 降级不并回 0 —— 否则 `device-audit.py scan || 告警` 永不触发，只看 $? 的
    消费者会把「降级」读成「成功」（本工具曾如此，v0.6.0 修正）。
  ★ 源状态四态（每设备 source_status）: 有值 / absent(404 可达但未注册) /
    http_error / unreachable —— 404 与「不可达」不可混为一谈。

声明: 输出含 produced_by / produced_how / scan_ts / source_instance / env / known_gaps
范围: 仅只读（黑板 GET），不写任何存储；不覆盖运行时行为与依赖库""")
