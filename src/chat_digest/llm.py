"""Minimal Ollama client for optional local LLM summarization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests


@dataclass
class OllamaConfig:
    model: str = "smollm2:latest"
    endpoint: str = "http://localhost:11434"
    timeout: int = 30
    max_tokens: int = 512


class OllamaClient:
    def __init__(self, config: Optional[OllamaConfig] = None):
        self.config = config or OllamaConfig()

    def generate(self, prompt: str, *, model: Optional[str] = None, max_tokens: Optional[int] = None) -> str:
        cfg = self.config
        payload = {
            "model": model or cfg.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens or cfg.max_tokens},
        }
        url = f"{cfg.endpoint}/api/generate"
        response = requests.post(url, json=payload, timeout=cfg.timeout)
        response.raise_for_status()
        data = response.json()
        return (data.get("response") or "").strip()
