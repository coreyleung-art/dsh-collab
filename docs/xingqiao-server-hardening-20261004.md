# xingqiao 服务器加固标准与现状（2026-10-04）

> 基线：CIS Ubuntu Linux 22.04 LTS Benchmark（Level 1）+ 云服务器通用安全基线。
> 主机：106.53.214.108（xingqiao.meetfunbp.com）· Ubuntu 22.04.5 · 唯一角色=通讯中枢。

## 逐项对照（✅ 达标 / 🔶 已补 / ⏳ 待办 / ⚠️ 接受风险）

| # | 控制项 | 行业标准 | 审计时状态 | 处置 |
|---|---|---|---|---|
| 1 | SSH 禁密码、禁 root 登录 | 仅公钥 | ✅ 已达标（PasswordAuthentication no · PermitRootLogin prohibit-password） | 维持 |
| 2 | 主机防火墙 | 默认拒绝+最小放行 | 🔶 原 ufw inactive（仅云防火墙） | **已启用 ufw**：22/80/443/8791/8792/8803 tcp 放行，其余拒绝；SSH 新会话复验通过 |
| 3 | 暴力破解防护 | fail2ban | 🔶 原未装 | **已装**：sshd jail（bantime 1h / findtime 10m / maxretry 5），已 enable --now |
| 4 | 自动安全更新 | unattended-upgrades | ✅ 已启用 | 本次手动跑了一轮安全更新 |
| 5 | 系统补丁 | 定期全量升级 | ⏳ 154 个非安全包待升级 | **入维护窗口**：full apt upgrade + 重启（按 R043 读回验证），与用户约时间 |
| 6 | 最小端口面 | 只开业务端口 | ✅ 8791/8792/8803（业务必须公网）+ 80/443（nginx） | 维持；新端口上线必须过 ufw |
| 7 | 敏感文件权限 | 600 | ✅ token env / authorized_keys 均 600 | 维持 |
| 8 | 最小权限 | 最小 sudo | ⚠️ ubuntu 有 NOPASSWD ALL（自动化部署依赖） | **接受风险**留档；缓解=仅公钥登录+fail2ban+云防火墙 |
| 9 | 服务最小化 | 无多余常驻 | 🔶 测试实例 comm-server-test 常驻 | **已清理**（stop+disable+数据目录删除+健康清单同步 10/10） |
| 10 | 变更留痕与回滚 | 每变更留回滚点 | ✅ .bak 惯例 + runbook 回滚路径 + 双板登记卡 | 维持 |

## 已执行变更（今日）
1. ufw 启用（默认拒绝 + 6 端口放行）——回滚：`sudo ufw disable`
2. fail2ban 安装 + sshd jail——回滚：`sudo systemctl stop fail2ban; sudo apt remove fail2ban`
3. 安全更新一轮（unattended-upgrade）
4. 测试实例清理（前序）+ comm-health 期望清单同步

## 待办（维护窗口，与用户约定时间）
- 154 包全量升级 + 重启（重启按 R043：读回验证 + 诊断指纹；业务端口复验矩阵）
- （可选）sudo NOPASSWD 收窄为白名单命令（先梳理部署脚本用到的命令再动）

## 验收矩阵（每次变更后跑）
- `curl clock` 200 · 鉴权矩阵（无头 401 / 三 token 200）· ufw status active · fail2ban sshd jail 计数 · comm-health HEALTHY · 双板读回一致
