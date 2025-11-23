"""Run the Textual UI in a browser via textual-serve."""

from __future__ import annotations

import argparse

from textual_serve.server import Server

from gemini_agent.config import DEFAULT_THINKING_LEVEL_KEY, THINKING_LEVEL_CHOICES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Serve the Gemini CLI agent UI over HTTP using textual-serve"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host interface to bind (default: %(default)s)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind for the HTTP server (default: %(default)s)",
    )
    parser.add_argument(
        "--thinking-level",
        choices=sorted(THINKING_LEVEL_CHOICES),
        default=DEFAULT_THINKING_LEVEL_KEY,
        help="Gemini thinking level to pass through to main.py",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    command = f"python main.py --thinking-level {args.thinking_level}"
    server = Server(command, host=args.host, port=args.port)
    server.serve()


if __name__ == "__main__":
    main()
