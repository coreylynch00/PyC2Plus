from queue import Queue

# Global state for agents
agents = {}     # agent_id -> {registered_at, last_seen}
tasks = {}      # agent_id -> Queue()
results = {}    # agent_id -> list of dicts {timestamp, result}

# Configuration
AUTH_KEY = "MySecretKey123"
AGENT_TIMEOUT = 10  # seconds before agent is considered offline
HOST = "0.0.0.0"
PORT = 80
