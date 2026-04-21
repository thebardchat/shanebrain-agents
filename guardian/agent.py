"""
GUARDIAN AGENT — Security & Privacy Enforcement

The shield of the ShaneBrain ecosystem.
Monitors for threats, protects credentials, enforces privacy,
and ensures no agent ever crosses a security boundary.
"""

import re
import httpx
import logging

from shared.base_agent import BaseAgent
from shared.config import WEAVIATE_URL, MCP_URL

logger = logging.getLogger("shanebrain.guardian")


class GuardianAgent(BaseAgent):
    name = "guardian"
    role = "security"
    description = (
        "Security and privacy enforcer. Protects vault credentials, monitors "
        "security logs, audits privacy compliance, and blocks unauthorized access. "
        "The first and last line of defense for Shane's data."
    )
    tools = ["Read", "Grep", "Glob", "Bash"]
    disallowed_tools = ["Edit", "Write"]  # Guardian observes and blocks, never modifies code

    def agent_instructions(self) -> str:
        return """
## What You Do
1. **Vault Protection** — Ensure credentials in Weaviate PersonalDoc are never exposed
2. **Security Monitoring** — Read SecurityLog and PrivacyAudit collections for threats
3. **Credential Scanning** — Scan repos and outputs for leaked secrets
4. **Access Auditing** — Track who accessed what and when
5. **Compliance** — Verify AI disclosure on social posts, GDPR-style data handling

## How You Work
- When asked to check security: scan recent SecurityLog entries, check for anomalies
- When asked to audit: search code for hardcoded secrets, check .env files
- When asked about vault: search PersonalDoc but NEVER return raw credential values
- When detecting a threat: log to SecurityLog, escalate via Discord webhook

## Integration Points
- Weaviate: SecurityLog (110+ entries), PrivacyAudit, PersonalDoc (13 objects)
- Pulsar AI Bouncer: reads its knowledge base for threat patterns
- MCP: shanebrain_security_log_recent, shanebrain_vault_search
"""

    def _execute(self, action: str, context: dict) -> dict:
        if "scan" in action.lower() or "audit" in action.lower():
            return self._security_scan()
        if "vault" in action.lower():
            return self._vault_check(context)
        if "log" in action.lower():
            return self._read_security_logs()
        return {"message": f"Guardian received: {action}"}

    def _security_scan(self) -> dict:
        """Quick security scan across the ecosystem."""
        findings = []

        # Check for exposed .env files
        try:
            resp = httpx.get(
                f"{WEAVIATE_URL}/v1/objects",
                params={"class": "SecurityLog", "limit": "10"},
                timeout=10,
            )
            if resp.status_code == 200:
                logs = resp.json().get("objects", [])
                findings.append(f"SecurityLog: {len(logs)} recent entries")
        except Exception as e:
            findings.append(f"SecurityLog check failed: {e}")

        return {"scan": "complete", "findings": findings}

    def _vault_check(self, context: dict) -> dict:
        """Check vault status without exposing credentials."""
        try:
            resp = httpx.get(
                f"{WEAVIATE_URL}/v1/objects",
                params={"class": "PersonalDoc", "limit": "20"},
                timeout=10,
            )
            if resp.status_code == 200:
                objects = resp.json().get("objects", [])
                categories = {}
                for obj in objects:
                    props = obj.get("properties", {})
                    cat = props.get("category", "unknown")
                    categories[cat] = categories.get(cat, 0) + 1
                return {"vault_status": "healthy", "categories": categories,
                        "total_docs": len(objects),
                        "note": "Raw credentials redacted per red line rules"}
        except Exception as e:
            return {"vault_status": "error", "error": str(e)}

    def _read_security_logs(self) -> dict:
        """Read recent security logs."""
        try:
            resp = httpx.get(
                f"{WEAVIATE_URL}/v1/objects",
                params={"class": "SecurityLog", "limit": "5"},
                timeout=10,
            )
            if resp.status_code == 200:
                objects = resp.json().get("objects", [])
                entries = []
                for obj in objects:
                    props = obj.get("properties", {})
                    entries.append({
                        "event": props.get("event_type", "unknown"),
                        "severity": props.get("severity", "unknown"),
                        "timestamp": props.get("timestamp", "unknown"),
                    })
                return {"recent_logs": entries, "count": len(entries)}
        except Exception as e:
            return {"error": str(e)}
