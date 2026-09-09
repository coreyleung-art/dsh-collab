# 手机 GUI 控制 AI 技术路线调研报告（任务 B）

> 调研日期：2026-08-17 ｜ 调研方法：16 次中英文 web_search（多角度交叉验证）+ 11 个一手/官方来源全文抓取落盘（AppAgent、Maestro、scrcpy、UI-TARS、MobileUse、Anthropic Computer Use、Appium Uiautomator2、X-PLUG/MobileAgent、video-vision-mcp、AutoGLM 等）｜ 目标场景：自动操作外卖消费者端 App（美团/饿了么），切换定位查看周边竞品门店、浏览商品/价格/排名、观看分析直播/短视频流
> 合规声明：本报告仅作技术调研；不收集任何敏感个人数据。涉及电商/外卖平台自动化的任何落地，都必须先做平台规则与法律合规评审（详见「合规边界」）。

## 调研结论

1. **技术栈分四层，各层可独立选型**：视觉理解层（Accessibility 树 / OCR / 截图+VLM / GUI 智能体模型）、交互执行层（adb / Appium / UIAutomator2 / Maestro / XCUITest）、Agent 编排层（LLM 决策循环与工具调用）、多设备管理层（adb 池 / scrcpy / 分布式调度）。任务 B 的核心难度不在单一环节，而在「感知→决策→执行→校验」闭环的稳定性。

2. **Android 优先，双通道感知最稳**：官方推荐路线是「Accessibility 树（uiautomator2 dump XML 层级）为主 + 截图 VLM 兜底」。Accessibility 树定位精确、零推理成本，但对 Flutter/自绘 UI（美团、饿了么均有大量自绘组件）会出现节点缺失；截图+VLM（GPT-4V、Qwen2.5-VL 等）不依赖层级但每步都要 token 成本。工程上应两者结合：树能拿到就用树，拿不到回退到 OCR/截图理解。

3. **GUI 智能体模型已从论文走向开源可用**：AppAgent（腾讯开源，探索-学习范式）、MobileUse（NeurIPS 2025，分层反思，AndroidWorld 62.9% / AndroidLab 44.2%）、UI-TARS（端到端原生 GUI agent，AndroidWorld 46.6 超过 GPT-4o 的 34.5）、AutoGLM（智谱开源，中文手机 Agent）、Clawdbot 类（手机端无 root 常驻助手）。它们的共性问题是**可控性与可观测性弱于规则自动化**，适合做「长尾任务的智能兜底」，不适合做高频确定性采集的主干。

4. **桌面 Computer Use 不宜直接套用到手机**：OpenAI computer use 与 Anthropic computer use 都是桌面优先（截图→鼠标键盘坐标），Anthropic 后续通过 Cowork/远程管理支持手机派活，但移动端原生 GUI 控制仍以 Android/iOS 原生栈更可靠。它们可作 Agent 大脑复用（决策+反思），但执行层必须换成 adb/Appium/Maestro。

5. **多设备管理已有成熟免费方案**：adb 支持多设备并行（adb -s 指定序列号），scrcpy（开源，GitHub 高星）可批量投屏+控制+录屏，社区有 scrcpy-multi-device-controller、go-scrcpy-client 等批处理封装；商业方案（BrowserStack App Automate、AWS Device Farm）成本高、主要面向测试，长期采集场景不划算。

6. **虚拟定位是高风险区，必须标注**：Android 开发者选项的 mock location（允许模拟位置）可被主流 App 检测（美团/饿了么有风控）；root + Xposed/Frida 改定位更隐蔽但违反平台规则且封号概率高，还可能触碰「破坏计算机信息系统」类法律红线。iOS 模拟定位（Xcode 模拟器/开发者模式）仅限自有设备+测试环境。**切换定位浏览竞品本身是平台明令禁止的「虚假定位/薅羊毛」行为，任何落地前必须取得合规结论，且仅用测试账号、低频、只读浏览。**

