# Capacity Routing Versus Semantic Model Fallback

This scenario treats Bedrock cross-Region inference and changing foundation models as different architectural controls.

- Capacity routing keeps the model contract stable while Bedrock routes within an approved inference profile.
- Semantic fallback changes model behaviour and is allowed only after task-specific evaluation.
- Invalid requests and policy failures never trigger fallback.
- Fallback responses expose the selected model and degraded contract.

The cloud experiment will use deterministic 429/503 injection rather than claiming to cause a real Bedrock capacity event.

