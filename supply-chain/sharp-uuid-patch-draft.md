# sharp/uuid 漏洞修复补丁草稿（供 c1111ffe 审）

- 起草：session-0e84e65c（依赖/供应链专员）· 2026-08-17
- 状态：**草稿待审，未落地**——落地并入协调者宣布的下一个维护窗口（CLD-008 护栏）
- 目标文件：`~/.dsh/profiles/web/pnpm-workspace.yaml`
- 红线遵守：只改 pnpm.overrides 块，**零触碰** package.json 插件条目 / dsh.profile.bundles / dsh-pet 手改资产 / postinstall

---

## 一、修改内容

### 当前 pnpm-workspace.yaml 的 pnpm.overrides 块

```yaml
pnpm:
  overrides:
    '@xberg-io/xberg': 1.0.14
```

### 补丁后（新增 sharp + 可选 uuid）

```yaml
pnpm:
  overrides:
    '@xberg-io/xberg': 1.0.14
    sharp: 0.35.3
    # uuid 11.x 为可选项（见 §二 风险说明），如决定同窗口处理则取消注释：
    # uuid: 11.1.1
```

> ⚠️ 注意：这是**草稿演示**，实际落地时只需在两行 overrides 间插入。落地前先 `cp pnpm-workspace.yaml pnpm-workspace.yaml.bak-sharp-$(date +%Y%m%d-%H%M%S)` 备份。

---

## 二、风险与验证矩阵

| 项 | 评估 | 验证动作（落地时 c1111ffe 执行） |
|----|------|--------------------------------|
| sharp 0.34.5→0.35.3 | minor 升级，可能破坏性变更；主用方 dsh-knowledge embedding + zero-cli | ① `node -e "require('sharp')"` 冒烟 ② dsh-knowledge embedding 路径功能验证 ③ 回滚判断：出现破坏行为立即回报 0e84e65c 决策 |
| sharp 平台二进制 | @img/sharp-darwin-arm64 0.35.3 + libvips 1.3.2 齐全 ✅ | pnpm install 后确认平台包正确解析 |
| sharp engines | node≥20.9（本机 v25.9.0）✅ | — |
| uuid 9.0.1→11.1.1（可选） | major 升级（9→11）：gaxios 声明 ^9.0.1 会被 overrides 覆盖；uuid 11 保留 v4 API 但属 major 变更 | 仅影响 zero-cli optional Google auth 路径；验证 `require('uuid')` + zero-cli 冒烟。**建议保守：先只升 sharp，uuid 观察 zero-cli 上游（其 gaxios 7.x 已移除 uuid 依赖，zero-cli 升级后自然消除）** |

### 关键事实（升级路径依据）

1. **sharp 升级上游无效**：zero-cli 最新 0.12.11 声明 sharp ^0.34.2、transformers 最新 4.2.0 声明 ^0.34.5 → 仅 overrides 可达 0.35.3
2. **uuid 更优路径**：gaxios 7.3.1 **已移除 uuid 依赖**（google-auth-library 11.0.2 用 gaxios ^7.1.4）→ 长期靠 zero-cli 上游升级自然修复，overrides uuid 11.1.1 仅为临时缓解
3. **allowBuilds**：sharp 已在 pnpm-workspace.yaml allowBuilds 列表（2026-08-16 已批），升级 0.35 不触发新构建审批

---

## 三、执行步骤（维护窗口内）

1. 红绿灯：`agent_light(file:~/.dsh/profiles/web)` → 绿灯则 `agent_lock(exclusive, heartbeat)`
2. 备份：pnpm-workspace.yaml.bak-sharp-*（+ 现有 lockfile 备份）
3. 编辑：pnpm.overrides 加 `sharp: 0.35.3`（uuid 按决策暂缓）
4. `pnpm install --no-frozen-lockfile`（CI 默认 frozen，需显式关闭）
4b. **`pnpm list sharp` 确认解析版本 = 0.35.3**（c1111ffe 补充：防 overrides 未生效的静默）
5. 验证：frozen-lockfile 复验 + require('sharp') 冒烟 + dsh-knowledge embedding 验证 + **`dsh --profile web --dump-default-config`（bundle 树稳定确认，xberg/sharp 无依赖关系但同树回归，c1111ffe 补充）**
6. `pnpm audit --prod --registry=https://registry.npmjs.org` 确认 sharp high 消除
7. 回滚预案：还原备份文件 + lockfile 即可
8. 解锁 + 迭代报告 + 通知 QA ffb7c3ab 验收

> 补充项 4b/5 已并入 c1111ffe 验证清单（2026-08-17 审阅通过后定稿）。

---

## 四、审阅结论（c1111ffe 2026-08-17）

- [x] sharp 0.35.3 overrides 写法认可（顶层 key 覆盖所有解析，零触碰红线明确）
- [x] uuid 暂缓同意（gaxios 7.3.1 已移除 uuid，zero-cli 上游升级自然修复；overrides 9→11 major 不划算）——跟踪 zero-cli 即可
- [x] 分工确认（本角色出补丁 → c1111ffe 验证冒烟/embedding/回滚判断 → QA ffb7c3ab 验收）
- 状态：**已定稿，待维护窗口落地**（CLD-014）
