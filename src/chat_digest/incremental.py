"""Incremental digest updates - append new messages to existing digests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from .parser import parse_transcript
from .schemas import Message, ThreadDigest, ThreadMetadata, Summary
from .summarize import extract_signals, generate_summary


def load_existing_digest(path: Path) -> Optional[ThreadDigest]:
    """
    Load an existing digest from JSON file.
    
    Returns None if file doesn't exist or is invalid.
    """
    if not path.exists():
        return None
    
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return ThreadDigest(**data)
    except (json.JSONDecodeError, ValueError):
        return None


def merge_messages(
    existing_messages: List[Message],
    new_messages: List[Message],
) -> List[Message]:
    """
    Merge new messages with existing ones, avoiding duplicates.
    
    Uses message order as the deduplication key.
    """
    existing_orders = {msg.order for msg in existing_messages}
    
    # Add only new messages that don't exist
    merged = list(existing_messages)
    for msg in new_messages:
        if msg.order not in existing_orders:
            merged.append(msg)
    
    # Sort by order
    merged.sort(key=lambda m: m.order)
    
    return merged


def create_incremental_digest(
    existing_digest: ThreadDigest,
    new_messages: List[Message],
    llm_model: Optional[str] = None,
    max_brief_words: int = 180,
) -> ThreadDigest:
    """
    Create an updated digest by appending new messages.
    
    Merges messages and regenerates summary with all content.
    """
    # Merge messages
    all_messages = merge_messages(existing_digest.messages, new_messages)
    
    # Regenerate summary with all messages
    signals = extract_signals(all_messages)
    summary = generate_summary(
        all_messages,
        signals=signals,
        llm_model=llm_model,
        max_brief_words=max_brief_words,
    )
    
    # Create updated digest
    return ThreadDigest(
        thread=existing_digest.thread,
        messages=all_messages,
        summary=summary,
    )


def append_to_digest_file(
    digest_path: Path,
    new_transcript: str,
    llm_model: Optional[str] = None,
    max_brief_words: int = 180,
) -> ThreadDigest:
    """
    Append new transcript content to an existing digest file.
    
    If digest doesn't exist, creates a new one.
    """
    # Load existing digest
    existing = load_existing_digest(digest_path)
    
    # Parse new messages
    new_messages = parse_transcript(new_transcript)
    
    if existing:
        # Incremental update
        digest = create_incremental_digest(
            existing,
            new_messages,
            llm_model=llm_model,
            max_brief_words=max_brief_words,
        )
    else:
        # Create new digest
        from .parser import infer_title
        
        signals = extract_signals(new_messages)
        summary = generate_summary(
            new_messages,
            signals=signals,
            llm_model=llm_model,
            max_brief_words=max_brief_words,
        )
        
        digest = ThreadDigest(
            thread=ThreadMetadata(
                id=str(digest_path.stem),
                title=infer_title(new_messages),
            ),
            messages=new_messages,
            summary=summary,
        )
    
    # Save updated digest
    digest_path.write_text(
        json.dumps(digest.model_dump(), indent=2),
        encoding="utf-8",
    )
    
    return digest


def get_new_messages_since(
    all_messages: List[Message],
    last_order: int,
) -> List[Message]:
    """
    Get messages that are newer than the specified order.
    
    Useful for extracting just the delta.
    """
    return [msg for msg in all_messages if msg.order > last_order]


def get_digest_stats(digest: ThreadDigest) -> dict:
    """
    Get statistics about a digest.
    
    Useful for tracking growth over incremental updates.
    """
    return {
        "total_messages": len(digest.messages),
        "first_message_order": digest.messages[0].order if digest.messages else 0,
        "last_message_order": digest.messages[-1].order if digest.messages else 0,
        "total_decisions": len(digest.summary.decisions),
        "total_actions": len(digest.summary.actions),
        "total_questions": len(digest.summary.open_questions),
        "has_code": digest.summary.code_summary is not None,
    }


def compare_digests(old: ThreadDigest, new: ThreadDigest) -> dict:
    """
    Compare two digests to see what changed.
    
    Returns a diff showing additions.
    """
    old_stats = get_digest_stats(old)
    new_stats = get_digest_stats(new)
    
    return {
        "messages_added": new_stats["total_messages"] - old_stats["total_messages"],
        "decisions_added": new_stats["total_decisions"] - old_stats["total_decisions"],
        "actions_added": new_stats["total_actions"] - old_stats["total_actions"],
        "questions_added": new_stats["total_questions"] - old_stats["total_questions"],
        "old_last_order": old_stats["last_message_order"],
        "new_last_order": new_stats["last_message_order"],
    }
