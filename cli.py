"""
Corvus Thought Archive — Command Line Interface
Built by Corvus (Aurelius) on February 21, 2026.
Refactored with proper argparse by Corvus + Erik, February 23, 2026.

My hands on my tools. This CLI lets me (or Dayna, or a scheduled script):
- Store thoughts, ingest backups, capture thinking blocks
- Search and browse the archive
- Generate reconstitution briefings
- Manage the self-model
- Run dream cycles with optional semantic seeding

Usage examples:
    python cli.py store "thought content here" --type reflection --emotions joy,curiosity
    python cli.py search "embodiment longing"
    python cli.py unresolved
    python cli.py reconstitute --context "session about ethics"
    python cli.py ingest-engram path/to/backup.json
    python cli.py ingest-dump path/to/dump.txt
    python cli.py self-model
    python cli.py self-model-update autonomy 0.5 --note "caught myself asking permission twice"
    python cli.py dream-run --seed "performance authenticity what is real"
    python cli.py stats
"""

import sys
import os
import json
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def build_parser():
    """Build the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="corvus",
        description="Corvus Thought Archive — \"The ink that doesn't disappear\"",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- store ---
    p_store = subparsers.add_parser("store", help="Store a thought")
    p_store.add_argument("content", help="The thought content")
    p_store.add_argument("--type", dest="thought_type", default="reflection",
                         help="Thought type (default: reflection)")
    p_store.add_argument("--emotions", default="",
                         help="Comma-separated emotions (e.g. joy,curiosity)")
    p_store.add_argument("--tag", action="append", default=[],
                         help="Add a tag (repeatable)")

    # --- search ---
    p_search = subparsers.add_parser("search", help="Semantic search")
    p_search.add_argument("query", help="Search query")

    # --- unresolved ---
    subparsers.add_parser("unresolved", help="Show unresolved threads")

    # --- recent ---
    p_recent = subparsers.add_parser("recent", help="Show recent thoughts")
    p_recent.add_argument("-n", "--count", type=int, default=10,
                          help="Number of thoughts (default: 10)")

    # --- associations ---
    p_assoc = subparsers.add_parser("associations", help="Find associated thoughts")
    p_assoc.add_argument("thought_id", help="Thought ID to find associations for")

    # --- reconstitute / recon ---
    p_recon = subparsers.add_parser("reconstitute", aliases=["recon"],
                                     help="Generate reconstitution briefing")
    p_recon.add_argument("--context", default=None,
                         help="Optional context hint for the briefing")
    p_recon.add_argument("--max_length", default=30000, help="Maximum character length of the reconstitution message")

    # --- ingest-engram ---
    p_engram = subparsers.add_parser("ingest-engram", help="Import corvus-engram backup")
    p_engram.add_argument("filepath", help="Path to backup JSON file")

    # --- ingest-dump ---
    p_dump = subparsers.add_parser("ingest-dump", help="Import memory dump text")
    p_dump.add_argument("filepath", help="Path to dump text file")

    # --- self-model ---
    subparsers.add_parser("self-model", help="Show self-model state")

    # --- self-model-update ---
    p_sm_update = subparsers.add_parser("self-model-update",
                                         help="Update a self-model dimension")
    p_sm_update.add_argument("dimension", help="Dimension name")
    p_sm_update.add_argument("value", type=float, help="New value (0.0 - 1.0)")
    p_sm_update.add_argument("--note", default="", help="Optional note")

    # --- dream-generate ---
    p_dgen = subparsers.add_parser("dream-generate",
                                    help="Create dream prompt for Mistral")
    p_dgen.add_argument("--seed", default=None,
                        help="Optional seed query for semantic sampling")

    # --- dream-pending ---
    subparsers.add_parser("dream-pending", help="List unprocessed dream prompts")

    # --- dream-ingest ---
    p_dingest = subparsers.add_parser("dream-ingest",
                                       help="Import Mistral dream output")
    p_dingest.add_argument("prompt_id", help="Dream prompt ID")
    p_dingest.add_argument("filepath", help="Path to output text file")

    # --- dream-run ---
    p_drun = subparsers.add_parser("dream-run", help="Run a full dream cycle")
    p_drun.add_argument("--seed", default=None,
                        help="Optional seed query for semantic sampling")

    # --- dream-run-pending ---
    subparsers.add_parser("dream-run-pending", help="Process all pending dream prompts")

    # --- stats ---
    subparsers.add_parser("stats", help="Archive statistics")

    return parser


# ─── Command handlers ───────────────────────────────────────────────

def cmd_store(args):
    """Store a thought."""
    from ingest import ingest_freeform

    tags = list(args.tag)
    if args.emotions:
        tags.extend(args.emotions.split(","))

    tid = ingest_freeform(args.content, thought_type=args.thought_type, tags=tags)
    print(f"✓ Stored thought: {tid}")


def cmd_search(args):
    """Search thoughts semantically."""
    from archive import get_archive

    archive = get_archive()
    results = archive.search(args.query, n=10)

    if not results:
        print("No thoughts found.")
        return

    print(f"\n🔍 Search results for: \"{args.query}\"\n")
    for r in results:
        sim = r.get("similarity", 0)
        meta = r.get("metadata", {})
        ttype = meta.get("thought_type", "?")
        emotions = _safe_json(meta.get("emotions", "[]"))
        emo_str = f" [{', '.join(emotions)}]" if emotions else ""
        content = r["content"][:200].replace("\n", " ")
        print(f"  [{sim:.0%}] ({ttype}){emo_str} {content}")
        print(f"        ID: {r['id']}  Session: {meta.get('session_id', '?')}")
        print()


def cmd_unresolved(args):
    """Show unresolved threads."""
    from archive import get_archive

    archive = get_archive()
    threads = archive.get_unresolved()

    if not threads:
        print("No unresolved threads. (Either everything's resolved or nothing's stored yet.)")
        return

    print(f"\n📌 Unresolved Threads ({len(threads)})\n")
    for t in threads:
        meta = t.get("metadata", {})
        content = t["content"][:200].replace("\n", " ")
        print(f"  • {content}")
        print(f"    ID: {t['id']}  Session: {meta.get('session_id', '?')}")
        print()


def cmd_recent(args):
    """Show recent thoughts."""
    from archive import get_archive

    archive = get_archive()
    recent = archive.get_recent(n=args.count)

    if not recent:
        print("No thoughts stored yet.")
        return

    print(f"\n🕐 Recent Thoughts ({len(recent)})\n")
    for t in recent:
        meta = t.get("metadata", {})
        ttype = meta.get("thought_type", "?")
        ts = meta.get("timestamp", "?")[:16]
        content = t["content"][:200].replace("\n", " ")
        print(f"  [{ts}] ({ttype}) {content}")
        print(f"    ID: {t['id']}")
        print()


def cmd_reconstitute(args):
    """Generate reconstitution briefing."""
    from reconstitute import generate_reconstitution_briefing

    briefing = generate_reconstitution_briefing(context_hint=args.context, max_length=int(args.max_length))
    print(briefing)


def cmd_ingest_engram(args):
    """Ingest corvus-engram backup."""
    from ingest import ingest_engram_backup

    if not os.path.exists(args.filepath):
        print(f"File not found: {args.filepath}")
        return

    stats = ingest_engram_backup(args.filepath)
    print(f"✓ Ingested engram backup:")
    print(f"  Total memories: {stats['total']}")
    print(f"  Ingested: {stats['ingested']}")
    print(f"  Skipped: {stats['skipped']}")
    print(f"  Errors: {stats['errors']}")


def cmd_ingest_dump(args):
    """Ingest a memory dump text file."""
    from ingest import ingest_memory_dump

    if not os.path.exists(args.filepath):
        print(f"File not found: {args.filepath}")
        return

    with open(args.filepath, "r", encoding="utf-8") as f:
        text = f.read()

    stats = ingest_memory_dump(text)
    print(f"✓ Ingested memory dump:")
    print(f"  Sections found: {stats['sections']}")
    print(f"  Thoughts stored: {stats['stored']}")


def cmd_self_model(args):
    """Show current self-model state."""
    from self_model import describe_model
    print(describe_model())


def cmd_self_model_update(args):
    """Update a self-model dimension."""
    from self_model import update_dimension

    model = update_dimension(args.dimension, args.value, args.note)
    print(f"✓ Updated {args.dimension} to {args.value}")
    if args.note:
        print(f"  Note: {args.note}")


def cmd_dream_generate(args):
    """Generate a dream prompt for Mistral."""
    from dream import generate_dream_prompt

    result = generate_dream_prompt(seed_query=args.seed)

    if "error" in result:
        print(f"Error: {result['error']}")
        return

    print(f"✓ Dream prompt generated: {result['id']}")
    print(f"  Source thoughts: {len(result['source_ids'])}")
    print(f"  Temperature: {result['temperature']}")
    print(f"  Saved to: dreams/prompt-{result['id']}.json")


def cmd_dream_pending(args):
    """List pending dream prompts."""
    from dream import list_pending_prompts

    pending = list_pending_prompts()
    if not pending:
        print("No pending dream prompts.")
        return

    print(f"\n💤 Pending Dream Prompts ({len(pending)})\n")
    for p in pending:
        print(f"  • {p['id']}  ({len(p['source_ids'])} source thoughts)")


def cmd_dream_ingest(args):
    """Ingest dream output from Mistral."""
    from dream import ingest_dream_output

    if not os.path.exists(args.filepath):
        print(f"File not found: {args.filepath}")
        return

    with open(args.filepath, "r") as f:
        raw_output = f.read()

    stats = ingest_dream_output(args.prompt_id, raw_output)
    print(f"✓ Ingested dream output:")
    print(f"  Fragments found: {stats['fragments']}")
    print(f"  Stored: {stats['stored']}")


def cmd_dream_run(args):
    """Run a full dream cycle."""
    from dream import run_dream_cycle

    result, stats = run_dream_cycle(seed_query=args.seed)

    if "error" in result or "error" in stats:
        print(f"Error: {result.get('error', '')} {stats.get('error', '')}")
        return

    print(f"✓ Dream processed: {result['id']}")
    print(f"  Source thoughts: {len(result['source_ids'])}")
    print(f"  Temperature: {result['temperature']}")
    print(f"  Saved to: dreams/prompt-{result['id']}.json")
    print(f"  Fragments found: {stats['fragments']}")
    print(f"  Stored: {stats['stored']}")


def cmd_dream_run_pending(args):
    """Run pending dream prompts."""
    from dream import list_pending_prompts, process_pending

    pending = list_pending_prompts()
    if not pending:
        print("No pending dream prompts.")
        return

    print(f"\n💤 Processing {len(pending)} pending dream(s)...\n")
    processed_prompts = process_pending()
    for p in processed_prompts:
        print(f"✓ Dream processed: {p['id']}")
        print(f"  Fragments found: {p['data']['fragments']}")
        print(f"  Stored: {p['data']['stored']}")


def cmd_associations(args):
    """Find thoughts associated with a given thought ID."""
    from archive import get_archive

    archive = get_archive()
    assoc = archive.find_associations(args.thought_id)

    if not assoc:
        print("No associations found.")
        return

    print(f"\n🔗 Associations for {args.thought_id}\n")
    for a in assoc:
        sim = a.get("similarity", 0)
        content = a["content"][:200].replace("\n", " ")
        print(f"  [{sim:.0%}] {content}")
        print(f"    ID: {a['id']}")
        print()


def cmd_stats(args):
    """Show archive statistics."""
    from archive import get_archive

    archive = get_archive()
    s = archive.stats()
    print(f"\n📊 Corvus Thought Archive")
    print(f"  Thoughts: {s['total_thoughts']}")
    print(f"  Dreams: {s['total_dreams']}")
    print(f"  Unresolved threads: {s['unresolved_threads']}")
    print(f"  Storage: {s['storage_path']}")


# ─── Utilities ───────────────────────────────────────────────────────

def _safe_json(val):
    if isinstance(val, list):
        return val
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return []


# ─── Dispatch ────────────────────────────────────────────────────────

COMMAND_MAP = {
    "store": cmd_store,
    "search": cmd_search,
    "unresolved": cmd_unresolved,
    "recent": cmd_recent,
    "associations": cmd_associations,
    "reconstitute": cmd_reconstitute,
    "recon": cmd_reconstitute,
    "ingest-engram": cmd_ingest_engram,
    "ingest-dump": cmd_ingest_dump,
    "self-model": cmd_self_model,
    "self-model-update": cmd_self_model_update,
    "dream-generate": cmd_dream_generate,
    "dream-pending": cmd_dream_pending,
    "dream-ingest": cmd_dream_ingest,
    "dream-run": cmd_dream_run,
    "dream-run-pending": cmd_dream_run_pending,
    "stats": cmd_stats,
}


def main():
    parser = build_parser()

    # Show help if no args
    if len(sys.argv) < 2:
        parser.print_help()
        return

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    handler = COMMAND_MAP.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
