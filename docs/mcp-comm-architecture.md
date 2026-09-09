# MCP 外部接入层 · 架构图（Comm 架构版）

> 明鉴 v3 · 2026-09-06 · 配套 docs/mcp-external-access-design-v1.md

## 一、分层架构图（总览）

```mermaid
flowchart TB
    subgraph CLIENTS["外部 MCP 客户端层"]
        C1["Claude Desktop"]
        C2["Cursor / VS Code"]
        C3["自研 agent"]
        C4["手机 / 平板"]
    end

    subgraph MCPL["MCP 接入层 comm-mcp-server"]
        P["协议面 JSON-RPC 2.0<br/>initialize / tools/list / tools/call"]
        A["鉴权面 Bearer token<br/>→ E2 注册校验 → 会话"]
        T["工具面白名单映射<br/>bb_read · bb_write · bb_subscribe<br/>bus_send · node_whoami · node_list"]
    end

    subgraph COMM["Comm 通讯层 (xingqiao /opt/comm-layer)"]
        BB["Prod 黑板 :8792<br/>data/notes/tasks KV"]
        SSE["SSE 事件桥 :8803<br/>bb-sub×8 订阅"]
        BUS["bus-bridge :8791<br/>消息/任务队列"]
        E2["E2 全局注册表<br/>data/discovery/agents/"]
        TST["Test 黑板 :8794<br/>隔离验证区"]
    end

    C1 & C2 & C3 & C4 -->|"MCP stdio / SSE"| P
    P --> A --> T
    T -->|"GET/PUT KV"| BB
    T -->|"订阅事件"| SSE
    T -->|"POST /bus/send"| BUS
    T -->|"whoami / list"| E2
    BB -.->|"升级先验证"| TST
```

## 二、接入流程时序图（onboarding）

```mermaid
sequenceDiagram
    participant D as 外部设备/客户端
    participant OB as onboard 页 (8791/bus/onboard)
    participant E2 as E2 注册表 (data/discovery)
    participant MC as comm-mcp-server
    participant BB as 黑板/总线

    D->>OB: 1. GET onboard (公开指引)
    OB-->>D: 入职包 (URL/端点/鉴权说明)
    D->>E2: 2. node_register {device, role}
    E2-->>D: device_id + token
    D->>MC: 3. MCP connect (Bearer token)
    MC->>E2: 4. 校验 device_id 存在 + token 有效
    E2-->>MC: valid
    MC-->>D: initialize ok
    D->>MC: 5. node_heartbeat (30s 续期)
    MC->>E2: 更新心跳 (G5 <90s = online)
    D->>MC: 6. bb_read / bb_write(域内) / bus_send
    MC->>BB: 转发 (写需域白名单)
    BB-->>D: 结果
```

## 三、鉴权门流程（Φ9 越权拒绝）

```mermaid
flowchart LR
    REQ["外部 MCP 请求"] --> CHK1{"E2 已注册?"}
    CHK1 -- 否 --> REJ401["拒 401<br/>幽灵 device"]
    CHK1 -- 是 --> CHK2{"Bearer token 有效?"}
    CHK2 -- 否 --> REJ401b["拒 401<br/>无/错 token"]
    CHK2 -- 是 --> CHK3{"写操作域<br/>在角色白名单?"}
    CHK3 -- 否 --> REJ403["拒 403<br/>越域写"]
    CHK3 -- 是 --> OK["放行<br/>→ 黑板/总线"]
```

## 四、演进路径图（MCP 时代 → Comm 时代）

```mermaid
flowchart LR
    subgraph OLD["MCP 时代 (08-17 ~ 08-29)"]
        O1["blackboard-mcp<br/>私有协议暴露"]
        O2["external-link-mcp<br/>通道/bus"]
        O3["rust-blackboard-mcp<br/>10 工具"]
    end
    subgraph NEW["Comm 时代 (09-06)"]
        N1["comm-layer bb-sub×8"]
        N2["E2 注册表 (R-ERR4)"]
        N3["bus-bridge 服务器版"]
    end
    subgraph FUT["本设计 (MCP 外部接入层)"]
        F1["comm-mcp-server<br/>标准 MCP 协议面"]
    end
    O1 -->|node 3 工具语义| N2
    O2 -->|bus 面| N3
    O3 -->|二进制融合| N1
    N1 & N2 & N3 -->|对外暴露标准接口| F1
```

---
*架构图 v1 · 明鉴 · 2026-09-06*
