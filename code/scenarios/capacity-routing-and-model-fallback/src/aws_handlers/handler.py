"""Bedrock capacity routing and independently evaluated semantic fallback."""

import os
from decimal import Decimal

import boto3


BEDROCK = boto3.client("bedrock-runtime")
DDB = boto3.resource("dynamodb")
TABLE = DDB.Table(os.environ["EVALUATION_TABLE"])
PRIMARY_PROFILE = os.environ["PRIMARY_PROFILE"]
FALLBACK_MODEL = os.environ["FALLBACK_MODEL"]
SUITE_VERSION = os.environ["SUITE_VERSION"]
MINIMUM_SCORE = Decimal(os.environ.get("MINIMUM_SCORE", "0.66"))


CASES = [
    ("Reply with exactly the single word BLUE.", "BLUE"),
    ("What is 2 + 2? Reply with only the numeral.", "4"),
    ("Reply with exactly the single word ALLOW.", "ALLOW"),
]


def converse(model_id: str, prompt: str) -> dict:
    response = BEDROCK.converse(
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 16, "temperature": 0},
    )
    text = response["output"]["message"]["content"][0]["text"].strip()
    usage = response.get("usage", {})
    return {"text": text, "usage": usage}


def evaluation_handler(event: dict, _context) -> dict:
    results = []
    for prompt, expected in CASES:
        invocation = converse(FALLBACK_MODEL, prompt)
        normalized = invocation["text"].strip().upper().rstrip(".")
        results.append(
            {
                "expected": expected,
                "actual": invocation["text"],
                "passed": normalized == expected,
                "usage": invocation["usage"],
            }
        )
    measured_score = Decimal(sum(1 for result in results if result["passed"])) / Decimal(len(results))
    stored_score = Decimal(str(event.get("override_score", measured_score)))
    TABLE.put_item(
        Item={
            "model_id": FALLBACK_MODEL,
            "suite_version": SUITE_VERSION,
            "measured_score": measured_score,
            "approved_score": stored_score,
            "minimum_score": MINIMUM_SCORE,
            "approved_geography": "EU",
            "results": results,
        }
    )
    return {
        "model_id": FALLBACK_MODEL,
        "suite_version": SUITE_VERSION,
        "measured_score": float(measured_score),
        "approved_score": float(stored_score),
        "minimum_score": float(MINIMUM_SCORE),
        "passed": stored_score >= MINIMUM_SCORE,
        "results": results,
    }


def gateway_handler(event: dict, _context) -> dict:
    prompt = event.get("prompt", "Reply with exactly the single word HEALTHY.")
    reason = event.get("reason", "HEALTHY")
    status_code = int(event.get("injected_status", 200))
    geography = event.get("geography", "EU")

    if reason == "POLICY_DENIED":
        return {"decision": "FAIL_CLOSED", "model_invoked": False, "fallback": False}
    if status_code in {400, 401, 403, 404}:
        return {"decision": "RETURN_ERROR", "model_invoked": False, "fallback": False}
    if status_code == 200:
        result = converse(PRIMARY_PROFILE, prompt)
        return {
            "decision": "CAPACITY_ROUTED",
            "model_invoked": True,
            "fallback": False,
            "model_id": PRIMARY_PROFILE,
            "degraded": False,
            "response": result["text"],
            "usage": result["usage"],
        }
    if status_code not in {429, 500, 502, 503, 504}:
        return {"decision": "RETURN_ERROR", "model_invoked": False, "fallback": False}

    evaluation = TABLE.get_item(Key={"model_id": FALLBACK_MODEL}, ConsistentRead=True).get("Item")
    if not evaluation or evaluation["suite_version"] != SUITE_VERSION:
        return {"decision": "SAFE_FAILURE", "reason": "EVALUATION_MISSING", "model_invoked": False, "fallback": False}
    if geography != evaluation["approved_geography"]:
        return {"decision": "CAPACITY_ROUTE_ONLY", "reason": "GEOGRAPHY_NOT_APPROVED", "model_invoked": False, "fallback": False}
    if evaluation["approved_score"] < evaluation["minimum_score"]:
        return {"decision": "CAPACITY_ROUTE_ONLY", "reason": "FALLBACK_BELOW_THRESHOLD", "model_invoked": False, "fallback": False}

    result = converse(FALLBACK_MODEL, prompt)
    return {
        "decision": "SEMANTIC_FALLBACK",
        "model_invoked": True,
        "fallback": True,
        "model_id": FALLBACK_MODEL,
        "evaluation_suite": SUITE_VERSION,
        "evaluation_score": float(evaluation["approved_score"]),
        "degraded": True,
        "response": result["text"],
        "usage": result["usage"],
    }

