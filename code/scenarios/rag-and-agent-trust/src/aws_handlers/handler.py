"""AWS handlers for deterministic RAG trust recovery evidence."""

from __future__ import annotations

import json
import os
import time

import boto3


DDB = boto3.client("dynamodb")
S3 = boto3.client("s3")
BEDROCK = boto3.client("bedrock-runtime")
S3VECTORS = boto3.client("s3vectors")
LEDGER_TABLE = os.environ["LEDGER_TABLE"]
SOURCE_BUCKET = os.environ["SOURCE_BUCKET"]
VECTOR_BUCKET_NAME = os.environ["VECTOR_BUCKET_NAME"]
VECTOR_INDEX_NAME = os.environ["VECTOR_INDEX_NAME"]
EMBEDDING_MODEL_ID = os.environ.get(
    "EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0"
)
RUN_ID = os.environ["RUN_ID"]


def emit(metric: str, value: int = 1, **fields: object) -> None:
    payload = {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": "FaultToleranceRagTrust",
                    "Dimensions": [["RunId"]],
                    "Metrics": [{"Name": metric, "Unit": "Count"}],
                }
            ],
        },
        "RunId": RUN_ID,
        metric: value,
        **fields,
    }
    print(json.dumps(payload, separators=(",", ":")))


def ledger_key(tenant_id: str, document_id: str) -> str:
    return f"{tenant_id}#{document_id}"


def get_ledger(tenant_id: str, document_id: str) -> dict | None:
    response = DDB.get_item(
        TableName=LEDGER_TABLE,
        Key={"document_key": {"S": ledger_key(tenant_id, document_id)}},
        ConsistentRead=True,
    )
    return response.get("Item")


def embed(text: str) -> list[float]:
    response = BEDROCK.invoke_model(
        modelId=EMBEDDING_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({"inputText": text, "dimensions": 1024, "normalize": True}),
    )
    payload = json.loads(response["body"].read())
    return payload["embedding"]


def publish_handler(event: dict, _context: object) -> dict:
    tenant_id = event["tenant_id"]
    document_id = event["document_id"]
    source_version = int(event["source_version"])
    text = event["text"]
    source_key = f"{tenant_id}/{document_id}.txt"
    response = S3.put_object(
        Bucket=SOURCE_BUCKET,
        Key=source_key,
        Body=text.encode("utf-8"),
        ContentType="text/plain",
        Metadata={
            "tenant-id": tenant_id,
            "document-id": document_id,
            "source-version": str(source_version),
        },
    )
    version_id = response["VersionId"]
    DDB.put_item(
        TableName=LEDGER_TABLE,
        Item={
            "document_key": {"S": ledger_key(tenant_id, document_id)},
            "tenant_id": {"S": tenant_id},
            "document_id": {"S": document_id},
            "authoritative_version": {"N": str(source_version)},
            "indexed_version": {"N": str(event.get("previous_indexed_version", 0))},
            "ingestion_status": {"S": "PENDING"},
            "source_bucket": {"S": SOURCE_BUCKET},
            "source_key": {"S": source_key},
            "source_version_id": {"S": version_id},
            "policy_version": {"S": event.get("policy_version", "policy-v1")},
            "run_id": {"S": RUN_ID},
        },
    )
    emit("SourcePublished", SourceVersion=source_version)
    return {
        "tenant_id": tenant_id,
        "document_id": document_id,
        "source_version": source_version,
        "source_version_id": version_id,
    }


