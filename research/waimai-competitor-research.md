# 外卖竞品市场调研自动化（任务 C）调研报告

> 调研方式：web_search 中英文共 18 次检索（工具/爬虫/合规/视频流/VLM/开放平台等 6 组关键词），来源交叉验证后收录 22 个。
> 声明：本报告仅用于内部竞品调研（不发布、不转售、不对外公开），不采集个人敏感数据。涉及平台自动化存在合规与账号风险，落地前需经法务/合规评审。

## 调研结论

1. 没有官方"消费者端竞品数据"通道：美团、饿了么的开放平台（ISV/OpenAPI）面向商家自有店铺与履约场景（订单、商品、配送等），不提供竞争对手门店的消费者视图数据。竞品数据只能通过商家端自有数据、Web/App 端采集、第三方数据服务获得。
2. 技术路线可归纳为四类，移动端自动化是与任务 B 衔接最顺的路线：商家端官方数据（合规但只覆盖自家店）；Web 端爬虫（Selenium 或接口逆向，反爬签名强度高，维护成本大）；移动端自动化（uiautomator2 + adb/scrcpy + Appium，可看到消费者端完整视图，配合虚拟定位即可模拟门店周边视角，社区已有 meituan-cli 等参考实现）；视频流采集（直播/短视频录制 + 抽帧 + VLM 内容理解）。
3. 数据采集内容可分四层：门店基础信息、商品明细、排名快照、促销策略。排名与活动是时变数据，必须做定时快照与增量对比，单次抓取无长期价值。
4. 视频流内容理解已具备成熟组件：开源录制工具（DouyinLiveRecorder、StreamCap）+ ffmpeg 抽帧 + 本地可部署 VLM（Qwen2.5-VL / GLM-4.6V）即可实现花艺展示/价格话术/优惠信息的结构化提取，且有 E-VAds 等公开 benchmark 支撑。
5. 合规与风控是最大约束：美团用户服务协议明确禁止机器人、蜘蛛、截屏等程序或设备使用服务；虚拟定位已有被限制账号的真实投诉案例；2025 年最高法典型案例认定电商平台对商品数据享有经营性利益，批量抓取可能构成不正当竞争。结论：方案可行但必须低频率、低权重、仅调研不发布。
6. 落地路线：POC（单店单机）到定期巡检再到竞品周报自动化。建议先做 5 家店、2 周 POC 验证数据质量与账号存活率，再扩大规模。

## 数据采集内容设计

| 数据域 | 字段 | 采集方式 | 频率建议 |
|---|---|---|---|
| 门店基础 | 店名、评分、月售、人均、配送费/时长、起送价、满减标签、距离、营业状态 | 列表页+详情页快照（OCR/UI 树） | 1-2 次/日/店 |
| 商品 | 名称、规格（份/克/ml）、价格、原价、销量、图片、标签（招牌/新品） | 详情页滚动采集商品列表 | 1 次/日 |
| 排名 | 分类页排名、搜索页排名（品牌词/品类词）、榜单（人气榜/好评榜） | 固定关键词搜索+列表位置记录 | 2-3 次/日 |
| 促销 | 满减档位、折扣/第二份半价、会员红包、进店领券、新客立减 | 详情页+活动页快照 | 1-2 次/日 + 活动期加采 |

设计要点：所有字段带采集时间戳与定位坐标；排名用固定关键词脚本化回放；增量比较用商品名/规格做归一化键，价格变动、上下架、满减变化单独记事件表。

## 视频流采集分析

流水线：自动录制（DouyinLiveRecorder/StreamCap 或 ffmpeg 拉流）→ 分段存储 → 抽帧（均匀抽帧 1fps 或关键帧）→ VLM 批量理解 → 结构化 JSON → 汇总入库。

VLM 提示词模板建议输出字段：出现时间、商品名（花束/花材）、展示时长、口播价格/优惠话术原文、画面优惠信息（满减/秒杀/券）、主播动作（展示/包装过程）。本地部署优先 Qwen2.5-VL（7B 级可跑消费级显卡），敏感内容可加 GLM-4.6V 交叉验证。抽帧后先做场景切分（画面相似度）再送 VLM，可省 60-80% token。

## 与任务 B（手机 GUI 控制）的衔接

