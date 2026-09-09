# CLD 版本管理 · 清单与变更史

> 建立：2026-09-05 · 版本基线：当前部署 = **v0.6.0「运行时修复+治理工具面」**
> 机制：见《版本管理规程》(§六)；工具 guard-cld-release

---

## 一、版本号规约

格式 `MAJOR.MINOR.PATCH[-tag]`
- **MAJOR**：架构性重构/不兼容（如换 runtime、改造壳 spawn）
- **MINOR**：功能增量（新能力/插件/UI 特性）
- **PATCH**：缺陷修复/微调
- tag：`-rcN`（候选）

本机为**自维护构建**（非官方发布），以 `CLD` 壳改动为版本主线，dsh runtime 视为底层依赖（记版本不随改）。

## 二、版本变更史（按时间序）

### v0.0.x → v0.1.0（2026-08 官方基线）
- 官方 app（asar ~87-105KB 时代），Resources 内 4 个原始备份（v0.2.0/v0.3.0 等）
- 现役起点：`app.asar.bak-v0.3.0-20260829`（105036B）

### v0.1.x（09-02~09-04 · 崩溃治理期）
| 版本 | 内容 | asar 锚点 |
|---|---|---|
| 09-02 基线 | 六次 OOM 崩溃排查起点 | (无 asar 改动) |
| v0.1.1 (pre-p0) | 无 asar 改动前 | `app.asar.bak-good-pre-p0` 105918B |
| v0.1.2 (pre-s5) | （S1 看门狗评估窗口） | `bak-good-pre-s5` 138880B |
| v0.1.3 (S1) | child exit 看门狗(traceCrash) | `bak-good-…201121` 138880B |

### v0.2.x（09-04 · 可观测性期）
| 版本 | 内容 | asar 锚点 |
|---|---|---|
| v0.2.0 (S5) | crashReporter+memory-trend | `bak-good-pre-s5fix2` 140354B |
| v0.2.1 (s5fix2) | v8 heap 修复 | 140354B 时代 |
| v0.2.2-5 | reload 自愈实验(s5fix3-5, 已弃用回滚) | pre-s5fix3~5 |
| v0.2.6 (eye) | /shot 截图端点 | `bak-good-…pre-eye` 140354B |
| v0.2.7 (eye2) | +/dom 文本端点 | `bak-good-…pre-eye2` 175113B |
| v0.2.8 (eye3) | v8.getHeapStatistics 修复(当前沿用) | `bak-good-…pre-eye3` 176105B |

### v0.3.x（09-05 · 品牌化期）
| 版本 | 内容 | asar 锚点 |
|---|---|---|
| v0.3.0 (brandtitle) | 窗口标题 BRAND_TITLE + 页面标题拦截 | `bak-good-…pre-brandtitle` 176190B |
| v0.3.1 (no-open) | spawn 加 --no-open(不弹浏览器) | `bak-good-…pre-noopen` 176716B |
| v0.3.2 (domeye) | /dom 增强(styles+hero) | `bak-good-…pre-domeye` 176796B |
| v0.3.3 (domhit*) | 几何+祖链查询(半成品, 演进中) | 现役 179448B |

### v0.4.0（品牌化+eye 完整）
- asar 含：BRAND_TITLE / no-open / /dom(styles+hero+几何?q=) / /shot
- **sha1 `179ab2ea0a552c58` · 179448B**
- 备份锚点：pre-domeye(176796B) 是最接近的上一好版

### v0.5.0（P1 崩溃治理收尾 · 09-05）
- asar 含：崩溃自动重启(crashRestartCount/CRASH_RESTART_MAX=3) / doctor 错峰(ready 后 6s) / 日志归档轮转(.1)
- **sha1 `19294dac461a7ecb` · 181918B**
- 效果：OOM 后自动拉起；9-05 起 0 次崩溃

