# Infrastructure

The primary path invokes the `global.amazon.nova-2-lite-v1:0` system inference profile. This preserves one model contract while allowing Bedrock to route capacity within that profile's geography.

The semantic fallback uses `amazon.nova-micro-v1:0`, a different model. It is enabled only when a versioned evaluation record meets the declared threshold and the request geography is approved. Deterministic injected HTTP classifications drive recovery decisions; the experiment does not claim to manufacture a real Bedrock regional outage or throttling event.

