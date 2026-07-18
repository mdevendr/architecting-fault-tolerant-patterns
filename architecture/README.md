# Architecture Catalogue

This directory contains the visual architecture views supporting the article **Architecting AWS Fault-Tolerant Architecture - From Multi-AZ Resilience to AI/ML and GenAI Workloads**.

The diagrams communicate failure boundaries, containment mechanisms, recovery paths, state transitions, governance controls, and operational feedback loops. They are architectural views rather than deployable reference implementations.

## Current Architecture Views

The catalogue currently includes views covering:

- advanced fault-tolerance domains and capability boundaries
- AI/ML ingestion, feature management, training, evaluation, and deployment
- write-time data-quality and freshness controls
- compute bulkheads and recoverable training state
- circuit breaking and dependency protection
- multi-Region routing and recovery control
- runtime request processing and degraded operation
- stream buffering, backpressure, and controlled recovery
- GenAI retrieval and RAG fault tolerance
- agentic workflow resilience
- AI service recovery versus trust recovery

## File Types

- `.jpg` files are rendered architecture views suitable for the article and architecture discussions.
- `.mmd` files are retained Mermaid sources for selected AI and GenAI architecture views.

## Interpretation

Each diagram should make the following concerns visible where applicable:

1. The workload capability and failure boundary.
2. The authoritative state or business invariant being protected.
3. The mechanism used to contain or absorb failure.
4. The degraded, retry, replay, rollback, or failover path.
5. The control-plane decision and operational ownership.
6. The telemetry or evidence required to confirm recovery.

The diagrams intentionally avoid presenting one universal AWS topology. Service selection and recovery design must be derived from workload-specific availability objectives, consistency requirements, regulatory constraints, traffic characteristics, and operational maturity.

## Evolution

Additional diagrams may be added as new architectural patterns are assessed for the article. Superseded views should be removed or clearly identified so that this directory remains the canonical architecture catalogue.
