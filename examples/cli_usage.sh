#!/usr/bin/env bash

set -euo pipefail

: "${DIFY_API_KEY:?Set DIFY_API_KEY before running this example}"

USER_ID="${DIFY_USER:-demo-user}"

echo "Inspect app inputs"
dify --api-key "$DIFY_API_KEY" --json app inspect --user "$USER_ID"

echo "Send the first chat message"
ROUND_ONE_JSON=$(dify --api-key "$DIFY_API_KEY" --json chat send \
  --user "$USER_ID" \
  --query "Plan a 3-day trip to Kyoto" \
  --input destination=Kyoto \
  --input days=3)

echo "$ROUND_ONE_JSON"
CONVERSATION_ID=$(printf '%s\n' "$ROUND_ONE_JSON" | python -c 'import json,sys; print(json.load(sys.stdin)["conversation_id"])')

echo "Continue the conversation with typed JSON inputs"
dify --api-key "$DIFY_API_KEY" --json chat send \
  --user "$USER_ID" \
  --conversation-id "$CONVERSATION_ID" \
  --query "Make day 2 lower budget and kid-friendly" \
  --inputs-json '{"destination":"Kyoto","days":3,"budget":"low","travel_with_kids":true}'

echo "Run a workflow"
dify --api-key "$DIFY_API_KEY" --json workflow run \
  --user "$USER_ID" \
  --inputs-json '{"context":"trip planning","user_prompt":"What is the capital of France?"}'

echo "List datasets"
dify --api-key "$DIFY_API_KEY" --json kb dataset list
