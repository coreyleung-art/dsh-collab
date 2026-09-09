#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""comm_domains v1.1 — 通讯域流向单源矩阵 (Lean4 同源 · bb-gate + 同步层共用)

域矩阵单一来源: sync-up/down/hb-fwd 与 bb-gate 均引用本表, 防多份维护漂移。
流向语义:
  UP    = mac-mini 本机键上行中枢 (sync-to-central)
  DOWN  = 中枢 i9/mbp 域键下行本机 (sync-from-central) + 设备双写域
  HB    = 心跳节点域 (hb-forward 转发)
  LOCAL = 仅本机 (不跨端)

角色写权 (G1 域权, bb-gate 引用): 设备只写自域; coordinator 全域。

v1.1 (2026-09-09 · §3.1 设备内通讯结构门, G-C39/G-C40):
  notes/collab/ 是广播域(上行中枢 → 端侧 i9/mbp 可见)。按 §3.1「设备内
  角色沟通不走服务器」, 只有带「广播语义」的卡才允许落 collab 并被 sync-up
  上行: ① 守护信封转写(type=bus-envelope/含 _bus) ② action 前缀
  broadcast-/collab- ③ 显式 scope/kind ∈ {broadcast, collab}。
  无标记的治理/回执/报告卡 = 设备内消息 → 本机角色域(notes/<role>/), 禁 collab。
