"""AWS handlers for exactly-once outcome and derived-state reconciliation evidence."""

from __future__ import annotations

from decimal import Decimal
import json
import os
import time
from uuid import uuid4

import boto3
from boto3.dynamodb.types import TypeDeserializer
from botocore.exceptions import ClientError


DDB = boto3.client("dynamodb")
OPERATIONS_TABLE = os.environ["OPERATIONS_TABLE"]
PROVIDER_TABLE = os.environ["PROVIDER_TABLE"]
OUTBOX_TABLE = os.environ["OUTBOX_TABLE"]
PROJECTION_TABLE = os.environ["PROJECTION_TABLE"]
RUN_ID = os.environ["RUN_ID"]
DESERIALIZER = TypeDeserializer()


class ExecutionBusy(Exception):
    pass


class InjectedCrash(Exception):
    pass


def emit(metric: str, value: int = 1, **fields: object) -> None:
    payload = {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": "FaultToleranceExactlyOnce",
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


def get_item(table: str, key: dict) -> dict | None:
    result = DDB.get_item(TableName=table, Key=key, ConsistentRead=True)
    return result.get("Item")


def acquire(operation_key: str, owner: str, now: int, lease_seconds: int) -> dict | None:
    key = {"operation_key": {"S": operation_key}}
    item = get_item(OPERATIONS_TABLE, key)
    if item is None:
        try:
            DDB.put_item(
                TableName=OPERATIONS_TABLE,
                Item={
                    **key,
                    "status": {"S": "IN_PROGRESS"},
                    "owner": {"S": owner},
                    "lease_expires": {"N": str(now + lease_seconds)},
                    "version": {"N": "0"},
                    "run_id": {"S": RUN_ID},
                },
                ConditionExpression="attribute_not_exists(operation_key)",
            )
            emit("OperationAcquired")
            return None
        except ClientError as error:
            if error.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise
            item = get_item(OPERATIONS_TABLE, key)

    if item and item["status"]["S"] == "COMPLETE":
        emit("CanonicalResultReplayed")
        return {"result": item["result"]["S"], "replayed": True}

    lease_expires = int(item["lease_expires"]["N"])
    current_owner = item["owner"]["S"]
    if lease_expires > now and current_owner != owner:
        emit("ExecutionBusy")
        raise ExecutionBusy(operation_key)

    try:
        DDB.update_item(
            TableName=OPERATIONS_TABLE,
            Key=key,
            UpdateExpression="SET #owner=:owner, lease_expires=:lease",
            ConditionExpression="#status=:in_progress AND (#owner=:owner OR lease_expires<=:now)",
            ExpressionAttributeNames={"#owner": "owner", "#status": "status"},
            ExpressionAttributeValues={
                ":owner": {"S": owner},
                ":lease": {"N": str(now + lease_seconds)},
                ":now": {"N": str(now)},
                ":in_progress": {"S": "IN_PROGRESS"},
            },
        )
        emit("LeaseReclaimed" if current_owner != owner else "LeaseRenewed")
        return None
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ExecutionBusy(operation_key) from error
        raise


def invoke_provider(operation_key: str) -> tuple[str, bool]:
    key = {"operation_key": {"S": operation_key}}
    existing = get_item(PROVIDER_TABLE, key)
    if existing:
        emit("ProviderResultReplayed")
        return existing["result"]["S"], True
    provider_reference = f"provider-{uuid4()}"
    result = json.dumps(
        {"provider_reference": provider_reference, "status": "APPROVED"},
        sort_keys=True,
    )
    try:
        DDB.put_item(
            TableName=PROVIDER_TABLE,
            Item={
                **key,
                "provider_reference": {"S": provider_reference},
                "result": {"S": result},
                "run_id": {"S": RUN_ID},
                "created_at": {"N": str(int(time.time()))},
            },
            ConditionExpression="attribute_not_exists(operation_key)",
        )
        emit("ProviderEffectCommitted")
        return result, False
    except ClientError as error:
        if error.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
        existing = get_item(PROVIDER_TABLE, key)
        emit("ProviderResultReplayed")
        return existing["result"]["S"], True


def complete(
    operation_key: str,
    owner: str,
    result: str,
    projection_fault_mode: str,
) -> None:
    DDB.transact_write_items(
        TransactItems=[
            {
                "Update": {
                    "TableName": OPERATIONS_TABLE,
                    "Key": {"operation_key": {"S": operation_key}},
                    "UpdateExpression": "SET #status=:complete,#result=:result,#version=:version",
                    "ConditionExpression": "#status=:in_progress AND #owner=:owner",
                    "ExpressionAttributeNames": {
                        "#status": "status",
                        "#result": "result",
                        "#version": "version",
                        "#owner": "owner",
                    },
                    "ExpressionAttributeValues": {
                        ":complete": {"S": "COMPLETE"},
                        ":in_progress": {"S": "IN_PROGRESS"},
                        ":owner": {"S": owner},
                        ":result": {"S": result},
                        ":version": {"N": "1"},
                    },
                }
            },
            {
                "Put": {
                    "TableName": OUTBOX_TABLE,
                    "Item": {
                        "operation_key": {"S": operation_key},
                        "event_id": {"S": str(uuid4())},
                        "source_version": {"N": "1"},
                        "payload": {"S": result},
                        "delivery_status": {"S": "PENDING"},
                        "projection_fault_mode": {"S": projection_fault_mode},
                        "run_id": {"S": RUN_ID},
                    },
                    "ConditionExpression": "attribute_not_exists(operation_key)",
                }
            },
        ]
    )
    emit("OperationCompleted")
    emit("OutboxCommitted")


def worker_handler(event: dict, _context: object) -> dict:
    operation_key = event["operation_key"]
    owner = event["owner"]
    now = int(event.get("now", time.time()))
    lease_seconds = int(event.get("lease_seconds", 30))
    completed = acquire(operation_key, owner, now, lease_seconds)
    if completed:
        return {"operation_key": operation_key, **completed}
    result, provider_replayed = invoke_provider(operation_key)
    if event.get("crash_after_provider"):
        emit("InjectedCrashAfterProvider")
        raise InjectedCrash(operation_key)
    complete(
        operation_key,
        owner,
        result,
        event.get("projection_fault_mode", "NONE"),
    )
    return {
        "operation_key": operation_key,
        "result": result,
        "replayed": False,
        "provider_replayed": provider_replayed,
    }


def deserialize_image(image: dict) -> dict:
    return {key: DESERIALIZER.deserialize(value) for key, value in image.items()}


def put_projection(item: dict) -> bool:
    try:
        DDB.put_item(
            TableName=PROJECTION_TABLE,
            Item={
                "operation_key": {"S": item["operation_key"]},
                "source_version": {"N": str(item["source_version"])},
                "result": {"S": item["payload"]},
                "run_id": {"S": RUN_ID},
            },
            ConditionExpression="attribute_not_exists(operation_key) OR source_version < :version",
            ExpressionAttributeValues={
                ":version": {"N": str(item["source_version"])}
            },
        )
        emit("ProjectionCommitted")
        return False
    except ClientError as error:
        if error.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
        existing = get_item(
            PROJECTION_TABLE,
            {"operation_key": {"S": item["operation_key"]}},
        )
        exact_match = (
            existing
            and int(existing["source_version"]["N"]) == int(item["source_version"])
            and existing["result"]["S"] == item["payload"]
        )
        if not exact_match:
            raise
        emit("ProjectionReplaySuppressed")
        return True


def projector_handler(event: dict, _context: object) -> dict:
    processed = 0
    for record in event.get("Records", []):
        if record.get("eventName") != "INSERT":
            continue
        item = deserialize_image(record["dynamodb"]["NewImage"])
        replayed = put_projection(item)
        if item.get("projection_fault_mode") == "CRASH_AFTER_PROJECTION_ONCE" and not replayed:
            emit("InjectedCrashAfterProjection")
            raise InjectedCrash(item["operation_key"])
        DDB.update_item(
            TableName=OUTBOX_TABLE,
            Key={"operation_key": {"S": item["operation_key"]}},
            UpdateExpression="SET delivery_status=:delivered, delivered_at=:now",
            ExpressionAttributeValues={
                ":delivered": {"S": "DELIVERED"},
                ":now": {"N": str(int(time.time()))},
            },
        )
        emit("OutboxDelivered")
        processed += 1
    return {"processed": processed}


def reconcile_handler(_event: dict, _context: object) -> dict:
    operations = DDB.scan(TableName=OPERATIONS_TABLE).get("Items", [])
    missing = mismatched = repaired = 0
    for operation in operations:
        if operation["status"]["S"] != "COMPLETE":
            continue
        key = {"operation_key": operation["operation_key"]}
        projection = get_item(PROJECTION_TABLE, key)
        expected_version = int(operation["version"]["N"])
        expected_result = operation["result"]["S"]
        if projection is None:
            missing += 1
        elif (
            int(projection["source_version"]["N"]) != expected_version
            or projection["result"]["S"] != expected_result
        ):
            mismatched += 1
        else:
            continue
        DDB.put_item(
            TableName=PROJECTION_TABLE,
            Item={
                **key,
                "source_version": {"N": str(expected_version)},
                "result": {"S": expected_result},
                "run_id": {"S": RUN_ID},
                "reconciled_at": {"N": str(int(time.time()))},
            },
        )
        repaired += 1
    emit("ProjectionMismatch", missing + mismatched)
    emit("ProjectionRepaired", repaired)
    return {"missing": missing, "mismatched": mismatched, "repaired": repaired}

