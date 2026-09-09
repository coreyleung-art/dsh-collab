# labforge 考古快照（自动沉淀）

> 方法论: cld-dsh-dev-system/rules/考古治理闭环-方法论-v1.md (Arch-Act-Loop)
> 6 大根因模式: M1遮蔽/M2物化OOM/M3重启竞态/M4插件协议/M5凭旧认知/M6不留痕
> 每 6h 主动考古追加快照
---


## 考古快照 2026-09-05T14:51:44
```

═══ 故障根因考古 ═══
报告源: /Users/coreyleung/dsh-collab/repair-reports + /Users/coreyleung/dsh-collab/archaeology-mbp/mini-reports | 条目: 44 | 时间 2026-09-05T06:51:44.622Z

根因模式分布:
 🛡 M1 版本遮蔽/漂移: 8 条 (例: 20260904-202817 S5-sampling-P58-tools-session-rootcause)
 🛡 M2 全量物化内存失控: 8 条 (例: 20260904-202817 S5-sampling-P58-tools-session-rootcause)
 🛡 M3 重启竞态/启动器冲突: 8 条 (例: 20260904-202817 S5-sampling-P58-tools-session-rootcause)
 ⚠️ M4 插件加载协议不符: 4 条 (例: 20260905-015515 dsh-replaceable-elements-map-standard)
 ⚠️ M5 凭旧认知修: 2 条 (例: 20260904-134929 修复评估: CLD 反复 OOM 崩溃 - 堆上限扩容+auto-index 治理)
 ⚠️ M6 改完不验证/不留痕: 0 条
 ? 未归类: 28 条

守护面: 已守护 [M1, M2, M3] | 缺口 M4(插件加载协议不符), M5(凭旧认知修), M6(改完不验证/不留痕)

⚠️ 建议补卡:
   labforge new m4-regression  # 守护 M4 插件加载协议不符 (防御: OP-add-plugin 路由 + T4 + 冒烟)
   labforge new m5-regression  # 守护 M5 凭旧认知修 (防御: P0 doc-check 门)
   labforge new m6-regression  # 守护 M6 改完不验证/不留痕 (防御: C1-C7 + repair-report + P1 备份)
```

## 考古快照 2026-09-05T14:52:03
```

═══ 故障根因考古 ═══
报告源: /Users/coreyleung/dsh-collab/repair-reports + /Users/coreyleung/dsh-collab/archaeology-mbp/mini-reports | 条目: 44 | 时间 2026-09-05T06:52:03.666Z

根因模式分布:
 🛡 M1 版本遮蔽/漂移: 8 条 (例: 20260904-202817 S5-sampling-P58-tools-session-rootcause)
 🛡 M2 全量物化内存失控: 8 条 (例: 20260904-202817 S5-sampling-P58-tools-session-rootcause)
 🛡 M3 重启竞态/启动器冲突: 8 条 (例: 20260904-202817 S5-sampling-P58-tools-session-rootcause)
 ⚠️ M4 插件加载协议不符: 4 条 (例: 20260905-015515 dsh-replaceable-elements-map-standard)
 ⚠️ M5 凭旧认知修: 2 条 (例: 20260904-134929 修复评估: CLD 反复 OOM 崩溃 - 堆上限扩容+auto-index 治理)
 ⚠️ M6 改完不验证/不留痕: 0 条
 ? 未归类: 28 条

守护面: 已守护 [M1, M2, M3] | 缺口 M4(插件加载协议不符), M5(凭旧认知修), M6(改完不验证/不留痕)

⚠️ 建议补卡:
   labforge new m4-regression  # 守护 M4 插件加载协议不符 (防御: OP-add-plugin 路由 + T4 + 冒烟)
   labforge new m5-regression  # 守护 M5 凭旧认知修 (防御: P0 doc-check 门)
   labforge new m6-regression  # 守护 M6 改完不验证/不留痕 (防御: C1-C7 + repair-report + P1 备份)
```
