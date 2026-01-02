"""Enhanced code extraction and preservation utilities."""

from __future__ import annotations

import re
from typing import List, Optional

from .schemas import Message


class CodeBlock:
    """Represents an extracted code block with metadata."""
    
    def __init__(
        self,
        content: str,
        language: Optional[str] = None,
        context: Optional[str] = None,
        message_order: Optional[int] = None,
    ):
        self.content = content.strip()
        self.language = language or "text"
        self.context = context  # Surrounding text for context
        self.message_order = message_order
    
    def __repr__(self) -> str:
        lang_display = f" ({self.language})" if self.language else ""
        return f"<CodeBlock{lang_display}: {len(self.content)} chars>"
    
    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "language": self.language,
            "context": self.context,
            "message_order": self.message_order,
        }


def extract_code_blocks(messages: List[Message]) -> List[CodeBlock]:
    """
    Extract all code blocks from messages with metadata.
    
    Returns a list of CodeBlock objects with language, context, and position.
    """
    blocks = []
    
    # Pattern to match code blocks with optional language specifier
    code_pattern = re.compile(r'```(\w+)?\n(.*?)```', re.DOTALL)
    
    for msg in messages:
        if "code" not in msg.tags:
            continue
        
        # Extract context (text before the code block)
        lines = msg.content.split('\n')
        context_lines = []
        
        for match in code_pattern.finditer(msg.content):
            language = match.group(1)
            code_content = match.group(2)
            
            # Find context: text before this code block
            start_pos = match.start()
            context_text = msg.content[:start_pos].strip()
            
            # Get last sentence or line as context
            if context_text:
                context_sentences = re.split(r'[.!?]\s+', context_text)
                context = context_sentences[-1] if context_sentences else context_text[:100]
            else:
                context = None
            
            blocks.append(CodeBlock(
                content=code_content,
                language=language,
                context=context,
                message_order=msg.order,
            ))
    
    return blocks


def extract_latest_code_by_file(messages: List[Message]) -> dict[str, CodeBlock]:
    """
    Extract the most recent version of code for each file mentioned.
    
    Returns a dict mapping filename -> CodeBlock for the latest version.
    """
    file_code_map: dict[str, CodeBlock] = {}
    
    # Pattern to detect file mentions near code blocks
    file_mention_pattern = re.compile(
        r'(?:file|create|update|edit|modify)?\s*[`"]?([a-zA-Z0-9_/\-\.]+\.(py|js|ts|json|yaml|yml|toml|md|txt|sh|go|rs|java|cpp|c|h))[`"]?',
        re.IGNORECASE
    )
    
    blocks = extract_code_blocks(messages)
    
    for block in blocks:
        # Try to find associated filename from context
        if block.context:
            match = file_mention_pattern.search(block.context)
            if match:
                filename = match.group(1)
                # Keep the latest version (higher message_order)
                if filename not in file_code_map or (
                    block.message_order and 
                    file_code_map[filename].message_order and
                    block.message_order > file_code_map[filename].message_order
                ):
                    file_code_map[filename] = block
    
    return file_code_map


def format_code_block(block: CodeBlock, include_context: bool = True) -> str:
    """
    Format a code block for display in markdown.
    
    Args:
        block: The CodeBlock to format
        include_context: Whether to include context text above the code
    
    Returns:
        Formatted markdown string
    """
    parts = []
    
    if include_context and block.context:
        parts.append(f"*{block.context}*\n")
    
    parts.append(f"```{block.language}")
    parts.append(block.content)
    parts.append("```")
    
    return "\n".join(parts)


def get_code_summary(messages: List[Message]) -> dict:
    """
    Generate a summary of all code in the conversation.
    
    Returns:
        Dict with statistics and categorized code blocks
    """
    blocks = extract_code_blocks(messages)
    file_map = extract_latest_code_by_file(messages)
    
    # Count by language
    language_counts: dict[str, int] = {}
    for block in blocks:
        lang = block.language or "text"
        language_counts[lang] = language_counts.get(lang, 0) + 1
    
    return {
        "total_blocks": len(blocks),
        "unique_files": len(file_map),
        "languages": language_counts,
        "files": {filename: block.to_dict() for filename, block in file_map.items()},
        "all_blocks": [block.to_dict() for block in blocks],
    }
