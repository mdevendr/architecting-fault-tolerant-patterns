# Governed Agent Tool Execution and Compensation

This evidence package tests an agent workflow at the business side-effect boundary. It is not a prompt-routing demonstration.

The implementation proves four independent controls:

1. deterministic policy denial occurs before a tool effect;
2. a stable tool-call identity returns the canonical result after ambiguous completion;
3. compensation is idempotent and reaches an auditable terminal state; and
4. high-impact approval uses a durable workflow callback rather than conversational memory.

## Planned AWS architecture

- Amazon Bedrock AgentCore Gateway exposes the tool.
- AgentCore Policy in `ENFORCE` mode evaluates Cedar policy before invocation.
- A Lambda tool adapter stores call ownership, result and compensation state in DynamoDB.
- AWS Step Functions owns the multi-step workflow and callback-based human approval.
- AgentCore Evaluations assesses expected tool selection and policy-conformant outcomes separately from transaction correctness.

## Local contract tests

Run:

```powershell
python -m unittest discover -s code\scenarios\governed-agent-recovery\tests -v
```

The local model is intentionally small. Deployed evidence, rather than this model alone, will support article claims.

