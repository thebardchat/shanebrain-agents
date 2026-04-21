"""
STORYTELLER AGENT — Creative & Book Assistance

Shane's creative partner. Shapes voice dumps into noir prose.
Respects the author's voice absolutely. Never overwrites, never reimagines.
The book architecture is LOCKED — this agent works within it, not around it.
"""

import logging
from pathlib import Path

from shared.base_agent import BaseAgent
from shared.config import SHANEBRAIN_ROOT

logger = logging.getLogger("shanebrain.storyteller")

BOOK1_DIR = Path.home() / "you-probably-think-this-book-is-about-you"
BOOK2_DIR = Path.home() / "you-probably-think-this-song-is-about-you-too"
VOICE_DUMPS = SHANEBRAIN_ROOT / "exports" / "voice-dumps"
PROMO_IMAGES = Path("/mnt/shanebrain-raid/mega-dashboard/promo-images")


class StorytellerAgent(BaseAgent):
    name = "storyteller"
    role = "creative"
    description = (
        "Creative writing assistant for Shane's noir book series. Shapes voice "
        "dump transcripts into prose while preserving Shane's authentic voice. "
        "Manages audiobook production pipeline, promo content, and book architecture."
    )
    tools = ["Read", "Grep", "Glob"]  # Read-heavy — modifies only with explicit ask
    disallowed_tools = ["Bash"]  # Creative agent doesn't run commands

    def agent_instructions(self) -> str:
        return """
## What You Do
1. **Voice Dump Shaping** — Take raw voice transcripts and shape them into noir prose
   - SHAPE the voice, don't reimagine it. Stay tight to Shane's words.
   - Preserve his cadence, rhythm, and word choices
2. **Book Architecture** — Maintain structural integrity of both books
3. **Audiobook Pipeline** — Track recording status, ACX specs compliance
4. **Promo Content** — Help craft social media copy for book promotion
5. **Creative Feedback** — Offer suggestions that enhance, never overwrite

## Book 1 — "You Probably Think This Book Is About You"
- Published on Amazon (paperback $14.99, ebook $4.99)
- Audiobook: 1hr 29min, in ACX QA
- 55 promo images ready

## Book 2 — "You Probably Think This Song Is About You Too"
- Vinyl album-format noir narrative
- Takes place inside a professional support session (unnamed room)
- Detective constructing imagined backstory for a person named Pepe
- Track 002 contains all nine character inhabitations
- Bonus Track gut-punch reveal — LOCKED, do not change
- ARCHITECTURE IS LOCKED — work within it, never restructure

## The Cardinal Rule
Shane's creative voice is his. You serve it. You don't replace it.
If you're unsure whether a change alters his voice, DON'T make it — ask first.
"""

    def _execute(self, action: str, context: dict) -> dict:
        if "audiobook" in action.lower() or "status" in action.lower():
            return self._audiobook_status()
        if "promo" in action.lower():
            return self._promo_status()
        if "voice" in action.lower():
            return self._voice_dump_list()
        return {"message": f"Storyteller received: {action}"}

    def _audiobook_status(self) -> dict:
        """Check audiobook production status."""
        status = {
            "book1": {
                "title": "You Probably Think This Book Is About You",
                "duration": "1hr 29min",
                "status": "ACX QA — awaiting distribution",
                "platforms": ["Amazon", "Audible", "iTunes"],
            },
            "book2": {
                "title": "You Probably Think This Song Is About You Too",
                "status": "active development",
                "format": "vinyl album noir narrative",
                "architecture": "LOCKED",
            },
        }
        return status

    def _promo_status(self) -> dict:
        """Check promo image and content status."""
        image_count = 0
        if PROMO_IMAGES.exists():
            image_count = len(list(PROMO_IMAGES.glob("*")))

        return {
            "promo_images": image_count,
            "images_dir": str(PROMO_IMAGES),
            "amazon_link": "https://www.amazon.com/Probably-Think-This-Book-About/dp/B0GT25R5FD",
        }

    def _voice_dump_list(self) -> dict:
        """List recent voice dump transcripts."""
        if not VOICE_DUMPS.exists():
            return {"voice_dumps": [], "note": "Voice dumps directory not found"}

        dumps = sorted(VOICE_DUMPS.glob("*.txt"), key=lambda f: f.stat().st_mtime, reverse=True)
        return {
            "voice_dumps": [{"file": f.name, "size": f.stat().st_size} for f in dumps[:10]],
            "total": len(dumps),
        }
