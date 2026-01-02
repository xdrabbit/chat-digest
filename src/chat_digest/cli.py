from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from uuid import uuid4

import typer

from .parser import infer_title, parse_transcript
from .schemas import ThreadDigest, ThreadMetadata
from .summarize import extract_signals, generate_summary

app = typer.Typer(add_completion=False, help="Digest markdown chat transcripts into JSON + brief")


@app.command()
def main(
    path: Path = typer.Argument(..., exists=True, readable=True, help="Path to markdown transcript"),
    json_out: Optional[Path] = typer.Option(None, "--json", help="Path to write JSON output"),
    brief_out: Optional[Path] = typer.Option(None, "--brief", help="Path to write brief output"),
    llm: Optional[str] = typer.Option(None, "--llm", help="Ollama model name (e.g., smollm2:latest)"),
    max_brief_words: int = typer.Option(180, help="Word limit for brief"),
    schema_version: int = typer.Option(1, help="Schema version to embed in metadata"),
) -> None:
    """Entry point for chat-digest CLI."""
    text = path.read_text(encoding="utf-8")
    messages = parse_transcript(text)

    if not messages:
        typer.secho("No messages parsed from transcript", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    signals = extract_signals(messages)
    summary = generate_summary(messages, signals=signals, llm_model=llm, max_brief_words=max_brief_words)

    digest = ThreadDigest(
        thread=ThreadMetadata(
            id=str(uuid4()),
            title=infer_title(messages),
            source_file=str(path),
            schema_version=schema_version,
        ),
        messages=messages,
        summary=summary,
    )

    payload = digest.model_dump()

    if json_out:
        json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    else:
        typer.echo(json.dumps(payload, indent=2))

    if brief_out:
        brief_out.write_text(summary.brief, encoding="utf-8")
    else:
        typer.echo("\nBrief:\n" + summary.brief)


if __name__ == "__main__":
    app()
