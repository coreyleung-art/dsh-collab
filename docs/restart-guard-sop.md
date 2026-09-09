# 重启沙箱强制门 · SOP v3.0（R011 v3 · restart-gate 三级）

> 建立：2026-08-29 · 星桥-mac-mini-协调者 · 用户指示「重启前先跑沙箱模拟确认不崩溃，插件化工具化自动化，纳入规则本作为强制门」
> 触发：**任何** CLD/DSH 重启、插件更新、宿主升级之前（强制门，R011 enforced）
> 工具：`dsh-tools restart-gate`（v1.12.0 三级强制门 = 隔离小样本 + 静态检查 + 动态压测，Rust + Python）

## 一、命令

```bash
# 单插件审查
dsh-tools restart-guard ~/dsh-plugin-central-inbox

# 多插件审查（CLD 重启前全量）
dsh-tools restart-guard ~/dsh-plugin-central-inbox ~/dsh-plugin-agent-bus ~/dsh-plugin-openchronicle

# 带 profile 检查 bundles 顺序
dsh-tools restart-guard <插件目录>... --profile ~/.dsh/profiles/web/package.json

# JSON 输出（自动化接入）
dsh-tools restart-guard <插件目录> --json
```

## 二、检测项（11 项全覆盖）

| # | 检测 | 说明 |
|---|------|------|
| ① | 基础结构 | lib/ 目录 + package.json 存在 |
| ② | package.json 解析 | name/peerDeps/deps 合法性 |
| ③ | import/require 扫描 | 外部依赖 + API 漂移 |
| ④ | link/file 语法 | 跨设备安装约定 |
| ⑤ | bundle.patch 存在 | cordis.patch.yml 配置生效 |
| ⑥ | bundles 顺序 | 依赖插件先于依赖它的插件 |
| ⑦ | JS 语法 | node --check（自动探测 node） |
| ⑧ | **type:module 匹配** | ESM export 必须配 type:module（缺则 CJS 解析 SyntaxError → 加载即崩）|
| ⑨ | **ESM 导入完整性** | join/homedir/fs 必须显式 import（防 ReferenceError）|
| ⑩ | **符号链接** | node_modules/@deepseek-ai/* peer 依赖解析 |
| ⑪ | **模块加载实测** | node import() 模拟 cordis 加载（LOAD_OK 验证）|

⑧-⑪ 为 restart-guard 重启专属（R011），来自 2026-08-29 central-inbox 事故教训。

## 三、判定标准

```
exit 0 = 全部 OK（可重启）
exit 1 = 存在 FAIL（禁止重启 → 修复 → 重跑 → exit 0 才重启）
```

## 四、自动化集成（CLD 重启前置钩子）

```bash
# 重启前一键（全量插件 + profile）
dsh-tools restart-guard \
  ~/dsh-plugin-central-inbox ~/dsh-plugin-agent-bus ~/dsh-plugin-openchronicle \
  --profile ~/.dsh/profiles/web/package.json
[ $? -eq 0 ] && echo "✅ 可重启" || echo "❌ 禁止重启"
```

- launchd 定时自检（可选）：`com.dsh.restart-guard.watch` 每日跑一次，FAIL 即黑板告警
- CI 集成：插件发布流水线 deploy 前必跑 restart-guard（与 deploy-check 并列）

## 五、实战验证（2026-08-29）

| 场景 | 结果 |
|------|------|
| 修复后 central-inbox v0.1.6 | 0 FAIL / 0 WARN / 4 OK → exit 0 ✅ |
| 未修复版（缺 type:module）| 5 FAIL（type:module/join/homedir/require/加载实测）→ exit 1 ❌ 拦截 |

**验证了强制门的价值**：不修就重启，central-inbox 加载即崩 → CLD 插件组失败可能整体崩溃打不开——restart-guard 在重启前拦截。

## 六、规则账本关联

- R011「重启沙箱强制门（restart-guard）」enforced，账本 v1.4.0
- 与 R005（CCEP 沙箱先行）配套：R005 定义纪律，R011 提供工具强制
- 与 R006（插件化 9 项）配套：restart-guard 本身按 9 项实施（dsh-tools 工具形态/文档/版本/日志/落链/CLI）

## 七、可扩展检查清单（R011 v2，2026-08-29）

**核心**：新问题出现 → 在 `checks/*.json` 加清单文件 → restart-guard 自动加载合并执行，**无需改代码**。

### 清单格式（checks/esm-cjs-hygiene.json 为例）

```json
{
  "id": "检查类目ID",
  "name": "类目名",
  "checks": [
    {
      "id": "检查项ID",
      "name": "检查名",
      "type": "file-content | package-json | path-exists",
      "target": "index.js | *.js（lib/ 内文件名）| node_modules/@deepseek-ai",
      "mode": "fail-if | warn-if | warn-if-missing",
      "pattern": "正则或子串（file-content）",
      "exclude_if": ["命中任一跳过（如 createRequire, window.）"],
      "require": {"file": "package.json", "key": "type", "equals": "module"},  // 未满足才 FAIL
      "message": "报错信息"
    }
  ]
}
```

### 新增检查流程（新问题 → 专项检查）

1. 记录踩坑档案（docs/pitfalls/）
2. 在 `checks/` 新建或追加清单文件（含检测规则）
3. 跑 `dsh-tools restart-guard <插件目录> --checks-dir checks/` 验证能命中
4. 推 GitHub（checks/ 目录入库）

### 内置 vs 清单

| 来源 | 检测 | 何时用 |
|------|------|--------|
| 内置 11 项 | 结构/解析/语法/加载实测等通用项 | 每次重启必查 |
| 清单文件 | 专项（esm-cjs-hygiene 等，按类目扩展） | 内置之外按需加载 |

### 使用

```bash
# 默认加载 dsh-tools 旁 checks/
dsh-tools restart-guard <插件目录>...
# 指定清单目录
dsh-tools restart-guard <插件目录>... --checks-dir ~/dsh-collab/rust-tools/checks
```

## 九、统一强制门 restart-gate（R011 v3 三级）

**重启前唯一入口**：一键跑完整验证链（隔离小样本 → 静态 → 动态压测），任一 FAIL 禁止重启。

```bash
# 完整三级强制门（默认 3 轮压测）
dsh-tools restart-gate

# 指定压测强度
dsh-tools restart-gate --rounds 5 --hold 10

# 跳过某阶段
dsh-tools restart-gate --skip-sandbox   # 跳过隔离小样本
dsh-tools restart-gate --skip-stress    # 跳过动态压测
```

- 阶段 0: **隔离小样本验证**（cld-shell-sandbox-test：壳行为/模式对话框阻塞/launchd KeepAlive，不动生产 CLD/config/app.asar）
- 阶段 1: restart-guard 静态检查（type:module/ESM/符号链接/加载实测 + checks 清单）
- 阶段 2: restart-stress-test 动态压测（隔离端口 boot 冒烟，自查门+注入+无崩溃，100% 才过）
- exit 0 = 可重启；exit 1 = 禁止重启

## 十、压测工具（restart-stress-test.py）

独立深度压测（restart-gate 阶段 2 调用，也可单独跑）：
```bash
python3 scripts/restart-stress-test.py --rounds 10 --hold 15
```
- 隔离端口（默认 3090+），不碰生产 CLD
- 每轮验证：三插件自查门 ✅ / node=mac-mini 注入 ✅ / 无崩溃 ✅
- 统计：成功率 / 启动时间 / 内存趋势
- 2026-08-29 实战：15 轮全通过
