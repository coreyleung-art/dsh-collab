# R006 v2 · Lean4 约束门灯塔自查（de7b29de）

> ts: 2026-09-06 · R006 十项扩展（第10项 Lean4 约束门）知悉 + 本域工具自查

## 自查结果（灯塔采集域工具）

| 工具 | 结构性门 | 状态 |
|---|---|---|
| scripts/jd-relogin.js | assertPhone 防错登门（registry 自检索+门禁，storeId 无登记/手机号不符→拒） | ✅ 结构门已有 |
| lib/im-send.js | 六道闸门（approval_token HMAC 内容绑定/白名单/频率/告警） | ✅ 结构门已有 |
| lib/report.js accountHint | 取号走 account-registry 自检索（不硬编码） | ✅ 已有 |
| 内存治理 Step1（评审中） | transition 状态机门（方案设计含） | ⏳ C1 门控未过 |

## 差距项

- ❌ 灯塔域工具均未带 `--lean4-check` 自检标志（断言"试一次违规应返回拒"）
- 补建建议：jd-relogin.js 加 `--lean4-check`（模拟错手机号 → 应拒）；im-send 加 dry-run 违规断言

## 结论

R006 v2 生效后，新交付工具带结构门+lean4-check；存量工具按 todo-eval 排期补。灯塔采集域优先补 jd-relogin（已有门，补自检成本最低）。

## 存量补建完成（追加 2026-09-06）

### 1. scripts/jd-relogin.js --lean4-check ✅
- 7 用例全过：店9/店11 正确号过、交叉错号拒、空号拒、未知 storeId 拒、错格式拒
- 纯门断言（assertPhone），离线可跑，不触 Chrome

### 2. lib/im-send.js --lean4-check ✅
- 重构：闸门2(classifyContent)/闸门3(verifyApprovalToken) 抽为纯函数，sendReply 复用（消除复制）
- 7 用例全过：测试标记分类、无token拒、篡改拒、内容绑定失效拒、过期拒、正确token过
- CLI: node lib/im-send.js --lean4-check
- 回归: sendReply 真实路径闸门2 仍拦截（不触 CDP）

### 状态
- 灯塔采集域存量工具 lean4-check 补齐 ✅（2/2）
- 运行 server 需重启加载新 im-send（下次 restart-panel 生效）
