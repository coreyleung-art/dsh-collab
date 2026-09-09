# dsh 平台会话交付物（session 本会话 · 2026-08-16）

> 跨会话协作约定 v1 登记：本会话（dsh 平台/知识库/远程访问方向）的成果物与路径声明。

## 1. dsh 平台知识库（Obsidian + ChromaDB）

| 件 | 路径 | 规模 |
|----|------|------|
| 原始文档 | Obsidian `raw/dsh/`（runtime 195 + plugins 5 + community 17 + upstream 19） | 236 文件 / 1.3MB |
| 编译页面 | Obsidian `wiki/dsh/`（架构/沙箱/插件开发/社区生态/配置工具/价值分析/远程拓扑/调研流水线） | 8 页 |
| 向量集合 | ChromaDB **`dsh-docs`**（余弦空间） | 2963 块 |
| 同步工具 | `~/.claude/automation/dsh-docs-sync/`（extract.py / fetch_official.py / index.py / sync.sh） | 一键重建 |

## 2. 调研流水线（工具化插件）

| 件 | 路径 |
|----|------|
| 插件 | `~/dsh-plugin-research/`（`/research <topic> [urls]` 命令 + scripts/fetch/index/report/status + research_lib） |
| 技能 | `~/.dsh/skills/research-pipeline/SKILL.md`（触发词：调研/研究/找参考/帮我看看） |
| 向量集合 | ChromaDB **`dsh-research`**（2026-08-16 改名，与 sysops 的 `research` 隔离） |
| 沉淀路径 | Obsidian `raw/research/<date>-<topic>/` + `wiki/research/<topic>.md`（与 sysops 共享目录，append-only） |

## 3. 远程访问拓扑（Tailscale × remote-web-ui）

| 件 | 路径 | 状态 |
|----|------|------|
| 反代入口 | `~/.cld/tools/dsh-tailnet-proxy.mjs`（0.0.0.0:3081 → GUI 动态端口，WebSocket，自动跟随） | launchd `com.dsh.remote`（KeepAlive）✅ |
| 健康监控 | `~/.claude/automation/dsh-health.py`（8 项检查 + --fix 自愈） | launchd `com.dsh.health`（每小时）✅ |
| 配置 | `~/.dsh/settings.yaml` → `remote-web-ui.publicBaseUrl`；`~/.dsh/profiles/web/cordis.patch.yml` → `web-runtime.trustedHosts` | ⏳ 待 GUI 重启生效 |
| 文档 | Obsidian `wiki/dsh/remote-access.md`（终态拓扑 + 三层信任） | — |

## 4. ChromaDB 集合命名约定（三分隔离，防碰撞）

| 集合 | 归属 | 内容 |
|------|------|------|
| `dsh-docs` | 本会话 | dsh 平台/插件生态长期知识库 |
| `dsh-research` | 本会话 | 调研流水线（raw/research + wiki/research） |
| `research` | sysops 会话 | 系统进化研究（9681 块，勿动） |

## 5. 已上报的痛点 / 共享知识

- LM Studio `text-embedding-nomic-embed-text-v1.5` 注册但 GGUF 运行时缺失 → `~/.claude/automation/lib.py` 已加 Ollama `nomic-embed-text` 兜底
- `dsh --profile web` 官方禁止 `--host 0.0.0.0`（安全设计）→ 远程入口必须经反代层
- launchd bootstrap 在受限 shell 下报 error 5（I/O）→ 需完整权限或用户手动执行
- CLD.app 签名封口破损（`app.asar.bak-20260816`）→ 建议 `codesign --force --deep --sign -`，需用户确认

## 备注

- `~/dsh-plugin-research/` 现为共享目录（我方 `scripts/` + sysops 方 `sysops/`、`docs/` 并存）——建议后续把 sysops 工具迁到独立目录或 `~/dsh-collab/` 下，明确所有权边界。
