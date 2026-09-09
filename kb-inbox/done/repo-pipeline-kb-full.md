# repo-pipeline — 知识库全文（工具清单 / 使用手册 / 踩坑 / 插件开发工作流）

> 来源会话: session-dcac2308 · 2026-08-16 · 供 Dify KB / ChromaDB research 摄入
> 配套: ~/dsh-collab/repo-pipeline-deliverable.md（精编索引版）、~/dsh-plugin-repo-pipeline/README.zh.md

---

## 一、工具清单

repo-pipeline = GitHub + Gitee 双仓接入与 CI/CD 流水线一键搭建工具，双形态交付：

### DSH 插件（web profile 已注册）
| 工具 | 功能 |
|---|---|
| `repo_pipeline_setup` | 一键全流程：git 初始化 → 通道探测（SSH 回退）→ 创建/复用 GitHub+Gitee 仓库 → remote 规划（origin/upstream/gitee）→ 按工具链生成 CI/Gitee 同步/Release/Deploy 工作流 → 双端推送 → 写 GITEE_TOKEN Secret |
| `repo_pipeline_status` | 双仓同步状态（本地 HEAD vs origin vs gitee tip）+ GitHub Actions 最近 5 次运行 |
| `repo_pipeline_sync` | 手动推 Gitee + 触发 Actions 同步工作流 |

### 独立 CLI（零额外依赖：git/curl/gh）
| 子命令 | 功能 |
|---|---|
| `setup <repo_path>` | 同 repo_pipeline_setup，支持 --name/--github-user/--gitee-user/--token/--private/--no-history/--no-push/--no-secret/--no-ci/--no-sync/--no-release/--no-deploy |
| `status <repo_path>` | 双仓状态 + 流水线运行 |
| `sync <repo_path>` | 手动同步 Gitee + 触发 Actions |
| `doctor` | 环境检查：git/curl/gh 登录/凭据/通道探测 |

---

## 二、使用手册

### 安装位置
- 插件工程：`~/dsh-plugin-repo-pipeline`（package name: dsh-plugin-repo-pipeline；行 id: repo-pipeline；已注册 web profile bundles，重启后工具可见）
- CLI：`~/dsh-plugin-repo-pipeline/scripts/repo-pipeline.sh`（可 `ln -s` 挂 ~/bin）

### 凭据（优先级：参数 > 凭据文件 > 环境变量）
```json
// ~/.dsh/repo-pipeline.json（0600）
{ "githubUser": "coreyleung-art", "giteeUser": "coreyleung", "giteeToken": "..." }
```
- Gitee Token 只在推送命令内联使用（不落盘 remote URL）；GitHub 侧靠 gh CLI 登录。
- 首次 setup 会把用到的凭据自动写入该私有文件。

### setup 关键参数
- `repo_path`（必填）、`repo_name`（默认目录名）、`visibility`（public/private）、
- `keep_history`（false 压缩为单次初始提交）、`create_repos`、`push`、`set_secret`
- `enable_ci` / `enable_gitee_sync` / `enable_release` / `enable_deploy`

### 工作流模板（工具链自适应）
- `pyproject.toml` → python/uv：CI 跑 ruff + pytest（3.11/3.12 矩阵）、Release 用 uv build
- `package.json` → node：CI 跑 npm ci + npm test、Release 用 npm ci + npm pack
- 四件套：`ci.yml` / `sync-gitee.yml`（GITEE_TOKEN Secret + --force 镜像 main）/ `release.yml`（tag v* + softprops/action-gh-release）/ `deploy.yml`（占位模板，等 DEPLOY_HOST/USER/KEY Secrets）

### 源码
- GitHub: https://github.com/coreyleung-art/dsh-plugin-repo-pipeline
- Gitee: https://gitee.com/coreyleung/dsh-plugin-repo-pipeline（自动镜像）
- 本地: ~/dsh-plugin-repo-pipeline（README.zh.md 全文档）

---

## 三、网络与密钥踩坑（本机实测沉淀）

