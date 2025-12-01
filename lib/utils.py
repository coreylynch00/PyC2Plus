# utils.py
import time
import subprocess
import base64
import os
import platform

AUTH_KEY = "MySecretKey123"

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
    downloads_dir = os.path.join(os.environ['USERPROFILE'], "Downloads") if system == "Windows" else os.path.expanduser("~/Downloads")

    agent_dir = os.path.join(downloads_dir, agent_id)
    os.makedirs(agent_dir, exist_ok=True)

    filepath = os.path.join(agent_dir, filename)
    with open(filepath, "wb") as f:
        f.write(data)

    return filepath
