# meeting-verify · 语音会议产物·原文核实器 — R006 十项合规

> 明鉴 · 2026-09-09 · v1.0.0 · 纯 stdlib Python CLI
> 触发: "淘闪口径复核"全过程工具化——产物扫描→原文核实→断言审计
> 位置: ~/dsh-collab/scripts/meeting-verify.py

## 十项达标矩阵

| # | R006 项 | 达标 | 实现 |
|---|---------|------|------|
| ① | CLI 形态 | ✅ | argparse 规范入口 + epilog 用法文档 |
| ② | TCC 检测 | ✅ | --selfcheck (原文文件/speakers 映射/产物目录可达) |
| ③ | CLD 自适应 | ✅ | 纯 stdlib 无第三方依赖 |
| ④ | dsh 版本自适应 | ✅ | 不依赖 dsh API, 数据路径独立 |
| ⑤ | 文档化 | ✅ | 本文档 + docstring 三大能力说明 |
| ⑥ | 版本管理 | ✅ | --tool-version v1.0.0 |
| ⑦ | 统一日志 | ✅ | ~/dsh-collab/logs/meeting-verify.log (audit 落盘审计) |
| ⑧ | 自动落链 | ✅ | asset-map 登记(会议知识工具族) |
| ⑨ | CLI 治理 | ✅ | --help 完整 + --json 结构化 + 子命令语义清晰 |
| ⑩ | Lean4 约束门 | ✅ | --lean4-check PASS (只读工具, 写路径仅 --out + 日志) |

## 三大能力

### ① 产物扫描 --scan
在会议产物(docs/ 等 md)定位关键词/数字/断言, 输出 文件×命中行×上下文 分类清单。
```bash
python3 meeting-verify.py --scan 淘闪,美团,GMV --scope docs
python3 meeting-verify.py --scan 中恒天雅 --scope "docs,data/blueprint" --json
```

### ② 原文核实 --verify
回会议转写原文(split 分章 72 文件)核实, 说话人经 identity-graph speakers 自动反查实名。
```bash
python3 meeting-verify.py --verify 双平台 --meeting 0908   # 0908=三场合
python3 meeting-verify.py --verify 返佣,12点 --meeting 0905
```

### ③ 断言审计 --audit
把"产物断言"与"原文证据"并列成报告, 供人/模型判读口径偏差(最常用)。
```bash
python3 meeting-verify.py --audit "成都鲜花 GMV 8000万/月" --kws "8000万,双平台,2000万" \
  --meeting 0908 --out /tmp/audit.md
```

## 会议元信息
| id | prefix | split 目录 | 内容 |
|----|--------|-----------|------|
| 0905 | obcnuhtix | split | 合作项目相关事宜讨论(21章) |
| 0908a | obcnwhp3 | split-obcnwhp3 | 垂类资本架构(25章) |
| 0908b | obcnwjk9 | split-obcnwjk9 | 淘闪城市站(11章) |
| 0908c | obcnwk6q | split-obcnwk6q | 自营供应链(15章) |

## 数据源
- 原文: ~/.dsh/meeting-notes/full/split*/ (分章 txt)
- 说话人映射: ~/dsh-collab/data/meeting-identity-graph.json (persons.speakers)
- 产物: ~/dsh-collab/docs/ + data/blueprint/

---
*meeting-verify R006 · 明鉴 · 2026-09-09*
