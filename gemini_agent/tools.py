"""Tool implementations the Gemini agent can invoke."""

from __future__ import annotations

import os
import subprocess
from typing import Callable, Dict, List

from .config import WORK_DIR


def validate_path(path: str) -> str:
    """Ensure file operations are restricted to the configured work directory."""

    full_path = os.path.abspath(os.path.join(WORK_DIR, path))
    if not full_path.startswith(WORK_DIR):
        raise ValueError(f"SECURITY ALERT: Access denied to {path}. Stay in {WORK_DIR}")
    return full_path


def run_shell(command: str) -> str:
    """Execute a shell command within the sandboxed work directory."""

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORK_DIR,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout + "\n" + result.stderr
        return output.strip() or "Command executed successfully (no output)."
    except subprocess.TimeoutExpired:
        return "Error: Command timed out."
    except Exception as exc:  # pragma: no cover - defensive guard
        return f"Error executing command: {exc}"


def write_file(file_path: str, contents: str) -> str:
    """Write (or overwrite) a file inside the sandbox."""

    try:
        safe_path = validate_path(file_path)
        with open(safe_path, "w", encoding="utf-8") as handle:
            handle.write(contents)
        return f"Successfully wrote to {file_path}"
    except Exception as exc:  # pragma: no cover - defensive guard
        return f"Error writing file: {exc}"


def read_file(file_path: str) -> str:
    """Read a file from the sandbox, returning its contents or an error string."""

    try:
        safe_path = validate_path(file_path)
        if not os.path.exists(safe_path):
            return "Error: File not found."
        with open(safe_path, "r", encoding="utf-8") as handle:
            return handle.read()
    except Exception as exc:  # pragma: no cover - defensive guard
        return f"Error reading file: {exc}"


TOOLS_SCHEMA: List[Dict[str, object]] = [
    {
        "name": "run_shell",
        "description": "Executes a Linux shell command.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to run.",
                }
            },
            "required": ["command"],
        },
    },
    {
        "name": "write_file",
        "description": "Writes content to a file (overwrites if exists).",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Filename (relative to workspace).",
                },
                "contents": {
                    "type": "string",
                    "description": "The content to write.",
                },
            },
            "required": ["file_path", "contents"],
        },
    },
    {
        "name": "read_file",
        "description": "Reads content from a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Filename to read.",
                }
            },
            "required": ["file_path"],
        },
    },
]

TOOL_FUNCTIONS: Dict[str, Callable[..., str]] = {
    "run_shell": run_shell,
    "write_file": write_file,
    "read_file": read_file,
}
