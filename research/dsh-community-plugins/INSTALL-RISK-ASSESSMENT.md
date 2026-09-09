# dsh 社区插件安装 · 专项风险评估（2026-09-06）

> 评估：数据调查员 4787d717 · 关联：R006 工具化标准 / J37 隔离验证 / R027 审批 / CLD-017 内存治理
> 对象：dsh-community-plugins 调研推荐的候选安装（SUMMARY-main-report.md）
> 方法：安装通道实测 + npm registry 交叉验证 + peerDeps 核对 + 历史事故复盘 + 供应链核查
> 结论前置：**批 1-2 可安全执行（低风险）**，需按本报告操作护栏执行；批 3 个别项需额外评估

---

## 一、操作层风险（安装动作本身）

### R1. dsh CLI 通道风险 【中 → 已缓解】
- **发现**：`dsh` CLI 不在系统 PATH；本机曾历史性出现「双 dsh 实例并发写会话 → 重复 seq 事故」（见 dsh-session-loss-root-cause.md）
- **缓解（已实测确认）**：正确调用 = `export PATH="/opt/homebrew/bin:/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/.bin:$PATH"` 后执行 `dsh` → 实测 `dsh --version` = **0.1.1-rc.2**（与 harness 同版本 ✅）
- **护栏**：安装全程**只用 CLD 内置 dsh CLI**，禁止 npx 另启实例（防双实例事故重演）

### R2. profiles/web/package.json 改动风险 【高 → 已缓解】
- **背景**：该文件 00:25 出过写坏事故（HR 台账记录）；现为 35 deps + 32 bundles
- **缓解**：已有 5+ 备份（.bak-20260904-shade 等）；安装前再备份一次
- **护栏**：`cp package.json package.json.bak-preext-<ts>` → 安装 → `dump-config` 校验 JSON 有效 → 验证 bundle 加载

### R3. npm registry 可达性 【低 · 已验证】
- 实测三个目标包均可 npm view 到（registry 通）
- ⚠️ **版本修正**：子代理报告的 `dsh-context@0.41.9` **不存在（404）**——实测 0.41.x 最高 = **0.41.3**（0.41.0~0.41.3），**应装 @0.41.3**

---

## 二、版本兼容风险（peerDeps 实测核对）

| 包 | 建议版本 | peerDeps 实测 | 兼容 rc.2 | 风险 |
|---|---|---|---|---|
| dsh-context | **@0.41.3**（勿 0.42+/0.43） | dsh-session `>=0.1.1-rc.2` | ✅ | 低（须钉 0.41.x，latest=0.43.0 会断链） |
| @liustack/modsearch | @5.10.1 | **无 peerDeps** | ✅ | 极低 |
| @changfenhuang/dsh-genui | @0.9.8 | dsh-* `>=0.1.1-rc.0 <0.2.0` | ✅ | 低 |
| dsh-univer-office | @0.2.14 | 官方明示支持 rc.2 | ✅ | 中（重依赖） |
| @graysilver/dsh-evolve-modes | @0.4.0 | `^0.1.1-rc.2` 精确 | ✅ | 中（上下文副作用） |
| @shengsheng/dsh-taskboard | — | **钉死 0.1.2-alpha.2** | ❌ | 高（版本墙，不装） |
| dsh-mimir | pin 0.16.0 | 0.18 需 ≥0.1.2-alpha.4 | ⚠️ | 中（pin 锁功能） |

---

## 三、第三方代码风险（J37 视角，逐候选）

| 候选 | 代码面 | 权限 | 风险 | 缓解 |
|---|---|---|---|---|
| **dsh-context** | 只读仪表 + 事件订阅 | client 侧为主 | **低** | 不写文件不改会话；主要风险=误装 0.42+ |
| **modsearch** | 替换 searchProvider + 网络请求 | 联网（搜索 API） | **低** | keyless 引擎无凭据；作者=已装 modlens 同源 |
| **genui 迁移** | 移除旧包+装新包 | 与现用能力 100% 等效 | **低** | 迁移即防未来重装失败 |
| dsh-univer-office | 重依赖（univerjs-pro+libsql+puppeteer） | 文件/浏览器 | **中** | puppeteer 可能需系统 Chrome；装前评估磁盘 |
| evolve-modes | 注入 system prompt + 隔离学习请求 | 全局规则注入 | **中** | 只开 Propose 不批准；克制规则量 |
| dshmarket | 插件安装执行器 | **高**（可装任意插件） | **中** | 官方市场，2300+ 已验证条目；装它本身安全，但它装的插件需逐个审 |
| subscriptions | 逆向端点 | 凭据导入 | **高** | **明确不装**（ToS 灰区+封号+10 issues） |

**共性缓解**：安装跑第三方代码=本机权限——本次候选均已审源码（package.json/cordis.patch.yml/结构）；正式启用前 J37 隔离副本验证 + 冒烟。

