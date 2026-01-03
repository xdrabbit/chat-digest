"""Tests for Chronicle integration."""

import csv
from datetime import datetime
from pathlib import Path

import pytest

from chat_digest.chronicle import (
    export_to_chronicle,
    _extract_actor,
    _extract_title,
    _format_date,
    _map_importance_to_emotion,
    _should_export_message,
    _truncate_description,
)
from chat_digest.schemas import Message, Summary, ThreadDigest, ThreadMetadata


def test_export_to_chronicle_basic(tmp_path):
    """Test basic Chronicle CSV export."""
    output_path = tmp_path / "test.csv"
    
    messages = [
        Message(
            order=1,
            role="user",
            content="We need to fix the authentication bug immediately.",
            tags=["decision", "action"],
            importance_score=8.5,
        ),
        Message(
            order=2,
            role="assistant",
            content="I'll start working on it right away.",
            tags=["action"],
            importance_score=7.0,
        ),
    ]
    
    digest = ThreadDigest(
        thread=ThreadMetadata(id="test-1", title="Bug Fix"),
        messages=messages,
        summary=Summary(brief="Test", decisions=[], actions=[], open_questions=[], constraints=[]),
    )
    
    count = export_to_chronicle(digest, output_path, timeline_name="Development")
    
    assert count == 2
    assert output_path.exists()
    
    # Verify CSV format
    with open(output_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    assert len(rows) == 2
    assert rows[0]['timeline'] == 'Development'
    assert rows[0]['actor'] == 'User'
    assert 'authentication bug' in rows[0]['title'].lower()


def test_export_filters_low_importance(tmp_path):
    """Test that low importance messages are filtered out."""
    output_path = tmp_path / "test.csv"
    
    messages = [
        Message(
            order=1,
            role="user",
            content="Critical decision made",
            tags=["decision"],
            importance_score=9.0,
        ),
        Message(
            order=2,
            role="user",
            content="Thanks!",
            tags=[],
            importance_score=2.0,  # Low importance
        ),
    ]
    
    digest = ThreadDigest(
        thread=ThreadMetadata(id="test-2"),
        messages=messages,
        summary=Summary(brief="Test", decisions=[], actions=[], open_questions=[], constraints=[]),
    )
    
    count = export_to_chronicle(digest, output_path, min_importance=5.0)
    
    assert count == 1  # Only the important message


def test_export_requires_relevant_tags(tmp_path):
    """Test that messages need relevant tags to be exported."""
    output_path = tmp_path / "test.csv"
    
    messages = [
        Message(
            order=1,
            role="user",
            content="Important message",
            tags=["decision"],  # Relevant tag
            importance_score=8.0,
        ),
        Message(
            order=2,
            role="user",
            content="Also important",
            tags=["other"],  # No relevant tags
            importance_score=8.0,
        ),
    ]
    
    digest = ThreadDigest(
        thread=ThreadMetadata(id="test-3"),
        messages=messages,
        summary=Summary(brief="Test", decisions=[], actions=[], open_questions=[], constraints=[]),
    )
    
    count = export_to_chronicle(digest, output_path)
    
    assert count == 1  # Only message with relevant tags


def test_extract_title_basic():
    """Test title extraction from message content."""
    msg = Message(
        order=1,
        role="user",
        content="This is the first sentence. This is the second.",
        tags=[],
    )
    
    title = _extract_title(msg)
    
    assert title == "This is the first sentence"


def test_extract_title_removes_markdown():
    """Test that markdown formatting is removed from titles."""
    msg = Message(
        order=1,
        role="user",
        content="**Bold text** and *italic* and `code` here.",
        tags=[],
    )
    
    title = _extract_title(msg)
    
    assert "**" not in title
    assert "*" not in title
    assert "`" not in title
    assert "Bold text" in title


def test_extract_title_truncates_long():
    """Test that long titles are truncated."""
    long_content = "A" * 100
    msg = Message(order=1, role="user", content=long_content, tags=[])
    
    title = _extract_title(msg)
    
    assert len(title) <= 80
    assert title.endswith("...")


def test_truncate_description():
    """Test description truncation."""
    short = "Short description"
    assert _truncate_description(short) == short
    
    long = "A" * 600
    truncated = _truncate_description(long, max_length=500)
    assert len(truncated) <= 500
    assert truncated.endswith("...")


def test_format_date_with_timestamp():
    """Test date formatting with timestamp."""
    dt = datetime(2026, 1, 3, 14, 30, 0)
    formatted = _format_date(dt)
    
    assert formatted == "2026-01-03 14:30:00"


def test_format_date_without_timestamp():
    """Test date formatting without timestamp (uses current time)."""
    formatted = _format_date(None)
    
    # Should be valid datetime string
    assert len(formatted) == 19  # YYYY-MM-DD HH:MM:SS
    assert formatted[4] == '-'
    assert formatted[7] == '-'


def test_extract_actor_from_role():
    """Test actor extraction from message role."""
    msg = Message(order=1, role="user", content="Test", tags=[])
    assert _extract_actor(msg) == "User"
    
    msg = Message(order=1, role="assistant", content="Test", tags=[])
    assert _extract_actor(msg) == "Assistant"


def test_extract_actor_from_mention():
    """Test actor extraction from @mention."""
    msg = Message(
        order=1,
        role="user",
        content="Hey @john, can you help?",
        tags=[],
    )
    
    actor = _extract_actor(msg)
    
    assert actor == "John"


def test_extract_actor_legal_terms():
    """Test actor extraction for legal terms."""
    legal_terms = [
        ("The opposing counsel filed a motion", "Opposing Counsel"),
        ("The court ruled in our favor", "Court"),
        ("Our attorney advised us", "Attorney"),
    ]
    
    for content, expected_actor in legal_terms:
        msg = Message(order=1, role="user", content=content, tags=[])
        actor = _extract_actor(msg)
        assert actor == expected_actor


def test_map_importance_to_emotion_high():
    """Test emotion mapping for high importance scores."""
    msg = Message(order=1, role="user", content="Test", tags=[], importance_score=9.5)
    assert _map_importance_to_emotion(msg) == "critical"
    
    msg.importance_score = 8.5
    assert _map_importance_to_emotion(msg) == "urgent"
    
    msg.importance_score = 7.5
    assert _map_importance_to_emotion(msg) == "important"


def test_map_importance_to_emotion_by_tag():
    """Test emotion mapping based on message tags."""
    tag_emotions = [
        (["decision"], "decisive"),
        (["action"], "focused"),
        (["question"], "curious"),
        (["constraint"], "concerned"),
        (["code"], "technical"),
    ]
    
    for tags, expected_emotion in tag_emotions:
        msg = Message(order=1, role="user", content="Test", tags=tags, importance_score=6.0)
        emotion = _map_importance_to_emotion(msg)
        assert emotion == expected_emotion


def test_should_export_message_checks_importance():
    """Test message export filtering by importance."""
    msg = Message(
        order=1,
        role="user",
        content="Test",
        tags=["decision"],
        importance_score=8.0,
    )
    
    assert _should_export_message(msg, min_importance=5.0) is True
    assert _should_export_message(msg, min_importance=9.0) is False


def test_should_export_message_checks_tags():
    """Test message export filtering by tags."""
    msg = Message(
        order=1,
        role="user",
        content="Test",
        tags=["other"],
        importance_score=8.0,
    )
    
    assert _should_export_message(msg, min_importance=5.0) is False
    
    msg.tags = ["decision"]
    assert _should_export_message(msg, min_importance=5.0) is True


def test_csv_format_compliance(tmp_path):
    """Test that exported CSV matches Chronicle format exactly."""
    output_path = tmp_path / "chronicle.csv"
    
    messages = [
        Message(
            order=1,
            role="user",
            content="Opposing counsel missed the deadline again.",
            tags=["decision", "constraint"],
            importance_score=9.0,
            timestamp="2026-01-03T14:30:00",
        ),
    ]
    
    digest = ThreadDigest(
        thread=ThreadMetadata(id="test-4"),
        messages=messages,
        summary=Summary(brief="Test", decisions=[], actions=[], open_questions=[], constraints=[]),
    )
    
    export_to_chronicle(digest, output_path, timeline_name="Legal")
    
    # Verify exact CSV format
    with open(output_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    
    # Check required Chronicle fields
    required_fields = [
        'title', 'description', 'date', 'timeline',
        'actor', 'emotion', 'tags', 'evidence_links'
    ]
    
    assert fieldnames == required_fields
    assert len(rows) == 1
    
    row = rows[0]
    assert row['timeline'] == 'Legal'
    assert row['date'] == '2026-01-03 14:30:00'
    assert 'deadline' in row['title'].lower()
    assert row['emotion'] == 'critical'  # High importance
    assert 'decision' in row['tags']


def test_empty_messages_exports_nothing(tmp_path):
    """Test that empty message list exports 0 events."""
    output_path = tmp_path / "empty.csv"
    
    digest = ThreadDigest(
        thread=ThreadMetadata(id="test-5"),
        messages=[],
        summary=Summary(brief="Test", decisions=[], actions=[], open_questions=[], constraints=[]),
    )
    
    count = export_to_chronicle(digest, output_path)
    
    assert count == 0
    assert output_path.exists()
    
    # CSV should have header but no rows
    with open(output_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    assert len(rows) == 0


def test_custom_timeline_name(tmp_path):
    """Test custom timeline name parameter."""
    output_path = tmp_path / "custom.csv"
    
    messages = [
        Message(
            order=1,
            role="user",
            content="Project milestone reached",
            tags=["decision"],
            importance_score=8.0,
        ),
    ]
    
    digest = ThreadDigest(
        thread=ThreadMetadata(id="test-6"),
        messages=messages,
        summary=Summary(brief="Test", decisions=[], actions=[], open_questions=[], constraints=[]),
    )
    
    export_to_chronicle(digest, output_path, timeline_name="ProjectX")
    
    with open(output_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    assert rows[0]['timeline'] == 'ProjectX'
