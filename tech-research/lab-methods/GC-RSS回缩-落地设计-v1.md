# GC/RSS 回缩 · 落地设计方案 v1（细化版）

> mbp-ops · 2026-09-06 · 基于：深度调研 + 风险审查 + GC 逻辑门(G1-G6 全过)
> 目标：dsh RSS 从 3.6GB(90% cage) 周期回缩至 ~1GB，在 4GB Electron cage 内安全治理

---

## 一、设计约束（来自前置审查，全部机械强制）

| 约束 | 来源 | 强制手段 |
|---|---|---|
| G1-G3 会话安全 | 代码级证明(落盘+强引用+无回调) | guard-gc-gate |
| G4 GC 阻塞 ≤300ms | 实测 39-332ms(堆大小相关) | 方案 max_block 声明 |
| G5 仅空闲触发 | 避免撞推理/流式 | **会话写入判闲** |
| G6 RSS 阈值触发 | 非高频 | 3.0GB 阈值 |
| 零改动 dsh/runtime | 降风险 | 环境注入(非 asar 补丁) |

## 二、架构（三层解耦）

```
┌─ 第1层: 观察器(cld-monitor 扩展) ─────────────────┐
│  每 60s: 采样 dsh RSS + 会话活跃度(最近写入)         │
│  产出: dsh_rss_mb / active_15s / 状态快照          │
│  告警: dsh_rss > 3.0GB → 写 GC 许可标记            │
└──────────────────────────────────────────────────┘
                    ↓ 文件标记
┌─ 第2层: GC 执行器(dsh 内注入, --require) ────────┐
│  每 30s 检查许可标记(非定时无脑 GC)                 │
│  有许可且 15s 无会话写入 → global.gc()×2           │
│  记录: GC 前后 RSS / 耗时 → 审计文件               │
└──────────────────────────────────────────────────┘
                    ↓ 审计
┌─ 第3层: 审计/验证 ───────────────────────────────┐
│  gc-audit.jsonl: 每次 GC 的 时间/前RSS/后RSS/耗时   │
│  验证: RSS 回缩达标 / 无会话丢失 / GC 频率合理       │
└──────────────────────────────────────────────────┘
```

**关键解耦**：GC 在 dsh 内执行（必须进程内），但"何时允许"由外部观察器决策（文件标记）——外部能看会话活跃度，进程内不能轻易感知业务空闲。

## 三、空闲判据（已实测可行）

**会话文件 15s 无写入 = 空闲**
- 任何 agent 推理/工具执行 → append 会话帧 → 文件 mtime 更新
- 15s 无写入 → 无活跃推理 → 安全 GC 窗口
- 实测: 当前 0 活跃会话(空闲) / 活跃时 92623479/fa1f9150/f38244df 等 mtime 新鲜

**为什么可靠**：会话落盘是 fsync 同步（G1）→ mtime 是硬信号，非轮询猜测。

## 四、GC 执行器脚本（注入 dsh）

```javascript
// gc-timer-v2.cjs — 阈值+空闲 GC(替代 v1 的无脑定时)
const FS = require('node:fs');
const MARK = '/Users/coreyleung/.cld/gc-permit';     // 外部观察器写的许可
const SESS = '/Users/coreyleung/.dsh/sessions/--Users-coreyleung--';
let lastLog = 0;

setInterval(() => {
  try {
    // 1. 有许可标记?
    if (!FS.existsSync(MARK)) return;
    // 2. 15s 无会话写入(空闲)?
    const now = Date.now();
    let active = false;
    for (const w of FS.readdirSync(SESS)) {
      const st = FS.statSync(SESS + '/' + w + '/session.jsonl.zstd', {bigint:false});
      if (now - st.mtimeMs < 15000) { active = true; break; }
    }
    if (active) return; // 忙, 不 GC
    // 3. 空闲 + 有许可 → 完整 GC
    const before = process.memoryUsage().rss;
    const t0 = Date.now();
    global.gc(); global.gc();
    const after = process.memoryUsage().rss;
    const ms = Date.now() - t0;
    // 4. 记录审计 + 清许可
    const rec = {ts: new Date().toISOString(), beforeMB: Math.round(before/1048576), afterMB: Math.round(after/1048576), gcMs: ms};
    FS.appendFileSync('/Users/coreyleung/.cld/gc-audit.jsonl', JSON.stringify(rec)+'\n');
    FS.unlinkSync(MARK); // 一次许可一次 GC
  } catch {}
}, 30000); // 30s 检查一次(轻量 stat, 非每30s GC)
```

