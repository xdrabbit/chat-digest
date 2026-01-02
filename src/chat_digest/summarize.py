"""Summarization utilities (rule-based with optional Ollama refinement)."""

from __future__ import annotations

import textwrap
from typing import Dict, List, Optional

import requests

from .code_extraction import get_code_summary
from .llm import OllamaClient, OllamaConfig
from .schemas import Message, Summary


def extract_signals(messages: List[Message]) -> Dict[str, List[str]]:
    decisions: List[str] = []
    actions: List[str] = []
    open_questions: List[str] = []
    constraints: List[str] = []

    for msg in messages:
        for line in _lines(msg.content):
            lowered = line.lower()
            if line.endswith("?"):
                open_questions.append(line)
            if "- [" in line or "todo" in lowered:
                actions.append(line)
            if any(token in lowered for token in ["decide", "decision", "will", "choose", "set"]):
                decisions.append(line)
            if any(token in lowered for token in ["must", "ensure", "require", "need to"]):
                constraints.append(line)

    return {
        "decisions": _dedupe(decisions),
        "actions": _dedupe(actions),
        "open_questions": _dedupe(open_questions),
        "constraints": _dedupe(constraints),
    }


def generate_summary(
    messages: List[Message],
    *,
    signals: Optional[Dict[str, List[str]]] = None,
    llm_model: Optional[str] = None,
    max_brief_words: int = 180,
) -> Summary:
    signals = signals or extract_signals(messages)
    brief = build_rule_based_brief(messages, signals, max_brief_words=max_brief_words)

    if llm_model:
        client = OllamaClient(OllamaConfig(model=llm_model))
        maybe_brief = _try_llm_brief(client, messages, signals, max_brief_words)
        if maybe_brief:
            brief = maybe_brief

    # Extract code summary
    code_summary = get_code_summary(messages)

    return Summary(
        brief=brief,
        decisions=signals.get("decisions", []),
        actions=signals.get("actions", []),
        open_questions=signals.get("open_questions", []),
        constraints=signals.get("constraints", []),
        code_summary=code_summary if code_summary["total_blocks"] > 0 else None,
    )


def build_rule_based_brief(messages: List[Message], signals: Dict[str, List[str]], *, max_brief_words: int) -> str:
    context_line = _first_nonempty_line(messages)
    lines = [f"Context: {context_line}"] if context_line else []

    if signals.get("decisions"):
        lines.append("Decisions: " + "; ".join(signals["decisions"]))
    if signals.get("actions"):
        lines.append("Actions: " + "; ".join(signals["actions"]))
    if signals.get("open_questions"):
        lines.append("Open questions: " + "; ".join(signals["open_questions"]))
    if signals.get("constraints"):
        lines.append("Constraints: " + "; ".join(signals["constraints"]))

    if not lines:
        lines.append("Brief: Transcript contained no extractable signals; review raw messages.")

    text = "\n".join(lines)
    return _truncate_words(text, max_brief_words)


def _try_llm_brief(
    client: OllamaClient,
    messages: List[Message],
    signals: Dict[str, List[str]],
    max_brief_words: int,
) -> Optional[str]:
    context = _clip("\n\n".join(m.content for m in messages), max_chars=4000)
    prompt = textwrap.dedent(
        f"""
        You are creating a concise handoff brief for a new assistant. Keep it under {max_brief_words} words.
        Use short bullet-style sentences. Include: brief context, key decisions, action items, open questions, constraints.

        Extracted signals (may be incomplete):
        Decisions: {signals.get('decisions', [])}
        Actions: {signals.get('actions', [])}
        Open questions: {signals.get('open_questions', [])}
        Constraints: {signals.get('constraints', [])}

        Transcript:
        {context}

        Provide only the brief text.
        """
    ).strip()

    try:
        return client.generate(prompt)
    except requests.RequestException:
        return None


def _first_nonempty_line(messages: List[Message]) -> str:
    for msg in messages:
        for line in _lines(msg.content):
            if line:
                return line
    return ""


def _lines(text: str) -> List[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    deduped = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _truncate_words(text: str, limit: int) -> str:
    words = text.split()
    if len(words) <= limit:
        return text
    return " ".join(words[:limit]) + " …"


def _clip(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + " …"
