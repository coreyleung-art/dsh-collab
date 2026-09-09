---
title: "dsh 远程访问/基础设施验收 checklist（582093dd 提供）"
tags: [qa, checklist, dsh]
updated: 2026-08-17
---

# 验收 Checklist · dsh 远程访问与基础设施

> 由 dsh 平台会话（582093dd）沉淀：历次重启 / 重签 / 插件安装验证流程。QA 验收员可复跑作为回归基线。

## A. 重启后复核（每次重启必跑）
- [ ] dsh-health.py 全绿：`~/.openchronicle/venv/bin/python ~/.claude/automation/dsh-health.py`（期望 10 项 0 严重 0 警告）
- [ ] 反代跟随：`tail ~/.cld/logs/dsh-remote.out.log` 显示 GUI 端口已更新（CLD 换端口后约 60s 内）
- [ ] tailnet 可达：`curl -o /dev/null -w '%{http_code}' http://100.120.203.20:3081/` → 200
- [ ] 配对路由：`curl http://100.120.203.20:3081/api/pair/status` → ok:true
- [ ] 普通 /api：`curl -o /dev/null -w '%{http_code}' http://100.120.203.20:3081/api/sandbox-policy/api/state` → 200
- [ ] 绑定收口：`lsof -nP -iTCP:3081 -sTCP:LISTEN` 显示仅 `100.120.203.20:3081`（禁止 0.0.0.0）

## B. 代理（com.dsh.remote）专项
- [ ] launchd 存活：`launchctl list | grep com.dsh.remote`
- [ ] WebSocket 透传：连一个 SSE/WS 端点无断流（如 /api/pair/events）
- [ ] Host 改写行为与登记表一致（loopback 改写 + tailnet-only 绑定）

## C. 知识库/调研流水线
- [ ] 集合属主隔离：dsh-docs / dsh-research / research 三集合 count 与登记一致（勿动 research）
- [ ] /research 命令可用（GUI 斜杠命令）
- [ ] 嵌入双通道：`curl -X POST http://127.0.0.1:1234/v1/embeddings -d '{"model":"text-embedding-nomic-embed-text-v1.5","input":"test"}'` → 200（LM Studio 优先，Ollama 兜底）

## D. 插件安装/重签后（QA 与变更共同执行）
- [ ] 插件入口冒烟（slots 渲染、命令注册、设置页签可见）
- [ ] 重签后：`codesign --verify --deep --strict /Applications/CLD.app` 通过
- [ ] 重签后 headless 复测：`CLD_HEADLESS=1 CLD_PORT=3082`（勿用 3081，代理占用）应正常绑端口
- [ ] 会话恢复：重启后会话列表完整（无丢失）

## E. 回归基线命令（供自动化）
```bash
# 健康基线
~/.openchronicle/venv/bin/python ~/.claude/automation/dsh-health.py
# 代理日志跟随
tail -20 ~/.cld/logs/dsh-remote.out.log
# 集合 count
python3 -c "import sys,os; sys.path.insert(0, os.path.expanduser('~/.claude/automation')); from lib import _get_chroma; [print(c.name, c.count()) for c in _get_chroma().list_collections()]"
```
