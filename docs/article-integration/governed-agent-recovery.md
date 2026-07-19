# Governed Agent Tool Execution and Compensation

## Architectural objective

An agent must not be treated as a transaction coordinator. Authorization, durable execution identity, business-state recovery and compensation require independent controls outside conversational memory.

The validated architecture separates these responsibilities:

- AgentCore Gateway and Cedar policy decide whether an agent may invoke the forward tool.
- A DynamoDB-backed tool adapter makes the business operation replay-safe.
- An internal recovery path owns compensation and its terminal state.
- AgentCore Evaluations can assess tool selection and behavioural quality, but do not replace state reconciliation.

## Validated sequence

Run `20260719-g04` first attempted a reservation above the Cedar policy threshold. AgentCore denied the request by default because no permit policy applied, and the tool-state table contained no record for that call identity.

An allowed reservation then committed its result before an injected response loss. The Gateway reported a tool error, creating ambiguous completion from the caller's perspective. Replaying the same call identity returned the original result rather than creating another reservation.

The recovery path compensated the reservation and then lost its response. Replaying compensation returned the original release result. The final durable state was `COMPENSATED` with one forward result identity and one compensation result identity.

## Important design correction

Only the forward reservation is exposed through the agent Gateway. Compensation is intentionally absent from tool discovery and is invoked by a scoped recovery principal. This prevents an agent from independently reversing committed business operations.

## Evidence boundary

The experiment proves deterministic authorization before tool execution and replay-safe forward/compensating effects. It does not prove that policy enforcement makes external effects transactional or that an evaluator can establish state consistency.

