# blueprint:mingjian-toolchain · 明鉴交付工具链（工具维度·内容交付的方法固化） · v1.0

> 生成：明鉴 v3 · 2026-09-10 · 三件套纪律（文档/代码/依赖）
> 状态：active · 门禁：工具可用性（每工具须有实测证据才计入）
> 依据：本蓝图汇总 **2026-09-09 ~ 09-10 花联网对外材料项目**中提炼出的交付工具链。工具实体在 `~/dsh-collab/scripts/` 与 `~/relationship-graph-app/gallery/`，本蓝图作索引与关系承载。
> ⚠️ 数据口径：全部工具均有自测证据（见工具链索引「各工具实测证据」节）；未经实测的不计入。

---

## 〇、BP-9 元信息

| 字段 | 值 |
|------|-----|
| id | mingjian-toolchain |
| name | 明鉴交付工具链（内容交付的方法固化） |
| version | v1.0 |
| purpose | 把「两天里踩过的坑」固化成**交付前必跑的检查**，让同类错误不再依赖人的记性；承载工具、SOP、原则三层资产 |
| mainlines | {"scan": {"name": "一致性线", "desc": "一事实多载体 → 全载体扫描"}, "verify": {"name": "验证线", "desc": "交付前逐字节比对 + 界面三重验证"}, "review": {"name": "审查线", "desc": "多视角红队 + 逐单元语义审查 + 立场 16 项 + 受众分层"}, "orchestrate": {"name": "编排线", "desc": "11 步交付链一条命令"}, "secure": {"name": "安全线", "desc": "真加密门禁 + 口令槽位管理 + 凭据纪律"}, "decide": {"name": "决策线", "desc": "四跑法标准框架 + 六维打分"}} |
| stages | [{"id":"tc-s1","name":"P0 三个（扫描/验证/红队）","status":"done"},{"id":"tc-s2","name":"P1 补完（单元审查/界面验证/受众检查/P16）","status":"done"},{"id":"tc-s3","name":"P2 编排（四跑法框架/交付链）","status":"done"},{"id":"tc-s4","name":"插件化（工具入 CP / 凭据防火墙）","status":"todo"}] |
| works | [{"work":"TOOLCHAIN-INDEX-v1（10 工具+3 SOP+8 原则）","status":"done","owner":"明鉴"},{"work":"PROCESS-ASSETS-INVENTORY-v1（12 环节盘点+泛化方向）","status":"done","owner":"明鉴"},{"work":"LESSONS-2026-09-09-10（认知错误9+技术错误7）","status":"done","owner":"明鉴"},{"work":"PASSCODE-SLOTS-AUTHORITATIVE（槽位表+凭据纪律）","status":"done","owner":"明鉴"},{"work":"工具入 CP","status":"pending","owner":"待用户裁"},{"work":"凭据防火墙","status":"pending","owner":"待用户裁"} ] |
| gate | 每个工具须有**自测证据**（实测输出）方计入；仅有设计未实测的不入册 |
| status | active |
| ts | 2026-09-10 |

## 一、主线（六条）

1. **一致性线**：一个事实有多个载体（正文 / 图表 JS 字符串 / 派生版 / 生成的产物），改一处漏多处。工具：`consistency-scan.py`。
2. **验证线**：只看 HTTP 200 会漏掉「服务的是旧版本」；一个 `}` 缺失会让整个样式表静默失效。工具：`verify-deploy.py`（逐字节）+ `verify-ui.py`（渲染/哈希/computed 三重）。
3. **审查线**：单视角有盲区；关键词搜索漏报率高。工具：`red-team.py`（多视角）+ `unit-review.py`（逐单元）+ `stance-auditor.py`（16 项）+ `audience-check.py`（受众分层）。
4. **编排线**：11 步交付链全靠手敲。工具：`deliver.py`。
5. **安全线**：前端门 ≠ 访问控制。工具：`encrypt-gate.py`（AES-256-GCM 真加密）+ 口令槽位表 + 凭据纪律。
6. **决策线**：四跑法缺标准对比框架。工具：`runfour.py`。

## 二、工具清单（10 个 · 全部有实测证据）

