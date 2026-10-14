# 仓库全量盘点与整理规划（2026-10-08 · 星桥）

## 一、取证摘要（2026-10-08 实测）

| 端 | 数量 | 状态 |
|---|---|---|
| GitHub coreyleung-art | 55 仓 | 活跃 6（今晚推）；DSH 生态 13（08-10 月）；OpenClaw/LLM 时代 ~20（02-04 月）；著名项目 fork 8（PythonRobotics/tesseract/WeKnora/XLeRobot/ollama/claude-code/moltbot/Peekaboo）；疑似误建 1（「-」）；2024 遗留 2 |
| Gitee coreyleung | 15 仓 | **全部 private**（含今晚 5 个——实际建成了私有，比我以为的公开更安全） |
| 本地 ↔ remote | — | agent-bus→agent-way 命名漂移；central-inbox 5 文件未提交；channel-gate/guard 等无 git |

## 二、问题清单（按风险排序）

1. **敏感仓库公开**：GitHub 上 `fn-bp-fdb2052b`（花联网公司发展计划）、`flower-shop-naming`、`hermes-agent` 等业务/计划类为 PUBLIC——商业机密暴露面
2. **命名漂移**：本地 `dsh-plugin-agent-bus` ↔ GitHub 仓 `dsh-plugin-agent-way`（PSTD N2 审计项，账本 R047 已登记属主星桥）
3. **未提交漂移**：central-inbox 5 个文件（v0.2.15 未发布源码）未提交未推
4. **本地无版本控制的治理插件**：channel-gate、guard 等没有 .git
5. **疑似误建仓**：「-」（private，2026-04-20）
6. **历史冗余**：dsh-collab / dsh-collab-cld / dsh-rules-registry 三个仓库是「治理仓」的演进三代（dsh-collab 为现行）
7. **fork 库存**：8 个著名项目 fork 无本地关联，仅存档价值

## 三、整理方案（按执行顺序）

### ① 修命名 + 提交漂移（先做，无风险）
- GitHub 仓 `dsh-plugin-agent-way` → 改名 `dsh-plugin-agent-bus`（gh repo rename，本地 remote 同步改）
- central-inbox 提交并推 5 个文件（v0.2.15 源码）

### ② 敏感仓转私有（GitHub）
- 转 PRIVATE：`fn-bp-fdb2052b`、`flower-shop-naming`、`hermes-agent`、`corey-i9`（已私）、`phoneuse`（已私）、`openclaw-ha-state`（已私）
- 规则：业务/计划/个人数据类一律 private；工具/插件类可 public
- Gitee 侧已全 private，无需动

### ③ 活跃自研仓 → 双仓镜像
- 现活跃 6 仓 + dsh 生态活跃插件（agent-bus、central-inbox、repo-pipeline、hr、external-link-policy、openchronicle、dsh-tools、node-bridge）
- GitHub 为主 + Gitee 镜像 + gitee-sync 工作流（复用 repo-pipeline 模板）

### ④ 历史仓归档/清理
- 归档（README 加 ARCHIVED 说明，保留不删）：`dsh-collab-cld`、`dsh-rules-registry`（指向现行 dsh-collab）、2024 遗留 2 个
- 查证后删除：「-」仓（先拉元数据确认内容再删）
- fork 类：保留 GitHub 页面存档，不维护、不入镜像

### ⑤ 治理插件全部入库（补 git）
- channel-gate、guard 等本机治理插件 init + 建仓 + 首推（与 PSTD 命名门对齐后再建，避免又造 N2/N3 漂移）

### ⑥ 落登记卡
- `data/registry/repo-inventory-v1`：三端对照表（本地目录 ↔ GitHub ↔ Gitee）+ 镜像状态 + 敏感级别

## 四、执行安全边界

- 全程 SSH（新钥匙已全权限）；Gitee 用 token 内联推送（不入 config）
- 改名/转私有前先 gh api 备份元数据（json 留档）
- 不在本规划内动：MBP 侧本地仓库（其域）、i9 侧

## 五、裁判有条件通过的整改（2026-10-08）

### 6.1 程序补正：R046 声明体
见 audits/20261008/r048-repo-plan-claim.json（surface/surface_measured/surface_unmeasured/evidence_refs 齐备，经 acceptance-gate --check）。

### 6.2 数字更正：54 仓（43 PUBLIC / 11 PRIVATE），原方案「55」作废

### 6.3 43 个 PUBLIC 逐仓分类（实测 2026-10-08）

| 分类 | 处置 | 仓 |
|---|---|---|
| A 业务/计划敏感 → 转私有 | fn-bp-fdb2052b（花联网计划）· flower-shop-naming · hermes-agent · turboquant_plus · teaching-boyfriend-llm · vision-automation-framework · deer-flow · sect-alliance-sdk · evil-read-arxiv | 
| B 自研工具/治理 → 保持公开（双仓镜像） | dsh-collab · dsh-plugin-*（pstd/agent-way/central-inbox/external-link-policy/hr/openchronicle/repo-pipeline）· dsh-files · dsh-tools · dsh-collab-cld · dsh-collab-install-playbooks · dsh-rules-registry · node-bridge · rust-blackboard · openchronicle · sb-mobile · meituan-multi（业务代码但含运营方法论价值；若老板要求转私则归 A）· CLD（救援产物留档） |
| C 著名项目 fork / 二手克隆 → 归档不删 | PythonRobotics · tesseract · WeKnora · XLeRobot · ollama · claude-code · moltbot · Peekaboo · Claude-Code-Notifier · awesome-claude-code-subagents · awesome-deepseek-integration · clawflows · openclaw-feishu |
| D 2024 遗留 → 归档 | getting-started · multi-container-app |

### 6.4 改名/转私有影响面声明
- agent-way→agent-bus：本地 ~/dsh-plugin-agent-bus remote 同步改；R047 台账已登记此 N2 项；无 CI 依赖该仓名（查无 workflow 引用）。
- 转私有：无 fork 依赖（fork 数待逐仓核）；公开 README 外链失效仅影响外部访客。

### 6.5 删除「-」仓：审批单 aprv-muylf3qj-nfdq0kbt 待老板裁决；批准则三件齐备（Git 层 mirror 留档→书面记录→删）
- 平台数据实测（裁判 state=all，2026-10-08）：issues=0 / pulls=0 / releases=0；has_wiki=false / has_discussions=false ⇒ **无平台数据可失**
- 不可逆记录措辞据此改为「实测 issue/PR/release 均为 0，无物可失」（原「将永久丢失」暗示有损失，不实）
- 判「是否曾有过 issue」必须用 `issues?state=all`（`open_issues_count` 只含未解决，会漏已关闭）
- 补测（2026-10-08，裁判标未覆盖的面）：deployments=0 · environments=0 · has_pages/has_wiki/has_discussions 均 false · fork=false · size=0 · pushed==created=2026-04-20（建后从未推送）
- ⚠ **packages 面：推进一档后仍不称 0**（裁判 2026-10-08 补第三条路径）
  · 三条路径读数：仓库级 container/npm ⇒ 404；组织级 ⇒ 404；用户级与 `/user/packages` ⇒ 403（PAT 缺 scope）⇒ **404/403 均无法区分「无权限」与「真的没有」**
  · ★ 第三条路径（无需 token）：**账号级 packages 页** `https://github.com/coreyleung-art?tab=packages` ⇒ 呈现**空白引导页**（该账号尚无任何 package 时的空态）
  · ⇒ 准确表述：**「未登录可见范围内，该账号无 packages；登录后是否可见 private packages：未证」** —— 不称 0，删除评估按此口径记录
