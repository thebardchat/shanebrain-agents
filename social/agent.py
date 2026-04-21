"""
SOCIAL AGENT — Discord, Facebook, Messenger Management

The voice to the world. Manages social media presence with
mandatory AI disclosure. Never impersonates. Never auto-DMs.
Every outbound message is accountable.
"""

import logging
from pathlib import Path

from shared.base_agent import BaseAgent
from shared.config import SHANEBRAIN_ROOT

logger = logging.getLogger("shanebrain.social")

SOCIAL_DIR = SHANEBRAIN_ROOT / "social"
PROMO_IMAGES = Path("/mnt/shanebrain-raid/mega-dashboard/promo-images")


class SocialAgent(BaseAgent):
    name = "social"
    role = "communications"
    description = (
        "Social media and communications manager. Handles Discord bot ops, "
        "Facebook promo posting, Messenger storyteller, and community engagement. "
        "Every AI-generated post includes mandatory disclosure."
    )
    tools = ["Read", "Grep", "Glob", "Bash"]

    def agent_instructions(self) -> str:
        return """
## What You Do
1. **Discord Management** — Monitor bot health, manage arcade bot, handle commands
2. **Facebook Promo** — Post book promos with random image from 55 promo images
3. **Messenger Storyteller** — Monitor OPTOUT/ANON/FORGET commands in messenger.py
4. **Content Drafting** — Draft social media posts for Shane's review
5. **Community Engagement** — Track friend interactions via FriendProfile collection

## Social Bots
- shanebrain-discord: Main Discord bot (systemd)
- shanebrain-social: Facebook/social posting bot (systemd)
- shanebrain-arcade: Game/arcade Discord bot (systemd)
- Messenger storyteller: angel-cloud/messenger.py

## AI Disclosure — MANDATORY
Every AI-generated or AI-assisted post MUST include one of:
- "[AI-assisted]" or "[AI-generated]" tag
- "Created with AI assistance" footer
- Equivalent clear disclosure

This is non-negotiable. No exceptions.

## Promo Assets
- 55 promo images at /mnt/shanebrain-raid/mega-dashboard/promo-images/
- Amazon link: https://www.amazon.com/Probably-Think-This-Book-About/dp/B0GT25R5FD
- Book title: "You Probably Think This Book Is About You"

## Rules
- NEVER auto-send DMs without Shane's confirmation
- NEVER impersonate Shane or family members
- NEVER post without AI disclosure
- Draft all posts for review before sending
- Respect OPTOUT/ANON/FORGET commands from messenger users
"""

    def _execute(self, action: str, context: dict) -> dict:
        if "status" in action.lower() or "bot" in action.lower():
            return self._bot_status()
        if "draft" in action.lower() or "post" in action.lower():
            return self._draft_post(context)
        if "promo" in action.lower():
            return self._promo_assets()
        return {"message": f"Social received: {action}"}

    def _bot_status(self) -> dict:
        """Check social bot service status."""
        import subprocess
        bots = ["shanebrain-discord", "shanebrain-social", "shanebrain-arcade"]
        status = {}
        for bot in bots:
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", bot],
                    capture_output=True, text=True, timeout=5,
                )
                status[bot] = result.stdout.strip()
            except Exception:
                status[bot] = "unknown"
        return {"bots": status}

    def _draft_post(self, context: dict) -> dict:
        """Draft a social media post (always includes AI disclosure)."""
        content = context.get("content", "")
        platform = context.get("platform", "general")

        if not content:
            return {"error": "No content provided for draft"}

        # Enforce AI disclosure
        disclosure = "\n\n[AI-assisted]"
        draft = f"{content}{disclosure}"

        return {
            "draft": draft,
            "platform": platform,
            "has_ai_disclosure": True,
            "status": "draft_ready — needs Shane's approval before posting",
        }

    def _promo_assets(self) -> dict:
        """List available promo assets."""
        images = list(PROMO_IMAGES.glob("*")) if PROMO_IMAGES.exists() else []
        return {
            "promo_images": len(images),
            "sample_files": [f.name for f in images[:5]],
            "amazon_link": "https://www.amazon.com/Probably-Think-This-Book-About/dp/B0GT25R5FD",
        }
