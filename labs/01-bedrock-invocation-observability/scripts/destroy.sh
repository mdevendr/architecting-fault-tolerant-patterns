#!/usr/bin/env bash
set -euo pipefail

PROFILE="melon"
REGION="us-east-1"
STACK_NAME="ft-lab01-bedrock-observability"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --stack-name) STACK_NAME="$2"; shift 2 ;;
    -h|--help)
      cat <<USAGE
Usage: $0 [--profile melon] [--region us-east-1] [--stack-name ft-lab01-bedrock-observability]
USAGE
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

aws cloudformation delete-stack \
  --profile "$PROFILE" \
  --region "$REGION" \
  --stack-name "$STACK_NAME"

aws cloudformation wait stack-delete-complete \
  --profile "$PROFILE" \
  --region "$REGION" \
  --stack-name "$STACK_NAME"

echo "Deleted stack $STACK_NAME"
