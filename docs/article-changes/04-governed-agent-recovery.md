# Article Change Sheet 04: Governed Agent Recovery

Apply these changes by heading, not PDF page number.

## Change 1: Replace the unevidenced agent tool code

### Find

The **Agentic Workflows** material containing illustrative tool-execution, DynamoDB lock or SQS human-escalation code.

### Remove

- code implying that agent memory coordinates business transactions;
- the generic tool handler that has no stable tool-call identity or canonical result;
- any SQS example that passes a Step Functions task token without implementing and validating the callback contract; and
- claims that a distributed lock alone prevents repeated external effects.

### Retain

Retain the architectural discussion of non-idempotent tools, lost responses, human approval, workflow divergence and compensation.

## Change 2: Add the validated implementation

### Add this heading

#### Validated Reference Implementation: Govern, Replay and Compensate Agent Actions

### Add this text

> A controlled AWS experiment separated agent authorization from business-state recovery. Amazon Bedrock AgentCore Gateway exposed one forward tool through a Cedar policy engine in `ENFORCE` mode. A request above the permitted amount was denied before Lambda invocation, and no business-state record existed for the denied call identity.
>
> An allowed tool call then committed a reservation before an injected response loss. Although the Gateway returned an error, replaying the same stable tool-call identity returned the canonical committed result rather than repeating the effect. A later recovery operation compensated the reservation and also lost its response; compensation replay returned the original release result and preserved one terminal `COMPENSATED` state.
>
> Compensation was deliberately excluded from the agent's Gateway tool catalogue. It remained an internal recovery operation available only to a scoped workflow principal. Policy enforcement, tool idempotency and compensation therefore remain distinct controls.

## Change 3: Add the evidence table

| Failure or control | Observed result |
|---|---|
| Over-limit agent action | Denied by AgentCore Policy |
| Business state after denial | No effect record |
| Response lost after forward commit | Ambiguous completion injected |
| Forward call replay | Canonical result returned |
| Response lost after compensation | Ambiguous compensation injected |
| Compensation replay | Canonical release result returned |
| Final state | `COMPENSATED` |

Add:

> **Evidence scope:** Run `20260719-g04` executed in `eu-west-2`. The provider was a DynamoDB-backed simulator so authorization decisions and each business-state transition could be inspected independently.

## Change 4: Add short implementation excerpts

Use the Cedar boundary:

```cedar
permit(principal, action == AgentCore::Action::"<gateway-arn>___CreditTool___reserve_credit", resource)
when {
  context.input.actor_role == "credit-operator" &&
  context.input.amount > 0 &&
  context.input.amount <= 1000
};
```

Then use the replay boundary:

```python
existing = get_tool_record(call_id)
if existing:
    return canonical_result(existing, replayed=True)
```

Do not paste the complete Lambda handler or CloudFormation template.

## Change 5: Tighten the human-approval statement

Use:

> High-impact approval must pause a durable workflow through a real callback contract, persist approval identity and expiry, and resume with the same business-operation identity. A queue message or conversational response alone is not proof of resumable approval.

## Change 6: Bound AgentCore claims

Add:

> AgentCore Policy deterministically authorizes tool calls at the Gateway boundary; it does not make downstream effects transactional. AgentCore Evaluations assess agent behaviour and quality; they do not establish exactly-once effects or source-to-derived state equality.

## Change 7: Add the visual

Suggested title:

> **Authorization, Execution and Compensation Are Separate Boundaries**

```text
Agent request → AgentCore Policy → durable tool adapter → business effect
                    │ denied              │ response lost
                    ▼                     ▼
               zero effect          replay canonical result
                                          │ later failure
                                          ▼
                              internal compensation workflow
                                          │ response lost
                                          ▼
                              replay → COMPENSATED
```

## Change 8: Add limitations

> The reference provider is a DynamoDB-backed simulator, not a financial system. A real provider must persist the stable operation identity or expose reconciliation and reversal APIs. AgentCore Policy controls whether a tool call may cross the Gateway boundary; it does not make the downstream side effect transactional. The evidence Gateway used `NONE` inbound authorization only within the isolated experiment and this is not a production recommendation.

## Change 9: Repository links

Link to:

- `code/scenarios/governed-agent-recovery/README.md`
- `code/scenarios/governed-agent-recovery/src/aws_handlers/handler.py`
- `code/scenarios/governed-agent-recovery/infrastructure/template.yaml`
- `code/scenarios/governed-agent-recovery/evidence/validated/20260719-g04/README.md`

Suggested immutable tag:

```text
evidence/governed-agent-recovery-20260719-g04
```
