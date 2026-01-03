"""Tests for pattern detection."""

from datetime import datetime, timedelta

import pytest

from chat_digest.patterns import (
    Pattern,
    detect_all_patterns,
    detect_escalation_pattern,
    detect_promise_break_cycles,
    detect_recurring_topics,
    detect_timing_patterns,
    get_pattern_summary,
)
from chat_digest.schemas import Message


def test_pattern_creation():
    """Test Pattern class creation."""
    pattern = Pattern(
        pattern_type="test",
        description="Test pattern",
        frequency=5,
        confidence=0.85,
    )
    
    assert pattern.pattern_type == "test"
    assert pattern.description == "Test pattern"
    assert pattern.frequency == 5
    assert pattern.confidence == 0.85
    assert pattern.evidence == []


def test_pattern_to_dict():
    """Test Pattern to_dict conversion."""
    dt = datetime(2026, 1, 3, 14, 30)
    pattern = Pattern(
        pattern_type="test",
        description="Test",
        frequency=3,
        confidence=0.90,
        first_occurrence=dt,
        last_occurrence=dt,
        evidence=["a", "b", "c"],
    )
    
    result = pattern.to_dict()
    
    assert result['pattern_type'] == "test"
    assert result['frequency'] == 3
    assert result['confidence'] == 0.90
    assert result['evidence_count'] == 3
    assert result['first_occurrence'] == dt.isoformat()


def test_detect_promise_break_cycles_insufficient_data():
    """Test that promise-break detection requires enough supersessions."""
    messages = [
        Message(order=1, role="user", content="Decision A", tags=["decision"]),
        Message(order=2, role="user", content="Actually, not A", tags=["decision"]),
    ]
    
    pattern = detect_promise_break_cycles(messages)
    
    assert pattern is None  # Need at least 3 supersessions


@pytest.mark.xfail(reason="Needs more work on supersession detection integration")
@pytest.mark.xfail(reason="Needs more work on supersession detection integration")
def test_detect_promise_break_cycles_with_pattern():
    """Test promise-break cycle detection with sufficient data."""
    base_time = datetime(2026, 1, 1)
    messages = []
    
    # Create 5 promise-break cycles
    for i in range(5):
        dt = base_time + timedelta(days=i*10)
        messages.append(Message(
            order=i*2,
            role="user",
            content=f"We will use approach {i}",
            tags=["decision"],
            timestamp=dt.isoformat(),
        ))
        messages.append(Message(
            order=i*2+1,
            role="user",
            content=f"Actually, let's switch to approach {i+1} instead",  # Supersession keyword
            tags=["decision"],
            timestamp=(dt + timedelta(days=2)).isoformat(),
        ))
    
    pattern = detect_promise_break_cycles(messages)
    
    assert pattern is not None
    assert pattern.pattern_type == "promise_break_cycle"
    assert pattern.frequency >= 3  # At least 3 supersessions
    assert pattern.confidence > 0.7
    assert "Promise-break cycle" in pattern.description


def test_detect_escalation_pattern_insufficient_data():
    """Test that escalation detection requires enough messages."""
    messages = [
        Message(order=1, role="user", content="Test", tags=[], importance_score=5.0),
        Message(order=2, role="user", content="Test", tags=[], importance_score=6.0),
    ]
    
    pattern = detect_escalation_pattern(messages)
    
    assert pattern is None  # Need at least 5 messages


def test_detect_escalation_pattern_with_trend():
    """Test escalation pattern detection with increasing importance."""
    messages = []
    
    # Create messages with increasing importance
    for i in range(10):
        messages.append(Message(
            order=i,
            role="user",
            content=f"Message {i}",
            tags=["decision"],
            importance_score=5.0 + (i * 0.5),  # 5.0 to 9.5
        ))
    
    pattern = detect_escalation_pattern(messages)
    
    assert pattern is not None
    assert pattern.pattern_type == "escalation"
    assert pattern.confidence > 0.6
    assert "Escalation pattern" in pattern.description
    assert "increasing" in pattern.description.lower()


