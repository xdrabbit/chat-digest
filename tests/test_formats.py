"""Tests for multi-format output generation."""

from chat_digest.formats import (
    generate_context_card,
    generate_detailed_brief,
    generate_slack_summary,
    generate_markdown_report,
    generate_all_formats,
)
from chat_digest.schemas import Message, Summary, ThreadDigest, ThreadMetadata


def test_generate_context_card():
    """Test context card generation."""
    summary = Summary(
        brief="We're building a REST API with FastAPI. Decided on PostgreSQL for the database.",
        decisions=["Use FastAPI", "Use PostgreSQL"],
        actions=["Create database schema", "Implement auth"],
        open_questions=["Which ORM?"],
        constraints=[],
    )
    
    digest = ThreadDigest(
        thread=ThreadMetadata(id="test-1", title="API Project"),
        messages=[],
        summary=summary,
    )
    
    card = generate_context_card(digest)
    
    assert "API Project" in card
    assert len(card.split()) <= 110  # Should be under 100 words + some buffer
    assert "FastAPI" in card or "PostgreSQL" in card


def test_generate_context_card_truncates():
    """Test that context card truncates long content."""
    summary = Summary(
        brief="Very long brief " * 100,  # Way too long
        decisions=[],
        actions=[],
        open_questions=[],
        constraints=[],
    )
    
    digest = ThreadDigest(
        thread=ThreadMetadata(id="test-2"),
        messages=[],
        summary=summary,
    )
    
    card = generate_context_card(digest, max_words=50)
    
    assert len(card.split()) <= 55  # Should be truncated


def test_generate_detailed_brief():
    """Test detailed brief generation."""
    summary = Summary(
        brief="Building an API",
        decisions=["Use FastAPI"],
        actions=["Create endpoints"],
        open_questions=["Which database?"],
        constraints=["Must be RESTful"],
        code_summary={"total_blocks": 3, "languages": {"python": 3}, "unique_files": 2, "files": {}, "all_blocks": []},
    )
    
    digest = ThreadDigest(
        thread=ThreadMetadata(id="test-3", title="API Development", source_file="chat.md"),
        messages=[Message(order=1, role="user", content="Let's build an API", tags=[])],
        summary=summary,
    )
    
    brief = generate_detailed_brief(digest)
    
    assert "# API Development" in brief
    assert "Executive Summary" in brief
    assert "Key Decisions" in brief
    assert "Use FastAPI" in brief
    assert "Action Items" in brief
    assert "Create endpoints" in brief
    assert "Open Questions" in brief
    assert "Which database?" in brief
    assert "Constraints" in brief
    assert "Must be RESTful" in brief
    assert "Code Summary" in brief
    assert "3" in brief  # Total blocks


def test_generate_slack_summary():
    """Test Slack-formatted summary."""
    summary = Summary(
        brief="We're building a web app with React and Node.js",
        decisions=["Use React", "Use Node.js", "Use MongoDB"],
        actions=["Set up project", "Create components"],
        open_questions=["Which CSS framework?"],
        constraints=[],
    )
    
    digest = ThreadDigest(
        thread=ThreadMetadata(id="test-4", title="Web App"),
        messages=[],
        summary=summary,
    )
    
    slack = generate_slack_summary(digest)
    
    assert "📋" in slack  # Emoji
    assert "*Web App*" in slack  # Bold title
    assert "✅" in slack or "Decisions" in slack
    assert "React" in slack
    assert "🎯" in slack or "Action" in slack
    assert "❓" in slack or "Question" in slack


def test_generate_slack_summary_truncates_lists():
    """Test that Slack summary truncates long lists."""
    summary = Summary(
        brief="Project summary",
        decisions=[f"Decision {i}" for i in range(10)],  # 10 decisions
        actions=[f"Action {i}" for i in range(10)],  # 10 actions
        open_questions=[f"Question {i}" for i in range(10)],  # 10 questions
        constraints=[],
    )
    
    digest = ThreadDigest(
        thread=ThreadMetadata(id="test-5"),
        messages=[],
        summary=summary,
    )
    
    slack = generate_slack_summary(digest)
    
    # Should show "...and X more" for truncated lists
    assert "more" in slack.lower()


