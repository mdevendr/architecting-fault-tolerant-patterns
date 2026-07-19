"""AWS worker for measured recovery-storm and cell-isolation experiments."""

from __future__ import annotations

from decimal import Decimal
import json
import os
import time

import boto3
from botocore.exceptions import ClientError


DYNAMODB = boto3.resource("dynamodb")
CONTROL_TABLE = DYNAMODB.Table(os.environ["CONTROL_TABLE"])
COUNTER_TABLE = DYNAMODB.Table(os.environ["COUNTER_TABLE"])
OUTCOME_TABLE = DYNAMODB.Table(os.environ["OUTCOME_TABLE"])
CELL_ID = os.environ["CELL_ID"]
RUN_ID = os.environ["RUN_ID"]
POLICY_MODE = os.environ["POLICY_MODE"]
DOWNSTREAM_CAPACITY = int(os.environ["DOWNSTREAM_CAPACITY_PER_SECOND"])
PROTECTED_RATE = int(os.environ["PROTECTED_RATE_PER_SECOND"])


def emit(metric: str, value: int = 1, **dimensions: str) -> None:
    payload = {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": "FaultToleranceEvidence",
                    "Dimensions": [["RunId", "Mode", "CellId"]],
                    "Metrics": [{"Name": metric, "Unit": "Count"}],
                }
            ],
        },
        "RunId": RUN_ID,
        "Mode": POLICY_MODE,
        "CellId": CELL_ID,
        metric: value,
        **dimensions,
    }
    print(json.dumps(payload, separators=(",", ":")))


def increment_with_limit(counter_type: str, limit: int) -> bool:
    epoch_second = int(time.time())
    counter_id = f"{RUN_ID}#{CELL_ID}#{counter_type}#{epoch_second}"
    try:
        COUNTER_TABLE.update_item(
            Key={"counter_id": counter_id},
            UpdateExpression="SET expires_at = :expiry ADD used :one",
            ConditionExpression="attribute_not_exists(used) OR used < :limit",
            ExpressionAttributeValues={
                ":expiry": epoch_second + 3600,
                ":one": Decimal(1),
                ":limit": Decimal(limit),
            },
        )
        return True
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise


def cell_is_running() -> bool:
    response = CONTROL_TABLE.get_item(
        Key={"cell_id": CELL_ID}, ConsistentRead=True
    )
    return response.get("Item", {}).get("state", "RUNNING") == "RUNNING"


def reserve_outcome(message_id: str, tenant_id: str) -> bool:
    try:
        OUTCOME_TABLE.put_item(
            Item={
                "message_id": message_id,
                "tenant_id": tenant_id,
                "cell_id": CELL_ID,
                "run_id": RUN_ID,
                "completed_at": int(time.time()),
            },
            ConditionExpression="attribute_not_exists(message_id)",
        )
        return True
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise


def process_record(record: dict) -> bool:
    body = json.loads(record["body"])
    message_id = body["message_id"]
    tenant_id = body["tenant_id"]

    running = cell_is_running()
    if POLICY_MODE == "protected" and not running:
        emit("CircuitOpenRejected")
        return False

    if POLICY_MODE == "protected" and not increment_with_limit(
        "admission", PROTECTED_RATE
    ):
        emit("AdmissionRejected")
        return False

    emit("DownstreamAttempt")
    if not running or not increment_with_limit("downstream", DOWNSTREAM_CAPACITY):
        emit("DownstreamRejected")
        return False

    if reserve_outcome(message_id, tenant_id):
        emit("Completed")
    else:
        emit("DuplicateSuppressed")
    return True


def lambda_handler(event: dict, _context: object) -> dict:
    failures = []
    for record in event.get("Records", []):
        try:
            if not process_record(record):
                failures.append({"itemIdentifier": record["messageId"]})
        except Exception as error:  # Lambda must report the item for bounded retry.
            print(json.dumps({"level": "ERROR", "error": repr(error)}))
            failures.append({"itemIdentifier": record["messageId"]})
    return {"batchItemFailures": failures}
