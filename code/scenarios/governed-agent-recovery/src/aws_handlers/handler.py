"""AgentCore Gateway tool target with durable idempotency and compensation state."""

import os
import time

import boto3


DDB = boto3.client("dynamodb")
TABLE_NAME = os.environ["TABLE_NAME"]
RUN_ID = os.environ["RUN_ID"]


def _item(call_id: str):
    result = DDB.get_item(
        TableName=TABLE_NAME,
        Key={"call_id": {"S": call_id}},
        ConsistentRead=True,
    )
    return result.get("Item")


def _tool_name(context) -> str:
    custom = getattr(getattr(context, "client_context", None), "custom", None) or {}
    full_name = custom.get("bedrockAgentCoreToolName", "")
    return full_name.split("___", 1)[-1]


def reserve_credit(event: dict) -> dict:
    call_id = event["call_id"]
    amount = int(event["amount"])
    existing = _item(call_id)
    if existing:
        if existing["tenant_id"]["S"] != event["tenant_id"]:
            raise ValueError("call identity belongs to another tenant")
        return {
            "call_id": call_id,
            "status": existing["status"]["S"],
            "result": existing["result"]["S"],
            "replayed": True,
        }

    result = f"reservation:{call_id}:{amount}"
    DDB.put_item(
        TableName=TABLE_NAME,
        Item={
            "call_id": {"S": call_id},
            "tenant_id": {"S": event["tenant_id"]},
            "actor_role": {"S": event["actor_role"]},
            "amount": {"N": str(amount)},
            "status": {"S": "COMMITTED"},
            "result": {"S": result},
            "compensation_status": {"S": "NOT_REQUIRED"},
            "run_id": {"S": RUN_ID},
            "committed_at": {"N": str(int(time.time()))},
        },
        ConditionExpression="attribute_not_exists(call_id)",
    )
    if event.get("inject_failure_after_commit"):
        raise TimeoutError("injected response loss after commit")
    return {"call_id": call_id, "status": "COMMITTED", "result": result, "replayed": False}


def compensate_credit(event: dict) -> dict:
    call_id = event["call_id"]
    existing = _item(call_id)
    if not existing:
        raise ValueError("committed tool call not found")
    if existing["tenant_id"]["S"] != event["tenant_id"]:
        raise ValueError("call identity belongs to another tenant")
    if existing["compensation_status"]["S"] == "COMPENSATED":
        return {
            "call_id": call_id,
            "status": "COMPENSATED",
            "result": existing["compensation_result"]["S"],
            "replayed": True,
        }

    result = f"released:{call_id}"
    DDB.update_item(
        TableName=TABLE_NAME,
        Key={"call_id": {"S": call_id}},
        UpdateExpression=(
            "SET #status=:compensated, compensation_status=:compensated, "
            "compensation_result=:result, compensated_at=:now"
        ),
        ConditionExpression="compensation_status=:not_required",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":compensated": {"S": "COMPENSATED"},
            ":not_required": {"S": "NOT_REQUIRED"},
            ":result": {"S": result},
            ":now": {"N": str(int(time.time()))},
        },
    )
    if event.get("inject_failure_after_commit"):
        raise TimeoutError("injected response loss after compensation commit")
    return {"call_id": call_id, "status": "COMPENSATED", "result": result, "replayed": False}


def lambda_handler(event: dict, context) -> dict:
    tool_name = event.pop("_tool_name", None) or _tool_name(context)
    if tool_name == "reserve_credit":
        return reserve_credit(event)
    if tool_name == "compensate_credit":
        return compensate_credit(event)
    raise ValueError(f"unknown tool: {tool_name}")

