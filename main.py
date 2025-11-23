"""Entry point for the Gemini CLI agent with a Textual UI."""

from __future__ import annotations

import argparse
import os
from typing import Optional

from gemini_agent.agent import Agent
from gemini_agent.config import (
    DEFAULT_THINKING_LEVEL_KEY,
    THINKING_LEVEL_CHOICES,
    resolve_thinking_level,
)
from gemini_agent.ui import run_ui


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gemini CLI Agent with Textual UI")
    parser.add_argument(
        "--thinking-level",
        choices=sorted(THINKING_LEVEL_CHOICES.keys()),
        default=DEFAULT_THINKING_LEVEL_KEY,
        help="Gemini thinking level to use for all interactions.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Please set GEMINI_API_KEY environment variable.")
        return 1

    agent = Agent(
        api_key=api_key,
        thinking_level=resolve_thinking_level(args.thinking_level),
    )
    run_ui(agent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
