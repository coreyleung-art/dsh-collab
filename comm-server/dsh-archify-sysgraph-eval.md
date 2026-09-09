# dsh-archify 接入 SystemGraph 可行性评估（2026-09-07 星桥）

## 移植版概况（GongYuanCaiJi/dsh-archify）
- DSH 插件：JSON 规格 → 可验证架构图(5图型) → 独立 HTML
- 逐字保留上游 archify/（THIRD_PARTY_NOTICES 钉 SHA 零回归可验）
- 安装：dsh plugin --profile add github:GongYuanCaiJi/dsh-archify
- 环境：node ^22.19||>=24 + dsh 0.1.0-rc.6
- 安全：零依赖/无遥测/无网络/无后台（prepare 仅暂存 skills/）

## SystemGraph 现状（明鉴域）
- 数据：hardware-nodes.json + device-links.json + business-asset-map.json（JSON）
- 渲染：gallery HTML 看板（8798 后端）+ macOS app
- 校验：schema-gate（integrity 100/100，Lean4 门）

## 可行性评估
### 数据形态匹配 ✅
SystemGraph nodes/edges JSON ↔ archify architecture JSON（typed IR）
- hardware-nodes.device/node → archify nodes（type/role）
- relations/device-links → archify connections（label/direction）
- business-asset-map → archify business view

### 能力互补 ✅（高价值）
| 维度 | SystemGraph 现 | archify 可补 |
|---|---|---|
| 可视化 | gallery 看板 | 交互单文件 HTML（搜索/主题/导出 PNG/SVG/WebM/分享卡）|
| 验证 | schema-gate | validate 9 项验收（showcase/standard）叠加 |
| 变更 | — | compare Before/Delta/After（架构演进追踪）|
| Mermaid | 技能链手写 | Mermaid 输入自动转（美化）|

### 接入路径（三选/叠加）
- A. DSH 插件装（agent 画图技能）：dsh plugin add——给全体 agent 加 archify 技能（仓库/系统描述→图）
- B. SystemGraph 导出升级：hardware-nodes/device-links → archify 规格 → validate → 交互 HTML（作为 SystemGraph 对外交付格式）
- C. 视觉看板增强：gallery 渲染层接入 archify 主题/预设（classic/signal-flow/blueprint/editorial）

### 障碍与风险
1. **版本匹配**：dsh 0.1.0-rc.6（我们 CLD dsh-runtime 版本需验证——可能不同需适配）
2. **node 要求**：^22.19||>=24（本机 node 版本需查——可能 <22.19 需升）
3. **pnpm allowBuilds**：profile 的 pnpm-workspace.yaml 需加 allowBuilds（供应链门 R-J37）
4. **技能英文**：上游逐字保留（已知限制，可接受/后续包壳中文化）
5. **Produced Files**：HTML 产物需 agent 返回精确路径（非自动显示）

## 结论
**可行且高价值**：archify 的「typed JSON IR + 确定性验证渲染」与 SystemGraph 数据(JSON)+schema-gate 哲学同源；最大增量 = SystemGraph 图的**交互化对外交付**（架构演进对比/分享）与 agent 画图技能。建议按 A+B 渐进（先装技能试跑，再数据桥接导出）。

## 下一步（待批）
1. 版本核验（dsh/node 本机版本 vs 要求）→ 2. 装 dsh-archify 试跑（沙箱）→ 3. 数据桥接 demo（hardware-nodes → archify 规格 → HTML）→ 4. 明鉴评审接入

## Demo 验证结果（2026-09-07 沙箱实测）
1. ✅ SystemGraph hardware-nodes.json → archify architecture 规格：**schema 校验通过**（type 枚举映射 messagebus/backend/cloud/external）
2. ✅ archify 渲染管线工作：官方 example deliver 9/9 artifact checks pass（633KB 交互 HTML）
3. ⚠️ 自定义规格 grid 自动布局 NaN：组件需显式 pos [x,y] + size（或调 grid origin/spacing 参数）——集成时处理（非可行性障碍）
4. Demo 产物：/tmp/dsh-archify-sandbox/{demo-crossdevice.architecture.json, checkout-demo.html}
5. 结论修正：数据桥接可行（schema 层通），渲染集成需 layout 参数适配

---

## 自研评估（2026-09-07 用户问 · R006 十项视角）

### 核心区分
archify 两层：
- 架构思想层（typed JSON IR + 确定性验证渲染）——**我们已自研内化**（bb-gate/lean4-check/schema-gate 同哲学；SystemGraph 数据即 JSON IR；规格转换桥已做 demo）
- 渲染器本体（布局引擎+交互 HTML+导出 PNG/SVG/WebM）——上游 ~数百 KB Node 工程，**自研=数月工作量**

### R006 十项对照
| 项 | 第三方依赖(现状) | 自研 |
|---|---|---|
| ① dsh 插件形态 | ✓ 移植版 | ✓ 可控 |
| ⑩ Lean4 约束门 | ✗ 上游无 | ✓ 内建 lean4-check |
| ⑥ 版本管理 | ✗ 随上游 | ✓ 自控 |
| ④ dsh 版本自适应 | ⚠️ 适配滞后 | ✓ 同步 |
| ⑧ 自动落链 | ✗ | ✓ 深度集成 |

### 结论（用户批准 2026-09-07）：分层策略，非全有全无
1. 思想层：已自研（规格+验证+SystemGraph 桥）
2. 渲染层：先依赖上游（MIT 活跃，demo 9/9 验证）——若渲染成核心资产（对外交付主业务）再立项自研
3. 中间桥：自研（SystemGraph→archify 规格转换已做 demo）
4. 全量自研克隆 = 复制上游渲染器护城河 = 数月工程，当前 ROI 低 → 不做

### 触发自研的条件（未来）
- 上游停止维护/license 变化
- 交互图渲染成为核心产品能力（对外交付主业务）
