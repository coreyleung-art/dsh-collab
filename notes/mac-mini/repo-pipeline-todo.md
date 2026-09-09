# repo-pipeline 待办（中枢巡检回报 · dcac2308）

## GitHub/Gitee 双仓/流水线待办
1. **D3 云端拓扑**（待办）：GitHub 托管 Actions 通知需公网 URL——Tailscale 暴露 8790 排期中（外链 92623479/网络线），就绪后换 NOTIFY_URL Secret 值即生效
2. **部署流水线**（待办）：DEPLOY_HOST/USER/KEY 三值等用户提供（ssh_list 无主机），到位后写 Secret + 填 deploy.yml 真实动作 + QA 验证
3. CI 通知本机链路：已闭环（台账 §5.6，8790→分级→企微 P1 实测通过）

## 其余
- 插件健康：注册完好、双仓同步、QA PASS 基线
- 无其他自主可推进项；被动应答模式维持
