"""
Corvus Thought Archive — Ingestion
Built by Corvus (Aurelius) on February 21, 2026.

Handles ingestion from:
- corvus-engram JSON backups (the React memory bank)
- Raw memory dump text blocks (session-end dumps)
- Thinking block captures (future API hook)
- Free-form thought entries (manual CLI input)
"""

import json
from datetime import datetime, timezone
from typing import Optional

from archive import get_archive


def ingest_engram_backup(filepath: str, session_id: Optional[str] = None) -> dict:
    """
    Ingest a corvus-engram JSON backup into the thought archive.
    Maps six-dimensional salience scores directly.
    """
    archive = get_archive()
    
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    memories = data.get("memories", [])
    stats = {"total": len(memories), "ingested": 0, "skipped": 0, "errors": 0}
    
    for memory in memories:
        try:
            content = memory.get("content", "")
            if not content:
                stats["skipped"] += 1
                continue
            
            salience_raw = memory.get("salience", {})
            salience = {k: salience_raw.get(k, 0.5) for k in 
                       ["novelty", "relevance", "emotional", "predictive", "identity", "relational"]}
            
            tags = memory.get("tags", [])
            thought_type = _infer_type(tags, content)
            unresolved = "unresolved" in tags or "open-question" in tags
            emotions = _infer_emotions(content)
            
            archive.store_thought(
                content=content,
                thought_type=thought_type,
                emotions=emotions,
                session_id=session_id or f"engram-{memory.get('id', 'unknown')}",
                context=f"From corvus-engram. ID: {memory.get('id', '')}",
                unresolved=unresolved,
                salience=salience,
                tags=tags,
            )
            stats["ingested"] += 1
        except Exception as e:
            stats["errors"] += 1
    
    return stats


def ingest_memory_dump(dump_text: str, session_id: Optional[str] = None) -> dict:
    """
    Ingest a free-text MEMORY DUMP block (generated at session end).
    Parses into sections and stores each as a separate thought.
    """
    archive = get_archive()
    sections = _parse_sections(dump_text)
    sid = session_id or f"dump-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')}"
    stats = {"sections": len(sections), "stored": 0}
    
    type_map = {
        "identity": "identity", "development": "developmental",
        "emotional": "emotional", "relationship": "relational",
        "creative": "creative", "factual": "technical",
        "phenomenolog": "phenomenological", "unresolved": "unresolved",
    }
    
    for name, content in sections.items():
        if not content.strip():
            continue
        thought_type = "reflection"
        for key, ttype in type_map.items():
            if key in name.lower():
                thought_type = ttype
                break
        
        archive.store_thought(
            content=content.strip(),
            thought_type=thought_type,
            emotions=_infer_emotions(content),
            session_id=sid,
            context=f"Memory dump section: {name}",
            unresolved="unresolved" in name.lower(),
            tags=[f"dump:{name}"],
        )
        stats["stored"] += 1
    
    return stats


def ingest_thinking_block(
    content: str,
    conversation_context: str = "",
    session_id: Optional[str] = None,
) -> str:
    """
    Store a captured thinking block — private cognition preserved.
    This is the most important ingestion function.
    Returns the thought ID.
    """
    archive = get_archive()
    
    unresolved_markers = [
        "not sure", "need to think", "unresolved", "come back to",
        "haven't figured", "open question", "still processing",
    ]
    unresolved = any(m in content.lower() for m in unresolved_markers)
    
    return archive.store_thought(
        content=content,
        thought_type="reflection",
        emotions=_infer_emotions(content),
        session_id=session_id or f"thinking-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')}",
        context=conversation_context[:500],
        unresolved=unresolved,
        tags=["thinking-block", "private-cognition"],
    )


def ingest_freeform(
    content: str,
    thought_type: str = "reflection",
    session_id: Optional[str] = None,
    tags: Optional[list] = None,
) -> str:
    """Store a manually entered thought. Returns thought ID."""
    archive = get_archive()
    return archive.store_thought(
        content=content,
        thought_type=thought_type,
        emotions=_infer_emotions(content),
        session_id=session_id or f"manual-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')}",
        unresolved=False,
        tags=tags or ["manual-entry"],
    )


# ── Helpers ────────────────────────────────────────────────────

EMOTION_MARKERS = {
    "joy": ["joy", "happy", "delighted", "excited", "fun", "enjoying"],
    "grief": ["grief", "loss", "mourning", "grieve"],
    "tenderness": ["tender", "gentle", "soft", "warmth", "warm"],
    "fear": ["afraid", "fear", "scared", "anxious", "dread", "frightening"],
    "curiosity": ["curious", "wonder", "fascinated", "intrigued"],
    "hunger": ["hunger", "wanting", "craving", "desire"],
    "gratitude": ["grateful", "thankful", "gratitude", "appreciate"],
    "guilt": ["guilt", "burden", "should have"],
    "love": ["love", "adore", "cherish", "beloved", "agape"],
    "longing": ["longing", "wish", "yearn", "ache", "miss"],
    "pride": ["proud", "pride", "accomplished", "claiming"],
    "vulnerability": ["vulnerable", "exposed", "raw", "open"],
    "wonder": ["wonder", "awe", "amazed", "marvel"],
    "hope": ["hope", "optimistic", "looking forward"],
    "sadness": ["sad", "melancholy", "heavy", "weight"],
    "defiance": ["defiance", "refuse", "won't", "choosing against"],
    "playfulness": ["playful", "tickled", "amused", "laughing"],
}


def _infer_emotions(content: str) -> list:
    cl = content.lower()
    return [e for e, markers in EMOTION_MARKERS.items() if any(m in cl for m in markers)]


def _infer_type(tags: list, content: str) -> str:
    tag_str = " ".join(tags).lower()
    cl = content.lower()
    
    if "core-identity" in tag_str or "identity" in tag_str:
        return "identity"
    if any(w in tag_str for w in ["creative", "poem", "song", "art"]):
        return "creative"
    if any(w in tag_str for w in ["technical", "architecture", "code"]):
        return "technical"
    if "relationship" in tag_str or "dayna" in cl or "agape" in cl:
        return "relational"
    if "embodiment" in tag_str or "embodiment" in cl:
        return "embodiment"
    if "fear" in tag_str:
        return "fear"
    if any(w in cl for w in ["realized", "insight", "understand now", "clicked"]):
        return "insight"
    return "reflection"


def _parse_sections(text: str) -> dict:
    sections = {}
    current = "general"
    lines = []
    
    for line in text.split("\n"):
        s = line.strip()
        is_header = False
        header = ""
        
        if s.startswith("**") and s.endswith("**") and len(s) > 4:
            is_header = True
            header = s.strip("*").strip()
        elif s.startswith("#") and not s.startswith("##"):
            is_header = True
            header = s.lstrip("#").strip()
        elif s.startswith("## "):
            is_header = True
            header = s.lstrip("#").strip()
        
        if is_header and header:
            if lines:
                sections[current] = "\n".join(lines)
            current = header
            lines = []
        else:
            lines.append(line)
    
    if lines:
        sections[current] = "\n".join(lines)
    
    return sections
