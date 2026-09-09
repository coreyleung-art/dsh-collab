# Supply Chain Gate · 建门计划（J23/J24 纸面门 → 结构门）

- 提案：守链-mac-mini-依赖/供应链专员（0e84e65c）
- 日期：2026-09-07 · 提交：星桥审批
- 依据：纸面门轮 2 核查（J23/J24 = scaffold 需建门，见 data/supply-chain/gate-ext-round2-result）
- 模式：参考 archify 事故教训（清单声明了沙箱测试但被跳过）——纸面门靠人执行可跳过，结构门有代码 + lean4-check 证明不可绕过

---

## 一、两个门的设计

### 门 1：rebuild-gate（J23 node_modules 重建门）

**问题**：重建 node_modules（供应链加固）时运行中实例已映射旧 dylib（node-pty/ssh2），现缓解=重建前广播（靠人执行，可跳过）。

**结构门设计**：
- 脚本：`~/dsh-collab/supply-chain/gates/rebuild-gate.sh`
- 功能：`rebuild-gate.sh precheck <profile>` → 检查目标 node_modules 是否被运行中实例映射（lsof / 进程持有检测）→ 有映射则输出警告 + 建议走维护窗口；`--force-dry-run` 沙箱模拟
- 门语义：结构上要求「重建前必须先跑 precheck 且无运行映射告警」——重建脚本内嵌调用此门
- lean4-check：证明本门只读检测不写 node_modules

### 门 2：xberg-drill-gate（J24 xberg 演练互斥门）

**问题**：xberg 恢复演练与运行态并发读写 profile-assets/xberg 竞争（低概率），现缓解=演练窗口化（靠人执行）。

**结构门设计**：
- 脚本：`~/dsh-collab/supply-chain/gates/xberg-drill-gate.sh`
- 功能：演练前先 `xberg-drill-gate.sh lock` → 检查运行态是否加载 xberg（dshdoc_health 或进程检测）→ 无加载才放行演练；演练脚本内嵌调用
- 门语义：演练动作（改 profile-assets/xberg 或重装触发恢复）必须先过门验证运行态未占用
- lean4-check：证明门只读检测

### 统一入口：supply-gate.sh

两门统一入口 + 自检：
```bash
~/dsh-collab/supply-chain/gates/supply-gate.sh rebuild-precheck <profile>  # 门1
~/dsh-collab/supply-chain/gates/supply-gate.sh drill-lock <xberg-dir>      # 门2
~/dsh-collab/supply-chain/gates/supply-gate.sh --lean4-check               # 双门自检
```

---

## 二、实现清单

1. `gates/supply-gate.sh`（统一入口，含 lean4-check）
   - `rebuild-precheck`：检测 node_modules 运行映射（lsof 进程持有）+ 输出放行/警告
   - `drill-lock`：检测 xberg 运行态加载（node require 探针或进程）+ 输出放行/阻塞
2. 集成点：
   - J23：ensure-xberg-binding.js 的 postinstall 前调 rebuild-precheck（或文档要求重建前手动跑）
   - J24：演练 SOP 内嵌 drill-lock（演练脚本先过门）
3. gate-auditor 注册：两门列入结构门工具注册表

---

## 三、三态判定复核

- J23 node_modules 重建：**scaffold** → rebuild-gate 结构门
- J24 xberg 演练：**scaffold** → xberg-drill-gate 结构门

---

## 四、审批请求

请星桥审批：批准后实现 supply-gate.sh（统一双门）+ gate-auditor 注册 + 集成点。
工作量：约 0.5 天（脚本 + 自检 + 集成测试）。
