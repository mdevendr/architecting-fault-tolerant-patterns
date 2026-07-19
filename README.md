# Architecting Fault-Tolerant Patterns on AWS

This repository is the architecture and implementation-evidence companion to the article **Architecting AWS Fault-Tolerant Architecture - From Multi-AZ Resilience to AI/ML and GenAI Workloads**.

It is intended for enterprise architects, solution architects, platform architects, technical leaders, and architecture review boards. The repository combines architecture diagrams with bounded AWS experiments that test specific failure contracts.

## Purpose

Fault tolerance is broader than infrastructure availability. A system can remain online while producing stale data, losing workflow state, exhausting shared capacity, returning degraded model output, or making unsafe automated decisions.

The material examines:

- failure containment and blast-radius reduction;
- Multi-AZ and multi-Region recovery;
- state protection, replay, and reconciliation;
- asynchronous shock absorption;
- dependency isolation and graceful degradation;
- controlled deployment and rollback;
- AI/ML data and inference resilience;
- GenAI retrieval, agentic workflows and trust recovery; and
- observable proof that recovery controls work as intended.

## Architecture Principles

1. Define the business failure contract before selecting AWS services.
2. Separate authoritative state from derived and rebuildable state.
3. Contain failures through cells, bulkheads, queues, quotas and bounded concurrency.
4. Design recovery paths as production paths with explicit capacity and ownership.
5. Treat retry, replay, rollback, failover and reconciliation as controlled operations.
6. Distinguish service recovery from data, model and business-trust recovery.
7. Require measurable evidence that a recovery mechanism works as intended.

## Repository Structure

```text
architecture/               Architecture diagrams and retained diagram sources
code/
  scenarios/                Independently executable failure experiments
  shared/                   Shared evidence utilities
docs/
  article/                  Article-supporting architectural material
  article-changes/          Exact article removal and insertion sheets
  article-integration/      Detailed implementation-to-article guidance
evidence/                   Architecture-assurance placeholders and reviewed evidence
```

The `architecture` directory remains the canonical diagram catalogue. The `code/scenarios` directory contains bounded evidence implementations, not general application samples.

## Validated Implementation Evidence

| Failure contract | Validated run | Evidence |
|---|---|---|
| Recovery-storm containment and cell isolation | `20260719-g01` | [Report](code/scenarios/recovery-and-isolation/evidence/validated/20260719-g01/README.md) |
| Exactly-once business outcome under at-least-once execution | `20260719-g02` | [Report](code/scenarios/exactly-once-and-reconciliation/evidence/validated/20260719-g02/README.md) |
| RAG freshness, tenant authorization and provenance recovery | `20260719-g03` | [Report](code/scenarios/rag-and-agent-trust/evidence/validated/20260719-g03/README.md) |
| Governed agent tool execution and compensation | `20260719-g04` | [Report](code/scenarios/governed-agent-recovery/evidence/validated/20260719-g04/README.md) |
| Source-to-derived-state reconciliation | `20260719-g05` | [Report](code/scenarios/derived-state-reconciliation/evidence/validated/20260719-g05/README.md) |
| Capacity routing versus evaluated semantic model fallback | `20260719-g06` | [Report](code/scenarios/capacity-routing-and-model-fallback/evidence/validated/20260719-g06/README.md) |

Each scenario includes:

- a machine-readable failure contract;
- deterministic local tests;
- AWS infrastructure definitions;
- a repeatable fault-injection and evidence runner;
- a sanitized validated result; and
- explicit limitations and article-placement guidance.

## Using the Evidence

The implementations support architectural claims; they are not production capacity recommendations or turnkey production systems. Each result is bounded by its workload, Region, quotas, fault seam and evaluation contract.

When referencing evidence from the article:

1. link to the relevant validated report;
2. link short code excerpts to the exact implementation file;
3. use an immutable commit or evidence tag rather than a moving branch; and
4. retain the documented limitations.

The numbered change sheets in [`docs/article-changes`](docs/article-changes/) specify what to remove, what to add and where each evidence package belongs in the article.

## Architecture Catalogue

Each diagram is a design view rather than a prescriptive deployment template. It communicates the failure boundary, protected capability, containment mechanism, degraded path and operational proof required.

AWS service choices must still be evaluated against workload availability targets, consistency requirements, recovery objectives, regulatory constraints, traffic profile and operational maturity.

## Scope and Safety

- Infrastructure templates deploy bounded evidence stacks and require review before use.
- Raw generated run payloads, credentials, customer data and unreviewed operational logs are excluded from Git.
- Validated evidence reports are sanitized summaries.
- Managed-service outages are not induced; experiments use explicit application fault seams.
- Cost, quotas, Region availability and teardown behaviour must be reviewed before reproduction.

## Author

**Mahesh Devendran** - Cloud Architect focused on secure, scalable, and identity-driven AI platforms across AWS, Azure, and GCP.

My work focuses on zero-trust data access patterns, serverless architecture, AI-driven architectures, predictable resilient systems, and regulated-industry workloads where correctness and clarity matter most.

- LinkedIn: [mahesh-devendran](https://www.linkedin.com/in/mahesh-devendran-83a3b214/)
- Medium: [@mahesh.devendran](https://medium.com/@mahesh.devendran)

## Status

Six evidence packages have completed bounded AWS validation. Article integration, diagram refinement and final publication review remain in progress.
