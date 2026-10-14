# 发布门禁报告 · SystemGraph v9.9.9

> 时间: 2026-10-13 05:12:38 · 工具: 三闸

| 闸 | 工具 | 结果 | 明细 |
|----|------|------|------|
| G1 | bb-gallery-gate | ✅ | 8过/0败 |
| G2 | bb-blueprint-content-check | ✅ | 空呈现 0 |

## G2 蓝图空呈现扫描明细
```
══ 蓝图内容健康度 ══
✅ flowernet                  mainlines=3 stages=7 works=0 svg文本43/22子 
✅ flowernet-platform         mainlines=6 stages=6 works=8 svg文本47/20子 
✅ agent-network              mainlines=6 stages=13 works=13 svg文本61/34子 
✅ blueprint-platform         mainlines=3 stages=3 works=2 svg文本25/8子 
✅ aistartup                  mainlines=3 stages=3 works=5 svg文本26/9子 
✅ banking                    mainlines=3 stages=3 works=6 svg文本27/10子 
✅ rule-judge                 mainlines=3 stages=4 works=5 svg文本30/12子 
✅ flowernet-erp              mainlines=3 stages=3 works=4 svg文本22/8子 
✅ flowernet-miniapp          mainlines=3 stages=3 works=3 svg文本21/7子 
✅ flowernet-website          mainlines=4 stages=2 works=0 svg文本14/0子 
✅ memory-governance          mainlines=3 stages=11 works=12 svg文本50/25子 
✅ gene-bank                  mainlines=4 stages=4 works=4 svg文本29/9子 
✅ distributed-network        mainlines=6 stages=6 works=0 svg文本37/17子 
✅ mtm                        mainlines=3 stages=3 works=3 svg文本17/0子 
✅ laodeng-app                mainlines=3 stages=5 works=5 svg文本19/0子 
✅ merchant-ops-ai            mainlines=3 stages=3 works=6 svg文本20/6子 
✅ flowernet-ops              mainlines=4 stages=3 works=8 svg文本23/8子 
✅ flowernet-supply           mainlines=6 stages=3 works=0 svg文本27/10子 
✅ flowernet-citywar          mainlines=4 stages=3 works=0 svg文本24/9子 
✅ mingjian-toolchain         mainlines=6 stages=4 works=7 svg文本24/0子 
✅ flowernet-jv               mainlines=8 stages=5 works=9 svg文本29/0子 
→ 21 蓝图, 0 个空/退化
```
| G3 | bb-blueprint-integrity | ✅ | 🔴 0 |

## G3 蓝图完整度扫描明细
```
══ 蓝图完整度(0-100) ══
🟢 100 flowernet-platform         缺:—
🟢 100 agent-network              缺:—
🟢 100 blueprint-platform         缺:—
🟢 100 aistartup                  缺:—
🟢 100 banking                    缺:—
🟢 100 rule-judge                 缺:—
🟢 100 flowernet-erp              缺:—
🟢 100 flowernet-miniapp          缺:—
🟢 100 memory-governance          缺:—
🟢 100 gene-bank                  缺:—
🟢 100 merchant-ops-ai            缺:—
🟢  94 flowernet-ops              缺:status
🟢  84 distributed-network        缺:works ts
🟢  80 mtm                        缺:stages
🟢  80 laodeng-app                缺:stages
🟢  80 mingjian-toolchain         缺:stages
🟢  80 flowernet-jv               缺:stages
🟡  78 flowernet-supply           缺:works status ts
🟡  78 flowernet-citywar          缺:works status ts
🟡  72 flowernet                  缺:identity works status
🟡  64 flowernet-website          缺:stages works ts

→ 21 蓝图 · 低于60分 0 个: []
```
| G4 | r062-archive-discipline-check | ❌ | 告警 2 · 不可判 0 |

## G4 归档三纪律明细（R062）
```
{
 "tool": "r062-archive-discipline-check",
 "version": "1.0.0",
 "checkedAt": "2026-10-13T05:12:42.424135",
 "rule": "R062",
 "results": [
  {
   "id": "③",
   "name": "段存在性原语",
   "verdict": "WARN",
   "realSeg": {
    "ok": true,
    "count": 2695
   },
   "fakeSeg": {
    "ok": true,
    "count": 0,
    "hasListKey": true
   },
   "sameShape": true,
   "registryExists": true,
   "detail": "★ **本板无「段存在」原语**：假段 `zzz-r062-no-such-segment` 与真段**同形**（都返 200 + list）⇒ **「段名打错」与「真无告警」在返回层面不可区分**⇒ 凡「读不到 ⇒ 判无」的判据，其**不可判分支在本板上结构上不可达**。★ 处置：**必须查【板外段登记表】** `/Users/coreyleung/dsh-collab/data/registry/board-segments.json`（现存在）。"
  },
  {
   "id": "②",
   "name": "板级 ts 覆盖",
   "verdict": "WARN",
   "checked": 2,
   "shadowed": [
    {
     "key": "data/blueprint/relations",
     "boardTs": "2026-09-10T23:05:15",
     "innerTs": "2026-09-10",
     "shadowed": true
    }
   ],
   "undecided": [
    {
     "key": "data/registry/sg-acl",
     "err": "HTTP 404"
    }
   ],
   "detail": "★ 1/2 个键的板级 ts 与内层 value.ts **不一致** ⇒ 凡按板级 ts 计龄/排序的读者会读到一个【被覆盖过的时间】⇒ **必须同时读内层 value.ts 并报两者之差**（差本身就是信号）"
  },
  {
   "id": "①",
   "name": "归档≠已处理",
   "verdict": "PASS",
   "archivedCount": 0,
   "disposalCount": 0,
   "gap": 0,
   "seg": "notes/mac-mini/",
   "total": 2695,
   "detail": "已查 2695 条；归档 0 · 处置证据 0 ⇒ 未发现「归档多于处置」"
  }
 ],
 "failCount": 2,
 "undecidableCount": 0,
 "ok": false
}
```

## 结论
**❌ 未通过 — 发布中止**
