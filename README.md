# shanebrain-agents

> **Try Claude free for 2 weeks** — the AI behind this entire ecosystem. [Start your free trial →](https://claude.ai/referral/4fAMYN9Ing)

---

A production multi-agent orchestration system running 24/7 on a Raspberry Pi 5.
Seven specialized AI agents coordinated by a central orchestrator, all powered by local Ollama + Claude API.

Built by Shane Brazelton + Claude (Anthropic) — not a demo, live infrastructure for one family's AI future.

---

## The Seven Agents

| Agent | Role |
|-------|------|
| **guardian** | Security monitoring, anomaly detection, system health |
| **librarian** | RAG ingestion, Weaviate knowledge management |
| **dispatcher** | Routes tasks between agents, manages work queue |
| **builder** | Code generation, repo updates, file ops |
| **storyteller** | MEGA crew narrative engine, episode generation |
| **ops** | Systemd, Docker, cluster management |
| **social** | Facebook/Discord social posting and engagement |

## Architecture

```
orchestrator.py  ←→  FastAPI server (port 8400)
     │
     ├── guardian/
     ├── librarian/
     ├── dispatcher/
     ├── builder/
     ├── storyteller/
     ├── ops/
     └── social/
```

Each agent is a self-contained directory with its own `agent.py` and `__init__.py`.
Shared config, logging, and Weaviate/Ollama clients live in `shared/`.

## Requirements

- Raspberry Pi 5 (or any Linux host with 8GB+ RAM)
- Python 3.11+
- [Ollama](https://ollama.ai) with `llama3.2:3b` pulled
- Weaviate (Docker) on port 8080
- Anthropic API key (for Claude-powered agents)

```bash
pip install fastapi uvicorn weaviate-client anthropic aiohttp
```

## Setup

```bash
git clone https://github.com/thebardchat/shanebrain-agents
cd shanebrain-agents

# Copy and edit config
cp shared/config.py shared/config.local.py
# Edit CLUSTER_NODES with your own Tailscale IPs

# Set environment
export ANTHROPIC_API_KEY=your_key_here

# Run
python3 server.py
```

## Systemd (optional)

```bash
sudo cp shanebrain-agents.service /etc/systemd/system/
sudo systemctl enable --now shanebrain-agents
```

## Related Projects

- [shanebrain-core](https://github.com/thebardchat/shanebrain-core) — Pi 5 operational layer (private)
- [shanebrain_mcp](https://github.com/thebardchat/shanebrain_mcp) — MCP server with 42 tools
- [mega-crew](https://github.com/thebardchat/mega-crew) — AI character bot system

## License

GPL v3 — fork it, build on it, keep it open.
