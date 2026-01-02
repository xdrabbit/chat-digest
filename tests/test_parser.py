from pathlib import Path

from chat_digest.parser import infer_title, parse_transcript
from chat_digest.summarize import build_rule_based_brief, extract_signals


def test_parse_transcript_sample():
    text = Path("tests/fixtures/mic_audio_settings.md").read_text(encoding="utf-8")
    messages = parse_transcript(text)

    assert len(messages) >= 3
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert infer_title(messages)


def test_brief_generation_capped_words():
    text = Path("tests/fixtures/mic_audio_settings.md").read_text(encoding="utf-8")
    messages = parse_transcript(text)
    signals = extract_signals(messages)
    brief = build_rule_based_brief(messages, signals, max_brief_words=50)

    assert len(brief.split()) <= 51  # allow trailing ellipsis token
    assert "Context:" in brief