| # | 工具 | 主line | 行数 | 位置 |
|---|------|--------|------|------|
| 1 | consistency-scan.py | scan | 412 | scripts/ |
| 2 | verify-deploy.py | verify | 282 | scripts/ |
| 3 | red-team.py | review | 1210 | scripts/ |
| 4 | unit-review.py | review | 782 | scripts/ |
| 5 | verify-ui.py | verify | 657 | scripts/ |
| 6 | audience-check.py (+audience-matrix.json 12 规则) | review | 247 | scripts/ |
| 7 | stance-auditor.py（v1.4 · 16 项） | review | 745 | scripts/ |
| 8 | runfour.py | decide | 1084 | scripts/ |
| 9 | deliver.py（11 步编排） | orchestrate | 724 | scripts/ |
| 10 | encrypt-gate.py | secure | 14KB | gallery/ |

**辅助**：stance-derive.py · clean-external.py · export-marker.py · wargame-sim.py

## 三、SOP（三条必跑）

| SOP | 触发 | 命令 |
|-----|------|------|
| SOP-1 全载体扫描 | 改任何数字/口径后 | `consistency-scan.py --facts <facts> --roots <源> <产物>` |
| SOP-2 部署验证 | 每次部署后 | `verify-deploy.py --map <map>` |
| SOP-3 多视角红队 | 重要交付前 | `red-team.py prep <文件> --perspectives platform,math,expression` |

**一条命令跑全链**：`deliver.py run --config deliver.json`（11 步，第 09 步推送恒不自动执行）

## 四、八条原则（事故提炼）

1. **逐行读才叫审查，搜关键词只是检索**（同一份 BP：关键词报 12 项，逐单元审查发现 570 项）
2. **一个事实有多个载体，改一处不等于改完**（只搜源码会漏掉 JS 生成的 HTML）
3. **数字要先问归属，再问数值**（分母/分子/谁做的/什么时候做的）
4. **不要替对方下判断**（「平台不必做」→「平台定规则，我们做执行」）
5. **给对方的材料 = 做什么，不是怎么想**
6. **授权必须来自授权人本人**（否则闸门形同虚设）
7. **前端门 ≠ 访问控制**（真防护是内容加密）
8. **取证先于处置**（覆盖是破坏性动作；须标注哪些证据来自处置前）

**另有第 9 条（凭据类特有）**：**谈论凭据本身，就是凭据的复制机制**（4 次复制里 3 次是「为了说明而引用」）

## 五、阶段

### tc-s1 P0 三个 [done]
`consistency-scan` / `verify-deploy` / `red-team` —— 本会话直接踩过的坑

### tc-s2 P1 补完 [done]
`unit-review` / `verify-ui` / `audience-check` / `stance-auditor` P16

### tc-s3 P2 编排 [done]
`runfour`（四跑法框架） / `deliver`（11 步交付链）

### tc-s4 插件化 [todo]
① 工具入 CP（用户待裁）② 凭据防火墙（用户待裁）

## 六、依赖与关系

- **depends_on** blueprint-platform：工具链遵循元层的 BP-9 标准与 `data/blueprint/<id>/` namespace 规范
- **serves** flowernet-jv：工具链服务于花联网对外材料的交付
- **consumed_by** 全部内容交付任务：任何交付都跑这套 SOP

## 七、证据链

| 工具 | 实测证据 |
|------|---------|
| consistency-scan | 抓到 `10-15%` 残留 4 处 + `成都已经做出来的` 2 处；跳过规则全部正确 |
| verify-deploy | 抓到「HTTP 200 但是旧版」；抓到「字节数相同但内容不同」 |
| red-team | 3 视角 prep 13 项校验全命中；merge 去重 + 抓出 82% 疑似抽样 |
| unit-review | 9 单元切分正确；PROMPT.md 17 项自检全过 |
| verify-ui | 坏例报出 `position=static` + 「花括号不平衡 { = 7，} = 6」 |
| audience-check | 同材料：股东 0 越界 / 平台 20 处越界涉 11 条规则 |
| stance-auditor P16 | 该报 6 处全中、零误报；P01-P15 回归 30/30 一致 |
| runfour | compare 五节齐全；空记录 exit=2 并点明「推演没做透」 |
| deliver | 缺工具时不崩溃；退出码记录但继续；汇总标红 |
| encrypt-gate | 明文零命中；新口令 53ms 解出 18.6 万字符；错口令全失败 |

---

*blueprint:mingjian-toolchain v1.0 · 明鉴 v3 · 2026-09-10*
