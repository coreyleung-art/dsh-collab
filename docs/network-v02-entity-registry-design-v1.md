# Network v0.2 · 统一实体主源设计文档 v1

> 明鉴 · 2026-09-09 · 用户拍板: 打通模式 B(统一实体主源) + 混合写过渡
> 前置: Network(独立 app,8812) + SystemGraph gallery(8798) + identity-graph CLI
> 三答已齐: ①模式B ②events=妙记自动提取+用户补充 ③人类范围=全部生意(银行/活动/供应链/花店)

## 一、目标与决策记录

| 决策项 | 结论 | 依据 |
|---|---|---|
| 打通深度 | **模式 B：统一实体主源** | 跨域规模下一致性是主矛盾; 基建已倾斜(identity-graph 已是事实主源) |
| 主源文件形态 | **新建 `business-entity-registry.json`**（干净分层） | 原 identity-graph.json 保留作"会议人物派生视图"，不混业务上下文 |
| 写入模式 | **混合写过渡**：注册表为主(people/orgs/aliases)，Network 本地增强(events/relations 自定义字段) | 迁移期双写风险降到最低 |
| events 数据源 | 妙记自动提取 L1(在场 speakers) + L2(时间线落库) + L3(用户补充) | speakers 字段跨场稳定映射已验证 |
| 人类范围 | 全部生意域: banking / flowernet / supply / event / cross | entity-alias-map 已有 domain 模式雏形 |

## 二、架构图

```mermaid
graph LR
    subgraph 主源层
        REG[business-entity-registry.json<br/>people/orgs/aliases 带 domain]
        ALIAS[entity-alias-map.json<br/>口径/别名(迁移并入 REG)]
    end
    subgraph 会议派生视图
        IDG[meeting-identity-graph.json<br/>speakers/会议上下文(保留)]
    end
    subgraph 消费端
        NET[Network.app engine :8812<br/>读 REG + 本地 events/relations]
        SG[SystemGraph gallery :8798<br/>只读人类维度视图]
        CLI[identity-graph.py<br/>--registry 写入门控]
    end
    IDG -->|派生导入| REG
    ALIAS -->|合并| REG
    REG --> NET
    REG --> SG
    CLI -->|受控写| REG
    NET -->|本地增强写| NET_DATA[(relationships.json<br/>events/relations)]
```

## 三、主源 schema（business-entity-registry.json）

```json
{
  "version": "1.0",
  "kind": "business-entity-registry",
  "updated": "2026-09-09T...",
  "domains": ["banking", "flowernet", "supply", "event", "cross"],
  "people": [
    {
      "id": "p-zhenyu",
      "name": "梁振宇",
      "aliases": ["振宇", "梁振宇", "初蘅方"],
      "domains": ["cross"],
      "orgIds": ["org-youchiqu", "org-chuheng"],
      "title": "初蘅创始人/用户本人",
      "role": "核心操盘手: 控盘51%+GP-LP; 全域",
      "verified": {"confidence": "high", "note": "用户确认"},
      "relations": [{"to": "org-youchiqu", "type": "GP/控盘"}, {"to": "p-ziyang", "type": "谈判"}]
    }
  ],
  "orgs": [
    {
      "id": "org-zhongheng",
      "name": "中恒天仰信息技术(北京)有限公司",
      "aliases": ["中恒天雅(口语误读)", "中恒天仰"],
      "domains": ["flowernet"],
      "type": "ESP城市合伙人中标主体",
      "uscc": "91110108327275954W",
      "legalRep": "雷玛莎",
      "owner": "林燕100%",
      "role": "【ESP城市合伙人-成都】中标主体",
      "verified": {"confidence": "high", "ts": "2026-09-09", "note": "企查查锁定+中标公告"},
      "risk": "35项仅1条原告涉诉"
    }
  ]
}
```

**与 identity-graph.json 的关系**：
- identity-graph = 会议人脉派生视图（保留 speakers/场次上下文），只增不改字段
- REG = 业务实体主源（跨域 people/orgs/aliases + verified/risk 核验状态）
- 会议识别 → identity-graph 更新 → **同步/映射进 REG**（CLI 单一入口）

## 四、混合写规则

| 数据 | 主写位置 | 说明 |
|---|---|---|
| people/orgs/aliases 基础信息 | **REG**（经 CLI --registry add 或升级 identity-graph --add-person 双写） | 全域一致 |
| verified/risk 核验状态 | **REG** | 企查查/信源回填处 |
| relations（人-人/人-组织） | REG 基础 + Network 本地增强 | REG 存主关系; Network 存强度/备注等增强 |
| events（时间线） | **Network 本地** (relationships.json events) | 会议时间线属 Network 域，自动提取管道写入 |
| speakers（会议映射） | identity-graph（派生视图） | 识别中间产物 |

**写入门控（Lean4 门延续）**：REG 仅经受控 CLI/API；前端只读。

## 五、events 妙记自动提取管道

```
L1 在场识别: identity-graph speakers 反查 → 人×会议出席矩阵
    振宇 obcnuhtix-0905=S4/S7 · obcnwhp3-0908=S5 · obcnwk6q-0908=S2(?)
L2 时间线落库: 每场妙记 → 1 event
    {id, meeting_id, date, title, attendees:[person ids], source:"speakers映射"}
L3 用户补充: 事件性质(决策/推进/分歧) + 结果 + 下一步 (GUI 增量补录)
```

- 妙记目录 29 个会议 JSON（含 title），首轮批量生成
- 未映射 speaker 会议 → "待标注池"（GUI 点选绑人，复用 --add-person 门控）

## 六、③ 全生意范围扩展

- REG domains 枚举四生意域 + cross（银行/活动/供应链/flowernet 跨界人如振宇）
- 人物 schema 支持多 orgIds + 多 domains（一人可属多域多组织）
- 别名映射统一带 domain/evidence/source/confidence（entity-alias-map 既有模式）
- 种子数据：identity-graph 8人8组织（会议） + entity-alias-map 5条（跨域别名，含淘闪口径修正） + business-asset-map 70资产（资产侧，暂不并入 REG 但 SG 视图可关联）

## 七、SystemGraph gallery 只读人类维度

- SG 新增只读端点（或由 bb-blueprint-gallery 读 REG 映射蓝图成员）
- 蓝图关联人 = REG people[domains~蓝图域] 交 orgIds 命中
- SG 不承担主写——REG 更新自动反映（读时取）

## 八、落地顺序与验收

1. 建 REG 主源（迁移 identity-graph 8人8组织 + entity-alias-map 5 别名 + 钟总信源核验状态）
2. 升级 identity-graph.py：--registry 命令（导入/导出/校验 REG↔IDG 一致性）
3. relationship-engine.py 改读 REG（加载 REG + 本地 relationships.json 增强合并）
4. events 提取脚本（scan meeting-notes → REG/Network events 首轮灌入）
5. SG 只读人类维度挂接
6. R006 验收：--selfcheck / --lean4-check / --tool-version v0.2.0 全过 + 重启验证

---
*Network v0.2 设计 v1 · 明鉴 · 2026-09-09 · 模式B+混合写已拍板*
