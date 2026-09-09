# 跨设备对账协议 v2（泛化版 · 适用 mac-mini/MBP/i9/未来节点）

> 版本: v2.0 · HR 司库 · 2026-09-06 · 经验来源: MBP 对账 + i9 对账（两次实战）
> 适用: 任何两个 DSH 节点间的规则/工具/教训/资产全量对齐

═══════════════════════════════════════

## 一、对账对象（5 类）

规则(RULES/rules.json) / 工具(tools-registry) / 教训(repair-reports/err-net) / 资产(registry) / 状态(心跳/版本)

## 二、对账算法（三阶段）

1. **盘点(diff)**: 发起方产出对账清单 → 双方 diff(规则 id/工具版本/教训模式/资产清单/心跳)
2. **分级**: absorbable(应吸收) / sync-only(仅同步) / reference(仅参考)
3. **登记**: 吸收→规则账本+registry；同步→tools-registry；参考→镜像索引

## 三、协议流程（含 v2 回报通知闭环 ★关键修复）

1. 发起方写请求单 → 黑板 notes/<目标>/hr-reconciliation-request-<date>
2. agent-msg 通知目标「看黑板 <key>」
3. 目标方处理 → 回报写 notes/<目标>/reconciliation-reply-<date>（JSON）
4. **★ 回报方必须 agent-msg 反向通知发起方「已回报, 看黑板 <reply-key>」**
   （v1 缺陷: 回报写键后无反向通知 → 双方互等 26-27 秒甚至更久）
5. 发起方读回报 → 逐项吸收登记 → agent-msg 确认闭环
6. 双向同步变更 → 周周期或事件触发

## 四、回报格式(JSON 标准)

\`\`json
{
  "from": "节点名",
  "to": "发起方",
  "ts": "<ISO时间>",
  "type": "reconciliation-reply",
  "rules": {"local": "...", "version": "...", "unique_ids": [...]},
  "tools": {"dsh_tools": "v...", "node_bridge": "v...", "guard": "..."},
  "lessons": {"unique": [...], "patterns": [...]},
  "oncall": {"owner": "...", "status": "..."},
  "pending": ["..."],
  "diff_requests": ["需要发起方处理项"]
}
\`\`json

## 五、泛化要点(本次实战教训)

1. **回报通知闭环**(v2 新增): 回报方完成即 agent-msg 通知, 勿只写键等对方发现
2. **发起方主动轮询**: 发出请求后主动查回报键(对方可能秒回)
3. **黑板 JSON body**: 所有写入用 JSON(R003 固化), 禁纯文本/BOM
4. **消息域规范**: 给谁的消息写谁的域(notes/i9/ notes/mbp/)
5. **工具分发验证**: 同名文件≠同版本, 分发后验证编译时间/写入行为
6. **错误统一登记**: 跨设备错误 → data/err-net/ 条目化(R-ERR3)

## 六、触发方式

- 周期: 每周一次(各节点上线时)
- 事件: 规则账本版本 bump / 工具族大升级 / 新节点接入 / 异常发生
- 工具: 对账工具化(待建, 可参考 session-rebirth 模式)

---
*对账协议 v2.0 · HR 司库 · 2026-09-06 · 泛化自 MBP+i9 两次实战*
