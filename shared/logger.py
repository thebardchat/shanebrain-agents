"""
Agent Logger — Every agent action is logged to Weaviate.
Nothing runs in the dark. Full accountability, full traceability.
"""

import time
import json
import logging
import httpx
from dataclasses import dataclass, asdict

from .config import WEAVIATE_URL

logger = logging.getLogger("shanebrain.agent_logger")


@dataclass
class AgentLogEntry:
    agent: str
    action: str
    status: str  # "started", "completed", "failed", "blocked"
    details: str = ""
    duration_ms: float = 0
    red_line_violations: str = ""  # JSON string of violations if any
    timestamp: float = 0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


class AgentLogger:
    """Logs agent actions to Weaviate AgentLog collection."""

    COLLECTION = "AgentLog"

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self._ensure_collection()

    def _ensure_collection(self):
        """Create AgentLog collection if it doesn't exist."""
        try:
            resp = httpx.get(f"{WEAVIATE_URL}/v1/schema/{self.COLLECTION}", timeout=5)
            if resp.status_code == 200:
                return
        except Exception:
            pass

        schema = {
            "class": self.COLLECTION,
            "description": "ShaneBrain Agent Ecosystem action log",
            "vectorizer": "text2vec-ollama",
            "moduleConfig": {
                "text2vec-ollama": {
                    "apiEndpoint": "http://host.docker.internal:11434",
                    "model": "nomic-embed-text",
                }
            },
            "properties": [
                {"name": "agent", "dataType": ["text"], "description": "Agent name"},
                {"name": "action", "dataType": ["text"], "description": "Action performed"},
                {"name": "status", "dataType": ["text"], "description": "Action status"},
                {"name": "details", "dataType": ["text"], "description": "Action details"},
                {"name": "duration_ms", "dataType": ["number"], "description": "Duration in ms"},
                {"name": "red_line_violations", "dataType": ["text"], "description": "Violations JSON"},
                {"name": "timestamp", "dataType": ["number"], "description": "Unix timestamp"},
            ],
        }
        try:
            resp = httpx.post(f"{WEAVIATE_URL}/v1/schema", json=schema, timeout=10)
            if resp.status_code in (200, 422):  # 422 = already exists
                logger.info(f"AgentLog collection ready")
            else:
                logger.error(f"Failed to create AgentLog: {resp.text}")
        except Exception as e:
            logger.error(f"Weaviate unreachable for schema: {e}")

    def log(self, action: str, status: str, details: str = "",
            duration_ms: float = 0, violations: list | None = None):
        """Log an action to Weaviate."""
        entry = AgentLogEntry(
            agent=self.agent_name,
            action=action,
            status=status,
            details=details[:1000],
            duration_ms=duration_ms,
            red_line_violations=json.dumps(violations) if violations else "",
        )

        try:
            resp = httpx.post(
                f"{WEAVIATE_URL}/v1/objects",
                json={
                    "class": self.COLLECTION,
                    "properties": asdict(entry),
                },
                timeout=10,
            )
            if resp.status_code not in (200, 201):
                logger.error(f"Log write failed: {resp.text}")
        except Exception as e:
            logger.error(f"Failed to log to Weaviate: {e}")

        return entry

    def log_start(self, action: str, details: str = "") -> float:
        """Log action start, return start time for duration tracking."""
        self.log(action, "started", details)
        return time.time()

    def log_complete(self, action: str, start_time: float, details: str = ""):
        """Log action completion with duration."""
        duration = (time.time() - start_time) * 1000
        self.log(action, "completed", details, duration_ms=duration)

    def log_blocked(self, action: str, violations: list):
        """Log a red-line blocked action."""
        self.log(action, "blocked",
                 f"Red line violations: {len(violations)}",
                 violations=violations)

    def log_failed(self, action: str, error: str):
        """Log a failed action."""
        self.log(action, "failed", error[:500])
