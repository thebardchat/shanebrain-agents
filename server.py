"""
SHANEBRAIN AGENT GATEWAY — FastAPI Service

HTTP API for the agent ecosystem. Port 8400.
Every request is routed, red-line-checked, executed, and logged.

Endpoints:
  POST /ask          — Route a request through the agent ecosystem
  POST /agent/{name} — Talk directly to a specific agent
  GET  /health       — Ecosystem health check
  GET  /stats        — Full ecosystem statistics
  GET  /agents       — List all agents and their red lines
  GET  /red-lines    — View all red line rules
"""

import sys
import os
import asyncio
import logging
import time

# Add agents directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from orchestrator import Orchestrator

# ─── Logging ─────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("shanebrain.gateway")

# ─── App ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="ShaneBrain Agent Ecosystem",
    description=(
        "7 specialist AI agents with red line rules, coordinated by an orchestrator. "
        "Built on a Raspberry Pi 5 by Shane Brazelton + Claude Code."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Orchestrator ────────────────────────────────────────────────────

orchestrator = Orchestrator()
START_TIME = time.time()


# ─── Models ──────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    request: str
    context: dict | None = None


class AgentRequest(BaseModel):
    action: str
    context: dict | None = None


class SDKRequest(BaseModel):
    request: str
    model: str | None = None


# ─── Routes ──────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Ecosystem health check."""
    agent_health = orchestrator.health()
    all_ok = all(a["status"] == "ok" for a in agent_health.values())
    return {
        "status": "healthy" if all_ok else "degraded",
        "agents": agent_health,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "version": "1.0.0",
    }


@app.get("/stats")
def stats():
    """Full ecosystem statistics."""
    return orchestrator.stats()


@app.get("/agents")
def list_agents():
    """List all agents with descriptions and red line counts."""
    agents = {}
    for name, agent in orchestrator.agents.items():
        agents[name] = {
            "name": agent.name,
            "role": agent.role,
            "description": agent.description,
            "red_lines": len(agent.red_lines.rules),
            "red_line_names": [r.name for r in agent.red_lines.rules],
        }
    return {"agents": agents, "count": len(agents)}


@app.get("/red-lines")
def red_lines():
    """View all red line rules across all agents."""
    rules = {}
    for name, agent in orchestrator.agents.items():
        rules[name] = [
            {
                "name": r.name,
                "description": r.description,
                "severity": r.severity.value,
            }
            for r in agent.red_lines.rules
        ]
    total = sum(len(v) for v in rules.values())
    return {"red_lines": rules, "total_rules": total}


@app.post("/ask")
def ask(req: AskRequest):
    """
    Route a request through the full agent ecosystem.
    The Dispatcher classifies intent and delegates to the right specialist.
    """
    logger.info(f"ASK: {req.request[:100]}")
    result = orchestrator.route(req.request, req.context)
    return result


@app.post("/agent/{agent_name}")
def direct_agent(agent_name: str, req: AgentRequest):
    """Talk directly to a specific agent, bypassing the Dispatcher."""
    agent = orchestrator.get_agent(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    logger.info(f"DIRECT [{agent_name}]: {req.action[:100]}")
    result = agent.execute(req.action, req.context)
    return result


@app.post("/sdk")
async def sdk_query(req: SDKRequest):
    """
    Route through the full Claude Agent SDK with sub-agents.
    This is the power mode — Claude orchestrating Claude.
    Requires ANTHROPIC_API_KEY in environment.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY not set — SDK mode unavailable",
        )

    logger.info(f"SDK: {req.request[:100]}")
    try:
        result = await orchestrator.route_with_sdk(req.request, req.model)
        return {"status": "ok", "result": result}
    except Exception as e:
        logger.error(f"SDK query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def root():
    """Welcome page."""
    return {
        "name": "ShaneBrain Agent Ecosystem",
        "version": "1.0.0",
        "agents": list(orchestrator.agents.keys()),
        "mission": "Building for the ~800 million people Big Tech is about to leave behind.",
        "built_by": "Shane Brazelton + Claude Code",
        "built_on": "Raspberry Pi 5 (16GB RAM)",
        "endpoints": {
            "POST /ask": "Route through agent ecosystem",
            "POST /agent/{name}": "Direct agent access",
            "POST /sdk": "Claude Agent SDK power mode",
            "GET /health": "Health check",
            "GET /stats": "Full statistics",
            "GET /agents": "List all agents",
            "GET /red-lines": "View red line rules",
        },
    }


# ─── Entrypoint ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting ShaneBrain Agent Ecosystem on port 8400")
    uvicorn.run(app, host="0.0.0.0", port=8400, log_level="info")