建议把任务 B 的手机 GUI 控制抽象为采集原语层，竞品调研直接复用：

- 基础能力：open_app、set_location、search、open_store、scroll、screenshot、get_ui_tree（uiautomator2 dump / OCR）；
- 业务原语：collect_store_card、collect_product_list、collect_ranking、collect_promos、record_live；
- 编排：巡检脚本 = 定位切换 → 关键词搜索 → 列表快照 → 进入 TOP N 门店 → 商品/促销采集 → 结果写入队列 → 视频录制任务并发执行。

实现建议：Android 真机/云真机优先（uiautomator2+scrcpy），iOS 用 Appium/XCUITest 成本高、作为二期；定位用系统级 mock（root/ADB）优于第三方分身软件；每次巡检前后截图留痕，便于人工复核与风控回溯。

## 合规与风控

| 风险 | 说明 | 缓解措施 |
|---|---|---|
| 平台协议禁止自动化 | 美团/饿了么用户协议禁止机器人、模拟程序、截屏程序 | 仅内部调研；频率压到最低；不参与薅羊毛/抢单类行为 |
| 账号封禁 | 虚拟定位有真实封号投诉案例 | 专用低权重账号、独立设备、IP 干净、失败降级人工 |
| 接口逆向 | 消费者端接口有签名/风控，逆向本身违反协议 | 优先 UI 自动化而非协议逆向；逆向仅作只读评估 |
| 数据合规 | 平台对商品数据享有经营性利益，批量抓取有判例风险 | 数据不出境、不转售、不公开；周报仅内部脱敏展示 |
| 视频内容 | 直播/短视频可能有主播肖像与版权 | 仅提取事实性商品/价格信息，不保存完整视频副本 |

## 候选方案对比表

| 方案 | 数据覆盖 | 技术栈 | 实现成本 | 稳定性/反爬 | 合规风险 | 适用阶段 |
|---|---|---|---|---|---|---|
| A. 商家端官方数据 | 仅自家店 | 商家版后台导出 / 开放平台 API | 低 | 高（官方渠道） | 低 | 基线校准、自家店看板 |
| B. Web 端爬虫 | 消费者端公开数据 | Selenium/Playwright + 签名逆向 | 中 | 低-中（反爬强） | 高 | 不可用/仅小样本 |
| C. 手机端自动化+虚拟定位 | 消费者端完整视图 | uiautomator2 / Appium / scrcpy + mock 定位 | 中-高 | 中（模拟真人） | 中-高（封号风险） | 推荐主路线（复用任务 B） |
| D. 第三方 SaaS/数据服务 | 视服务商 | 购买 API/报表（九数云、富泰科、魔镜等） | 高 | 未知 | 中 | 快速验证、交叉校验 |
| E. 视频流采集+VLM | 直播/短视频内容 | DouyinLiveRecorder/StreamCap + ffmpeg + Qwen2.5-VL | 中 | 中-高 | 中（版权/肖像） | 内容情报补充线 |

## 推荐路线

主路线 = C（移动端自动化，复用任务 B）+ E（视频流 VLM）补充内容情报；A 做自家店基线；D 仅用于交叉验证，不依赖。

1. 阶段 1 · POC（2 周）：1 台 Android 真机 + uiautomator2/scrcpy + 虚拟定位；5 家目标门店；跑通定位、搜索、列表快照、详情/商品/促销采集，输出 5 份门店 JSON；评估账号存活率与数据完整率（目标大于 90%）。
2. 阶段 2 · 定期巡检（2-4 周）：定时任务每日 2-3 轮巡检；数据入 SQLite/Postgres；实现商品价格/满减/排名变化检测；加入视频录制与抽帧 VLM 摘要。
3. 阶段 3 · 竞品周报自动化（4-8 周）：周报聚合（排名漂移、调价/上新/活动事件流、视频内容要点），接入现有 BI/飞书/企业微信渠道；建立人工复核到自动执行的灰度机制。

## 证据来源

