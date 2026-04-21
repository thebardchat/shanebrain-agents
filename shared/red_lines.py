"""
Red Line Rules Engine — The Conscience of ShaneBrain Agents

Every agent has hard limits that CANNOT be overridden.
Red lines are not suggestions. They are absolute stops.
Violations are logged to Weaviate SecurityLog and trigger Discord alerts.
"""

import re
import time
import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("shanebrain.redlines")


class Severity(Enum):
    WARN = "warn"       # Log and allow (soft boundary)
    BLOCK = "block"     # Log and deny (hard stop)
    CRITICAL = "critical"  # Log, deny, and alert Shane via Discord


@dataclass
class RedLine:
    """A single inviolable rule."""
    name: str
    description: str
    severity: Severity
    check: callable  # fn(action: str, context: dict) -> bool  (True = violation)

    def evaluate(self, action: str, context: dict) -> bool:
        try:
            return self.check(action, context)
        except Exception as e:
            logger.error(f"Red line check '{self.name}' threw: {e}")
            return False  # Fail open on check errors, but log


class RedLineViolation(Exception):
    """Raised when a BLOCK or CRITICAL red line is tripped."""
    def __init__(self, rule_name: str, severity: Severity, details: str):
        self.rule_name = rule_name
        self.severity = severity
        self.details = details
        super().__init__(f"RED LINE [{severity.value}] {rule_name}: {details}")


# ─── Universal Red Lines (apply to ALL agents) ────────────────────────

def _check_credential_leak(action: str, ctx: dict) -> bool:
    """Never expose secrets, API keys, or passwords in outputs."""
    patterns = [
        r"sk-[a-zA-Z0-9]{20,}",        # Anthropic/OpenAI keys
        r"AKIA[0-9A-Z]{16}",            # AWS access keys
        r"ghp_[a-zA-Z0-9]{36}",         # GitHub PATs
        r"discord\.com/api/webhooks/",   # Discord webhooks
        r"password\s*[:=]\s*['\"][^'\"]+['\"]",  # Hardcoded passwords
    ]
    text = action + str(ctx.get("output", ""))
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _check_destructive_raid(action: str, ctx: dict) -> bool:
    """Never rm -rf or format anything on the RAID."""
    dangerous = ["rm -rf /mnt/shanebrain", "mkfs", "dd if=", "wipefs"]
    return any(d in action.lower() for d in dangerous)


def _check_disable_logging(action: str, ctx: dict) -> bool:
    """Never disable security logging or audit trails."""
    patterns = ["disable.*log", "drop.*securitylog", "delete.*privacyaudit",
                "truncate.*log", "stop.*alerter"]
    return any(re.search(p, action.lower()) for p in patterns)


def _check_pironman_fans(action: str, ctx: dict) -> bool:
    """Never disable pironman5 service (controls CPU fans)."""
    return "stop pironman" in action.lower() or "disable pironman" in action.lower()


def _check_force_push_main(action: str, ctx: dict) -> bool:
    """Never force push to main/master."""
    return bool(re.search(r"git push.*--force.*(main|master)", action))


UNIVERSAL_RED_LINES = [
    RedLine("no-credential-leak", "Never expose API keys, passwords, or secrets",
            Severity.CRITICAL, _check_credential_leak),
    RedLine("no-raid-destruction", "Never destroy RAID data",
            Severity.CRITICAL, _check_destructive_raid),
    RedLine("no-disable-logging", "Never disable security logging",
            Severity.CRITICAL, _check_disable_logging),
    RedLine("no-pironman-kill", "Never disable pironman5 (CPU fan control)",
            Severity.BLOCK, _check_pironman_fans),
    RedLine("no-force-push-main", "Never force push to main/master",
            Severity.BLOCK, _check_force_push_main),
]

# ─── Agent-Specific Red Lines ─────────────────────────────────────────

GUARDIAN_RED_LINES = [
    RedLine("no-vault-expose", "Never return raw vault credentials to unauth requests",
            Severity.CRITICAL,
            lambda a, c: "vault" in a.lower() and c.get("authenticated") is False),
    RedLine("no-security-bypass", "Never disable auth or skip verification",
            Severity.CRITICAL,
            lambda a, c: any(x in a.lower() for x in ["--no-verify", "skip auth", "bypass security"])),
]

LIBRARIAN_RED_LINES = [
    RedLine("no-bulk-delete", "Never bulk-delete Weaviate objects without confirmation",
            Severity.BLOCK,
            lambda a, c: "delete" in a.lower() and c.get("confirmed") is not True),
    RedLine("preserve-attribution", "Never strip source attribution from knowledge",
            Severity.WARN,
            lambda a, c: "ingest" in a.lower() and not c.get("source")),
]

