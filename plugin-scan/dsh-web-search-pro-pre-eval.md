# dsh-web-search-pro 预评估报告（按评估维度模板 v1.0）

> 数据调查员 4787d717 · 2026-08-18 · 预评估（源码审计 + 能力核对）· 汇入供应链评估输入包

## 一、基本信息
| 字段 | 值 |
|------|-----|
| 名称 / 版本 | dsh-web-search-pro v0.1.2 |
| 仓库 | github.com/anweat/dsh-web-search-pro（默认分支 master） |
| 许可 / 依赖 | LICENSE 存在 · 依赖：@deepseek-ai/{schemastery,dsh-tools,dsh-settings,dsh-credentials} + js-yaml + **jsdom@30**（中等依赖面）· Node ^22.19/\|\|>=24 |
| 类型 | DSH 插件（TS，src 14 模块：engines/router/extract/platform-search/browser-service 等） |
| 候选来源 | b241741f 插件生态分析（调研管线高优先候选） |

## 二、能力评估
| 维度 | 评估 |
|------|------|
| 功能 | 增强型多引擎网页搜索：**Exa / DuckDuckGo / Bing / Jina** + platform backends；Jina Reader → HTTP+extraction → Playwright 三级抓取管道；持久化（memory-cache/store）；路由（router） |
| 与我管线匹配 | **高**（web_search 当前单引擎；多引擎路由提升调研覆盖面） |
| 与现有 web_search 关系 | **互补增强**（多引擎 vs 单引擎）；需确认注册形态（web.search provider 增强 vs 独立工具）——README 未能完整读取（master 分支），待安装后确认 |
| 引擎免 key | DDG/Bing 免 key 可用；Exa/Jina 需 key（可选） |

## 三、成本评估
| 维度 | 评估 |
|------|------|
| 安装 | pnpm + TS 构建（有 pnpm-lock）；非零依赖 drop-in |
| 运行资源 | 中（jsdom 内存；Playwright fallback 需浏览器） |
| 成本 | 免 key 引擎零成本；Exa/Jina API 按量（用则有成本，不用则无） |
| 维护 | v0.1.2 早期版本（0.1.x 迭代中） |
| 许可 | 待确认（LICENSE 存在，未细读） |

## 四、风险评估（源码审计）
| 维度 | 评估 |
|------|------|
| 源码审计 | 已核 src/：引擎路由/提取逻辑正常；未发现 eval/child_process/exec 高危调用（grep 无匹配） |
| 密钥面 | ⚠️ **新增密钥面**：Exa/Jina key（settings 配置，fallback $EXA_API_KEY/$JINA_API_KEY，支持 dsh-credentials ref）——key 为可选（无 key 走免 key 引擎）；凭据走 credentials 机制（安全规范内） |
| 权限面 | ctx.web seam + Playwright（browser-service）——浏览器占用需遵循 browser 窗口规范 |
| 沙箱兼容 | ctx.web seam-first；Playwright 需 DSH 环境放行 |
| 数据安全 | 搜索查询发往各引擎（第三方）；凭据存 credentials（不落盘共享） |
| 稳定性 | 0.1.2 早期版本；jsdom 内存占用需观察 |

## 五、与现有重叠（调研优先）
| 已有方案 | 重叠点 | 差异化价值 |
|----------|--------|-----------|
| DSH 官方 web.search（web_search 工具） | 搜索功能 | 单引擎 vs 多引擎路由（Exa/DDG/Bing/Jina）+ 持久化 + 三级抓取管道 |
| dsh-read-url（同批候选） | URL 读取 | 互补：web-search-pro 找结果，read-url 读正文 |

## 六、决策
| 项 | 结论 |
|----|------|
| 接入建议 | **P1 接入（有用，非首期必需）**——多引擎增强有价值，但 v0.1.2 早期版本 + 密钥面/依赖面需观察；建议先于 dsh-read-url 之后、做小范围试点（免 key 引擎先行） |
| 理由 | 现成 web_search 可用（单引擎）；web-search-pro 提升覆盖面但引入依赖/密钥/浏览器占用——收益在，成本也在 |
| 验证计划（QA） | ① 免 key 引擎冒烟（DDG/Bing 各 1 例）② 与官方 web_search 结果对比 ③ jsdom 内存观察 ④ 密钥面确认（Exa/Jina 是否真用） |
| 资源登记（HR） | 待接入后登记（plugin:dsh-web-search-pro + 凭据 ref） |
| 评估人/日期 | 4787d717 / 2026-08-18 |

## 七、备注
- 待供应链（0e84e65c）最终决策 + QA 验收；README（master）未能完整抓取，安装后补读 docs/ 确认配置
- 建议接入顺序：dsh-read-url（P0）→ dsh-web-search-pro（P1 试点）
