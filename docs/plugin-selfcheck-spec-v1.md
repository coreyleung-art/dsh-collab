# 插件自查门规范 v1.0（R014）

> 2026-08-29 星桥-mac-mini-协调者 · 用户指示：沙箱环境应工具化插件化更稳固，本身该有自查的门基础设施，避免反复缺模块
> 定位：插件依赖完整性自查基础设施——缺模块在加载前暴露，不等到崩溃或被外部检查发现

## 一、为什么（历史教训）

| 事故 | 缺什么 | 如何暴露 |
|------|--------|---------|
| central-inbox 缺 type:module | package.json type | CLD 启动崩溃 |
| central-inbox 缺 ESM 导入 | join/homedir/fs | apply 阶段 ReferenceError |
| central-inbox startAdaptGuard 未导入 | 函数导入 | apply 阶段崩溃（MBP 修复）|
| openchronicle require('fs') 死代码 | fs 导入 | 运行时 ReferenceError |
| NODE_ID 探测 HOSTNAME undefined | 环境变量 | 监听错通道 |

**规律**：缺模块反复出现——因为没有「插件自身检查依赖」的门基础设施。外部 restart-guard 是事后校验，插件自查门是事前主动暴露。

## 二、自查门（selfcheck.js）

每个 dsh 插件必须内置 `lib/selfcheck.js`，apply() 最前调用：

```js
import { runSelfCheck } from './selfcheck.js';

export function apply(ctx) {
  runSelfCheck('my-plugin', {
    requiredPeers: ['@deepseek-ai/cordis', '@deepseek-ai/dsh-tools'], // 必须可解析的 peer 依赖
    requiredSymbols: ['join', 'homedir'],  // 顶层必须导入的符号
  });
  // ... 正常逻辑
}
```

### 检查项
1. **peerDependencies 可解析性**：`require.resolve(peer)` 探测（符号链接断裂/缺失 → missing）
2. **关键符号顶层导入**：当前文件 `import { sym }` 扫描（裸调用 → ReferenceError 风险）
3. **type:module 匹配**：ESM 语法但 package.json 缺 type:module → SyntaxError 风险

### 输出
- 落盘 `~/.dsh/plugin-selfcheck/<plugin>.json`（结构化结果）
- 写 `~/.dsh/plugin-selfcheck/selfcheck.log`（统一日志）
- 失败 → 黑板告警 `data/ops/plugin-selfcheck/<plugin>-<ts>`（协调者可感知）
- 返回 `{ ok, missing[], warnings[] }` 供插件决定是否继续

## 三、双层防线（自查门 + 外部强制）

| 层 | 工具 | 时机 | 能力 |
|----|------|------|------|
| 内层 | selfcheck.js（插件内）| apply 最前（每次启动）| 主动暴露缺模块，黑板告警 |
| 外层 | restart-guard（外部）| 重启前（强制门）| 静态 + 模块/apply 加载实测 |

**互补**：自查门 = 运行时主动，restart-guard = 重启前强制。两者都查依赖完整性，但自查门在「缺了也不崩」时仍标记告警（如 NODE_ID 配置错）。

## 四、已接入

| 插件 | 版本 | 自查项 |
|------|------|--------|
| central-inbox | v0.1.10 | peers: cordis/dsh-tools, symbols: join/homedir |
| agent-way | v1.3.3 | peers: cordis/dsh-tools, symbols: join/homedir |
| openchronicle | v0.1.6 | peers: dsh-tools, symbols: join/homedir |

## 五、验证标准（沙箱先行）

1. 正常：三插件自查 ✅（boot 冒烟 15s 存活）
2. 缺依赖：临时移除符号链接 → `missing: [peer:cordis]` 抓出 ✅
3. restart-guard 复核：0 FAIL

## 六、规则账本

- **R014「插件自查门（依赖完整性）」enforced**（账本 v1.7.0）
- 新增/修改插件必须带 selfcheck.js（R006 插件化标准补充）
- 与 R011（restart-guard 外部强制）+ R012（完整体传输）配套
