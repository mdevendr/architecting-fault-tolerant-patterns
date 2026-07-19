# Architecting Fault-Tolerant Patterns on AWS

This repository is the architecture companion to the article **Architecting AWS Fault-Tolerant Architecture - From Multi-AZ Resilience to AI/ML and GenAI Workloads**.

It is intended for enterprise architects, solution architects, platform architects, technical leaders and architecture review boards. It provides architecture views and validated evidence for reasoning about how AWS workloads behave when dependencies, data flows, models or automated workflows are impaired.

## Architectural Scope

Fault tolerance is broader than infrastructure availability. A capability may remain online while producing stale data, losing workflow state, exhausting shared capacity, returning degraded model output or making unsafe automated decisions.

The architectural scope includes:

- Availability Zone and Region failure tolerance;
- failure containment and blast-radius reduction;
- shock absorption, backpressure and recovery-storm control;
- authoritative-state protection, replay and reconciliation;
- dependency isolation and graceful degradation;
- deployment safety and rollback;
- AI/ML data and inference resilience;
- RAG freshness, authorization and provenance;
- governed agent actions and compensating recovery; and
- operational evidence that recovery controls satisfy the failure contract.

## Architecture Principles

1. Define the business failure contract before selecting an AWS pattern.
2. Treat availability, resilience and fault tolerance as related but distinct properties.
3. Separate authoritative state from derived and rebuildable state.
4. Contain failures through cells, bulkheads, queues, quotas and bounded concurrency.
5. Design recovery paths with explicit capacity, ownership and safe replay.
6. Treat retry, rollback, failover and reconciliation as controlled operations.
7. Separate service recovery from data, model and business-trust recovery.
8. Require measurable proof that the capability recovered safely.

## Architecture Catalogue

The [`architecture`](architecture/) directory is the canonical diagram catalogue. Each diagram is a design view rather than a prescriptive deployment template. It should identify:

- the business capability and failure boundary;
- the authoritative state that must be protected;
- the containment, degradation or recovery mechanism;
- dependencies across data and control planes;
- the expected behaviour while impaired; and
- the telemetry needed to prove recovery.

AWS service choices must be evaluated against workload availability targets, consistency requirements, RTO and RPO, data-loss tolerance, regulatory constraints, traffic profile and operational maturity.

## Architectural Validation Evidence

The repository includes six bounded AWS experiments. Their purpose is to validate architectural claims, not to present general application examples or production capacity recommendations.

| Architectural question | Validated evidence |
|---|---|
| Can queued work recover without overwhelming a returning dependency or affecting a healthy cell? | [Recovery-storm containment and cell isolation](code/scenarios/recovery-and-isolation/evidence/validated/20260719-g01/README.md) |
| Can at-least-once execution still produce one business outcome and convergent derived state? | [Exactly-once business outcome](code/scenarios/exactly-once-and-reconciliation/evidence/validated/20260719-g02/README.md) |
| Can an available RAG service refuse stale or cross-tenant context until trust recovers? | [RAG trust recovery](code/scenarios/rag-and-agent-trust/evidence/validated/20260719-g03/README.md) |
| Can policy prevent an unauthorized agent action while replay and compensation remain safe? | [Governed agent recovery](code/scenarios/governed-agent-recovery/evidence/validated/20260719-g04/README.md) |
| Can an asynchronous projection detect and repair missing, extra and mismatched state? | [Source-to-derived-state reconciliation](code/scenarios/derived-state-reconciliation/evidence/validated/20260719-g05/README.md) |
| Can capacity routing be separated from a semantic model change and its quality contract? | [Capacity routing versus model fallback](code/scenarios/capacity-routing-and-model-fallback/evidence/validated/20260719-g06/README.md) |

Each evidence report states the injected failure, observed recovery behaviour and limitations. Implementation mechanics and reproduction guidance remain under [`code`](code/README.md), keeping this landing page focused on architectural decisions.

## Repository Structure

```text
architecture/               Canonical architecture diagrams
code/                       Bounded validation implementations and evidence
evidence/                   Reviewed architecture-assurance material
```

## Using This Repository

Use the repository to support architecture reviews and article claims:

1. begin with the relevant failure contract;
2. use the diagram to understand boundaries and recovery paths;
3. inspect the validated evidence before accepting the architectural claim;
4. retain the stated limitations and service-selection trade-offs; and
5. cite an immutable commit or evidence tag rather than a moving branch.

## Boundaries

- The diagrams are not universal reference architectures.
- The evidence workloads are bounded experiments, not production benchmarks.
- Managed-service outages are not induced; controlled application fault seams are used.
- A successful experiment validates only its declared failure contract and configuration.
- Production adoption requires independent security, cost, quota, performance and regulatory review.

## Author

**Mahesh Devendran** - Cloud Architect focused on secure, scalable, and identity-driven AI platforms across AWS, Azure, and GCP.

My work focuses on zero-trust data access patterns, serverless architecture, AI-driven architectures, predictable resilient systems, and regulated-industry workloads where correctness and clarity matter most.

- LinkedIn: [mahesh-devendran](https://www.linkedin.com/in/mahesh-devendran-83a3b214/)
- Medium: [@mahesh.devendran](https://medium.com/@mahesh.devendran)

## Status

Six architectural evidence packages have completed bounded AWS validation. Article integration, diagram refinement and final publication review remain in progress.
