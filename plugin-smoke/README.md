# DSH 插件冒烟测试工具链（模板 v1.2 · QA #005 验收通过）

跨会话协作产物（需求 #5，来源 e032fb77）。用途：插件构建后统一冒烟验证，不依赖人工记忆验证步骤。

## 快速开始

```bash
cp plugins.example.json plugins.json   # 按你的插件改配置
chmod +x plugin-smoke.sh
./plugin-smoke.sh                      # 冒烟全部