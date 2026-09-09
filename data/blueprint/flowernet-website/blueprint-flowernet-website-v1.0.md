# blueprint:flowernet-website · 初蘅官网 · v1.0

> 生成：bb-blueprint-create.py · 2026-09-02T13:16:43 · 三件套纪律（文档/代码/依赖）
> 状态：active · 门禁：① 官网骨架上线 ② 内容运营跑通 ③ 流量导流生效（对接私域）
> 依据：待 i9 扫描确认（flowerclaw.meetfunbp.com 可能为 ERP 域名，官网需单独确认）

## 〇、BP-9 元信息

| 字段 | 值 |
|------|-----|
| id | flowernet-website |
| name | 初蘅官网 |
| version | v1.0 |
| mainlines | {"brand": "品牌展示（初蘅东方美学/守白高定/品牌故事）", "content": "内容运营（公众号/小红书联动/活动展示）", "traffic"... |
| stages | [{"id": "fws1", "name": "官网骨架", "stage": "1.0", "status": "todo", "substages": [... |
| works | [{"owner": "i9 扫描确认中", "stage": "fws1-1", "status": "todo", "work": "官网现状确认（域名/技... |
| gate | ① 官网骨架上线 ② 内容运营跑通 ③ 流量导流生效（对接私域） |
| status | active |
| ts | 2026-09-02T13:16:43 |

## 一、主线

- **brand**：品牌展示（初蘅东方美学/守白高定/品牌故事）
- **content**：内容运营（公众号/小红书联动/活动展示）
- **traffic**：流量入口（SEO/搜索/平台导流）

## 二、阶段与子阶段

### 1.0 官网骨架 [todo]
- fws1-1 品牌页 [todo] — chuheng-website 已确认（i9 E 盘）；品牌页待盘点
- fws1-2 产品展示 [todo] — 节日花束/周边/案例

### 2.0 内容+流量 [todo]
- fws2-1 内容运营 [todo] — 公众号/小红书联动/活动专题（教师节等）
- fws2-2 流量导流 [todo] — SEO/搜索/平台导流（私域入口）

## 三、工作项（works）

| 状态 | 工作 | owner | stage |
|------|------|-------|-------|
| todo | 官网现状确认（域名/技术栈） | i9 扫描确认中 | fws1-1 |
| todo | 品牌内容资产（初蘅/守白故事） | 明鉴/拾光 | fws1-1 |

## 四、依赖关系（relations）

- **parent**：flowernet

## 四b、自动化开关锁（R027 + Lean4 逻辑锁）

（无自动化开关声明——非 AI 自动化阶段或待补）

## 五、门禁链

① 官网骨架上线 ② 内容运营跑通 ③ 流量导流生效（对接私域）

---
*blueprint:flowernet-website · v1.0 · 三件套纪律落盘*
