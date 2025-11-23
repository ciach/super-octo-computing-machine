# Gemini CLI Agent with Textual UI

A sandboxed developer assistant that uses Google Gemini to plan actions, call tools (shell, read/write files), and surface results through a Textual terminal UI. It keeps all file operations within `./playground` to avoid accidental edits outside the workspace.

## Features

- Modular agent with tool routing (shell, read_file, write_file)
- Textual-based UI showing conversation history, tool prompts, and outputs
- User approval gating for shell commands
- Configurable thinking levels mapped to Gemini ADK thinking modes
- Simple sandbox (`./playground`) for generated files and commands

## Requirements

- Python 3.12+
- `pip install -r requirements.txt` (ensure `google-genai`, `textual`, etc.)
- Google Gemini API key available via the `GEMINI_API_KEY` environment variable

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY="your-key"
python main.py --thinking-level LOW
```

## Thinking Levels

`main.py` accepts `--thinking-level` with values from `gemini_agent.config.THINKING_LEVEL_CHOICES` (`LOW`, `HIGH`, `AUTO`). The selected value feeds into the Gemini generation config so you can trade off reasoning depth vs. speed.

## Tools

| Tool       | Description                                | Confirmation |
|------------|--------------------------------------------|--------------|
| run_shell  | Executes a shell command inside playground | Yes          |
| read_file  | Reads file contents (optional `num_lines`)  | No           |
| write_file | Writes contents to a file                  | No           |

## Workflow

1. Launch the UI (`python main.py`).
2. Type natural-language instructions (e.g., "list python files" or "create app.py").
3. When the agent wants to run a command, approve or deny in the UI.
4. Tool outputs appear inline so you can verify each action.

## Development Notes

- All file operations stay inside `./playground` (created automatically).
- The codebase is structured under `gemini_agent/` for config, tools, agent logic, and UI.
- Use `black .` and `ruff .` (if installed) before committing changes.

## Future Work

- Complete migration to Google ADK agents for fully managed tool confirmation and streaming.
- Add tests covering tool sandboxing and UI flows.
