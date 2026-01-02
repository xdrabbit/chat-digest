"""Tests for message importance scoring."""

from chat_digest.importance import (
    score_message_importance,
    rank_messages_by_importance,
    filter_important_messages,
    get_importance_distribution,
    get_top_messages,
)
from chat_digest.schemas import Message


def test_score_message_basic():
    """Test basic message scoring."""
    msg = Message(order=1, role="user", content="Hello, how are you?", tags=[])
    score = score_message_importance(msg)
    
    assert 0.0 <= score <= 10.0
    assert score > 0  # Should have some base score


def test_score_assistant_higher_than_user():
    """Test that assistant messages score higher than user messages."""
    user_msg = Message(order=1, role="user", content="Can you help me with this?", tags=[])
    assistant_msg = Message(order=2, role="assistant", content="Sure, I can help with that.", tags=[])
    
    user_score = score_message_importance(user_msg)
    assistant_score = score_message_importance(assistant_msg)
    
    assert assistant_score > user_score


def test_score_code_tag_boosts_score():
    """Test that code tag significantly boosts importance."""
    without_code = Message(order=1, role="assistant", content="Here's some text", tags=[])
    with_code = Message(order=2, role="assistant", content="Here's some code", tags=["code"])
    
    score_without = score_message_importance(without_code)
    score_with = score_message_importance(with_code)
    
    assert score_with > score_without
    assert score_with - score_without >= 1.5  # Code adds significant value


def test_score_decision_tag_boosts_score():
    """Test that decision tag boosts importance."""
    without_decision = Message(order=1, role="assistant", content="Let's think about this", tags=[])
    with_decision = Message(order=2, role="assistant", content="We'll use React", tags=["decision"])
    
    score_without = score_message_importance(without_decision)
    score_with = score_message_importance(with_decision)
    
    assert score_with > score_without


def test_score_short_acknowledgment_low():
    """Test that short acknowledgments score low."""
    acknowledgment = Message(order=1, role="user", content="ok", tags=[])
    score = score_message_importance(acknowledgment)
    
    assert score < 5.0  # Should be below average


def test_score_question_boosts():
    """Test that questions boost importance."""
    statement = Message(order=1, role="user", content="I need help with this task", tags=[])
    question = Message(order=2, role="user", content="Can you help me with this task?", tags=[])
    
    statement_score = score_message_importance(statement)
    question_score = score_message_importance(question)
    
    assert question_score > statement_score


def test_score_multiple_tags_cumulative():
    """Test that multiple tags have cumulative effect."""
    no_tags = Message(order=1, role="assistant", content="Some content here", tags=[])
    one_tag = Message(order=2, role="assistant", content="Some content here", tags=["code"])
    two_tags = Message(order=3, role="assistant", content="Some content here", tags=["code", "decision"])
    
    score_none = score_message_importance(no_tags)
    score_one = score_message_importance(one_tag)
    score_two = score_message_importance(two_tags)
    
    assert score_one > score_none
    assert score_two > score_one


def test_score_ideal_length_boost():
    """Test that ideal length (100-500 chars) gets a boost."""
    short = Message(order=1, role="assistant", content="Short", tags=[])
    ideal = Message(order=2, role="assistant", content="A" * 300, tags=[])  # 300 chars
    
    short_score = score_message_importance(short)
    ideal_score = score_message_importance(ideal)
    
    assert ideal_score > short_score


def test_rank_messages_by_importance():
    """Test ranking messages by importance."""
    messages = [
        Message(order=1, role="user", content="ok", tags=[]),  # Low importance
        Message(order=2, role="assistant", content="```python\ncode\n```", tags=["code"]),  # High
        Message(order=3, role="user", content="Can you explain this?", tags=["question"]),  # Medium
    ]
    
    ranked = rank_messages_by_importance(messages)
    
    assert len(ranked) == 3
    assert ranked[0][0].order == 2  # Code message should be first
    assert ranked[0][1] > ranked[1][1]  # Scores should be descending


