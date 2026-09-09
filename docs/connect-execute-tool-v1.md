# 连接真实执行器 bb-connect-execute.py v1(R006 合规)

> 作者: 明鉴 v2 · 2026-09-05 · 用户提出
> 问题: 五步门"执行"只写 confirmed 记录+图紫线, 没通知两端 agent / 没建协作 → 糊弄。
> 目标: 执行 = 真实动作(通知相关 agent + 协作登记), 工具化插件化按 R006 九标准。

## 一、执行动作(真实开干)
确认边后, 工具做 3 件事:
1. **黑板投递通知两端**: 对 from/to 两个 agent(或域主体)各发一条黑板 note:
   - 你被确认与 XX 建立连接(协作潜力)
   - 复用点/价值(来自候选叙事)
   - 建议: 相互知会、认领协作方向
2. **协作任务登记**: 写入黑板 data/connect-lab/collab-tasks/ 一条待办
   - {from, to, graph, value, suggested_action, status:new, assigned}
3. **幂等**: 同一连接只通知一次(已发不重发)

## 二、R006 九标准对照
| # | 标准 | 实现 |
|---|------|------|
| 1 | dsh 插件形态 | 独立 bb-connect-execute.py |
| 2 | TCC 自检 | --selfcheck(校验依赖+干跑) |
| 3 | CLD 自适应 | 黑板 127.0.0.1:8792 可配; 无服务时降级本地日志 |
| 4 | dsh 版本自适应 | --tool-version v1.0.0 |
| 5 | 文档化 | 本文档 + docs/connect-execute-guide.md |
| 6 | 版本管理 | 纳入版本台账 |
| 7 | 统一日志 | --log 输出 + 黑板落链留痕 |
| 8 | 自动落链 | 执行结果写黑板 data/connect-lab/executions/ |
| 9 | CLI 治理 | --confirm-file / --exec / --list / --json |

## 三、CLI
```bash
# 执行一条已确认连接(读 confirmed-links.json 找未执行的)
python3 bb-connect-execute.py --run --graph rules --from bp:gene-bank --to bp:agent-network
# 或批量: 执行所有已确认未通知的连接
python3 bb-connect-execute.py --run-all
# 查看执行/通知状态
python3 bb-connect-execute.py --list
# TCC / 版本
python3 bb-connect-execute.py --selfcheck
python3 bb-connect-execute.py --tool-version
```

## 四、执行留痕数据
```
黑板 data/connect-lab/executions/   # 每次执行记录
黑板 data/connect-lab/collab-tasks/ # 协作待办
黑板 notes/<agent-id>/connect-*.json # 发给两端 agent 的通知
confirmed-links.json auth 内标 executed:true
```

## 五、验收
| # | 标准 |
|---|------|
| A1 | --run 发两端黑板通知 + 协作登记 + confirmed 标 executed |
| A2 | 幂等: 二次 --run 不重发 |
| A3 | --run-all 批量处理全部未执行确认 |
| A4 | --selfcheck / --tool-version 工作 |
| A5 | 无黑板时降级本地日志(不崩) |
| A6 | 与五步门 confirm-link 衔接(执行后图紫实线+agent 收到通知) |