1. 美团外卖商家版用户服务协议 — https://rules-center.meituan.com/rule-detail/816/1
2. 美团用户服务协议 — https://rules-center.meituan.com/m/detail/4
3. 美团开放平台《合规分管理规则》解读 — https://developer.meituan.com/isv/announcement/detail?dockey=anno-all&id=announcement-5026
4. 美团开放平台服务商数据交互整改通知 — https://developer.meituan.com/isv/announcement/detail?dockey=anno-all&id=announcement-1489
5. 饿了么 OpenAPI 文档 — https://openapi-doc.faas.ele.me/v2/
6. 饿了么 OpenAPI 附录（数据模型） — https://openapi-doc.faas.ele.me/v2/appendix/index.html
7. GitHub: oscarka/meituan-cli（UIAutomator2+ADB 控制美团 App） — https://github.com/oscarka/meituan-cli
8. GitHub: ihmily/DouyinLiveRecorder（多平台直播录制） — https://github.com/ihmily/DouyinLiveRecorder
9. GitHub: foanet/LiveRecorder-pandaliver — https://github.com/foanet/LiveRecorder-pandaliver
10. StreamCap 多平台直播流自动录制工具指南 — https://blog.csdn.net/j8267643/article/details/152049294
11. Qwen2.5-VL 技术报告 — https://huggingface.ac.cn/papers/2502.13923
12. E-VAds Benchmark（电商直播视频理解数据集） — https://huggingface.co/datasets/TaobaoTmall-AlgorithmProducts/E-VAds_Benchmark
13. GLM-4.6V 直播带货产品展示分析实践 — https://blog.csdn.net/weixin_36074800/article/details/159139829
14. 腾讯云：爬取美团外卖商家评分与销量实战 — https://cloud.tencent.com.cn/developer/article/2592306
15. 阿里云：Selenium 美团外卖动态数据爬虫方案 — https://developer.aliyun.com/article/1729210
16. Thunderbit：如何抓取外卖配送数据 — https://thunderbit.com/zh-Hans/blog/how-to-scrape-food-delivery-data
17. 富泰科：美团外卖数据采集（第三方采集服务） — https://www.futaike.net/new_cases/11352.html
18. 九数云：美团数据采集软件 — https://www.jiushuyun.com/other/16385.html
19. 袋鼠参谋（美团餐饮商家 AI 决策工具） — https://baike.baidu.com/item/餐饮商家AI决策工具袋鼠参谋
20. 魔镜市场情报（电商数据 SaaS） — https://baike.baidu.com/item/魔镜市场情报
21. 帆软博客：外卖数据分析平台评测 — https://www.finebi.com/blog/article/685a16de28946ecca803a90e
22. 黑猫投诉：美团外卖使用虚拟定位被限制账号案例 — https://tousu.sina.com.cn/complaint/view/17400288187
23. 最高人民法院 2025 年知识产权典型案例（平台商品数据经营性利益） — https://www.acla.org.cn/info/c8513ea830344c639dc3518206a141fb
24. 电商爬虫合规边界白皮书 — https://datasea.cn/go0625622880.html
25. scrcpy+Appium 安卓群控改造实践 — https://blog.csdn.net/paroleg/article/details/131705429
26. GitHub: dockerized-robot-appium-environment — https://github.com/ecureuill/dockerized-robot-appium-environment

噪音排除记录：52pojie 抢红包连点器帖、LINUX DO 领券帖、京东 VPN 软文（灰产/营销向，与竞品调研无关）；多篇 CSDN 采集教程内容同源，仅保留最早且带代码的教程。

## 下一步建议

1. 与任务 B 对接：确认手机 GUI 控制层已提供的能力（adb / uiautomator2 / scrcpy / 坐标点击 / OCR / UI dump），输出采集原语接口清单；若未提供，先补 set_location 与 get_ui_tree 两个基础原语。
2. 合规前置：把仅调研不发布、低频率、专用账号写入项目规范，找法务评审一次，记录风险接受书。
3. 数据模型先行：定义门店/商品/排名快照/促销事件/视频摘要五张表（含 timestamp、location、source_app 字段），先建 SQLite 跑 POC。
4. VLM 选型：本地部署 Qwen2.5-VL（7B）做视频抽帧理解，用 3-5 段目标门店直播视频做标注集验证提取准确率（目标：价格/优惠信息 F1 大于等于 0.85）。
5. POC 验收标准：5 家店 x 3 天连续采集，数据完整率大于等于 90%、账号零封禁、每店每天采集小于等于 3 次；达标后再进入巡检阶段。
