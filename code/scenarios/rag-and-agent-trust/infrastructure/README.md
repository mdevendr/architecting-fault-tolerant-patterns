# AWS RAG trust implementation

The stack deploys a versioned S3 authoritative source, DynamoDB source/index ledger, S3 vector bucket and index, Titan embedding path, and three Lambda functions:

- publish source and advance the authoritative version;
- ingest the exact S3 object version and advance the indexed version; and
- enforce freshness, authorization and provenance before returning an answer.

The gateway returns a controlled non-answer before embedding or vector query when ingestion is incomplete or the index version is stale.

The cloud evidence runner will validate:

1. current authorized retrieval with a versioned citation;
2. source update without ingestion, producing a safe non-answer;
3. cross-tenant access rejection;
4. ingestion recovery and a new versioned citation; and
5. tenant metadata filtering inside S3 Vectors.

## Deploy and run

```powershell
./deploy.ps1 -RunId 20260719-g03 -Profile melon
./run-cloud-experiment.ps1 -RunId 20260719-g03 -Profile melon
```
