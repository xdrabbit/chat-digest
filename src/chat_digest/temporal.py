"""Temporal analysis and chronological tracking for conversations."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from .schemas import Message


class TimelineEvent:
    """Represents a significant event in the conversation timeline."""
    
    def __init__(
        self,
        message_order: int,
        event_type: str,  # decision, action, question, code, etc.
        content: str,
        timestamp: Optional[str] = None,
        superseded_by: Optional[int] = None,  # Message order that supersedes this
    ):
        self.message_order = message_order
        self.event_type = event_type
        self.content = content
        self.timestamp = timestamp
        self.superseded_by = superseded_by
        self.is_current = superseded_by is None
    
    def __repr__(self) -> str:
        status = "CURRENT" if self.is_current else f"SUPERSEDED@{self.superseded_by}"
        return f"<TimelineEvent #{self.message_order} {self.event_type} [{status}]>"
    
    def to_dict(self) -> dict:
        return {
            "message_order": self.message_order,
            "event_type": self.event_type,
            "content": self.content,
            "timestamp": self.timestamp,
            "superseded_by": self.superseded_by,
            "is_current": self.is_current,
        }


def extract_timeline(messages: List[Message]) -> List[TimelineEvent]:
    """
    Extract significant events from messages and build a timeline.
    
    Returns events in chronological order with supersession tracking.
    """
    events = []
    
    for msg in messages:
        # Extract decisions
        if "decision" in msg.tags:
            events.append(TimelineEvent(
                message_order=msg.order,
                event_type="decision",
                content=msg.content[:200],  # Truncate for brevity
                timestamp=msg.timestamp,
            ))
        
        # Extract actions
        if "action" in msg.tags:
            events.append(TimelineEvent(
                message_order=msg.order,
                event_type="action",
                content=msg.content[:200],
                timestamp=msg.timestamp,
            ))
        
        # Extract questions
        if "question" in msg.tags:
            events.append(TimelineEvent(
                message_order=msg.order,
                event_type="question",
                content=msg.content[:200],
                timestamp=msg.timestamp,
            ))
        
        # Extract code additions
        if "code" in msg.tags:
            events.append(TimelineEvent(
                message_order=msg.order,
                event_type="code",
                content=f"Code block added",
                timestamp=msg.timestamp,
            ))
    
    return events


def detect_supersessions(events: List[TimelineEvent], messages: List[Message]) -> List[TimelineEvent]:
    """
    Detect when decisions or actions are superseded by later ones.
    
    Uses heuristics to identify contradictions or updates.
    """
    # Group events by type
    decisions = [e for e in events if e.event_type == "decision"]
    
    # Look for contradictory decisions
    supersession_keywords = [
        "actually", "instead", "changed my mind", "let's use", "switch to",
        "no wait", "correction", "update:", "revised", "new plan"
    ]
    
    for i, event in enumerate(decisions):
        # Check if any later decision contradicts this one
        for later_event in decisions[i+1:]:
            later_msg = next((m for m in messages if m.order == later_event.message_order), None)
            if later_msg:
                content_lower = later_msg.content.lower()
                # If later message contains supersession keywords, mark earlier as superseded
                if any(keyword in content_lower for keyword in supersession_keywords):
                    event.superseded_by = later_event.message_order
                    event.is_current = False
                    break
    
    return events


def get_current_state(events: List[TimelineEvent]) -> dict:
    """
    Get the current state by filtering to only non-superseded events.
    
    Returns:
        Dict with current decisions, actions, questions, etc.
    """
    current = [e for e in events if e.is_current]
    
    return {
        "decisions": [e for e in current if e.event_type == "decision"],
        "actions": [e for e in current if e.event_type == "action"],
        "questions": [e for e in current if e.event_type == "question"],
        "code_events": [e for e in current if e.event_type == "code"],
    }


def get_historical_changes(events: List[TimelineEvent]) -> List[TimelineEvent]:
    """
    Get events that were superseded (historical changes).
    
    Useful for understanding how the conversation evolved.
    """
    return [e for e in events if not e.is_current]


def generate_timeline_summary(events: List[TimelineEvent]) -> str:
    """
    Generate a human-readable timeline summary.
    
    Shows chronological progression with current vs. superseded markers.
    """
    if not events:
        return "No significant events in timeline."
    
    lines = ["# Conversation Timeline\n"]
    
    # Group by event type
    by_type = {}
    for event in events:
        if event.event_type not in by_type:
            by_type[event.event_type] = []
        by_type[event.event_type].append(event)
    
    # Show decisions with supersession tracking
    if "decision" in by_type:
        lines.append("## Decisions\n")
        for event in by_type["decision"]:
            status = "✓ CURRENT" if event.is_current else f"⨯ Superseded by #{event.superseded_by}"
            lines.append(f"- **#{event.message_order}** {status}")
            lines.append(f"  {event.content[:100]}...")
        lines.append("")
    
    # Show actions
    if "action" in by_type:
        lines.append("## Actions\n")
        for event in by_type["action"]:
            status = "[ ]" if event.is_current else "[x]"
            lines.append(f"- {status} **#{event.message_order}** {event.content[:100]}...")
        lines.append("")
    
    # Show questions
    if "question" in by_type:
        lines.append("## Questions\n")
        current_questions = [e for e in by_type["question"] if e.is_current]
        if current_questions:
            lines.append("**Still open:**")
            for event in current_questions:
                lines.append(f"- **#{event.message_order}** {event.content[:100]}...")
        lines.append("")
    
    # Show code timeline
    if "code" in by_type:
        lines.append(f"## Code Activity\n")
        lines.append(f"Total code blocks added: {len(by_type['code'])}")
        lines.append("")
    
    return "\n".join(lines)


def get_conversation_phases(messages: List[Message]) -> List[dict]:
    """
    Identify distinct phases in the conversation.
    
    Phases might be: planning, implementation, debugging, etc.
    """
    phases = []
    current_phase = None
    phase_start = 0
    
    for i, msg in enumerate(messages):
        # Detect phase transitions based on tags and content
        tags_set = set(msg.tags)
        
        # Planning phase: lots of questions and decisions
        if "question" in tags_set or "decision" in tags_set:
            if current_phase != "planning":
                if current_phase:
                    phases.append({
                        "type": current_phase,
                        "start": phase_start,
                        "end": i - 1,
                        "message_count": i - phase_start,
                    })
                current_phase = "planning"
                phase_start = i
        
        # Implementation phase: code blocks
        elif "code" in tags_set:
            if current_phase != "implementation":
                if current_phase:
                    phases.append({
                        "type": current_phase,
                        "start": phase_start,
                        "end": i - 1,
                        "message_count": i - phase_start,
                    })
                current_phase = "implementation"
                phase_start = i
        
        # Discussion phase: everything else
        else:
            if current_phase not in ["planning", "implementation", "discussion"]:
                if current_phase:
                    phases.append({
                        "type": current_phase,
                        "start": phase_start,
                        "end": i - 1,
                        "message_count": i - phase_start,
                    })
                current_phase = "discussion"
                phase_start = i
    
    # Add final phase
    if current_phase:
        phases.append({
            "type": current_phase,
            "start": phase_start,
            "end": len(messages) - 1,
            "message_count": len(messages) - phase_start,
        })
    
    return phases
