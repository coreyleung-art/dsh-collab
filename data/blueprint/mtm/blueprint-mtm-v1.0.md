# blueprint:mtm · MTM 外卖门店多平台管理（代运营作业层工具） · v1.0

> 生成：明鉴 v2 · 2026-09-03 · 三件套纪律（文档/代码/依赖）
> 状态：active · 门禁：① 10 店代运营作业不因工具变更中断 ② 新平台接入先小规模试点再全量 ③ 批量/导出操作幂等可回滚
> 依据：产品定位 v1（黑板 data/ops/laodeng-vs-mtm-positioning-v1）+ meituan-multi 实际运行资产（8787 面板/脚本族）
> ⚠️ 定位：MTM ≠ 老登 App —— 本蓝图只管「代运营作业效率工具」，不管行业商家触达产品（见 docs/product-positioning-laodeng-vs-mtm-v1.md）
> 2026-09-06 四栈 MCP 扩展：mcp-export 主线（能力中台 core + 商家向 merchant + 服务商向 ops）—— 妙记1/2 双用户对象依据（docs/mcp-four-stack-masterplan-v1.md）

## 〇、BP-9 元信息

| 字段 | 值 |
|------|-----|
| id | mtm |
| name | MTM 外卖门店多平台管理（代运营作业层 + 能力 MCP 化） |
| version | v1.1 |
| mainlines | {"ops": {"desc": "多平台门店实时运营作业（10 店）", "name": "作业线"}, "auto": {"desc": "采集/监控/分析/批量操作的自动化能力", "name": "自动化线"}, "insight": {"desc": "经营分析/报表/决策支持", "name": "洞察线"}, "mcp-export": {"desc": "外卖能力 MCP 服务化: core能力中台+merchant商家向+ops服务商向", "name": "能力服务线(四栈)"}} |
| gate | ① 10 店代运营作业不因工具变更中断 ② 新平台接入先试点再全量 ③ 批量/导出幂等可回滚 ④ MCP 动作类强制 R027+R026 门 |
| status | active |
| ts | 2026-09-06 |

## 一、主线

- **ops**：作业线 — Chrome 多开 + 8787 面板 → 多平台（美团/京东/淘宝/抖音/快手）10 店实时运营作业
- **auto**：自动化线 — 采集/监控/分析/批量操作/导出 → 把重复作业工具化（产品下载/报表导出/价格分析/返图提取等 lib 族）
- **insight**：洞察线 — 经营日报/周报/关键词分析/流量分析 → 代运营决策支持
- **mcp-export**：能力服务线（新·2026-09-06） — 外卖能力 MCP 化四栈: core(能力中台·8787封装) / merchant(商家自助向·妙记1) / ops(服务商作业向·妙记2); 共享栈1 comm-mcp(agent-network) 通讯底座

## 二、阶段与子阶段

### 1.0 作业底座 [active]
- mt1-1 多平台接入 [done] — Chrome 多开实例 + 面板 8787（waimai-store-manager）
- mt1-2 实时监控 [done] — 事件采集/告警（新订单/超时/掉线）
- mt1-3 操作原语库 [done] — 接单/拒单/上下架/改价/改折扣/评价回复/售后（原语库 12+）

### 2.0 自动化 [active]
- mt2-1 报表自动化 [done] — 12 类报表导出双通道（report-export skill）
- mt2-2 数据下载分析 [done] — 商品销售订单下载（product-download）+ 价格策略（price-analysis）
- mt2-3 客服自动化 [todo] — 返图提取/反馈登记（return-photos）→ 消息登记

### 3.0 洞察 [todo]
- mt3-1 经营分析 [todo] — 日报/周报/投产比/流量（waimai_analyze/traffic/roi）
- mt3-2 智能建议 [todo] — 经营分析报告（Dify 工作流）→ 行动建议

### 4.0 MCP 能力服务化(mcp-export) [active 2026-09-06]
- mcp-export-1 四栈设计定稿 [done] — docs/mcp-four-stack-masterplan-v1.md + 妙记1/2 双用户对象
- mcp-export-2 waimai-mcp-core(栈2): 只读 7 工具封装 8787 [todo]
- mcp-export-3 鉴权+审计(栈2 P1) [todo]
- mcp-export-4 merchant(栈3): 单店 AI 建议面+商家确认流 [todo]
- mcp-export-5 ops(栈4): 多店矩阵+批量+抽佣统计 [todo]
- mcp-export-6 商业模式(栈3订阅/栈4阶梯收费) [todo] — 妙记2 收费模型输入

## 三、relations

- child_of: agent-network（工具底座系能力支撑）— 若需更清晰归属可改顶层独立
- references: flowernet（自营 flowernet 业务用 MTM 作业 → 消费关系）
- ⚠️ distinct_from: laodeng-app（老登 App = 行业商家触达层，非运营作业工具——勿混淆）
- mcp-export uses: agent-network#mcp-access（栈1 comm-mcp 通讯底座）
- merchant 面 references: flowernet（商家自营门店数据域）

## 四、资产（已在 business-asset-map v1.2）
- MTM 外卖门店多平台管理（app）→ 代码 ~/meituan-multi（mtm.js/scripts/lib/desktop）
- laodeng-h5 系列归 blueprint:laodeng-app，不属本蓝图
- 跨蓝图精确引用: MTM 作业数据可支撑老登 App 展示 → blueprint:laodeng-app#1.0(展示 Demo 阶段消费 MTM 作业样例); 反向 MTM 的 insight 洞察线引用 blueprint:flowernet#2.0(花店业务演进主线)
- 四栈 MCP 资产(待入 business-asset-map): waimai-mcp-core/merchant/ops + comm-mcp-server(栈1归 agent-network)

---
*blueprint:mtm v1.1 · 明鉴 v3 · 2026-09-06（v1.0: 2026-09-03）*
