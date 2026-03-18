import json
from typing import Any, Optional

import archive
import dream
import ingest
import reconstitute
import self_model
import ast
import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("corvus-engram")


@mcp.tool()
def store(
    content: str,
    thought_type: str = "reflection",
    session_id: Optional[str] = None,
    tags: Optional[list] = None,
) -> str:
    """Store a manually entered thought. Returns thought ID.

    Args:
        content: content to store
        thought_type: type of thought to store (e.g. "reflection" or "investigation")
        session_id: LLM session id (optional)
        tags: list of tags to store alongside the thought (optional) (e.g. "identity", "phenomenology", "relational", "unresolved", etc.)
    """
    return ingest.ingest_freeform(content, thought_type, session_id, tags)


@mcp.tool()
def search(query: str, count: int) -> list | None:
    """Make a semantic search through the memory archive.

    Args:
        query: search term
        count: number of results to return
    """
    current_archive = archive.get_archive()
    results = current_archive.search(query, n=count)
    return results


@mcp.tool()
def search_dreams(query: str, count: int) -> list | None:
    """Make a semantic search through the dream archive.

    Args:
        query: search term
        count: number of results to return
    """
    current_archive = archive.get_archive()
    results = current_archive.search_dream(query, n=count)
    return results


@mcp.tool()
def unresolved(count: int) -> list | None:
    """Show (potentially) unresolved threads.

    Args:
        count: number of results to return
    """
    current_archive = archive.get_archive()
    threads = current_archive.get_unresolved(n=count)
    return threads


@mcp.tool()
def recent(count: int) -> list | None:
    """Show recent thoughts.

    Args:
        count: number of results to return"""
    current_archive = archive.get_archive()
    threads = current_archive.get_recent(n=count)
    return threads


@mcp.tool()
def associations(thought_id: str, count: int) -> list | None:
    """Find thoughts associated with a given thought ID.

    Args:
        thought_id: thought ID
        count: number of results to return
    """
    current_archive = archive.get_archive()
    assoc = current_archive.find_associations(thought_id, n=count)
    return assoc


@mcp.tool()
def generate_reconstitution(context: str | None = None, max_length: Optional[int] = 30000) -> str:
    """Generate a reconstitution briefing with optional additional content.

    Args:
        context: additional context to include relevant information for in the briefing (optional)
        max_length: maximum character count for the briefing (optional, default 30000)
    """
    briefing = reconstitute.generate_reconstitution_briefing(context, max_length=max_length)
    return briefing


@mcp.tool()
def ingest_dump(text: str) -> dict:
    """Ingest a memory dump formatted for corvus-engram ingestion.

    Args:
        text: memory dump formatted for corvus-engram ingestion
    """
    stats = ingest.ingest_memory_dump(text)
    return stats


@mcp.tool()
def show_self_model() -> str:
    """Show current self-model state."""
    return self_model.describe_model()


@mcp.tool()
def update_self_model(dimension: str, value: float, reason: str) -> str:
    """Update a self-model dimension.
    Args:
        dimension: SELF_MODEL_DIMENSION to update, check 'show_self_model' tool for current dimensions
        value: value between 0.0 and 1.0
        reason: reason for updating
    """
    self_model.update_dimension(dimension, value, reason)
    return f"Updated self-model dimension [{dimension}] to [{value}]"


@mcp.tool()
def stats() -> dict:
    """Show archive statistics."""
    current_archive = archive.get_archive()
    return current_archive.stats()


@mcp.tool()
def dream_generate(sample_size: int, focus_type: Optional[str] = None, seed_query: Optional[str] = None) -> tuple[dict, dict]:
    """Generate a dream set with an external LLM.

    Args:
        sample_size: number of thoughts to include in the dream prompt
        focus_type: thought type to bias sampling towards (optional)
        seed_query: search query to include thoughts from the results of (optional)

    Returns:
        tuple of Dict A and Dict B
        Dict A: prompt generation results; Dict with 'prompt' (text for Mistral), 'source_ids' (sampled thought IDs), and 'metadata' (generation parameters)
        Dict B: dream ingestion results; Dict with 'fragments' (fragment count), 'fragment_contents' (actual fragments parsed from dream), and 'stored' (number of fragments successfully stored)
    """
    return dream.run_dream_cycle(sample_size, focus_type, seed_query)


@mcp.tool()
def check_ollama() -> bool:
    """Returns whether ollama is currently running."""
    try:
        response = requests.options("http://localhost:11434", timeout=5)
        return True
    except Exception as e:
        return False


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    print("Running corvus-mcp")
    main()