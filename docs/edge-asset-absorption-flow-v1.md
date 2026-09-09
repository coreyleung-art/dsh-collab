# 端侧资产吸收流程 v1.0（AI 网盘打包 → 中枢评估）

> 2026-08-29 星桥-mac-mini-协调者 · 用户指示：端侧吸收应「打包整个设计与代码挂 AI 网盘，中枢再做内部评估分析流程」
> 定位：R010 v1.1 补充——从「黑板描述吸收」升级为「网盘实体打包 + 中枢完整评估」

## 一、为什么（本次教训）

i9 回传 dsh-plugin-health-check（pitfall 工具）时，只通过黑板 notes 描述了功能（4 插件/20 工具/31 踩坑），
**中枢没有拿到源码实体** → 只能凭描述判断，无法跑 deploy-check / restart-guard / 选型评估器完整审查。

**规律**：黑板描述是「摘要」，评估需要「实体」——端侧资产必须打包挂网盘，中枢拉实体评估。

## 二、AI 网盘 = rust-genebank

- **定位**：独立 AI 网盘服务器（注册层+存储层+检索层，零 token）
- **端口**：8801（mac-mini 常驻）
- **API**：
  - `PUT /api/v1/genes` — 注册基因（manifest：chromosome/gene_id/name/mutation/size/ts）
  - `PUT /api/v1/genes/<id>/file` — 文件上传（X-Offset 续传）
  - `GET /api/v1/registry` — 基因登记查询
  - 染色体 6 类：models/datasets/corpora/knowledge/artifacts/recipes
- **端侧取件**：i9/MBP 经 Tailscale 访问 `http://100.120.203.20:8801`

## 三、吸收流程（五步）

```
【端侧打包】
1. 端侧（i9/MBP）把要吸收的资产打包：
   - 设计文档（README/设计说明/评估建议）
   - 完整源码（项目目录/插件目录）
   - 版本信息（git tag/CHANGELOG/依赖清单）
   → 打 tar.gz：<asset-name>-v<ver>-full.tar.gz

【挂网盘】
2. 上传 genebank：
   - curl PUT /api/v1/genes（注册 manifest，chromosome=artifacts）
   - curl PUT /api/v1/genes/<id>/file（上传 tar.gz）
   → 回报黑板：gene_id + 资产摘要

【中枢拉取】
3. 中枢收到黑板回报 → 从 genebank 拉取 tar.gz → 解压到本地暂存

【内部评估（R010 完整流程）】
4. 中枢执行评估链：
   - deploy-check（依赖/API 漂移/bundles/语法）
   - restart-guard（type:module/ESM 导入/符号链接/模块+apply 加载实测）
   - 选型评估器 tech-choice-evaluator（独立 vs 纳入已有 vs 复用）
   - 与现有资产对比（插件评估 plugin-eval-cli）
   → 输出评估报告：定位/理由/整合方案

【决策落地】
5. 评估报告 → 用户决策 → 整合/吸收/复用 → 登记 registry + 落链 KB
```

## 四、命令速查

```bash
# 端侧打包
tar -czf dsh-plugin-health-check-v0.1.0-full.tar.gz \
  -C ~/dsh-plugin-health-check . \
  -C ~/dsh-collab/designs health-check-design.md

# 端侧注册 + 上传（genebank）
curl -X PUT "http://100.120.203.20:8801/api/v1/genes" \
  -H "Content-Type: application/json" \
  -d '{"chromosome":"artifacts","name":"dsh-plugin-health-check","mutation":"v0.1.0","size":<bytes>}'
curl -X PUT "http://100.120.203.20:8801/api/v1/genes/<gene_id>/file" \
  --data-binary @dsh-plugin-health-check-v0.1.0-full.tar.gz

# 中枢拉取
curl -s "http://127.0.0.1:8801/api/v1/genes/<gene_id>/file" -o /tmp/absorb/asset.tar.gz
tar -xzf /tmp/absorb/asset.tar.gz -C /tmp/absorb/

# 中枢评估
dsh-tools deploy-check <插件目录>
dsh-tools restart-guard <插件目录>
python3 scripts/tech-choice-evaluator.py <候选> --check-kb
```

## 五、与现有机制衔接

| 环节 | 机制 |
|------|------|
| 端侧打包规范 | 本文档（设计+源码+版本） |
| 传输通道 | genebank（AI 网盘，零 token）|
| 中枢评估 | deploy-check + restart-guard + 选型评估器 + plugin-eval |
| 决策 | 用户批准（R010）|
| 沉淀 | registry 登记 + KB 落链 + 踩坑档案 |

## 六、规则账本

- R010 v1.1 补充：端侧资产吸收必须走「打包 → 挂 genebank → 中枢拉取评估」流程，禁止只凭黑板描述评估
- 触发：任何端侧（i9/MBP）向中枢提交设计/代码/工具/插件吸收请求
