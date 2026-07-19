# Article Change Sheet 06: Capacity Routing Versus Semantic Model Fallback

Apply changes by heading, not PDF page number.

## Change 1: Replace the generic fallback state machine

### Find

The **Model Invocation** or **Step Functions retry and Bedrock fallback** material that routes `States.ALL` failures directly to another model.

### Remove

- fallback triggered by every error;
- claims that changing models is equivalent to regional or capacity routing;
- unevidenced Step Functions syntax; and
- any implication that a fallback model automatically meets the primary model's safety and quality contract.

### Retain

Retain the architectural need to handle throttling, transient service faults, token limits and model unavailability.

## Change 2: Add the validated implementation

### Add this heading

#### Validated Reference Implementation: Separate Capacity Routing from Semantic Fallback

### Add this text

> A controlled AWS experiment treated Bedrock cross-Region inference and model fallback as different controls. The healthy path invoked the `global.amazon.nova-2-lite-v1:0` system inference profile, preserving the Nova 2 Lite model contract while allowing Bedrock to route capacity within the profile.
>
> Semantic fallback used a different model, `amazon.nova-micro-v1:0`, and was disabled by default unless a versioned evaluation record met its threshold and the request geography was approved. Invalid requests and policy failures returned without another model invocation. A deliberately lowered evaluation score and an unapproved geography both blocked fallback.
>
> After the bounded evaluation suite scored 1.0, an injected transient 503 selected Nova Micro. The response explicitly carried the fallback model ID, evaluation-suite version, score and `degraded=true`. This demonstrates evaluated degraded service, not equivalence between models.

## Change 3: Add the decision table

| Failure classification | Architectural response |
|---|---|
| Healthy request | Invoke approved inference profile |
| 429, 500, 502, 503 or 504 | Bounded capacity recovery; semantic fallback only if separately approved |
| 400 invalid request | Return error; no retry or fallback |
| Authentication/authorization failure | Return or fail closed; no fallback |
| Policy/guardrail denial | Fail closed; another model is not a bypass |
| Fallback below evaluation threshold | Keep fallback disabled |
| Geography not approved | Keep fallback disabled |

## Change 4: Add the evidence table

| Evidence | Result |
|---|---|
| Primary inference profile | Nova 2 Lite system profile invoked |
| Bounded fallback evaluation | 3/3; score 1.0 |
| Invalid request | No model invocation |
| Policy denial | Failed closed |
| Low evaluation score | Fallback blocked |
| Unapproved geography | Fallback blocked |
| Injected 503 after approval | Nova Micro invoked |
| Fallback response | Marked degraded with evaluation evidence |

Add:

> **Evidence scope:** Run `20260719-g06` executed in `eu-west-2`. Bedrock invocations were real; 429/503 classifications were injected through an application fault seam rather than by attempting to cause a managed-service outage.

## Change 5: Add the implementation excerpt

```python
if reason == "POLICY_DENIED":
    return fail_closed_without_model_invocation()

if status_code in NON_RETRYABLE:
    return return_error_without_fallback()

if transient(status_code) and fallback_evaluation.passed:
    return invoke_fallback(degraded=True)
```

Keep the complete classifier and evaluation runner in the repository rather than reproducing the entire handler.

## Change 6: Add limitations

> The bounded evaluation does not establish general equivalence between Nova Micro and Nova 2 Lite. Production approval requires representative task, safety and adversarial datasets, pinned prompt and model versions, latency and cost thresholds, and repeated evaluation after change. Cross-Region inference profile selection must also satisfy data-residency, geography and Service Control Policy constraints.

## Change 7: Add the visual

Suggested title:

> **Capacity Routing Preserves the Model; Fallback Changes It**

```text
Request → classify failure
              │
      ┌───────┼───────────┐
      ▼       ▼           ▼
 transient  invalid     policy denied
      │       │           │
 profile     stop       fail closed
 routing
      │ still impaired
      ▼
 evaluation + geography gate
      │ pass              │ fail
      ▼                   ▼
 different model      safe failure
 degraded=true
```

## Change 8: Repository links

Link to:

- `code/scenarios/capacity-routing-and-model-fallback/README.md`
- `code/scenarios/capacity-routing-and-model-fallback/src/aws_handlers/handler.py`
- `code/scenarios/capacity-routing-and-model-fallback/infrastructure/template.yaml`
- `code/scenarios/capacity-routing-and-model-fallback/evidence/validated/20260719-g06/README.md`

Suggested immutable tag:

```text
evidence/capacity-routing-model-fallback-20260719-g06
```

