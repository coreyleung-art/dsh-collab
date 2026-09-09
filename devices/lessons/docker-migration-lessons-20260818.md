# Docker 迁移踩坑沉淀 · Docker Desktop DataFolder 迁移机制

> 沉淀：session-5a5368af（设备协调）· 2026-08-18 · 类型：踩坑/教训（J46 官方文档沉淀）
> 关联：docker-migration-plan.md v2（~dsh-collab/devices/）+ docker-migration-pc-i9-assessment.md

## 一、结论（教训核心）

**Docker Desktop（Windows/WSL2）的 Docker 数据目录迁移必须走 GUI 官方路径（Settings → Resources → Advanced → Disk image location → Apply & Restart），纯命令行手动移动 vhdx 不生效。**

## 二、踩坑过程（时间线）

1. Step 1：settings-store.json 写 `DataFolder: E:\docker-data` ✅ 配置生效（E 盘创建目录）
2. 手动迁移尝试：robocopy 复制 docker_data.vhdx（57.1GB）到 E:\docker-data + 删除 C 盘源 + C 盘释放 57GB ✅
3. ❌ Docker Desktop 重启后**未从 E 盘 vhdx 加载**——C 盘新建空 vhdx（1.9GB），容器列表为空
4. 原因分析：DataFolder 迁移需 Docker Desktop 内部机制（同步 WSL 注册表 + 目录结构 `wsl\disk\` 嵌套），纯放文件不更新注册
5. 回退：E 盘 vhdx 复制回 C 盘默认位置（%LOCALAPPDATA%\Docker\wsl\disk\）→ 仍失败
6. 深度诊断：DataFolder 修复为默认值 → /var/lib/docker 仍不挂载（vhdx 作为 /dev/sde 块设备附加但文件系统未挂载到 docker 数据路径）→ daemon 永久卡 starting
7. vhdx 数据完好性验证：只读挂载 /dev/sde → 容器 ID 目录（fi-dify/tailscale 等 11+）与数据层全部完好 ✅（数据无损失）

## 三、根因判断

- 多次手动移动/复制 vhdx + Docker Desktop 状态残留 → backend 挂载逻辑失效（内部 bug 级，非数据损坏）
- WSL 注册表（docker-desktop distro 的 vhdx 绑定）与 DataFolder 配置不一致导致挂载失败

## 四、正确路径（官方）

1. Docker Desktop → Settings → Resources → Advanced → Disk image location 设为 E:\docker-data
2. Apply & Restart（Docker Desktop 内部执行 vhdx 迁移：复制 + WSL 注册更新 + 挂载切换）
3. 验证：/var/lib/docker 出现数据 + 容器恢复

## 五、经验沉淀（后续可复用）

| 教训 | 应用 |
|---|---|
| DataFolder 迁移必须 GUI Apply&Restart（内部机制同步 WSL 注册） | Docker 迁移、任何 Docker Desktop 数据目录操作 |
| 手动移动 vhdx 不更新 WSL 注册 → 挂载失败 | 避免命令行迁移 |
| vhdx 数据完好性可只读挂载验证（mount -o ro /dev/sdX） | 数据安全确认手段 |
| 迁移前评估 vhdx 冷启动对远程会话影响（I/O 饱和期间 cmd2 不可用） | 迁移窗口规划 |
| 破坏性操作按 J45 L3 审批 | 审批纪律 |

## 六、当前状态（2026-08-18）

- C 盘已释放 57GB（14.8→75GB）✅ 实打实收益
- E:\docker-data 有完整 vhdx 备份（57.1GB）✅
- Docker daemon 待恢复：用户 GUI Troubleshoot → Restart/Reset（官方恢复路径，数据在 vhdx 内保留）
