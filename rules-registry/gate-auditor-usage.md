# gate-auditor v1.1.0 纸面门审查器（2026-09-07）

> 起源：archify 事故教训（清单写了沙箱测试但被跳过 = 纸面门被绕过）
> 用途：扫描全局规则/流程门声明 → 识别「纸面门」（声明无工具）vs「结构门」（工具实现+lean4-check），输出候选清单供逐项升级

## 用法
- python3 ~/dsh-collab/scripts/gate-auditor.py --lean4-check   # 自检（识别门生效证明）
- python3 ~/dsh-collab/scripts/gate-auditor.py scan             # 扫描 RULES.md 出纸面门报告
- python3 ~/dsh-collab/scripts/gate-auditor.py list-tools       # 结构门工具注册表
- python3 ~/dsh-collab/scripts/gate-auditor.py --version

## 识别逻辑（Lean4 同源：纯函数+自检）
- is_structural(text)：命中结构门工具注册表（bb-gate/lean4-check/cld-monitor/agent_lock 等 30+）
- classify_entry：有门措辞+工具=structural / 有门措辞无工具=paper / 无门词=doc-only
- 报告：纸面门候选 + 建议升级路径（领域启发）

## v1.1 首扫结果（RULES.md 75 规则）
- 结构门 24 / 纸面门候选 51
- ⚠️ 精度：51 为候选清单（含误报——需人工逐条确认归属后升级）；审计器定位=筛候选非定论

## 校准方向（迭代）
- 工具注册表扩展（每次新结构门工具加入登记）
- 每条 paper 确认后：或登记其对应工具（改 structural）或设计升级结构门（如 plugin-install-gate）
