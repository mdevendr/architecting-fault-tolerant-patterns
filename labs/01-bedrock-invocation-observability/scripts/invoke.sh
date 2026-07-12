#!/usr/bin/env bash
set -euo pipefail

PROFILE="${AWS_PROFILE:-default}"
REGION="us-east-1"
STACK_NAME="ft-lab01-bedrock-observability"
SCENARIO="normal"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --stack-name) STACK_NAME="$2"; shift 2 ;;
    --scenario) SCENARIO="$2"; shift 2 ;;
    -h|--help)
      cat <<USAGE
Usage: $0 [--profile default] [--region us-east-1] [--stack-name ft-lab01-bedrock-observability]
          [--scenario normal|degraded|policy-sensitive]
USAGE
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

case "$SCENARIO" in
  normal|degraded|policy-sensitive) ;;
  *) echo "Invalid scenario: $SCENARIO" >&2; exit 1 ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$LAB_DIR/../.." && pwd)"
PAYLOAD="$LAB_DIR/events/$SCENARIO.json"
OUTPUT_DIR="$REPO_ROOT/evidence/sample-responses"
OUTPUT_FILE="$OUTPUT_DIR/01-$SCENARIO-response.json"

mkdir -p "$OUTPUT_DIR"

FUNCTION_NAME="$(aws cloudformation describe-stacks \
  --profile "$PROFILE" \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='FunctionName'].OutputValue | [0]" \
  --output text)"

aws lambda invoke \
  --profile "$PROFILE" \
  --region "$REGION" \
  --function-name "$FUNCTION_NAME" \
  --cli-binary-format raw-in-base64-out \
  --payload "file://$PAYLOAD" \
  "$OUTPUT_FILE"

echo "Response written to $OUTPUT_FILE"
cat "$OUTPUT_FILE"
