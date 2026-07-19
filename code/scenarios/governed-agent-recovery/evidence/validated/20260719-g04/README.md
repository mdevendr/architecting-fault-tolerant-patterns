# Validated AWS evidence: 20260719-g04

## Scope

- Region: `eu-west-2`
- Policy boundary: Amazon Bedrock AgentCore Gateway with a Cedar policy in `ENFORCE` mode
- Business-state boundary: DynamoDB-backed Lambda tool adapter
- Agent-callable surface: `reserve_credit` only
- Recovery-only operation: `compensate_credit`, deliberately absent from the Gateway tool catalogue

## Results

| Injected condition or control | Observed result |
|---|---|
| Reservation above the permitted amount | AgentCore policy denied the call |
| State lookup for the denied call identity | No DynamoDB item existed |
| Response lost after an allowed reservation committed | Gateway returned a tool error |
| Same tool call replayed | Canonical committed result returned with `replayed=true` |
| Response lost after compensation committed | Lambda invocation reported the injected failure |
| Same compensation replayed | Canonical release result returned with `replayed=true` |
| Final workflow record | `COMPENSATED` |
| Forward result identities | One |
| Compensation result identities | One |

Contract result: **PASS**

## Architectural finding

Policy enforcement, tool idempotency and compensation solve different problems. AgentCore prevented an unauthorized request from reaching the tool. The tool adapter handled ambiguous completion through a stable call identity and canonical result. The recovery path performed compensation through a separately scoped internal operation that the agent could not discover or invoke.

## Limitations

- `NONE` inbound Gateway authorization was used only for an isolated evidence stack; it is not a production recommendation.
- The experiment uses a DynamoDB-backed credit-reservation simulator rather than a financial provider.
- A real provider must persist the same operation identity or expose reconciliation and reversal APIs.
- AgentCore Policy does not make tool side effects transactional.
- AgentCore Evaluations measure agent behaviour and quality; they do not prove business-state correctness.