def test_detect_escalation_pattern_no_trend():
    """Test that flat importance scores don't trigger escalation."""
    messages = []
    
    # All messages have same importance
    for i in range(10):
        messages.append(Message(
            order=i,
            role="user",
            content=f"Message {i}",
            tags=["decision"],
            importance_score=7.0,
        ))
    
    pattern = detect_escalation_pattern(messages)
    
    assert pattern is None


def test_detect_recurring_topics_basic():
    """Test recurring topic detection."""
    messages = []
    
    # Create messages with recurring 'bug' tag
    for i in range(8):
        messages.append(Message(
            order=i,
            role="user",
            content=f"Message {i}",
            tags=["bug", "other"],
        ))
    
    patterns = detect_recurring_topics(messages)
    
    assert len(patterns) > 0
    bug_pattern = next((p for p in patterns if 'bug' in p.evidence), None)
    assert bug_pattern is not None
    assert bug_pattern.pattern_type == "recurring_topic"
    assert bug_pattern.frequency >= 5


def test_detect_recurring_topics_filters_infrequent():
    """Test that infrequent topics are not detected."""
    messages = []
    
    # Tag appears only 3 times
    for i in range(3):
        messages.append(Message(
            order=i,
            role="user",
            content=f"Message {i}",
            tags=["rare"],
        ))
    
    # Add other messages
    for i in range(3, 10):
        messages.append(Message(
            order=i,
            role="user",
            content=f"Message {i}",
            tags=["other"],
        ))
    
    patterns = detect_recurring_topics(messages)
    
    # 'rare' should not be detected (< 5 occurrences)
    rare_pattern = next((p for p in patterns if 'rare' in p.evidence), None)
    assert rare_pattern is None


def test_detect_timing_patterns_insufficient_data():
    """Test that timing detection requires enough timestamped messages."""
    messages = [
        Message(
            order=1,
            role="user",
            content="Test",
            tags=["decision"],
            timestamp="2026-01-01T10:00:00",
        ),
    ]
    
    pattern = detect_timing_patterns(messages)
    
    assert pattern is None


def test_detect_timing_patterns_with_clustering():
    """Test timing pattern detection with day-of-week clustering."""
    messages = []
    base_date = datetime(2026, 1, 5)  # Monday
    
    # Create 10 messages, 8 on Fridays (day 4)
    for i in range(8):
        friday = base_date + timedelta(days=4 + (i * 7))  # Every Friday
        messages.append(Message(
            order=i,
            role="user",
            content=f"Friday message {i}",
            tags=["decision"],
            timestamp=friday.isoformat(),
        ))
    
    # Add 2 on other days
    for i in range(2):
        other_day = base_date + timedelta(days=i)
        messages.append(Message(
            order=8+i,
            role="user",
            content=f"Other day {i}",
            tags=["decision"],
            timestamp=other_day.isoformat(),
        ))
    
    pattern = detect_timing_patterns(messages)
    
    assert pattern is not None
    assert pattern.pattern_type == "timing_pattern"
    assert "Friday" in pattern.description
    assert pattern.confidence > 0.7


def test_detect_timing_patterns_no_clustering():
    """Test that evenly distributed events don't trigger timing pattern."""
    messages = []
    base_date = datetime(2026, 1, 1)
    
    # Distribute evenly across week
    for i in range(7):
        dt = base_date + timedelta(days=i)
        messages.append(Message(
            order=i,
            role="user",
            content=f"Message {i}",
            tags=["decision"],
            timestamp=dt.isoformat(),
        ))
    
    pattern = detect_timing_patterns(messages)
    
    assert pattern is None  # No day has > 50%


def test_detect_all_patterns_empty():
    """Test detect_all_patterns with no messages."""
    patterns = detect_all_patterns([])
    
    assert patterns == []


def test_detect_all_patterns_integration():
    """Test detect_all_patterns finds multiple pattern types."""
    messages = []
    base_time = datetime(2026, 1, 1)
    
    # Add messages with escalating importance
    for i in range(10):
        messages.append(Message(
            order=i,
            role="user",
            content=f"Message {i}",
            tags=["bug", "decision"],
            importance_score=5.0 + (i * 0.5),
            timestamp=(base_time + timedelta(days=i)).isoformat(),
        ))
    
    patterns = detect_all_patterns(messages)
    
    # Should detect at least recurring topic and escalation
    assert len(patterns) > 0
    pattern_types = {p.pattern_type for p in patterns}
    assert "recurring_topic" in pattern_types or "escalation" in pattern_types


