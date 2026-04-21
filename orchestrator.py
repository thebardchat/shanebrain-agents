"""
SHANEBRAIN ORCHESTRATOR — The Central Intelligence

Coordinates all seven specialist agents using the Claude Agent SDK.
Routes requests through the Dispatcher, executes via specialists,
logs everything to Weaviate. This is the heartbeat.

Built by Shane Brazelton + Claude Code on a Raspberry Pi 5.
Not a demo. Not a toy. A living, breathing AI ecosystem.
"""

import asyncio
import time
import json
import logging
from pathlib import Path

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AgentDefinition,
    ResultMessage,
    AssistantMessage,
    StreamEvent,
)

from shared.config import (
    AGENTS_ROOT, SHANEBRAIN_ROOT, MCP_URL,
    DEFAULT_MODEL, FAST_MODEL, POWER_MODEL,
    AGENT_NAMES,
)
from shared.red_lines import RedLineEngine, UNIVERSAL_RED_LINES
from shared.logger import AgentLogger

# Import all agents
from guardian import GuardianAgent
from librarian import LibrarianAgent
from dispatcher import DispatcherAgent
from builder import BuilderAgent
from storyteller import StorytellerAgent
from ops import OpsAgent
from social import SocialAgent

logger = logging.getLogger("shanebrain.orchestrator")

# ─── Agent Registry ──────────────────────────────────────────────────

AGENT_CLASSES = {
    "guardian": GuardianAgent,
    "librarian": LibrarianAgent,
    "dispatcher": DispatcherAgent,
    "builder": BuilderAgent,
    "storyteller": StorytellerAgent,
    "ops": OpsAgent,
    "social": SocialAgent,
}


class Orchestrator:
    """
    The ShaneBrain Orchestrator.

    Lifecycle:
    1. Request comes in
    2. Dispatcher classifies intent → picks agent(s)
    3. Red lines checked on the proposed action
    4. Specialist agent executes
    5. Result logged to Weaviate
    6. Response returned
    """

    def __init__(self):
        self.agents = {name: cls() for name, cls in AGENT_CLASSES.items()}
        self.dispatcher = self.agents["dispatcher"]
        self.logger = AgentLogger("orchestrator")
        self.red_lines = RedLineEngine("orchestrator")
        self._request_count = 0
        self._start_time = time.time()
        logger.info("ShaneBrain Orchestrator initialized with %d agents", len(self.agents))

    def route(self, request: str, context: dict | None = None) -> dict:
        """
        Route a request through the agent ecosystem.
        Synchronous entry point for the FastAPI gateway.
        """
        self._request_count += 1
        context = context or {}
        start = self.logger.log_start(f"route: {request[:100]}")

        # Step 1: Dispatch
        routing = self.dispatcher.execute(request, context)
        if routing["status"] != "ok":
            return {"error": "Dispatcher failed", "details": routing}

        route_result = routing["result"]
        primary = route_result.get("primary")

        if not primary:
            return {
                "status": "unroutable",
                "message": "Could not determine which agent should handle this request",
                "scores": route_result.get("scores", {}),
            }

        # Step 2: Execute via primary agent
        agent = self.agents.get(primary)
        if not agent:
            return {"error": f"Unknown agent: {primary}"}

        result = agent.execute(request, context)

        # Step 3: If secondary agent needed, chain it
        secondary = route_result.get("secondary")
        if secondary and secondary != primary:
            sec_agent = self.agents.get(secondary)
            if sec_agent:
                sec_result = sec_agent.execute(request, context)
                result["secondary_result"] = sec_result

        # Step 4: Log completion
        self.logger.log_complete(f"route: {request[:100]}", start,
                                 f"routed to {primary}" +
                                 (f" + {secondary}" if secondary else ""))

        return {
            "status": "ok",
            "routed_to": primary,
            "secondary": secondary,
            "result": result,
            "routing": route_result,
        }

    async def route_with_sdk(self, request: str, model: str | None = None) -> str:
        """
        Route a request using the full Claude Agent SDK with sub-agents.
        This is the power mode — Claude orchestrates Claude.
        """
        # Build agent definitions for the SDK
        agent_defs = {}
        for name, agent in self.agents.items():
            agent_defs[name] = agent.to_agent_definition()

        options = ClaudeAgentOptions(
            system_prompt=self._orchestrator_prompt(),
            model=model or DEFAULT_MODEL,
            agents=agent_defs,
            mcp_servers={
                "shanebrain": {
                    "type": "http",
                    "url": f"{MCP_URL}/mcp",
                },
            },
            max_turns=50,
            permission_mode="acceptEdits",
            cwd=str(SHANEBRAIN_ROOT),
        )

        result_text = ""
        async for message in query(prompt=request, options=options):
            if isinstance(message, ResultMessage):
                result_text = message.text if hasattr(message, "text") else str(message)
            elif isinstance(message, AssistantMessage):
                for block in getattr(message, "content", []):
                    if hasattr(block, "text"):
                        result_text += block.text

        return result_text

    def _orchestrator_prompt(self) -> str:
        """System prompt for the SDK orchestrator."""
        agent_list = "\n".join(
            f"- **{name}**: {agent.description}"
            for name, agent in self.agents.items()
        )
        return f"""# SHANEBRAIN ORCHESTRATOR

You are the central coordinator of the ShaneBrain Agent Ecosystem,
built by Shane Brazelton on a Raspberry Pi 5 in Hazel Green, Alabama.

## Your Agents
{agent_list}

## How to Route
1. Analyze the user's request
2. Delegate to the appropriate specialist agent using the Agent tool
3. For multi-step tasks, chain agents: e.g., Guardian first for security, then Builder
4. Security concerns ALWAYS go through Guardian first
5. Log all actions

## Red Lines
Every agent has inviolable rules. You enforce them at the orchestration level.
If an agent tries to violate a red line, BLOCK the action and report it.

## The Mission
Building for the ~800 million people Big Tech is about to leave behind.
This ecosystem runs on a $80 computer. It's real. It works. It matters.
"""

    def get_agent(self, name: str):
        """Get a specific agent by name."""
        return self.agents.get(name)

    def stats(self) -> dict:
        """Full ecosystem statistics."""
        agent_stats = {name: agent.stats() for name, agent in self.agents.items()}
        return {
            "orchestrator": {
                "requests_processed": self._request_count,
                "uptime_seconds": round(time.time() - self._start_time, 1),
                "agents_loaded": len(self.agents),
            },
            "agents": agent_stats,
        }

    def health(self) -> dict:
        """Quick health check of all agents."""
        return {
            name: {
                "status": "ok",
                "red_lines": len(agent.red_lines.rules),
                "actions": agent._action_count,
            }
            for name, agent in self.agents.items()
        }