### v0.6.0（当前 · 运行时修复 + 治理工具面 · 09-05）
- **runtime 补丁**：孤儿 tool_calls 续跑修复（dsh-agent-loop `reconcileOrphanToolCalls`，sha `5092b508`）——重启竞态导致 tool/result 未落盘的会话卡死修复
- **guard 插件 v0.3**：guard_compliance(一键五道闸) + guard_premortem(Q0-Q4) + guard_archaeology(考古)
- **P2-3**：preparedSessionCacheSize 5→2（cordis.patch.yml，待重启生效）
- asar/icon **未变**（sha 19294dac / efabd8a8）——本版为 runtime/配置/插件增量
- 登记：`~/.dsh/cld-release.json` v0.6.0

### my-brand 品牌插件版本史（独立于 asar，v0.5~v0.17）
见 §四。文件 `~/dsh-plugin-my-brand/lib/client.js`（+ .bak-v0x）

## 三、当前部署指纹（v0.6.0）

| 资产 | 指纹/值 | 位置 |
|---|---|---|
| app.asar | sha1 19294dac461a7ecb · 181918B | Resources/app.asar |
| icon.icns | sha1 efabd8a8fa23e23d · 658749B(深色) | Resources/icon.icns |
| my-brand | v0.17(审批dock隐藏) | ~/dsh-plugin-my-brand/lib/client.js |
| 窗口标题 | Corey Leung Distributed Agent Network Platform | main.js BRAND_TITLE |
| hero 文案 | 构建智能·连接思想 / Build Agents Connect Minds | my-brand CSS |
| hero/侧栏 logo | 网络节点图形 | my-brand MyBrandMark |
| 侧栏品牌名 | CLD + 分布式智能体网络工作台 | my-brand MyBrandName |
| dsh runtime | rc.2(@deepseek-ai 0.1.1-rc.2) | Resources/dsh-runtime |

## 四、my-brand 品牌插件版本表

| 版本 | 内容 | 备份 |
|---|---|---|
| v0.5 | React 元素修复(slot shadow 基线) | bak-20260905 |
| v0.6 | hero 官方文字 CSS 隐藏 | bak-v06-hidden |
| v0.7 | hero 文案替换(标语) | bak-v07-slogans |
| v0.8 | logo 蓝底 CLD 字母 | bak-v08-cldletters |
| v0.9 | logo 网络节点图形 | bak-v09-nodelogo |
| v0.10-12 | 英文下移 grid 布局 | bak-v10-11-12 |
| v0.13 | 去标点+下移定稿 | bak-v13 |
| v0.14 | 侧栏品牌名 CLD+英文副标 | bak-v14-en |
| v0.15 | 副标改中文 | bak-v15 |
| v0.16 | dock-cards 修复(弃,改隐藏) | bak-v16 |
| **v0.17** | 审批 dock 隐藏(当前) | (现役) |

## 五、图标版本

| 版本 | 文件 | 状态 |
|---|---|---|
| 官方原版 | icon.icns.bak-…pre-cld (241405B) | 备份 |
| 深色版(当前) | icon.icns · efabd8a8… 658749B | 在用 |
| 浅色版 | (生成过未留档, 可从 Downloads mockup-light 重建) | 需时重建 |

## 六、版本管理规程（工具 guard-cld-release）

```
guard-cld-release status          # 现役指纹: asar/icon/my-brand/runtime + 距上个好版
guard-cld-release tag <ver> --note "…"   # 给现役打语义版本标(写 ~/.dsh/cld-release.json)
guard-cld-release history         # 版本史(本清单对应)
guard-cld-release rollback <ver>  # 回滚 asar 到某版本备份(先备份当前)
guard-cld-release verify          # 全资产指纹核对
```
**部署纪律**：每次改 asar/插件/图标 →
① 先 `guard backup`(已自动记时间戳) ② 改完 `tag` ③ 本清单 §三 更新指纹。

**回滚要点**：asar 备份命名 `…bak-good-<时间戳>-pre-<特性>`，回滚 = 把对应备份 cp 回 Resources + adhoc 重签 + 重启；my-brand 用 `.bak-v0x`；图标 `icon.icns.bak-*`。

---

*清单 v1.0 · 2026-09-05 · 与 ~/.dsh/cld-release.json + guard-cld-release 工具配套*
