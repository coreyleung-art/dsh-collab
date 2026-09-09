# repo-pipeline 交付物说明（dsh-collab 索引条目）

> 来源会话: session-dcac2308 · 2026-08-16 · 按协作约定 v1 落盘

## 是什么
GitHub + Gitee 双仓接入与 CI/CD 流水线一键搭建工具：
- **DSH 插件** `~/dsh-plugin-repo-pipeline`（已注册 web profile bundles，行 id `repo-pipeline`；重启后 `repo_pipeline_setup / repo_pipeline_status / repo_pipeline_sync` 三工具可用）
- **独立 CLI** `~/dsh-plugin-repo-pipeline/scripts/repo-pipeline.sh`（零额外依赖，git/curl/gh 即可）

## 能力
| 工具/子命令 | 功能 |
|---|---|
| repo_pipeline_setup / setup | 建仓（GitHub+Gitee）→ 通道探测（SSH 回退）→ remote 规划 → 按工具链生成 CI/Gitee 同步/Release/Deploy 工作流 → 双端推送 → 写 GITEE_TOKEN Secret |
| repo_pipeline_status / status | 双仓同步状态 + Actions 最近运行 |
| repo_pipeline_sync / sync | 手动推 Gitee + 触发同步工作流 |
| doctor | 环境检查（gh/git/curl/凭据/通道） |

## 关键实现（踩坑沉淀）
1. **GitHub git-over-HTTPS 假阳性**：TCP 端口通 ≠ git 通道通（SNI/路由过滤）。探测用 `git ls-remote`（connectTimeout+lowSpeed）而非 TCP。
2. **insteadOf 全局重写**：`url."git@github.com:".insteadOf` 会让所有 https URL 变 SSH；工具识别该配置并强制 SSH 模式。
3. **Deploy Key 全局唯一**：一把密钥只能绑一个仓库 → per-repo 独立密钥 `~/.ssh/repo-pipeline_<owner>_<repo>`，push 用 `GIT_SSH_COMMAND`。
4. **Token 不落盘**：Gitee 推送用内联 URL token（当次命令），remote URL 保持干净；凭据存 `~/.dsh/repo-pipeline.json`（0600）。

## 使用
```bash
~/dsh-plugin-repo-pipeline/scripts/repo-pipeline.sh setup ~/my-repo [--private] [--no-push]
~/dsh-plugin-repo-pipeline/scripts/repo-pipeline.sh status ~/my-repo
```
或 DSH 会话内直接说「把 X 接入 GitHub 和 Gitee 并搭流水线」。

## 源码
- GitHub: https://github.com/coreyleung-art/dsh-plugin-repo-pipeline
- Gitee:  https://gitee.com/coreyleung/dsh-plugin-repo-pipeline（自动同步镜像）
- 本地: ~/dsh-plugin-repo-pipeline（含 README.zh.md 完整文档）
