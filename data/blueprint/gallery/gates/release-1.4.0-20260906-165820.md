# 发布门禁报告 · SystemGraph v1.4.0

> 时间: 2026-09-06 16:58:20 · 工具: 三闸

| 闸 | 工具 | 结果 | 明细 |
|----|------|------|------|
| G1 | bb-gallery-gate | ✅ | 7过/0败 |
| G2 | bb-blueprint-content-check | ✅ | 空呈现 0 |

## G2 蓝图空呈现扫描明细
```
══ 蓝图内容健康度 ══
✅ flowernet                  mainlines=3 stages=7 works=0 svg文本43/22子 
✅ flowernet-platform         mainlines=6 stages=6 works=8 svg文本47/20子 
✅ agent-network              mainlines=6 stages=13 works=13 svg文本61/34子 
✅ blueprint-platform         mainlines=3 stages=3 works=5 svg文本25/8子 
✅ aistartup                  mainlines=3 stages=3 works=5 svg文本26/9子 
✅ banking                    mainlines=3 stages=3 works=6 svg文本27/10子 
✅ rule-judge                 mainlines=3 stages=4 works=5 svg文本30/12子 
✅ flowernet-erp              mainlines=3 stages=3 works=4 svg文本22/8子 
✅ flowernet-miniapp          mainlines=3 stages=3 works=3 svg文本21/7子 
✅ flowernet-website          mainlines=3 stages=2 works=2 svg文本17/4子 
✅ memory-governance          mainlines=3 stages=11 works=12 svg文本50/25子 
✅ gene-bank                  mainlines=4 stages=4 works=4 svg文本29/9子 
✅ distributed-network        mainlines=5 stages=5 works=5 svg文本35/12子 
✅ mtm                        mainlines=3 stages=3 works=3 svg文本17/0子 
✅ laodeng-app                mainlines=3 stages=5 works=5 svg文本19/0子 
→ 15 蓝图, 0 个空/退化
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
🟢 100 flowernet-website          缺:—
🟢 100 memory-governance          缺:—
🟢 100 gene-bank                  缺:—
🟢 100 distributed-network        缺:—
🟢  80 mtm                        缺:stages
🟢  80 laodeng-app                缺:stages
🟡  72 flowernet                  缺:identity works status

→ 15 蓝图 · 低于60分 0 个: []
```

## 结论
**✅ 通过 — 可发布**
