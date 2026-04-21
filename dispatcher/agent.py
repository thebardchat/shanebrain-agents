"""
DISPATCHER AGENT — Intent Router

The traffic controller. Never executes — only routes.
Classifies incoming requests and delegates to the right specialist agent.
"""

import re
import logging

from shared.base_agent import BaseAgent

logger = logging.getLogger("shanebrain.dispatcher")

# Intent classification keywords
INTENT_MAP = {
    "guardian": [
        "security", "vault", "credential", "password", "secret", "audit",
        "privacy", "threat", "breach", "scan", "firewall", "encrypt",
    ],
    "librarian": [
        "search", "knowledge", "weaviate", "rag", "ingest", "collection",
        "find", "lookup", "what do you know", "remember", "memory",
    ],
    "builder": [
        "code", "build", "fix", "bug", "repo", "git", "commit", "deploy",
        "python", "javascript", "test", "refactor", "function", "class",
    ],
    "storyteller": [
        "book", "write", "story", "chapter", "vignette", "noir", "track",
        "creative", "voice dump", "audiobook", "prose", "draft",
    ],
    "ops": [
        "docker", "service", "restart", "health", "disk", "cluster",
        "systemd", "container", "backup", "cpu", "temperature", "raid",
        "ollama", "weaviate status", "node", "ssh", "tailscale",
    ],
    "social": [
        "discord", "facebook", "post", "message", "dm", "social",
        "promo", "tweet", "share", "messenger", "bot",
    ],
}


class DispatcherAgent(BaseAgent):
    name = "dispatcher"
    role = "router"
    description = (
        "Intent classifier and task router. Analyzes incoming requests, "
        "determines which specialist agent should handle them, and delegates. "
        "Never executes actions directly — only routes."
    )
    tools = None  # Dispatcher doesn't use tools directly
    max_turns = 5  # Quick classification, no long conversations

    def agent_instructions(self) -> str:
        return """
## What You Do
1. **Classify Intent** — Determine what the user wants based on keywords and context
2. **Route to Agent** — Select the best specialist agent for the task
3. **Multi-Agent Tasks** — For complex requests, identify multiple agents needed
4. **Priority** — Security concerns always go to Guardian first

## Routing Rules
- Security/privacy → Guardian (ALWAYS first if security is involved)
- Knowledge/search/RAG → Librarian
- Code/repos/bugs → Builder
- Book/creative/writing → Storyteller
- Infrastructure/docker/cluster → Ops
- Social media/messaging → Social
- Ambiguous → Ask for clarification, don't guess

## You NEVER:
- Execute actions yourself
- Write or modify code
- Access Weaviate directly
- Make decisions that should be made by a specialist
"""

    def _execute(self, action: str, context: dict) -> dict:
        return self.classify(action, context)

    def classify(self, request: str, context: dict | None = None) -> dict:
        """
        Classify a request and return routing instructions.
        Returns the agent(s) that should handle this request.
        """
        request_lower = request.lower()
        scores: dict[str, int] = {agent: 0 for agent in INTENT_MAP}

        for agent, keywords in INTENT_MAP.items():
            for keyword in keywords:
                if keyword in request_lower:
                    scores[agent] += 1

        # Sort by score descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_agent = ranked[0][0] if ranked[0][1] > 0 else None

        # Security override: if anything security-related, Guardian goes first
        if scores["guardian"] > 0 and top_agent != "guardian":
            return {
                "primary": "guardian",
                "secondary": top_agent,
                "scores": dict(ranked),
                "reason": "Security concern detected — Guardian routes first",
            }

        if top_agent is None:
            return {
                "primary": None,
                "scores": dict(ranked),
                "reason": "Could not classify intent — needs clarification",
            }

        # Check for multi-agent tasks
        secondary = ranked[1][0] if len(ranked) > 1 and ranked[1][1] > 0 else None

        return {
            "primary": top_agent,
            "secondary": secondary,
            "scores": dict(ranked),
            "reason": f"Routed to {top_agent} (score: {ranked[0][1]})",
        }
