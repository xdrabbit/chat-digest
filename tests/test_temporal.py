"""Tests for temporal analysis and timeline tracking."""

from chat_digest.temporal import (
    TimelineEvent,
    extract_timeline,
    detect_supersessions,
    get_current_state,
    get_historical_changes,
    generate_timeline_summary,
    get_conversation_phases,
)
from chat_digest.schemas import Message


def test_timeline_event_creation():
    """Test TimelineEvent creation and properties."""
    event = TimelineEvent(
        message_order=5,
        event_type="decision",
        content="Use FastAPI",
        timestamp="2024-01-01T12:00:00Z",
    )
    
    assert event.message_order == 5
    assert event.event_type == "decision"
    assert event.content == "Use FastAPI"
    assert event.is_current is True
    assert event.superseded_by is None


def test_timeline_event_superseded():
    """Test superseded timeline event."""
    event = TimelineEvent(
        message_order=3,
        event_type="decision",
        content="Use Flask",
        superseded_by=7,
    )
    
    assert event.is_current is False
    assert event.superseded_by == 7


def test_timeline_event_to_dict():
    """Test timeline event serialization."""
    event = TimelineEvent(
        message_order=1,
        event_type="action",
        content="Create project",
    )
    
    data = event.to_dict()
    
    assert data["message_order"] == 1
    assert data["event_type"] == "action"
    assert data["content"] == "Create project"
    assert data["is_current"] is True


def test_extract_timeline_basic():
    """Test basic timeline extraction."""
    messages = [
        Message(order=1, role="user", content="Let's build an API", tags=["question"]),
        Message(order=2, role="assistant", content="We'll use FastAPI", tags=["decision"]),
        Message(order=3, role="user", content="Create the project", tags=["action"]),
    ]
    
    events = extract_timeline(messages)
    
    assert len(events) == 3
    assert events[0].event_type == "question"
    assert events[1].event_type == "decision"
    assert events[2].event_type == "action"


def test_extract_timeline_with_code():
    """Test timeline extraction includes code events."""
    messages = [
        Message(order=1, role="assistant", content="```python\ncode\n```", tags=["code"]),
    ]
    
    events = extract_timeline(messages)
    
    assert len(events) == 1
    assert events[0].event_type == "code"
    assert "Code block added" in events[0].content


def test_extract_timeline_empty():
    """Test timeline extraction with no tagged messages."""
    messages = [
        Message(order=1, role="user", content="Hello", tags=[]),
    ]
    
    events = extract_timeline(messages)
    
    assert len(events) == 0


def test_detect_supersessions():
    """Test detection of superseded decisions."""
    messages = [
        Message(order=1, role="assistant", content="Let's use Flask", tags=["decision"]),
        Message(order=2, role="assistant", content="Actually, let's use FastAPI instead", tags=["decision"]),
    ]
    
    events = extract_timeline(messages)
    events = detect_supersessions(events, messages)
    
    assert len(events) == 2
    assert events[0].is_current is False  # Flask decision superseded
    assert events[0].superseded_by == 2
    assert events[1].is_current is True   # FastAPI decision is current


def test_detect_supersessions_with_keywords():
    """Test supersession detection with various keywords."""
    messages = [
        Message(order=1, role="assistant", content="Use PostgreSQL", tags=["decision"]),
        Message(order=2, role="assistant", content="Changed my mind, use MongoDB", tags=["decision"]),
    ]
    
    events = extract_timeline(messages)
    events = detect_supersessions(events, messages)
    
    assert events[0].is_current is False
    assert events[1].is_current is True


def test_get_current_state():
    """Test getting current state from timeline."""
    events = [
        TimelineEvent(1, "decision", "Use Flask", superseded_by=3),
        TimelineEvent(2, "action", "Create project"),
        TimelineEvent(3, "decision", "Use FastAPI"),
        TimelineEvent(4, "question", "Which database?"),
    ]
    
    current = get_current_state(events)
    
    assert len(current["decisions"]) == 1
    assert current["decisions"][0].content == "Use FastAPI"
    assert len(current["actions"]) == 1
    assert len(current["questions"]) == 1


def test_get_historical_changes():
    """Test getting historical (superseded) events."""
    events = [
        TimelineEvent(1, "decision", "Use Flask", superseded_by=3),
        TimelineEvent(2, "action", "Create project"),
        TimelineEvent(3, "decision", "Use FastAPI"),
    ]
    
    historical = get_historical_changes(events)
    
    assert len(historical) == 1
    assert historical[0].content == "Use Flask"


