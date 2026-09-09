# concept-dict · 概念数据字典工具

> 版本：v1.0.0 · 属主：HR 司库 · R019 概念精确性纪律落地载体
> R006 九标准：✅ 全达标（插件形态/TCC 自检/CLD 自适应/dsh 版本自适应/文档/版本/日志/落链/CLI）

## 定位
概念精确性纪律（R019）的登记/查证/检查工具——解决「概念混淆」（2026-08-30 特征库事件教训：返图特征库 vs 物品特征库）。

## 命令
| 命令 | 说明 |
|---|---|
| add <概念> --def <定义> --src <来源> [--alias a] | 登记新概念 |
| query <词> | 查证概念（精确/别名/模糊） |
| check <文本> | 用词检查（已登记概念 + 混淆风险） |
| suggest [--dir] | 新概念提取（启发式词频） |
| audit | 字典健康（无来源/无定义） |
| list | 列出全部 |
| selfcheck | TCC 自检 |
| version | 版本 |

## 存储
- ~/dsh-collab/data/concept-dictionary.json（机器可读权威）
- ~/dsh-collab/docs/concept-dictionary.md（人类可读自动生成）
- ~/.dsh/concept-dict.log（统一日志）
- 黑板 data/registry/concept-dict/（可选同步）

## 示例
python3 concept-dict.py add 返图特征库 --def "客服返图提取的客户反馈特征集合" --src "return-photos-extract"
python3 concept-dict.py query 返图特征库
python3 concept-dict.py check "返图特征库与物品特征库需要区分"

## 零 LLM
登记/查证/检查纯规则；suggest 用词频+上下文启发式（非模型）——省 token 符合主线。
