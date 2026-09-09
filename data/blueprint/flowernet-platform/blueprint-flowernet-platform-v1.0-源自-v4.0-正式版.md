# blueprint:flowernet-platform · FlowerNet 技术基础设施（P0 协议→P5 应用） · v1.0（源自 v4.0 正式版）

> 生成：bb-blueprint-create.py · 2026-09-02T00:17:15 · 三件套纪律（文档/代码/依赖）
> 状态：active · 门禁：里程碑 M1-M5：M1 插件可安装 ✅ → M2 基础可靠（身份/audit/token）→ M3 企业级（云接管/计量/看门狗）→ M4 多租户（门店隔离 PoC）→ M5 商业化（首个付费订阅）
> 依据：docs/flowernet-master-blueprint-v4-20260827.md（15 可靠性缺口全映射）

## 〇、BP-9 元信息

| 字段 | 值 |
|------|-----|
| id | flowernet-platform |
| name | FlowerNet 技术基础设施（P0 协议→P5 应用） |
| version | v1.0（源自 v4.0 正式版） |
| mainlines | {"app": {"desc": "花店蓝图（业务）+ 订阅平台（ERP HA）", "name": "应用层"}, "bridge": {"desc": "n... |
| stages | [{"id": "fp0", "mainline": "protocol", "name": "协议层 FNP", "stage": "P0", "status... |
| works | [{"owner": "星桥", "stage": "fp0-1", "status": "done", "work": "FNP v1.0 规范正式化"}, ... |
| gate | 里程碑 M1-M5：M1 插件可安装 ✅ → M2 基础可靠（身份/audit/token）→ M3 企业级（云接管/计量/看门狗）→ M4 多租户（门店隔离 PoC）→ M5 商业化（首个付费订阅） |
| status | active |
| ts | 2026-09-02T00:17:15 |

## 一、主线

- **app**：应用层 — 花店蓝图（业务）+ 订阅平台（ERP HA）
- **bridge**：桥接层 — node-bridge + dsh-tools（看门狗/版本统一）
- **govern**：治理层 — deploy-check/自适应/台账/多租户
- **infra**：基础设施 — HubBridge Server：身份/计量/HA/audit/token/genebank
- **plugin**：插件层 — dsh 插件家族（agent-way/central-inbox/门店插件）
- **protocol**：协议层 — FlowerNet FNP 语义定义

## 二、阶段与子阶段

### P0 协议层 FNP [active]
- fp0-1 FNP v1.0 规范 [done] — 已正式化（2026-08-23）✅
- fp0-2 v0.7 per-namespace 授权 [todo] — 门店数据隔离（缺口 #8）
- fp0-3 v1.1 能力发现 [todo] — 门店 capabilities（缺口 #8）

### P1 基础设施 HubBridge [partial]
- fp1-1 传输层 rust-blackboard [done] — 8792+8803 ✅
- fp1-2 身份层（device-id+token） [done] — register API ✅ identity ✅ 认证中间件 ✅（v0.6.4）
- fp1-3 计量层（token 计量+订阅） [todo] — 缺口 #3：SQLite 计量+订阅层级
- fp1-4 HA（云接管+备份） [todo] — 缺口 #4：腾讯云轻量部署+snapshot 备份
- fp1-5 audit 轮转+保留 [todo] — 缺口 #5：磁盘可控 <100MB/天
- fp1-6 genebank 恢复启用 [todo] — 缺口 #9：/api/v1/genes 验证

### P2 插件层 dsh 家族 [active]
- fp2-1 peerDeps 补全 [done] — 11 个（v1.3.0）✅ 缺口 #1
- fp2-2 三端安装验证 [active] — MBP/i9 git URL 安装（缺口 #1 收尾）
- fp2-3 门店插件 [todo] — FlowerNet 接入（缺口 #8）

### P3 桥接层 [partial]
- fp3-1 node-bridge 看门狗 [todo] — 崩溃自启（缺口 #6）
- fp3-2 三端版本统一 v1.2.0+ [todo] — 缺口 #12/#13

### P4 治理层 [partial]
- fp4-1 台账自动化 [done] — git tag+version 扫描（缺口 #7）✅
- fp4-2 多租户安全 ZTNA/mTLS [todo] — 门店隔离（缺口 #8）
- fp4-3 规则灰度发布 [todo] — 新规则影子模式→回测误杀率→硬阻断（rule-judge rj2-3 衔接）
- fp4-4 LLM 二次审查层 [todo] — 规则层拦数字硬错误+LLM审策略合理性——1000店分界线启用（年损失73万vs成本几万）

### P5 应用层 [todo]
- fp5-1 ERP PG16 备份 [todo] — 缺口 #10：pg_dump 定时
- fp5-2 订阅平台 [todo] — 缺口 #3：租户+支付+计费
- fp5-3 门店端到端 [todo] — 注册→隔离→数据→订阅（缺口 #8）

## 三、工作项（works）

| 状态 | 工作 | owner | stage |
|------|------|-------|-------|
| done | FNP v1.0 规范正式化 | 星桥 | fp0-1 |
| active | 黑板 token 启用（BLACKBOARD_TOKEN） | 星桥 | fp1-2 |
| todo | 计量层+订阅层级（缺口 #3） | 星桥 | fp1-3 |
| todo | HA 云部署+备份（缺口 #4） | 星桥 | fp1-4 |
| todo | 三端 node-bridge 版本统一 | 星桥 | fp3-2 |
| todo | 多租户隔离（进货价/利润/客户数据隔离） | 星桥 | fp4-2 |
| todo | 规则灰度发布框架（影子模式） | 明鉴 | fp4-3 |
| todo | LLM 二次审查层评估（1000店门槛） | 明鉴 | fp4-4 |

## 四、依赖关系（relations）

- **contains**：flowernet
- **depends_on**：agent-network
- **references**：blueprint-platform

## 四b、自动化开关锁（R027 + Lean4 逻辑锁）

（无自动化开关声明——非 AI 自动化阶段或待补）

## 五、门禁链

里程碑 M1-M5：M1 插件可安装 ✅ → M2 基础可靠（身份/audit/token）→ M3 企业级（云接管/计量/看门狗）→ M4 多租户（门店隔离 PoC）→ M5 商业化（首个付费订阅）

---
*blueprint:flowernet-platform · v1.0（源自 v4.0 正式版） · 三件套纪律落盘*
