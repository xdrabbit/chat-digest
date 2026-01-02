"""Parsing utilities for chat transcripts in markdown."""

from __future__ import annotations

import re
from typing import List, Sequence

from .schemas import Message, Role

SPEAKER_PATTERN = re.compile(r"^(#+\s*)?(you said:|chatgpt said:|user:|assistant:|system:)\s*$", re.IGNORECASE)
ROLE_MAP = {
    "you said:": "user",
    "user:": "user",
    "chatgpt said:": "assistant",
    "assistant:": "assistant",
    "system:": "system",
}

action_pattern = re.compile(r"^- \[ \]|\bTODO\b", re.IGNORECASE)
decision_pattern = re.compile(r"\b(decision|decide|choose|will|set|lock|select)\b", re.IGNORECASE)
constraint_pattern = re.compile(r"\b(must|ensure|require|need to)\b", re.IGNORECASE)


def parse_transcript(text: str) -> List[Message]:
    """Split markdown transcript into ordered Message objects."""
    lines = text.splitlines()
    messages: List[Message] = []
    buffer: List[str] = []
    current_role: Role = "unknown"
    order = 1
    started = False

    def flush() -> None:
        nonlocal order, buffer
        content = "\n".join(buffer).strip()
        if content:
            tags = _infer_tags(content)
            messages.append(Message(order=order, role=current_role, content=content, tags=tags))
            order += 1
        buffer = []

    for raw_line in lines:
        line = raw_line.rstrip()
        speaker = SPEAKER_PATTERN.match(line.strip())
        if speaker:
            if started:
                flush()
            else:
                buffer = []
                started = True
            current_role = ROLE_MAP.get(speaker.group(2).lower(), "unknown")  # type: ignore[arg-type]
            continue
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