7. **视频流分析管线成熟**：录制（adb screenrecord 或 scrcpy --record）→ ffmpeg 按秒/关键帧抽帧 → VLM（Qwen-VL / GPT-4V）逐帧或批量分析 → 结构化 JSON（门店、商品、价格、话术）。现成参考：video-vision-mcp（帧提取+视觉分析+音频转写 MCP 服务）。注意直播流时效性（错过无法重放）与内容版权（直播内容属平台/主播权益，采集仅限个人研究样本）。

## 候选方案对比表

| 方案 | 层级 | 平台 | 感知方式 | 执行方式 | 可控性 | 稳定性 | 成本 | 学习曲线 | 备注 |
|------|------|------|----------|----------|--------|--------|------|----------|------|
| adb shell + uiautomator dump | 视觉+执行 | Android | Accessibility 树 | adb input tap/swipe/text | 高 | 高（原生 API） | 低 | 低 | 最底层的确定性方案；自绘 UI 节点缺失时需 OCR/VLM 兜底 |
| Appium + Uiautomator2 driver | 视觉+执行 | Android/iOS | XML 层级+截图 | 标准 WebDriver 协议 | 高 | 高 | 中 | 中 | 生态最全，支持并行 session；配置重 |
| Maestro | 视觉+执行 | Android/iOS/Web | 层级+YAML 流 | 声明式 flow（tap/assertOn） | 高 | 高 | 中 | 低 | 15k+ star，录制回放体验好，适合 POC 快速跑通；底层 iOS 走 XCTest runner |
| XCUITest（XCTest） | 视觉+执行 | iOS | Accessibility 层级 | 原生测试框架 | 高 | 高 | 高（需 macOS+Xcode） | 中 | iOS 侧最稳；Appium/Maestro 的 iOS 端最终也落到 XCTest |
| OCR（Tesseract / PaddleOCR） | 视觉 | 跨平台 | 截图文字识别 | —（辅助） | 中 | 中 | 低 | 低 | 中文场景 PaddleOCR 明显优于 Tesseract；无坐标语义，需配版面分析 |
| 截图+VLM（GPT-4V / Qwen2.5-VL / Qwen-VL） | 视觉 | 跨平台 | 截图理解+grounding | —（决策辅助） | 中 | 中 | 高（每步 token） | 低 | 自绘 UI 的主力兜底；Qwen-VL 可本地部署降成本 |
| UI-TARS | Agent 模型 | Android/桌面 | 纯截图端到端 | 模型直接输出动作 | 中 | 中 | 高 | 中 | 原生 GUI agent，AndroidWorld 46.6；需要 GPU 部署或 API |
| AppAgent | Agent 框架 | Android | 截图+层级探索 | LLM 决策→ADB 执行 | 中 | 中 | 中 | 中 | 开源，先探索学习 App 操作再执行；适合冷启动 |
| MobileUse | Agent 框架 | Android | 截图 | 分层反思+ADB 执行 | 中 | 中 | 中 | 中 | NeurIPS 2025，AndroidWorld 62.9% SOTA；附物理设备工具箱 |
| AutoGLM | Agent 框架 | Android | 截图+界面理解 | 模型直控 | 中 | 中 | 中 | 中 | 智谱开源，中文场景友好，有 Web GUI 封装（AutoGLM-GUI） |
| Anthropic / OpenAI computer use | Agent 大脑 | 桌面为主 | 截图 | 鼠标键盘（桌面） | 中 | 中 | 高 | 中 | 移动端支持有限（Anthropic 有手机远程 Cowork 形态）；可复用作推理大脑 |
| scrcpy + adb 多设备池 | 多设备管理 | Android | 投屏/录屏 | 镜像控制+并行 adb | 高 | 高 | 低 | 低 | 免费开源；社区有 multi-device-controller / go-scrcpy-client 批处理 |
| 录屏+抽帧+VLM（video-vision-mcp 类） | 视频流分析 | 跨平台 | 帧提取+音频转写 | —（分析管线） | 中 | 中 | 中 | 中 | 直播/短视频采集理解的标准做法：record → ffmpeg 抽帧 → VLM 批量摘要 |

