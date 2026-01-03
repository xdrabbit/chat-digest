"""Chronicle timeline integration - export chat digests to Chronicle CSV format."""

from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .schemas import Message, ThreadDigest


def export_to_chronicle(
    digest: ThreadDigest,
    output_path: Path,
    timeline_name: str = "Legal",
    min_importance: float = 5.0,
    include_patterns: bool = False,
) -> int:
    """
    Export digest to Chronicle-compatible CSV format.
    
    Args:
        digest: The thread digest to export
        output_path: Path to write CSV file
        timeline_name: Chronicle timeline category (default: "Legal")
        min_importance: Minimum importance score to include (default: 5.0)
        include_patterns: Whether to include detected patterns as events (default: False)
    
    Returns:
        Number of events exported
    """
    events = _extract_chronicle_events(
        digest.messages,
        timeline_name=timeline_name,
        min_importance=min_importance,
    )
    
    # Add pattern events if requested
    if include_patterns:
        from .patterns import detect_all_patterns
        
        patterns = detect_all_patterns(digest.messages)
        pattern_events = _patterns_to_chronicle_events(patterns, timeline_name)
        events.extend(pattern_events)
    
    _write_chronicle_csv(events, output_path)
    
    return len(events)


def _extract_chronicle_events(
    messages: List[Message],
    timeline_name: str,
    min_importance: float,
) -> List[dict]:
    """Extract Chronicle events from messages."""
    events = []
    
    for msg in messages:
        # Only export important messages with specific tags
        if not _should_export_message(msg, min_importance):
            continue
        
        event = {
            'title': _extract_title(msg),
            'description': _truncate_description(msg.content),
            'date': _format_date(msg.timestamp),
            'timeline': timeline_name,
            'actor': _extract_actor(msg),
            'emotion': _map_importance_to_emotion(msg),
            'tags': ','.join(msg.tags) if msg.tags else '',
            'evidence_links': '',  # Future: extract from content
        }
        
        events.append(event)
    
    return events


def _should_export_message(msg: Message, min_importance: float) -> bool:
    """Determine if message should be exported to Chronicle."""
    # Must have importance score
    if not hasattr(msg, 'importance_score'):
        return False
    
    # Must meet minimum importance threshold
    if msg.importance_score < min_importance:
        return False
    
    # Must have relevant tags
    relevant_tags = {'decision', 'action', 'question', 'constraint', 'code'}
    if not any(tag in relevant_tags for tag in msg.tags):
        return False
    
    return True


def _extract_title(msg: Message) -> str:
    """Extract a concise title from message content."""
    # Try to get first sentence
    content = msg.content.strip()
    
    # Remove markdown formatting
    content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)  # Bold
    content = re.sub(r'\*([^*]+)\*', r'\1', content)      # Italic
    content = re.sub(r'`([^`]+)`', r'\1', content)        # Code
    
    # Get first sentence or line
    sentences = re.split(r'[.!?]\s+', content)
    if sentences:
        title = sentences[0].strip()
    else:
        lines = content.split('\n')
        title = lines[0].strip() if lines else content
    
    # Truncate to reasonable length
    max_length = 80
    if len(title) > max_length:
        title = title[:max_length-3] + '...'
    
    return title


def _truncate_description(content: str, max_length: int = 500) -> str:
    """Truncate description to reasonable length."""
    if len(content) <= max_length:
        return content
    
    return content[:max_length-3] + '...'


def _format_date(timestamp: Optional[str | datetime]) -> str:
    """Format timestamp for Chronicle (YYYY-MM-DD HH:MM:SS)."""
    if timestamp is None:
        dt = datetime.now()
    elif isinstance(timestamp, str):
        # Parse ISO format string
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    else:
        dt = timestamp
    
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def _extract_actor(msg: Message) -> str:
    """Extract actor from message role and content."""
    # Map roles to actors
    role_map = {
        'user': 'User',
        'assistant': 'Assistant',
        'system': 'System',
    }
    
    actor = role_map.get(msg.role, 'Unknown')
    
    # Try to extract specific person from content
    # Look for patterns like "Tom said", "@username", etc.
    content_lower = msg.content.lower()
    
    # Check for @mentions
    mention_match = re.search(r'@([a-zA-Z0-9_-]+)', msg.content)
    if mention_match:
        return mention_match.group(1).title()
    
    # Check for common legal actors
    legal_actors = [
        'opposing counsel', 'court', 'judge', 'attorney', 
        'realtor', 'mediator', 'expert witness'
    ]
    
    for legal_actor in legal_actors:
        if legal_actor in content_lower:
            return legal_actor.title()
    
    return actor


def _map_importance_to_emotion(msg: Message) -> str:
    """Map importance score and tags to Chronicle emotion."""
    score = getattr(msg, 'importance_score', 5.0)
    
    # High importance = critical/urgent
    if score >= 9.0:
        return 'critical'
    elif score >= 8.0:
        return 'urgent'
    elif score >= 7.0:
        return 'important'
    
    # Map based on tags
    if 'decision' in msg.tags:
        return 'decisive'
    elif 'action' in msg.tags:
        return 'focused'
    elif 'question' in msg.tags:
        return 'curious'
    elif 'constraint' in msg.tags:
        return 'concerned'
    elif 'code' in msg.tags:
        return 'technical'
    
    return 'neutral'


def _write_chronicle_csv(events: List[dict], output_path: Path) -> None:
    """Write events to Chronicle CSV format."""
    fieldnames = [
        'title',
        'description',
        'date',
        'timeline',
        'actor',
        'emotion',
        'tags',
        'evidence_links',
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(events)


def _patterns_to_chronicle_events(patterns: List, timeline_name: str) -> List[dict]:
    """Convert detected patterns to Chronicle events."""
    from .patterns import Pattern
    
    events = []
    
    for pattern in patterns:
        # Use last occurrence if available, otherwise current time
        if pattern.last_occurrence:
            date = pattern.last_occurrence.strftime('%Y-%m-%d %H:%M:%S')
        else:
            date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Map pattern type to title
        title_map = {
            'promise_break_cycle': 'Pattern: Promise-Break Cycle',
            'escalation': 'Pattern: Escalation Detected',
            'recurring_topic': f'Pattern: Recurring Topic',
            'timing_pattern': 'Pattern: Timing Anomaly',
        }
        
        title = title_map.get(pattern.pattern_type, f'Pattern: {pattern.pattern_type}')
        
        # Add frequency to title for recurring topics
        if pattern.pattern_type == 'recurring_topic' and pattern.evidence:
            title = f"Pattern: Recurring Topic '{pattern.evidence[0]}'"
        
        event = {
            'title': title,
            'description': pattern.description,
            'date': date,
            'timeline': timeline_name,
            'actor': 'System',
            'emotion': 'analytical',
            'tags': f'pattern,{pattern.pattern_type},automated',
            'evidence_links': '',  # Could link to evidence file
        }
        
        events.append(event)
    
    return events
