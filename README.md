# Architecting Fault-Tolerant Patterns on AWS

Companion evidence repository for the Medium article:

> Architecting AWS Fault-Tolerant Architecture - From Multi-AZ Resilience to AI/ML and GenAI Workloads

This repository is structured as a set of small AWS failure labs. Each lab proves one resilience behaviour with implementation, controlled failure injection, and operational evidence.

The first focus is AI/ML and GenAI resilience, because those failure modes are less commonly covered than standard Multi-AZ, queue, backup, and disaster-recovery patterns.

## Evidence Themes

- Bedrock invocation observability
- Model fallback and degraded responses
- Guardrail intervention and safe refusal
- RAG freshness and grounding checks
- Agent tool-call circuit breakers
- Prompt version rollback

## Repository Structure

```text
docs/
  article-evidence-map.md
  ai-resilience-evidence.md
labs/
  01-bedrock-invocation-observability/
  02-model-fallback-step-functions/
  03-guardrail-intervention/
  04-rag-freshness-gate/
  05-agent-tool-circuit-breaker/
  06-prompt-version-rollback/
evidence/
  screenshots/
  logs/
  cloudwatch/
scripts/
```

## Lab Pattern

Each lab follows the same evidence contract:

1. What this proves.
2. AWS services used.
3. Failure injected.
4. Expected resilience behaviour.
5. Evidence captured.
6. How to deploy.
7. How to run the failure test.
8. How to clean up.

## Shell Convention

All automation scripts in this repository use Git Bash compatible `.sh` scripts. PowerShell scripts are intentionally avoided.

## Status

This repository is private while evidence is being produced. It can be made public once the screenshots, logs, deployment scripts, and cleanup steps are complete.