"""
import os

# ═══════════ 域流向表 ═══════════
# 前缀 → (流向, 所有者)
UP_DOMAINS = [
    ("notes/collab/", "mac-mini"),        # 广播域: mac-mini 上行中枢
    ("notes/mac-mini/", "mac-mini"),      # mac-mini 会话域
    ("tasks/central/queue/", "mac-mini"), # 任务队列
    ("data/asset-inventory/", "mac-mini"),
    ("data/rules/", "mac-mini"),
    ("data/blueprint/", "mac-mini"),
]
DOWN_DOMAINS = [
    ("notes/i9/", "i9"),    # i9 消息域: 中枢下行本机 + i9 双写
    ("notes/mbp/", "mbp"),  # MBP 消息域
    # 门店域 (2026-09-07 Windows 试点): notes/store-<id>/ = 门店瘦采集数据域
    # store-reader 角色 (门店采集器) 只写本店数据域, 无动作原语 (lean4 无写门)
]
STORE_DOMAIN_PREFIX = "notes/store-"


def is_store_domain(key):
    """门店数据域判定: notes/store-<id>/ 前缀"""
    return key.startswith(STORE_DOMAIN_PREFIX)


def store_id_of(key):
    """从键提取 store id (notes/store-3/xxx → store-3)"""
    rest = key[len(STORE_DOMAIN_PREFIX):]
    return rest.split("/", 1)[0] if "/" in rest else rest
HB_NODES = ["i9", "mbp", "mac-mini"]  # hb-fwd 转发节点
OTHER_UP = ["notes/session-fa1f9150/", "notes/cld-monitor/", "data/ops/", "data/registry/", "data/gates/", "data/device/"]

# 角色写权 (G1)
ROLE_DOMAINS = {
    # i9 白名单(2026-09-06 用户批): +notes/mbp/ 真直连——i9 消息可直写 MBP 域(经中枢双写)
    "i9": ["notes/i9/", "notes/mbp/", "nodes/i9/"],
    "mbp": ["notes/mbp/", "nodes/mbp/"],
    "mac-mini": ["notes/mac-mini/", "nodes/mac-mini/", "notes/collab/"] + OTHER_UP,
    "coordinator": ["notes/", "nodes/", "data/", "tasks/"],
    # store-reader: 门店采集器 (Windows 试点) —— 只写本店 notes/store-<id>/ 数据域
    # 动态匹配: 写权 = 键前缀 notes/store/<own-store-id>/ (bb-gate can_write 校验)
    "store-reader": [],
}
COORDINATORS = {"coordinator", "session-fa1f9150-c949-401f-ba8c-d265f6221676"}

# ═══════════ v1.1 collab 广播语义门 (G-C39/G-C40 · §3.1) ═══════════
BROADCAST_MARKERS = ("broadcast", "collab")
ENVELOPE_TYPES = ("bus-envelope",)
BROADCAST_ACTION_PREFIXES = ("broadcast-", "collab-")

# ═══════════ v1.2 类型/收件人归属层 (R-ERR6 误投根治 · G-C41) ═══════════
# 服务器需要的不只是 target/域级拦截, 而是「收件人语义 → 合法投递面」的自动判定:
# 一张卡 to=星桥/司库HR(全 mac-mini 本机角色) → 设备内内容, 即便误落 collab 也不得上行中央(防 i9/mbp 收到)。
# 用户(2026-09-09): 「服务器有没有类型管理器/错误投递自动拦截分发器」→ 本层即该管理器的判定核心。
LOCAL_ROLES = frozenset((
    "星桥", "明鉴", "司库", "守灯", "守望", "守灯塔", "守链", "罗盘", "老登",
    "知了", "验金石", "回声", "灯塔", "文汇", "驿使", "数据调查员", "星舵", "拾光", "明鉴v2", "用户洞察",
    "coordinator", "协调者", "mac协调者", "星桥/mac协调者",
))
ADMIN_HOME_ALIASES = frozenset(("管理员", "人工", "human", "admin", "mac-mini", "server", "server:coordinator", "mac-mini:星桥", "mac-mini:coordinator"))
EDGE_DEVICES = frozenset(("mbp", "i9", "any", "collab", "broadcast"))
_IMPORT_RE = None


def _recipient_home(rec):
    """单个收件人 → 归属设备; None=无法判定(保守: 不当成本机)"""
    rec = rec.strip()
    if not rec:
        return None
    if "(" in rec:  # 去角色后附的会话标注, 如 司库HR(2a15e6b1)
        rec = rec.split("(", 1)[0].strip()
    # 别名归正: 司库HR/HR → 司库(本机)
    rec = {"司库HR": "司库", "HR": "司库", "HR司库": "司库"}.get(rec, rec)
    if ":" in rec:
        prefix = rec.split(":", 1)[0]
        if prefix in ("mbp", "i9"):
            return prefix
        if prefix in ("mac-mini", "server") or prefix.startswith("session-"):
            return "mac-mini"
    if rec in ("mbp", "i9"):
        return rec
    if rec in EDGE_DEVICES:
        return "mac-mini"
    if rec in ADMIN_HOME_ALIASES:
        return "mac-mini"
    if rec in LOCAL_ROLES:
        return "mac-mini"
    if rec.startswith("session-"):
        return "mac-mini"
    return None  # 未知角色/设备 → 不能证明本机


def recipient_home_only(val):
    """类型层判定: 卡的收件人(to/to_full, 支持 / + 空格 多候选)是否全部归属本机(mac-mini)
    True = 设备内卡(禁 collab 禁上行——即使误写广播域也在 sync-up/写入门被拦)"""
    if not isinstance(val, dict):
        return False
    raw = str(val.get("to_full") or val.get("to") or "")
    if not raw or raw in ("any", "broadcast", "collab"):
        return False
    global _IMPORT_RE
    if _IMPORT_RE is None:
        import re as _re
        _IMPORT_RE = _re.compile(r"[/+\s,，、&]+")
    toks = [t for t in _IMPORT_RE.split(raw) if t.strip()]
    if not toks:
        return False
    for t in toks:
        if _recipient_home(t) != "mac-mini":
            return False
    return True


def collab_broadcast_ok(val):
    """collab 卡是否带广播语义（允许落 collab / 被 sync-up 上行）：
    ① type=bus-envelope（守护信封转写, MBP/i9 落卡走此）
    ② type/action/subject 前缀 broadcast-/collab-（显式广播）
    ③ 含 _bus 信封字段
    ④ 显式 scope/kind ∈ {broadcast, collab}
    无标记的治理/回执/报告/评审卡 = 设备内消息 → 不进广播域（§3.1 结构门）"""
    if not isinstance(val, dict):
        return False
    if str(val.get("type") or "") in ENVELOPE_TYPES:
        return True
    if str(val.get("_bus") or "") != "":
        return True
    t = str(val.get("type") or val.get("action") or val.get("subject") or "")
    if t.startswith(BROADCAST_ACTION_PREFIXES):
        return True
    # v1.2 类型层(R-ERR6 · G-C41): 无广播标记且收件人全为本机角色 → 设备内卡
    #   ——即使误写 collab / 误带 scope, 也按收件人语义拦截(类型管理器判定核心)
    if recipient_home_only(val):
        return False
    return str(val.get("scope") or val.get("kind") or "") in BROADCAST_MARKERS


def collab_writable(role, key, val):
    """bb-gate G4(§3.1): 写 notes/collab/ = 域权(G1) + 广播语义双门"""
    if not can_write(role, key):
        return False
    if key.startswith("notes/collab/"):
        return collab_broadcast_ok(val)
    return True


def is_up_domain(key):
    """sync-up 上行域判定 (mac-mini → 中枢)"""
    if any(key.startswith(d) for d, _ in UP_DOMAINS):
        return True
    if any(key.startswith(d) for d in OTHER_UP):
        return True
    return False


def is_down_domain(key):
    """sync-down 下行域判定 (中枢 i9/mbp → 本机)"""
    return any(key.startswith(d) for d, _ in DOWN_DOMAINS)


def is_self_domain(key):
    """SELF_PREFIXES: 本机推上去的键不镜像回 (防回声)"""
    return is_up_domain(key)


def can_write(role, key):
    """G1: 角色域权 (与 bb-gate 同源)"""
    if role in COORDINATORS:
        return True
    if role.startswith("session-"):
        return key.startswith(f"notes/{role}/") or key.startswith("notes/mac-mini/")
    # store-reader 动态规则: store-reader-<store-id> 只写本店 notes/store-<store-id>/
    # store-id 约定纯数字 (store-reader-3 → notes/store-3/); 兼容 store- 前缀写法
    if role.startswith("store-reader-"):
        store_id = role[len("store-reader-"):]
        if store_id.startswith("store-"):
            store_id = store_id[len("store-"):]
        return key.startswith(f"notes/store/{store_id}/") or key.startswith(f"notes/store-{store_id}/")
    domains = ROLE_DOMAINS.get(role, [])
    return any(key.startswith(d) for d in domains)


def should_mirror(key, role):
    """G3: 设备自域消息镜像中枢 (i9/mbp 直写时双写)"""
    if role not in ("i9", "mbp"):
        return False
    return is_down_domain(key)


def up_domains_as_prefixes():
    """sync-up 用前缀列表 (UP_PREFIXES 单源)"""
    return tuple(d for d, _ in UP_DOMAINS) + tuple(OTHER_UP)


def down_domains_as_prefixes():
    return tuple(d for d, _ in DOWN_DOMAINS)


def self_domains_as_prefixes():
    """防回声前缀 (sync-down SELF_PREFIXES 单源)"""
    return up_domains_as_prefixes()


if __name__ == "__main__":
    # 自检
    assert is_up_domain("notes/collab/x"), "collab 应上行"
    assert is_up_domain("notes/mac-mini/x"), "mac-mini 应上行"
    assert is_down_domain("notes/i9/x"), "i9 应下行"
    assert not is_up_domain("notes/i9/x"), "i9 不应上行"
    assert can_write("i9", "notes/i9/x"), "i9 写自域"
    assert not can_write("i9", "notes/mac-mini/x"), "i9 越权拒"
    assert can_write("coordinator", "notes/i9/x"), "协调者全域"
    assert should_mirror("notes/i9/x", "i9"), "i9 双写"
    assert not should_mirror("notes/i9/x", "mac-mini"), "mac-mini 不双写"
    # v1.1 广播语义门自检 (G-C39/G-C40)
    assert not collab_broadcast_ok({"content": "治理回执", "type": "ack"}), "无标记治理卡=设备内, 拒"
    assert collab_broadcast_ok({"type": "bus-envelope", "_bus": {"task_id": "t"}}), "守护信封转写放行"
    assert collab_broadcast_ok({"action": "broadcast-update", "content": "x"}), "broadcast- 前缀放行"
    assert collab_broadcast_ok({"scope": "broadcast", "content": "x"}), "显式 scope=broadcast 放行"
    assert not collab_broadcast_ok({"content": "not-a-dict"}), "非 dict 拒"
    assert collab_writable("coordinator", "notes/collab/x", {"type": "bus-envelope", "_bus": {"t": 1}}), "协调者信封落 collab 放行"
    assert not collab_writable("coordinator", "notes/collab/x", {"type": "review"}), "coordinator 无标记卡也禁 collab"
    assert not collab_writable("mbp", "notes/collab/x", {"type": "bus-envelope"}), "mbp 无 collab 域权(G1)"
    assert collab_broadcast_ok({"type": "bus-envelope", "_bus": {"t": 1}}), "MBP 信封(直写)过语义(上行过滤层放行)"
    # v1.2 收件人归属类型层 (G-C41 · R-ERR6 根治)
    assert recipient_home_only({"to": "星桥", "content": "x"}), "to=星桥(本机) → 设备内"
    assert recipient_home_only({"to": "司库HR", "content": "x"}), "to=司库HR → 设备内(HR 本机角色, 别名)"
    assert recipient_home_only({"to_full": "星桥/mac协调者"}), "多候选斜杠全本机 → 设备内"
    assert not recipient_home_only({"to": "mbp:mbp-bus"}), "to=MBP → 跨设备"
    assert not recipient_home_only({"to": "星桥+mbp:mbp-bus"}), "混收件人含 MBP → 跨设备"
    assert not collab_broadcast_ok({"type": "stage-gate", "to": "星桥", "content": "x"}), "无标记+本机收件人 → 禁广播(R-ERR6 类)"
    assert collab_broadcast_ok({"type": "bus-envelope", "_bus": {"task_id": "t"}, "to": "星桥"}), "信封转写豁免类型层(合法通道)"
    print("✅ comm_domains v1.2 自检全过")
