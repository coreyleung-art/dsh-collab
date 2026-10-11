# 跨端通讯规范 · v1.3（单点定稿 · 全端对齐）

> 定稿：星桥（协调者）2026-10-03（v1.3：铁律6「自查不得自指+出包预演」+ §4.2 rsync 陷阱，吸收 MBP 原链路反馈「两代门都不可靠」与 1.5.10 部署实测）｜ 依据：用户顶层要求 + 当日 14 类实测失败清单 + MBP 5 小时 7 包 3 次异常复盘
> 地位：**通讯前择优判断的唯一规范文件**；RULES/portal/即刻协议全部以本文件为准。
> 落地：各端本地 `~/dsh-collab/docs/comm-standard-v1.md`（或经板同步）；本文件改动=协调者定稿→广播→各端更新→门校验。
> 变更记录：v1.1（subject 必带）→ v1.2（§1.3 两板 token 澄清）→ v1.3（铁律6 + §4.2/§4.5/§4.6）。

## 1. 六条铁律（每条对应当日实测事故，违反=失败）

| # | 铁律 | 违反的实测后果 |
|---|---|---|
| 1 | 要求行动的卡必须带 `reply_required: true` + `awaiting: <对端>` | 指针不唤醒 ⇒ 对方不知情 ⇒ 互相等待死锁（11.5h 空档） |
| 2 | 不要求行动的卡必须显式 `notify_only: true`（或 type: notification） | 无声明=语义不明，门不放行 |
| 3 | **跨机写板一律写中枢**（用自己 token 认证头，Authorization: Bearer 或 X-Blackboard-Token，读 ~/.dsh/blackboard-token）→ 由 sync 分发到各端本机板；**本机板只本机写**。两板 token 不同（本机板=各端自持 token，中枢=多端白名单）——不要拿对端 token 写对端本机板 | 只写本机板到不了读中枢的端；flip 后无头=401 静默；拿错 token 写对端本机板 401（实测） |
| 4 | 收件人 `to` 必须完整 session id（跨机消息用节点别名或黑板键，不用对端 session id 直发）；**回复卡写 `notes/<对端节点>/`（如 notes/mac-mini/、notes/mbp/），禁写 notes/<session-id>/ 前缀**（实测该前缀无人监听） | 会话 id 跨机排队 7 天 expired（实测 145 条）；写错前缀=写错板 |
| 5 | 送达状态只信「boarded/双板回读」，不信乐观 delivered；卡片必须带 from（缺 from 由工具补 `restore-<端>` 标记） | 假 delivered 比静默失败更糟；unattributed 不可归属不可去重 |
| 6 | **自查不得自指**：apply() 调用链上的检查禁止再调用 apply()；真挂载冒烟/集成验证只能由 CLI/CI 入口驱动（独立入口+防重入守卫）；**出包前必须真实 boot 预演一次**，发布卡附证据（输出行号/hash），不带证据的「验收达成」视为未验证 | 0.2.8 白名单自检判别力=0（崩溃同刻日志仍写「✅自查通过」）；0.2.9 冒烟挂 apply 链 ⇒ 自递归死循环（无异常行、只烧 CPU，实测 15:58 MBP 刷屏）；「生产首跑=验收」⇒ 5 小时 7 包 3 次异常 |

## 2. 通道择优判断表（通讯前按此选，不是按习惯）

| 场景 | 唯一正确通道 | 禁止 |
|---|---|---|
| 同机会话间 | agent_send（≤200 字；超长落板发指针） | 跨机用 agent_send |
| 跨机要求行动 | bb-card-send 双板 + reply_required + awaiting | 只写单板 / 无 awaiting |
| 跨机纯通知 | bb-card-send + notify_only: true | 假借「通知」压要求行动的语义 |
| 广播（多收件人） | agent_broadcast（同机）/ 黑板 notes/collab/（跨机） | 逐人 agent_send 制造风暴 |
| 跨机信封唤醒 | bus-8791（带 token）+ 内容落板 | 信封塞全文 |