def test_generate_markdown_report():
    """Test markdown report generation."""
    messages = [
        Message(order=1, role="user", content="How do I build an API?", tags=["question"]),
        Message(order=2, role="assistant", content="Use FastAPI. Here's how...", tags=["decision"]),
    ]
    
    summary = Summary(
        brief="API development discussion",
        decisions=["Use FastAPI"],
        actions=["Create project"],
        open_questions=[],
        constraints=[],
    )
    
    digest = ThreadDigest(
        thread=ThreadMetadata(id="test-6", title="API Tutorial"),
        messages=messages,
        summary=summary,
    )
    
    report = generate_markdown_report(digest)
    
    # Check front matter
    assert "---" in report
    assert "title: API Tutorial" in report
    
    # Check TOC
    assert "Table of Contents" in report
    assert "[Summary](#summary)" in report
    assert "[Decisions](#decisions)" in report
    
    # Check sections
    assert "## Summary" in report
    assert "## Decisions" in report
    assert "## Transcript" in report
    
    # Check transcript includes messages
    assert "👤" in report or "User" in report
    assert "🤖" in report or "Assistant" in report
    assert "How do I build an API?" in report


def test_generate_all_formats():
    """Test generating all formats at once."""
    summary = Summary(
        brief="Test summary",
        decisions=["Decision 1"],
        actions=["Action 1"],
        open_questions=[],
        constraints=[],
    )
    
    digest = ThreadDigest(
        thread=ThreadMetadata(id="test-7"),
        messages=[],
        summary=summary,
    )
    
    all_formats = generate_all_formats(digest)
    
    assert "context_card" in all_formats
    assert "detailed_brief" in all_formats
    assert "slack" in all_formats
    assert "markdown_report" in all_formats
    
    # Each should have content
    assert len(all_formats["context_card"]) > 0
    assert len(all_formats["detailed_brief"]) > 0
    assert len(all_formats["slack"]) > 0
    assert len(all_formats["markdown_report"]) > 0


def test_context_card_with_no_decisions_or_actions():
    """Test context card when there are no decisions or actions."""
    summary = Summary(
        brief="Just a discussion",
        decisions=[],
        actions=[],
        open_questions=[],
        constraints=[],
    )
    
    digest = ThreadDigest(
        thread=ThreadMetadata(id="test-8"),
        messages=[],
        summary=summary,
    )
    
    card = generate_context_card(digest)
    
    assert len(card) > 0  # Should still generate something
    assert "Just a discussion" in card


def test_detailed_brief_with_minimal_data():
    """Test detailed brief with minimal data."""
    summary = Summary(
        brief="Minimal",
        decisions=[],
        actions=[],
        open_questions=[],
        constraints=[],
    )
    
    digest = ThreadDigest(
        thread=ThreadMetadata(id="test-9"),
        messages=[],
        summary=summary,
    )
    
    brief = generate_detailed_brief(digest)
    
    assert "Executive Summary" in brief
    assert "Minimal" in brief


def test_markdown_report_with_code_summary():
    """Test markdown report includes code summary."""
    summary = Summary(
        brief="Code discussion",
        decisions=[],
        actions=[],
        open_questions=[],
        constraints=[],
        code_summary={
            "total_blocks": 5,
            "languages": {"python": 3, "javascript": 2},
            "unique_files": 2,
            "files": {"app.py": {}, "utils.js": {}},
            "all_blocks": [],
        },
    )
    
    digest = ThreadDigest(
        thread=ThreadMetadata(id="test-10"),
        messages=[],
        summary=summary,
    )
    
    report = generate_markdown_report(digest)
    
    assert "## Code" in report
    assert "5" in report  # Total blocks
    assert "app.py" in report
    assert "utils.js" in report
