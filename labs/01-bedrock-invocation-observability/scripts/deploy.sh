#!/usr/bin/env bash
set -euo pipefail

PROFILE="${AWS_PROFILE:-default}"
REGION="us-east-1"
STACK_NAME="ft-lab01-bedrock-observability"
MODEL_ID="anthropic.claude-3-haiku-20240307-v1:0"
PROMPT_VERSION="support-assistant-v1"
CAPABILITY_NAME="customer-support-assistant"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --stack-name) STACK_NAME="$2"; shift 2 ;;
    --model-id) MODEL_ID="$2"; shift 2 ;;
    --prompt-version) PROMPT_VERSION="$2"; shift 2 ;;
    --capability-name) CAPABILITY_NAME="$2"; shift 2 ;;
    -h|--help)
      cat <<USAGE
Usage: $0 [--profile default] [--region us-east-1] [--stack-name ft-lab01-bedrock-observability]
          [--model-id MODEL_ID] [--prompt-version VERSION] [--capability-name NAME]
USAGE
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE="$LAB_DIR/template.yaml"

aws cloudformation deploy \
  --profile "$PROFILE" \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --template-file "$TEMPLATE" \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    FunctionName="$STACK_NAME" \
    ModelId="$MODEL_ID" \
    PromptVersion="$PROMPT_VERSION" \
    CapabilityName="$CAPABILITY_NAME"

aws cloudformation describe-stacks \
  --profile "$PROFILE" \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs" \
  --output table