def test_filter_important_messages():
    """Test filtering messages by importance threshold."""
    messages = [
        Message(order=1, role="user", content="ok", tags=[]),  # Low
        Message(order=2, role="assistant", content="Here's a detailed explanation" * 10, tags=["decision"]),  # High
        Message(order=3, role="user", content="thanks", tags=[]),  # Low
        Message(order=4, role="assistant", content="```python\ncode\n```", tags=["code"]),  # High
    ]
    
    important = filter_important_messages(messages, min_score=6.0)
    
    assert len(important) < len(messages)
    assert all(msg.order in [2, 4] for msg in important)  # Only high-scoring messages


def test_filter_important_messages_max_count():
    """Test limiting number of important messages."""
    messages = [
        Message(order=i, role="assistant", content="Important content" * 20, tags=["decision"])
        for i in range(10)
    ]
    
    important = filter_important_messages(messages, min_score=5.0, max_count=5)
    
    assert len(important) == 5


def test_filter_important_messages_preserves_order():
    """Test that filtering preserves original message order."""
    messages = [
        Message(order=1, role="assistant", content="First important message with code", tags=["code"]),
        Message(order=2, role="user", content="ok", tags=[]),
        Message(order=3, role="assistant", content="Second important message with decision", tags=["decision"]),
    ]
    
    important = filter_important_messages(messages, min_score=5.5)
    
    assert len(important) >= 2  # Should have at least 2 important messages
    assert important[0].order < important[1].order  # Order preserved


def test_get_importance_distribution():
    """Test importance distribution statistics."""
    messages = [
        Message(order=1, role="user", content="ok", tags=[]),  # Low
        Message(order=2, role="assistant", content="Medium content here", tags=[]),  # Medium
        Message(order=3, role="assistant", content="```code```", tags=["code"]),  # High
    ]
    
    dist = get_importance_distribution(messages)
    
    assert dist["count"] == 3
    assert "min" in dist
    assert "max" in dist
    assert "mean" in dist
    assert "median" in dist
    assert dist["high_importance"] >= 0
    assert dist["medium_importance"] >= 0
    assert dist["low_importance"] >= 0


def test_get_importance_distribution_empty():
    """Test distribution with no messages."""
    dist = get_importance_distribution([])
    
    assert dist["count"] == 0
    assert dist["min"] == 0.0
    assert dist["max"] == 0.0


def test_get_top_messages():
    """Test getting top N messages."""
    messages = [
        Message(order=i, role="assistant", content=f"Message {i}" * 20, tags=["decision" if i % 2 == 0 else ""])
        for i in range(20)
    ]
    
    top_5 = get_top_messages(messages, n=5)
    
    assert len(top_5) == 5
    # Should be sorted by original order
    for i in range(len(top_5) - 1):
        assert top_5[i].order < top_5[i + 1].order


def test_get_top_messages_fewer_than_n():
    """Test getting top N when there are fewer messages."""
    messages = [
        Message(order=1, role="user", content="Only message", tags=[]),
    ]
    
    top_5 = get_top_messages(messages, n=5)
    
    assert len(top_5) == 1


def test_score_constraint_tag():
    """Test that constraint tag boosts score."""
    without = Message(order=1, role="assistant", content="Some text", tags=[])
    with_constraint = Message(order=2, role="assistant", content="Must use Python 3.11", tags=["constraint"])
    
    score_without = score_message_importance(without)
    score_with = score_message_importance(with_constraint)
    
    assert score_with > score_without


def test_score_action_tag():
    """Test that action tag boosts score."""
    without = Message(order=1, role="assistant", content="Some text", tags=[])
    with_action = Message(order=2, role="assistant", content="TODO: implement feature", tags=["action"])
    
    score_without = score_message_importance(without)
    score_with = score_message_importance(with_action)
    
    assert score_with > score_without


def test_score_very_short_message_penalty():
    """Test that very short messages get penalized."""
    very_short = Message(order=1, role="user", content="hi", tags=[])
    normal = Message(order=2, role="user", content="Hello, I need help with something", tags=[])
    
    very_short_score = score_message_importance(very_short)
    normal_score = score_message_importance(normal)
    
    assert normal_score > very_short_score


def test_score_multiple_questions():
    """Test that multiple questions boost score more."""
    one_question = Message(order=1, role="user", content="What is this?", tags=[])
    three_questions = Message(order=2, role="user", content="What? Why? How?", tags=[])
    
    one_score = score_message_importance(one_question)
    three_score = score_message_importance(three_questions)
    
    assert three_score > one_score
