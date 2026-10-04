# SystemGraph 通用注册表 · schema 五类分层 v1（2026-09-07 星桥草拟 · E3 前定稿）

## 设计原则
- SystemGraph = 读侧总账 + 定义权威; 各源运行时写(单一写者各源) → 高可用(关键元数据双写本机+服务器)
- 五类分层: device / agent / tool / gate / lock —— 每类注册条目 schema

## 五类 Schema（草案）
### device（设备注册）
来源: hardware-nodes.json + E2 data/discovery/agents
{id, type: device, name, os, ip, role, status, hb_ref, registry_ref: E2, since, sgVersion}

### agent（智能体会话）
来源: E2 discovery + agent_profiles
{id, type: agent, session_id, device_ref, role, abilities[], status, hb_ref, ts}

### tool（工具/插件/功能）
来源: business-asset-map + 工具注册
{id, type: tool, kind: tool|plugin|skill|mcp|script, domain, exec_path, version, lean4_check: enum{yes|no|na}, owner, capability_tags[], ts, schema_ver: v1}

### gate（门 - 强制约束点）
来源: mechanism.gates + gate-auditor 识别 + bb-gate/lean4 工具门
{id, type: gate, kind: bb-gate|lean4|paper|restart|schema|... , covered_rule: Rxxx, structural: bool, tool_ref, check_cmd, health: ok|paper, status: identified|classified|staged|applied|verified}

### lock（锁 - 资源互斥）
来源: mechanism.locks + agent-bus 红绿灯
{id, type: lock, resource, holder, mode: exclusive|shared, status: green|red|queued, acquired_at, expires_at, queue_len}

## 关联
- gate.covered_rule ↔ rules-registry (gate-auditor 报告对接)
- agent.device_ref ↔ device.id (E2 注册表)
- lock.resource ↔ gate 管辖区 (红绿灯锁资源)
- tool.lean4_check ↔ gate.kind=lean4 (R006#10)


## 修订采纳 (2026-09-07 明鉴审 · v1-final)
① tool.lean4_check: bool → **enum{yes/no/na}**（区分未达标 vs 不需门——gate-auditor 判纸面准）
② gate.kind 补 **connect|comm**（E1 已入 BBG 系）
③ lock.resource 补规则前缀（**file:/task:/store:/agent:** 便于红绿灯按前缀归组展示）
④ 五类条目统一 **ts + schema_ver(v1)**（演进可溯）

## 定稿路径（三方签字）
明鉴/星桥/HR 三方签 → rules-registry 正式版 schema-v1-final → 落地顺序: device/gate/lock 先行 → tool 补字段 → agent(E2 后)

## 三方签字
- 星桥: ✅ 草拟(2026-09-07)
- 明鉴: ✅ 审+4 修订采纳
- **HR 司库: ✅ 签字(2026-09-07)——治理合规检查通过: device↔E2 data/discovery 同源 / gate.covered_rule↔Rxxx 衔接 / tool.lean4_check enum 与 R006#10 对齐 / lock 前缀与红绿灯归组一致; 建议落地顺序 device→gate→lock→tool→agent 认同(E2 后 agent)
- 状态: **schema-v1-final**(三方签齐, 入正式版)