# Validated AWS evidence: 20260719-g06

## Scope

- Region: `eu-west-2`
- Capacity-routing path: `global.amazon.nova-2-lite-v1:0` system inference profile
- Semantic fallback: `amazon.nova-micro-v1:0`
- Evaluation suite: `fallback-contract-v1`
- Deterministic fault injection: HTTP classification seam for 400, 403, 429 and 503 outcomes

## Results

| Contract | Observed result |
|---|---|
| Fallback evaluation | 3/3 bounded cases passed; score 1.0 |
| Healthy primary request | Invoked the Nova 2 Lite inference profile |
| Primary response classification | Not degraded |
| Invalid request | Returned without retry or model invocation |
| Policy denial | Failed closed without model invocation |
| Unapproved geography | Semantic fallback blocked |
| Injected evaluation score 0.33 | Semantic fallback blocked |
| Evaluation restored to 1.0 | Fallback eligibility restored |
| Injected transient 503 | Nova Micro semantic fallback invoked |
| Fallback response | Marked degraded and carried model, suite and score evidence |

Contract result: **PASS**

## Architectural finding

Cross-Region inference and semantic fallback are not the same recovery mechanism. The system inference profile preserved the Nova 2 Lite model contract while allowing Bedrock to route capacity. Switching to Nova Micro changed the model contract and was therefore conditional on an explicit evaluation record, geography approval and transient-fault classification.

## Limitations

- Capacity errors were injected deterministically; the run did not manufacture a real Bedrock regional outage or throttling event.
- The three-case evaluation suite is intentionally bounded and proves only the example contract, not general model equivalence.
- A global inference profile can route outside a workload's preferred geography; production selection must follow residency and SCP requirements.
- Evaluation quality can drift as prompts, models and policies change, so suite and model versions must be pinned and revalidated.
- Changing models may alter safety, latency, cost, tokenization, context limits and output semantics.