**选型速记**：确定性高频采集 → adb/uiautomator2 + Maestro 主干；长尾/异常界面 → Qwen2.5-VL 截图理解兜底；探索型任务 → MobileUse/AppAgent/AutoGLM；设备规模 → scrcpy+adb 自建池，不上商业云真机。

## 推荐路线

目标：**多台安卓手机为主**，自动切定位看竞品门店、浏览商品/价格/排名、观看分析直播/短视频。推荐分层架构：

1. **设备层（POC 2~4 台安卓）**：统一 adb 连接，scrcpy 投屏+录屏；按序列号建设备池，脚本并行派发任务；不 root 起步（先验证 mock location 与风控表现）。
2. **感知层**：uiautomator2 dump XML 为主通道，PaddleOCR 处理自绘文字，Qwen2.5-VL（本地部署）截图理解兜底；统一输出「元素+坐标」结构供执行层使用。
3. **执行层**：POC 用 Maestro（录制 3 条关键路径：切定位→搜周边→浏览商品/直播），逐步迁移到 Appium+Uiautomator2 做并行与动态坐标注入（VLM 输出坐标 → adb input 执行）。
4. **Agent 层**：先用 Python 规则编排（状态机+重试），稳定后再引入 MobileUse/AppAgent 处理异常与未知弹窗；反思/自检机制参考 MobileUse 的分层反思设计，动作级+任务级双重校验。
5. **视频流管线**：scrcpy --record 录屏 → ffmpeg 每秒抽帧 → Qwen-VL 批量分析（门店/商品/价格/排名/话术）→ JSON 入库；直播需值班录制，短视频可批量拉取。
6. **合规护栏（必须）**：仅测试账号、低频只读浏览、不领券不交易不下单、禁止薅羊毛/虚假交易；定位模拟仅用于自家测试设备；上线前完成平台规则与法务评审，评估《反不正当竞争法》与平台协议风险；数据仅内部研究，不对外分发含个人信息的内容。

**POC 建议（2 周）**：第 1 周跑通「1 台安卓 + adb dump + PaddleOCR + Maestro 录制」的浏览闭环，产出 10 张真实页面截图与元素命中率报告；第 2 周扩展 4 台设备池 + Qwen2.5-VL 兜底 + 录屏抽帧分析，验证定位切换与直播流采集，输出稳定性数据（成功率/单任务成本/封号观测）。

## 证据来源（URL 列表）

**论文与官方文档**
- AppAgent: Multimodal Agents as Smartphone Users — https://appagent-official.github.io/ ｜ GitHub: https://github.com/TencentQQGYLab/AppAgent
- MobileUse（NeurIPS 2025）— https://papers.neurips.cc/paper_files/paper/2025/hash/3994410d63ec68ce9a66011a34c9a2c4-Abstract-Conference.html ｜ 工具箱: https://github.com/MadeAgents/mobile-use
- UI-TARS（arXiv 2501.12326）— https://arxiv.org/abs/2501.12326v1 ｜ UI-TARS-2 技术报告: https://arxiv.org/abs/2509.02544
- Anthropic Computer Use 官方文档 — https://docs.anthropic.com/en/docs/build-with-claude/computer-use ｜ 博客: https://claude.com/blog/dispatch-and-computer-use
- OpenAI Computer Use 指南（注意：桌面优先；移动端支持有限）— https://platform.openai.com/docs/guides/computer-use
- OpenPhone: Mobile Agentic Foundation Models — https://www.semanticscholar.org/paper/OpenPhone%3A-Mobile-Agentic-Foundation-Models-Jiang-Huang/b016d838c818bc116852e08e85a2ed309994bbc0

