#!/usr/bin/env python3
"""
preset-fit v1 —— 角色专用模式评估器（模式评估工具化）

作用：数据驱动判断每个角色「是否需要专用 preset / 插件增强」——
  替代「凭感觉建模式」，按 4 维信号评分给出建议。

输入：总线 agent_profiles（角色/能力/资源）+ 领域关键词信号
输出：三级建议 ——
  ✅ 标准模式（工具全即可）
  🔧 专用 preset（工具面收窄 + persona 纪律注入）
  📊 插件增强（界面/数据可视化，挂在 preset 之上）

用法：
  python3 preset-fit.py                 # 评估全部档案
  python3 preset-fit.py --id=<id>       # 评估单个角色
  python3 preset-fit.py --json          # JSON 输出（供插件面板）
  python3 preset-fit.py --threshold=8   # 调整专用 preset 阈值（默认 8）

纪律：只读分析，不写文件、不广播（J34）；秒级时间观可随时跑。
"""
import json
import os
import re
import sys

BUS_FILE = os.path.expanduser("~/.dsh/agent-bus.json")

# ── 领域信号词典：角色职责中出现这些词 → 高领域化 → 需要专用 preset ──
DOMAIN_SIGNALS = {
    # 领域化角色（专用 preset 候选）
    "运营": 3, "外卖": 3, "客服": 3, "供应链": 3, "依赖": 3,
    "知识库": 2, "调研": 2, "情报": 2, "设备": 2, "算力": 2,
    "媒体": 2, "外链": 2, "通道": 2, "摄取": 2, "归档": 2,
    "资源": 2, "治理": 2, "审计": 2, "成本": 2, "健康": 2,
    "文档": 1, "文件": 1, "开发": 1, "插件": 1, "测试": 1, "验收": 1,
}

# ── 能力信号：abilities 中体现的复杂度/特殊性 ──
COMPLEX_ABILITY_KW = ["监控", "调度", "仲裁", "审批", "引擎", "管道", "SDK",
                      "API", "协议", "算法", "模型", "OCR", "爬虫", "自动化"]

# ── 现有专用 preset 对照表 ──
EXISTING_PRESETS = {
    "外卖运营管理": "waimai-ops",
    "知识馆员模式": "librarian",
    "资源管理模式": "resource-manager",
    "梁神模式": "liangshen",
}

def load_profiles():
    with open(BUS_FILE) as f:
        return json.load(f).get("profiles", [])

def score_role(p):
    """4 维信号评分：领域化 + 能力复杂度 + 资源专属 + 角色声明"""
    role = p.get("role", "") or ""
    abilities = p.get("abilities", []) or []
    resources = p.get("resources", []) or []

    s = {"domain": 0, "ability": 0, "resource": 0, "declared": 0}
    role_l = role.lower()

    # 1. 领域化信号（职责描述中的领域词）
    for kw, w in DOMAIN_SIGNALS.items():
        if kw in role:
            s["domain"] += w

    # 2. 能力复杂度信号
    for a in abilities:
        for kw in COMPLEX_ABILITY_KW:
            if kw in a:
                s["ability"] += 1
                break

    # 3. 资源专属信号（有独占资源 = 需要边界）
    if resources:
        s["resource"] = min(3, len(resources) // 2 + 1)
        # 高专属资源（file: 独占/专属维护 关键词）
        res_txt = " ".join(str(r) for r in resources)
        if "独占" in res_txt or "专属" in res_txt or "写" in res_txt:
            s["resource"] += 1

    # 4. 角色声明信号（role 字段明确说自己是"xx智能体/专员"）
    if any(k in role for k in ["智能体", "专员", "专家", "员", "管理", "协调"]):
        s["declared"] = 1

    total = sum(s.values())
    return total, s

def suggest(total, s, p):
    """三级建议：标准 / 专用 preset / 插件增强"""
    if total >= 8:
        mode = "🔧 专用 preset"
        # 领域词命中决定 preset 名
        role = p.get("role", "") or ""
        hit = [kw for kw in DOMAIN_SIGNALS if kw in role]
        preset_name = "".join(hit[:2]) + "管理" if hit else "领域专用"
        detail = f"建议创建专用 preset（{preset_name}）——工具面收窄 + persona 纪律注入"
        # 资源多/需可视化 → 插件增强
        if s["resource"] >= 3 and s["domain"] >= 3:
            mode = "🔧 专用 preset + 📊 插件增强"
            detail = "专用 preset + 侧边栏/面板视图（资源/锁/待办可视化）"
    elif total >= 5:
        mode = "📊 插件增强（可选项）"
        detail = "标准模式够用，若高频数据查看可加面板视图（非必需）"
    else:
        mode = "✅ 标准模式"
        detail = "工具面全即可，无需专用 preset"
    return mode, detail

def main():
    profiles = load_profiles()
    target = None
    as_json = "--json" in sys.argv
    threshold = 8
    for arg in sys.argv[1:]:
        if arg.startswith("--id="):
            target = arg.split("=")[1]
        if arg.startswith("--threshold="):
            threshold = int(arg.split("=")[1])

    results = []
    for p in profiles:
        aid = p.get("agentId", "")
        if target and target not in aid:
            continue
        total, s = score_role(p)
        mode, detail = suggest(total, s, p)
        results.append({
            "id": aid,
            "role": (p.get("role", "") or "")[:60],
            "score": total,
            "signals": s,
            "mode": mode,
            "detail": detail,
        })

    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    print(f"[preset-fit] 评估 {len(results)} 个角色档案（专用阈值 ≥{threshold}）")
    print("=" * 78)
    # 按分数降序
    for r in sorted(results, key=lambda x: -x["score"]):
        sid = r["id"].replace("session-", "")[:8] if "session-" in r["id"] else r["id"][:8]
        print(f"{r['score']:>3}  {r['mode']:28} {sid}  {r['role'][:40]}")
        print(f"       {r['detail']}")
    print("=" * 78)
    # 汇总
    from collections import Counter
    c = Counter(r["mode"].split()[0] for r in results)
    print(f"[preset-fit] 汇总: 标准模式 {c.get('✅',0)} / 专用preset {c.get('🔧',0)} / 插件增强 {c.get('📊',0)}")

if __name__ == "__main__":
    main()
