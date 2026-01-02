"""Tests for incremental digest updates."""

import json
from pathlib import Path

from chat_digest.incremental import (
    load_existing_digest,
    merge_messages,
    create_incremental_digest,
    get_new_messages_since,
    get_digest_stats,
    compare_digests,
)
from chat_digest.schemas import Message, Summary, ThreadDigest, ThreadMetadata


def test_merge_messages_no_duplicates():
    """Test merging messages without duplicates."""
    existing = [
        Message(order=1, role="user", content="First", tags=[]),
        Message(order=2, role="assistant", content="Second", tags=[]),
    ]
    
    new = [
        Message(order=3, role="user", content="Third", tags=[]),
        Message(order=4, role="assistant", content="Fourth", tags=[]),
    ]
    
    merged = merge_messages(existing, new)
    
    assert len(merged) == 4
    assert merged[0].order == 1
    assert merged[-1].order == 4


def test_merge_messages_with_duplicates():
    """Test that merge avoids duplicates."""
    existing = [
        Message(order=1, role="user", content="First", tags=[]),
        Message(order=2, role="assistant", content="Second", tags=[]),
    ]
    
    new = [
        Message(order=2, role="assistant", content="Second", tags=[]),  # Duplicate
        Message(order=3, role="user", content="Third", tags=[]),
    ]
    
    merged = merge_messages(existing, new)
    
    assert len(merged) == 3  # Should not duplicate order 2
    assert [m.order for m in merged] == [1, 2, 3]


def test_merge_messages_preserves_order():
    """Test that merged messages are sorted by order."""
    existing = [
        Message(order=1, role="user", content="First", tags=[]),
        Message(order=5, role="assistant", content="Fifth", tags=[]),
    ]
    
    new = [
        Message(order=3, role="user", content="Third", tags=[]),
        Message(order=2, role="assistant", content="Second", tags=[]),
    ]
    
    merged = merge_messages(existing, new)
    
    assert [m.order for m in merged] == [1, 2, 3, 5]


def test_create_incremental_digest():
    """Test creating an incremental digest."""
    existing_digest = ThreadDigest(
        thread=ThreadMetadata(id="test-1", title="Test Thread"),
        messages=[
            Message(order=1, role="user", content="Hello", tags=[]),
        ],
        summary=Summary(
            brief="Initial brief",
            decisions=[],
            actions=[],
            open_questions=[],
            constraints=[],
        ),
    )
    
    new_messages = [
        Message(order=2, role="assistant", content="Hi there", tags=[]),
    ]
    
    updated = create_incremental_digest(existing_digest, new_messages)
    
    assert len(updated.messages) == 2
    assert updated.thread.id == "test-1"
    assert updated.thread.title == "Test Thread"


def test_get_new_messages_since():
    """Test extracting new messages since a certain order."""
    messages = [
        Message(order=1, role="user", content="First", tags=[]),
        Message(order=2, role="assistant", content="Second", tags=[]),
        Message(order=3, role="user", content="Third", tags=[]),
        Message(order=4, role="assistant", content="Fourth", tags=[]),
    ]
    
    new = get_new_messages_since(messages, last_order=2)
    
    assert len(new) == 2
    assert new[0].order == 3
    assert new[1].order == 4


def test_get_digest_stats():
    """Test digest statistics generation."""
    digest = ThreadDigest(
        thread=ThreadMetadata(id="test-2"),
        messages=[
            Message(order=1, role="user", content="First", tags=[]),
            Message(order=5, role="assistant", content="Last", tags=[]),
        ],
        summary=Summary(
            brief="Test",
            decisions=["Decision 1", "Decision 2"],
            actions=["Action 1"],
            open_questions=[],
            constraints=[],
        ),
    )
    
    stats = get_digest_stats(digest)
    
    assert stats["total_messages"] == 2
    assert stats["first_message_order"] == 1
    assert stats["last_message_order"] == 5
    assert stats["total_decisions"] == 2
    assert stats["total_actions"] == 1


def test_compare_digests():
    """Test comparing two digests."""
    old = ThreadDigest(
        thread=ThreadMetadata(id="test-3"),
        messages=[Message(order=1, role="user", content="First", tags=[])],
        summary=Summary(
            brief="Old",
            decisions=["Decision 1"],
            actions=[],
            open_questions=[],
            constraints=[],
        ),
    )
    
    new = ThreadDigest(
        thread=ThreadMetadata(id="test-3"),
        messages=[
            Message(order=1, role="user", content="First", tags=[]),
            Message(order=2, role="assistant", content="Second", tags=[]),
        ],
        summary=Summary(
            brief="New",
            decisions=["Decision 1", "Decision 2"],
            actions=["Action 1"],
            open_questions=[],
            constraints=[],
        ),
    )
    
    diff = compare_digests(old, new)
    
    assert diff["messages_added"] == 1
    assert diff["decisions_added"] == 1
    assert diff["actions_added"] == 1
    assert diff["old_last_order"] == 1
    assert diff["new_last_order"] == 2


def test_load_existing_digest_nonexistent(tmp_path):
    """Test loading a digest that doesn't exist."""
    path = tmp_path / "nonexistent.json"
    
    digest = load_existing_digest(path)
    
    assert digest is None


def test_load_existing_digest_valid(tmp_path):
    """Test loading a valid existing digest."""
    path = tmp_path / "digest.json"
    
    # Create a digest
    digest_data = {
        "thread": {"id": "test-4", "title": "Test", "created_at": "2024-01-01T00:00:00Z", "schema_version": 1},
        "messages": [{"order": 1, "role": "user", "content": "Hello", "tags": []}],
        "summary": {
            "brief": "Test brief",
            "decisions": [],
            "actions": [],
            "open_questions": [],
            "constraints": [],
        },
    }
    
    path.write_text(json.dumps(digest_data), encoding="utf-8")
    
    loaded = load_existing_digest(path)
    
    assert loaded is not None
    assert loaded.thread.id == "test-4"
    assert len(loaded.messages) == 1
