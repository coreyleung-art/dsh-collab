# 迭代需求 · 资产关系建模持久内置(工具化) v1

> 作者: 明鉴 v2 · 2026-09-05 · 状态: 规划(用户拍板推进)
> 背景: 跨节点资产 Tab 原为"孤立星群"(资产互不连); 已加关系层 v2(设备通道+蓝图归属)让网络呈现。用户要求: 关系梳理工具化/持久内置到系统架构管理器, 表达数据模型关系层的真实状态。

## 一、目标
让资产间的**真实关系**(依赖/协作/共享)可建模、可维护、可校验、可呈现——不靠人工臆造, 靠工具 + 数据。

## 二、数据模型(schema v2)
扩展 `data/blueprint/gallery/business-asset-map.json`:
```json
{
  "version": "1.5",
  "relations": [              // 新增: 资产间/资产↔设备 显式关系
    {"from": "flower-l2 权重", "to": "flower-yolo 训练集", "type": "depends_on",
     "desc": "模型权重依赖训练集", "since": "2026-09-05", "verified": true},
    {"from": "DSH 运行资产(i9)", "to": "设备资产表", "type": "collaborates",
     "desc": "i9 节点资产登记", "verified": true}
  ],
  "relationTypes": {          // 类型枚举(防乱标)
    "depends_on": "依赖(被依赖方先行)",
    "collaborates": "协作(共同完成)",
    "uses": "使用(消费方引用)",
    "duplicates": "冗余/副本(需注意)",
    "part_of": "隶属(子资产)"
  }
}
```

## 三、工具 scripts/bb-asset-relations.py(幂等可复跑)
| 命令 | 功能 |
|------|------|
| `--add "from" "to" depends_on "desc"` | 加关系(自动查重/校验两端存在) |
| `--del from to` | 删关系 |
| `--list [type]` | 列关系 |
| `--selfcheck` | 校验: 端点存在/类型合法/重复/孤儿资产 |
| `--suggest` | 扫描潜在关系建议(同蓝图同设备/responder 同人/命名相似) — 供人工确认后 --add |
| `--export-graph` | 与 gallery 对齐(关系 → 图数据) |

## 四、管理器呈现(gallery 已支持 v2 基础)
- 设备通道边(device-links.json 真实)✅ 已有
- 蓝图归属边(资产 blueprint)✅ 已有
- **资产间 relations 边**(新): 从 relations 数组画 depends_on/collaborates 等 — 真实依赖呈现
- 点击资产卡显示: 它依赖谁 / 谁依赖它(关系反查)
- hover 关系边 → desc

## 五、真实世界原则(用户强调)
- ⚠️ 只画**数据里有据**的关系: 通道来自 device-links(实测) / 归属来自 blueprint 字段 / 资产间 relations 必须 verified=true 才上边
- --suggest 只给**建议**, 人工确认后 --add 并 verified=true
- 不臆造: 无据连接不画(如实反映"无直连"如 i9↔MBP)

## 六、验收
| # | 标准 |
|---|------|
| A1 | relations schema v1.5 落盘, 工具可增删改查 |
| A2 | --selfcheck 通过(端点/类型/重复校验) |
| A3 | 资产间 relations 在图谱呈现(第三层边) |
| A4 | 资产卡反查关系(依赖谁/谁依赖) |
| A5 | --suggest 建议准确(不误报), 确认后入 verified |
| A6 | 工具纳入 sysgraph-version release 流程(变更驱动) |

## 七、里程碑
- M1 schema v1.5 + 工具骨架(add/del/list/selfcheck)
- M2 --suggest 扫描建议 + 首批人工确认关系入档
- M3 gallery 渲染 relations 第三层边 + 资产卡反查
- M4 文档 + release 流程接入

## 八、三件套
- 文档: 本文档 + docs/asset-relations-guide.md(关系建模规范)
- 代码: scripts/bb-asset-relations.py + gallery 渲染扩展
- 数据: business-asset-map.json v1.5(relations 层)