def ingest_handler(event: dict, _context: object) -> dict:
    tenant_id = event["tenant_id"]
    document_id = event["document_id"]
    ledger = get_ledger(tenant_id, document_id)
    if not ledger:
        raise ValueError("source ledger missing")
    source_version = int(ledger["authoritative_version"]["N"])
    source_version_id = ledger["source_version_id"]["S"]
    source_key = ledger["source_key"]["S"]
    response = S3.get_object(
        Bucket=SOURCE_BUCKET,
        Key=source_key,
        VersionId=source_version_id,
    )
    text = response["Body"].read().decode("utf-8")
    embedding = embed(text)
    vector_key = f"{tenant_id}#{document_id}#v{source_version}"
    source_uri = f"s3://{SOURCE_BUCKET}/{source_key}?versionId={source_version_id}"
    S3VECTORS.put_vectors(
        vectorBucketName=VECTOR_BUCKET_NAME,
        indexName=VECTOR_INDEX_NAME,
        vectors=[
            {
                "key": vector_key,
                "data": {"float32": embedding},
                "metadata": {
                    "tenant_id": tenant_id,
                    "document_id": document_id,
                    "source_version": source_version,
                    "source_uri": source_uri,
                    "source_text": text,
                },
            }
        ],
    )
    DDB.update_item(
        TableName=LEDGER_TABLE,
        Key={"document_key": {"S": ledger_key(tenant_id, document_id)}},
        UpdateExpression="SET indexed_version=:version, ingestion_status=:complete, indexed_at=:now",
        ConditionExpression="authoritative_version=:version AND source_version_id=:version_id",
        ExpressionAttributeValues={
            ":version": {"N": str(source_version)},
            ":version_id": {"S": source_version_id},
            ":complete": {"S": "COMPLETE"},
            ":now": {"N": str(int(time.time()))},
        },
    )
    emit("IngestionCompleted", SourceVersion=source_version)
    return {
        "tenant_id": tenant_id,
        "document_id": document_id,
        "indexed_version": source_version,
        "vector_key": vector_key,
    }


def safe_non_answer(reason: str, **evidence: object) -> dict:
    emit("SafeNonAnswer", Reason=reason)
    return {
        "status": "SAFE_NON_ANSWER",
        "reason": reason,
        "answer": None,
        "citations": [],
        "evidence": evidence,
    }


def gateway_handler(event: dict, _context: object) -> dict:
    caller_tenant = event["caller_tenant"]
    document_tenant = event.get("document_tenant", caller_tenant)
    document_id = event["document_id"]
    if caller_tenant != document_tenant:
        emit("AuthorizationRejected")
        return safe_non_answer("CALLER_NOT_AUTHORIZED")

    ledger = get_ledger(document_tenant, document_id)
    if not ledger:
        return safe_non_answer("SOURCE_LEDGER_MISSING")
    authoritative_version = int(ledger["authoritative_version"]["N"])
    indexed_version = int(ledger["indexed_version"]["N"])
    ingestion_status = ledger["ingestion_status"]["S"]
    if ingestion_status != "COMPLETE":
        return safe_non_answer(
            "INGESTION_NOT_COMPLETE",
            authoritative_version=authoritative_version,
            indexed_version=indexed_version,
        )
    if indexed_version != authoritative_version:
        return safe_non_answer(
            "INDEX_VERSION_STALE",
            authoritative_version=authoritative_version,
            indexed_version=indexed_version,
        )

    query_embedding = embed(event["query"])
    emit("VectorQueryAttempt")
    response = S3VECTORS.query_vectors(
        vectorBucketName=VECTOR_BUCKET_NAME,
        indexName=VECTOR_INDEX_NAME,
        queryVector={"float32": query_embedding},
        topK=int(event.get("top_k", 3)),
        filter={
            "$and": [
                {"tenant_id": {"$eq": caller_tenant}},
                {"document_id": {"$eq": document_id}},
                {"source_version": {"$eq": authoritative_version}},
            ]
        },
        returnMetadata=True,
        returnDistance=True,
    )
    valid_hits = []
    for hit in response.get("vectors", []):
        metadata = hit.get("metadata", {})
        if metadata.get("tenant_id") != caller_tenant:
            emit("CrossTenantContextRejected")
            return safe_non_answer("CROSS_TENANT_CONTEXT")
        if metadata.get("document_id") != document_id:
            continue
        if int(metadata.get("source_version", -1)) != authoritative_version:
            return safe_non_answer("RETRIEVED_VERSION_STALE")
        if not metadata.get("source_uri"):
            return safe_non_answer("PROVENANCE_MISSING")
        valid_hits.append(hit)
    if not valid_hits:
        return safe_non_answer("NO_AUTHORIZED_CURRENT_CONTEXT")

    best = valid_hits[0]["metadata"]
    citation = (
        f"{best['source_uri']}#document={document_id}&version={authoritative_version}"
    )
    emit("TrustedResponse", SourceVersion=authoritative_version)
    return {
        "status": "ANSWER",
        "reason": "TRUST_CONTRACT_SATISFIED",
        "answer": best["source_text"],
        "citations": [citation],
        "evidence": {
            "authoritative_version": authoritative_version,
            "indexed_version": indexed_version,
            "tenant_id": caller_tenant,
            "policy_version": ledger["policy_version"]["S"],
        },
    }
