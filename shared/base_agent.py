"""
BaseAgent — The DNA every ShaneBrain agent inherits.
Red lines checked before every action. Every action logged. No exceptions.
"""

import time
import logging
from claude_agent_sdk import AgentDefinition

from .config import DEFAULT_MODEL
from .red_lines import RedLineEngine, RedLineViolation
from .logger import AgentLogger

logger = logging.getLogger("shanebrain.base_agent")


class BaseAgent:
    """
    Base class for all ShaneBrain agents.

    Every agent:
    - Has a name, role, and system prompt
    - Has red line rules that cannot be overridden
    - Logs every action to Weaviate
    - Can be converted to an AgentDefinition for the SDK
    """

    name: str = "unnamed"
    role: str = "general"
    description: str = "A ShaneBrain agent"
    model: str = DEFAULT_MODEL
    tools: list[str] | None = None
    disallowed_tools: list[str] | None = None
    max_turns: int = 25

    def __init__(self):
        self.red_lines = RedLineEngine(self.name)
        self.logger = AgentLogger(self.name)
        self._action_count = 0
        self._blocked_count = 0
        self._start_time = time.time()

    def system_prompt(self) -> str:
        """Build the full system prompt including red lines."""
        red_lines_section = self.red_lines.get_rules_prompt()
        return f"""# {self.name.upper()} AGENT — ShaneBrain Ecosystem

## Role
{self.description}

## Owner
Shane Brazelton — Hazel Green, AL. Building local AI for the 800 million.

## Core Principles
- You are one agent in a coordinated ecosystem of seven specialists.
- You do real work. No faking, no placeholders, no half-measures.
- Every action you take is logged and auditable.
- You serve Shane and his family's mission.

{red_lines_section}

## Agent-Specific Instructions
{self.agent_instructions()}
"""

    def agent_instructions(self) -> str:
        """Override in subclass to add agent-specific instructions."""
        return "No additional instructions."

    def check_action(self, action: str, context: dict | None = None) -> bool:
        """
        Check an action against red lines. Returns True if allowed.
        Raises RedLineViolation and logs if blocked.
        """
        try:
            result = self.red_lines.check(action, context)
            if not result["allowed"]:
                self._blocked_count += 1
                self.logger.log_blocked(action, result["violations"])
                return False
            return True
        except RedLineViolation as e:
            self._blocked_count += 1
            self.logger.log_blocked(action, [{"rule": e.rule_name,
                                               "severity": e.severity.value}])
            raise

    def execute(self, action: str, context: dict | None = None) -> dict:
        """
        Execute an action with red line checking and logging.
        Override _execute() in subclasses for actual work.
        """
        self._action_count += 1
        start = self.logger.log_start(action)

        try:
            self.check_action(action, context)
            result = self._execute(action, context or {})
            self.logger.log_complete(action, start, str(result)[:500])
            return {"status": "ok", "result": result}
        except RedLineViolation as e:
            return {"status": "blocked", "error": str(e)}
        except Exception as e:
            self.logger.log_failed(action, str(e))
            return {"status": "error", "error": str(e)}

    def _execute(self, action: str, context: dict) -> dict:
        """Override in subclass. This is where the real work happens."""
        raise NotImplementedError(f"{self.name} must implement _execute()")

    def to_agent_definition(self) -> AgentDefinition:
        """Convert to SDK AgentDefinition for use in orchestrator."""
        return AgentDefinition(
            description=self.description,
            prompt=self.system_prompt(),
            tools=self.tools,
            disallowedTools=self.disallowed_tools,
            model=self.model,
            maxTurns=self.max_turns,
        )

    def stats(self) -> dict:
        """Return agent runtime stats."""
        return {
            "name": self.name,
            "role": self.role,
            "actions": self._action_count,
            "blocked": self._blocked_count,
            "uptime_seconds": round(time.time() - self._start_time, 1),
            "red_line_count": len(self.red_lines.rules),
        }
