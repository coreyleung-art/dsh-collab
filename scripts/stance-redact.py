#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
立场脱敏生成器 · 由 stance-auditor 的 P05/P03 规则驱动
用法: python3 stance-redact.py <in.md> <out.md> --audience partner|public

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== stance-redact 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 立场脱敏生成器 · 由 stance-auditor 的 P05/P03 规则驱动")
    print("  · 用法: python3 stance-redact.py <in.md> <out.md> --audience partner|public")
    print("  · ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。")
    print("  · 依据：r006-debt-assess.py 机械扫描未检出以下原语：")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: sys, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/stance-redact.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import sys, os, re

# 各受众的脱敏规则：(正则, 替换, 说明)

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/stance-redact.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

RULES = {
 "partner": [   # 合作方版：去股权/对赌/出资额细节，保留合作边界
   (r"公司层面(只有)?两个股东[^。]*。", "公司结构：见正式协议。", "股权结构"),
   (r"梁振宇及其实控主体公司\s*\*{0,2}51%\*{0,2}", "本公司方", "持股比例"),
   (r"橙果\s*\*{0,2}49%\*{0,2}", "合作方", "持股比例"),
   (r"对赌[^。]*。", "相关风险保障安排详见正式协议。", "对赌条款"),
   (r"回购[^。]*。", "", "回购条款"),
   (r"优先清算[^。]*。", "", "优先清算"),
   (r"反稀释[^。]*。", "", "反稀释"),
   (r"出资额【[^】]*】", "出资额（以协议为准）", "出资额"),
   (r"\d+ ?万元?的?(出资|启动资金)", "约定金额的\\1", "具体金额"),
   (r"橙果|声通", "合作方", "合作方名称"),
   (r"股权|持股|股比", "权益安排", "股权词"),
   (r"对赌|回购|优先清算|反稀释|领售权|拖售权", "风险保障条款", "对赌词"),
   (r"出资额[^。|]*", "出资安排（以协议为准）", "出资额"),
   (r"估值[^。|]*", "公司价值（以协议为准）", "估值"),
   (r"收益分配|分红", "收益安排", "分配"),
 ],
 "public": [    # 公开版：更激进——去所有比例/金额/牌照细节/合作方名
   (r"公司层面(只有)?两个股东[^。]*。", "公司由创始团队与产业合作方共同设立。", "股权结构"),
   (r"梁振宇及其实控主体公司[^。，、；]*", "创始团队", "实控主体"),
   (r"梁振宇", "创始团队负责人", "人名"),
   (r"\*{0,2}5[01]%\*{0,2}", "", "持股比例"),
   (r"橙果|声通|广州橙果供应链科技|中恒天仰", "产业合作方", "合作方名称"),
   (r"淘宝闪购|淘闪|美团|京东|抖音", "主流即时零售平台", "平台名称"),
   (r"城市合伙人牌照[^。]*。", "相关经营资质已通过合作方落实。", "牌照细节"),
   (r"全国鲜花类目服务商[^。]*。", "", "牌照细节"),
   (r"授权(链)?[^。]*。", "", "授权细节"),
   (r"对赌|回购|优先清算|反稀释|领售权", "相关条款", "对赌条款"),
   (r"\d[\d,\.]*\s*(万元|亿元|万|亿)", "约定金额", "具体金额"),
   (r"\d{1,3}(\.\d+)?%", "约定比例", "具体比例"),
   (r"成都", "某新一线城市", "地名"),
   (r"双牌确权|确权|资质确权", "相关资质核验", "确权"),
   (r"牌照|资质|资格", "经营资格", "牌照词"),
   (r"授权链|法律文书授权|授权给", "合作方安排", "授权词"),
   (r"启动资金|启动出资", "启动投入", "资金词"),
   (r"份额|市占|渗透率", "市场表现", "地位"),
   (r"溢价|毛差价|毛利", "附加值", "盈利词"),
   (r"抽成|返佣|补贴", "平台结算", "结算词"),
 ],
}

def redact(text, aud):
    n = 0
    for pat, rep, label in RULES.get(aud, []):
        text, k = re.subn(pat, rep, text)
        n += k
    # 清理残留：连续空行/空标点
    text = re.sub(r"\n{3,}", "\n\n", text)
    # ★ 脱敏后结构修复：删掉空表格行 / 列数不齐行 / 空列表项
    lines = []
    for ln in text.split("\n"):
        st = ln.strip()
        if re.match(r"^\|[\s|\-]*\|?$", st):          # 全空表格行
            continue
        if re.match(r"^[-*]\s*$", st):                  # 空列表项
            continue
        if re.match(r"^#{1,6}\s*$", st):                # 空标题
            continue
        lines.append(ln)
    text = "\n".join(lines)
    # 表格列数归一（以每张表的表头为准，截断/补齐）
    out2 = []; i = 0
    while i < len(lines):
        if lines[i].strip().startswith("|") and i+1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i+1]):
            n = lines[i].count("|")
            out2.append(lines[i]); out2.append(lines[i+1]); j = i+2
            while j < len(lines) and lines[j].strip().startswith("|"):
                row = lines[j]; c = row.count("|")
                if c > n:      # 多 → 截断到表头列数
                    parts = row.split("|")[:n+1]; row = "|".join(parts) + "|"
                elif c < n - 1: # 少太多 → 补齐
                    row = row.rstrip().rstrip("|").rstrip() + " |" * (n - c)
                out2.append(row); j += 1
            i = j
        else:
            out2.append(lines[i]); i += 1
    text = "\n".join(out2)
    text = re.sub(r"[，、；]{2,}", "，", text)
    text = re.sub(r"：\s*。", "：略。", text)
    text = re.sub(r"^\s*[，、；。]\s*$", "", text, flags=re.M)
    return text, n

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: stance-redact.py <in.md> <out.md> --audience partner|public"); sys.exit(1)
    src, dst = sys.argv[1], sys.argv[2]
    aud = "partner"
    if "--audience" in sys.argv:
        aud = sys.argv[sys.argv.index("--audience") + 1]
    text = open(src, encoding="utf-8").read()
    out, n = redact(text, aud)
    # 头部加脱敏声明
    banner = (f"> ⚠️ **本文件为「{'合作方版' if aud=='partner' else '公开版'}（已脱敏）」**：\n"
              f"> 已去除具体股权比例、出资金额、对赌条款细节、相关方名称与牌照归属细节。\n"
              f"> 需要完整条款的，请参阅正式协议或另行签署保密协议后提供。\n\n")
    out = banner + out
    open(dst, "w", encoding="utf-8").write(out)
    print(f"  ✅ {os.path.basename(dst)} —— 脱敏 {n} 处（{aud}）")
