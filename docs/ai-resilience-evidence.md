# AI/ML and GenAI Resilience Evidence

Traditional resilience evidence often focuses on uptime, health checks, queue depth, failover, and backup restore. AI workloads need those signals, but also need trust signals.

## Service Signals

- model invocation count
- model invocation errors
- inference latency
- timeout count
- throttling count
- Step Functions execution status
- Lambda error count
- DLQ depth

## Trust Signals

- model ID or inference profile ID
- prompt version
- retrieval index version
- source document version
- guardrail policy version
- guardrail block count
- stale retrieval block count
- fallback count
- degraded response count
- human escalation count
- answer quality or grounding validation result

## Evidence Capture Checklist

For every lab, capture:

- architecture diagram or simple flow
- deployment command and output
- failure injection command
- expected behaviour
- actual behaviour
- CloudWatch metrics or logs
- screenshots
- cleanup command
- cost notes

## Article Language

Use this framing in the Medium article:

> The platform is not recovered simply because the model responds. It is recovered when the response is current, grounded, safe, authorised, and traceable.
