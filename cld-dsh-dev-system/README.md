# CLD / DSH 开发系统

> 建立：2026-09-04 · 沉淀自 09-02~09-04 大型事故处置（OOM×6、pnpm 破坏、品牌套壳、界面修复）
> 定位：一套「规则 + 工作流 + 工具 + 风险清单」的完整开发与运维体系，杜绝同类事故复发，让成功经验可复用

---

## 体系结构

```
~/dsh-collab/cld-dsh-dev-system/
├── README.md               ← 本文件（总纲）
├── docs/
│   ├── 经验沉淀-20260904.md     完整过程复盘（OOM→pnpm→品牌→界面）
│   └── 架构基线.md               CLD/DSH 架构速查（现状+目标）
├── rules/
│   └── (见 ../guard/rules/ 治理规范，本系统规则全集在 risks/ 与 docs/ 交叉引用)
├── workflows/
│   ├── 标准化工作流.md           成功做法 → 可复用流程
│   └── (脚本化工具见 ../guard/tools/)
├── risks/
│   └── 风险行为清单.md           错误操作 → 红灯行为 + 正确替代
└── tools/
    ├── guard                    五道闸 CLI（备份/门禁/校对/沙箱/审查）
    ├── guard-check-deps         依赖一致性检查（profile vs runtime）
    └── (更多见「可插件化清单」)
```

## 三大支柱

### 1. 规则层（防错）
- **五道闸**：备份 → 版本校对 → 不可写门禁 → 沙箱模拟 → 物理审查（见 guard/rules/）
- **不可写清单**：Electron 二进制 / dsh-tools lib / .pnpm / 事故停用项 = 红线
- **风险行为清单**：14 项红灯行为 + 正确替代（见 risks/）

### 2. 工作流层（做对）
- **标准化操作流**：任何底层改动走「备份→沙箱→落真→审查→报告」
- **成功案例模板**：品牌插件套壳、修复报告 SOP、依赖回滚模式

### 3. 工具层（自动化）
- `guard` 五道闸 CLI（已实现）
- 待插件化：guard_* 工具面、依赖一致性检查器、品牌脚手架

---

## 快速引用

| 需要 | 看 |
|---|---|
| 要改 CLD/dsh 底层文件 | guard/rules/治理规范 + guard check-writable |
| 忘了哪些是危险操作 | risks/风险行为清单.md |
| 想加品牌/UI 定制 | workflows/品牌插件套壳流程.md |
| 想改依赖 | guard version-check + 依赖一致性检查 |
| 出事故了 | docs/经验沉淀 → 按标准化流程恢复 |

## 双机同步
- 本机：`~/dsh-collab/cld-dsh-dev-system/`
- Mac mini：同步至 `~/dsh-collab/cld-dsh-dev-system/`
- 变更走黑板通知星桥/守灯审阅

---

*系统 v1.0 · 2026-09-04 · 随经验持续迭代*
