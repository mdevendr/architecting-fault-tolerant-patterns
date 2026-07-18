# Architecting Fault-Tolerant Patterns on AWS

This repository is the architecture companion to the article **Architecting AWS Fault-Tolerant Architecture - From Multi-AZ Resilience to AI/ML and GenAI Workloads**.

It provides architecture diagrams and supporting design material for evaluating fault tolerance across AWS workloads. The repository is intended for enterprise architects, solution architects, platform architects, technical leaders, and architecture review boards.

## Purpose

Fault tolerance is broader than infrastructure availability. A system can remain online while producing stale data, losing workflow state, exhausting shared capacity, returning degraded model output, or making unsafe automated decisions.

The architecture material in this repository examines resilience across several related dimensions:

- failure containment and blast-radius reduction
- Multi-AZ and multi-Region recovery
- state protection, replay, and reconciliation
- asynchronous shock absorption
- dependency isolation and graceful degradation
- controlled deployment and rollback
- AI/ML data, training, registry, and inference resilience
- GenAI retrieval, agentic workflow, and trust recovery
- observability, operational evidence, and recovery governance

## Architecture Principles

The diagrams are guided by the following principles:

1. Define the business failure contract before selecting AWS services.
2. Separate authoritative state from derived and rebuildable state.
3. Contain failures through cells, bulkheads, queues, quotas, and bounded concurrency.
4. Design recovery paths as production paths with explicit capacity and ownership.
5. Treat retries, replay, rollback, failover, and reconciliation as controlled operations.
6. Distinguish service recovery from data, model, and business-trust recovery.
7. Require observable evidence that a recovery mechanism works as intended.

## Repository Structure

```text
architecture/
  *.jpg       Rendered architecture diagrams used by the article
  *.mmd       Retained Mermaid sources for selected architecture views
docs/         Supporting architectural notes and article material
evidence/     Architecture assurance and operational evidence, when available
```

The `architecture` directory is the canonical catalogue of diagrams. Additional architecture views may be added as the article and its supporting analysis evolve.

## Using the Architecture Catalogue

Each diagram should be read as a design view rather than a prescriptive deployment template. It communicates:

- the failure boundary being addressed
- the state or capability that must be protected
- the primary containment or recovery mechanism
- the relevant control and data flows
- the expected degraded or recovery path
- the operational signals needed to govern the design

AWS service choices must be validated against the workload's availability targets, consistency requirements, recovery objectives, regulatory constraints, traffic profile, and operational maturity.

## Scope

This repository contains architecture-level material. It is not a software-development project, deployable reference implementation, or collection of production-ready infrastructure templates.

Any future implementation evidence will be assessed separately and included only when it directly supports an architectural claim and has been validated against an explicit failure scenario.

## Article Reference

The associated article develops the full narrative, including failure semantics, architectural trade-offs, AWS service selection, AI/ML resilience, and operational recovery considerations. This repository provides stable visual references that can be linked from the relevant article sections.

## Author

**Mahesh Devendran** - Cloud Architect focused on secure, scalable, and identity-driven AI platforms across AWS, Azure, and GCP.

My work focuses on zero-trust data access patterns, serverless architecture, AI-driven architectures, predictable resilient systems, and regulated-industry workloads where correctness and clarity matter most.

- LinkedIn: [mahesh-devendran](https://www.linkedin.com/in/mahesh-devendran-83a3b214/)
- Medium: [@mahesh.devendran](https://medium.com/@mahesh.devendran)

## Status

The architecture catalogue is evolving alongside the article. Diagram names, captions, and supporting notes may be refined before publication.
