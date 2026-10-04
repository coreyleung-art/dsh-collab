#!/usr/bin/env python3
"""rules-cli.py — 规则账本治理 CLI（跨平台）
用法:
  rules-cli.py list                     # 列出全部规则
  rules-cli.py get <id>                 # 查单条
  rules-cli.py add <id> <name> <category> <summary>   # 新增（status=pending 待审核）
  rules-cli.py approve <id>             # 总线审核通过 → enforced
  rules-cli.py reject <id> <reason>     # 总线拒绝 → rejected
  rules-cli.py update <id> <field> <value>  # 更新字段
  rules-cli.py sync                     # 同步到黑板（data/rules/）+ 生成全量快照
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
    elif cmd == "sync": cmd_sync(data)
    elif cmd == "audit": cmd_audit(data)
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
