# repo-pipeline vs dsh-tools version 工具对比评估

> 记录：2026-08-28 ｜ 中枢 fa1f9150 ｜ 待用户拍板合并方向
> 背景：dsh-tools v1.5.0 新增 version 子命令（自动化版本管理）后，发现与既有 dsh-plugin-repo-pipeline（GitHub+Gitee 双仓 CI/CD）功能有重叠与互补，需评估是否合并。

---

## 一、两工具能力对比

| 维度 | dsh-plugin-repo-pipeline (v0.1.0) | dsh-tools version (v1.5.0) | 备注 |
|------|----------------------------------|---------------------------|------|
| **建仓**（GitHub/Gitee）| ✅ 完整（gh repo create + Gitee API）| ❌ 无 | repo-pipeline 独有 |
| **推送**（HTTPS 被墙处理）| ✅ 完整（SSH 探测 + insteadOf + deploy key）| ⚠️ 手动 GIT_SSH_COMMAND | repo-pipeline 更强 |
| **版本管理**（bump/CHANGELOG/commit/tag）| ❌ 无 | ✅ 完整（fix/feat/breaking 全类型）| version 独有 |
| **双仓同步**（GitHub→Gitee 镜像）| ✅ 完整（工作流 + GITEE_TOKEN Secret）| ❌ 无 | repo-pipeline 独有 |
| **CI/CD 工作流生成** | ✅ 完整（CI/Release/Deploy 模板）| ❌ 无 | repo-pipeline 独有 |
| **依赖** | node（dsh 插件）| Rust（dsh-tools 固化）| 形态不同 |

## 二、关键发现：repo-pipeline 已内置今天我手搓的解决方案

今天推 dsh-tools 到 GitHub 时，手动做了三件事（生成 deploy key → API 添加 → GIT_SSH_COMMAND 推送），**repo-pipeline 全部已内置且更完整**：

1. **SSH 通道配置**（lib/index.js L48-63）：自动写 `~/.ssh/config` 让 `github.com → ssh.github.com:443`（**443 端口 SSH 穿透被墙**）+ `url."git@github.com:".insteadOf` 全局重定向
2. **repo 专属 deploy key**（L70-88）：每仓一把 `~/.ssh/repo-pipeline_<owner>_<repo>` key，`gh repo deploy-key add --allow-write`——**正是我手动做的，但自动化了**
3. **推送**（L283）：`GIT_SSH_COMMAND="ssh -i <key>"`——与我手动的完全一致

**结论**：今天 version 工具「推送 GitHub」这块是重复造轮子，repo-pipeline 早已解决。

## 三、本机现状核对

| 项 | 状态 |
|----|------|
| `~/.ssh/config` ssh.github.com:443 | ✅ 已配置（IdentityFile=id_ed25519，但那是 openchronicle deploy key 权限不够）|
| `url."git@github.com:".insteadOf` | ❌ 未配（之前双重引号污染清理时可能一并清除）|
| repo-pipeline 的版本管理 | ❌ 无（只做建仓/推送/工作流）|

## 四、合并需求评估

**不是重复，是互补**：
- repo-pipeline 管「**建仓 + 推送 + 双仓 + CI/CD**」
- dsh-tools version 管「**bump + CHANGELOG + commit + tag**」

**真正的合并需求**（两处）：

### 需求 A：version 工具复用 repo-pipeline 的 SSH 推送能力
当前 version 只提示「推送提示」（手动），推送需手动 GIT_SSH_COMMAND。
- 增强方向：version 推送时自动配置 insteadOf + 检测/复用 repo-pipeline 的 deploy key 机制
- 收益：推送不再手动，一条命令完成「bump→CHANGELOG→commit→tag→push」

### 需求 B：repo-pipeline 吸收版本管理（可选）
repo-pipeline 已管建仓/推送，若再加 version 能力则「建仓→推→版本化→双仓同步」全链路一条龙。
- 但 repo-pipeline 是 node 插件、version 是 Rust 固化——**形态冲突**，吸收需重写或桥接

## 五、候选方案

| 方案 | 改动 | 优点 | 缺点 |
|------|------|------|------|
| **A1**（推荐）：version 增强推送 | version 自动配 insteadOf + 调 deploy key 推送 | 最小改动，解决推送痛点 | version 与 repo-pipeline 仍两处推送逻辑 |
| **A2**：version 调 repo-pipeline | version 推送时调用 repo-pipeline 的 setup | 复用成熟逻辑 | 跨语言调用复杂 |
| **B1**：repo-pipeline 加 version 子命令 | 插件内实现 bump/CHANGELOG/tag | 一条龙 | node 重写版本管理，与 Rust 版重复 |
| **C**：保持独立，补互相引用文档 | 只改 README/纪律 | 最轻 | 推送痛点仍在 |

## 六、建议

**短期（现在）**：方案 A1——version 工具补 SSH 推送（insteadOf 自动配置 + 复用 deploy key 机制），解决今天手动推送的问题。同时把今天手动做的 `~/.ssh/dsh-tools_deploy` 记录进 repo-pipeline 的 deploy key 管理认知。

**中期（用户拍板后）**：若倾向「工具统一」，方案 B1（repo-pipeline 加 version 能力，node 实现或调用 dsh-tools）实现「建仓→推送→版本化→双仓」全链路。

**长期**：版本管理纪律已接入（dsh-tools version 自动跟随迭代），推送增强后即形成「改代码 → dsh-tools version 自动版本化+推送」的完整闭环。

---
*关联：dsh-tools v1.5.0 / dsh-plugin-repo-pipeline v0.1.0 / 双向注入修复 2026-08-28 / 工具台账*
