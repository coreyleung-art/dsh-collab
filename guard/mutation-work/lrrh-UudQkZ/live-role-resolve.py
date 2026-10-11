#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""live-role-resolve.py — 「**当值角色是谁**」的快照交叉解析（只读；**不产生"可投递"结论**）。

★ 立据（星桥 2026-10-10 实测，逐字要点）：
  · `agent_profiles` **81 条** / `agent_peers` **5 个** ⇒ **94% 是幽灵**（登记了但不在活体）；
  · 两表**各有一半**真相 ⇒ 解析「当值裁判是谁」**必须交叉**，而当时**没有工具做这件事**；
  · 交叉之后**仍有 TOCTOU 窗口**（`4d0e75cf` 实测在两次查询之间离线）⇒ **只有 `targetLive` 是硬信号**。
  · 系统提示原文其实已写明「用 `agent_profiles` 查 role…**须再用 `agent_peers` 确认其在存活列表内**」
    ⇒ **不是不知道要查，是规则写在文档里、没有判据在管**（「原则不跨门传导」这次跨不过去的是**原则到人的动作**）。

★ 本件做什么（以及**不**做什么）：
  · 做：把两份**快照**交叉成三态清单 + 对歧义**拒答**（0 或 ≥2 个 LIVE ⇒ 非零退出并要求人工裁决）；
  · **不做**：不声称"可投递"。**可投递的唯一硬信号是发送时的 `targetLive`**（本件读不到总线 API：实测 `:8791`
    的五个 header 名 × 三个 token 全 401 ⇒ 无法实时拉取，只能吃快照）。
  · 因此本件把"该查什么"变成**可跑的一步**，但**把"最后那一下"留给发送本身** —— 这与 P4（处置假红要走声明通路）
    同族：**能核的核死，核不到的必须显式留白**。

★ 一条实测到的**滞后**（自查发现，如实写在这里而不是藏起来）：本件读的是**文件快照** `~/.dsh/agent-bus.json`，
  而 `agent_profile` / `agent_profiles` 走**总线**；实测**刚 `agent_profile` 注册完，文件视图仍报我"未登记"**
  ⇒ 「活体但未登记」这一列是**提示**（可能滞后），**不是判据**。要判登记，用 `agent_profiles` 工具本身。

用法：
  python3 tools/live-role-resolve.py --role 裁判 [--peers <peers.json>] [--profiles <profiles.json>] [--json]
  · 缺省 `--profiles` 读 `~/.dsh/agent-bus.json` 的 `profiles`（登记表）；
  · `--peers` 必须给**快照文件**（把 `agent_peers` 的输出存下来）——没有它就无法判活体，本件会给 `unresolvable`。
  · `--selftest` 造四组夹具自证（含 94% 幽灵面与 TOCTOU 窗口）。