def test_generate_timeline_summary():
    """Test timeline summary generation."""
    events = [
        TimelineEvent(1, "decision", "Use FastAPI"),
        TimelineEvent(2, "action", "Create endpoints"),
        TimelineEvent(3, "question", "Which database?"),
        TimelineEvent(4, "code", "Code block added"),
    ]
    
    summary = generate_timeline_summary(events)
    
    assert "# Conversation Timeline" in summary
    assert "## Decisions" in summary
    assert "## Actions" in summary
    assert "## Questions" in summary
    assert "## Code Activity" in summary
    assert "✓ CURRENT" in summary


def test_generate_timeline_summary_with_superseded():
    """Test timeline summary shows superseded events."""
    events = [
        TimelineEvent(1, "decision", "Use Flask", superseded_by=2),
        TimelineEvent(2, "decision", "Use FastAPI"),
    ]
    
    summary = generate_timeline_summary(events)
    
    assert "⨯ Superseded" in summary
    assert "✓ CURRENT" in summary


def test_generate_timeline_summary_empty():
    """Test timeline summary with no events."""
    summary = generate_timeline_summary([])
    
    assert "No significant events" in summary


def test_get_conversation_phases():
    """Test conversation phase detection."""
    messages = [
        Message(order=1, role="user", content="Should we use FastAPI?", tags=["question"]),
        Message(order=2, role="assistant", content="Yes, let's decide on FastAPI", tags=["decision"]),
        Message(order=3, role="assistant", content="```python\ncode\n```", tags=["code"]),
        Message(order=4, role="assistant", content="```python\nmore code\n```", tags=["code"]),
        Message(order=5, role="user", content="Thanks!", tags=[]),
    ]
    
    phases = get_conversation_phases(messages)
    
    assert len(phases) >= 2  # At least planning and implementation
    assert any(p["type"] == "planning" for p in phases)
    assert any(p["type"] == "implementation" for p in phases)


def test_get_conversation_phases_single_phase():
    """Test phase detection with single phase."""
    messages = [
        Message(order=1, role="user", content="Question?", tags=["question"]),
        Message(order=2, role="assistant", content="Answer", tags=["decision"]),
    ]
    
    phases = get_conversation_phases(messages)
    
    assert len(phases) >= 1
    assert phases[0]["type"] == "planning"


def test_get_conversation_phases_includes_counts():
    """Test that phases include message counts."""
    messages = [
        Message(order=1, role="user", content="Q1?", tags=["question"]),
        Message(order=2, role="user", content="Q2?", tags=["question"]),
        Message(order=3, role="assistant", content="```code```", tags=["code"]),
    ]
    
    phases = get_conversation_phases(messages)
    
    for phase in phases:
        assert "message_count" in phase
        assert phase["message_count"] > 0
        assert "start" in phase
        assert "end" in phase


def test_timeline_event_repr():
    """Test TimelineEvent string representation."""
    event = TimelineEvent(5, "decision", "Use FastAPI")
    
    repr_str = repr(event)
    
    assert "TimelineEvent" in repr_str
    assert "#5" in repr_str
    assert "decision" in repr_str
    assert "CURRENT" in repr_str


def test_timeline_event_repr_superseded():
    """Test superseded event representation."""
    event = TimelineEvent(3, "decision", "Use Flask", superseded_by=7)
    
    repr_str = repr(event)
    
    assert "SUPERSEDED@7" in repr_str


def test_extract_timeline_preserves_order():
    """Test that timeline preserves message order."""
    messages = [
        Message(order=5, role="user", content="Q?", tags=["question"]),
        Message(order=2, role="assistant", content="D", tags=["decision"]),
        Message(order=8, role="user", content="A", tags=["action"]),
    ]
    
    events = extract_timeline(messages)
    
    assert events[0].message_order == 5
    assert events[1].message_order == 2
    assert events[2].message_order == 8


def test_get_current_state_empty():
    """Test current state with no events."""
    current = get_current_state([])
    
    assert len(current["decisions"]) == 0
    assert len(current["actions"]) == 0
    assert len(current["questions"]) == 0
    assert len(current["code_events"]) == 0