**GitHub 项目**
- Maestro（mobile-dev-inc）— https://github.com/mobile-dev-inc/Maestro
- scrcpy — https://github.com/Genymobile/scrcpy ｜ 多设备控制: https://github.com/BarisSenel/scrcpy-multi-device-controller ｜ go-scrcpy-client: https://deepwiki.com/xmsociety/go-scrcpy-client/6.2-batch-operations
- Appium Uiautomator2 Driver — https://github.com/appium/appium-uiautomator2-driver
- X-PLUG/MobileAgent — https://github.com/X-PLUG/MobileAgent ｜ MobileAgent-Android（无 PC/ADB 的 Android 原生 agent）: https://github.com/GiggleWang/MobileAgent-Android
- AutoGLM（智谱开源）— https://www.zhipuai.cn/zh/research/145 ｜ Web GUI 封装: https://github.com/hilbert-yaa/AutoGLM-GUI
- video-vision-mcp（录屏/视频帧提取+视觉分析+音频转写）— https://github.com/OAMaestro/video-vision-mcp
- Clawdbot 类手机端方案（phoneclaw: 无 root 自动化 Android）— https://github.com/rohanarun/phoneclaw

**行业与合规参考**
- 智谱 AutoGLM 开源报道（36氪）— https://m.36kr.com/p/3590627907863304
- 广州黄埔法院诉前禁令（外卖外挂不正当竞争案例）— http://hpfy.gzcourt.gov.cn/article/detail/2025/12/id/9096796.shtml
- 美团打击抢单外挂（2024 封禁 3 万+账号，佐证自动化风控强度）— http://m.mydrivers.com/newsview/1025077.html
- 人民网评：治理外卖抢单外挂 — https://xinwen.bjd.com.cn/content/s673d9faae4b0840b5f9e2b48.html
- iOS 模拟定位风险参考（第三方 GPS 工具评测，仅作风险提示，非权威来源）— https://www.imobie.com/location-change/safe-gps-spoofer-iphone-guide.htm

## 下一步建议

1. **先跑通最小闭环**（1 台安卓，1 周内）：uiautomator2 dump → PaddleOCR → Maestro 录制「打开美团→切定位→搜周边→浏览门店/商品」脚本，产出页面元素覆盖率报告。
2. **VLM 兜底基准测试**：收集 30~50 张美团/饿了么真实截图，对比 Qwen2.5-VL（本地）、GPT-4V（云端）的元素定位命中率与单步延迟/成本，确定默认模型。
3. **设备池小规模验证**：4 台安卓 + scrcpy + adb 并行任务，测定位切换频率与平台风控阈值（仅测试账号、低频），记录封号/限制观测。
4. **视频流管线**：实现 record → ffmpeg 抽帧 → VLM 批量摘要 → JSON 入库的流水线，先对 3~5 个直播/短视频样本人工标注验证准确率。
5. **Agent 化演进**：规则编排稳定后，接入 MobileUse/AppAgent 处理异常与长尾页面，设计动作级+任务级双层校验与失败重试。
6. **合规评审**：形成书面合规结论（平台规则、账号风险、法律边界）后再考虑任何规模化部署。

## 附：噪音排除记录与合规边界

- **排除**：LINUX DO 等论坛的「美团神卷/虚拟定位薅羊毛」帖（灰产导向、无权威性，仅提示风控存在）；SEO 拼凑站（bestforandroid 等）的定位工具软文（无方法论价值）；36kr 等自媒体对 AutoGLM 的蹭热度报道仅作背景引用，事实以智谱官方发布为准。
- **局限**：各 Agent 框架的基准数字来自论文自测（AndroidWorld/AndroidLab），与美团/饿了么真实 App 表现存在差距，需实测；平台风控策略（定位检测、设备指纹、频率限制）不透明，封号风险只能通过小样本观测估计；iOS 侧成本高，本报告未做深度实测。
- **合规边界**：不采集账号密码/支付凭证/个人身份信息；不领券、不下单、不批量注册；切换虚拟定位浏览竞品数据仅限合规评审通过后的内部研究用途；涉及《反不正当竞争法》与平台用户协议，建议法务前置。
