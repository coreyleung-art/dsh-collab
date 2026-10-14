# 发布门禁报告 · SystemGraph v1.5.0

> 时间: 2026-10-13 02:37:47 · 工具: 三闸

| 闸 | 工具 | 结果 | 明细 |
|----|------|------|------|
| G1 | bb-gallery-gate | ✅ | 8过/0败 |
| G2 | bb-blueprint-content-check | ❌ | 空呈现 2 |

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
❌ 空 merchant-ops-ai            mainlines=3 stages=0 works=0 svg文本10/0子 空因:no-stages-works
✅ flowernet-ops              mainlines=4 stages=3 works=0 svg文本15/0子 
✅ flowernet-supply           mainlines=6 stages=3 works=0 svg文本27/10子 
✅ flowernet-citywar          mainlines=4 stages=3 works=0 svg文本24/9子 
✅ mingjian-toolchain         mainlines=6 stages=4 works=7 svg文本24/0子 
❌ 空 flowernet-jv               mainlines=8 stages=0 works=0 svg文本24/0子 空因:no-stages-works
→ 21 蓝图, 2 个空/退化
```
| G3 | bb-blueprint-integrity | ❌ | 🔴 2 |

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
🟢  84 distributed-network        缺:works ts
🟢  80 mtm                        缺:stages
🟢  80 laodeng-app                缺:stages
🟢  80 mingjian-toolchain         缺:stages
🟡  78 flowernet-supply           缺:works status ts
🟡  78 flowernet-citywar          缺:works status ts
🟡  72 flowernet                  缺:identity works status
🟡  64 flowernet-website          缺:stages works ts
🟡  60 flowernet-jv               缺:stages works render
🔴  58 flowernet-ops              缺:stages works status ts
🔴  44 merchant-ops-ai            缺:stages works gate render ts

→ 21 蓝图 · 低于60分 2 个: ['flowernet-ops', 'merchant-ops-ai']
```

## 结论
**❌ 未通过 — 发布中止**
