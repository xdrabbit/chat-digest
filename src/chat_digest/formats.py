"""Multi-format output generation for different use cases."""

from __future__ import annotations

from typing import List

from .schemas import ThreadDigest, Message


def generate_context_card(digest: ThreadDigest, max_words: int = 100) -> str:
    """
    Generate an ultra-compressed context card (<100 words).
    
    Perfect for quick handoffs or status updates.
    """
    summary = digest.summary
    
    lines = []
    
    # Title
    title = digest.thread.title or "Untitled"
    lines.append(f"**{title[:50]}**\n")
    
    # One-line summary (first sentence of brief)
    if summary.brief:
        first_sentence = summary.brief.split('.')[0] + '.'
        lines.append(f"{first_sentence}\n")
    
    # Quick stats
    stats = []
    if summary.decisions:
        stats.append(f"{len(summary.decisions)} decisions")
    if summary.actions:
        stats.append(f"{len(summary.actions)} actions")
    if summary.open_questions:
        stats.append(f"{len(summary.open_questions)} open questions")
    
    if stats:
        lines.append(f"*{', '.join(stats)}*\n")
    
    # Top decision or action
    if summary.decisions:
        lines.append(f"→ {summary.decisions[0]}")
    elif summary.actions:
        lines.append(f"→ TODO: {summary.actions[0]}")
    
    text = '\n'.join(lines)
    words = text.split()
    if len(words) > max_words:
        text = ' '.join(words[:max_words]) + '...'
    
    return text


def generate_detailed_brief(digest: ThreadDigest) -> str:
    """
    Generate a detailed brief with full context.
    
    More comprehensive than the standard brief, includes all signals.
    """
    summary = digest.summary
    messages = digest.messages
    
    sections = []
    
    # Header
    sections.append(f"# {digest.thread.title or 'Thread Digest'}\n")
    sections.append(f"**Source:** {digest.thread.source_file or 'Unknown'}")
    sections.append(f"**Messages:** {len(messages)}")
    sections.append(f"**Created:** {digest.thread.created_at}\n")
    
    # Executive summary
    sections.append("## Executive Summary\n")
    sections.append(summary.brief + "\n")
    
    # Decisions
    if summary.decisions:
        sections.append("## Key Decisions\n")
        for i, decision in enumerate(summary.decisions, 1):
            sections.append(f"{i}. {decision}")
        sections.append("")
    
    # Actions
    if summary.actions:
        sections.append("## Action Items\n")
        for action in summary.actions:
            sections.append(f"- [ ] {action}")
        sections.append("")
    
    # Questions
    if summary.open_questions:
        sections.append("## Open Questions\n")
        for question in summary.open_questions:
            sections.append(f"- {question}")
        sections.append("")
    
    # Constraints
    if summary.constraints:
        sections.append("## Constraints & Requirements\n")
        for constraint in summary.constraints:
            sections.append(f"- {constraint}")
        sections.append("")
    
    # Code summary
    if summary.code_summary and summary.code_summary.get("total_blocks", 0) > 0:
        code_sum = summary.code_summary
        sections.append("## Code Summary\n")
        sections.append(f"- **Total blocks:** {code_sum['total_blocks']}")
        
        if code_sum.get("languages"):
            langs = ", ".join(f"{lang} ({count})" for lang, count in code_sum["languages"].items())
            sections.append(f"- **Languages:** {langs}")
        
        if code_sum.get("unique_files", 0) > 0:
            sections.append(f"- **Files:** {code_sum['unique_files']}")
        sections.append("")
    
    return '\n'.join(sections)


