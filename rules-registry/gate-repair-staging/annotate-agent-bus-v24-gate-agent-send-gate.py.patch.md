# gate-repairer annotate 补丁建议 (审核后应用)
# 目标: RULES.md 中 [agent-bus-v24-gate] agent-bus-v24-gate
# 动作: 规则详情尾部追加结构门标注
# 建议文本:
- **结构门**: agent-send-gate.py (经 gate-repairer 3.0.0 加固标注, 2026-09-07)
# 效果: gate-auditor 再扫该条将判 structural (引用工具名)