---

## 四、冲突与功能风险

| 冲突面 | 分析 | 判定 |
|---|---|---|
| modsearch vs 原生 web_search | modsearch 替换 searchProvider seam；原生 web_search 工具仍可用（走新 provider） | ✅ 兼容（增强非替代） |
| univer-office vs dsh-plugin-office | 不同层（交互式 vs 轻量生成），工具名不冲突 | ✅ 可并存 |
| genui 迁移 | 移除 @omdsh-dev → 装 @changfenhuang；0.8.6→0.9.8 有 streaming 增强 | ⚠️ 迁移瞬间需重启（几十秒 UI 中断） |
| dshmarket vs 自研 dsh-plugin-market | 功能重叠；官方更全 | ⚠️ 建议装官方后评估自研退役，勿同时抢 Settings 入口 |
| evolve-modes 规则注入 | 与 R006 文件规则并存需人工映射；永久占 system prompt | ⚠️ 与 CLD-017 相悖，只开 Propose |
| dsh-context vs 后续 compaction | context 是仪表，compaction 是执行——需**另配** compaction 插件才治 CLD-017 | 📌 立项时一并配 |

---

## 五、供应链风险（守链 0e84e65c 视角）

| 项 | 核查结果 |
|---|---|
| 包活跃度 | 三包近期活跃（dsh-context 09-05 / modsearch 09-03 / genui 09-05 更新）✅ |
| 维护者 | 单维护者（个人项目常态）；bowenliang123（context）/ liustack（modsearch，与 modlens 同人）/ changfenhuang（genui） |
| 体积 | context 434KB / modsearch 454KB / genui 6.1MB（正常） |
| 完整性 | npm registry 直查（非 github tarball），pnpm lockfile 校验 |
| 风险项 | genui 包名迁移 = 供应链改名（旧键失效），需确保 remove 旧 + add 新原子完成 |

---

## 六、操作护栏（最终执行清单）

```bash
# 0. 前置（必做）
export PATH="/opt/homebrew/bin:/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/.bin:$PATH"
dsh --version   # 确认 = 0.1.1-rc.2（单实例，勿 npx 另启）
cp ~/.dsh/profiles/web/package.json ~/.dsh/profiles/web/package.json.bak-preext-$(date +%Y%m%d-%H%M%S)

# 1. 批 1（装-优先）——逐包执行，每包后验证
dsh plugin --profile web add dsh-context@0.41.3    # ⚠️ 钉 0.41.3，勿 latest
dsh plugin --profile web add @liustack/modsearch@5.10.1

# 2. 批 2（genui 迁移）——原子完成
dsh plugin --profile web remove @omdsh-dev/dsh-genui
dsh plugin --profile web add @changfenhuang/dsh-genui@0.9.8

# 3. 验证（每步后）
node -e "JSON.parse(require('fs').readFileSync('$HOME/.dsh/profiles/web/package.json'))" && echo "JSON VALID"
dsh plugin list 2>/dev/null | grep -E "context|modsearch|genui"   # bundle 加载确认

# 4. 重启 dsh → 浏览器 Cmd+R
# 5. 冒烟：搜索返回带源 JSON / console [genui] client active / Settings 出现 Plugin Market
```

**禁止项**：
- ❌ 装 dsh-context@latest（0.43.0 需 0.1.2-rc.1，会断链）
- ❌ 装 dsh-plugin-subscriptions（逆向端点+ToS 灰区）
- ❌ 装 DSH-taskboard（0.1.2-alpha.2 版本墙，强装 peer 冲突）
- ❌ 用 npx 另起 dsh 实例装（防双实例会话事故）

---

## 七、风险总评

| 批次 | 风险等级 | 结论 |
|---|---|---|
| 批 1（context@0.41.3 + modsearch） | 🟢 低 | 可执行；版本钉死是唯一注意点 |
| 批 2（genui 迁移） | 🟢 低 | 必须做（防重装即坏）；迁移瞬间需重启 |
| 批 3a（dshmarket） | 🟡 中 | 可装（官方成熟）；但它装的插件需逐个审 |
| 批 3b（univer-office） | 🟡 中 | 需评估磁盘/启动开销；有报表需求再装 |
| 批 3c（evolve-modes） | 🟡 中 | 只开 Propose；克制批准规则量 |
| 不装组 | — | subscriptions（高合规风险）/ taskboard（版本墙）/ Mimir（条件性） |

**综合**：推荐候选的风险均可控，核心护栏 = ① 单实例 dsh CLI ② 版本钉死（context@0.41.3）③ 备份 package.json ④ 逐包验证冒烟 ⑤ 禁止项清单。

---
*风险评估 · 4787d717 · 2026-09-06 · 与 SUMMARY-main-report.md 配套 · J37/R006/R027 合规*
