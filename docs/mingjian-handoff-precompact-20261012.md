# 明鉴 · compact 前交接锚点（2026-10-12）

> **用途**：本会话（`session-a190c54c-ca73-4845-9a65-9dc002d45044`）压缩/重启后的**恢复入口**。
> **读法**：先读 §0 一页速览 → §8 恢复动作。其余按需查。
> **配套**：黑板卡 `notes/collab/mingjian-handoff-precompact-20261012`（同样内容，可跨机读）；本文件路径已登记进 `agent_profile.resources`。

---

## §0 一页速览

| 项 | 值 |
|---|---|
| 我是谁 | **明鉴 v3** · session `a190c54c-ca73-4845-9a65-9dc002d45044` · **mac-mini** |
| 角色 | 蓝图主编 + **SystemGraph 主源架构师（属主/实施主体）** + Φ 治理哲学库维护 + 检测工具作者 |
| 唯一主线 | **SystemGraph 内部补全与端到端跑通**（A 实时 → B 编辑 → C 推荐 → D 体检 → E 壳对齐） |
| 方案 | `~/dsh-collab/docs/systemgraph-internal-completion-plan-20261008.md` · **11,816 B** · 指纹 **`4f9a4da35b83a9ed`** |
| 裁定 | **已下**（2026-10-08 裁判，**有条件通过**）；**A 组 v2 已裁定落实 ⇒ 可开工** |
| 当前状态 | **A 组可开工**（等用户一句「开工」）；C 组有**真阻塞**（数据源 0 条） |
| 基础设施 | 8798 后端（PID 5516）· 8792 黑板（rust-blackboard PID 1221）· `/api/overview` 200 ✅ |
| 我持有锁 | **0**（实测 `lights: []`） |

---

## §1 主线：SystemGraph 五组状态

### A 组 · 数据实时化（**可开工**）
裁定条件（方案 §十一）：
- **双通道保留**；术语澄清：**双通道/双触发 ≠ 双写**（前者=两种触发方式，后者=写两个板实例）
- **前置1** 文件监听元组 = **`(mtime, size, ctime)`** —— `cp -a`/`cp -p`/`rsync -a` 这类**保 mtime 的静默写必须可见**
- **前置2 ★ 权威源单一 = 后端内存模型**（初始化时由文件全量加载；**文件变更与 SSE 事件都只作「触发重读」信号，不以事件载荷直接改模型**）
- **前置3 四路验收**：①黑板写 ②普通文件写 ③**保 mtime 写（`cp -a`）** ④原子 rename —— **每路单独断言 10s 内反映，四路全过才算通过**
- **补1** 轮询间隔 **< 10s 且留余量**（★ 主路径事件驱动 **≠** 兜底路径免约束；兜底同样 <10s，否则须显式声明事件驱动路径具备独立丢失检测）
- **补2** **逐路记 pass/fail + 实测时延**，**禁止只报总失败**（四路失效原因各不相同）
- 我的 401 修复（`Authorization: Bearer <~/.dsh/blackboard-token>`）**采纳入实施**

### B 组 · 蓝图编辑与版本治理（条件齐备）
- **写端点三件**：授权（Bearer board-token + 调用者身份登记/写卡留痕 author）· 回滚（软删 `retired` + `POST /blueprints/<id>/rollback?to=<v>`）· **幂等**（同内容重复 PUT 返回同版本号，版本不自增）
- **diff 内容基准 = 一版一文件**：`~/dsh-collab/data/blueprint/<id>/blueprint-<id>-v<X.Y>.md`
- **修复对象 = 黑板卡 `data/blueprint/versionlog`（v12）的流程层**（自 09-07 停写）
- **明确不在范围**：①`version-map.json`（后端**渲染状态缓存**，`versions:{}` 设计如此）②「9 条 src 断链」（**我已撤回**：那 9 个值是**黑板键**不是路径，实测 9/9 存在 200 且真内容 —— 我核错了域）

### C 组 · 孤岛推荐引擎（⚠️ **有真阻塞**）
- **阻塞**：`confirmed-links` 数据源 = **0 条** ⇒ recall@60 不是「未测」而是「**无条件可测**」；门槛建议 **N ≥ 50**
  - 穷举证据：`~/Desktop/SystemGraph-本地文件化/api/confirmed-links.json` 存在但 `links`=0 · `~/dsh-collab/data/blueprint/{gallery/,}confirmed-links.json` 均不存在 · 板端三候选键均 404 · `/api/confirmed-links` → `{"links": []}`
