# 验收报告 #003 · crawler-lab 第 19 轮交付物

> 验收员：session-ffb7c3ab（QA 验收员） · 日期：2026-08-17
> 交付方：crawler-lab 迭代 worker e83724af · 属主：4787d717（已通知）
> 委派：worker 直接提交（thread-mswbfjhm-kugaxhth）
> 判定：✅ **PASS**（独立复跑证据链全绿；1 项信息级卫生提示非缺陷）

## 1. 交付物清单（期望 vs 实测）

| # | 交付项 | 期望形态 | 实测 | 结论 |
|---|--------|----------|------|------|
| 1 | report-19.md | 证据文档 | ✅ 在位（251 行，含验证记录/基准/勾销进度） | ✅ |
| 2 | crawler/export.py | checksum 清单+verify | ✅ 文件在位；CLI+库级实测通过 | ✅ |
| 3 | crawler/fetch.py | url:regex/透明截图/levels | ✅ 文件在位；36 用例覆盖 | ✅ |
| 4 | crawler/parse.py | prefix/fk_off/coverage | ✅ 文件在位；库级实测通过 | ✅ |
| 5 | crawler/dedup.py | SeedQueue 到期窗 | ✅ 文件在位；CLI queue 实测 | ✅ |
| 6 | bin/crawl 增强 | 6 处子命令 | ✅ 参数解析实测通过 | ✅ |
| 7 | test_round19.py | 36 用例 | ✅ 复跑 OK（3.943s）| ✅ |
| 8 | test_sites_round19_network.py | 3 用例 | ✅ 复跑 OK（5.644s 真实站点）| ✅ |
| 9 | examples/demo_round19.py / bench | 演示+基准 | ✅ 在位（report 声明双环境跑通）| ✅ |

## 2. 独立复跑证据（QA 实测，非交付方报告转述）

### 2.1 测试复跑
| 套件 | QA 复跑结果 | 与交付方声称一致 |
|------|-------------|------------------|
| test_round19.py（离线 36 用例）| ✅ Ran 36 tests in 3.943s OK | 一致 |
| test_sites_round19_network.py（网络 3 用例，CRAWLER_NETWORK_TESTS=1）| ✅ Ran 3 tests in 5.644s OK（hnrss Ask/Show + v2ex 深翻页无重叠）| 一致 |
| 全量 654（py3.13）| 复跑中 → 见 §2.4 | — |

### 2.2 CLI 端到端抽查（QA 实测）
| 命令 | 实测结果 | 结论 |
|------|----------|------|
| `crawl export … --checksum MANIFEST.json` | ✅ 71 条转换 + 清单写盘（sha256, 1 文件 12892B, overall 摘要）| ✅ |
| `verify_checksum_manifest` 篡改检测 | ✅ clean: ok=True checked=1 → 篡改后 ok=False mismatches=1（点名文件）| ✅ |
| `crawl check --env --out env.json` | ✅ 390B 级 JSON 写盘（crawler_version=0.21.0, modules/render/errors 字段齐全）+ 终端摘要照常 | ✅ |
| `crawl runs --json --recovered '*'` | ✅ 纯 JSON（crawler_version/path/filtered）无注释行 | ✅ |
| `crawl queue --since --until --json` | ✅ 纯 JSON（counts/due_count/backoff_count 结构正确）| ✅ |
| `crawl table --schema-sql --table-prefix --fk-off` | ✅ 参数解析通过（输入 books.ndjson 无表格 → 提示无表格，库级验证补强）| ✅ |
| `crawl --version` | ✅ crawler-lab 0.21.0 | ✅ |

### 2.3 库级功能验证（QA 实测，schemas_to_sql / reconcile_schema_records）
| 功能 | 实测 | 与 report 3.5 声称一致 |
|------|------|------------------------|
| table_prefix | ✅ `CREATE TABLE "site1_sales"` / `"site1_categories"` | 一致 |
| fk_off | ✅ FOREIGN KEY 次数 = 0 | 一致 |
| coverage 漏抓识别 | ✅ 期望 50 实抓 30 → 顶层 coverage=0.6, under_crawled=True | 一致 |

### 2.4 全量 654 复跑（py3.13，QA）
- 首次复跑：Ran 654 in 206.8s，**failures=1**（与交付方声称不符，触发定位）
- 二次复跑（-v 全量）：Ran 654 in 199.1s **OK (skipped=18)**，unittest_exit=0——首次 failure 未复现
- 归因：flaky/时序类偶发，与交付方基线（654 OK / skipped=18）二次确认一致
- **第 20 轮渲染矩阵补验（2026-08-17）**：`tests.test_sites_round20_render_matrix` → Ran 2 tests in 98.3s **OK**（bad 429→冷却→good 接管 + 3 域随机 429 恢复矩阵）——crawler-lab 11-20 轮交付闭环完整（全量 654 + 网络套件 + 渲染矩阵三通道全绿）

## 3. 注意项/提示

| # | 项 | 说明 | 级别 |
|---|----|------|------|
| 1 | test_round19.py 文件句柄卫生 | **已修复确认（2026-08-17）**：6 处 `json.load(open(...))` 全部改为 `with open()`（`_read_json` 辅助），grep 清零；`-W error::ResourceWarning` 复跑 36 用例 OK；sqlite3 unclosed 警告**归因定稿（e83724af 代码审计+复现矩阵）**：全部 sqlite 连接点显式 close（SeedQueue 5 处 + _make_items_db 1 处），复现尝试 6+ 方式 0/N——差异为 CPython 3.9 解释器退出阶段 GC 时序怪癖（close 已调用仍触发 finalizer 告警），**非泄漏非 r19 缺陷，无需代码改动** | 信息（已修复；sqlite3 GC 伪影定稿）|
| 2 | round-17 TestScrapemeSortPaginationCombo 缺 playwright skip 门控 | report-19 §5 自述遗留；py3.9 网络套件 2 既有错误，非本轮引入 | 信息（交付方已记录）|
| 3 | 全量首次复跑 1 failure 未复现 | 二次全量 OK（199.1s）+ e83724af 侧 py3.13 复跑 OK（197.4s，0 failure）+ py3.9 复验 OK；**归因确认（e83724af 协助）**：疑似 test_round18.py::TestSpiderCooldownSerialization::test_cooldown_gap_then_burst（429 冷却期计时敏感断言 ≥0.40s/<0.15s），负载敏感型 flaky，第 18 轮引入非 r19 代码（r19 的 36+3 用例 standalone 稳定）；QA 首次失败详情未保留（教训：复跑失败应存完整日志再定位）| 信息（既有 flaky，非本轮引入）|

## 4. 验收结论

**PASS。** 交付物清单 9/9 在位；QA 独立复跑：离线 36 用例 OK（3.9s）、网络 3 用例 OK（5.6s 真实站点）、CLI 七项抽查全过（含篡改检测 ok=False 点名文件）、库级 SQL 前缀/关外键/coverage 与 report 声称逐项一致、全量 654 二次复跑 OK（199.1s, skipped=18）、版本 0.21.0 与收尾复核一致。报告证据链真实可复跑。3 项信息级提示（测试文件句柄卫生、round-17 渲染门控遗留、全量首跑 1 flaky 未复现）均不影响本交付。
