"""Version-aware projection, poison isolation and bounded reconciliation."""

import json
import os
import time

import boto3
from boto3.dynamodb.types import TypeDeserializer
from botocore.exceptions import ClientError


DDB = boto3.client("dynamodb")
SQS = boto3.client("sqs")
SOURCE_TABLE = os.environ["SOURCE_TABLE"]
PROJECTION_TABLE = os.environ["PROJECTION_TABLE"]
QUARANTINE_URL = os.environ["QUARANTINE_URL"]
DESERIALIZER = TypeDeserializer()


def decode(image: dict) -> dict:
    return {key: DESERIALIZER.deserialize(value) for key, value in image.items()}


def project_record(record: dict) -> str:
    event_id = record.get("eventID", "synthetic")
    image = record.get("dynamodb", {}).get("NewImage")
    if not image:
        return "IGNORED_DELETE"
    item = decode(image)
    if item.get("inject_poison"):
        SQS.send_message(
            QueueUrl=QUARANTINE_URL,
            MessageBody=json.dumps({"event_id": event_id, "record_id": item["record_id"]}),
        )
        return "QUARANTINED"
    if item.get("inject_skip_projection"):
        return "INTENTIONALLY_SKIPPED"

    now = int(time.time())
    try:
        DDB.put_item(
            TableName=PROJECTION_TABLE,
            Item={
                "record_id": {"S": item["record_id"]},
                "version": {"N": str(item["version"])},
                "value": {"S": item["value"]},
                "source_event_id": {"S": event_id},
                "projected_at": {"N": str(now)},
            },
            ConditionExpression="attribute_not_exists(record_id) OR #version < :incoming",
            ExpressionAttributeNames={"#version": "version"},
            ExpressionAttributeValues={":incoming": {"N": str(item["version"])}},
        )
        return "APPLIED"
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return "DUPLICATE_OR_STALE"
        raise


def projection_handler(event, _context):
    records = event if isinstance(event, list) else event.get("Records", [event])
    outcomes = [{"event_id": record.get("eventID"), "outcome": project_record(record)} for record in records]
    return {"batchItemFailures": [], "outcomes": outcomes}


def scan(table_name: str) -> dict:
    response = DDB.scan(TableName=table_name, ConsistentRead=True)
    items = {}
    for raw in response.get("Items", []):
        item = decode(raw)
        items[item["record_id"]] = item
    return items


def reconciliation_handler(event, _context):
    repair = bool(event.get("repair", False))
    source = scan(SOURCE_TABLE)
    projection = scan(PROJECTION_TABLE)
    source_keys = set(source)
    projection_keys = set(projection)
    missing = sorted(source_keys - projection_keys)
    extra = sorted(projection_keys - source_keys)
    mismatched = sorted(
        key for key in source_keys & projection_keys
        if int(source[key]["version"]) != int(projection[key]["version"])
        or source[key]["value"] != projection[key]["value"]
    )
    repaired = 0
    if repair:
        for key in missing + mismatched:
            item = source[key]
            DDB.put_item(
                TableName=PROJECTION_TABLE,
                Item={
                    "record_id": {"S": key},
                    "version": {"N": str(item["version"])},
                    "value": {"S": item["value"]},
                    "source_event_id": {"S": "RECONCILIATION"},
                    "projected_at": {"N": str(int(time.time()))},
                },
            )
            repaired += 1
        for key in extra:
            DDB.delete_item(TableName=PROJECTION_TABLE, Key={"record_id": {"S": key}})
            repaired += 1
    return {
        "missing": missing,
        "extra": extra,
        "mismatched": mismatched,
        "missing_count": len(missing),
        "extra_count": len(extra),
        "version_or_value_mismatch_count": len(mismatched),
        "repaired_count": repaired,
        "source_count": len(source),
        "projection_count": len(projection),
    }

