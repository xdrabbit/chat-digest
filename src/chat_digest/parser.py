"""Parsing utilities for chat transcripts in markdown."""

from __future__ import annotations

import re
from datetime import datetime
from typing import List, Sequence, Optional

from .schemas import Message, Role

SPEAKER_PATTERN = re.compile(r"^(#+\s*)?(you said:|chatgpt said:|user:|assistant:|system:|nyra said:|nyra:)\s*$", re.IGNORECASE)
DATE_PATTERN = re.compile(r"^(#+\s*)?((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}|Date:\s*[\d/-]+|[\d]{1,2}/[\d]{1,2}/[\d]{2,4}).*$", re.IGNORECASE)

ROLE_MAP = {
    "you said:": "user",
    "user:": "user",
    "chatgpt said:": "assistant",
    "assistant:": "assistant",
    "system:": "system",
    "nyra said:": "assistant",
    "nyra:": "assistant",
}

action_pattern = re.compile(r"^- \[ \]|\bTODO\b", re.IGNORECASE)
decision_pattern = re.compile(r"\b(decision|decide|choose|will|set|lock|select|order|decree)\b", re.IGNORECASE)
constraint_pattern = re.compile(r"\b(must|ensure|require|need to|deadline|mandatory)\b", re.IGNORECASE)


def parse_transcript(text: str, filename: Optional[str] = None) -> List[Message]:
    """Split markdown transcript into ordered Message objects."""
    lines = text.splitlines()
    messages: List[Message] = []
    buffer: List[str] = []
    current_role: Role = "unknown"
    order = 1
    started = False
    
    # Try to extract base date from filename (e.g., 01042026)
    current_timestamp = None
    if filename:
        date_match = re.search(r"(\d{2})(\d{2})(\d{4})", filename)
        if date_match:
            try:
                m, d, y = date_match.groups()
                current_timestamp = datetime(int(y), int(m), int(d))
            except ValueError:
                pass

    def flush() -> None:
        nonlocal order, buffer
        content = "\n".join(buffer).strip()
        if content:
            tags = _infer_tags(content)
            # Use current_timestamp if available
            ts_str = current_timestamp.isoformat() if current_timestamp else None
            messages.append(Message(order=order, role=current_role, content=content, tags=tags, timestamp=ts_str))
            order += 1
        buffer = []

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        
        # Check for date headers
        date_header = DATE_PATTERN.match(stripped)
        if date_header:
            try:
                # Basic date parsing - could be expanded
                new_date_str = date_header.group(2)
                # If it's MM/DD/YY, handle it
                if '/' in new_date_str:
                    parts = new_date_str.split('/')
                    if len(parts) == 3:
                        m, d, y = parts
                        if len(y) == 2: y = "20" + y
                        current_timestamp = datetime(int(y), int(m), int(d))
            except Exception:
                pass
            continue

        speaker = SPEAKER_PATTERN.match(stripped)
        if speaker:
            if started:
                flush()
            else:
                buffer = []
                started = True
            current_role = ROLE_MAP.get(speaker.group(2).lower(), "unknown")  # type: ignore[arg-type]
            continue
        
        if started:
            buffer.append(line)

    if started:
        flush()
    return messages


def infer_title(messages: Sequence[Message]) -> str:
    """Derive a short title from the first user message or fallback to first message."""
    if not messages:
        return "Untitled Thread"
    first_user = next((m for m in messages if m.role == "user" and m.content.strip()), None)
    candidate = first_user or messages[0]
    text = candidate.content.strip().split("\n", 1)[0]
    return (text[:60] + "…") if len(text) > 60 else text


def _infer_tags(content: str) -> List[str]:
    tags = []
    lowered = content.lower()
    if "```" in content:
        tags.append("code")
    if "?" in content:
        tags.append("question")
    if action_pattern.search(content):
        tags.append("action")
    if decision_pattern.search(content):
        tags.append("decision")
    if constraint_pattern.search(content):
        tags.append("constraint")
    return tags