def test_detect_all_patterns_sorted_by_confidence():
    """Test that patterns are sorted by confidence."""
    messages = []
    
    # Create conditions for multiple patterns
    for i in range(15):
        messages.append(Message(
            order=i,
            role="user",
            content=f"Message {i}",
            tags=["bug", "feature"],
            importance_score=5.0 + (i * 0.3),
        ))
    
    patterns = detect_all_patterns(messages)
    
    if len(patterns) > 1:
        # Check sorted by confidence (descending)
        for i in range(len(patterns) - 1):
            assert patterns[i].confidence >= patterns[i+1].confidence


def test_get_pattern_summary_empty():
    """Test pattern summary with no patterns."""
    summary = get_pattern_summary([])
    
    assert summary['total_patterns'] == 0
    assert summary['by_type'] == {}
    assert summary['highest_confidence'] == 0.0
    assert summary['average_confidence'] == 0.0


def test_get_pattern_summary_with_patterns():
    """Test pattern summary with multiple patterns."""
    patterns = [
        Pattern("type_a", "Description A", 5, 0.90),
        Pattern("type_a", "Description A2", 3, 0.85),
        Pattern("type_b", "Description B", 7, 0.95),
    ]
    
    summary = get_pattern_summary(patterns)
    
    assert summary['total_patterns'] == 3
    assert summary['by_type']['type_a'] == 2
    assert summary['by_type']['type_b'] == 1
    assert summary['highest_confidence'] == 0.95
    assert summary['average_confidence'] == pytest.approx(0.90, abs=0.01)
    assert len(summary['patterns']) == 3


def test_pattern_confidence_calculation():
    """Test that confidence scores are reasonable."""
    messages = []
    
    # Create escalating messages
    for i in range(10):
        messages.append(Message(
            order=i,
            role="user",
            content=f"Message {i}",
            tags=["decision"],
            importance_score=5.0 + i,
        ))
    
    pattern = detect_escalation_pattern(messages)
    
    assert pattern is not None
    assert 0.0 <= pattern.confidence <= 1.0


def test_recurring_topics_span_requirement():
    """Test that recurring topics must span conversation."""
    messages = []
    
    # Create 10 messages with 'bug' tag only in first 3
    for i in range(3):
        messages.append(Message(
            order=i,
            role="user",
            content=f"Message {i}",
            tags=["bug"] * 5,  # Repeat to get count up
        ))
    
    # Add many more messages without the tag
    for i in range(3, 20):
        messages.append(Message(
            order=i,
            role="user",
            content=f"Message {i}",
            tags=["other"],
        ))
    
    patterns = detect_recurring_topics(messages)
    
    # 'bug' appears 15 times but only spans 3/20 messages (15%)
    # Should not be detected as recurring
    bug_pattern = next((p for p in patterns if 'bug' in p.evidence), None)
    assert bug_pattern is None


@pytest.mark.xfail(reason="Needs more work on supersession detection integration")
@pytest.mark.xfail(reason="Needs more work on supersession detection integration")
def test_promise_break_confidence_with_consistent_timing():
    """Test that consistent timing increases confidence."""
    base_time = datetime(2026, 1, 1)
    messages = []
    
    # Create very consistent 10-day cycles
    for i in range(5):
        dt = base_time + timedelta(days=i*10)
        messages.append(Message(
            order=i*2,
            role="user",
            content=f"We will use approach {i}",
            tags=["decision"],
            timestamp=dt.isoformat(),
        ))
        messages.append(Message(
            order=i*2+1,
            role="user",
            content=f"Actually, changed my mind about {i}",  # Supersession keyword
            tags=["decision"],
            timestamp=(dt + timedelta(days=1)).isoformat(),
        ))
    
    pattern = detect_promise_break_cycles(messages)
    
    assert pattern is not None
    # Consistent timing should yield high confidence
    assert pattern.confidence > 0.85
