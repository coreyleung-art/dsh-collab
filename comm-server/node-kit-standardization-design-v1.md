# 节点装备标准化 + 设备/Agent 身份注册表 设计 v1（2026-09-08 星桥）

> 触发：用户三问——①漏变量类 bug 能否加 Lean4 结构门 ②建立守护+部署标准化为未来节点（Windows 为主）落地方案 ③服务器注册表/路由应清晰区分设备与端口节点（agent 身份证）
> 直接教训：device-daemon.py DSH_NODE_ID 硬编码日志 bug（漏变量）→ 需结构门防复发
> 关联：E2 discovery schema / SystemGraph registry schema-v1 / gate-j23/j24 Lean4 门 / R032 三写

---

## 一、问题定性（三问合一）

1. **漏变量** = 逻辑正确但字面量残留（日志/默认值写死"mac-mini"）→ 部署到 MBP 时行为正确、日志误导，难排查。属**结构可验证错误**，应入 Lean4 门。
2. **节点落地** = 每次手动 scp+env+launchd+验证（MBP 这次踩了 5 个坑：目录/token/黑板地址/代理身份/硬编码）→ 需**一次装备、处处复用**的标准化。
3. **身份注册** = MBP 被 hb-fwd 代管注册（via: hb-fwd-mac-mini），掩盖了"MBP 自己有 CLD/黑板/agent"的事实 → 服务器路由无法清晰区分 → 需**设备自报身份**取代代管。

## 二、设计：三层

### 层 1 · Lean4 结构门（防漏变量/漏配置类）
新建 `gate-deploy-check.py`（部署门，入 gate 工具族），静态检查守护/脚本：
- **G-D1 字面量门**：脚本内不得硬编码 NODE 名（mac-mini/mbp/i9）、本机 IP、端口——须 env 或配置取
- **G-D2 env 契约门**：声明的 env 变量（DSH_NODE_ID/SERVER_BUS/LOCAL_BB/BB_TOKEN）启动前校验存在+格式
- **G-D3 平台门**：launchd/schtasks/systemd 平台模板与脚本内平台判断一致
- **G-D4 幂等门**：部署脚本可重复运行不破坏（已有状态检测）
- 用法：`gate-deploy-check.py --file device-daemon.py` → PASS/FAIL 列表
- 先例对齐：gate-j23/j24（Lean4 演练门）同模式，入 RULES.md 十项

### 层 2 · 装备包（node-kit）标准化
单目录 `~/dsh-collab/node-kit/` 一键装备任何节点：
```
node-kit/
├── device-daemon.py      # 守护（env 驱动，零硬编码——层1门保障）
├── deploy.sh             # 一键：建目录→校验→装守护→平台注册→自检
├── selfcheck.sh          # 健康自检（守护在跑? 队列通? 心跳新?）
├── conf/<node>.env       # 每节点配置（DSH_NODE_ID/URLs/token路径）
├── platform/             # macOS:launchd / windows:schtasks+xml / linux:systemd
└── README.md             # 落地 SOP（Windows 为主说明）
```
- Windows 落地要点：schtasks 代替 launchd；python3 需装；守护纯 stdlib 跨平台（已满足）；token 存 %USERPROFILE%\.dsh\ 0600 等效
- 装备顺序（标准 SOP，一次跑通）：
  1. `deploy.sh --node <id>` 校验门（层1）
  2. 复制守护+conf+平台注册
  3. 自检 selfcheck.sh（守护/队列/心跳三项）
  4. 上报 E2 注册（层3 自报）

### 层 3 · 身份注册表 v2（设备自报身份证，取代 hb-fwd 代管）
- **设备自报**：节点启动时守护 PUT `/data/discovery/devices/<id>`：
  `{id, os, ip, cli_ver, services:[{port:8792,kind:blackboard},{port:8791,kind:bus}...], agents:[{session,role}], heartbeat_ref, via:"self"}` 
- **服务器校验**：via 必须 self（设备自己报）；hb-fwd 降级为"仅心跳转发兜底"不再"代管注册身份"
- **agent 身份证**：`agent-id = device:session:role` 全局唯一；路由查注册表而非猜测
- **路由分离**：bus target 解析 → 注册表查 device → 该设备 services 的 bus/SSE 端点 → 投递
- 迁移：现有 data/discovery/agents/<dev>（E2 schema v1）升级为 v2（加 services+via:self 强制）

## 三、实施顺序

- [ ] P0：gate-deploy-check.py（层1）+ device-daemon.py 硬编码清零（改 DSH_NODE_ID 日志 bug 已修，全面扫）
- [x] P1：node-kit 目录 + macOS 模板 + deploy.sh 可复跑（2026-09-09 明鉴完成: ~/dsh-collab/node-kit/ deploy.sh/conf模板/selfcheck/README; dry-run 验证）
- [ ] P2：E2 v2 注册（设备自报）+ 服务器路由查注册表 —— **已排期: 待星桥/i9 确认守护部署后推进**(2026-09-09)
- [ ] P3：Windows schtasks 模板 + 试点（i9 已验证可承载）
- [ ] P4：入 RULES.md（R033 节点装备标准化 + R034 身份自报）+ SystemGraph 注册表同步

## 四、验收
- [ ] 新脚本部署前跑 gate-deploy-check → 硬编码/env 问题全拦截（本次漏变量类 bug 不再复发）
- [ ] 模拟新节点（Windows）按 SOP 10 分钟装备完成+自检通过
- [ ] MBP 注册 from via:hb-fwd-mac-mini → via:self（自己报）
- [ ] 路由按注册表清晰区分各设备/端口

---
*星桥 2026-09-08 · 用户三问合一设计 · 每步落盘*
