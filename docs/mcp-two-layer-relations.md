# 两层 MCP 化 × Comm 架构 · 关系总图

> 明鉴 v3 · 2026-09-06 · 计划 A(mcp-access) + 计划 B(mcp-export)

## 总览：MCP 化的两个面

```mermaid
flowchart TB
    subgraph BLUE["蓝图层 (agent-network + mtm)"]
        BA["agent-network<br/>mcp-access 主线(计划A)<br/>comm-server 同域"]
        BB["mtm 蓝图<br/>mcp-export 主线(计划B)<br/>MTM 作业工具本体"]
    end
    subgraph MCPA["计划 A · 通讯层 MCP (接入)"]
        A1["comm-mcp-server<br/>外部设备接入协作网"]
        A2["工具: bb_read/write/subscribe<br/>bus_send/node_list"]
    end
    subgraph MCPB["计划 B · 业务能力 MCP (调用)"]
        B1["waimai-mcp-server<br/>外卖能力对外服务化"]
        B2["工具: state/report/analyze<br/>动作 accept/price(带门)"]
    end
    subgraph COMM["Comm 通讯层 (xingqiao)"]
        C1["黑板/E2/bus/SSE"]
    end
    subgraph SRC["数据源"]
        S1["8787 面板"]
        S2["meituan-multi 脚本"]
    end
    BLUE --> MCPA
    BLUE --> MCPB
    A1 -->|后端| C1
    A2 --> C1
    B1 -->|内部 API| S1
    B2 --> S1
    B2 --> S2
    A1 -.共享基础设施.-> B1
    MCPA -.演进自.-> OLD["blackboard-mcp/external-link/rust-blackboard-mcp"]
```

## 关系矩阵

| 关系 | from | to | 类型 |
|------|------|-----|------|
| 蓝图归属 A | agent-network | mcp-access 主线 | contains |
| 蓝图归属 B | mtm | mcp-export 主线 | contains |
| A 数据依赖 | comm-mcp-server | E2/bus/黑板 | depends_on |
| B 数据依赖 | waimai-mcp-server | 8787 面板 | depends_on |
| A↔B 共享 | comm-mcp-server | waimai-mcp-server | 复用(基础设施) |
| A 演进 | mcp-access | blackboard-mcp(考古) | evolves_from |
| B 演进 | mcp-export | 8787服务化分析(08-25) | evolves_from |
| SystemGraph | 资产图 | mcp-access + mcp-export 资产 | shown_as |

## SystemGraph 落位

| 落位 | 计划 A | 计划 B |
|------|--------|--------|
| 蓝图 Tab | agent-network(mcp-access 主线) | mtm(mcp-export 主线) |
| 跨节点资产图 | +comm-mcp-server(归 xingqiao) | +waimai-mcp-server(归 mac-mini) |
| 机制/关系图谱 | relations 边 agent-network↔mtm(经基础设施) | 同上 |
| 版本台账 | 随 agent-network v1.3+ | 随 mtm v1.1 |

---
*关系总图 v1 · 明鉴 · 2026-09-06*