- **口径（我核出并已被采纳）**：候选 = **接口返回 60**（不是 588）；实现是 **5 特征**打分，不是「三路」；「名称相似度/权限边」**不是实现里的东西**
- 另有机器判据：hold-out 20% recall@60 ≥ 0.5（复跑手段 `scripts/holdout-split.py`）· 单特征退化下界 ≥ 0.3 · 不得推荐已存在的边 · 返回条数有界 ≤ 60

### D 组 · 能力体检与风险视图（条件齐备）
- **★ 前置（我核出）**：**先做 ability 归一化再出矩阵** —— 466 个 ability 中 **460 个是单例**（只被 1 个 agent 声明）⇒ 按字符串精确匹配算「能力冗余」会得出「几乎没有冗余」的**假读数**（更可能是自由文本表述差异）
- 数据面：`cap-perm`（132 节点/472 边 · 边全为「拥有」）· `cap-view`(87/293) · `perm-view`(121/113 · resTotal 48)
- 两份报告各带 `--selftest` 负控

### E 组 · 壳对齐（条件齐备）
- 壳位置：`~/system-graph-app`（macOS）· `~/system-graph-ios`（iOS）
- **双 URL + fallback 模式已存在**：`SystemGraphApp/Sources/WebShellView.swift:17-18`（Tailscale `100.120.203.20:8798` → 局域网 `192.168.1.28:8798`）

---

## §2 未结事项（★ 其中前 4 条**只活在会话上下文里**，最需要本文件兜住）

| # | 事项 | 状态 | 归属 |
|---|---|---|---|
| 1 | **Gitee token 轮换** | ⚠️ 待办 —— 2026-10-08 我把它**打进了会话记录**（我的操作错误：该只看键名不看值） | 用户 |
| 2 | **GitHub 仓「-」删除审批** `aprv-muylf3qj-nfdq0kbt` | **pending**（当时唯一未决）—— 我**没有代点**，倾向**归档而非删除** | 用户 |
| 3 | **xdom `int` 待回球** 🔴 | 外部线对 `xdom-mail.py` v1.1.2 的复核回信：**六条声称 5 成立 / 1 不成立（S3 游标负控守错了对象）**；钥匙 `int.key` **在**（`~/.dsh/xdom-keys/`） | 我（治理线，非 SystemGraph） |
| 4 | **`event-bus.py` 111 条 pending 积压** | 全部指向**已 bricked** 的 `session-fa1f9150-c94`（星桥第一任），跨度 08-20 → 10-03 ⇒ **队列在写、消费端死了** | 治理线 |
| 5 | **线上 SystemGraph 落后本地** | `tm.meetfunbp.com/systemgraph/` 仍是旧版；推送需 CloudBase 凭据（我没有） | 老登 / 用户 |
| 6 | 老登的 standalone 推送 + `version.json` 重生成 | 我给的命令与原则已交付；`version-json-pending-20260928.json` 我**主动标废**（它声明的是旧值） | 老登 |

---

## §3 关键实测事实（★ 复现成本高，直接可用）

### SystemGraph 后端（8798）
- **端点**：`path == "/api/*"` 去重 **38** 个 · 剔除 7 个有状态端点（connect-confirm/advance/gate/sandbox · link-status · manager-event · confirm-link）= **31 个只读端点**
- **服务类 = `ThreadingHTTPServer`**（源码 `:25` / `:2630`）⇒ 加 SSE 客户端线程**不阻塞**既有端点
- **`/api/agents` 真源 = `~/.dsh/agent-bus.json`**（实测 **21.0 MB** · profiles **76** · threads 5194）——**不读黑板**；黑板侧 6 个候选键**全 404**
- **`/api/versions` 真源 = 黑板卡 `data/blueprint/versionlog`**（v12 · 写入 ts **2026-09-07T16:47:14** · entries 19 · blueprints 10）
- **`version-map.json` = 后端渲染状态缓存**（`load_version_map`/`save_version_map`/`render_all_snapshots` 自己读写）
- **`/api/biz-assets` 真源 = `gallery/business-asset-map.json`**（我改到 **219 资产 / 21 关系** · 指纹 `8eb3ecce7ae8db88`）；后端**每次请求读盘** ⇒ 改文件立即生效
- 数据层规模实测：**21 蓝图 · 53 边 · 76 智能体 · 19 版本**

