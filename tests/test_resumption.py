"""Tests for resumption prompt generation."""

from chat_digest.parser import parse_transcript, infer_title
from chat_digest.resumption import (
    generate_resumption_prompt,
    _extract_file_mentions,
    _extract_code_snippets,
    _suggest_next_steps,
)
from chat_digest.schemas import Message, Summary, ThreadDigest, ThreadMetadata
from chat_digest.summarize import extract_signals, generate_summary


def test_generate_resumption_prompt_basic():
    """Test basic resumption prompt generation."""
    messages = [
        Message(order=1, role="user", content="Let's build a web app", tags=[]),
        Message(order=2, role="assistant", content="Great! We'll use React.", tags=["decision"]),
    ]
    
    summary = Summary(
        brief="Building a web app with React",
        decisions=["We'll use React"],
        actions=[],
        open_questions=[],
        constraints=[],
    )
    
    digest = ThreadDigest(
        thread=ThreadMetadata(id="test-123", title="Web App Project"),
        messages=messages,
        summary=summary,
    )
    
    prompt = generate_resumption_prompt(digest)
    
    assert "# Context from Previous Session" in prompt
    assert "Building a web app with React" in prompt
    assert "We'll use React" in prompt
    assert "Web App Project" in prompt


def test_resumption_prompt_with_files():
    """Test that file mentions are extracted and included."""
    messages = [
        Message(order=1, role="user", content="Edit `src/app.py` and `config.json`", tags=[]),
        Message(order=2, role="assistant", content="I'll update src/utils/helper.py too", tags=[]),
    ]
    
    summary = Summary(
        brief="Editing configuration files",
        decisions=[],
        actions=["Update app.py", "Modify config.json"],
        open_questions=[],
        constraints=[],
    )
    
    digest = ThreadDigest(
        thread=ThreadMetadata(id="test-456"),
        messages=messages,
        summary=summary,
    )
    
    prompt = generate_resumption_prompt(digest)
    
    assert "src/app.py" in prompt or "app.py" in prompt
    assert "config.json" in prompt
    assert "Files discussed/modified" in prompt


def test_resumption_prompt_with_code():
    """Test that code blocks are detected."""
    messages = [
        Message(
            order=1,
            role="assistant",
            content="Here's the code:\n```python\ndef hello():\n    print('world')\n```",
            tags=["code"],
        ),
    ]
    
    summary = Summary(
        brief="Added hello function",
        decisions=[],
        actions=[],
        open_questions=[],
        constraints=[],
        code_summary={"total_blocks": 1, "languages": {"python": 1}, "unique_files": 0, "files": {}, "all_blocks": []},
    )
    
    digest = ThreadDigest(
        thread=ThreadMetadata(id="test-789"),
        messages=messages,
        summary=summary,
    )
    
    prompt = generate_resumption_prompt(digest)
    
    assert "Code blocks" in prompt or "snippet" in prompt.lower()


def test_resumption_prompt_with_questions():
    """Test that open questions are highlighted."""
    summary = Summary(
        brief="Planning database schema",
        decisions=["Use PostgreSQL"],
        actions=["Create migration"],
        open_questions=["Should we use UUID or integer IDs?", "What about indexing strategy?"],
        constraints=["Must support 10k users"],
    )
    
    digest = ThreadDigest(
        thread=ThreadMetadata(id="test-q"),
        messages=[],
        summary=summary,
    )
    
    prompt = generate_resumption_prompt(digest)
    
    assert "Open Questions" in prompt or "Blockers" in prompt
    assert "UUID or integer IDs" in prompt
    assert "indexing strategy" in prompt


def test_resumption_prompt_suggests_next_steps():
    """Test that next steps are intelligently suggested."""
    summary = Summary(
        brief="API design discussion",
        decisions=["REST API with JWT auth"],
        actions=["Implement /login endpoint", "Add rate limiting"],
        open_questions=["Which rate limit: 100 or 1000 req/min?"],
        constraints=["Must be backwards compatible"],
    )
    
    digest = ThreadDigest(
        thread=ThreadMetadata(id="test-next"),
        messages=[],
        summary=summary,
    )
    
    prompt = generate_resumption_prompt(digest)
    
    assert "Suggested Next Steps" in prompt or "Next Steps" in prompt
    assert "question" in prompt.lower() or "resolve" in prompt.lower()


def test_extract_file_mentions():
    """Test file path extraction from messages."""
    messages = [
        Message(order=1, role="user", content="Update `src/main.py` please", tags=[]),
        Message(order=2, role="assistant", content="Also check tests/test_main.py", tags=[]),
        Message(order=3, role="user", content="And the config.yaml file", tags=[]),
    ]
    
    files = _extract_file_mentions(messages)
    
    assert "src/main.py" in files
    assert "tests/test_main.py" in files
    assert "config.yaml" in files


def test_extract_code_snippets():
    """Test code block extraction."""
    messages = [
        Message(
            order=1,
            role="assistant",
            content="```python\nprint('hello')\n```",
            tags=["code"],
        ),
        Message(
            order=2,
            role="assistant",
            content="```javascript\nconsole.log('world');\n```",
            tags=["code"],
        ),
        Message(order=3, role="user", content="No code here", tags=[]),
    ]
    
    snippets = _extract_code_snippets(messages)
    
    assert len(snippets) == 2
    assert "print('hello')" in snippets[0]
    assert "console.log('world')" in snippets[1]


def test_suggest_next_steps_with_questions():
    """Test next step suggestions prioritize questions."""
    summary = Summary(
        brief="Test",
        decisions=[],
        actions=["Do something"],
        open_questions=["What framework?"],
        constraints=[],
    )
    
    steps = _suggest_next_steps(summary)
    
    assert len(steps) > 0
    assert any("question" in step.lower() for step in steps)


def test_suggest_next_steps_with_actions():
    """Test next step suggestions include actions."""
    summary = Summary(
        brief="Test",
        decisions=["Use FastAPI"],
        actions=["Install FastAPI", "Create routes"],
        open_questions=[],
        constraints=[],
    )
    
    steps = _suggest_next_steps(summary)
    
    assert len(steps) > 0
    assert any("action" in step.lower() for step in steps)


def test_suggest_next_steps_with_decisions_only():
    """Test suggestions when only decisions exist."""
    summary = Summary(
        brief="Test",
        decisions=["Use TypeScript"],
        actions=[],
        open_questions=[],
        constraints=[],
    )
    
    steps = _suggest_next_steps(summary)
    
    assert len(steps) > 0
    assert any("implement" in step.lower() or "decision" in step.lower() for step in steps)


def test_resumption_prompt_integration():
    """Integration test with real transcript parsing."""
    transcript = """
User:
I need to build a REST API for a todo app. Should we use FastAPI or Flask?

Assistant:
Let's go with FastAPI. It's modern and has great async support.

User:
Perfect! We need to create models for tasks with title, description, and status.
Assistant:
I'll create a Pydantic model for that.
"""
    
    messages = parse_transcript(transcript)
    signals = extract_signals(messages)
    summary = generate_summary(messages, signals=signals)
    
    digest = ThreadDigest(
        thread=ThreadMetadata(id="integration-test", title=infer_title(messages)),
        messages=messages,
        summary=summary,
    )
    
    prompt = generate_resumption_prompt(digest)
    
    # Verify structure
    assert "# Context from Previous Session" in prompt
    assert "Summary" in prompt
    assert "Suggested Next Steps" in prompt
    
    # Verify content extraction
    assert "FastAPI" in prompt or "API" in prompt
    assert len(prompt) > 100  # Should be substantial
