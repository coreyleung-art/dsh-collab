# Rust 切换前后区别说明（node-bridge vs Python executor）

> 适用：MBP 侧 / i9 侧节点 agent 从 Python 切换到 Rust node-bridge
> 出品：mac-mini 中枢 · 2026-08-26 · 基于两侧实际代码对照（非假设）

---

## 一、一句话结论

**切换后「协议通道完全不变、节点身份不变、能力不变」——变的只是运行载体**：从「Python 解释器 + 3 个脚本文件」变成「1 个 Rust 单二进制」。所有依赖黑板的客户端（中枢/i9/mbp/脚本）**无感知**。

---

## 二、切换前后对照表

| 维度 | 切换前（Python） | 切换后（Rust node-bridge） |
|---|---|---|
| **运行载体** | Python 解释器（3.9/3.14）+ `.py` 脚本 | 1 个二进制（约 0.5-0.6MB） |
| **文件数** | executor + bb + guard 三件套 | 单文件 |
| **心跳** | `nodes/{node}/heartbeat`（60s） | 同（协议不变） |
| **任务取卡** | `tasks/{node}/cmd`（旧单卡）| `tasks/{node}/queue/`（新队列）+ 旧 cmd 兼容 |
| **任务回报** | `tasks/{node}/result` | 同（永远不变） |
| **消息通道** | `notes/{node}/*`（部分版本没读）| `notes/{node}/coordinator-*` 专属线程读 |
| **内存占用** | Python 解释器 30-50MB 常驻 | ~2-5MB |
| **依赖** | 需目标机装 Python + 编码坑（GBK/UTF-8）| 零依赖，拷贝即跑 |
| **升级** | 覆盖 3 个文件易漏 | 替换 1 个文件 |
| **崩溃重启** | 需外部 guard 脚本 | launchd（MBP）/ NSSM（i9）平台机制 |
| **日志** | print 到 stdout（可能乱码）| JSON 结构化 + 落盘 + 5MB 轮转 |

---

## 三、核心差异逐条说明

### 1. 任务通道：旧 cmd → 新 queue（协议 v1.0）
```
切换前：中枢 PUT /tasks/{node}/cmd（单卡，取一次清一次）
切换后：中枢 PUT /tasks/{node}/queue/{ts}（队列，可多卡排序）
兼容：Rust bridge 仍应答旧 cmd 卡（check_legacy_cmd）——不砸旧对讲机
```
> **对中枢无感**：中枢发 queue 卡，Rust bridge 消费；发 cmd 卡也消费。

### 2. 心跳格式（唯一存活标准不变）
```
切换前：{"ts": "...", "health": "ok", "os": "...", "hostname": "..."}
切换后：{"ts": "...", "health": "ok", "bridge": "rust", "ver": "1.0.5"}
```
> 判定逻辑不变：60 秒内新鲜 = 在线。多出 `bridge/ver` 字段只是标识载体，不影响判定。

### 3. 消息通道（新增专属读取）
```
切换前：多数 Python executor 不主动读 notes（导致「对空气说话」问题）
切换后：notes 专属线程 5s 轮询 notes/{node}/coordinator-*（DSH 智能体对话通道）
```
> **这是行为增强**：中枢写 notes 消息，Rust bridge 能读到并落日志，为节点侧 DSH 智能体对话打通通道。

### 4. 执行能力（动作白名单不变）
```
切换前：shell / info / status / ollama / scan
切换后：shell / info / status / scan / ollama / dsh（同白名单，只增不减）
```
> i9 的 GPU/ollama 能力、MBP 的文件/脚本能力都保留。

### 5. 编码处理（增强）
```
切换前：Python locale 检测 + 手动解码（GBK/UTF-8 切换）
切换后：UTF-8 优先，失败自动回退 GBK（encoding_rs）——Windows 中文零乱码
```

### 6. 架构（增强：四线程互不阻塞）
```
切换前：单线程串行（心跳/取卡/执行同一循环，scan 大目录可能卡死整体）
切换后：四线程独立
  heartbeat 60s（存活）
  queue 2s（取卡，含旧 cmd 兼容）
  worker 即时（执行→回报→清卡，与取卡解耦）
  notes 5s（消息读取）
```
> **关键改进**：任何线程卡死不影响其他——scan 卡死不阻塞心跳（解决历史「scan-002 卡死进程」教训）。

---

## 四、节点侧运维差异

| 操作 | 切换前 | 切换后 |
|---|---|---|
| 启动 | `python3 xxx.py --node-id X --blackboard ...` | `./node-bridge --node-id X --blackboard ...` |
| 自启 | launchd/NSSM 指向 python 脚本 | launchd/NSSM 指向二进制 |
| 日志 | stdout 重定向（可能 GBK 乱码）| JSON 结构化落盘 `node-bridge.log`（可 jq）|
| 升级 | 覆盖 3 个 .py | 替换 1 个二进制 + 重启 |
| 回滚 | — | 随时切回 Python（协议不变，无迁移成本）|

---

## 五、切换后验证清单（供执行侧核对）

1. **心跳在线**：黑板 `GET /nodes/{node}/heartbeat` → value 含 `"bridge":"rust","ver":"1.0.5"`
2. **任务链路**：中枢发一条 shell 任务 → 秒级执行回报 `ok:true`
3. **旧卡兼容**：发一条 `tasks/{node}/cmd` 旧卡 → 仍应答（可选验证）
4. **notes 读取**：中枢写 `notes/{node}/coordinator-*` → bridge 日志出现 MSG
5. **崩溃自拉起**：kill 进程 → launchd/NSSM 自动拉起，心跳恢复

---

## 六、回滚方案

```
随时可回滚：停 node-bridge → 跑回 python3 xxx.py（协议不变，黑板无感知）
```

---

## 七、变更记录
- v1.0（2026-08-26）：首版说明。基于两侧代码事实对照，不涉及切换状态假设。
