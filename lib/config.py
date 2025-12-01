from queue import Queue

agents = {}               # agent_id -> {registered_at, last_seen}
tasks = {}                # agent_id -> Queue() of tasks for agent
results = {}              # agent_id -> list of dicts {timestamp, result}  (history)
result_queues = {}        # agent_id -> Queue() for live output streaming

# Configuration
AUTH_KEY = "MySecretKey123"
AGENT_TIMEOUT = 10
HOST = "0.0.0.0"
PORT = 80