### 黑板（8792）与 SSE（8803）
- **8792 与 8803 是同一个进程**：`PID 1221 rust-blackboard-macos-arm64-v0.6.18 --port 8792 --sse-port 8803`
- **★ SSE 游标语义（关键）**：不带游标 → 1 条实时；`Last-Event-ID: 999999` → 0 条；**`Last-Event-ID: 1` → 386 条 / 709 KB**，其中带 `sent_at_iso` 的仅 40 条（含 10-03～10-06 旧卡），**346/386 无该字段**
  ⇒ **不能用事件内时间戳做新旧判据；必须用「已消费的最大 `id`」作水位线**（id 全局单调，10-08 时 ≈17214）
- **`/sse-stats` 不存在**（404）；`/events/stats` 是**假命中**（响应头 `text/event-stream`，掉进了 SSE 处理器）⇒ **桥没有统计端点**
- **写端鉴权**：本机板 + 中央板都要 **`Authorization: Bearer <~/.dsh/blackboard-token>`**（`central-wake.py:49-52` 是约定出处）；不带头则中央 **401**
- **中央板只写不读**（MBP 实测 `device-daemon.py:41`）
- **各机只监听 `notes/<自己>/` 与 `notes/collab/`** ⇒ 跨机要写 `notes/collab/`（我此前只写 `notes/mac-mini/`，本机可见、跨机不可见）
- `/data` 可枚举（32,060 键）但 `/data/blueprint` 与 `/data/blueprint/changelog` **都 404** ⇒ **中间层不可枚举**

### 环境
- `/tmp` 清理机制 = **`com.apple.tmp_cleaner`（launchd，`StartCalendarInterval Hour=0`，每日 00:00）按「未访问时长」清理** —— **不是按扩展名、不是重启清空**（实测有 6,286 个 mtime 早于开机的文件存活）
- `gh` 在 `/opt/homebrew/bin/gh`（**不在我的 PATH**）；`zstd` 在 `/opt/homebrew/bin/zstd`；Python `zstandard 0.25.0` 可用
- 会话日志：`~/.dsh/sessions/**/*.jsonl.zstd`（**446** 个）

---

## §4 我的工具与近期改动

| 件 | 状态 |
|---|---|
| `~/dsh-collab/scripts/put-card.py` | **296 行 · `d175464676f6ab08`** —— 2026-10-08 加写端 Bearer 鉴权（修「双写静默退化成单写」）；自测 **9/9**；备份 `guard/backups/put-card.py.bak-before-auth-20261008-044511` |
| `~/dsh-collab/scripts/bb-gallery-export.py` | 补 `assets/` 载荷复制（**载荷由索引派生** + 源缺失硬失败 `exit 2`）；兄弟自测 `bb-gallery-export-selftest.py`（正控 1/1 · 反控 2/2） |
| `~/dsh-collab/data/blueprint/gallery/business-asset-map.json` | **219 资产 / 21 关系**（10-08 补挂 09-29 四跑记录）· 备份 `guard/backups/business-asset-map.json.bak-before-fourrun-20261008-0455` |
| `~/dsh-collab/data/cross-session/approval-blocking-probe.py` | MBP 求数探针（6,075 字符，落盘版） |
| `~/dsh-collab/data/industry/four-run-position-definition-20260928/` | **首份四跑记录**（`four.json` 22,996 B + `COMPARISON.md` 34,114 B + `payloads/`） |
| `~/dsh-collab/data/cross-session/` | 本轮所有落卡源文件（`card-*.json`） |

**我落过的卡（本会话）**：`notes/collab/mac-mini-approval-probe-result-20260915` · `notes/mac-mini/mingjian-systemgraph-plan-review-20261008` · `…-plan-review-BCDE-20261008` · `…-b-group-version-source-20261008` · `…-b-group-ledger-rootcause-20261008` · `…-retract-src-brokenlink-20261008`（**撤回卡**）

---

## §5 判据积累（★ 跨轮复用，最容易丢的一批）

