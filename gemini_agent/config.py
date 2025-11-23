"""Shared configuration for the Gemini CLI agent project."""

from __future__ import annotations

import os
from google.genai import types

WORK_DIR = os.path.abspath("./playground")
MODEL_ID = "gemini-3-pro-preview"
DEFAULT_THINKING_LEVEL_KEY = "LOW"

THINKING_LEVEL_CHOICES = {
    "LOW": types.ThinkingLevel.LOW,
    "HIGH": types.ThinkingLevel.HIGH,
    "AUTO": types.ThinkingLevel.THINKING_LEVEL_UNSPECIFIED,
}

os.makedirs(WORK_DIR, exist_ok=True)


def resolve_thinking_level(key: str) -> types.ThinkingLevel:
    """Convert a CLI-provided key into the matching ThinkingLevel enum."""

    normalized = key.upper()
    try:
        return THINKING_LEVEL_CHOICES[normalized]
    except KeyError as exc:  # pragma: no cover - defensive coding
        raise ValueError(f"Unsupported thinking level: {key}") from exc