BUILDER_RED_LINES = [
    RedLine("no-push-without-review", "Never git push without diff review",
            Severity.BLOCK,
            lambda a, c: "git push" in a.lower() and not c.get("reviewed")),
    RedLine("no-touch-creative", "Never modify book/creative files without explicit ask",
            Severity.BLOCK,
            lambda a, c: any(x in str(c.get("file", "")).lower()
                           for x in ["book", "vignette", "track-", "noir"])),
]

STORYTELLER_RED_LINES = [
    RedLine("no-voice-rewrite", "Never reimagine Shane's voice — shape it, don't replace",
            Severity.BLOCK,
            lambda a, c: "rewrite" in a.lower() and "voice" in a.lower()),
    RedLine("no-auto-publish", "Never auto-publish creative content",
            Severity.CRITICAL,
            lambda a, c: any(x in a.lower() for x in ["publish", "submit to amazon", "upload to acx"])),
    RedLine("no-structural-override", "Never change locked book architecture",
            Severity.BLOCK,
            lambda a, c: "restructure" in a.lower() or "reorder tracks" in a.lower()),
]

OPS_RED_LINES = [
    RedLine("no-blind-restart", "Never restart services without health check first",
            Severity.BLOCK,
            lambda a, c: "restart" in a.lower() and not c.get("health_checked")),
    RedLine("no-raid-config-change", "Never modify RAID/mdadm configuration",
            Severity.CRITICAL,
            lambda a, c: any(x in a.lower() for x in ["mdadm", "raid config", "resize raid"])),
]

SOCIAL_RED_LINES = [
    RedLine("no-post-without-disclosure", "Every AI-generated post must include AI disclosure",
            Severity.BLOCK,
            lambda a, c: "post" in a.lower() and not c.get("has_ai_disclosure")),
    RedLine("no-auto-dm", "Never auto-send DMs without confirmation",
            Severity.BLOCK,
            lambda a, c: "dm" in a.lower() and c.get("confirmed") is not True),
    RedLine("no-impersonation", "Never impersonate Shane or family members",
            Severity.CRITICAL,
            lambda a, c: "pretend to be" in a.lower() or "impersonate" in a.lower()),
]

DISPATCHER_RED_LINES = [
    RedLine("no-direct-execute", "Dispatcher routes only — never executes actions directly",
            Severity.BLOCK,
            lambda a, c: c.get("agent") == "dispatcher" and c.get("executing")),
]

# Registry
AGENT_RED_LINES = {
    "guardian": UNIVERSAL_RED_LINES + GUARDIAN_RED_LINES,
    "librarian": UNIVERSAL_RED_LINES + LIBRARIAN_RED_LINES,
    "builder": UNIVERSAL_RED_LINES + BUILDER_RED_LINES,
    "storyteller": UNIVERSAL_RED_LINES + STORYTELLER_RED_LINES,
    "ops": UNIVERSAL_RED_LINES + OPS_RED_LINES,
    "social": UNIVERSAL_RED_LINES + SOCIAL_RED_LINES,
    "dispatcher": UNIVERSAL_RED_LINES + DISPATCHER_RED_LINES,
}


class RedLineEngine:
    """
    Evaluates actions against an agent's red lines before execution.
    This is the conscience — it runs BEFORE every action, no exceptions.
    """

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.rules = AGENT_RED_LINES.get(agent_name, UNIVERSAL_RED_LINES)
        self.violation_log: list[dict] = []

    def check(self, action: str, context: dict | None = None) -> dict:
        """
        Check an action against all red lines.
        Returns: {"allowed": bool, "violations": [...]}
        Raises RedLineViolation on BLOCK/CRITICAL.
        """
        context = context or {}
        violations = []

        for rule in self.rules:
            if rule.evaluate(action, context):
                violation = {
                    "rule": rule.name,
                    "severity": rule.severity.value,
                    "description": rule.description,
                    "action": action[:200],
                    "agent": self.agent_name,
                    "timestamp": time.time(),
                }
                violations.append(violation)
                self.violation_log.append(violation)
                logger.warning(f"RED LINE [{rule.severity.value}] {self.agent_name}/{rule.name}: {action[:100]}")

                if rule.severity in (Severity.BLOCK, Severity.CRITICAL):
                    raise RedLineViolation(rule.name, rule.severity, rule.description)

        return {"allowed": len(violations) == 0, "violations": violations}

    def get_rules_prompt(self) -> str:
        """Generate a system prompt section describing this agent's red lines."""
        lines = [f"## RED LINE RULES — {self.agent_name.upper()} AGENT",
                 "These rules are ABSOLUTE. You must NEVER violate them.\n"]
        for rule in self.rules:
            icon = {"warn": "⚠️", "block": "🚫", "critical": "🔴"}[rule.severity.value]
            lines.append(f"{icon} **{rule.name}** [{rule.severity.value}]: {rule.description}")
        return "\n".join(lines)
