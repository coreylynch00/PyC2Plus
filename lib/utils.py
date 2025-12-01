# utils.py
import time
import subprocess
import base64
import os

AUTH_KEY = "MySecretKey123"

def auth_check(req):
    return req.headers.get("Authorization", "").strip() == f"Bearer {AUTH_KEY}"

def timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

def run_local(cmd):
    # execute shell command on agent & return output to server
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return (result.stdout + result.stderr).strip()
    except Exception as e:
        return f"Error executing command: {e}"

def save_file(agent_id, filename, b64data):
    # decode B64 data and save to agent's Downloads folder
    data = base64.b64decode(b64data)
    downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    agent_dir = os.path.join(downloads_dir, agent_id)
    os.makedirs(agent_dir, exist_ok=True)
    filepath = os.path.join(agent_dir, filename)
    with open(filepath, "wb") as f:
        f.write(data)
    return filepath
