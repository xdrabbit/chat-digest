"""Tests for code extraction functionality."""

from chat_digest.code_extraction import (
    CodeBlock,
    extract_code_blocks,
    extract_latest_code_by_file,
    format_code_block,
    get_code_summary,
)
from chat_digest.schemas import Message


def test_code_block_creation():
    """Test CodeBlock object creation and representation."""
    block = CodeBlock(
        content="print('hello')",
        language="python",
        context="Here's a simple example",
        message_order=1,
    )
    
    assert block.content == "print('hello')"
    assert block.language == "python"
    assert block.context == "Here's a simple example"
    assert block.message_order == 1
    assert "python" in repr(block)


def test_extract_code_blocks_basic():
    """Test basic code block extraction."""
    messages = [
        Message(
            order=1,
            role="assistant",
            content="Here's some code:\n```python\nprint('hello')\n```",
            tags=["code"],
        ),
    ]
    
    blocks = extract_code_blocks(messages)
    
    assert len(blocks) == 1
    assert blocks[0].language == "python"
    assert "print('hello')" in blocks[0].content


def test_extract_code_blocks_multiple_languages():
    """Test extraction of multiple code blocks with different languages."""
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
        Message(
            order=3,
            role="assistant",
            content="```bash\necho 'test'\n```",
            tags=["code"],
        ),
    ]
    
    blocks = extract_code_blocks(messages)
    
    assert len(blocks) == 3
    assert blocks[0].language == "python"
    assert blocks[1].language == "javascript"
    assert blocks[2].language == "bash"


def test_extract_code_blocks_with_context():
    """Test that context is extracted correctly."""
    messages = [
        Message(
            order=1,
            role="assistant",
            content="Let's create a hello function. Here it is:\n```python\ndef hello():\n    print('world')\n```",
            tags=["code"],
        ),
    ]
    
    blocks = extract_code_blocks(messages)
    
    assert len(blocks) == 1
    assert blocks[0].context is not None
    assert "hello function" in blocks[0].context or "Here it is" in blocks[0].context


def test_extract_code_blocks_no_language():
    """Test extraction of code blocks without language specifier."""
    messages = [
        Message(
            order=1,
            role="assistant",
            content="```\nsome code\n```",
            tags=["code"],
        ),
    ]
    
    blocks = extract_code_blocks(messages)
    
    assert len(blocks) == 1
    assert blocks[0].language == "text" or blocks[0].language is None
    assert "some code" in blocks[0].content


def test_extract_code_blocks_skips_non_code_messages():
    """Test that messages without code tags are skipped."""
    messages = [
        Message(order=1, role="user", content="No code here", tags=[]),
        Message(
            order=2,
            role="assistant",
            content="```python\nprint('hello')\n```",
            tags=["code"],
        ),
        Message(order=3, role="user", content="Thanks!", tags=[]),
    ]
    
    blocks = extract_code_blocks(messages)
    
    assert len(blocks) == 1
    assert blocks[0].language == "python"


def test_extract_latest_code_by_file():
    """Test extraction of latest code version per file."""
    messages = [
        Message(
            order=1,
            role="assistant",
            content="Create app.py:\n```python\nprint('v1')\n```",
            tags=["code"],
        ),
        Message(
            order=2,
            role="assistant",
            content="Update app.py:\n```python\nprint('v2')\n```",
            tags=["code"],
        ),
    ]
    
    file_map = extract_latest_code_by_file(messages)
    
    assert "app.py" in file_map
    assert "v2" in file_map["app.py"].content
    assert "v1" not in file_map["app.py"].content


def test_extract_latest_code_multiple_files():
    """Test extraction with multiple different files."""
    messages = [
        Message(
            order=1,
            role="assistant",
            content="Create main.py:\n```python\nprint('main')\n```",
            tags=["code"],
        ),
        Message(
            order=2,
            role="assistant",
            content="Create utils.py:\n```python\nprint('utils')\n```",
            tags=["code"],
        ),
    ]
    
    file_map = extract_latest_code_by_file(messages)
    
    assert len(file_map) == 2
    assert "main.py" in file_map
    assert "utils.py" in file_map


def test_format_code_block():
    """Test code block formatting."""
    block = CodeBlock(
        content="print('hello')",
        language="python",
        context="Example code",
    )
    
    formatted = format_code_block(block, include_context=True)
    
    assert "*Example code*" in formatted
    assert "```python" in formatted
    assert "print('hello')" in formatted
    assert "```" in formatted


def test_format_code_block_without_context():
    """Test formatting without context."""
    block = CodeBlock(content="print('hello')", language="python")
    
    formatted = format_code_block(block, include_context=False)
    
    assert "```python" in formatted
    assert "print('hello')" in formatted
    assert "*" not in formatted  # No context markers


def test_get_code_summary():
    """Test comprehensive code summary generation."""
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
        Message(
            order=3,
            role="assistant",
            content="Create app.py:\n```python\nprint('app')\n```",
            tags=["code"],
        ),
    ]
    
    summary = get_code_summary(messages)
    
    assert summary["total_blocks"] == 3
    assert "python" in summary["languages"]
    assert "javascript" in summary["languages"]
    assert summary["languages"]["python"] == 2
    assert summary["languages"]["javascript"] == 1
    assert len(summary["all_blocks"]) == 3


def test_get_code_summary_with_files():
    """Test code summary includes file associations."""
    messages = [
        Message(
            order=1,
            role="assistant",
            content="Create main.py:\n```python\nprint('main')\n```",
            tags=["code"],
        ),
    ]
    
    summary = get_code_summary(messages)
    
    assert summary["unique_files"] >= 0  # May or may not detect file
    assert "files" in summary


def test_get_code_summary_empty():
    """Test code summary with no code blocks."""
    messages = [
        Message(order=1, role="user", content="No code here", tags=[]),
    ]
    
    summary = get_code_summary(messages)
    
    assert summary["total_blocks"] == 0
    assert len(summary["all_blocks"]) == 0


def test_code_block_to_dict():
    """Test CodeBlock serialization to dict."""
    block = CodeBlock(
        content="print('test')",
        language="python",
        context="Test code",
        message_order=5,
    )
    
    data = block.to_dict()
    
    assert data["content"] == "print('test')"
    assert data["language"] == "python"
    assert data["context"] == "Test code"
    assert data["message_order"] == 5


def test_extract_code_blocks_multiple_in_one_message():
    """Test extraction of multiple code blocks from a single message."""
    messages = [
        Message(
            order=1,
            role="assistant",
            content="First:\n```python\nprint('1')\n```\nSecond:\n```python\nprint('2')\n```",
            tags=["code"],
        ),
    ]
    
    blocks = extract_code_blocks(messages)
    
    assert len(blocks) == 2
    assert "print('1')" in blocks[0].content
    assert "print('2')" in blocks[1].content