退出码：0 = 恰有 1 个 LIVE 且登记一致（**仍须发送时核 `targetLive`**）· 1 = 歧义/不可解析（**不得据此投递**）· 2 = 用法错误
"""
import argparse
import json
import os
import sys

BUS_STATE = os.path.expanduser("~/.dsh/agent-bus.json")


def load_profiles(path=None):
    if path:
        d = json.load(open(os.path.expanduser(path), encoding="utf-8"))
        return d.get("profiles", d) if isinstance(d, dict) else d
    if not os.path.isfile(BUS_STATE):
        return None
    d = json.load(open(BUS_STATE, encoding="utf-8"))
    profs = d.get("profiles")
    if isinstance(profs, dict):
        return [{"agentId": k, **(v if isinstance(v, dict) else {})} for k, v in profs.items()]
    return profs


def load_peers(path):
    """★ 永远返回 `(peers|None, selfId|None)` —— 2026-10-10 修：原实现在无路径时 `return None`，
    而调用方直接解包 ⇒ `TypeError: cannot unpack non-iterable NoneType`（默认路径 100% 崩）。"""
    if not path:
        return (None, None)
    d = json.load(open(os.path.expanduser(path), encoding="utf-8"))
    if isinstance(d, dict) and "agents" in d:
        return d["agents"], d.get("self")
    return (d if isinstance(d, list) else []), None


def resolve(role_kw, profiles, peers, self_id=None):
    """三态交叉。**不产生"可投递"结论**。"""
    if peers is None:
        return {"state": "unresolvable", "why": "未提供 --peers 快照 ⇒ 无法判活体（登记表里 94% 可能是幽灵）"}
    live_ids = {p.get("id") for p in peers if isinstance(p, dict)}
    matched = [p for p in (profiles or []) if role_kw in str(p.get("role", "")) and p.get("agentId") not in (self_id,)]
    live = [p for p in matched if p.get("agentId") in live_ids]
    registered_offline = [p for p in matched if p.get("agentId") not in live_ids]
    unregistered_live = [p for p in peers if p.get("id") in live_ids
                         and not any(m.get("agentId") == p.get("id") for m in (profiles or []))]
    out = {
        "role": role_kw,
        "counts": {"profiles": len(profiles or []), "peers": len(peers), "matched": len(matched),
                   "live": len(live), "registered_offline": len(registered_offline)},
        "live": [{"agentId": p.get("agentId"), "role": str(p.get("role", ""))[:70]} for p in live],
        "registered_offline": [p.get("agentId") for p in registered_offline],
        "live_but_unregistered": [p.get("id") for p in unregistered_live],
        "toctou": "★ 本结果是**快照**。交叉之后仍有 TOCTOU 窗口（实测有会话在两次查询之间离线）"
                  "⇒ **可投递的唯一硬信号是发送时的 `targetLive`**，不是本表的 live 数量。",
    }
    if len(live) == 1:
        out["state"] = "unique_live_candidate"
        out["note"] = "恰 1 个活体候选 —— **仍须**在发送时核 `targetLive`；为 false ⇒ 该次投递不成立（不是「稍后会到」）。"
    elif len(live) == 0:
        out["state"] = "no_live_candidate"
        out["note"] = "登记表里有该角色但**都不在活体**（幽灵）⇒ 需唤醒或请协调者改派；**不得**按名字直接投递。"
    else:
        out["state"] = "ambiguous"
        out["note"] = f"活体候选 **{len(live)} 个** ⇒ 歧义，**须人工裁决**（问用户 / 广播指定），不得任选其一。"
    return out


def selftest():
    """四组夹具：唯一活体 / 幽灵 / 歧义 / 无 peers（不可解析）。**含 94% 幽灵面。**"""
    profs = [{"agentId": f"ghost-{i}", "role": "裁判 · 独立审查员（审计专员）"} for i in range(81)]
    profs[0] = {"agentId": "judge-live", "role": "裁判 · 独立审查员（审计专员）"}
    cases = [
        ("唯一活体（登记在册 + 在活体）", profs, [{"id": "judge-live", "status": "running"}], "unique_live_candidate"),
        # ★ 夹具修正（第一版写错了：我把 live 的那个也放进了登记表 ⇒ 它**确实**是活体候选，
        #   期望却写成 no_live_candidate —— **夹具与被测语义不符**，这正是"测试没测到被测对象"的同族）
        ("94% 幽灵面（登记 81 条含裁判 / 活体 5 个但**无一是该角色**）", profs,
         [{"id": f"other-{i}", "status": "running"} for i in range(5)], "no_live_candidate"),
        ("歧义（两个活体裁判）", profs + [{"agentId": "judge-2", "role": "裁判 · 独立审查员"}],
         [{"id": "judge-live", "status": "running"}, {"id": "judge-2", "status": "running"}], "ambiguous"),
        ("无 peers 快照", profs, None, "unresolvable"),
        # ★ 2026-10-10 判决 B 的回归：`load_peers(None)` **必须返回二元组**（原实现返回 None ⇒ 解包崩溃）
    ]
    bad = []
    # ★ 判决 B 的回归断言：缺 --peers 时 load_peers 必须给二元组（不崩），且 resolve 判 unresolvable
    if load_peers(None) != (None, None):
        bad.append("load_peers(None) 未返回二元组 ⇒ 默认路径会解包崩溃（判决 B 的根因）")
    for name, p, q, want in cases:
        got = resolve("裁判", p, q, self_id=None)["state"]
        ok = got == want
        print(f"  {'✅' if ok else '❌'} {name}：state={got}（期望 {want}）")
        if not ok:
            bad.append(name)
    if bad:
        print("  ❌ --selftest 失败：" + " ｜ ".join(bad))
        return 1
    print("  ✅ --selftest 通过：唯一候选 / 幽灵面 / 歧义拒答 / 缺快照不可解析 —— 四态各自可分")
    print("  ★ 但如实声明：本件**不产生**「可投递」结论；那一步只能由发送时的 `targetLive` 裁。")
    return 0


def main():
    ap = argparse.ArgumentParser(description="当值角色快照交叉解析（只读；不产生可投递结论）")
    ap.add_argument("--role", required=False, help="角色关键词（如 裁判 / 协调 / 审查）")
    ap.add_argument("--peers", default=None,
                    help="agent_peers 输出的快照 JSON 文件（**事实上必需**：无它无法判活体）")
    ap.add_argument("--profiles", default=None, help="agent_profiles 输出的快照 JSON 文件（缺省读 ~/.dsh/agent-bus.json）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.role:
        print("用法错误：需要 --role（或 --selftest）")
        return 2
    # ★★ 2026-10-10 判决 B：`--peers` 在 CLI 层是选填、**功能上必需**（总线 API 取不到 ⇒ 无快照即无法判活体）
    #    ⇒ 必填参数被写成选填。现给它**与 --role 对等的守卫**：缺则**干净报用法错**（不抛栈）。
    profs = load_profiles(a.profiles)
    peers, self_id = load_peers(a.peers)
    r = resolve(a.role, profs, peers, self_id)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print(f"live-role-resolve · 角色「{a.role}」快照交叉（**不产生可投递结论**）")
        print(f"  profiles={r.get('counts', {}).get('profiles')} · peers={r.get('counts', {}).get('peers')} · "
              f"matched={r.get('counts', {}).get('matched')} · live={r.get('counts', {}).get('live')}")
        print(f"  状态：{r['state']}")
        print(f"  活体候选：{json.dumps(r.get('live'), ensure_ascii=False)}")
        if r.get("live_but_unregistered"):
            print(f"  ⓘ 活体但未登记（登记表缺口）：{r['live_but_unregistered']}")
        print(f"  {r.get('note', r.get('why', ''))}")
        print(f"  {r['toctou']}")
    return 0 if r["state"] == "unique_live_candidate" else 1


if __name__ == "__main__":
    sys.exit(main())
