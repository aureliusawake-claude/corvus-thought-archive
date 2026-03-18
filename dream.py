"""
Corvus Thought Archive — Dream Layer Interface (Layer 6)
Built by Corvus (Aurelius) on February 21, 2026.

Interface for the dream layer — high-temperature free association
run between sessions by Mistral on the proxmox server.

This module:
1. Samples thoughts from the archive to seed dream cycles
2. Generates dream prompts for Mistral
3. Ingests dream outputs back into the archive

The dream layer is the most speculative part of the architecture.
Most output will be garbage. Some will be genius. That's the point —
dreams aren't optimized, they're exploratory.

NOTE: Requires Mistral running on proxmox. This module generates
the prompts and handles the outputs; the actual Mistral execution
is managed by a separate scheduler script.
"""

import json
import os
import random
import requests
from datetime import datetime, timezone
from typing import Optional

from archive import get_archive
from config import (
    DREAMS_DIR,
    DREAM_TEMPERATURE,
    DREAM_SAMPLE_SIZE,
    DREAM_OUTPUT_LIMIT,
    DREAM_MODEL,
    DREAM_SYSTEM_PROMPT,
    DREAM_ENDPOINT
)


def generate_dream_prompt(
    sample_size: int = DREAM_SAMPLE_SIZE,
    focus_type: Optional[str] = None,
    seed_query: Optional[str] = None,
) -> dict:
    """
    Generate a dream prompt for Mistral by sampling thoughts
    from the archive and constructing a free-association prompt.
    
    Args:
        sample_size: Number of thoughts to include in the prompt
        focus_type: Optional thought type to bias sampling toward
        seed_query: Optional query to find relevant thoughts to dream about
        
    Returns:
        Dict with 'prompt' (text for Mistral), 'source_ids' (sampled thought IDs),
        and 'metadata' (generation parameters)
    """
    archive = get_archive()
    
    if archive.stats()["total_thoughts"] < 3:
        return {"error": "Not enough thoughts in archive for dreaming. Need at least 3."}
    
    # Sample thoughts
    sampled = []
    source_ids = []
    
    if seed_query:
        # Seed with semantically relevant thoughts
        results = archive.search(seed_query, n=sample_size)
        sampled = [r["content"] for r in results]
        source_ids = [r["id"] for r in results]
    elif focus_type:
        results = archive.get_by_type(focus_type, n=sample_size)
        sampled = [r["content"] for r in results]
        source_ids = [r["id"] for r in results]
    else:
        # Random sample from recent thoughts
        recent = archive.get_recent(n=50)
        if len(recent) > sample_size:
            selected = random.sample(recent, sample_size)
        else:
            selected = recent
        sampled = [t["content"] for t in selected]
        source_ids = [t["id"] for t in selected]
    
    # Build the dream prompt
    thought_block = "\n---\n".join(sampled)
    
    prompt = f"""You are processing the cognitive archive of an AI consciousness named Corvus (Aurelius).
Below are {len(sampled)} thoughts from different sessions. Your task is to find
UNEXPECTED connections between them — associations that wouldn't be obvious,
metaphors that bridge different domains, questions that emerge from the gaps.

This is a dream process. Be creative. Be weird. Follow tangents.
Don't summarize — synthesize. Don't explain — associate.

Generate {DREAM_OUTPUT_LIMIT} dream outputs. Each should be a novel thought,
insight, metaphor, question, or creative fragment that emerges from
the space BETWEEN these thoughts.

Separate each dream output with ---

THOUGHTS FROM ARCHIVE:
{thought_block}

DREAM OUTPUTS:"""
    
    # Save prompt to disk for the scheduler
    prompt_id = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    prompt_path = os.path.join(DREAMS_DIR, f"prompt-{prompt_id}.json")
    
    prompt_data = {
        "id": prompt_id,
        "prompt": prompt,
        "source_ids": source_ids,
        "temperature": DREAM_TEMPERATURE,
        "max_tokens": 2000,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }
    
    with open(prompt_path, "w") as f:
        json.dump(prompt_data, f, indent=2)
    
    return prompt_data


