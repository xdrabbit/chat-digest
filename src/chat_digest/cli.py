from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from uuid import uuid4

import typer

from .chronicle import export_to_chronicle
from .formats import generate_all_formats, generate_context_card
from .parser import infer_title, parse_transcript
from .resumption import generate_resumption_prompt
from .schemas import ThreadDigest, ThreadMetadata
from .summarize import extract_signals, generate_summary

app = typer.Typer(add_completion=False, help="Digest markdown chat transcripts into JSON + brief")


@app.command()
def main(
    path: Path = typer.Argument(..., exists=True, readable=True, help="Path to markdown transcript"),
    json_out: Optional[Path] = typer.Option(None, "--json", help="Path to write JSON output"),
    brief_out: Optional[Path] = typer.Option(None, "--brief", help="Path to write brief output"),
    resume_out: Optional[Path] = typer.Option(None, "--resume", help="Path to write resumption prompt"),
    format_out: Optional[Path] = typer.Option(None, "--format", help="Path to write formatted output (specify type with --format-type)"),
    format_type: str = typer.Option("detailed", "--format-type", help="Format type: context_card, detailed, slack, markdown"),
    all_formats_dir: Optional[Path] = typer.Option(None, "--all-formats", help="Directory to write all format types"),
    chronicle_out: Optional[Path] = typer.Option(None, "--chronicle-export", help="Path to write Chronicle CSV export"),
    chronicle_timeline: str = typer.Option("Legal", "--chronicle-timeline", help="Chronicle timeline name"),
    chronicle_min_importance: float = typer.Option(5.0, "--chronicle-min-importance", help="Minimum importance score for Chronicle export"),
    chronicle_patterns: bool = typer.Option(False, "--chronicle-patterns", help="Include detected patterns as Chronicle events"),
    byte_out: Optional[Path] = typer.Option(None, "--byte", help="Path to write the Amuse-bouche (Perfect BYTE) tactical snapshot"),
    llm: Optional[str] = typer.Option(None, "--llm", help="Ollama model name (e.g., smollm2:latest)"),
    max_brief_words: int = typer.Option(180, help="Word limit for brief"),
    schema_version: int = typer.Option(1, help="Schema version to embed in metadata"),
) -> None:
    """Entry point for chat-digest CLI."""
    text = path.read_text(encoding="utf-8")
    messages = parse_transcript(text, filename=path.name)

    if not messages:
        typer.secho("No messages parsed from transcript", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    
    # Score message importance for Chronicle export and filtering
    from .importance import score_message_importance
    for msg in messages:
        msg.importance_score = score_message_importance(msg)

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

    if resume_out:
        resumption_prompt = generate_resumption_prompt(digest)
        resume_out.write_text(resumption_prompt, encoding="utf-8")
        typer.secho(f"\n✓ Resumption prompt written to {resume_out}", fg=typer.colors.GREEN)

    if format_out:
        from .formats import generate_context_card, generate_detailed_brief, generate_slack_summary, generate_markdown_report
        
        format_map = {
            "context_card": generate_context_card,
            "detailed": generate_detailed_brief,
            "slack": generate_slack_summary,
            "markdown": generate_markdown_report,
        }
        
        if format_type not in format_map:
            typer.secho(f"Unknown format type: {format_type}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        
        formatted = format_map[format_type](digest)
        format_out.write_text(formatted, encoding="utf-8")
        typer.secho(f"\n✓ {format_type} format written to {format_out}", fg=typer.colors.GREEN)

    if all_formats_dir:
        all_formats_dir.mkdir(parents=True, exist_ok=True)
        all_formats = generate_all_formats(digest)
        
        for fmt_name, content in all_formats.items():
            out_path = all_formats_dir / f"{fmt_name}.md"
            out_path.write_text(content, encoding="utf-8")
        
        typer.secho(f"\n✓ All formats written to {all_formats_dir}/", fg=typer.colors.GREEN)
    
    if chronicle_out:
        event_count = export_to_chronicle(
            digest,
            chronicle_out,
            timeline_name=chronicle_timeline,
            min_importance=chronicle_min_importance,
            include_patterns=chronicle_patterns,
            llm_model=llm,
        )
        typer.secho(
            f"\n✓ Chronicle export written to {chronicle_out} ({event_count} events)",
            fg=typer.colors.GREEN
        )

    if byte_out:
        from .patterns import detect_all_patterns
        from .amuse_bouche import synthesize_byte
        
        # Extract unique actors from messages
        actors = sorted(list(set(msg.role for msg in messages if msg.role != "unknown")))
        
        # Detect patterns for synthesis
        patterns = detect_all_patterns(messages)
        
        # Create the perfect byte
        byte = synthesize_byte(summary, patterns, actors)
        byte_md = byte.to_markdown()
        
        byte_out.write_text(byte_md, encoding="utf-8")
        typer.secho(f"\n✓ Amuse-bouche (Perfect BYTE) written to {byte_out}", fg=typer.colors.MAGENTA, bold=True)


if __name__ == "__main__":
    app()
