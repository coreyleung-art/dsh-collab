#!/usr/bin/env python3
"""rules-cli.py — 规则账本治理 CLI（跨平台）
用法:
  rules-cli.py list                     # 列出全部规则
  rules-cli.py get <id>                 # 查单条
  rules-cli.py add <id> <name> <category> <summary>   # 新增（status=pending 待审核）
  rules-cli.py approve <id>             # 总线审核通过 → enforced
  rules-cli.py reject <id> <reason>     # 总线拒绝 → rejected
  rules-cli.py update <id> <field> <value>  # 更新字段
  rules-cli.py pull                     # ★【方向反转·推荐】从 RULES.md 拉取并更新 rules.json（MD=源）
  rules-cli.py sync                     # 同步到黑板（data/rules/）+ 生成全量快照（★ 默认不再覆盖 RULES.md；旧行为加 --emit-md）
  rules-cli.py audit                    # 审计（enforced/pending/rejected 统计）
"""
import json, os, sys, time, urllib.request

RULES_FILE = os.path.expanduser("~/.dsh/rules-registry/rules.json")
# 兼容本机路径（开发期）
if not os.path.exists(RULES_FILE):
    alt = os.path.expanduser("~/dsh-collab/rules-registry/rules.json")
    if os.path.exists(alt):
        RULES_FILE = alt

BB = "http://127.0.0.1:8792"

def load():
    with open(RULES_FILE) as f:
        return json.load(f)