1. **HTTPS 假阳性**：github.com:443 TCP 握手可通（nc/node net.connect 成功），但 git-over-HTTPS 实际挂（git push 75s 超时）。判断 git 通道必须实测 `git -c http.connectTimeout=5 -c http.lowSpeedLimit=1 -c http.lowSpeedTime=8 ls-remote https://github.com/github/gitignore.git HEAD`，不能只测端口。疑似 SNI/路由层对 github.com git 端点过滤。
2. **稳定通道 SSH-over-443**：~/.ssh/config 配 `Host github.com → HostName ssh.github.com / Port 443 / StrictHostKeyChecking accept-new / IdentityFile ~/.ssh/id_ed25519`。DNS 解析 20.205.243.x（亚太节点）正常，非污染。
3. **insteadOf 全局重写**：`git config --global url."git@github.com:".insteadOf https://github.com/` 会把所有 https://github.com URL（含显式命令行 URL）改写为 SSH。工具探测逻辑必须先查 `git config --global --get 'url.git@github.com:.insteadOf'`，有值则强制 SSH 模式，否则推送静默走未授权 SSH 路径报 Permission denied。
4. **Deploy Key 全局唯一**：GitHub deploy key 一个公钥只能绑一个仓库（422 "key is already in use"）。多仓库必须 per-repo 独立密钥：`~/.ssh/repo-pipeline_<owner>_<repo>`，推送时 `GIT_SSH_COMMAND="ssh -i <key> -o StrictHostKeyChecking=accept-new -o ConnectTimeout=8"`。
5. **PAT 权限差异**：fine-grained PAT 可建仓/写 Secret/加 repo deploy key，但加账号级 SSH 密钥 403（缺 admin:public_key scope）——账号级密钥需网页手动添加。
6. **Token 不落盘**：Gitee 推送内联 URL token（仅当次命令）；remote URL 干净；凭据集中 0600 私有文件；gh secret set 用 stdin 输入避免进程参数泄露。
7. **bash 命令替换陷阱**：`var=$(func)` 吞掉函数内全部 stdout（含 ok/warn），密钥路径混入提示文本变垃圾值——函数结果用全局变量传递。

---

## 四、DSH 插件开发工作流（Cordis）

- **运行时**：DSH 插件 = Cordis 插件 = npm 包，导出四命名导出：`name`（行 id，profile 唯一）/ `inject`（依赖服务）/ `Config`（schemastery schema）/ `apply`（入口）。
- **四种形态**：tool（`ctx.tools.register(defineTool(...))`）/ command（`ctx.commands.register`）/ service（`ctx.provide`）/ bundle（package.json `dsh.bundle.patch` + cordis.patch.yml insert，装包自动挂 profile 层）。
- **defineTool API**（@deepseek-ai/dsh-tools）：`{name, description, parameters(每属性 {type, required:true?, enum?, description}), output:{schema(JSON Schema), render(args,value)→ContentBlock[]}, execute(args)}`。
- **关键机制**：cordis/dsh-tools/schemastery 是 peerDependencies，**运行时由宿主注入**——插件目录不要装自己的 node_modules（双 cordis 实例会导致 inject 失效）。profile 组合配置：bundle 层 patch 自动合并，行 id 后写覆盖先写。
- **脚手架**：`node ~/dsh-plugin-workflow/bin/create-dsh-plugin.mjs <name> --kind tool --bundle --description "..." --dir <out>`；模板在 ~/dsh-plugin-workflow/templates；完整工作流 docs/workflow.zh.md + 技能 skills/dsh-plugin-production。
- **构建**：tsc NodeNext 严格模式；ESM 相对导入必须写 `.js` 后缀（src 里 import './helpers.js' 编译期映射回 .ts）；output.render 返回 `[{type:'text',text}]` 数组（不能 readonly/as const）。
- **profile 注册（手动）**：① 包加入 profile package.json dependencies（link:/path 或 file:/path）+ dsh.profile.bundles 数组 ② node_modules 建符号链接 ③ 改源码后重启 DSH 应用生效。验证：`node -e "import('./lib/index.js').then(m=>console.log(m.name,typeof m.apply))"`。
- **实践教训**：工具进程执行用 child_process spawn（execFile 无 stdin 通道）；GitHub Actions 模板里 `${{ }}` 在 TS 模板字符串要转义 `\${{`；凭据文件 0600；高险动作先 dry-run 演练。

---

## 五、验收建议（QA 检索词）
灌库后可跑三个查询验证命中：`repo-pipeline` / `deploy key 唯一` / `insteadOf` / `HTTPS 假阳性`。
