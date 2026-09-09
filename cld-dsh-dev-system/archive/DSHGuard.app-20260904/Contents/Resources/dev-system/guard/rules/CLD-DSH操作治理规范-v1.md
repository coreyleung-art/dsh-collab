# CLD / DSH 操作治理规范 v1.0

> 建立：2026-09-04 · mbp-ops（远程运维）· 用户指示
> 目的：给 CLD/dsh 底层的一切改动加上「备份 → 校对 → 门禁 → 沙箱 → 审查」五道闸，杜绝本日发生的（pnpm 误装 / gov schema 连环崩 / 手动 link 错位）类事故复发

---

## 一、总则（五道闸）

**任何对 CLD/dsh 底层文件的写操作，必须依次通过：**

```
① 备份闸  操作前备份「最后两个可正常加载状态」的完整文件
② 校对闸  对照官方版本/上游 commit，确认目标版本正确
③ 门禁闸  检查目标路径是否在「不可写清单」——在则禁止
④ 沙箱闸  先在隔离副本/模拟环境验证，再落真
⑤ 审查闸  变更后物理审查（diff/语法/权限/加载验证），并留档
```

任何一道不过 → 停下、报告、不落真。

---

## 二、备份规则（闸①）

### 2.1 覆盖范围（须备份的目标）
| 类别 | 路径 | 说明 |
|---|---|---|
| CLD 壳 | `/Applications/CLD.app/Contents/Resources/app.asar` | 主壳 |
| profile 清单 | `~/.dsh/profiles/web/package.json` | bundles/deps |
| profile 补丁 | `~/.dsh/profiles/web/cordis.patch.yml` | 覆盖层 |
| 依赖锁 | `~/.dsh/profiles/web/pnpm-lock.yaml` | 版本锁 |
| workspace 配置 | `~/.dsh/profiles/web/pnpm-workspace.yaml` | overrides |
| 用户插件 | `~/dsh-plugin-*/*` | link 型插件源码 |
| runtime 包 | `/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/*` | 官方包（只读为主） |
| 状态 | `~/.dsh/settings.yaml`、`~/.cld/config.json` | 运行配置 |

### 2.2 备份规范（核心）
1. **数量**：保留**最后两个可正常加载状态**的完整备份（`*.bak-good-1` / `*.bak-good-2`），循环滚动
2. **时机**：任何写操作**之前**执行（不是之后）
3. **命名**：`<文件>.bak-good-<N>-<YYYYMMDD-HHMMSS>`
4. **验证**：备份后立即校验（大小>0、可解析——JSON/YAML/JS 分别验）
5. **可回滚**：任何失败，用最近 good 备份还原 + 重启验证

### 2.3 工具
`guard backup <path>`（见 tools/）——自动完成 2.1-2.2。

---

## 三、不可写位置清单（闸③）

### 3.1 绝对不可写（红线）
| 路径 | 理由 |
|---|---|
| `/Applications/CLD.app/Contents/Frameworks/Electron Framework.framework/*` | Electron 二进制，改了壳必崩 |
| `/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh-tools/lib/*` | schema DSL 核心，改版本即 API 漂移（今日 gov 教训） |
| `~/.dsh/profiles/web/node_modules/.pnpm/*` | pnpm 内部结构，手改即锁不一致 |
| `~/Library/LaunchAgents/com.user.auto-index.plist` | 已按事故停用，恢复需审批 |

### 3.2 受限可写（须过五道闸）
| 路径 | 约束 |
|---|---|
| `app.asar` | 需备份 + 重签评估（有先例） |
| `profile package.json` | 备份 + 校对 + pnpm 正规路径 |
| `node_modules/*`（link 插件） | 只经 link 源改，不经 node_modules 手改 |
| runtime `@deepseek-ai/*` 包 | 原则上只读；确需改→视为升级，走完整流程 |

### 3.3 门禁工具
`guard check-writable <path>` → 命中清单即拒绝（exit 非 0 + 原因）。

---

## 四、官方版本校对（闸②）

### 4.1 校对内容
- CLD.app 版本 vs 上游（app 0.1.1、dsh-runtime、dsh 主包版本）
- 各 `@deepseek-ai/*` 包版本 vs npm registry / 上游 commit
- profile 内 link 插件 vs 源仓库 HEAD

### 4.2 规则
- **改任何依赖前**：`guard version-check <pkg>` 确认目标版本与 runtime 兼容
- **peer 解析**：确认改后 peer 能解析到 runtime 版本（gov 教训：profile 自装 dsh-tools rc.7 与 gov 不兼容）

### 4.3 工具
`guard version-check [--all | <pkg>]` → 输出当前版本 + 上游版本 + 兼容性判断。

---

## 五、写前沙箱模拟（闸④）

### 5.1 原则
**真环境不直接试**。任何 patch/安装/重命名，先在隔离副本验证：
- 文件级：复制到 `/tmp/guard-sandbox/`，在副本上打补丁 → 语法/解析检查通过才落真
- 依赖级：dump-config 冒烟（`dsh --profile web --dump-config` EXIT 0）通过才重启
- 配置级：cordis.patch.yml 改动 → dump-config 验证 disabled/insert 生效才重启

### 5.2 工具
`guard sandbox <patch-command>` → 在沙箱副本执行 + 校验，输出通过/失败。

---

## 六、物理审查（闸⑤）

### 6.1 变更后必查
| 检查 | 方法 |
|---|---|
| 语法 | `node --check` / YAML/JSON 解析 |
| 权限 | 文件 644/755 合理，非 600 意外 |
| 链接 | `ls -la` 确认 symlink 指向正确 |
| 加载 | dump-config EXIT 0 |
| 运行 | 重启后 doctor 会话数正常、web HTTP 200 |
| 差异 | 与备份 diff，确认只改预期内容 |

### 6.2 工具
`guard review <path>` → 输出上述检查结果。

---

## 七、操作留痕（贯穿）

每次对底层操作：
1. `guard backup` 记录操作前状态
2. 操作过程命令存档到 `~/dsh-collab/guard/backups/CHANGELOG.md`
3. 完成后按 SOP 发修复报告（send-repair-report.py）

---

## 八、豁免与升级

- 紧急修复（服务宕机）：可先备份+操作，后补沙箱/审查记录（24h 内）
- 本规范由守灯/星桥监督，违规操作记录在案
- 规范版本迭代走 `guard/rules/` 文档修订

---

*治理规范 v1.0 · 2026-09-04 · 配套工具见 guard/tools/ · 登记星桥待审*
