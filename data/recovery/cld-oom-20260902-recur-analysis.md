# OOM 复发调查 · 守灯归因（2026-09-02）

> 关联：data/recovery/cld-oom-20260901-recur / CLD-020

## 复发确认
- 第 3 次 OOM：CLD-2026-09-02-125103.ips（12:51，78KB）
- dsh-web.log 现有 3× `CALL_AND_RETRY_LAST Allocation failed - heap out of memory`（行 2592/2643/2796）
- 复发模式：boot 04:35→04:37→04:55（CST 12:35/12:37/12:55），12:51 崩溃距上一 boot ~14 分钟 =「13 分钟快速复发」成立

## heap 监控是否生效？
**否**。CLD-002 看门狗（exit-trace/heartbeat）仍未安装（待用户终端安装+重签批准）——崩溃仅能事后从 .ips + dsh-web.log 发现，无运行期堆监控/心跳留痕。这正是 CLD-002 应尽快安装的原因。

## 泄漏点快速定位（12:51 报告线程分析）
崩溃时活跃线程指纹：
1. **多 node WorkerThread**（node::worker::Worker::Run）——每 Worker 持有独立 isolate/context
2. **tokio-rt-worker ×N**（rust-blackboard agent 的 tokio 运行时，in-process/桥接）——大量线程等待 semaphore/kevent
3. **V8Worker 编译/GC 风暴**：MoveTracedReference / OptimizingCompileInputQueue::FlushJobsForIsolate / CompilationDependencies——JIT 编译 + GC 追踪活跃
4. **fs 操作流**：FSReqPromise/AfterMkdirp/uv__realloc（mkdirp/文件系统请求）
5. 一 V8Worker 触发 **Data Abort (Translation fault)**——V8 操作内存故障

## 定位建议（快速）
1. 运行期 heap 监控：启动参数加 `--trace-gc`/`--heapsnapshot-near-heap-limit`（或 NODE_OPTIONS），捕获 OOM 前快照
2. t0（boot）与 t1（~12 分钟）各取 heap snapshot 对比，定位增长 retainers
3. 高度嫌疑：a) 会话/上下文在 Worker isolate 累积（无压缩，CLD-017 未落地） b) rust-blackboard tokio 桥缓冲 c) fs watcher/mkdirp 句柄累积
4. 缓解先行：限制 Worker 并发 / 会话压减 / 上下文压缩试点（CLD-017）加速

## 处置
- CLD-020 更新为「3 次复发，快速复发模式确认」
- 调研派单（memory-resource-optimization）已发 4787d717，报告并入
- 建议 CLD-002 安装升级为 P0（heap 监控缺失是定位瓶颈）
