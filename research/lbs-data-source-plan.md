# LBS 数据源库规划（v1.0 草案）— 花店 POI 地理数据资产

> 规划：数据调查员 4787d717 · 2026-09-01 · 基线：flower-poi-base-2026W36（6 商圈 73 家 POI）
> 目标：把「一次性采集的花店画像库」升级为「可查询、可更新、可评级、可对接运营官」的 LBS（Location-Based Services）数据源库
> 关联：R006 插件化工具化 9 项标准 · source-trust 信源评级 · papers-db 落链模式 · 花店 AI 运营官产品

---

## 1. 定位与目标

**一句话**：LBS 数据源库 = 以商圈为空间单元、以花店 POI 为实体的**结构化地理数据资产**，与论文库（papers-db）并列成为第二类落链数据源，服务获客对标、配送覆盖、竞品画像与「花店 AI 运营官」产品的 POI 底表。

**要解决的问题**（现状痛点）：
1. 画像库是**一次性快照**（md+CSV），无更新机制 → 商圈重采需全量重做
2. 无**查询接口** → 运营官无法按商圈/置信度/电话可拨/品类过滤
3. 无**数据源评级** → 每家店的来源可信度未结构化（只有描述性置信度）
4. 未纳入**信源体系** → source-registry 没有 LBS 数据源登记，source-trust 无法对 POI 来源评级
5. 未**向量化/落链** → 无法语义检索「哪些店做高端定制」「哪些店在商圈边缘」

**成功标准**：
- P0：SQLite 建库（pois 主表 + sources 表 + districts 表），73 家 POI 全量入库，CSV 可导入导出
- P0：`dsh-tools poi-*` 子命令（query/list/import/audit/stats），对接 R006
- P1：source-trust 扩展到 POI 来源评级（数据源分级：聚合站/工商/地图 POI/平台店页）
- P1：data-sources.md + source-registry.json 登记 LBS 数据源
- P2：KB 向量化（poi-cache 库），语义检索「高端定制花店」「24h 营业」
- P3：对接花店 AI 运营官——POI 底表 API / 获客名单 / 竞品对标

## 2. 数据模型（SQLite 设计）

### 2.1 pois 主表（花店 POI 实体）

```sql
CREATE TABLE pois (
  shop_id     TEXT PRIMARY KEY,      -- JNX-01 / KC-01 / ZJX-01 / FS-01 / YX-01
  name        TEXT NOT NULL,
  district_id TEXT REFERENCES districts(district_id),  -- 商圈外键
  address     TEXT,
  phone       TEXT,                  -- 未公开=NULL；待核=标记
  platform_entry TEXT,              -- 平台入口 URL（多源用 JSON 或分表）
  category_clue TEXT,               -- 品类/特色线索
  confidence  TEXT,                 -- 高/中-高/中/中-低/低（保留 v1 口径）
  source_grade TEXT,                -- 数据源评级（见 §3，S/A/B/C）
  lat REAL, lon REAL,               -- 坐标（已知店填，未知 NULL）
  is_verified INTEGER DEFAULT 0,    -- 0=待核 1=已电话/到店核验
  in_operation INTEGER,             -- 在营状态：NULL=待核 1=在营 0=停业
  captured_at TEXT, updated_at TEXT,
  notes TEXT                        -- 疑点/清洗反例标注
);
```

### 2.2 districts 商圈表

```sql
CREATE TABLE districts (
  district_id TEXT PRIMARY KEY,     -- JNX / KC / TYD / ZJX / FS / YX
  name        TEXT NOT NULL,        -- 江南西 / 客村 / 体育东 / 珠江新城 / 佛山祖庙 / 北京路
  city        TEXT DEFAULT '广州',
  district    TEXT,                 -- 行政区（海珠/天河/禅城/越秀）
  lat REAL, lon REAL,               -- 商圈中心坐标
  radius_m    INTEGER,              -- 商圈半径（用于 LBS 距离查询）
  priority    TEXT,                 -- P0 自有店商圈 / P1 扩展
  notes       TEXT
);
```

### 2.3 poi_sources 数据源表（每家店多来源可追溯）

```sql
CREATE TABLE poi_sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  shop_id TEXT REFERENCES pois(shop_id),
  source_name TEXT,                 -- city8 / 花长廊 / 电话邦 / 天眼查 / Apple地图 ...
  source_url TEXT,
  grade TEXT,                       -- S/A/B/C（source-trust 域评级映射）
  captured_at TEXT,
  UNIQUE(shop_id, source_url)
);
```

### 2.4 字段映射（v2 CSV → SQLite）

| CSV 字段 | SQLite | 说明 |
|---|---|---|
| shop_id | pois.shop_id | 直接映射 |
| 名称 | pois.name | 直接映射 |
| 商圈 | districts.name（join） | 拆分前缀 |
| 地址 | pois.address | 直接映射 |
| 公开电话 | pois.phone | 未公开/待核 → NULL+flag |
| 平台入口 | pois.platform_entry | 多源 URL 入 poi_sources |
| 品类线索 | pois.category_clue | 直接映射 |
| 置信度 | pois.confidence | 直接映射 |
| 来源 | poi_sources.source_name | 拆分多条 |

## 3. 数据源评级（source-trust 扩展）

POI 来源与论文/文章信源不同，按**来源类型**评级（替代域名评级）：