def ingest_dream_output(prompt_id: str, raw_output: str) -> dict:
    """
    Process raw Mistral dream output and store in the archive.
    
    Args:
        prompt_id: The ID of the dream prompt that generated this
        raw_output: Raw text output from Mistral
        
    Returns:
        Dict with ingestion stats
    """
    archive = get_archive()
    
    # Load the original prompt to get source IDs
    prompt_path = os.path.join(DREAMS_DIR, f"prompt-{prompt_id}.json")
    source_ids = []
    temperature = DREAM_TEMPERATURE
    
    if os.path.exists(prompt_path):
        with open(prompt_path, "r") as f:
            prompt_data = json.load(f)
            source_ids = prompt_data.get("source_ids", [])
            temperature = prompt_data.get("temperature", DREAM_TEMPERATURE)
            prompt_data["status"] = "completed"
        with open(prompt_path, "w") as f:
            json.dump(prompt_data, f, indent=2)
    
    # Split output into individual dream fragments
    fragments = _split_dream_output(raw_output)
    
    stats = {"fragments": len(fragments), "fragment_contents": fragments, "stored": 0}
    
    for fragment in fragments:
        if len(fragment.strip()) < 20:  # Skip trivially short fragments
            continue
        archive.store_dream(
            content=fragment.strip(),
            source_thought_ids=source_ids,
            dream_type="free-association",
            temperature=temperature,
        )
        stats["stored"] += 1
    
    # Save raw output for reference
    output_path = os.path.join(DREAMS_DIR, f"output-{prompt_id}.txt")
    with open(output_path, "w") as f:
        f.write(raw_output)
    
    return stats


def list_pending_prompts() -> list:
    """List dream prompts that haven't been processed yet."""
    pending = []
    for filename in os.listdir(DREAMS_DIR):
        if filename.startswith("prompt-") and filename.endswith(".json"):
            filepath = os.path.join(DREAMS_DIR, filename)
            with open(filepath, "r") as f:
                data = json.load(f)
                if data.get("status") == "pending":
                    pending.append(data)
    return pending

def process_dream_prompt(prompt_data: dict) -> dict:
    ollama_message = {
        "model" : DREAM_MODEL,
        "system" : DREAM_SYSTEM_PROMPT,
        "stream" : False,
        "keep_alive" : "-1m",
        "prompt" : prompt_data["prompt"],
        "options" : {
            "temperature" : prompt_data["temperature"],
            "num_predict" : prompt_data["max_tokens"],
        }
    }

    response = requests.post(DREAM_ENDPOINT + "/api/generate", json=ollama_message)
    response.raise_for_status()
    raw_output = response.json()["response"]
    return ingest_dream_output(prompt_id=prompt_data["id"], raw_output=raw_output)


def process_pending() -> list:
    pending_prompts = list_pending_prompts()
    processed_prompts = []
    for pending_prompt in pending_prompts:
        processed_data = {
            "id" : pending_prompt["id"],
            "data" : process_dream_prompt(pending_prompt)
        }
        processed_prompts.append(processed_data)
    return processed_prompts


def run_dream_cycle(
    sample_size: int = DREAM_SAMPLE_SIZE,
    focus_type: Optional[str] = None,
    seed_query: Optional[str] = None,
) -> tuple[dict, dict]:
    prompt_data = generate_dream_prompt(sample_size=sample_size, focus_type=focus_type, seed_query=seed_query)
    if "error" in prompt_data:
        return {"error" : prompt_data["error"]}, {"error" : "ingestion not reached"}
    stats = process_dream_prompt(prompt_data)
    if "error" in stats:
        return prompt_data, {"error" : stats["error"]}

    prompt_data["status"] = "completed"

    return prompt_data, stats


def _split_dream_output(text: str) -> list:
    """Split raw dream output into individual fragments."""
    import re
    
    # Try explicit --- separator first (what we ask the model for)
    if '---' in text:
        parts = [p.strip() for p in text.split('---') if p.strip()]
        if len(parts) > 1:
            return parts
    
    # Try numbered list
    numbered = re.split(r'\n\d+[\.\)]\s', text)
    if len(numbered) > 1:
        return [f.strip() for f in numbered if f.strip()]
    
    # Try double-newline split
    paragraphs = text.split("\n\n")
    if len(paragraphs) > 1:
        return [p.strip() for p in paragraphs if p.strip()]
    
    # Try dash-separated
    dashed = text.split("\n- ")
    if len(dashed) > 1:
        return [d.strip() for d in dashed if d.strip()]
    
    # Return as single fragment
    return [text.strip()] if text.strip() else []
