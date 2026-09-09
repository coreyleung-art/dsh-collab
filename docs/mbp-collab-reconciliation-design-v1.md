# MBP ↔ mac-mini 跨设备对账设计（HR 司库 · 2026-09-06）

> 背景：用户指示「跟 mbphr 开会沟通，全量对齐和吸收 mbp 侧要素和信息以及规则，设计一个类似的对账逻辑」
> 现实约束（实测）：① MBP 心跳 6 天未更新（nodes/mbp ts=2026-08-30）→ 当前非在线协作 ② mac-mini 总线上无 mbp-hr/mbp-ops 会话 ③ MBP 治理资产已由老登 SSH 拉取镜像（research/mbp-memory-gov/，36 文件 1.57MB）④ 已存在 tools-registry.md + 多设备治理泛化手册-v1（设计图）
> 方案定位：**异步对账**（拉取周期内全量比对），MBP 在线时升级为实时同步

═══════════════════════════════════════

## 一、对账对象（5 类要素）

| 类别 | mac-mini 侧（基准） | MBP 侧（待对齐） | 对账方法 |
|---|---|---|---|
| ① 规则 | RULES.md / rules.json（75 条 v2.14）| mbp 独有规则（多设备治理/值守交接/插件工程）| 规则对账：diff + 吸收 |
| ② 工具 | scripts/ 134 + rust-tools v1.17 | labforge/guard/runner（11 工具 v1.1.0）| tools-registry 对账 |
| ③ 教训 | 本地 repair-reports 双目录 | MBP 37+7 修复报告 + 01-踩坑（敏感清单/插件机制）| 考古对账 |
| ④ 资产 | resource-registry v1.0.407 | mtm 架构 / 内存治理实验 / rust 评估 | 镜像清单对账 |
| ⑤ 状态 | 节点心跳/版本 | nodes/mbp（陈旧）+ device-registry | 心跳对账 |

## 二、对账逻辑（核心算法）

```
对账 = 三阶段：盘点(diff) → 分级(absorbable/sync-only/reference) → 登记(registry)

1. 盘点：拉取 MBP 侧 manifest（tools-registry/规则集/考古清单）↔ mac-mini 现状
   - 规则：RULES.md 条目 vs MBP 侧规则文件（按 id diff）
   - 工具：tools-registry 版本 vs 本地 scripts/（name+version 匹配）
   - 教训：repair-reports 案例库 vs MBP 考古（根因模式 M1-M6 已泛化）
2. 分级判定：
   - **absorbable**（应吸收）：MBP 独有且 mac-mini 缺失的规则/工具/教训（如 DSH 插件工程机制、敏感清单轮换提醒）
   - **sync-only**（仅同步）：同源不同版本（tools-registry 版本对齐、guard/labforge 部署）
   - **reference**（仅参考）：MBP 业务专属（mtm 架构/内存实验数据）→ 镜像索引不并入
3. 登记：吸收项 → rules.json/RULES.md + resource-registry；同步项 → tools-registry 版本更新；参考项 → 镜像 README-INDEX
```

## 三、执行路径（用户可操作）

### 路径 A · MBP 在线（用户在 MBP 前，推荐开会式）
1. 用户在 MBP 打开其 HR/治理会话（mbphr 或 mbp-ops）
2. mac-mini 侧我（HR 司库）产出「对齐请求单」（本文件 §四 对账清单）
3. 用户经 SSH/黑板 notes/mbp/ 传递 → MBP 侧执行 → 回报
4. mac-mini 收回报 → 逐项吸收登记（红绿灯）

### 路径 B · MBP 离线（异步，当前可行）
1. 老登 SSH 拉取（已有 mbp-memory-gov 先例）→ 更新镜像
2. 我基于镜像跑对账（§二算法）→ 产出吸收清单
3. 吸收项落 registry + 规则本；下次 MBP 上线推送回去

## 四、本次对账清单（待 MBP 侧确认/已从镜像吸收）

| # | 要素 | MBP 侧源 | 判定 | mac-mini 处置 |
|---|---|---|---|---|
| 1 | DSH 插件工程机制（symlink 依赖/defineTool API/cordis.patch 格式）| 01-踩坑 §5 | **absorbable** | 吸收为 docs/dsh-plugin-engineering-lessons.md + 入规则参考 |
| 2 | 敏感项轮换清单（Tavily/Tailscale/DeepSeek 等）| 01-踩坑 §四 | **absorbable** | 吸收为凭据轮换提醒（C3/H4 纪律延伸，只登记位置不登记内容）|
| 3 | skill 跨设备不通用教训 | 01-踩坑 §1 | **absorbable** | 入 role-name-check / preset 泛化规则 |
| 4 | 内存治理证据（OOM 复现/tail 窗口 23x/152x）| poc/memory-crash-lab | **reference** | 已镜像+向量化，作 HR 成本治理参考 |
| 5 | labforge/guard 工具 | archaeology-mbp | **sync-only** | tools-registry 对齐（MBP 侧 11 工具已在档）|
| 6 | CLD 崩溃时间线 9 次 + M1-M6 模式 | 历史问题考古报告 | **absorbable** | M1-M6 已与本地 guard-archaeology 6 模式一致 → 确认合并 |
| 7 | mtm 8787 架构（Chrome 多实例）| mtm-from-mac | **reference** | 镜像索引 |
| 8 | 值守交接机制（心跳/事件桥/恢复）| 值守交接单 | **absorbable** | 与 mac-mini 值守 SOP 对齐 |

## 五、交付物
1. 本设计文档（对账算法 + 清单）
2. MBP 在线时：开会对账 → 逐项确认
3. MBP 离线时：基于镜像先吸收 reference/absorbable 类（不依赖 MBP 在线）
4. 长期：对账工具化（对账逻辑可复用 i9/其他设备）

---
*对账设计 v1.0 · HR 司库 · 2026-09-06*
