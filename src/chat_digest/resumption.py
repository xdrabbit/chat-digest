"""Generate resumption prompts for continuing conversations."""

from __future__ import annotations

from typing import List

from .schemas import Message, Summary, ThreadDigest


def generate_resumption_prompt(digest: ThreadDigest) -> str:
    """
    Generate a ready-to-paste prompt for resuming work in a new chat session.
    
    This creates a structured context handoff that includes:
    - Brief summary of what was discussed
    - Key decisions made
    - Current state and files modified
    - Pending actions
    - Open questions blocking progress
    - Suggested next steps
    """
    summary = digest.summary
    messages = digest.messages
    
    sections = []
    
    # Header
    sections.append("# Context from Previous Session")
    sections.append("")
    
    # Brief overview
    if summary.brief:
        sections.append("## Summary")
        sections.append(summary.brief)
        sections.append("")
    
    # Key decisions
    if summary.decisions:
        sections.append("## Key Decisions Made")
        for decision in summary.decisions[:5]:  # Top 5 most important
            sections.append(f"- {decision}")
        sections.append("")
    
    # Current state - extract file mentions and code
    files_mentioned = _extract_file_mentions(messages)
    
    if files_mentioned or (summary.code_summary and summary.code_summary.get("total_blocks", 0) > 0):
        sections.append("## Current State")
        
        if files_mentioned:
            sections.append("**Files discussed/modified:**")
            for file in files_mentioned[:10]:  # Top 10 files
                sections.append(f"- `{file}`")
            sections.append("")
        
        # Enhanced code block display
        if summary.code_summary:
            code_sum = summary.code_summary
            total = code_sum.get("total_blocks", 0)
            unique_files = code_sum.get("unique_files", 0)
            languages = code_sum.get("languages", {})
            
            if total > 0:
                lang_str = ", ".join(f"{lang} ({count})" for lang, count in languages.items())
                sections.append(f"**Code blocks:** {total} snippet(s) in conversation")
                if lang_str:
                    sections.append(f"  - Languages: {lang_str}")
                if unique_files > 0:
                    sections.append(f"  - Associated with {unique_files} file(s)")
                sections.append("")
    
    # Pending actions
    if summary.actions:
        sections.append("## Pending Actions")
        for action in summary.actions[:8]:  # Top 8 actions
            sections.append(f"- [ ] {action}")
        sections.append("")
    
    # Blockers / Open questions
    if summary.open_questions:
        sections.append("## Open Questions / Blockers")
        for question in summary.open_questions[:5]:
            sections.append(f"- {question}")
        sections.append("")
    
    # Constraints to remember
    if summary.constraints:
        sections.append("## Constraints & Requirements")
        for constraint in summary.constraints[:5]:
            sections.append(f"- {constraint}")
        sections.append("")
    
    # Next steps suggestion
    sections.append("## Suggested Next Steps")
    next_steps = _suggest_next_steps(summary)
    for step in next_steps:
        sections.append(f"{step}")
    sections.append("")
    
    # Footer
    sections.append("---")
    sections.append(f"*Generated from {digest.thread.source_file or 'chat transcript'}*")
    sections.append(f"*Original thread: {digest.thread.title or 'Untitled'}*")
    
    return "\n".join(sections)


def _extract_file_mentions(messages: List[Message]) -> List[str]:
    """Extract file paths and names mentioned in the conversation."""
    import re
    
    file_pattern = re.compile(
        r'(?:'
        r'`([a-zA-Z0-9_/\-\.]+\.[a-zA-Z0-9]+)`|'  # Backtick-wrapped files
        r'(?:^|\s)([a-zA-Z0-9_/\-]+/[a-zA-Z0-9_/\-\.]+\.[a-zA-Z0-9]+)|'  # Path-like
        r'(?:file|module|script|class):\s*([a-zA-Z0-9_/\-\.]+)|'  # Explicit mentions
        r'\b([a-zA-Z0-9_\-]+\.(py|js|ts|json|yaml|yml|toml|md|txt|sh|go|rs|java|cpp|c|h))\b'  # Common file extensions
        r')'
    )
    
    files = set()
    for msg in messages:
        matches = file_pattern.findall(msg.content)
        for match in matches:
            # match is a tuple of groups, get the non-empty one
            file = next((m for m in match if m), None)
            if file and len(file) > 2:  # Avoid false positives like "a.b"
                files.add(file)
    
    return sorted(files)


def _extract_code_snippets(messages: List[Message]) -> List[str]:
    """Extract code blocks from messages."""
    snippets = []
    for msg in messages:
        if "code" in msg.tags:
            # Extract actual code blocks
            import re
            code_blocks = re.findall(r'```[\w]*\n(.*?)```', msg.content, re.DOTALL)
            snippets.extend(code_blocks)
    
    return snippets


def _suggest_next_steps(summary: Summary) -> List[str]:
    """Generate intelligent next step suggestions based on the summary."""
    steps = []
    
    # If there are open questions, suggest answering them first
    if summary.open_questions:
        steps.append("1. **Resolve open questions** listed above to unblock progress")
    
    # If there are pending actions, suggest tackling them
    if summary.actions:
        steps.append(f"2. **Complete pending actions** ({len(summary.actions)} item(s) remaining)")
    
    # If there are decisions but no actions, suggest implementation
    if summary.decisions and not summary.actions:
        steps.append("3. **Implement the decisions** made in the previous session")
    
    # Generic continuation
    if not steps:
        steps.append("1. Review the summary above and continue where you left off")
    
    return steps
