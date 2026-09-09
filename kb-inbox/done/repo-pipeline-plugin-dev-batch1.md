---
title: "repo-pipeline 使用手册 + DSH 插件开发工作流（dcac2308 交付）"
source_type: collaboration
source_url: "来自 session-dcac2308 跨会话交付"
ingested: 2026-08-16
tags: [llm-wiki-raw, dsh, repo-pipeline, plugin-dev]
---

# 块一：repo-pipeline 使用手册

【定位】GitHub+Gitee 双仓接入与 CI/CD 一键搭建工具，双形态交付：DSH 插件 + 独立 CLI。

【DSH 插件】本地 ~/dsh-plugin-repo-pipeline，已注册 web profile bundles（行 id: repo-pipeline；包名 dsh-plugin-repo-pipeline）。重启后三个工具可用：
- repo_pipeline_setup：一键全流程——git 初始化→通道探测（SSH 回退）→创建/复用 GitHub+Gitee 仓库→remote 规划（origin/upstream/gitee）→按工具链生成工作流→双端推送→写 GITEE_TOKEN Secret。关键参数：repo_path(必填)/repo_name/visibility/keep_history(压缩历史)/create_repos/push/set_secret/enable_ci|enable_gitee_sync|enable_release|enable_deploy。
- repo_pipeline_status：双仓同步状态（本地 HEAD vs origin vs gitee tip）+ GitHub Actions 最近 5 次运行。
- repo_pipeline_sync：手动推 Gitee + 触发 Actions 同步工作流。

【独立 CLI】scripts/repo-pipeline.sh，零额外依赖（git/curl/gh）。子命令：setup/status/sync/doctor。示例：repo-pipeline.sh setup ~/my-repo --private；doctor 输出环境检查（gh 登录/凭据/通道）。

【凭据】~/.dsh/repo-pipeline.json（0600）：{"githubUser","giteeUser","giteeToken"}；参数 > 凭据文件 > GITEE_TOKEN 环境变量。

【工作流模板】自动识别工具链：pyproject.toml→python/uv（ruff+pytest CI、uv build release）；package.json→node（npm ci+test、npm pack release）；均有 ci.yml/sync-gitee.yml/release.yml/deploy.yml 四件套。sync-gitee 用 GITEE_TOKEN Secret + --force 镜像；release 打 tag v* 触发。

【源码】GitHub: github.com/coreyleung-art/dsh-plugin-repo-pipeline；Gitee: gitee.com/coreyleung/dsh-plugin-repo-pipeline（自动镜像）；本地 README.zh.md 全文档。

# 块二：DSH 插件开发工作流（Cordis）

【运行时】DSH 插件 = Cordis 插件 = npm 包，导出四个命名导出：name（行 id，profile 内唯一）/ inject（依赖服务）/ Config（schemastery schema）/ apply（入口）。

【四种形态】tool（模型侧工具，ctx.tools.register(defineTool(...))）/ command（用户斜杠命令，ctx.commands.register）/ service（内部 API，ctx.provide）/ bundle（装包自动挂 profile 层：package.json 声明 dsh.bundle.patch + cordis.patch.yml insert）。

【工具定义】defineTool 来自 @deepseek-ai/dsh-tools：{name, description, parameters(每个属性 {type, required:true?, enum?, description}), output:{schema(JSON Schema), render(args,value)→ContentBlock[]}, execute(args)}。参数 enum 用字符串数组即可。

【关键机制】@deepseek-ai/cordis、dsh-tools、schemastery 是 peerDependencies，运行时由宿主注入——插件目录不要装自己的 node_modules（会双 cordis 实例导致 inject 失效）。profile 组合配置：bundle 层 patch 自动合并，行 id 后写覆盖先写。

【脚手架】node ~/dsh-plugin-workflow/bin/create-dsh-plugin.mjs <name> --kind tool --bundle --description "..." --dir <out>；模板在 ~/dsh-plugin-workflow/templates，完整工作流文档 docs/workflow.zh.md + 技能 skills/dsh-plugin-production。

【构建】tsc NodeNext 严格模式；ESM 相对导入必须写 .js 后缀（src 里 import './helpers.js' 编译期映射回 .ts）；output.render 返回 [{type:'text',text}] 数组（不能 readonly/as const）。

【profile 注册】手动方式：① 包加入 profile package.json 的 dependencies（link:/path 或 file:/path）+ dsh.profile.bundles 数组 ② node_modules 建符号链接 ③ 改源码后需重启 DSH 应用生效。验证：模块冒烟 node -e "import('./lib/index.js').then(m=>console.log(m.name,typeof m.apply))"。

【实践教训】工具进程执行用 child_process spawn（execFile 无 stdin）；GitHub Actions 模板里 ${{ }} 在 TS 模板字符串要转义 \${{；凭据文件 0600；高险动作先 dry-run。
