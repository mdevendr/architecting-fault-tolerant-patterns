# Capacity Routing Versus Semantic Model Fallback

## Architectural objective

A capacity-routing control should preserve the selected model contract. A semantic fallback deliberately changes that contract and therefore requires independent evaluation, geography approval and explicit degraded-response handling.

## Validated architecture

The primary path invokes the Bedrock system inference profile `global.amazon.nova-2-lite-v1:0`. The fallback path invokes `amazon.nova-micro-v1:0` only when all of these conditions hold:

1. the failure is classified as transient, such as an injected 429 or 503;
2. the fallback evaluation suite version matches the deployed contract;
3. its approved score meets the declared threshold; and
4. the request geography is approved.

Invalid requests and policy denials never route to another model. Low-scoring or geographically disallowed fallbacks remain disabled.

## Validated result

Run `20260719-g06` used real Bedrock calls. The fallback model scored 1.0 across three bounded deterministic cases. A healthy request used the Nova 2 Lite inference profile and was not marked degraded. Injected invalid and policy failures invoked no model. Geography and low-evaluation tests blocked semantic fallback. After evaluation was restored, an injected 503 selected Nova Micro and returned the fallback model ID, evaluation suite, score and `degraded=true`.

## Interpretation

The experiment does not claim that Nova Micro is generally equivalent to Nova 2 Lite. It proves that a different model can be admitted for one small, declared task contract. Broader workloads require representative evaluation datasets and separate safety, quality, latency and cost thresholds.

