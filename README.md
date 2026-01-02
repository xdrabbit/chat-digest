# chat-digest

CLI tool to ingest markdown chat transcripts and generate structured digests with advanced context preservation. Supports offline rule-based mode or optional local LLM via Ollama.

## Features ✨

- **📝 Resumption Prompts**: Ready-to-paste context for continuing conversations
- **💻 Code Extraction**: Track code blocks with language, context, and file associations
- **⭐ Importance Scoring**: Filter noise, prioritize valuable content
- **📊 Multi-Format Output**: Context cards, detailed briefs, Slack summaries, markdown reports
- **⏱️ Temporal Analysis**: Timeline tracking with supersession detection
- **🔍 Entity Extraction**: Track dependencies, APIs, configs, people, topics
- **🔄 Incremental Updates**: Append new messages to existing digests

## Quickstart

1) Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

2) Basic usage:

```bash
chat-digest transcript.md --json out.json --brief brief.md
```

3) Generate resumption prompt:

```bash
chat-digest transcript.md --resume resume.md
```

4) Multi-format output:

```bash
chat-digest transcript.md --all-formats ./outputs/
```

5) With LLM refinement:

```bash
ollama pull smollm2:latest
chat-digest transcript.md --llm smollm2:latest --brief brief.md
```

## CLI Options

```bash
chat-digest PATH [OPTIONS]
```

**Output Options:**
- `--json OUT`: Structured JSON digest
- `--brief OUT`: Concise summary
- `--resume OUT`: Resumption prompt for new chat sessions
- `--format OUT`: Custom format output (use with `--format-type`)
- `--format-type TYPE`: Format type: `context_card`, `detailed`, `slack`, `markdown`
- `--all-formats DIR`: Generate all formats in directory

**Processing Options:**
- `--llm MODEL`: Ollama model for summary refinement (e.g., `smollm2:latest`)
- `--max-brief-words N`: Word limit for brief (default: 180)

## What You Get

### Core Features
- Parsed messages with roles (`user`, `assistant`, `system`)
- Tags for decisions, actions, questions, code blocks
- Rule-based extractive summaries
- Optional LLM-refined summaries

### Advanced Features
- **Code Tracking**: Language detection, file associations, latest versions
- **Importance Scoring**: 0-10 scoring, noise filtering, smart prioritization
- **Timeline Analysis**: Event tracking, supersession detection, conversation phases
- **Entity Extraction**: Dependencies, APIs, configurations, people, topics
- **Incremental Updates**: Append to existing digests without reprocessing

### Output Formats
- **Context Cards**: Ultra-compressed (<100 words) for quick handoffs
- **Detailed Briefs**: Comprehensive with all signals and code summary
- **Slack Summaries**: Emoji-rich, platform-optimized
- **Markdown Reports**: Full documentation with table of contents
- **Resumption Prompts**: Ready-to-paste context for continuing work

## Tests

```bash
pytest  # 104 tests, all passing
```

## Development

**Python Version**: 3.11+  
**Test Coverage**: 104 tests across 7 feature modules  
**Repository**: [github.com/xdrabbit/chat-digest](https://github.com/xdrabbit/chat-digest)
