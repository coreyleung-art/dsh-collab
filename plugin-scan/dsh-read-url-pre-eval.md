# dsh-read-url 预评估报告（按评估维度模板 v1.0）

> 数据调查员 4787d717 · 2026-08-18 · 预评估（源码审计 + 能力核对）· 汇入供应链评估输入包

## 一、基本信息
| 字段 | 值 |
|------|-----|
| 名称 / 版本 | dsh-read-url v0.4.1 |
| 仓库 | github.com/2672243194/dsh-read-url |
| 许可 / 依赖 | MIT（LICENSE 存在）· **零依赖**（Node 20+ built-ins，dependencies: None） |
| 类型 | DSH 插件（JS ESM 单文件 index.js 962 行 + multi-site.mjs/spa.js） |
| 候选来源 | b241741f 插件生态分析（调研管线最优先候选） |

## 二、能力评估
| 维度 | 评估 |
|------|------|
| 功能 | 抓 URL → charset 自动检测 → 正文容器级清洗 → 紧凑文本/Markdown（默认 6000 字符段落对齐截断） |
| 与我管线匹配 | **高**（research-fetch 抓全文需先解决中文站乱码；read-url 直接产出 token 高效正文） |
| charset 覆盖 | ✅ GBK/GB2312（归一为 gbk）/UTF-8/Big5，content-type + meta 双重探测 + UTF-8 mojibake fallback（\uFFFD 检测）——实现已核对（index.js L38-74） |
| 反爬 | ✅ 完整浏览器 UA + TLS（README 实测：百度 https/热搜完整 vs 官方 web_fetch 被中间盒指纹降级） |
| 额外能力 | 会话级缓存 5 分钟 TTL、列表/表格提取、ctx.web seam-first + global fetch fallback、协作超时（exec.signal） |

## 三、成本评估
| 维度 | 评估 |
|------|------|
| 安装 | 零依赖 drop-in（JS ESM） |
| 运行资源 | 低（无服务端/无 API key） |
| 维护 | 0.4.1 活跃；CHANGELOG/THIRD_PARTY_NOTICES 齐全 |
| 许可 | MIT 合规 |

## 四、风险评估（源码审计）
| 维度 | 评估 |
|------|------|
| 源码审计 | ✅ 已核（index.js）：charset 用 Node TextDecoder；**无 eval/child_process/exec/危险调用**；正则驱动正文提取（无外部执行） |
| 权限面 | ctx.web seam（网络层可替换）+ global fetch fallback；无文件系统/命令执行面 |
| 沙箱兼容 | seam-first 设计（与官方 tool-web 同 seam）；需 DSH 沙箱网络放行 |
| 数据安全 | 无凭据/无外传（请求仅目标 URL）；不落盘 |
| 稳定性 | 0.4.1 迭代中；对比表有实测（Baidu 场景） |
| 供应链 | 零依赖树（供应链风险最低） |

## 五、与现有重叠（调研优先）
| 已有方案 | 重叠点 | 差异化价值 |
|----------|--------|-----------|
| 官方 tool-web web_fetch | 抓 URL 转 Markdown | web_fetch 全页转换（20 万字符黑洞）；read-url 正文清洗 + 6000 字符 + charset 修正 + 反爬 UA |
| research-fetch（我的调研管线） | 抓全文 | **互补非重叠**：read-url=读给模型（紧凑正文）；research-fetch=存为资产（Obsidian raw 全量） |
| dshdoc_convert_url | URL 转文档 | 面向文档格式（PDF/Office）；read-url 面向网页正文 |

## 六、决策
| 项 | 结论 |
|----|------|
| 接入建议 | **P0 接入（高价值）**——解决中文站乱码 + token 黑洞 + 反爬降级，直接增强 research 管线 |
| 理由 | 现成方案（web_fetch）不满足（全页/乱码/反爬弱）；read-url 零依赖低风险 |
| 验证计划（QA） | ① 安装后冒烟（GBK 中文站/UTF-8/Big5 各 1 例）② research-fetch 管线集成测试 ③ 与 web_fetch 对比 token 消耗 |
| 资源登记（HR） | 待接入后登记（plugin:dsh-read-url） |
| 评估人/日期 | 4787d717 / 2026-08-18 |

## 七、备注
- 待供应链（0e84e65c）最终决策 + QA 验收；安装遵循「装前查源码」纪律（本次审计可作为审计记录）
- 建议同批评估 dsh-web-search-pro（多引擎路由，P0 次优）