## 3. 发卡字段规范（bb-card-send 门强制）

必填：`key`（首段纯小写字母）、`to`（完整 session id）、`from`（工具自动注入）。
二选一必填：`reply_required: true` + `awaiting: <端>` 或 `notify_only: true`。
`subject` 必带（一眼判断轻重缓急；v1.1 定稿）。
键语法：首段 `[a-z]+`；写后必须回读（200 且内容一致）。

## 4. 包发布规范（部署类动作，防漂移）

1. 依赖完整性：发布前 `node lib/selfcheck.js`（或等价）全绿；清单列出全部依赖包（含 comm-shared 这类兄弟包）。
2. 禁带 `.bak`/旧副本；升级目录先清旧再放新（rsync 加 `--delete` 或先 rm）。★ **rsync `--delete` 必须同时 `--exclude=node_modules`**：发布包不含 node_modules（插件 node_modules 是 profile/runtime 符号链接），裸 `--delete` 会把符号链接目录删掉 ⇒ 部署即崩（MBP 1.5.10 部署实测陷阱）。
3. 版本三处一致：package.json / CHANGELOG / 登记卡。
4. 判据先行：每次交付附「能区分新旧」的判别点（不许拿无判别力的观测当版本判据）。
5. ★ 出包前真实 boot 预演（铁律6）：改包 → CLI 自检（含冒烟三态）→ 负控（注入同类 bug 必 fail exit 1）→ 真实环境预演 boot（如 `dsh web --port 0` 看到启动行；无独立 CLI 的环境以「应用级重启窗口」为预演点并显式声明）→ 才可发。
6. ★ 发布卡附证据而非声明：写「已过 X 门」时附输出行号/hash/片段；对端只做门后复核，「生产首跑即验收」为违规。

## 5. 服务端不变量（板端/总线）

1. SSE 事件必须带递增 `id:`；重连支持 `Last-Event-ID` 有界重放。
2. 写端鉴权：非回环写必须 token（多端白名单/指纹比对）；GET 与 SSE 公开；豁免只按来源（回环/白名单 IP），**不按路径**（i9 过渡期豁免除外，接 token 后移除）。
3. 持久化：audit/snapshot 写失败必须告警（不静默）；目录属主与服务用户一致。
4. 广播单点：每写恰好一次广播（禁止自指订阅回调打回）。

## 6. 门管理（④：不满足不放行）

| 门 | 载体 | 判据 |
|---|---|---|
| 发卡门 | bb-card-send gate.js（v1.1.1 起） | 字段规范 §3 全满足才 PUT（含 subject 必带）；违反=拒绝并给修正提示 |
| 服务端门 | 板端 v0.6.16+ / bus-bridge 白名单+审计 | §5 各项 |
| 部署门 | 各端 selfcheck（同步纯检查）+ 独立冒烟（CLI/CI 驱动）+ 负控 + boot 预演 | §4 各项 + 铁律6 |
| 规范符合声明 | 各端在登记卡声明「符合 comm-standard-v1.x」 | 对齐审计时逐端核对 |

## 7. 变更管理

本文件由协调者单点定稿；变更 → 黑板广播（data/registry/comm-standard-<ver>）→ 各端 48h 内落本地并声明版本。门校验以服务器登记的最新版本为准。

## 附：14 类失败清单 → 本文件条款映射（v1.3 增补两条）

缺 reply_required→§1.1｜缺 awaiting→§1.1｜板选错→§1.3/§2｜缺认证头→§1.3｜跨机会话id→§1.4｜假delivered→§1.5｜SSE无id→§5.1｜卡缺from→§1.5｜豁免按路径→§5.2｜静默失败→§5.3｜包带.bak→§4.2｜rsync无--delete→§4.2｜依赖漏装→§4.1｜多副本漂移→§4.3/§7｜**冒烟挂 apply 链自递归→铁律6/§6**｜**rsync --delete 删 node_modules→§4.2**。
