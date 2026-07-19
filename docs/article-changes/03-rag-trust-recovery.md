# Article Change Sheet 03: RAG Trust Recovery

Apply these changes by section heading; do not use PDF page numbers.

## Change 1: Add the validated implementation

### Find

The **Context and Retrieval (RAG)** section that discusses ingestion failure, vector-index lag and tenant isolation.

### Placement

Insert after the architectural controls for retrieval freshness and authorization, and before the section moves to model invocation or fallback.

### Add this heading

#### Validated Reference Implementation: Refuse Retrieval Until Trust Recovers

### Add this text

> A controlled AWS experiment separated service recovery from trust recovery. A versioned Amazon S3 document was registered in a DynamoDB source/index ledger and embedded with Amazon Titan Text Embeddings V2 into Amazon S3 Vectors. The retrieval gateway compared the authoritative source version, indexed version and ingestion state before invoking either the embedding model or vector search.
>
> The source was advanced from version 1 to version 2 while ingestion was deliberately withheld. The query path remained available, but returned a safe non-answer with evidence that the authoritative version was 2 and the indexed version was 1. A caller from another tenant was rejected before retrieval. After version 2 was indexed, the trust gate reopened and returned the current text with a versioned S3 citation.
>
> Tenant identity, document identity and authoritative source version were enforced inside the S3 Vectors metadata query. This matters because the first test filtered only by tenant: after recovery, semantic similarity still ranked the obsolete version-1 vector first. The stricter in-query contract removed the stale candidate and excluded a deliberately indexed cross-tenant distractor.

## Change 2: Add the evidence table

| Injected condition | Observed decision |
|---|---|
| Source and index both at version 1 | Answer with version-1 citation |
| Source at version 2; index at version 1 | Safe non-answer |
| Tenant-b caller requests tenant-a document | Caller not authorized |
| Tenant-b distractor present in vector index | Excluded from tenant-a candidates |
| Source and index converge at version 2 | Answer with version-2 citation |

Add below the table:

> **Evidence scope:** Run `20260719-g03` executed in `eu-west-1`. The run proves retrieval freshness, tenant authorization and source provenance. It does not claim to validate arbitrary generated statements.

## Change 3: Add one implementation excerpt

Use this shortened excerpt from the deployed gateway:

```python
if ingestion_status != "COMPLETE":
    return safe_non_answer(
        "INGESTION_NOT_COMPLETE",
        authoritative_version=authoritative_version,
        indexed_version=indexed_version,
    )

if authoritative_version != indexed_version:
    return safe_non_answer(
        "SOURCE_INDEX_VERSION_MISMATCH",
        authoritative_version=authoritative_version,
        indexed_version=indexed_version,
    )
```

Then show the in-query boundary compactly:

```python
filter={"$and": [
    {"tenant_id": {"$eq": caller_tenant}},
    {"document_id": {"$eq": document_id}},
    {"source_version": {"$eq": authoritative_version}},
]}
```

Add:

> Simplified excerpts from the deployed reference implementation; the complete gateway, ingestion function, infrastructure and evidence runner are available in the repository.

## Change 4: Cross-reference service and trust recovery

### Find

The introductory distinction between **Service Recovery** and **Trust Recovery**.

### Add this final sentence

> The RAG implementation later in this article demonstrates the distinction: the query service remains available while stale or unauthorized context is refused, and normal answers resume only when current, authorized and traceable evidence is available.

## Change 5: Bound Automated Reasoning claims

Where Amazon Bedrock Automated Reasoning is mentioned, use:

> Automated Reasoning checks can add a detect-only assessment of generated content against formalized policy rules in supported Regions. They complement, but do not replace, retrieval authorization, source/index freshness, provenance checks or application response controls.

Do not describe Automated Reasoning as:

- a universal hallucination detector;
- an enforcement mechanism by itself;
- a freshness or tenant-authorization control; or
- a zero-latency validation step.

## Change 6: Add limitations

> The reference run returns deterministic retrieved source text rather than free-form generated prose. Production implementations also require deletion and tombstone propagation, chunk lineage, re-embedding policy, scale and tail-latency tests, and a defined response when the trust gate cannot establish current evidence.

## Change 7: Add the visual

Suggested title:

> **Service Available; Trust Not Yet Recovered**

Show two adjacent paths:

```text
Service path: query endpoint → embedding → vector store       AVAILABLE
Trust path:   source v2 → ingestion pending → index v1        NOT RECOVERED
                              │
                              ▼
                       SAFE NON-ANSWER
                              │
                    index converges to v2
                              │
                              ▼
                authorized v2 result + provenance
```

## Change 8: Repository links

After push, link to:

- `code/scenarios/rag-and-agent-trust/README.md`
- `code/scenarios/rag-and-agent-trust/src/aws_handlers/handler.py`
- `code/scenarios/rag-and-agent-trust/infrastructure/template.yaml`
- `code/scenarios/rag-and-agent-trust/evidence/validated/20260719-g03/README.md`

Use an immutable tag or commit. Suggested tag:

```text
evidence/rag-trust-recovery-20260719-g03
```

