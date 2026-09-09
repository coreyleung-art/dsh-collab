# CLD 统一治理规范 v1.0（版本/日志/文档/落链/回流/热迭代/分发/沙箱）

> 2026-08-29 星桥-mac-mini-协调者 · 用户指示：CLD 本地开发统一版本管理和日志管理文档说明，落链，
> 不能每台设备自己修，每次迭代修改回流这里；规划热迭代逻辑；修完让其他安装侧接收新版本；
> 加入小样本沙箱模拟逻辑，隔离生产升级自己死掉。

## 一、治理原则（用户要求映射）

| 用户要求 | 治理机制 | 规则依据 |
|---------|---------|---------|
| 统一版本管理 | CLD 源码 git + tag + CHANGELOG + genebank 登记 | R006 第6项 |
| 统一日志管理 | CLD 日志规范（exit-trace/heartbeat + 统一落盘）| R006 第7项 |
| 文档说明 + 落链 | README + 设计文档 + 知识库落链 | R006 第5/8项 |
| 不每台设备自己修 | 单一治理中枢（本机 ~/dsh-collab/cld/），端侧只接收分发 | R006 第3项 |
| 迭代修改回流 | 端侧改动 → 打包挂 genebank → 中枢评估 → 合并 → 版本升级 | R010 v1.1 |
| 热迭代逻辑 | 评估重启需求分级（见四）| R011/R015 |
| 其他安装侧接收新版本 | genebank 分发 + 端侧升级指引 | R012 完整体 |
| 沙箱模拟隔离生产 | restart-gate 阶段0（dev-sandbox 小样本）→ 隔离验证后才动生产 | R011 v3/R015 |

## 二、CLD 治理仓库结构（~/dsh-collab/cld/）

```
cld/
├── src/                  # 完整源码（main.js/package.json/scripts/构建配置）
│   ├── main.js           # 壳主逻辑（当前 main.js.cld002 修复版）
│   ├── package.json      # 项目清单（含构建/打包脚本）
│   ├── scripts/          # inject-proxy/device-status 等
│   └── build/            # app.asar 构建产物
├── versions/             # 版本历史（每个版本：asar + main.js + CHANGELOG 摘录）
│   ├── v0.1.0/  v0.2.0/  ...
├── CHANGELOG.md          # 版本变更日志（统一）
├── README.md             # 项目说明（架构/构建/部署/调试）
├── LOGGING.md            # 日志规范（统一日志管理）
├── docs/
│   ├── architecture.md   # 架构文档（壳内嵌 dsh）
│   ├── hot-reload.md     # 热迭代逻辑规划
│   └── deploy.md         # 分发部署指南
└── sandbox/              # 沙箱验证配置（R011/R015）
```

## 三、版本管理规范

```
版本号: v<major>.<minor>.<patch>（语义化）
  major: 破坏性变更（进程模型/API 重构）
  minor: 功能新增（模式/代理/新机制）
  patch: 修复（崩溃/行为修正）

流程:
  1. 修改源码（本机 ~/dsh-collab/cld/src/）
  2. bump 版本号（package.json + CHANGELOG 记录）
  3. 构建 app.asar → versions/vX.Y.Z/
  4. 沙箱验证（restart-gate 阶段0：dev-sandbox + 隔离启动）
  5. 登记 genebank（chromosome=artifacts, name=cld, mutation=vX.Y.Z）
  6. 黑板广播（notes/collab/cld-vX.Y.Z-release）
  7. 端侧分发（MBP/i9 拉取新版本，见六）
  8. 落链知识库（ops-science-research）
```

## 四、热迭代逻辑规划（重启需求分级）

**核心问题：是否真的那么多必须重启的？**

| 变更类型 | 处理方式 | 是否重启 CLD |
|---------|---------|-------------|
| 壳 UI/窗口/菜单 | 修改 main.js → 需重启壳 | ✅ |
| dsh 服务参数/模式 | spawnDsh 参数变更 → 需重启壳 | ✅ |
| 插件更新（agent-way 等）| dsh 加载 → 需重启壳（dsh 随壳）| ✅ |
| 宿主 dsh rc 升级 | runtime 变更 → 需重启壳 | ✅ |
| 前端 UI/布局/状态 | 浏览器刷新（Cmd+R）| ❌ |
| 配置（config.json/settings 非关键）| 读时生效（模式选择等）| ❌ 部分 |
| 规则/文档/工具 | 黑板/独立二进制 | ❌ |

**热迭代方向（未来可做）**：
1. **壳内「重载 dsh」通道**：加 IPC/HTTP 端点 → 触发 spawnDsh 重启（不退出壳）——需改 main.js
2. **dsh 崩溃自动重启**（带退避）：child.on('exit') → 非干净退出自动重新 spawn + 退避上限（防循环）
3. **配置热加载**：config.json 变更 → 监听 + 局部应用（不重启）

**结论**：当前大部分「重启」确实是必要的（dsh 在壳内）；但可优化为「壳内重载」减少退出→拉起的中断。热迭代逻辑按此规划。

## 五、日志管理规范（统一）

```
日志位置: ~/.cld/logs/
  dsh-web.log          # dsh server 输出（壳转发）
  exit-marker.json     # 退出标记（cleanExit/崩溃追踪）
  heartbeat.json       # 30s 心跳（watchdog）
  crash-reason.log     # 崩溃原因追加

规范:
  1. 所有 CLD 日志统一落 ~/.cld/logs/（不散落）
  2. exit-trace 机制保留（崩溃可追溯）
  3. 端侧（MBP/i9）日志格式一致（同字段）
  4. 日志轮转（大小限制，防无限增长）
```

## 六、分发机制（其他安装侧接收新版本）

```
CLD 治理中枢（本机）→ genebank artifacts → 端侧拉取

端侧升级步骤（MBP/i9）:
  1. 收到 notes/collab/cld-vX.Y.Z-release 通知
  2. 从 genebank 拉取 cld-vX.Y.Z 完整包（asar + main.js + 校验和）
  3. R012 完整体校验（checks-transfer.py）
  4. 备份当前 /Applications/CLD.app/Contents/Resources/app.asar
  5. 替换 + 重启 CLD
  6. 回报黑板（notes/collab/cld-vX.Y.Z-ack-<node>）

安全: 每次替换前备份（.bak-v<旧版本>），可回滚
```

## 七、沙箱模拟（隔离生产升级）

```
升级前强制:
  dsh-tools restart-gate（阶段0: dev-sandbox 小样本验证 CLD 源码行为）
  → 隔离环境启动新 asar 验证不崩溃
  → 全 PASS 才动生产 /Applications/CLD.app

隔离验证内容:
  1. main.js 语法/模块加载（dev-sandbox script）
  2. 新 asar 解包完整性（R012 checks-transfer）
  3. 隔离启动新 CLD（独立端口/config）→ 验证 spawnDsh + 窗口 + 心跳
  4. exit-trace 正常（干净退出标记）
```

## 八、落链

- 知识库：ops-science-research（CLD 架构/治理规范）
- 台账：tools-registry.md 加 CLD 条目（版本/状态/分发）
- 黑板：data/mac-mini/registry/cld-vX.Y.Z（版本登记）
- 踩坑档案：CLD 问题 → docs/pitfalls/

## 九、规则账本

- 新增 **R016「CLD 统一治理」**（或并入 R006 工程条目）
- 触发：任何 CLD 源码修改/构建/分发
- 强制：单治理中枢 + 版本/日志/文档 + 沙箱先行 + 端侧分发
