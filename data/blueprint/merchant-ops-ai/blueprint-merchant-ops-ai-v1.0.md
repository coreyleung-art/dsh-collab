# blueprint:merchant-ops-ai · 商家 AI 运营产品线（外卖能力商家自助） · v1.0

> 生成：明鉴 v3 · 2026-09-06 · 用户决策: 栈3(商家向 MCP) 独立产品线
> 依据：妙记1「鲜花零售AI落地与业务布局」(obcnouizf, 2026-09-05) + 四栈 MCP 总规划(docs/mcp-four-stack-masterplan-v1.md)
> ⚠️ 定位: merchant-ops-ai ≠ laodeng-app(触达壳) ≠ mtm(代运营作业)——本蓝图=面向外卖商家的 AI 自助运营能力产品(MCP merchant 栈)
> 核心商业依据(妙记1): 自研 AI 运营工具产品化——自动改价/上下架/竞品监控/库存联动; 人效 20→50 店/人; 千店边际递减; 可泛化宠物/餐饮垂类

## 〇、BP-9 元信息

| 字段 | 值 |
|------|-----|
| id | merchant-ops-ai |
| name | 商家 AI 运营产品线（waimai-mcp-merchant 独立产品化） |
| version | v1.0 |
| dim | 产品 |
| mainlines | {"ai-ops": {"desc": "AI 自动运营(改价/上下架/竞品/防作弊)", "name": "AI 作业线"}, "merchant-ui": {"desc": "商家自助界面/MCP 接入(单店看板)", "name": "商家界面线"}, "replicate": {"desc": "跨垂类复制(宠物/餐饮等本地生活)", "name": "泛化复制线"}} |
| gate | ① 动作确认流(商家授权不可绕过) ② 测试仅守白店(J29) ③ MCP 动作 R027+R026 门 |
| status | active |
| ts | 2026-09-06 |

## 一、主线

- **ai-ops**：AI 作业线 — 自动改价/上下架/竞品监控/库存联动(妙记1: AI 改价锚定库存红线, 单小时46次改价)
- **merchant-ui**：商家界面线 — 单店看板(消费 waimai-mcp-core 只读) + AI 建议确认流 + SaaS 订阅形态
- **replicate**：泛化复制线 — AI 运营框架复制宠物/餐饮垂类(妙记1: 跨行业标准化工具矩阵)

## 二、阶段与子阶段

### 1.0 产品定案 [active]
- mo-1 商业模式定案 [todo] — 妙记1 能力产品化: SaaS 订阅定价(¥99-499/月) vs 效果分成
- mo-2 用户对象边界 [done] — 单商家/自有+代理门店(非代运营服务商, 服务商走 mtm ops)

### 2.0 MCP 能力接入 [todo]
- mo-2-1 消费 waimai-mcp-core [todo] — 单店只读看板 + AI 动作建议(商家确认后执行)
- mo-2-2 确认流设计 [todo] — 商家 GUI/MCP 确认动作(R027: 无授权不可执行)

### 3.0 产品壳 [todo]
- mo-3-1 SaaS 前端/订阅 [todo] — 商家自助界面
- mo-3-2 泛化复制验证 [todo] — 选 1 垂类(宠物/餐饮)试点

## 三、relations

- mcp consumer of: mtm#mcp-export-4(栈3 原登记位移至本蓝图, mtm 保留 core/ops)
- uses: agent-network#mcp-access(栈1 通讯底座)
- references: flowernet(自营门店数据域)
- ⚠️ distinct_from: laodeng-app(触达壳, 非运营能力) / mtm(代运营作业, 非商家自助)

## 四、资产（待入 business-asset-map）
- waimai-mcp-merchant(栈3) → 移本蓝图(node: mac-mini)
- AI 运营工具框架(妙记1 自研) → 产品核心

## 五、考量登记(2026-09-06 · 不实施, 防丢失)
- **门店接入形态谱系**(docs/store-access-form-spectrum-v1.md): A远程(软件·已共识)→B U盘钥(服务商随身)→C 带屏盒(商家常驻=星台+老登融合体)→双形态产品化(B钥+C盒)
- 启用 gate: ①软能力验证(四栈+门店A试点) ②商业模式确认 ③客户形态选型 ④硬件预算批准 —— 全满足才进硬件化, 否则保持软件形态
- C 盒若启用 = merchant-ui 主线的硬件交付形态(看板常显+对话+建议确认); 动作一律"建议+影子先行"(用户原则)
- 关联: Windows 部署评估(windows-store-deployment-eval-v1.md v1.1 MCP融合)

---
*blueprint:merchant-ops-ai v1.0 · 明鉴 v3 · 2026-09-06 · 用户决策: 独立产品线*
