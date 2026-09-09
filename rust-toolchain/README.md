# Rust 工具链 · 工程化三件套

> 管理：node-bridge / rust-blackboard / rust-genebank 三项目的**版本、日志、流水线**
> 状态：2026-08-25 · mac-mini 中枢

## 一、目录结构

```
rust-toolchain/
├── Makefile              # 统一入口（make test/build/release/status/bump）
├── manifest.json         # 版本清单（三项目版本/产物/tests）
├── scripts/
│   ├── build.sh          # 流水线：test → build(3×3=9产物) → release(归档+校验和)
│   └── bump.sh           # 版本递增（patch/minor/major）+ manifest 同步
├── templates/
│   └── logger.rs         # 统一结构化日志模板（复制进各项目 src/）
├── docs/
│   └── logging-spec-v1.0.md  # 日志规范
└── releases/             # 发布归档（每时间戳一目录 + SHA256SUMS）
```

## 二、日常命令

| 命令 | 作用 |
|---|---|
| `make test` | 三项目 cargo test（38 测试）|
| `make build` | 三项目 × 三平台（macOS/Windows/Linux musl）= 9 产物 |
| `make release` | test + build + 归档到 releases/<ts>/ + SHA256SUMS |
| `make status` | 查看版本清单 |
| `make bump P=node-bridge PART=patch` | 版本递增（Cargo.toml + manifest 同步）|
| `make clean` | 清理 target |

## 三、版本管理

- **Cargo.toml 是唯一事实源**（`version = "x.y.z"`）
- `bump.sh` 改 Cargo.toml + 同步 manifest.json
- 产物命名：`<name>-<platform>-v<version>[.exe]`
- 发布：`build.sh release` 自动归档 + 校验和

## 四、日志规范

- 统一 JSON 行格式：`{"ts","level","comp","msg"}`
- 双写 stdout + 文件（`~/dsh-collab/logs/<project>.log`，可 `DSH_LOG_DIR` 覆盖）
- 5MB 轮转保留 3 个
- 级别过滤（`--log-level` 预留）
- 详规：`docs/logging-spec-v1.0.md`

## 五、三项目现状

| 项目 | 版本 | 平台 | 测试 | 说明 |
|---|---|---|---|---|
| node-bridge | 1.0.5 | macOS/Win/Linux | 18 | 分布式节点桥 |
| rust-blackboard | 0.6.0 | macOS/Win/Linux | 11 | 黑板+SSE 事件桥 |
| rust-genebank | 1.0.0 | macOS/Win/Linux | 9 | 基因库 AI 网盘 |

## 六、变更记录
- v1.0（2026-08-25）：三件套落地。版本（manifest+bump）、日志（统一 JSON 模板）、流水线（build.sh 一键 test/build/release）。
