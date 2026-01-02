"""Message importance scoring for prioritizing content in summaries."""

from __future__ import annotations

from typing import List

from .schemas import Message


def score_message_importance(message: Message) -> float:
    """
    Calculate an importance score for a message (0.0 to 10.0).
    
    Higher scores indicate more important messages that should be prioritized
    in summaries and context extraction.
    
    Scoring factors:
    - Role: Assistant messages with code/decisions score higher
    - Tags: code, decision, action, constraint boost score
    - Length: Longer messages (up to a point) score higher
    - Questions: Questions from users score higher
    - Acknowledgments: Short confirmations score lower
    """
    score = 5.0  # Base score
    
    # Role-based scoring
    if message.role == "assistant":
        score += 1.0  # Assistant responses are generally more informative
    elif message.role == "user":
        score += 0.5  # User messages provide context
    elif message.role == "system":
        score += 0.3  # System messages are metadata
    
    # Tag-based scoring (cumulative)
    tag_weights = {
        "code": 2.0,        # Code is highly valuable
        "decision": 1.5,    # Decisions are critical
        "action": 1.0,      # Actions are important
        "constraint": 1.2,  # Constraints must be remembered
        "question": 0.8,    # Questions indicate uncertainty
    }
    
    for tag in message.tags:
        score += tag_weights.get(tag, 0.0)
    
    # Length-based scoring (sweet spot: 100-500 chars)
    content_length = len(message.content)
    if content_length < 20:
        score -= 2.0  # Very short = likely acknowledgment
    elif content_length < 50:
        score -= 1.0  # Short = minimal info
    elif 100 <= content_length <= 500:
        score += 1.0  # Ideal length
    elif content_length > 1000:
        score += 0.5  # Long but potentially verbose
    
    # Detect acknowledgments/confirmations (low value)
    acknowledgments = [
        "ok", "okay", "thanks", "thank you", "got it", "sounds good",
        "perfect", "great", "awesome", "yes", "no", "sure", "yep", "nope"
    ]
    content_lower = message.content.lower().strip()
    if any(ack == content_lower for ack in acknowledgments):
        score -= 3.0  # Pure acknowledgments are low value
    
    # Boost for questions (indicate important clarifications)
    if "?" in message.content:
        question_count = message.content.count("?")
        score += min(question_count * 0.3, 1.5)  # Cap at +1.5
    
    # Clamp score to 0-10 range
    return max(0.0, min(10.0, score))


def rank_messages_by_importance(messages: List[Message]) -> List[tuple[Message, float]]:
    """
    Rank messages by importance score.
    
    Returns:
        List of (message, score) tuples sorted by score (highest first)
    """
    scored = [(msg, score_message_importance(msg)) for msg in messages]
    return sorted(scored, key=lambda x: x[1], reverse=True)


def filter_important_messages(
    messages: List[Message],
    min_score: float = 6.0,
    max_count: int | None = None,
) -> List[Message]:
    """
    Filter messages to only include important ones.
    
    Args:
        messages: List of messages to filter
        min_score: Minimum importance score (default 6.0)
        max_count: Maximum number of messages to return (optional)
    
    Returns:
        List of important messages, sorted by original order
    """
    ranked = rank_messages_by_importance(messages)
    
    # Filter by score
    important = [msg for msg, score in ranked if score >= min_score]
    
    # Limit count if specified
    if max_count and len(important) > max_count:
        important = important[:max_count]
    
    # Re-sort by original order
    return sorted(important, key=lambda m: m.order)


def get_importance_distribution(messages: List[Message]) -> dict:
    """
    Get statistics about message importance distribution.
    
    Returns:
        Dict with min, max, mean, median scores and percentile breakdowns
    """
    if not messages:
        return {
            "count": 0,
            "min": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "median": 0.0,
            "high_importance": 0,
            "medium_importance": 0,
            "low_importance": 0,
        }
    
    scores = [score_message_importance(msg) for msg in messages]
    scores_sorted = sorted(scores)
    
    count = len(scores)
    mean_score = sum(scores) / count
    median_score = scores_sorted[count // 2]
    
    # Categorize by importance
    high = sum(1 for s in scores if s >= 7.0)
    medium = sum(1 for s in scores if 4.0 <= s < 7.0)
    low = sum(1 for s in scores if s < 4.0)
    
    return {
        "count": count,
        "min": min(scores),
        "max": max(scores),
        "mean": round(mean_score, 2),
        "median": round(median_score, 2),
        "high_importance": high,
        "medium_importance": medium,
        "low_importance": low,
    }


def get_top_messages(messages: List[Message], n: int = 10) -> List[Message]:
    """
    Get the top N most important messages, preserving order.
    
    Args:
        messages: List of messages
        n: Number of top messages to return
    
    Returns:
        Top N messages sorted by original order
    """
    ranked = rank_messages_by_importance(messages)
    top_n = [msg for msg, _ in ranked[:n]]
    return sorted(top_n, key=lambda m: m.order)
