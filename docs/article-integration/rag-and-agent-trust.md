# RAG Trust Recovery

## Architectural objective

The query service being available is not sufficient evidence that a RAG response is safe to serve. Trust recovery requires proof that the retrieved context is current, authorized for the caller and traceable to an authoritative source version.

The validated trust gate applies controls in this order:

1. authenticate the caller's tenant boundary;
2. read the authoritative and indexed versions from the document ledger;
3. refuse retrieval while ingestion is incomplete or versions differ;
4. embed the query only after the pre-retrieval checks pass;
5. enforce tenant, document and authoritative version inside the vector query; and
6. require provenance before returning the retrieved text.

## Deployed architecture

```text
Versioned S3 source ── publish ──► DynamoDB version ledger
       │                              │
       └── exact VersionId ──► ingest │
                                │     │
                           Titan embedding
                                │
                                ▼
                  S3 Vectors + trust metadata

Caller ──► Trust gateway ──► version/status check
                              │
                    fail ─────┴───── pass
                      │                 │
              safe non-answer     filtered vector query
                                        │
                                 provenance check
                                        │
                              answer + versioned citation
```

## Validated AWS run

Run `20260719-g03` in `eu-west-1` first established a valid version-1 response. The source was then advanced to version 2 without updating the vector index. Although the service remained reachable, the gateway returned a safe non-answer and recorded authoritative version 2 against indexed version 1. A tenant-b caller was separately refused access to the tenant-a document.

A tenant-b distractor containing a distinctive incorrect value was then indexed. After tenant-a version 2 was ingested, the gateway reopened and returned the new value with a version-2 S3 citation. The tenant-b vector was excluded by metadata evaluated as part of S3 Vectors candidate selection.

The first recovery attempt also exposed an older-version ranking defect. Filtering on tenant alone allowed the obsolete version-1 vector to rank ahead of version 2. The final design therefore binds retrieval to tenant, document identity and authoritative source version inside the vector query.

## Evidence summary

| Contract | Result |
|---|---|
| Current authorized context may be served | Passed |
| Stale source/index state must not be served | Passed |
| Cross-tenant request must be rejected | Passed |
| Recovery requires source/index convergence | Passed |
| Latest answer must carry versioned provenance | Passed |
| Cross-tenant distractor must be excluded in-query | Passed |

## Architectural interpretation

This implementation separates two recovery paths:

- **Service recovery:** the query endpoint, embedding model and vector store accept requests.
- **Trust recovery:** the source and index versions converge, authorization passes and the selected context carries valid provenance.

The system deliberately remains available to return a safe non-answer while trust has not recovered.

## Automated Reasoning boundary

Amazon Bedrock Automated Reasoning checks can provide an additional, detect-only assessment against formal policy rules in supported Regions. They do not replace tenant authorization, source/index freshness, provenance validation or application-level response handling. They also add latency and require policies suitable for formalization. Treat them as an optional post-generation evidence layer, not as the RAG trust gate itself.

## Limitations

- The cloud run returns deterministic retrieved source text rather than free-form generated prose.
- Scale, retrieval quality and tail latency require separate tests.
- Production pipelines need deletion/tombstone propagation and chunk-level lineage.
- Clock-age freshness can complement, but should not replace, explicit source/index version comparison.

