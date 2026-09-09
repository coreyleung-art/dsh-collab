# LBS 数据源库 · 花店 AI 运营官对接文档（P3-1）

> 数据调查员 4787d717 · 2026-09-01 · 对接：花店 AI 运营官产品（POI 底表 / 获客名单 / 竞品对标）
> 前置：P0-P2 已完成（poi-db SQLite + dsh-tools poi + source-trust --poi + KB poi-cache）

---

## 1. 数据资产现状

| 资产 | 位置 | 规模 | 用途 |
|---|---|---|---|
| SQLite 库 | `~/poi-db/pois.db` | 73 POI + 6 商圈 + 75 来源 | 机读查询（主） |
| CSV | `~/dsh-collab/research/flower-poi-base-2026W36.csv` | 73 行 | 人读/导入导出 |
| 主文档 | `flower-poi-base-2026W36.md` | 6 商圈明细 | 文档/评审 |
| KB 向量索引 | poi-cache（6c8dae0b-…） | 6 篇 18 chunks | 语义检索 |
| 工具链 | `dsh-tools poi` / `source-trust --poi` | v1.24.0 | CLI 查询/评级 |

## 2. 运营官对接接口（3 个场景）

### 场景 A：获客名单（外呼/地推优先级）

```bash
# 全部可直拨电话（19 家，按商圈分组）
dsh-tools poi phone

# 指定商圈可直拨
dsh-tools poi phone --district ZJX

# 高/中-高置信 + 可直拨（精准获客）
dsh-tools poi query --conf 高 --phone --json
```

**优先级规则**（建议运营官采用）：
1. 高置信 + 有电话（如 Flora 13202023344、和平花店 0757-83390379）→ 第一梯队外呼
2. 中-高 + 有电话 → 第二梯队
3. 无电话高置信 → 先平台 App 内搜店补电话再外呼
4. C 组（花长廊单源）→ 仅扫街，地推前现场核验

### 场景 B：竞品对标（同商圈价格带/品类分布）

```bash
# 按商圈列出全部（含品类线索）
dsh-tools poi list --district ZJX

# JSON 输出对接程序
dsh-tools poi query --district YX --json
```

**对标维度**（运营官可用）：
- 同商圈店型分布（高端定制 / 连锁速递 / 社区店 / 工商登记型）
- 价格带线索（珠江新城 ¥50→¥1280 高端带 vs 北京路楼内店为主）
- 竞争密度（北京路 1km² 23 家 vs 江南西 7 家）
- 用户自有店对标：天河守白/初蘅/体育东 ↔ TYD+ZJX 商圈；江南西 ↔ JNX；客村/越秀 ↔ KC+YX；佛山禅城 ↔ FS

### 场景 C：语义检索（运营官自然语言查询）

通过 KB poi-cache（baseId `6c8dae0b-8ced-40e4-8d9b-167f05f51e75`）：
- 「珠江新城高端定制花店」→ Flora/D'ardrée/LaFleur/Studio C（score 0.94）
- 「24 小时营业花店」→ 星汇园/花柚（宣传待核）
- 「商圈边缘店」→ 花恋/润花艺
- 「农贸市场花档」→ 广州喜庆/幸福聪聪

## 3. 数据质量约定（必须遵守）

1. **在营状态全部待核**（in_operation=NULL）——获客前必须电话/到店/平台确认，禁止直接断言在营
2. **置信度分层使用**：高/中-高 → POI 底表；中（C 组）→ 扫街名单；中-低/低 → 线索池，禁止对外断言
3. **工商登记型**（FS-07~12、ZJX-10 念花舍、YX-23 港凤）为注册地址非实体店，仅作线索
4. **清洗反例**：木可花房（花房主题餐厅非花店）已排除——花长廊 B 源条目需警惕
5. **反爬合规**：大众点评/美团/高德主站未直采；需平台数据时走人工/账号侧核验

## 4. 更新机制（成本治理下默认手动）

| 动作 | 命令/工具 | 频率 |
|---|---|---|
| 商圈重采 | 子代理 web_search + 聚合站（复用 v2 方法） | 手动，2-4 周 |
| 单店核验 | 电话/到店/平台 App 内搜店 → UPDATE pois SET is_verified=1 | 按需 |
| 入库 | `python3 ~/poi-db/import_pois.py <csv>`（幂等 upsert） | 每次重采后 |
| 审计 | `dsh-tools poi audit`（SQLite vs CSV 一致） | 每次入库后 |
| KB 同步 | 重导 6 篇商圈文档 → knowledge_add_document | 每次更新后 |
| 回报 | bb-write → 黑板 data/investigate/ | 每次实质变更 |

## 5. 后续扩展（P4 候选，待用户指令）

- [ ] 坐标补全：地址 → geocode（需外源服务，高德/百度逆地理有额度）
- [ ] LBS 距离查询：商圈半径内配送覆盖分析（pois.lat/lon + districts.radius_m 已预留）
- [ ] 获客名单导出：dsh-tools poi phone --json → 运营官 CRM 对接
- [ ] 竞品对标报告：按商圈自动生成店型/价格带/密度对比（对接 dify_report）
- [ ] 商圈扩采：天河城/上下九/沙面/越秀公园等新商圈（复用 merge_poi_v2.py）

---

*对接：数据调查员 · 2026-09-01 · 待运营官侧接入*
