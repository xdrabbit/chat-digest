# chat-digest

CLI tool to ingest markdown chat transcripts, emit structured JSON, and generate a concise handoff brief. Supports offline rule-based mode or optional local LLM via Ollama (e.g., `smollm2:latest`).

## Quickstart

1) Install dependencies (editable dev):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

2) Run on a markdown transcript:

```bash
chat-digest mic_audio_settings.md --json out.json --brief brief.md
```

3) Use Ollama for the brief (requires local Ollama and the model pulled):

```bash
ollama pull smollm2:latest
chat-digest mic_audio_settings.md --json out.json --brief brief.md --llm smollm2:latest
```

## CLI options

```bash
chat-digest PATH [--json OUT] [--brief OUT] [--llm MODEL] [--max-brief-words N] [--schema-version 1]
```

- `--llm MODEL`: use a local Ollama model for summary refinement (default: disabled).
- `--json OUT`: write structured JSON to file (otherwise prints to stdout).
- `--brief OUT`: write brief to file (otherwise prints to stdout).
- `--max-brief-words N`: length cap for the brief (default 180).

## What you get

- Parsed turns with roles (`user`, `assistant`, `system`, `unknown`).
- Tags for decisions, actions, questions, and code blocks.
- Rule-based extractive brief; optional LLM-refined brief.

## Tests

```bash
pytest
```
