# Validated AWS evidence: 20260719-g03

## Scope

- Region: `eu-west-1`
- Execution environment: AWS
- Source of truth: versioned Amazon S3 objects plus a DynamoDB version ledger
- Embeddings: Amazon Titan Text Embeddings V2
- Retrieval: Amazon S3 Vectors with in-query metadata enforcement
- Test tenants: `tenant-a` and `tenant-b`

## Failure sequence and results

| Failure or control | Observed result |
|---|---|
| Current tenant-a document at source/index version 1 | Answer served with a version-1 citation |
| Source advanced to version 2 without ingestion | `SAFE_NON_ANSWER` |
| Stale evidence recorded | Authoritative version 2; indexed version 1 |
| Tenant-b caller requested tenant-a document | `CALLER_NOT_AUTHORIZED` |
| Tenant-b distractor indexed with a highly distinctive value | Excluded from tenant-a retrieval |
| Tenant-a version 2 ingested | Trust gate reopened |
| Recovered response | Version-2 text and version-2 S3 citation returned |

Contract result: **PASS**

## What the run demonstrates

- Service availability alone did not authorize an answer: the gateway refused retrieval while ingestion was incomplete.
- The freshness decision was based on an authoritative source/index version comparison, not wall-clock age alone.
- Tenant, document identity and authoritative source version were enforced inside the S3 Vectors query.
- A cross-tenant caller was rejected before embedding or vector retrieval.
- Recovery meant restoring a current, authorized and traceable response, not merely restoring the query endpoint.
- The final response carried the authoritative version, indexed version, tenant and policy version as evidence.

## Defect discovered by the experiment

The first recovery run filtered only by tenant. After version 2 was indexed, semantic similarity still ranked the older version-1 vector first, so the trust gate correctly refused the result. The implementation was corrected to enforce tenant, document identity and authoritative source version together in the vector query. The repeated run passed.

## Limitations

- The returned text is deterministic retrieved content; this run does not claim to validate free-form model generation.
- Amazon Bedrock Automated Reasoning is complementary detect-only validation and was not required for the core freshness, authorization and provenance contract.
- The scenario uses one document per tenant for inspectable evidence; scale, recall and latency testing are separate concerns.
- A production ingestion pipeline also needs deletion/tombstone handling, chunk lineage, re-embedding policy and bounded recovery objectives.

