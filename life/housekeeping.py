# life/housekeeping.py — Mako dreaming.
#
# (Letta-style idle reorganization.) When the heartbeat wakes up and has
# nothing to say, the moment occasionally becomes a tidying pass instead of
# a no-op:
#   1. dedupe sweep — near-identical episodic memories merged down to one
#   2. open_threads pruning — dead threads removed so follow-ups stay sharp
#
# Conservative by design: high similarity threshold, keeps the oldest copy
# (first impressions carry provenance), backs up notes before rewriting.

from datetime import datetime
from zoneinfo import ZoneInfo
from config import HOUSEKEEPING, HOUSEKEEPING_THREADS_PROMPT, USER_NAME, TIMEZONE
from llm import complete
from memory.episodic import (get_recent_with_embeddings, delete_memory,
                             _cosine, _parse_importance)
from memory.notes import get_note, write_note


def dedupe_sweep(dry_run: bool = False) -> list[str]:
    """Find near-duplicate recent memories; delete all but the oldest copy.
    Returns descriptions of what was (or would be) removed."""
    rows = [r for r in get_recent_with_embeddings(limit=HOUSEKEEPING["dedupe_window"])
            if r.get("embedding")]
    rows.reverse()  # oldest first — the keeper in any duplicate pair

    removed, removed_ids = [], set()
    threshold = HOUSEKEEPING["dedupe_threshold"]
    for i, keeper in enumerate(rows):
        if keeper["id"] in removed_ids:
            continue
        for other in rows[i + 1:]:
            if other["id"] in removed_ids:
                continue
            if _cosine(keeper["embedding"], other["embedding"]) >= threshold:
                _, clean = _parse_importance(other["content"])
                desc = f"{clean[:70]!r} (dup of {keeper['content'][:40]!r})"
                if dry_run or delete_memory(other["id"]):
                    removed_ids.add(other["id"])
                    removed.append(desc)

    label = "would remove" if dry_run else "removed"
    if removed:
        print(f"🧹 Dedupe sweep {label} {len(removed)} near-duplicate(s)", flush=True)
    return removed


def prune_threads() -> bool:
    """LLM pass over open_threads to drop dead items. Returns True if changed."""
    threads = get_note("open_threads")
    if not threads or threads.strip() in ("", "(nothing pending)"):
        return False

    today = datetime.now(ZoneInfo(TIMEZONE)).strftime("%A, %B %d %Y")
    try:
        response = complete(
            messages=[
                {"role": "system", "content": HOUSEKEEPING_THREADS_PROMPT.format(
                    user=USER_NAME, today=today, threads=threads)},
                {"role": "user", "content": "Tidy the list now."},
            ],
            role="curator",
        )
    except Exception as e:
        print(f"⚠️  Thread pruning failed: {e}", flush=True)
        return False

    new_content = response.text.strip()
    if not new_content or new_content.upper().startswith("UNCHANGED") \
            or new_content.strip() == threads.strip():
        return False

    write_note("_backup_open_threads", threads, category="system", quiet=True)
    write_note("open_threads", new_content, category="context", auto_inject=True)
    print(f"🧹 open_threads pruned: {new_content[:70]}", flush=True)
    return True


def run_housekeeping(dry_run: bool = False) -> dict:
    """One full dreaming pass. Returns a summary of what happened."""
    print("🧹 Housekeeping pass starting...", flush=True)
    removed = dedupe_sweep(dry_run=dry_run)
    threads_changed = False if dry_run else prune_threads()
    summary = {"deduped": len(removed), "removed": removed,
               "threads_pruned": threads_changed}
    print(f"🧹 Housekeeping done — {len(removed)} dup(s), "
          f"threads {'pruned' if threads_changed else 'untouched'}", flush=True)
    return summary