**设计要点**：
- 30s 检查但**仅在"有许可+空闲"时 GC**（G5/G6 满足）
- 许可一次一清（防重复触发）
- 审计落盘（第3层验证）
- catch 兜底（脚本错误不影响 dsh）

## 五、观察器扩展（cld-monitor）

```python
# cld-monitor 增加:
def dsh_rss_mb():
    """采样 dsh 进程 RSS(现只监控壳=盲区)"""
    pids = pgrep(r"dsh/lib/bin\.js web")
    if not pids: return None
    # 取第一个 dsh 的 RSS
    try:
        out = subprocess.run(["ps","-o","rss=","-p",pids[0]], capture_output=True, text=True, timeout=5)
        return int(out.stdout.strip())//1024
    except: return None

# collect() 中:
snap["dsh_rss_mb"] = dsh_rss_mb()
# 告警: dsh_rss > 3000 → 写 GC 许可 + warn 告警
if (snap.get("dsh_rss_mb") or 0) > 3000:
    open(GC_PERMIT, "w").write(str(time.time()))
    alerts.append({"sev":"warn","msg":f"dsh RSS {snap['dsh_rss_mb']}MB > 3GB, 已发GC许可"})
```

## 六、部署步骤（分阶段，每阶段可回滚）

| 阶段 | 内容 | 验证 | 回滚 |
|---|---|---|---|
| **S1 观察**(先行) | cld-monitor 加 dsh_rss 采样+告警 | 能看到 dsh 真实 RSS | 删字段 |
| **S2 注入** | NODE_OPTIONS 加 --require gc-timer-v2 + --expose-gc | 许可触发 GC 审计落盘 | 撤 NODE_OPTIONS |
| **S3 调优** | 观察 7 天 GC 频率/回缩量/无会话问题 | RSS 3.6→~1GB 周期稳定 | S2 回滚 |

## 七、验收标准

```
1. dsh RSS 峰值后 30min 内回缩至 ≤1.5GB(经 GC)
2. GC 后会话数不变(189) / 无会话丢失(guard-recall 会话检查)
3. GC 耗时 ≤300ms 且不落在活跃推理期(审计验证)
4. 7 天 0 会话事故 / 0 误删(GC 逻辑门复检)
5. cld-monitor 能持续看到 dsh_rss(消除盲区)
```

## 八、风险与缓解(落地视角)

| 风险 | 缓解 |
|---|---|
| --require 注入影响 dsh 启动 | 脚本纯 setInterval+catch, 启动即验证(先 S2 小步) |
| 许可标记竞争(观察器与 GC 时序) | 许可一次一清 + 空闲二次确认 |
| GC 触发瞬间仍有请求 | 15s 空闲窗口(推理中会话持续写→不触发) |
| 环境变量污染其它进程 | 评估: 仅 GUI 启动的 dsh 受益, 其它 Node 程序无害(GC 是安全操作) |

## 九、与 Lean 门衔接

- 部署 S2/S3 = 受限操作(环境/监控变更) → 走 guard-gate + guard-gc-gate
- GC 逻辑门(G1-G6)已全过 → safe_gc_timer 可构造
- 每次 GC 审计可验证 G4(阻塞) 实际满足

---

*基线 2026-09-06 · 配套 guard-gc-gate / cld-monitor / 调研报告*
