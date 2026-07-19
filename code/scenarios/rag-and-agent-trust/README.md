# RAG and Agent Trust Recovery

This scenario distinguishes service availability from trustworthiness. It blocks or escalates responses when retrieval context is stale, unauthorized, unattributable or inconsistent with a bounded policy.

The first implementation slice covers:

- authoritative source version versus indexed version;
- ingestion completion state;
- tenant-scoped retrieval metadata;
- retrieved source provenance;
- safe non-answer and human-review outcomes; and
- policy consistency as an independent post-generation control.

The local deterministic model validates control ordering before AWS deployment. Local tests are not cloud evidence.

## Local tests

```powershell
python -m unittest discover -s code/scenarios/rag-and-agent-trust/tests -v
```

## Current AWS design direction

- Versioned S3 objects provide the authoritative source.
- DynamoDB records authoritative and indexed versions plus ingestion status.
- Amazon Titan Text Embeddings V2 generates embeddings.
- Amazon S3 Vectors stores vectors with tenant, document, source-version and provenance metadata.
- Metadata filters are applied inside `QueryVectors`, not after retrieval.
- Amazon Bedrock Automated Reasoning checks are optional policy-consistency evidence in a supported EU Region; they are not a freshness or authorization control.

