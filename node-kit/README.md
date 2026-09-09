# node-kit · 节点一键装备包（P1 · 2026-09-09）

> 目标：任何新节点（Windows 为主）**即插即用**入网——一次装备、处处复用。
> 设计依据：comm-server/node-kit-standardization-design-v1.md（层2 装备包）
> 从 MBP（5 坑）/i9 实战提炼：目录/token/黑板地址/代理身份/硬编码

## 目录结构

```
node-kit/
├── device-daemon.py      # 守护（从 comm-server 复制, env 驱动零硬编码）
├── deploy.sh             # 一键: 校验门→建目录→复制→平台注册→自检
├── selfcheck.sh          # 健康自检（守护/队列/心跳）  [待补]
├── conf/<node>.env       # 每节点配置模板
├── platform/
│   ├── macos/            # launchd plist 模板（README 含手工操作）
│   └── windows/          # schtasks + xml 模板  [P3]
└── README.md             # 本 SOP
```

## 装备 SOP（标准流程, 一次跑通）

```bash
# ① 部署门校验（层1 Lean4）
python3 ~/dsh-collab/scripts/gate-deploy-check.py --file <守护>.py

# ② 一键装备（校验→复制→launchd/schtasks 注册→自检）
./deploy.sh --node <id> [--dry-run]     # mac-mini 不需装(自持)

# ③ 自检三项
pgrep -fl device-daemon.py          # 守护在跑?
curl :8791/bus/status               # 队列零积压?
heartbeat 新鲜度                    # 心跳 <90s

# ④ E2 v2 自报注册（层3）——节点启动 PUT /data/discovery/devices/<id>
#   {id, os, ip, cli_ver, services:[...], agents:[...], via:"self"}
```

## Windows 落地要点（i9 已验证承载）

- **schtasks** 代替 launchd：`schtasks /create /tn dsh-nodekit-<id> /tr "python device-daemon.py" /sc onstart`
- python3 需安装；守护纯 stdlib 跨平台（device-daemon-i9.py 已满足）
- token 存 `%USERPROFILE%\.dsh\`（0600 等效）
- env 注入：schtasks 无直接 env → 守护读 conf/<node>.env

## 验收（P1 完成标准）

- [ ] deploy.sh --dry-run 可复跑不破坏（幂等）
- [ ] macOS launchd plist 模板可用
- [ ] 从 MBP 实战提炼的 env 全进 conf 模板（无硬编码）
- [ ] 守护复制后经 gate-deploy-check PASS

---
*node-kit P1 · 2026-09-09 · 明鉴(主源) + 星桥(i9部署确认)*
