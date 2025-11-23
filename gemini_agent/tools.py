"""Tool implementations the Gemini agent can invoke."""

from __future__ import annotations

import os
import subprocess
from typing import Dict, Optional

from .config import WORK_DIR


def validate_path(path: str) -> str:
    """Ensure file operations are restricted to the configured work directory."""

    full_path = os.path.abspath(os.path.join(WORK_DIR, path))
    if not full_path.startswith(WORK_DIR):
        raise ValueError(f"SECURITY ALERT: Access denied to {path}. Stay in {WORK_DIR}")
    return full_path


def run_shell(command: str) -> Dict[str, str]:
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
        output = (result.stdout + "\n" + result.stderr).strip()
        if not output:
            output = "Command executed successfully (no output)."
        return {"status": "success", "output": output}
    except subprocess.TimeoutExpired:
        return {"status": "error", "output": "Error: Command timed out."}
    except Exception as exc:  # pragma: no cover - defensive guard
        return {"status": "error", "output": f"Error executing command: {exc}"}


def write_file(file_path: str, contents: str) -> Dict[str, str]:
    """Write (or overwrite) a file inside the sandbox."""

    try:
        safe_path = validate_path(file_path)
        with open(safe_path, "w", encoding="utf-8") as handle:
            handle.write(contents)
        return {"status": "success", "output": f"Successfully wrote to {file_path}"}
    except Exception as exc:  # pragma: no cover - defensive guard
        return {"status": "error", "output": f"Error writing file: {exc}"}


def read_file(file_path: str, num_lines: Optional[int] = None) -> Dict[str, str]:
    """Read a file from the sandbox, optionally limiting to the first N lines."""

    try:
        safe_path = validate_path(file_path)
        if not os.path.exists(safe_path):
            return {"status": "error", "output": "Error: File not found."}
        with open(safe_path, "r", encoding="utf-8") as handle:
            data = handle.read()

        if num_lines is not None:
            if num_lines < 0:
                return {
                    "status": "error",
                    "output": "Error: num_lines must be positive.",
                }
            lines = data.splitlines()
            data = "\n".join(lines[:num_lines])

        return {"status": "success", "output": data}
    except Exception as exc:  # pragma: no cover - defensive guard
        return {"status": "error", "output": f"Error reading file: {exc}"}


# Schema and function map for backward compatibility/imports
TOOLS_SCHEMA = [
    {
        "name": "run_shell",
        "description": "Executes a shell command in sandbox directory",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to run",
                }
            },
            "required": ["command"],
        },
    },
    {
        "name": "write_file",
        "description": "Writes content to a file (sandboxed).",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Filename (relative)",
                },
                "contents": {
                    "type": "string",
                    "description": "Content to write",
                },
            },
            "required": ["file_path", "contents"],
        },
    },
    {
        "name": "read_file",
        "description": "Reads content from a file (sandboxed).",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Filename to read",
                },
                "num_lines": {
                    "type": "integer",
                    "description": "Optional limit of lines to return from the start of the file",
                    "minimum": 1,
                },
            },
            "required": ["file_path"],
        },
    },
]

TOOL_FUNCTIONS = {
    "run_shell": run_shell,
    "write_file": write_file,
    "read_file": read_file,
}