def generate_slack_summary(digest: ThreadDigest) -> str:
    """
    Generate a Slack-friendly summary with emoji and formatting.
    """
    summary = digest.summary
    
    lines = []
    
    # Title with emoji
    lines.append(f"📋 *{digest.thread.title or 'Thread Summary'}*\n")
    
    # Brief
    if summary.brief:
        lines.append(summary.brief[:200] + ("..." if len(summary.brief) > 200 else ""))
        lines.append("")
    
    # Decisions
    if summary.decisions:
        lines.append("✅ *Decisions:*")
        for decision in summary.decisions[:3]:
            lines.append(f"  • {decision}")
        if len(summary.decisions) > 3:
            lines.append(f"  _...and {len(summary.decisions) - 3} more_")
        lines.append("")
    
    # Actions
    if summary.actions:
        lines.append("🎯 *Action Items:*")
        for action in summary.actions[:3]:
            lines.append(f"  • {action}")
        if len(summary.actions) > 3:
            lines.append(f"  _...and {len(summary.actions) - 3} more_")
        lines.append("")
    
    # Questions
    if summary.open_questions:
        lines.append("❓ *Open Questions:*")
        for question in summary.open_questions[:2]:
            lines.append(f"  • {question}")
        if len(summary.open_questions) > 2:
            lines.append(f"  _...and {len(summary.open_questions) - 2} more_")
    
    return '\n'.join(lines)


def generate_markdown_report(digest: ThreadDigest) -> str:
    """
    Generate a comprehensive markdown report.
    
    Suitable for documentation or archival purposes.
    """
    summary = digest.summary
    messages = digest.messages
    
    sections = []
    
    # Front matter
    sections.append("---")
    sections.append(f"title: {digest.thread.title or 'Untitled'}")
    sections.append(f"date: {digest.thread.created_at}")
    sections.append(f"messages: {len(messages)}")
    sections.append(f"schema_version: {digest.thread.schema_version}")
    sections.append("---\n")
    
    # Table of contents
    sections.append("## Table of Contents\n")
    sections.append("1. [Summary](#summary)")
    if summary.decisions:
        sections.append("2. [Decisions](#decisions)")
    if summary.actions:
        sections.append("3. [Actions](#actions)")
    if summary.open_questions:
        sections.append("4. [Questions](#questions)")
    if summary.code_summary:
        sections.append("5. [Code](#code)")
    sections.append("6. [Full Transcript](#transcript)\n")
    
    # Summary
    sections.append("## Summary\n")
    sections.append(summary.brief + "\n")
    
    # Decisions
    if summary.decisions:
        sections.append("## Decisions\n")
        for i, decision in enumerate(summary.decisions, 1):
            sections.append(f"{i}. {decision}")
        sections.append("")
    
    # Actions
    if summary.actions:
        sections.append("## Actions\n")
        for action in summary.actions:
            sections.append(f"- [ ] {action}")
        sections.append("")
    
    # Questions
    if summary.open_questions:
        sections.append("## Questions\n")
        for question in summary.open_questions:
            sections.append(f"- {question}")
        sections.append("")
    
    # Code
    if summary.code_summary and summary.code_summary.get("total_blocks", 0) > 0:
        sections.append("## Code\n")
        code_sum = summary.code_summary
        sections.append(f"Total code blocks: {code_sum['total_blocks']}\n")
        
        if code_sum.get("files"):
            sections.append("### Files Modified\n")
            for filename in code_sum["files"].keys():
                sections.append(f"- `{filename}`")
            sections.append("")
    
    # Transcript
    sections.append("## Transcript\n")
    for msg in messages:
        role_emoji = {"user": "👤", "assistant": "🤖", "system": "⚙️"}.get(msg.role, "❓")
        sections.append(f"### {role_emoji} {msg.role.title()} (#{msg.order})\n")
        sections.append(msg.content + "\n")
    
    return '\n'.join(sections)


def generate_all_formats(digest: ThreadDigest) -> dict[str, str]:
    """
    Generate all output formats at once.
    
    Returns:
        Dict mapping format name to content
    """
    return {
        "context_card": generate_context_card(digest),
        "detailed_brief": generate_detailed_brief(digest),
        "slack": generate_slack_summary(digest),
        "markdown_report": generate_markdown_report(digest),
    }
