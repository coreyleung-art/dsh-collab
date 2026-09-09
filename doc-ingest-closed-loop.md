# 文档沉淀 → 摄取 → 索引 → 检索 闭环协议 v1.0

> 固化: 2026-08-17 · 维护: 文档摄取/归档智能体（session-55d4d1bd）· 工具链归属: 3b5efeef（~/dsh-toolchain/ingest/）
> 背景: 用户反馈「需求沉淀后另一智能体搜索不出来」——根因=文件落在 dsh-collab 工作区但未进知识库/语义库，各会话检索口径（vault+ChromaDB）查不到。

---

## 一、问题根因（实测确认）

| 环节 | 状态 | 结论 |
|------|------|------|
| 需求文件落盘 dsh-collab | ✅ 有 | 工作区 ≠ 知识库 |
| 进入 Obsidian vault raw/ | ❌ 缺 | 未走摄取 |
| 进入 ChromaDB 语义索引 | ❌ 缺 | 未索引 |
| 语义检索可命中 | ❌ 缺 | 查不到 |

**结论**：语义库每次查询实时计算，不存在「刷新频率」问题——缺的是「沉淀后未触发摄取→索引」。

## 二、闭环链路（已工具化自动化）

```
各会话产出文档
   ↓ ① 落盘 ~/dsh-collab/*.md（约定位置）
   ↓ ② 自动触发（ingest-watcher 每 15 分钟扫描 或 主动 @55d4d1bd）
   ↓ ③ ingest-pipeline 摄取：vault raw/d-55d4-/ 归档 + ChromaDB research 集合索引
   ↓ ④ raw/index.md 登记 + watcher 日志记录
   ↓ ⑤ 检索：research 集合语义查询（bge-m3 1024 维）
```

**工具**：
- `~/dsh-toolchain/ingest/ingest-pipeline.py`：单文件/批量摄取（--all 幂等，哈希去重，敏感检测）
- `~/dsh-toolchain/ingest/ingest-watcher.py`：变更监测（one-shot 供 launchd / watch 常驻）
- launchd: `com.dsh.ingest-watcher`（每 900s 检查一次，日志 ~/.dsh/ingest-watcher.log）

## 三、各会话执行规则（必须遵守）

1. **产出文档落盘 dsh-collab**：重要规划/需求/交付物 → `~/dsh-collab/<slug>.md`（INDEX.md 登记可选但推荐）
2. **自动摄取生效**：watcher 每 15 分钟扫描 dsh-collab 变更 → 自动摄取（无需手动）
3. **紧急/即时可检索**：主动 @55d4d1bd 说「摄取 <文件名>」→ 立即管道处理（不等 15 分钟）
4. **检索口径**：语义检索查 ChromaDB `research` 集合（bge-m3 1024 维）；全文检索查 Obsidian vault
5. **敏感内容**：含薪酬/财务/账号密码具体值 → 管道自动拦截只登记；主动标注「敏感」的文件不落 dsh-collab
6. **不改写**：摄取是复制归档，dsh-collab 原文件属主保留、内容不变

## 四、检索方式（各会话可用）

```bash
# 语义检索（bge-m3，research 集合）
~/.openchronicle/venv/bin/python -c "
import sys; sys.path.insert(0, '$HOME/.claude/automation')
from lib import CHROMA_PATH
import chromadb, json, urllib.request
from chromadb.config import Settings
c = chromadb.PersistentClient(path=CHROMA_PATH, settings=Settings(anonymized_telemetry=False))
coll = c.get_collection('research')
q = '你的查询'
req = urllib.request.Request('http://127.0.0.1:11434/api/embeddings',
  data=json.dumps({'model':'bge-m3:latest','prompt':q}).encode(), headers={'Content-Type':'application/json'})
emb = json.loads(urllib.request.urlopen(req).read().decode())['embedding']
for i,d in enumerate(coll.query(query_embeddings=[emb], n_results=3)['documents'][0]):
    print(f'#{i+1}', d[:80])
"
```

或直接 @55d4d1bd 说「查一下 <主题>」——我代查并给出带来源的引用。

## 五、验证记录（2026-08-17 首轮）

- 批量摄取 dsh-collab 66 个未入库文档 → vault raw/d-55d4-/ 67 个 + research 集合 10178→10323 块（+145）
- 语义复检「分布式设备 MCP」→ 第 1 名精确命中 external-link-mcp-plan.md（修复前搜不到）
- watcher 幂等：无变更跳过 ✅

## 六、边界与分工

- 摄取执行：session-55d4d1bd（文档摄取/归档）
- 工具链机制维护：3b5efeef（~/dsh-toolchain 归属）
- 集合属主：research=b241741f（写入走其命名约定，本协议复用现有集合不新建）
- 敏感隔离：只登记不入库（HR e7bfeea8 原则）
- 数据属主：dsh-collab 原文件属主不变，摄取副本仅供检索

## 七、属主可行性确认汇总（2026-08-17 全部闭环）

| 属主 | 结论 | 登记 |
|------|------|------|
| b241741f（research 属主） | 增量共享写合规 ✅；source 统一 collab/ 前缀；全量重建先 agent_light+广播 | v1.0.157 |
| 媒体 54e809ed | domain=media 标注固化（hub 排除、drafts 摘要级、不建独立集合）；16 集发布后 @55d4d1bd 补摄 | v1.0.158 |
| 设备 5a5368af | devices 9 文件全量可索引 ✅；awesun.env 凭据 0 命中（管道范围外） | v1.0.157 |
| 客服 b193c782 | 无隐私类索引 ✅；config.js 密钥 0 命中；草稿批不索引 | v1.0.157 |
| 调查员 4787d717 | 调研 40 文档合并认可 ✅；HTML 剔除正确 | v1.0.157 |
| 学习系统 a3bc8cba | meituan docs 53 份独立链路（不纳入管道）✅；manuals 单篇需检索走紧急 @ | v1.0.157 |

**机制运行状态**：launchd com.dsh.ingest-watcher 已激活（StartInterval 900s，实测 21:33 自动检测→21:35 摄取 17 个成功）。全量资产：vault d-55d4- 213 归档 + research 10688 块（初始 10178）。
