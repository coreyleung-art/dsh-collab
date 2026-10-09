# dsh-plugin-reflect · 每日反思流水线编排器

## ① 为什么需要（事故/证据）

**事故**：2026-09-10 花联网项目。当日发生两起信息处理事故（凭据 4 次复制 / 处置前后证据混记），
而**复盘只能靠一个人（明鉴）在会话结束时想一遍**。三个后果：
1. **只有一个人的视角** —— 别人踩过的坑我不知道（当天证实：老登踩了 Φ12/Φ13 各 2 次，守灯塔各 1 次）
2. **靠记性** —— 忙的时候就不做了
3. **产出不流动** —— 想出来的教训没有回到别人的工作里

**证据**：当日 7 个相关方对两条哲学提案给出意见，其中 **6 条域内实证是我一个人想不出来的**
（CLD-020 OOM 归因、runtime 升级证据失效、Gitee token 引用即复制、备份被 deploy 上线…）。

## ② 用法（含退出码）

```bash
# 看今天跑到哪
node cli.js status [--date YYYY-MM-DD] [--json]

# 跑流水线（默认跑到 synthesize；★ enroll 永不自动跑）
node cli.js run [--upto collect|dispatch|harvest|synthesize]
                [--only collect,dispatch] [--date YYYY-MM-DD] [--dry-run] [--json]

# 自检与证明
node cli.js --selfcheck      # ② 能力边界三段
node cli.js --lean4-check    # ⑩ 约束门六项
node cli.js --tool-version   # ⑥ 从 package.json 读
node cli.js --help
```

**退出码**：`0` 成功 · `1` 失败 / 门失效 · `2` 用法或 IO 错误

**★ 注意**：`run` **永不自动跑 enroll**（入册必须人裁，`phi-user-sovereignty`）。
入册请人工：`node ../dsh-plugin-reflect-enroll/cli.js --ruling <file>`

## ③ 十项达标矩阵

| # | 项 | 达标方式 | 自检 |
|---|---|---|---|
| ① | dsh 插件形态 | `package.json`(type:module + dsh.bundle.patch) + `cordis.patch.yml`(`- insert`) + `lib/index.js` 导出 `apply(ctx,config)`，`inject=['tools']`，注册 `reflect_run`/`reflect_status` | `node -e "import('./lib/index.js')"` |
| ② | TCC 检测 | `--selfcheck` 输出三段：能力清单 / **不该发生路径清单** / 依赖完整性 | `node cli.js --selfcheck` → exit 0 |
| ③ | CLD 自适应 | 只用 node 内置（fs/path/os/crypto/child_process）；无宿主可独立跑 CLI | 断网可跑 |
| ④ | 版本自适应 | `peerDependencies` 正式声明；不 import 宿主内部路径 | `--selfcheck` 显示 peer |
| ⑤ | 文档化 | 本文件（五要素：为什么/用法+退出码/十项矩阵/坑/复现） | 本文 |
| ⑥ | 版本管理 | 版本**只写 package.json**；`--tool-version` 从包读；`CHANGELOG.md` | `--tool-version` |
| ⑦ | 统一日志 | `~/dsh-collab/logs/dsh-plugin-reflect.log`；记 时间/环节/命令/退出/结果；**失败也留痕** | 跑一次看日志行数 |
| ⑧ | 自动落链 | 黑板 `data/registry/dsh-plugin-reflect` 登记卡；产物写 `data/reflect/` | `GET /data/registry/...` 200 |
| ⑨ | CLI 治理 | 严格参数解析（未知旗标 exit 2）；退出码 0/1/2；`--dry-run`；`--json`；`--help` | 见② |
| ⑩ | 约束前置 | `lib/gate.js`：`STAGES`/`STAGE_IMPL`/`HUMAN_GATED` 三个冻结枚举 + 命令白名单；`--lean4-check` 六项全绿 | `node cli.js --lean4-check` |

## ④ 坑

1. **`spawnSync` 是受控的**：`run.js` 用它在子进程跑环节插件。命令**只能从冻结的 `STAGE_IMPL` 取**，
   不接受外部传入的命令字符串 —— 否则就是任意命令执行。**改这个文件时务必保持这个约束。**
2. **`--dry-run` 的保证在 CLI 层**：`run.js` 在 `dryRun` 分支直接 return，不 spawn、不写盘。
   **若在 `run.js` 里加了写操作，必须同时加 dryRun 判断。**
3. **子插件未就位时跳过而非崩**：五个环节插件是独立交付的。**缺插件 → 该环节标「插件未就位（跳过）」**，
   其余环节照跑。这让编排器可以先于插件交付。
4. **`status` 的判据是"产物存在性"**，不是"跑过没有" —— 产物被删则显示未完成。这是有意的（以事实为准）。
5. **断点续跑不做幂等保证**：若某环节产物存在但内容不完整，`run` 会跳过它。**重建该环节要先删其产物。**

## ⑤ 复现命令

```bash
cd ~/dsh-collab/devices/dsh-plugin-reflect
node cli.js --tool-version          # → 1.0.0
node cli.js --selfcheck             # → 三段 + exit 0
node cli.js --lean4-check           # → 六项全绿 + exit 0
node cli.js status                  # → 五环节进度
node cli.js run --dry-run           # → 计划（不执行）
node cli.js --bogus; echo $?        # → 2
```

---

*配套设计文档：`~/dsh-collab/docs/daily-reflection-pipeline-design-v1.md`*
