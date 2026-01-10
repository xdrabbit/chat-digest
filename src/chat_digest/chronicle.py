"""Chronicle timeline integration - export chat digests to Chronicle CSV format."""

from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .schemas import Message, ThreadDigest
from .llm import OllamaClient, OllamaConfig


def export_to_chronicle(
    digest: ThreadDigest,
    output_path: Path,
    timeline_name: str = "Legal",
    min_importance: float = 5.0,
    include_patterns: bool = False,
    llm_model: Optional[str] = None,
) -> int:
    """
    Export digest to Chronicle-compatible CSV format.
    """
    client = None
    if llm_model:
        client = OllamaClient(OllamaConfig(model=llm_model))

    events = _extract_chronicle_events(
        digest.messages,
        timeline_name=timeline_name,
        min_importance=min_importance,
        llm_client=client,
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
    llm_client: Optional[OllamaClient] = None,
) -> List[dict]:
    """Extract Chronicle events from messages."""
    events = []
    
    for msg in messages:
        if not _should_export_message(msg, min_importance):
            continue
        
        # Distill title
        title = _extract_title(msg)
        if llm_client and len(msg.content) > 100:
            try:
                # Ask LLM for a concise 3-5 word title
                prompt = (
                    f"Create a 3-5 word concise legal title for the following message. "
                    f"Return ONLY the title, no quotes or punctuation.\n\n"
                    f"Message: {msg.content[:500]}"
                )
                suggested_title = llm_client.generate(prompt).strip().strip('"').strip('**')
                if suggested_title and len(suggested_title) < 60:
                    title = suggested_title
            except Exception:
                pass

        event = {
            'title': title,
            'description': _clean_content(msg.content),
            'date': _format_date(msg.timestamp),
            'timeline': timeline_name,
            'actor': _extract_actor(msg),
            'emotion': _map_importance_to_emotion(msg),
            'tags': ','.join(msg.tags) if msg.tags else '',
            'evidence_links': '',
        }
        
        events.append(event)
    
    return events


def _should_export_message(msg: Message, min_importance: float) -> bool:
    """Determine if message should be exported to Chronicle."""
    if not hasattr(msg, 'importance_score'):
        return False
    
    if msg.importance_score < min_importance:
        return False
    
    relevant_tags = {'decision', 'action', 'question', 'constraint', 'code', 'important'}
    if not any(tag in relevant_tags for tag in msg.tags):
        # Also export very high importance messages regardless of tags
        if msg.importance_score < 7.5:
            return False
    
    return True


def _extract_title(msg: Message) -> str:
    """Extract a concise title from message content."""
    content = msg.content.strip()
    
    # Priority 1: First Markdown Header
    header_match = re.search(r'^#+\s+(.*)$', content, re.MULTILINE)
    if header_match:
        return _clean_text(header_match.group(1))

    # Priority 2: First Bold Line
    bold_match = re.search(r'\*\*([^*]+)\*\*', content)
    if bold_match:
        return _clean_text(bold_match.group(1))

    # Priority 3: First sentence
    sentences = re.split(r'[.!?]\s+', content)
    if sentences:
        title = _clean_text(sentences[0])
    else:
        lines = content.split('\n')
        title = _clean_text(lines[0]) if lines else content
    
    # Truncate to reasonable length
    max_length = 70
    if len(title) > max_length:
        title = title[:max_length-3] + '...'
    
    return title

def _clean_text(text: str) -> str:
    """Strip markdown and special chars for titles."""
    text = re.sub(r'[*_`#]', '', text)
    text = text.replace('Tom...', '').replace('Nyra...', '').strip()
    return text

def _clean_content(content: str) -> str:
    """Clean content for CSV description."""
    # Strip some massive blobs if helpful, but usually we want context
    # Just fix mojibake-prone chars if needed, but utf-8-sig should handle it.
    return content.strip()


def _format_date(timestamp: Optional[str | datetime]) -> str:
    """Format timestamp for Chronicle (YYYY-MM-DD HH:MM:SS)."""
    if timestamp is None:
        dt = datetime.now()
    elif isinstance(timestamp, str):
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            dt = datetime.now()
    else:
        dt = timestamp
    
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def _extract_actor(msg: Message) -> str:
    """Extract actor from message role and content."""
    role_map = {'user': 'Tom', 'assistant': 'Nyra', 'system': 'System'}
    actor = role_map.get(msg.role, 'Unknown')
    
    content_lower = msg.content.lower()
    
    # Smart detection for legal actors
    actors_map = {
        'lisa': 'Lisa',
        'blaine': 'Attorney (Blaine)',
        'brody': 'Attorney (Brody)',
        'jeff': 'Realtor (Jeff)',
        'commissioner': 'Commissioner',
        'judge': 'Judge',
        'farm bureau': 'Insurance'
    }
    
    for key, val in actors_map.items():
        if key in content_lower:
            # If the user is talking ABOUT them, don't necessarily switch actor, 
            # but if it's the dominant subject, maybe.
            # For now, let's keep it simple.
            pass

    return actor


def _map_importance_to_emotion(msg: Message) -> str:
    score = getattr(msg, 'importance_score', 5.0)
    if score >= 9.0: return 'critical'
    if score >= 8.0: return 'urgent'
    if score >= 7.0: return 'important'
    
    if 'decision' in msg.tags: return 'decisive'
    if 'action' in msg.tags: return 'focused'
    if 'question' in msg.tags: return 'curious'
    if 'constraint' in msg.tags: return 'concerned'
    if 'code' in msg.tags: return 'technical'
    return 'neutral'


def _write_chronicle_csv(events: List[dict], output_path: Path) -> None:
    """Write events to Chronicle CSV format with UTF-8-SIG for Excel/Chronicle compatibility."""
    fieldnames = ['title', 'description', 'date', 'timeline', 'actor', 'emotion', 'tags', 'evidence_links']
    
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(events)


def _patterns_to_chronicle_events(patterns: List, timeline_name: str) -> List[dict]:
    from .patterns import Pattern
    events = []
    
    for pattern in patterns:
        if pattern.last_occurrence:
            date = pattern.last_occurrence.strftime('%Y-%m-%d %H:%M:%S')
        else:
            date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        title_map = {
            'promise_break_cycle': 'Pattern: Promise-Break Cycle',
            'escalation': 'Pattern: Escalation Detected',
            'recurring_topic': 'Pattern: Recurring Topic',
            'timing_pattern': 'Pattern: Timing Anomaly',
        }
        
        title = title_map.get(pattern.pattern_type, f'Pattern: {pattern.pattern_type}')
        if pattern.pattern_type == 'recurring_topic' and pattern.evidence:
            title = f"Pattern: Recurring Topic '{pattern.evidence[0]}'"
        
        events.append({
            'title': title,
            'description': pattern.description,
            'date': date,
            'timeline': timeline_name,
            'actor': 'System',
            'emotion': 'analytical',
            'tags': f'pattern,{pattern.pattern_type},automated',
            'evidence_links': '',
        })
    
    return events
