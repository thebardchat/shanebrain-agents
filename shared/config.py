"""
ShaneBrain Agent Ecosystem — Shared Configuration
Built with claude-agent-sdk on a Raspberry Pi 5.
This is not a demo. This is production infrastructure for one family's AI future.
"""

from pathlib import Path

# Paths
AGENTS_ROOT = Path("/mnt/shanebrain-raid/shanebrain-core/agents")
SHANEBRAIN_ROOT = Path("/mnt/shanebrain-raid/shanebrain-core")
MEGA_DASHBOARD = Path("/mnt/shanebrain-raid/mega-dashboard")
RAID_ROOT = Path("/mnt/shanebrain-raid")

# Network
WEAVIATE_URL = "http://localhost:8080"
OLLAMA_URL = "http://localhost:11435"  # Cluster proxy
OLLAMA_LOCAL = "http://localhost:11434"
MCP_URL = "http://localhost:8100"
GATEWAY_URL = "http://localhost:4200"

# Agent ecosystem
AGENT_API_PORT = 8400
AGENT_LOG_COLLECTION = "AgentLog"

# Cluster nodes — replace with your Tailscale IPs and SSH usernames
CLUSTER_NODES = {
    "node1": {"ssh": "user@100.x.x.x", "priority": 1},
    "pi5": {"ssh": "localhost", "priority": 2},
    "node2": {"ssh": "user@100.x.x.x", "priority": 3},
    "node3": {"ssh": "user@100.x.x.x", "priority": 4},
}

# Models
DEFAULT_MODEL = "claude-sonnet-4-20250514"
FAST_MODEL = "claude-haiku-4-5-20251001"
POWER_MODEL = "claude-opus-4-20250514"
LOCAL_MODEL = "llama3.2:3b"

# The Seven Agents
AGENT_NAMES = [
    "guardian",
    "librarian",
    "dispatcher",
    "builder",
    "storyteller",
    "ops",
    "social",
]
