# Agent 操作守则 · guard 工具接入（2026-09-04）

## 本 agent（mbp-ops 运维/诊断）每次对 CLD/dsh 底层操作必须：

### 写操作前（强制）
```
1. guard check-writable <目标路径>     # 红线即停（exit 1）
2. guard backup <目标路径>              # 备份（最后 2 good 滚动）
3. 若改依赖: guard version-check <pkg>  # 版本校对
4. 沙箱验证 → 落真 → 重启实测
```

### 工具调用方式
```bash
/Users/coreyleung/.dsh/tools/guard <subcommand> <args>
# 或统一 python 入口:
/usr/bin/python3 /Users/coreyleung/dsh-collab/guard/tools/guard <subcommand> <args>
```

### 关键路径
| 用途 | 路径 |
|---|---|
| guard 主程序 | ~/dsh-collab/guard/tools/guard |
| 便捷入口 | ~/.dsh/tools/guard |
| 治理规范 | ~/dsh-collab/cld-dsh-dev-system/rules/规则全集-v2.md |
| 风险清单 | ~/dsh-collab/cld-dsh-dev-system/risks/风险行为清单.md |
| 备份目录 | ~/dsh-collab/guard/backups/ |

### 红线备忘（check-writable 会拦）
- dsh-tools/lib → 绝不可改（schema DSL）
- Electron Framework → 绝不可改
- .pnpm → 绝不可手改
- auto-index.plist → 需审批

### 重启后必测（验证清单）
dump-config EXIT0 → web 200 → doctor 会话数 → 点会话历史可加载 → renderer 无错
