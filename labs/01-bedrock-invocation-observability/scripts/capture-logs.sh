#!/usr/bin/env bash
set -euo pipefail

PROFILE="melon"
REGION="us-east-1"
STACK_NAME="ft-lab01-bedrock-observability"
LIMIT="25"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --stack-name) STACK_NAME="$2"; shift 2 ;;
    --limit) LIMIT="$2"; shift 2 ;;
    -h|--help)
      cat <<USAGE
Usage: $0 [--profile melon] [--region us-east-1] [--stack-name ft-lab01-bedrock-observability]
          [--limit 25]
USAGE
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$LAB_DIR/../.." && pwd)"
OUTPUT_DIR="$REPO_ROOT/evidence/logs"
OUTPUT_FILE="$OUTPUT_DIR/01-bedrock-invocation-observability-logs.json"

mkdir -p "$OUTPUT_DIR"

LOG_GROUP_NAME="$(aws cloudformation describe-stacks \
  --profile "$PROFILE" \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='LogGroupName'].OutputValue | [0]" \
  --output text)"

aws logs filter-log-events \
  --profile "$PROFILE" \
  --region "$REGION" \
  --log-group-name "$LOG_GROUP_NAME" \
  --filter-pattern "ai_invocation_observability" \
  --limit "$LIMIT" \
  --output json > "$OUTPUT_FILE"

echo "Logs written to $OUTPUT_FILE"
cat "$OUTPUT_FILE"
