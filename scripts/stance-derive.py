#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
立场派生器 · Stance Deriver v1
================================
按「章节选取」而非「逐词替换」生成受众版本。

为什么不能用逐词替换：
    对一份 2000 行的技术型文档做正则替换，会产生「产业合作方产业合作方在产业合作方内部」
    这类嵌套错误，并破坏表格结构（实测：公开版产生 57 处结构损坏）。正确做法是
    按受众「该看什么」选取章节。

用法：
    python3 stance-derive.py <in.md> <out.md> --audience partner|public

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import sys, os, re

# 各受众的「保留章节」匹配规则（按 ## 章节标题文字匹配）

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/stance-derive.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

KEEP = {
    "partner": [   # 合作方：业务/能力/交付/增长，去掉股权·对赌·预算明细·估值
        "公司是什么", "机会在哪", "我们走到哪了", "四步走",
        "价值主张", "痛点", "解决方案与护城河", "市场",
        "商业模式与单位经济", "增长", "竞争", "团队", "亮点",
        "组织架构", "技术架构",
    ],
    "public": [    # 公开版：只留业务是什么 / 市场 / 模式 / 愿景
        "公司是什么", "机会在哪", "四步走",
        "价值主张", "痛点", "解决方案与护城河", "市场", "增长", "亮点",
    ],
}

# 无条件移除（即使标题命中保留规则）
DROP_ALWAYS = [
    "股权结构", "对赌", "预算", "启动资金", "各轮", "估值",
    "九要素", "推理依据", "个人层面", "结构速览", "风险事实",
]


def derive(text, aud):
    lines = text.split("\n")
    keep_pats = KEEP[aud]

    # 1) 切块：以 ## 为最小单位，记录所属 # 部分
    blocks = []
    part = None
    i = 0
    head = []
    while i < len(lines) and not re.match(r"^# ", lines[i]):
        head.append(lines[i]); i += 1
    while i < len(lines):
        m = re.match(r"^#\s+(.*)$", lines[i])
        if m:
            part = m.group(1); i += 1; continue
        m2 = re.match(r"^##\s+(.*)$", lines[i])
        if m2:
            sec = m2.group(1)
            j = i + 1
            while j < len(lines) and not re.match(r"^#{1,2}\s+", lines[j]):
                j += 1
            blocks.append((part, sec, lines[i:j])); i = j; continue
        i += 1

    # 2) 判定保留
    keep_blocks, dropped = [], 0
    for part, sec, body in blocks:
        hit = any(p in (sec or "") for p in keep_pats)
        drop = any(p in (sec or "") for p in DROP_ALWAYS) or any(p in (part or "") for p in DROP_ALWAYS)
        if hit and not drop:
            keep_blocks.append((part, sec, body))
        else:
            dropped += 1

    # 2.5) ★ 行级过滤：在已选章节上清残留（比全文档替换安全）
    SENSITIVE = {
      "partner": [r"对赌", r"回购", r"优先清算", r"反稀释", r"领售", r"拖售",
                  r"出资额", r"估值", r"持股", r"股比", r"清算优先", r"期权池"],
      "public":  [r"对赌", r"回购", r"优先清算", r"反稀释", r"领售", r"拖售",
                  r"出资额", r"估值", r"持股", r"股比", r"清算优先", r"期权池",
                  r"橙果", r"声通", r"授权链", r"牌照", r"确权", r"\d{1,3}%",
                  r"\d[\d,.]*\s*(万元|亿元|万|亿)"],
    }
    reps = {"partner": [("橙果", "合作方"), ("声通", "资源方"), ("梁振宇及其实控主体公司", "本公司方")],
            "public":  [("橙果", "产业合作方"), ("声通", "资源方"),
                        ("梁振宇及其实控主体公司", "创始团队主体"), ("梁振宇", "创始团队负责人")]}
    sens = [re.compile(x) for x in SENSITIVE[aud]]
    filtered = []
    for part, sec, body in keep_blocks:
        nb, dropped_line = [], 0
        for ln in body:
            for a, b in reps[aud]:
                ln = ln.replace(a, b)
            # 命中敏感 → 整行丢弃（保留标题行）
            if any(rx.search(ln) for rx in sens) and not ln.strip().startswith("#"):
                dropped_line += 1
                continue
            nb.append(ln)
        keep_blocks_out = (part, sec, nb)
        filtered.append(keep_blocks_out)
    keep_blocks = filtered

    # 3) 重组（按部分分组，插入部分标题）
    out, seen = [], None
    for part, sec, body in keep_blocks:
        if part != seen:
            out.append("# " + str(part))
            out.append("")
            seen = part
        out += body
        out.append("")

    name = "合作方版" if aud == "partner" else "公开版"
    # ★ 声明不得枚举"已移除什么"（那等于告诉读者这些内容存在）
    if aud == "partner":
        scope = "面向合作方，聚焦业务定位、能力与护城河、市场、增长与交付边界。"
    else:
        scope = "业务介绍版，聚焦业务定位、市场机会、模式与愿景。"

    banner = ("> **" + name + "** · 编制日期 2026-09-10 · 密级：可对外<br>\n"
              "> " + scope + "<br>\n"
              "> 如需更详细资料，请联系我们。\n\n")
    return banner + "# 花联网 · " + name + "\n\n" + "\n".join(out), len(keep_blocks), dropped


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: stance-derive.py <in.md> <out.md> --audience partner|public"); sys.exit(1)
    src, dst = sys.argv[1], sys.argv[2]
    aud = sys.argv[sys.argv.index("--audience") + 1] if "--audience" in sys.argv else "partner"
    text = open(src, encoding="utf-8").read()
    out, k, d = derive(text, aud)
    open(dst, "w", encoding="utf-8").write(out)
    print("  ✅ %s —— 保留 %d 节 / 移除 %d 节（%s）" % (os.path.basename(dst), k, d, aud))