def save(data):
    data["lastUpdated"] = time.strftime("%Y-%m-%d")
    with open(RULES_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def find_rule(data, rid):
    for r in data["rules"]:
        if r["id"] == rid:
            return r
    return None

def cmd_list(data):
    print(f"规则账本 v{data['version']} | {data['audit']['ruleCount']} 条 | enforced {data['audit']['enforced']}")
    print("-" * 90)
    for r in data["rules"]:
        status = {"enforced": "✅", "pending": "⏳", "rejected": "❌"}.get(r["status"], r["status"])
        print(f"  {r['id']} {status} [{r['category']}] {r['name']}")
        print(f"      {r['summary'][:70]}")

def cmd_get(data, rid):
    r = find_rule(data, rid)
    if not r:
        print(f"❌ 规则 {rid} 不存在")
        return
    print(json.dumps(r, ensure_ascii=False, indent=2))

def cmd_add(data, rid, name, category, summary):
    if find_rule(data, rid):
        print(f"❌ 规则 {rid} 已存在")
        return
    rule = {
        "id": rid, "name": name, "category": category, "scope": "all-bus-devices",
        "status": "pending", "version": "1.0",
        "source": "rules-registry/rules.json",
        "summary": summary, "detail": "",
        "enforcedBy": "process", "added": time.strftime("%Y-%m-%d"), "approvedBy": None,
    }
    data["rules"].append(rule)
    data["audit"]["ruleCount"] += 1
    save(data)
    print(f"✅ 规则 {rid} 已提交（status=pending，待总线审核）")

def cmd_approve(data, rid):
    r = find_rule(data, rid)
    if not r:
        print(f"❌ 规则 {rid} 不存在"); return
    r["status"] = "enforced"
    r["approvedBy"] = "bus"
    r["approvedAt"] = time.strftime("%Y-%m-%d %H:%M")
    data["audit"]["enforced"] = sum(1 for x in data["rules"] if x["status"] == "enforced")
    save(data)
    print(f"✅ 规则 {rid} 已批准 → enforced（同步泛化所有侧后生效）")

def cmd_reject(data, rid, reason):
    r = find_rule(data, rid)
    if not r:
        print(f"❌ 规则 {rid} 不存在"); return
    r["status"] = "rejected"
    r["rejectReason"] = reason
    save(data)
    print(f"❌ 规则 {rid} 已拒绝: {reason}")

def cmd_update(data, rid, field, value):
    r = find_rule(data, rid)
    if not r:
        print(f"❌ 规则 {rid} 不存在"); return
    if field in r:
        r[field] = value
        save(data)
        print(f"✅ 规则 {rid}.{field} = {value}")
    else:
        print(f"❌ 字段 {field} 不存在")

def cmd_pull(data, dry_run=False):
    """★ 方向反转（2026-10-12 明鉴 v3 · 用户授权 · 见 R061「账本单一真相源纪律」）:
    **从 RULES.md 解析 → 更新 rules.json**。

    ★ 为什么反转：原先 `sync` 的方向是 `json → md`（从 json 生成并覆盖 md），
      但**事实上 MD 才是手工编辑且更丰富的一方**（✅ 标题 / 授权背景 / 计数口径 / 分区注）
      ⇒ **声明的源 ≠ 实际的源** ⇒ 实测漂移 12 条（R049–R060），且 `rules-cli` 读 json（旧）、
      `rules-integrity.py` 读 md（新）⇒ **两个工具两个答案而无人对账**。
    ★★ 反转后：**MD = 源，json = 派生产物** —— 方向与事实一致（R061(a)）。
    ★ 幂等：按 id 合并 —— **MD 有而 json 无 ⇒ 新增**；**两侧都有 ⇒ 保留 json 已有值，仅【补空字段】**；
      **json 独有 ⇒ 保留**（并打印提示，不静默删）。★★ **pull 是【补差】不是【覆盖】**。
    """
    import re as _re
    md_file = os.path.join(os.path.dirname(RULES_FILE), "RULES.md")
    if not os.path.exists(md_file):
        print("❌ pull 失败：RULES.md 不存在（MD 是源，源不在无从拉取）"); return
    md = open(md_file, encoding="utf-8").read()
    blocks = _re.split(r'(?m)^(?=## )', md)
    js = {str(r.get("id")): r for r in (data.get("rules") or []) if r.get("id")}
    added, updated, orphan, skipped = [], [], [], []
    for b in blocks:
        m = _re.match(r'^## +([A-Za-z0-9-]+)\b', b)
        if not m: continue
        rid = m.group(1)
        if rid.startswith('治理哲学'): continue
        # 跳过【分区标题】这类非规则小节（无 ✅/⏳/❌ 标记且无 分类 行）
        has_cat = _re.search(r'(?m)^-\s*分类\s*[:：]', b)
        if not has_cat:
            skipped.append(rid); continue
        title = b.split('\n', 1)[0]
        nm = _re.match(r'^## +%s\b\s*[✅⏳❌]?\s*(.*)$' % _re.escape(rid), title)
        name = (nm.group(1).strip() if nm else '')
        def f(field):
            mm = _re.search(r'(?m)^-\s*%s\s*[:：]\s*(.+)$' % field, b)
            return mm.group(1).strip() if mm else ''
        cl = f('分类')
        cat = _re.split(r'\|', cl)[0].strip()
        mm = _re.search(r'范围:\s*([^|]+)', cl); scope = (mm.group(1).strip() if mm else '')
        mm = _re.search(r'状态:\s*([^|]+)', cl); status = (mm.group(1).strip() if mm else '')
        status = _re.sub(r'\*\*', '', status)
        status = _re.split(r'[（(]', status)[0].strip()
        rec = {'name': name, 'category': cat, 'scope': scope, 'status': status,
               'summary': _re.sub(r'\n\s*', '', f('摘要'))}
        if rid not in js:
            newr = {'id': rid, 'name': name, 'category': cat, 'scope': scope,
                    'status': status or 'enforced', 'version': '1.0.0',
                    'source': 'rules-registry/RULES.md（pull 拉取）',
                    'summary': rec['summary'], 'detail': '',
                    'added': '2026-10-12', 'approvedBy': '见 RULES.md 各条授权背景',
                    'enforcedBy': 'process'}
            det = f('详情')
            if det: newr['details'] = _re.sub(r'\n\s*', '', det)[:1500]
            data['rules'].append(newr); added.append(rid)
        else:
            # ★★ 2026-10-12 明鉴 v3 修（dry-run 实测发现）:
            #   第一版**以 MD 为准覆盖全部字段** ⇒ 实测会改 **35 条 name**，
            #   把 MD 标题里的**日期/授权**（如「（2026-09-09 用户裁决吸收 · …）」）
            #   污染进结构化字段。★ 而「切到第一个括号前」又会**丢掉真属名称的部分**
            #   （如 R006 的「（10 项）」）—— 两侧都不对。
            # ⇒ 正解：**pull 是【补差】，不是【覆盖】** —— 已有值就保留（人工核定过），
            #   只在**字段为空**时才从 MD 补。★ 与「json 独有则保留」同一精神。
            ch = []
            for k in ('name', 'category', 'scope', 'status', 'summary'):
                if rec[k] and not str(js[rid].get(k) or '').strip():
                    ch.append(k + ':补空'); js[rid][k] = rec[k]
            if ch: updated.append((rid, ch))
    for rid in js:
        if rid not in _re.findall(r'(?m)^## +([A-Za-z0-9-]+)\b', md):
            orphan.append(rid)
    print("★ pull（MD → JSON，方向已反转）")
    print("  新增 %d 条: %s" % (len(added), ' '.join(added) if added else '（无）'))
    print("  更新 %d 条: %s" % (len(updated), ' '.join('%s(%s)' % (r, ','.join(c)) for r, c in updated[:8]) if updated else '（无）'))
    print("  ★ json 独有（保留不动，未静默删）: %s" % (' '.join(orphan) if orphan else '（无）'))
    print("  跳过非规则小节: %s" % (' '.join(skipped) if skipped else '（无）'))
    if dry_run:
        print("  ★ --dry-run：未写盘"); return
    # 计算口径三要素并入 audit（与 RULES.md 首行同口径）
    ids = [str(r.get('id')) for r in data['rules']]
    n_r = len([i for i in ids if _re.match(r'^R\d{3}$', i)])
    n_j = len([i for i in ids if _re.match(r'^J\d+$', i)])
    n_e = len([i for i in ids if i.startswith('R-ERR')])
    # ★ 2026-10-12 明鉴 v3 补：pull 亦须同步 **版本号**（从 MD 首行读）
    #   ★ 实测发现：我改 MD 版本号后未同步 ⇒ json 停在旧版 ⇒ **又制造了一次漂移**
    #     （这正是本条要治的事，故 pull 必须把 version 一并拉回）。
    _vm = _re.search(r'>\s*v([0-9.]+)\s*\|', md)
    if _vm and _vm.group(1) != data.get('version'):
        print("  ★ 版本号同步: %s → %s（源 RULES.md 首行）" % (data.get('version'), _vm.group(1)))
        data['version'] = _vm.group(1)
    _nm = _re.search(r'>\s*v[0-9.]+\s*\|\s*(\d+)\s*条', md)
    if _nm and int(_nm.group(1)) != len(ids):
        print("  ⚠️ 计数不符: MD 声明 %s 条 / json 实际 %d 条（★ 不静默改 MD，请人工查明）" % (_nm.group(1), len(ids)))
    data['audit'] = {"ruleCount": len(ids),
                     "enforced": sum(1 for r in data['rules'] if r.get('status') == 'enforced'),
                     "advisory": sum(1 for r in data['rules'] if r.get('status') == 'advisory'),
                     "breakdown": "R%d · J%d · R-ERR%d" % (n_r, n_j, n_e),
                     "updated": "2026-10-12 pull（MD → JSON）"}
    save(data)
    print("  ✅ 已写 %s（口径 R%d · J%d · R-ERR%d = %d）" % (os.path.basename(RULES_FILE), n_r, n_j, n_e, len(ids)))


def cmd_sync(data):
    """同步到黑板（data/rules/）+ 生成全量快照"""
    # 全量快照
    snap = json.dumps(data, ensure_ascii=False)
    # 黑板同步
    try:
        req = urllib.request.Request(
            f"{BB}/data/rules/registry-v{data['version'].replace('.', '-')}",
            data=snap.encode(), method="PUT",
            headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=5)
        print(f"✅ 已同步黑板: HTTP {resp.status}")
    except Exception as e:
        print(f"⚠️ 黑板同步失败: {e}")
    # 生成快照文件
    snap_file = os.path.join(os.path.dirname(RULES_FILE), f"rules-v{data['version']}.snapshot.json")
    with open(snap_file, "w") as f:
        f.write(snap)
    print(f"✅ 快照: {snap_file}")
    # 生成规则本 md（人类可读，端侧同步用）
    # ★ v2 修复（HR 2026-09-11 读码自查，守灯未提及）:
    #   原用 data['audit']['ruleCount'] 作声明 —— 该字段实测 **75**，与 len(rules) **78** 不一致
    #   ⇒ **一次 sync 会把表头写成「75 条」而正文列 78 条**，即**重新制造**今晚刚修好的「计数不可核」缺陷。
    #   故声明改为**从正文实际条数计算**，并保留 N 条 形式（门侧解析器依赖该形式）。
    _ids_all = [str(r.get('id')) for r in (data.get('rules') or [])]
    _n_r = len([i for i in _ids_all if i.startswith('R') and not i.startswith('R-ERR')])
    _n_j = len([i for i in _ids_all if i.startswith('J')])
    _n_er = len([i for i in _ids_all if i.startswith('R-ERR')])
    _decl = '分区可核: R%d . J%d . R-ERR%d = %d' % (_n_r, _n_j, _n_er, len(_ids_all))
    md = ["# 规则账本（完整规则本）", "",
          f"> v{data['version']} | {len(_ids_all)} 条 | 所有总线设备必须服从", "",
          "> ★ 计数口径（" + _decl + "）", ""]
    for r in data["rules"]:
        st = {"enforced": "✅", "pending": "⏳", "rejected": "❌"}.get(r["status"], r["status"])
        md.append(f"## {r['id']} {st} {r['name']}")
        md.append(f"- 分类: {r['category']} | 范围: {r['scope']} | 状态: {r['status']}")
        md.append(f"- 摘要: {r['summary']}")
        if r.get("detail"): md.append(f"- 详情: {r['detail']}")
        md.append("")
    md_file = os.path.join(os.path.dirname(RULES_FILE), "RULES.md")
    # ★★★ 方向反转（2026-10-12 明鉴 v3 · 用户授权 · 见 R061）：
    #   本函数原先会**从 rules.json 生成并覆盖 RULES.md** —— 但事实是 **MD 才是源**。
    #   ⇒ 自本次起：**默认【不生成/不覆盖 MD】**，仅显式 `--emit-md` 才走旧路径
    #     （保留能力，但不再是默认；★ 且旧路径的守卫一并保留）。
    #   ⇒ 正确方向：`rules-cli.py pull`（MD → JSON）。
    if "--emit-md" not in sys.argv:
        print("ℹ️ 已跳过 RULES.md 生成（方向已反转为 MD→JSON；如需旧行为请加 --emit-md，见 R061）")
        return
    # ★★ 守卫（HR 2026-09-11，星桥「两份表示漂移」触发）:
    #   本函数会**从 rules.json 生成并覆盖 RULES.md**。而实测 RULES.md 已被人**手工编辑**
    #   （R035 加入 + HR 今晚的 R033/R034 合裁 + 计数修正），**领先于源** ⇒
    #   **一次 sync 会静默销毁这些手工改动。** 故：RULES.md 若比源新/内容更全，**拒绝覆盖**。
    # ★ v2 修复（守灯 2026-09-11 读码指出两处缺口，HR 复验属实并修）:
    #   缺口①「只比条数且严格大于」⇒ 手工改动**若不改条数**（改摘要/详情文字、改状态、修计数口径）
    #         则 _md_rules == _src_rules ⇒ 守卫不触发 ⇒ **静默覆盖销毁**。故判据改为**id 集合 + 内容指纹**。
    #   缺口②「守卫异常时 fail-open」⇒ 守卫自己出错就放行覆盖，与「结构门」语义相反。故改 **fail-closed**。
    if os.path.exists(md_file):
        try:
            _md = open(md_file, encoding="utf-8").read()
            _md_ids = set()
            _md_id_list = []   # ★ v4 修复（HR 自测发现）：dup 检查必须用**列表**计数 —— 此前用 set 计数 ⇒ 计数恒为 1 ⇒ **该检查是死代码、永不触发**
            _md_sig = {}
            _cur = None
            for l in _md.split(chr(10)):
                if l.startswith("## ") and not l.startswith("## 治理哲学"):
                    _t = l[3:].strip()
                    _sp = _t.split(" ")
                    if _sp and _sp[0]:
                        _cur = _sp[0]
                        _md_ids.add(_cur)
                        _md_id_list.append(_cur)
                        _md_sig[_cur] = []
                elif _cur is not None and l.startswith("- "):
                    _md_sig[_cur].append(l[2:].strip())
            # ★ v4 修复（守灯 2026-09-11 独立复验残留观察 G5）：
            #   若 MD 中同一 id 出现两次，`_md_sig` 会以「后一次覆盖前一次」方式收集字段行 ⇒ 可能指纹混淆。
            #   修法（采纳其建议）：**结构异常优先于内容比较** —— 重复 id 直接拒绝。
            _dups = sorted([i for i, n in __import__('collections').Counter(_md_id_list).items() if n > 1])
            if _dups:
                print("❌ 拒绝对 RULES.md 执行覆盖生成：**MD 中存在重复 id**（结构异常）: " + ", ".join(_dups[:12]))
                if "--force" not in sys.argv:
                    print("   （快照与黑板同步已完成；仅跳过 RULES.md 覆盖）")
                    return
            _src_ids = set(str(r.get("id")) for r in (data.get("rules") or []))
            _only_md = sorted(_md_ids - _src_ids)
            _only_src = sorted(_src_ids - _md_ids)
            _core = False
            if _only_md or _only_src:
                _core = True
                print("❌ 拒绝对 RULES.md 执行覆盖生成：**产物与源存在 id 集合差**。")
                if _only_md: print("   产物独有（覆盖会销毁）: " + ", ".join(_only_md[:12]))
                if _only_src: print("   源独有（产物落后）: " + ", ".join(_only_src[:12]))
            else:
                _diff = []
                for _r in (data.get("rules") or []):
                    _rid = str(_r.get("id"))
                    _exp = ["分类: %s | 范围: %s | 状态: %s" % (_r.get("category"), _r.get("scope"), _r.get("status")),
                            "摘要: %s" % _r.get("summary")]
                    if _r.get("detail"): _exp.append("详情: %s" % _r.get("detail"))
                    # ★ v3 修复（守灯 2026-09-11 独立复验用例 G 发现残余假阳性，方向为安全侧）:
                    #   仅调换字段顺序（分类/摘要/详情 逆序）会被判「内容不一致」⇒ 正当编辑被误拒。
                    #   修法：比较前对行**排序**再做指纹比对 ⇒ 判据对字段顺序不敏感，**不降低检出力**
                    #   （该判据关心行内容，不关心行序；且行按 id 分组比较，跨条移动仍会被抓到）。
                    if sorted(_md_sig.get(_rid, [])) != sorted(_exp): _diff.append(_rid)
                if _diff:
                    _core = True
                    print("❌ 拒绝对 RULES.md 执行覆盖生成：**同 id 内容不一致**（源与产物对该条文字不同）。")
                    print("   不一致条目: " + ", ".join(sorted(_diff)[:12]))
                    print("   说明：这类差异**不改变条数** —— 旧判据（只比条数）不会触发，即守灯指出的缺口①。")
            if _core:
                print("   判据已由「条数」升为「id 集合 + 内容指纹」（守灯 2026-09-11 读码指出）。")
                print("   处置：先把产物内容**回填源 JSON**，再 sync；或加 --force 自行承担。")
                if "--force" not in sys.argv:
                    print("   （快照与黑板同步已完成；仅跳过 RULES.md 覆盖）")
                    return
        except Exception as _e:
            print("❌ 守卫检查失败（**fail-closed**，拒绝覆盖）: " + str(_e)[:100])
            print("   原因：守卫自身异常时若放行，等于「门坏了就开门」——与结构门语义相反（守灯 2026-09-11 读码指出）。")
            if "--force" not in sys.argv:
                print("   （快照与黑板同步已完成；仅跳过 RULES.md 覆盖）")
                return
    with open(md_file, "w") as f:
        f.write("\n".join(md))
    print(f"✅ 规则本: {md_file}")

def cmd_audit(data):
    from collections import Counter
    c = Counter(r["status"] for r in data["rules"])
    print(f"规则总数: {len(data['rules'])}")
    for k, v in c.items():
        print(f"  {k}: {v}")

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__); return
    data = load()
    cmd = args[0]
    if cmd == "list": cmd_list(data)
    elif cmd == "get" and len(args) > 1: cmd_get(data, args[1])
    elif cmd == "add" and len(args) > 4: cmd_add(data, args[1], args[2], args[3], args[4])
    elif cmd == "approve" and len(args) > 1: cmd_approve(data, args[1])
    elif cmd == "reject" and len(args) > 2: cmd_reject(data, args[1], args[2])
    elif cmd == "update" and len(args) > 3: cmd_update(data, args[1], args[2], args[3])
    elif cmd == "pull": cmd_pull(data, dry_run=("--dry-run" in sys.argv))
    elif cmd == "sync": cmd_sync(data)
    elif cmd == "audit": cmd_audit(data)
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
