# xingqiao 服务器运维提示（接入 agent 必读 · 2026-10-04 星桥定稿）

> 适用：任何将要在 xingqiao 服务器（106.53.214.108 / xingqiao.meetfunbp.com，Ubuntu 22.04，
> 角色=通讯中枢黑板）上做操作的 agent。动手前先读完本文件；违反门规的操作会被拒或事后追责。

## 1. 登录与身份
- SSH：`ssh -i <key> ubuntu@106.53.214.108`（仅公钥，禁密码、禁 root 登录——不要试图改）。
- sudo：ubuntu 有 NOPASSWD ALL（自动化依赖，已接受风险留档）。**别用 sudo 做与任务无关的事**。

## 2. 动手前五问（缺一不做）
1. **锁**：该资源是否被别的 agent 占用？先 `agent_light(resource: server:106.53.214.108)`，
   独占操作取锁 `agent_lock`，做完 `agent_unlock`。
2. **门**：这是通道/服务变更吗？是 → 先 `channel_gate register`（channel/action/evidence/rollback/blast_radius）。
3. **备份**：要改的文件先 `cp <f> <f>.bak-$(date +%Y%m%d)`（沿用 /opt/comm-server/*.bak-* 惯例）。
4. **回滚**：动手前写下回滚命令（一行可执行），写在变更卡里。
5. **验收**：从第 6 节验收矩阵里挑出本次变更覆盖的行，**改完必跑并留证据**。

## 3. 服务地图（现状快照 · 改动后必须同步本文件）
| 组件 | 状态 | 说明 |
|---|---|---|
| comm-server.service | active（MainPID 311240） | 生产黑板，8792 HTTP + 8803 SSE，**别动** |
| comm-server-test.service | **已禁用（用户指示清理）** | 不要 enable/start 复活它；如确需测试区，先问用户 |
| comm-health.timer / service | 每 5 分钟 | 巡检 10 项服务+内存+磁盘；**改了服务清单必须同步 /opt/comm-layer/ctl/health-ctl.sh 的 SERVICES 与计数** |
| fail2ban | active | sshd jail（1h/10m/5）；被禁 IP 会拒绝登录，别把自己搞进 ban 名单（别用错 key 反复试） |
| ufw | active | 默认拒绝；仅 22/80/443/8791/8792/8803 tcp。**新端口上线必须先 `sudo ufw allow`** |
| nginx | 80/443 | 网关/TLS |
| comm-bus-bridge(8791) / bb-sub 系(8 进程) | active | 总线与订阅，勿随意 restart |

## 4. 数据与键
- 生产数据：`/var/lib/comm-server`（黑板 KV）；token 白名单：`/etc/comm-server-blackboard-tokens.env`（600，改前备份+改后回读）。
- 黑板 key 语法：首段纯小写字母（data/notes/tasks…）；**写后必回读**（写入 200 ≠ 内容落盘）。
- 板端边界：`/notes` 列表只列 notes/*；data/* 键必须直连 GET；跨板取包双头必带
  （X-Webhook-Token + X-Blackboard-Token），裸键会被当前缀查询。

## 5. 变更门规（红线）
- **comm-server 二进制替换**：只在维护窗口做；替换前备份 `.bak-<date>`；用 /tmp 暂存 → 校验 sha256 → 替换 → `systemctl restart` → 跑验收矩阵。
- **系统重启**：按 R043——读回验证（exit-marker startedAt 更新+进程存活）、窗口 ≥90s、失败留日志；
  插件热更优先壳 v4 `POST /reload`（不重启应用），整机重启只留给壳变更。
- **不要**：复活 comm-server-test；不经 ufw 开新端口；删 .bak 文件；在令牌文件里手改 token（追加新 token 走幂等脚本）。
- 用户指示的暂停项：i9 线暂停中（v0.6.17 部署等 i9 回执「已配置+实测 200」）——不要擅自动。

## 6. 验收矩阵（改完必跑，证据贴变更卡）
> ★ 12:28 实测教训：板端对 **localhost/回环连接是信任的**（无头写 200）；鉴权只在**公网面**生效。
> 鉴权矩阵必须打公网端点（https://xingqiao.meetfunbp.com/...），打 localhost 必假绿/假红。
```
curl -s https://xingqiao.meetfunbp.com/clock                # 期望 200 JSON
无头 PUT（公网）→ 401；三 token 写 → 200            # 鉴权矩阵（必须公网面）
systemctl is-active comm-server fail2ban                 # active
sudo ufw status                                          # active，端口面无多
/opt/comm-layer/ctl/health-ctl.sh --alert-board          # 期望 ✅ HEALTHY EXIT=0
journalctl -u comm-server -p err --since "10 min ago"    # 空
```

## 7. 故障诊断速查
- 黑板不通：`systemctl status comm-server` → journal 尾部 → `ss -tlnp | grep 8792`。
- 「拉起后秒退」诊断指纹：**115-131ms 秒退 + exit 0 + 零输出 = 单实例锁拒绝启动**（等锁释放/读回验证重试）。
- 「重启后没回来」：看守护日志 ~/dsh-collab/logs/agentway-relaunch.log（服务器上是 /home/ubuntu/...）+
  `systemctl list-timers` 确认 comm-health 在跑。
- 残留进程先查 systemd 单元再 kill（教训：杀进程前 `systemctl cat <疑似单元>`，防 Restart=always 秒拉）。

## 8. 做完登记（两条）
1. 变更卡：双板写 `data/registry/<变更名>-<日期>`（含：做了什么/证据/回滚命令）。
2. 告警/通知：影响跨端时写 `notes/collab/` 让所有端感知。
3. 若服务地图/验收矩阵因本次变更而变 → **回改本文件**并注明版本日期。
