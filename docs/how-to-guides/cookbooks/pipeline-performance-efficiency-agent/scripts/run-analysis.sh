#!/bin/bash
# Example local runner for testing Chicory API

if [ -z "$CHICORY_API_TOKEN" ] || [ -z "$CHICORY_AGENT_ID" ]; then
  echo "Error: Missing CHICORY_API_TOKEN or CHICORY_AGENT_ID"
  exit 1
fi

DIFF_CONTENT=$(cat examples/sample-pr-diff.sql)

PAYLOAD=$(jq -n \
  --arg agent_name "$CHICORY_AGENT_ID" \
  --arg content "$DIFF_CONTENT" \
  '{
    "agent_name": $agent_name,
    "input": [
      {
        "parts": [
          {
            "content_type": "text/plain",
            "content": $content
          }
        ]
      }
    ]
  }')

curl -s -X POST https://app.chicory.ai/api/v1/runs \
  -H "Authorization: Bearer $CHICORY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD"
