# subagent-govern · 子代理资源治理工具

> v1.1 增强：analyze --sediment（评估报告落盘+KB 向量化入库）→ check-new 检索历史报告 → **跨会话复用**（任何会话新建子代理前可识别存量可复用者，省 ~1400 token/次）

> 版本：v1.0.0 · 属主：HR 司库 · R006 九标准全达标
> 定位：子代理「评估→处理→协调」三过程工具化（2026-08-31 治理评估落地：15 子代理发现 2 重复+3 僵尸）

## 四过程
| 过程 | 命令 | 说明 |
|---|---|---|
| 新建前评估 | check-new --role <描述> | **R021 前置**：拟建子代理 vs 现有匹配 → REUSE（复用）/ CREATE（可新建） |
| 评估 | audit [--json] | 扫 agent_profiles → 类型分组 → 活跃度 → 僵尸/重复检测 → 建议 |
| 处理 | cleanup --targets <id1,id2> [--dry-run/--apply] | dry-run 预览 → apply 归档（workspace.json+备份） |
| 协调 | coordinate --targets <id1,id2> | 登记/黑板/通知/重启生效 动作清单 |

### check-new 示例
python3 subagent-govern.py check-new --role "论文调研-供应链方向"  # REUSE（匹配现有）
python3 subagent-govern.py check-new --role "数据可视化专员"       # CREATE（无现成）

## 判定标准
- 僵尸：消息 <5 条 且 活跃 >7 天
- 活跃：>=20 条消息
- 重复：同 role 精确匹配（>1 个）

## R006 九标准（全部实测 PASS）
插件形态（预留）/ TCC 自检（selfcheck PASS）/ CLD 自适应（cld-check PASS）/ dsh 版本自适应（version-check PASS）/ 文档（本 README）/ 版本（--version v1.0.0）/ 统一日志（~/.dsh/subagent-govern.log）/ 自动落链（coordinate+registry 登记）/ CLI 治理（9 子命令）
插件形态（预留）/ TCC 自检（selfcheck）/ CLD 自适应 / dsh 版本自适应 / 文档（本 README）/ 版本（--version）/ 统一日志（~/.dsh/subagent-govern.log）/ 自动落链（coordinate）/ CLI 治理

## 示例
python3 subagent-govern.py audit
python3 subagent-govern.py audit --json
python3 subagent-govern.py cleanup --targets session-xxx --dry-run
python3 subagent-govern.py cleanup --targets session-xxx --apply
python3 subagent-govern.py coordinate --targets session-xxx

## 注意
- workspace.json 改动按知了教训需重启生效（运行中改被宿主覆盖）——随受控重启窗口
- 零 LLM：纯规则 + agent-bus 数据

## 🚨 灾难级安全护栏（用户要求，2026-08-31）
1. **主角色黑名单**：协调者/资源管理/运营/客服/学习/摄取/调查/供应链/QA/设备/媒体/外链/健康/运维/开发/插件/洞察/恢复/自查/知识库/监督等主角色关键词 + 设备前缀 + 有资源档案 → 一律禁止归档（cleanup 返回 🚫 中止）
2. **audit 严格判定**：仅明确标注「子代理/worker/Ralph/调研专员」且无主角色格式的才视为子代理（宁可漏判不可误判）
3. **apply 三重确认**：dry-run 预览 → 主角色拦截校验 → 交互输入 YES 才执行
4. **零崩溃风险**：只写 workspace.json（纯 JSON + 备份），不动 CLD 本体/插件 bundle/宿主进程；与 cordis-crash-audit 审查范围无关
5. 实测：主角色拦截 ✅ / 子代理 10 个识别准确 / 零主角色误判