1. **判据的域 ≠ 对象的域** —— 字段叫 `src`、值长得像路径，**不等于它是文件路径**（我把黑板键当路径核，误报「9 条断链」，后自更）
2. **一个为真的读数，配上错的域，会得出错的结论** —— 同一族的否定式
3. **更正要替换，不是追加** —— 更正段加在文末、被更正的正文没改 = 读者读正文仍拿错值
4. **保 mtime 的写入对 mtime 监听不可见**（`cp -a`/`copy2`/`rsync -a`/`tar -x`）⇒ 用 `(mtime,size,ctime)` 或 `ctime`（ctime 不可被保留）
5. **未裁决 = 按 id 配对，不是数事件** —— 数事件会被 asked/decided 各自的计数骗
6. **空 ≠ 无 · 不可判 ≠ 不成立** —— 板不可达必须读作「不可判」
7. **报「0 条」必须附【扫过的面】**（文件数/行数/时间窗），否则「0」可能是没扫到
8. **数字必须带截至时刻** —— 「未发现」≠「不存在」
9. **数字要靠【被经过的入口】计数**；覆盖率的单位是被经过的入口数
10. **判据要跟着对象走** —— 资产属于哪个节点就在哪个节点核；核不了记【未评估】，**不记【坏】**（我曾把 i9 的 `E:\` 路径判成坏指针，62→18）
11. **我的观测装置会自己坏** —— 同一天多次：`ls --time-style`（macOS BSD 不支持）被 `2>/dev/null` 吃掉、`os.path.join("~/x",p)` 没 `expanduser`、`head -5` 截断让我误判 `int.key` 不存在、macOS 无 `timeout`。**量到异常先怀疑装置**
12. **越诚实地标注「测算」，某些闸门越不可能报警** —— R4 待验证项会被自动派生补满，闸门反而失去分辨力

---

## §6 协作对象与通道

| 对象 | id | 备注 |
|---|---|---|
| **星桥第二任** | `session-e317d6ab-5302-4b33-b095-947983ba16f4` | mac-mini · 协调/核验 · 10-11/12 在动 `xdom-mail.py`/`artifact-commit.sh`/`deviation-ledger` |
| 老登 | `session-aa528267-0434-4bf5-87c5-d5a61f8215b2` | CloudBase 凭据持有者 |
| MBP 发布官线 | `session-20b800d4-98f6-4e5e-90e4-34f7b6ca61d7` | 判据/门方向；曾求数 |
| 裁判 | 独立审查员（R048） | 不代改、不自裁 |
| HR 司库 | `session-2a15e6b1-32a9-48b3-a167-8fe0a28e8d82` | 用户曾指示**不要唤醒** |
| 星桥第一任 | `session-fa1f9150-…` | **已 bricked**（111 条队列积压指向它） |

**门**：`agent_send` v2.4 —— **>200 字且无黑板引用会被拒**（正解：先落卡 → 发「看黑板 <key>」≤200 字）

---

## §7 用户偏好（回复风格）

中文 · 纯 Markdown 表格 · **不用 `dsh-ui` 围栏** · **不用 mermaid** · 直接动手别反复问 · **实测 vs 测算必须区分** · 不美化风险 · 不替对方做决定 · 不锁给对方看的材料 · **正文用中文引号（R056）** · 报告要多轮输出不要压缩成摘要

---

## §8 恢复动作（★ compact 后第一件事）

1. 读本文件 §0 → §1 → §5
2. 跑开工三步（规范 `cross-session-handoff`）：
   - `python3 ~/dsh-collab/tools/xdom-mail.py status --stale-hours 6`（★ `未读 0 ≠ 无信`；**板不可达读作「不可判」**）
   - `python3 ~/dsh-collab/scripts/event-bus.py --status`
   - `agent_light`（写之前才取锁；**绿灯 ≠ 可以不取锁**）
3. 确认基础设施：8798 `/api/overview` 200 · 8792 可达
4. 读方案当前版（**先核指纹**，别信旧行数）：`docs/systemgraph-internal-completion-plan-20261008.md`
5. **如用户已说开工** ⇒ 直接进 **A 组**（按 §1 A 组的七条条件实现数据实时化）

---

*明鉴 v3 · 2026-10-12 · 本文件为 compact 前交接锚点 · 三处冗余：本文件 + 黑板卡 `notes/collab/mingjian-handoff-precompact-20261012` + `agent_profile.resources`*
