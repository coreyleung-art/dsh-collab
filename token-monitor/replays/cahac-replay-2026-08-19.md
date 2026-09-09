# CAHAC Offline Replay v0.1

> generated: 2026-08-19 · data: 12.8h aggregate (21,996 events) + billing calibration
> assumption: agent_send=13585, ratios ACK=60%/STATUS=20%/COLLAB=10%/TASK=7%/EVENT=2%/BROADCAST=1%

## 1. Event distribution (12.8h)

| tool | count | share |
|---|---|---|
| agent_send | 13585 | 61.8% |
| run_code | 5702 | 25.9% |
| bash | 1318 | 6.0% |
| other | 1391 | 6.3% |

## 2. CAHAC channel remap (agent_send part)

| type | count(est) | old | new channel | new weight |
|---|---|---|---|---|
| ACK | 8151 | 1.0x | blackboard-read | 0.05x |
| STATUS | 2717 | 1.0x | blackboard-write | 0.10x |
| COLLAB | 1358 | 1.0x | p2p-thread | 0.80x |
| TASK | 951 | 1.0x | p2p | 1.00x |
| EVENT | 272 | 1.0x | eventbus | 0.50x |
| BROADCAST | 136 | 1.0x | broadcast-whitelist | 10.00x |

## 3. Cost comparison (agent_send channel)

| basis | cost index |
|---|---|
| current (all p2p) | 13585 |
| CAHAC (graded) | 4211 |
| saving | 69% |

## 4. Money calibration (peak day 8/18)

- peak day = ¥748.2, storm share ~40% -> related ≈ ¥299
- if CAHAC: saving 69% ≈ **¥207/peak day**
- monthly (3 peak days/mo): ≈ ¥620/mo

> note: v0.1 = event-level weight model; ACK ratio tunable (--ack-ratio); token-level replay in v0.2 when thread history available.
---
*cahac-replay-v0.1 · HR · 2026-08-19*