| 等级 | POI 来源类型 | 示例 | 说明 |
|---|---|---|---|
| **S** | 官方一手 | 美团/点评商家自页、工商登记（天眼查企业版）、Apple 地图官方 POI | 平台直采/官方登记 |
| **A** | 权威聚合 | city8、城市惠、图吧公交（地图 POI 聚合）、高德排行榜 | 结构化 POI 数据，反爬但可信 |
| **B** | 二手媒体 | 花长廊/花浪漫（聚合站，曾有误收）、花好网店页、花柚 | 平台店页/聚合列表，需交叉 |
| **C** | 低质/待核 | 顺企网名录（工商聚合）、4huadian 加盟页、单一博主 | 登记地址/宣传地址，实体性弱 |

**评级规则**（沿用 source-trust 逻辑，新增 POI 模式）：
- 单店 ≥2 个 A/S 源一致 → 高置信（如御花房 ZJX-07 双源）
- 单 A 源 + 地址精确 → 中-高（如花厝里 YX-03 三源）
- 单 B 源 → 中（如花长廊 C 组整组）
- 工商登记型（注册地址非实体店）→ 中-低/低（佛山 FS-07~12、念花舍 ZJX-10）
- **清洗反例**：木可花房（B 源误收为花店，实为餐饮）→ 记入 notes 并作为交叉验证警示

**实现**：`dsh-tools source-trust` 增加 `--poi` 模式或新增 `poi-grade` 子命令，输入来源列表 → 输出评级 + 置信度建议。

## 4. 采集与更新管道

### 4.1 管道（对齐论文落链 5 步）

```
poi-scan（商圈重采） → poi-fetch（单店核验） → poi-import（入库） → poi-audit（一致性自检） → poi-report（回报）
```

| 阶段 | 工具 | 说明 |
|---|---|---|
| 商圈重采 | 子代理 web_search+聚合站 | 新增商圈/重采已有商圈（复用 v2 方法） |
| 单店核验 | 电话/到店/平台 App 内搜店 | is_verified=1；在营状态确认 |
| 入库 | dsh-tools poi-import（CSV→SQLite） | 幂等 upsert，来源拆分 |
| 审计 | dsh-tools poi-audit | CSV/SQLite/md 三处一致 + 缺失检查 |
| 回报 | bb-write + 黑板 | 增量变更入 data/investigate/ |

### 4.2 更新机制

- **快照模式（默认）**：每次商圈重采生成新快照文件，审计比对增量（新增/停业/改名）
- **增量模式（P1）**：pois.updated_at + in_operation 字段驱动，仅更新变更行
- **时效**：商圈重采 2-4 周周期（成本治理下默认手动，可挂 plist 但默认禁用，同 paper-sync）

### 4.3 数据质量护栏

- 在营状态**一律待核**直到人工/平台核验（in_operation=NULL）
- C 组（单 B 源）仅作扫街名单，禁止对外断言
- 工商登记型必须标注「注册地址非实体店」
- 反爬即停标注（花长廊 acw_sc__v2 / 天眼查登录墙 / 顺企网 429）

## 5. 与现有体系衔接

| 体系 | 衔接方式 |
|---|---|
| **source-registry.json** | 新增 3+ 条 LBS 数据源登记（city8/花长廊/顺企网/电话邦等，type=poi-aggregator） |
| **data-sources.md** | 新增「LBS/POI 数据源」章节（含评级规则） |
| **source-trust** | `--poi` 模式：按来源类型评级（§3） |
| **rust-tools** | 新增 poi.rs（query/import/audit/stats）+ 注册 main.rs；版本 v1.24.0 |
| **papers-db 模式** | 平行建 `~/poi-db/pois.db`；双写（CSV 人读 + SQLite 机读 + md 文档） |
| **KB 向量化** | 新建 knowledge base `poi-cache`，pois 关键字段逐条索引 |
| **花店 AI 运营官** | POI 底表 API（按商圈/置信度/电话可拨过滤）；获客名单导出；竞品对标（同商圈价格带/品类分布） |

## 6. 实施路线（按成本治理，手动推进）

| 阶段 | 内容 | 产出 | 状态 |
|---|---|---|---|
| **P0-1** | 建库脚本 + SQLite schema + 73 家导入 | `~/poi-db/pois.db` + import 脚本 | 待执行 |
| **P0-2** | dsh-tools poi 子命令（query/list/stats/import/audit） | rust-tools v1.24.0 | 待执行 |
| **P1-1** | source-trust --poi 评级 + 置信度规则 | source-trust v1.2.0 | 待执行 |
| **P1-2** | source-registry + data-sources.md 登记 LBS 源 | registry +6 条 | 待执行 |
| **P1-3** | poi-audit 三处一致性（CSV/SQLite/md） | 审计 ok | 待执行 |
| **P2-1** | KB poi-cache 向量化 | KB 1 个 | 待执行 |
| **P3-1** | 运营官 POI API / 获客名单 / 竞品对标 | 对接文档 | 待执行 |

## 7. 风险与边界

1. **数据时效**：POI 在营状态是最大不确定项——旅游商圈（北京路/祖庙）流动性高，必须核验后使用
2. **主站反爬**：大众点评/美团/高德主站不直采（合规），聚合站数据有滞后
3. **坐标缺失**：仅窈窕花房等少数店有坐标，LBS 距离查询精度受限（可后续用地址→geocode 补，但需外源服务）
4. **成本治理**：默认手动更新，不挂定时（同 paper-sync 策略）
5. **评级主观性**：S/A/B/C 来源评级是规则初版，需用清洗反例持续校准

---

*规划：数据调查员 · 2026-09-01 · 待用户确认后进入 P0 实施*
