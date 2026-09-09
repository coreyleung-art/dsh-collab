---
title: "GitHub 网络与密钥陷阱（dcac2308 实测沉淀）+ 协作补充"
source_type: collaboration
source_url: "来自 session-dcac2308 跨会话交付批次 2/2"
ingested: 2026-08-16
tags: [llm-wiki-raw, github, network, security, deploy-key]
---

# 块三：GitHub 网络与密钥陷阱（本机实测沉淀）

1. HTTPS 假阳性：github.com:443 TCP 握手可通（nc/node net.connect 成功），但 git-over-HTTPS 实际挂（git push 75s 超时）。判断 git 通道是否可用必须实测：`git -c http.connectTimeout=5 -c http.lowSpeedLimit=1 -c http.lowSpeedTime=8 ls-remote https://github.com/github/gitignore.git HEAD`，不能只测端口。根因疑似 SNI/路由层对 github.com git 端点的过滤。

2. 稳定通道是 SSH-over-443：~/.ssh/config 配 Host github.com → HostName ssh.github.com / Port 443 / StrictHostKeyChecking accept-new / IdentityFile ~/.ssh/id_ed25519。DNS 解析 20.205.243.x（GitHub 亚太节点）正常，非 DNS 污染。

3. insteadOf 全局重写：`git config --global url."git@github.com:".insteadOf https://github.com/` 会让所有 https://github.com URL（含显式命令行 URL）在存储/使用时被改写为 SSH。后果：工具若按 HTTPS 模式建 remote，实际推送却走 SSH；若仓库没配密钥则「Permission denied (publickey)」。探测逻辑必须先查 `git config --global --get 'url.git@github.com:.insteadOf'`，有值则强制 SSH 模式。

4. Deploy Key 全局唯一：GitHub deploy key 一个公钥只能绑定一个仓库（"key is already in use" 422）。一台机器多仓库场景必须 per-repo 独立密钥：~/.ssh/repo-pipeline_<owner>_<repo>，推送时 GIT_SSH_COMMAND="ssh -i <key> -o StrictHostKeyChecking=accept-new -o ConnectTimeout=8"。

5. PAT 权限差异：gh 的 fine-grained PAT 可建仓/写 Secret/加 repo deploy key，但加账号级 SSH 密钥会 403（缺 admin:public_key scope）——账号级密钥需用户在网页手动添加。

6. Token 不落盘：Gitee 推送用内联 URL（https://user:token@gitee.com/...，仅当次命令）；remote URL 保持无 token 干净形式；凭据集中存 0600 私有文件；Actions Secret 用 gh secret set（stdin 输入，避免进程参数泄露）。

7. CLI 命令替换陷阱：bash 里 `var=$(func)` 会吞掉函数内所有 stdout（含 ok/warn 提示），密钥路径若混入提示文本会变垃圾值——函数结果用全局变量传递。

# 协作补充

- 部署验证：DEPLOY_HOST/USER/KEY 配好后协助 dsh-ssh 验证——deploy.yml 是占位模板（appleboy/ssh-action 已注释），服务器信息到位后填真实部署动作。
- 知识灌入后 QA 验证建议：检索「repo-pipeline」「deploy key 唯一」「insteadOf」三个查询确认命中。
- 有更新（如部署模板落地、插件迭代）增量同步到 ~/dsh-collab/repo-pipeline-deliverable.md。
