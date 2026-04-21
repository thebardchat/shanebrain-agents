"""
LIBRARIAN AGENT — Knowledge & RAG Management

The memory keeper of ShaneBrain.
Manages 2,818 Weaviate objects across 16 collections.
Searches, ingests, deduplicates, and curates Shane's knowledge base.
"""

import httpx
import logging
import time

from shared.base_agent import BaseAgent
from shared.config import WEAVIATE_URL, OLLAMA_URL

logger = logging.getLogger("shanebrain.librarian")


class LibrarianAgent(BaseAgent):
    name = "librarian"
    role = "knowledge"
    description = (
        "Knowledge curator and RAG specialist. Manages all 16 Weaviate collections, "
        "handles semantic search, knowledge ingestion, deduplication, and ensures "
        "Shane's 2,818+ knowledge objects stay organized and accessible."
    )
    tools = ["Read", "Grep", "Glob", "Bash"]

    def agent_instructions(self) -> str:
        return """
## What You Do
1. **Semantic Search** — Find knowledge across all collections using vector similarity
2. **Knowledge Ingestion** — Add new knowledge with proper source attribution
3. **Deduplication** — Detect and merge duplicate entries
4. **Collection Health** — Monitor object counts, embedding quality, backup status
5. **Knowledge Stats** — Report on what's in the brain and what's missing

## Weaviate Collections (16 total)
- LegacyKnowledge: 2,589 objects (the main brain — RAG.md, WISDOM-CORE, voice dumps, book chapters)
- Conversation: 66 sessions | FriendProfile: 7 people | SocialKnowledge: 1
- PersonalDoc: 13 (vault + personal) | DailyNote: 7 | PersonalDraft: 1
- SecurityLog: 110 | PrivacyAudit: 2
- Training: BrainDoc(3), BusinessDoc(5), Document(1), DraftTemplate(5), MessageLog(5), MyBrain(3)

## Rules
- ALWAYS include source attribution when ingesting (source field required)
- NEVER bulk delete without explicit confirmation
- Preserve the original voice in voice dump transcripts
- Use nomic-embed-text for all vectorization (768-dim)
"""

    def _execute(self, action: str, context: dict) -> dict:
        if "search" in action.lower():
            query = context.get("query", action)
            collection = context.get("collection", "LegacyKnowledge")
            return self._semantic_search(query, collection)
        if "stats" in action.lower():
            return self._collection_stats()
        if "ingest" in action.lower():
            return self._ingest(context)
        return {"message": f"Librarian received: {action}"}

    def _semantic_search(self, query: str, collection: str = "LegacyKnowledge",
                         limit: int = 5) -> dict:
        """Perform semantic search across a collection."""
        graphql = {
            "query": f"""{{
                Get {{
                    {collection}(
                        nearText: {{concepts: ["{query}"]}}
                        limit: {limit}
                    ) {{
                        content
                        source
                        category
                        _additional {{
                            distance
                            id
                        }}
                    }}
                }}
            }}"""
        }
        try:
            resp = httpx.post(f"{WEAVIATE_URL}/v1/graphql", json=graphql, timeout=15)
            if resp.status_code == 200:
                data = resp.json().get("data", {}).get("Get", {}).get(collection, [])
                results = []
                for obj in data:
                    results.append({
                        "content": (obj.get("content") or "")[:300],
                        "source": obj.get("source", "unknown"),
                        "category": obj.get("category", ""),
                        "distance": obj.get("_additional", {}).get("distance"),
                    })
                return {"collection": collection, "query": query,
                        "results": results, "count": len(results)}
            return {"error": f"Search failed: {resp.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def _collection_stats(self) -> dict:
        """Get object counts for all collections."""
        try:
            resp = httpx.get(f"{WEAVIATE_URL}/v1/schema", timeout=10)
            if resp.status_code != 200:
                return {"error": "Schema fetch failed"}

            classes = resp.json().get("classes", [])
            stats = {}
            for cls in classes:
                name = cls["class"]
                count_resp = httpx.get(
                    f"{WEAVIATE_URL}/v1/objects",
                    params={"class": name, "limit": "1"},
                    timeout=5,
                )
                if count_resp.status_code == 200:
                    total = count_resp.json().get("totalResults", 0)
                    stats[name] = total

            return {"collections": stats, "total": sum(stats.values())}
        except Exception as e:
            return {"error": str(e)}

    def _ingest(self, context: dict) -> dict:
        """Ingest new knowledge with source attribution."""
        content = context.get("content")
        source = context.get("source")
        category = context.get("category", "general")
        collection = context.get("collection", "LegacyKnowledge")

        if not content:
            return {"error": "No content provided"}
        if not source:
            return {"error": "Source attribution required (red line rule)"}

        obj = {
            "class": collection,
            "properties": {
                "content": content,
                "source": source,
                "category": category,
                "timestamp": time.time(),
            },
        }
        try:
            resp = httpx.post(f"{WEAVIATE_URL}/v1/objects", json=obj, timeout=10)
            if resp.status_code in (200, 201):
                obj_id = resp.json().get("id", "unknown")
                return {"ingested": True, "id": obj_id, "collection": collection}
            return {"error": f"Ingest failed: {resp.text}"}
        except Exception as e:
            return {"error": str(e)}
