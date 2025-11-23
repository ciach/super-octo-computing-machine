"""Shared configuration for the Gemini CLI agent project."""

from __future__ import annotations

import os

# Workspace & model configuration
WORK_DIR = os.path.abspath("./playground")
MODEL_ID = "gemini-3-pro-preview"
DEFAULT_THINKING_LEVEL_KEY = "LOW"

# Thinking level mapping for ADK (and CLI choices)
THINKING_LEVEL_MAP = {
    "LOW": "LOW",
    "HIGH": "HIGH",
    "AUTO": "THINKING_LEVEL_UNSPECIFIED",
}

# CLI-choices alias (so main.py can import THINKING_LEVEL_CHOICES)
THINKING_LEVEL_CHOICES = list(THINKING_LEVEL_MAP.keys())

# Environment variable for API key
API_KEY_ENV = "GEMINI_API_KEY"

os.makedirs(WORK_DIR, exist_ok=True)


def resolve_thinking_level(key: str) -> str:
    """Convert a CLI-provided key into the matching ADK run_config value."""

    normalized = key.upper()
    try:
        return THINKING_LEVEL_MAP[normalized]
    except KeyError as exc:  # pragma: no cover - defensive coding
        raise ValueError(f"Unsupported thinking level: {key}") from exc
