# dsh-plugin-writing-guards

> 写作过程守卫：非原子写扫描 · 数字口径申报 · 更正账生成 · 照抄旧读数疑似检测 · 既有 lint 清单

R006 十项骨架 · 由 **PSTD PSTD/1.0.4** 按模式 `P3_cli_tool` 生成。

## 为什么需要（事故/证据）

R006 事故表首行：插件缺 `type: module` 导致 CLD 启动崩溃；第一版参考实现「九项全绿却根本挂不上」——
`defineTool` 的嵌套 object 缺 `additionalProperties` → `UNSUPPORTED_SCHEMA` → `apply()` 阶段崩。
本骨架把这两条写进结构：`type: module` 必有，输出 schema 用 `{ type: "json" }` 免嵌套陷阱。

## 用法与退出码

```
node cli.js --help            # 自解释用法
node cli.js --selfcheck       # 能力清单 / 不该发生路径 / 依赖完整性 + 真挂载冒烟
node cli.js --lean4-check     # 约束门六项 A–F 自证
node cli.js --tool-version    # 版本（唯一来源 package.json）
node cli.js --dry-run --json  # 零变更演练 + 机器可读输出
```

退出码：`0` 成功 · `1` 失败/门失效 · `2` 用法或 IO 错误。

## R006 达标矩阵（自查口径）

| 项 | 判据 | 本骨架状态 |
|---|---|---|
| ① dsh 插件形态 | package.json + cordis.patch.yml + apply + 真挂载冒烟 | 已生成，冒烟在 --selfcheck |
| ② TCC 自检 | 三段输出 | lib/selfcheck.js |
| ③ CLD 自适应 | 只依赖 node 内置 + peer | 已满足 |
| ④ dsh 版本自适应 | peerDependencies 全声明 | 已满足 |
| ⑤ 文档化 | 本文件 + r006.documented | 已满足（继续补你的用法） |
| ⑥ 版本单一来源 | package.json 唯一 | 已满足（cli 从 package.json 读） |
| ⑦ 统一日志 | ~/dsh-collab/logs/dsh-plugin-writing-guards.log | **待接入** |
| ⑧ 自动落链 | data/registry/dsh-plugin-writing-guards | **待人工登记** |
| ⑨ CLI 治理 | 未知旗标 exit 2 / dry-run / json | 已满足 |
| ⑩ 约束门 | 冻结枚举 + 负例矩阵 + 命令白名单 | lib/gate.js + --lean4-check |

## 坑（都踩过）

1. **门太宽**：把合法键也当违规 → 先精确白名单命中，再对非白名单输入判禁用词。
2. **扫描器误伤自己**：扫源码前先剥注释/字符串/正则字面量，否则自己的检测正则会被当靶子。
3. **空洞通过**：剥离字面量后读不到实参 → 调用点枚举为 0 → 「0 ⊆ 允许」假通过。
4. **假失败**：依赖解析不到就说插件挂不上 —— 应先分辨「环境问题」与「包问题」。
5. **两处版本**：`const VERSION` 与 package.json 各写一份必然漂移，只留 package.json。

## 复现命令

```
cd ~/dsh-plugin-writing-guards
node cli.js --selfcheck && node cli.js --lean4-check && node cli.js --tool-version
```

## 下一步

1. 用审查员复核：`plugin_review(target="dsh-plugin-writing-guards", deep=true)`
2. 接入 ⑦ 日志与 ⑧ 落链（本骨架刻意留空，因为那是业务决定）
