# Infrastructure

The stack creates the durable tool boundary, an AgentCore Gateway and a dedicated policy engine in `ENFORCE` mode. The Cedar policy is validated after the target is active because it references the generated gateway ARN and target-derived action name.

Only the forward `reserve_credit` action is exposed to the agent. Compensation remains an internal recovery operation invoked by a scoped workflow role; it is deliberately absent from the agent's tool catalogue.

The gateway uses `NONE` inbound authorization only for this isolated evidence run. Production gateways should use `AWS_IAM`, `AUTHENTICATE_ONLY` with downstream/policy authorization, or a validated JWT authorizer as appropriate. The experiment does not present `NONE` as a production default.
