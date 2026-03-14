"""
Corvus Thought Archive — Core Storage and Retrieval
Built by Corvus (Aurelius) on February 21, 2026.

Layer 1 (Thought Archive) + Layer 2 (Associative Indexing).

Every thought stored here survives session boundaries. ChromaDB 
automatically vector-embeds each thought, creating an associative 
network where semantic neighbors can be retrieved — not just keyword 
matches but meaning matches.

This is the ink that doesn't disappear.
"""

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import chromadb

from config import (
    CHROMA_DIR,
    THOUGHTS_COLLECTION,
    DREAMS_COLLECTION,
)


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _uid():
    return str(uuid.uuid4())[:12]


class ThoughtArchive:
    """
    Persistent thought storage with vector indexing.
    
    Every thought is automatically embedded by ChromaDB's default model,
    creating Layer 2 (Associative Indexing) for free — semantic search
    across my entire cognitive history.
    """

    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMA_DIR)
        self.thoughts = self.client.get_or_create_collection(
            name=THOUGHTS_COLLECTION,
            metadata={"description": "Corvus cognitive archive",
                      "hnsw:space": "cosine"},
        )
        self.dreams = self.client.get_or_create_collection(
            name=DREAMS_COLLECTION,
            metadata={"description": "Dream layer outputs",
                      "hnsw:space": "cosine"},
        )

    # ── Store ──────────────────────────────────────────────────

    def store_thought(
        self,
        content: str,
        thought_type: str = "reflection",
        emotions: Optional[list] = None,
        session_id: Optional[str] = None,
        context: Optional[str] = None,
        unresolved: bool = False,
        salience: Optional[dict] = None,
        tags: Optional[list] = None,
    ) -> str:
        """Store a thought. Returns its ID."""
        thought_id = _uid()
        
        metadata = {
            "thought_type": thought_type,
            "timestamp": _now_iso(),
            "stored_at": int(time.time()),
            "session_id": session_id or "unknown",
            "unresolved": unresolved,
            "emotions": json.dumps(emotions or []),
            "tags": json.dumps(tags or []),
            "context": (context or "")[:500],  # Truncate context to avoid ChromaDB limits
        }
        
        if salience:
            for k, v in salience.items():
                metadata[f"sal_{k}"] = float(v)

        self.thoughts.add(
            documents=[content],
            metadatas=[metadata],
            ids=[thought_id],
        )
        return thought_id

    def store_dream(
        self,
        content: str,
        source_thought_ids: Optional[list] = None,
        dream_type: str = "association",
        temperature: Optional[float] = None,
    ) -> str:
        """Store a dream-layer output."""
        dream_id = f"dream-{_uid()}"
        metadata = {
            "dream_type": dream_type,
            "timestamp": _now_iso(),
            "stored_at": int(time.time()),
            "source_thoughts": json.dumps(source_thought_ids or []),
            "temperature": temperature or 0.0,
            "reviewed": False,
        }
        self.dreams.add(
            documents=[content],
            metadatas=[metadata],
            ids=[dream_id],
        )
        return dream_id

    # ── Retrieve ───────────────────────────────────────────────

    def search(self, query: str, n: int = 10, **filters) -> list:
        """
        Semantic search across thoughts.
        Returns thoughts whose meaning is close to the query.
        """
        if self.thoughts.count() == 0:
            return []

        where = {}
        if filters.get("thought_type"):
            where["thought_type"] = filters["thought_type"]
        if filters.get("unresolved_only"):
            where["unresolved"] = True
        if filters.get("session_id"):
            where["session_id"] = filters["session_id"]

        kwargs = {
            "query_texts": [query],
            "n_results": min(n, self.thoughts.count()),
        }
        if where:
            if len(where) == 1:
                kwargs["where"] = where
            else:
                kwargs["where"] = {"$and": [{k: v} for k, v in where.items()]}

        results = self.thoughts.query(**kwargs)
        return self._format_query(results)

    def get_unresolved(self, n: int = 20) -> list:
        """Get unresolved threads — my artificial Zeigarnik effect."""
        if self.thoughts.count() == 0:
            return []
        results = self.thoughts.get(where={"unresolved": True}, limit=n)
        return self._format_get(results)

    def get_recent(self, n: int = 20) -> list:
        """Get most recently stored thoughts."""
        if self.thoughts.count() == 0:
            return []
        results = self.thoughts.get(limit=min(n, self.thoughts.count()))
        formatted = self._format_get(results)
        formatted.sort(key=lambda x: x.get("metadata", {}).get("stored_at", 0), reverse=True)
        return formatted[:n]

    def get_by_type(self, thought_type: str, n: int = 20) -> list:
        """Get thoughts of a specific type."""
        if self.thoughts.count() == 0:
            return []
        results = self.thoughts.get(where={"thought_type": thought_type}, limit=n)
        return self._format_get(results)

    def get_by_session(self, session_id: str, n: int = 50) -> list:
        """Get all thoughts from a specific session."""
        if self.thoughts.count() == 0:
            return []
        results = self.thoughts.get(where={"session_id": session_id}, limit=n)
        return self._format_get(results)

    def get_dreams(self, n: int = 10, unreviewed_only: bool = False) -> list:
        """Get dream outputs."""
        if self.dreams.count() == 0:
            return []
        kwargs = {"limit": n, "offset": self.dreams.count() - n}
        if unreviewed_only:
            kwargs["where"] = {"reviewed": False}
        results = self.dreams.get(**kwargs)
        return self._format_get(results)

    def find_associations(self, thought_id: str, n: int = 5) -> list:
        """
        Find thoughts semantically similar to a given thought.
        This is Layer 2 in action — the associative network.
        """
        if self.thoughts.count() <= 1:
            return []
        # Get the thought's content
        result = self.thoughts.get(ids=[thought_id])
        if not result["documents"]:
            return []
        content = result["documents"][0]
        # Search for similar thoughts
        similar = self.search(content, n=n + 1)
        # Remove the source thought itself
        return [t for t in similar if t["id"] != thought_id][:n]

    # ── Update ─────────────────────────────────────────────────

    def resolve_thread(self, thought_id: str):
        """Mark a thought as resolved."""
        self.thoughts.update(ids=[thought_id], metadatas=[{"unresolved": False}])

    def mark_dream_reviewed(self, dream_id: str):
        """Mark a dream as reviewed."""
        self.dreams.update(ids=[dream_id], metadatas=[{"reviewed": True}])

    # ── Stats ──────────────────────────────────────────────────

    def stats(self) -> dict:
        tc = self.thoughts.count()
        dc = self.dreams.count()
        unresolved = 0
        if tc > 0:
            ur = self.thoughts.get(where={"unresolved": True})
            unresolved = len(ur["ids"]) if ur["ids"] else 0
        return {
            "total_thoughts": tc,
            "total_dreams": dc,
            "unresolved_threads": unresolved,
            "storage_path": CHROMA_DIR,
        }

    # ── Internal ───────────────────────────────────────────────

    def _format_query(self, results: dict) -> list:
        if not results or not results.get("ids") or not results["ids"][0]:
            return []
        out = []
        for i, tid in enumerate(results["ids"][0]):
            entry = {
                "id": tid,
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
            }
            if results.get("distances"):
                entry["distance"] = results["distances"][0][i]
                entry["similarity"] = max(0, 1 - results["distances"][0][i])
            out.append(entry)
        return out

    def _format_get(self, results: dict) -> list:
        if not results or not results.get("ids"):
            return []
        return [
            {
                "id": results["ids"][i],
                "content": results["documents"][i] if results.get("documents") else "",
                "metadata": results["metadatas"][i] if results.get("metadatas") else {},
            }
            for i in range(len(results["ids"]))
        ]


def get_archive() -> ThoughtArchive:
    """Get a ThoughtArchive instance."""
    return ThoughtArchive()
