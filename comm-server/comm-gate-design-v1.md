# 通讯管理 Lean4 逻辑门框架 v1（2026-09-06 · 星桥）

> 目的：把通讯管理从「规则声明」升级为「结构不可绕过的逻辑门」（R006-⑩ Lean4 范式 + Φ9 约束前置）
> 原则：抽纯判定函数 + 生产/自检同源 + --lean4-check 断言矩阵证明门生效
> 范围：所有写黑板/通讯的入口（mac-mini 工具 / i9-bb.py / MBP blackboard-events / 同步层）

---

## 一、域权限矩阵（声明：谁能写什么）

| 域前缀 | 写权（设备） | 写权（协调者） | 读权 | 双写要求 |
|---|---|---|---|---|
| notes/i9/ | i9 | coordinator/星桥 | 全体 | 是（i9-bb.py 已实现）|
| notes/mbp/ | MBP | coordinator/星桥 | 全体 | 建议 |
| notes/mac-mini/ | mac-mini 会话 | — | 全体 | 镜像中枢 |
| notes/collab/ | 全员广播 | — | 全体 | 上行中枢（sync-up）|
| nodes/<dev>/heartbeat | 各设备自己 | — | 全体 | 镜像（hb-fwd）|
| data/ops/ | 治理方 | 全体可写 | 全体 | 上行 |
| data/registry/ | HR | 全体可写 | 全体 | 上行 |

> 纯函数：`can_write(role: &str, key: &str) -> bool` —— 角色+键前缀 → 允许/拒绝
> 不可绕过：写入门 gate 强制调用（非文档约定）

## 二、门清单（每门 = 纯判定函数 + lean4-check 断言）

### G1 域权写入门 `can_write(role, key)`
- 不该发生路径：i9 写 notes/mac-mini/（越权）
- 断言：越权域拒 / 自域放行 / 协调者跨域放行 / 未知角色拒

### G2 JSON 格式门 `is_valid_json_body(body) -> bool`
- 不该发生路径：纯文本 body → value 空壳（R003 实测根因）
- 断言：合法 JSON 放行 / 纯文本拒 / 空 body 拒

### G3 双写触发门 `should_mirror(key, role) -> bool`
- 不该发生路径：设备自域消息不镜像中枢 → 备灾失效
- 断言：notes/i9/+i9 → true / notes/collab/ 广播 → false(上行sync-up管) / 心跳 → false(hb-fwd管)

### G4 状态闭环门 `task_needs_ack(value) -> bool`
- 不该发生路径：任务卡处理完不回写 → 假完成
- 断言：type=task 且无 reply 字段 → true（须回写）/ 非 task → false

### G5 静默检测门 `heartbeat_stale(ts, now, max_age) -> bool`
- 不该发生路径：长连/轮询服务心跳超时无人知（MBP 事件桥 8 天静默停摆教训）
- 断言：fresh 放行 / 超 max_age 告警

## 三、纯函数签名（生产与自检同源）

```python
# bb_gate.py 核心（不依赖网络，纯逻辑——可单测/自检）
def can_write(role: str, key: str) -> bool: ...
def is_valid_json_body(body: str) -> bool: ...
def should_mirror(key: str, role: str) -> bool: ...
def task_needs_ack(value: dict) -> bool: ...
def heartbeat_stale(ts: float, now: float, max_age: float) -> bool: ...
```

## 四、--lean4-check 自检（断言矩阵证明门生效）

```
bb-gate --lean4-check
  [✅] G1 越权域拒：i9 写 notes/mac-mini/ → 拒
  [✅] G1 自域放行：i9 写 notes/i9/ → 放
  [✅] G1 协调者跨域：coordinator 写 notes/i9/ → 放
  [✅] G2 纯文本拒：body="hello" → 拒
  [✅] G2 合法 JSON 放行
  [✅] G3 设备自域镜像：notes/i9/+i9 → true
  [✅] G4 task 需 ack
  [✅] G5 心跳超时检测
结果: GATE OK / FAIL
```

## 五、接入方案
1. mac-mini：bb 写入工具/脚本收口经 bb-gate（curl 包装或 python 库）
2. i9：i9-bb.py 已收口（put/putfile）→ 接入 bb-gate.can_write/should_mirror（放行层已实现镜像）
3. MBP：blackboard-events.py 接入（写前 gate 校验 + 心跳探针 G5）
4. 同步层（sync-up/down/hb-fwd）：域过滤逻辑对齐 can_write/should_mirror（同源）

## 六、验证标准（R030）
- bb-gate --lean4-check GATE OK
- 端到端：越权写被 gate 拒（无键生成）/ 合法写正常 / 双写镜像中枢
- 历史键扫描：空 value 键归因 R003（非 JSON body）
