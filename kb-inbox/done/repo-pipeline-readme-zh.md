# dsh-plugin-repo-pipeline

GitHub + Gitee 仓库接入与 CI/CD 流水线一键搭建：建仓、SSH 回退、remote 规划、
工作流模板生成、双端推送、Actions Secret —— 全部封装为模型可调工具。

DeepSeek Harness 插件，基于 Cordis 运行（tool 形态 + bundle 层挂载）。

## 工具

| 工具 | 作用 |
|---|---|
| `repo_pipeline_setup` | 一键搭建：git 初始化 → 网络探测（HTTPS 不通自动切 SSH）→ 创建/复用 GitHub + Gitee 仓库 → 规划 remote（origin/upstream/gitee）→ 按工具链生成 CI / Gitee 同步 / Release / Deploy 工作流 → 双端推送 → 写入 GITEE_TOKEN Secret |
| `repo_pipeline_status` | 查看双仓同步状态 + GitHub Actions 最近运行 |
| `repo_pipeline_sync` | 手动推送到 Gitee + 触发 Actions 同步工作流 |

setup 核心参数：`repo_path`（必填）、`repo_name`、`visibility`、`keep_history`（false 压缩为单次提交）、
`create_repos` / `push` / `set_secret`、`enable_ci` / `enable_gitee_sync` / `enable_release` / `enable_deploy`。

## 凭据

优先读取 `~/.dsh/repo-pipeline.json`（0600）：

```json
{
  "githubUser": "coreyleung-art",
  "giteeUser": "coreyleung",
  "giteeToken": "你的 Gitee 私人令牌"
}
```

命令行传参 `gitee_token` 优先级最高（不落盘）；`GITEE_TOKEN` 环境变量兜底。
首次 setup 会把用到的凭据自动写入该私有文件。

## 独立 CLI（工具化）

不依赖 DSH，任何装了 git/curl/gh 的机器可用：

```bash
scripts/repo-pipeline.sh doctor                        # 环境检查
scripts/repo-pipeline.sh setup ~/my-repo --private     # 一键搭建
scripts/repo-pipeline.sh status ~/my-repo              # 状态
scripts/repo-pipeline.sh sync ~/my-repo                # 手动同步 Gitee
```

可选 `ln -s ~/dsh-plugin-repo-pipeline/scripts/repo-pipeline.sh ~/bin/repo-pipeline` 全局使用。

## 设计要点

- **SSH 回退**：`github.com:443`（HTTPS）不可达时自动生成 ed25519 密钥、
  配置 `~/.ssh/config`（github.com → ssh.github.com:443）、注册仓库 Deploy Key
  （写权限）、并设置全局 `insteadOf` 重写。
- **工具链自适应**：检测 `pyproject.toml`（python/uv：ruff+pytest CI、uv build
  release）或 `package.json`（node：npm ci+test、npm pack release）。
- **模板与 GitHub 官方实践一致**：CI（双 Python 版本矩阵）、sync-gitee
  （GITEE_TOKEN Secret + `--force` 镜像）、release（`v*` tag + softprops/action-gh-release）。
- **凭据不落盘**：Gitee 推送用内联 URL token（仅当次命令），remote URL 保持干净。

## 开发

```bash
pnpm install && pnpm build && pnpm typecheck   # tsc → lib/
node -e "import('./lib/index.js').then(m=>console.log(m.name, typeof m.apply))"
```

## 安装到 profile

```bash
dsh plugin --profile <name> add <本目录> @deepseek-ai/dsh-headless
# 或手动：把 dsh-repo-pipeline 加入 profile package.json 的 dependencies
# 与 dsh.profile.bundles，并在 node_modules 建符号链接。改源码后需重启应用。
```

bundle 的 `cordis.patch.yml` 会在 profile 中插入一行：

```yaml
- insert:
    - id: repo-pipeline
      name: dsh-plugin-repo-pipeline
      config:
        defaultVisibility: public
        credsFile: ~/.dsh/repo-pipeline.json
```

## 目录结构

```
src/index.ts          插件实现（setup/status/sync 三个工具）
src/helpers.ts        进程执行 / 凭据 / 连通性探测 / remote 工具
src/templates.ts      内置 GitHub Actions 工作流模板（自适应工具链）
scripts/repo-pipeline.sh  独立 CLI（bash，零额外依赖）
cordis.patch.yml      bundle 层 patch
```

## 常见问题

- **改了源码不生效**：`pnpm build` 后重启 DSH 应用（bundle 层需要重启加载）。
- **工具未被模型看到**：确认 `dsh-repo-pipeline` 在 profile 的 `dsh.profile.bundles`
  里，且插件行 `repo-pipeline` 已进入组合配置。
- **Gitee 建仓 403**：令牌需勾选 projects 权限；推送用同一令牌（用户名+令牌作密码）。
- **Deploy Key 添加失败**：当前 PAT 无账号级 SSH 管理权限时，改用仓库级
  deploy key（setup 已自动处理），或手动在 GitHub 网页添加。
