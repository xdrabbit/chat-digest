"""Pattern detection for Chronicle integration - identify recurring behaviors and trends."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Optional

from .schemas import Message
from .temporal import detect_supersessions, extract_timeline


class Pattern:
    """Represents a detected pattern in conversation."""
    
    def __init__(
        self,
        pattern_type: str,
        description: str,
        frequency: int,
        confidence: float,
        first_occurrence: Optional[datetime] = None,
        last_occurrence: Optional[datetime] = None,
        evidence: Optional[List[str]] = None,
    ):
        self.pattern_type = pattern_type
        self.description = description
        self.frequency = frequency
        self.confidence = confidence
        self.first_occurrence = first_occurrence
        self.last_occurrence = last_occurrence
        self.evidence = evidence or []
    
    def to_dict(self) -> dict:
        """Convert pattern to dictionary."""
        return {
            'pattern_type': self.pattern_type,
            'description': self.description,
            'frequency': self.frequency,
            'confidence': self.confidence,
            'first_occurrence': self.first_occurrence.isoformat() if self.first_occurrence else None,
            'last_occurrence': self.last_occurrence.isoformat() if self.last_occurrence else None,
            'evidence_count': len(self.evidence),
        }


def detect_promise_break_cycles(messages: List[Message]) -> Optional[Pattern]:
    """
    Detect promise-break cycles using supersession detection.
    
    A promise-break cycle is when decisions/promises are repeatedly made and then
    contradicted or violated.
    """
    # First extract timeline events
    timeline_events = extract_timeline(messages)
    
    # Then detect supersessions
    supersessions = detect_supersessions(timeline_events, messages)
    
    # Filter to only superseded events
    superseded = [e for e in supersessions if e.superseded_by is not None]
    
    if len(superseded) < 3:  # Need at least 3 to establish a pattern
        return None
    
    # Calculate average time between supersessions
    timestamps = []
    for sup in superseded:
        if sup.timestamp:
            try:
                dt = datetime.fromisoformat(sup.timestamp.replace('Z', '+00:00'))
                timestamps.append(dt)
            except (ValueError, AttributeError):
                continue
    
    if len(timestamps) < 3:
        return None
    
    # Calculate average days between violations
    time_diffs = []
    for i in range(1, len(timestamps)):
        diff = (timestamps[i] - timestamps[i-1]).days
        if diff > 0:  # Only count positive differences
            time_diffs.append(diff)
    
    if not time_diffs:
        return None
    
    avg_days = sum(time_diffs) / len(time_diffs)
    
    # Build evidence list
    evidence = [f"{sup.original_content[:100]}..." for sup in supersessions[:5]]
    
    # Calculate confidence based on consistency
    # More consistent timing = higher confidence
    if len(time_diffs) > 1:
        variance = sum((d - avg_days) ** 2 for d in time_diffs) / len(time_diffs)
        std_dev = variance ** 0.5
        # Lower std_dev = more consistent = higher confidence
        confidence = min(0.98, max(0.70, 1.0 - (std_dev / avg_days)))
    else:
        confidence = 0.75
    
    description = (
        f"Promise-break cycle detected: {len(superseded)} instances over "
        f"{(timestamps[-1] - timestamps[0]).days} days. "
        f"Average {avg_days:.1f} days between violations. "
        f"{int(confidence * 100)}% confidence."
    )
    
    return Pattern(
        pattern_type="promise_break_cycle",
        description=description,
        frequency=len(superseded),
        confidence=confidence,
        first_occurrence=timestamps[0] if timestamps else None,
        last_occurrence=timestamps[-1] if timestamps else None,
        evidence=evidence,
    )


def detect_escalation_pattern(messages: List[Message]) -> Optional[Pattern]:
    """
    Detect escalation patterns based on increasing importance scores over time.
    """
    # Get messages with importance scores
    scored_messages = [
        msg for msg in messages 
        if hasattr(msg, 'importance_score') and msg.importance_score > 0
    ]
    
    if len(scored_messages) < 5:  # Need enough data
        return None
    
    # Split into time windows and calculate average importance
    window_size = max(1, len(scored_messages) // 4)  # 4 windows
    windows = []
    
    for i in range(0, len(scored_messages), window_size):
        window = scored_messages[i:i+window_size]
        if window:
            avg_score = sum(msg.importance_score for msg in window) / len(window)
            windows.append(avg_score)
    
    if len(windows) < 3:
        return None
    
    # Check for increasing trend
    increases = sum(1 for i in range(1, len(windows)) if windows[i] > windows[i-1])
    trend_strength = increases / (len(windows) - 1)
    
    if trend_strength < 0.6:  # At least 60% increasing
        return None
    
    # Calculate percentage increase
    pct_increase = ((windows[-1] - windows[0]) / windows[0]) * 100 if windows[0] > 0 else 0
    
    if pct_increase < 10:  # At least 10% increase
        return None
    
    description = (
        f"Escalation pattern detected: Importance scores increasing by "
        f"{pct_increase:.1f}% over conversation. "
        f"Trend strength: {int(trend_strength * 100)}%."
    )
    
    return Pattern(
        pattern_type="escalation",
        description=description,
        frequency=len(windows),
        confidence=trend_strength,
        first_occurrence=None,  # Could extract from message timestamps
        last_occurrence=None,
        evidence=[],
    )


def detect_recurring_topics(messages: List[Message]) -> List[Pattern]:
    """
    Detect recurring topics that appear frequently throughout conversation.
    """
    # Count tag frequencies
    tag_counts = Counter()
    tag_messages = defaultdict(list)
    
    for msg in messages:
        for tag in msg.tags:
            tag_counts[tag] += 1
            tag_messages[tag].append(msg.order)
    
    patterns = []
    
    # Find tags that appear frequently (at least 5 times)
    for tag, count in tag_counts.items():
        if count >= 5:
            # Check if distributed across conversation (not clustered)
            message_orders = tag_messages[tag]
            span = max(message_orders) - min(message_orders)
            total_messages = len(messages)
            
            # If tag appears across > 50% of conversation span, it's recurring
            if span > (total_messages * 0.5):
                confidence = min(0.95, 0.70 + (count / total_messages))
                
                description = (
                    f"Recurring topic: '{tag}' appears {count} times "
                    f"throughout conversation. "
                    f"Spans {span} messages."
                )
                
                patterns.append(Pattern(
                    pattern_type="recurring_topic",
                    description=description,
                    frequency=count,
                    confidence=confidence,
                    evidence=[tag],
                ))
    
    return patterns


def detect_timing_patterns(messages: List[Message]) -> Optional[Pattern]:
    """
    Detect timing patterns (e.g., violations cluster on specific days of week).
    
    Note: Requires messages to have timestamp information.
    """
    # Extract timestamps from messages with 'decision' or 'constraint' tags
    timestamps = []
    
    for msg in messages:
        if not msg.timestamp:
            continue
        
        if 'decision' in msg.tags or 'constraint' in msg.tags:
            try:
                dt = datetime.fromisoformat(msg.timestamp.replace('Z', '+00:00'))
                timestamps.append(dt)
            except (ValueError, AttributeError):
                continue
    
    if len(timestamps) < 5:  # Need enough data
        return None
    
    # Count by day of week (0=Monday, 6=Sunday)
    day_counts = Counter(dt.weekday() for dt in timestamps)
    
    # Find most common day
    if not day_counts:
        return None
    
    most_common_day, count = day_counts.most_common(1)[0]
    total = len(timestamps)
    percentage = (count / total) * 100
    
    # Only report if > 50% cluster on one day
    if percentage < 50:
        return None
    
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_name = day_names[most_common_day]
    
    confidence = min(0.95, percentage / 100)
    
    description = (
        f"Timing pattern detected: {percentage:.0f}% of events occur on {day_name}. "
        f"Statistical significance suggests intentional timing."
    )
    
    return Pattern(
        pattern_type="timing_pattern",
        description=description,
        frequency=count,
        confidence=confidence,
        evidence=[day_name],
    )


def detect_all_patterns(messages: List[Message]) -> List[Pattern]:
    """
    Detect all patterns in messages.
    
    Returns list of detected patterns sorted by confidence.
    """
    patterns = []
    
    # Promise-break cycles
    promise_pattern = detect_promise_break_cycles(messages)
    if promise_pattern:
        patterns.append(promise_pattern)
    
    # Escalation
    escalation_pattern = detect_escalation_pattern(messages)
    if escalation_pattern:
        patterns.append(escalation_pattern)
    
    # Recurring topics
    topic_patterns = detect_recurring_topics(messages)
    patterns.extend(topic_patterns)
    
    # Timing patterns
    timing_pattern = detect_timing_patterns(messages)
    if timing_pattern:
        patterns.append(timing_pattern)
    
    # Sort by confidence (highest first)
    patterns.sort(key=lambda p: p.confidence, reverse=True)
    
    return patterns


def get_pattern_summary(patterns: List[Pattern]) -> dict:
    """Get summary statistics for detected patterns."""
    if not patterns:
        return {
            'total_patterns': 0,
            'by_type': {},
            'highest_confidence': 0.0,
            'average_confidence': 0.0,
        }
    
    by_type = Counter(p.pattern_type for p in patterns)
    confidences = [p.confidence for p in patterns]
    
    return {
        'total_patterns': len(patterns),
        'by_type': dict(by_type),
        'highest_confidence': max(confidences),
        'average_confidence': sum(confidences) / len(confidences),
        'patterns': [p.to_dict() for p in patterns],
    }
