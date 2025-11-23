import argparse
import os
import sys
import subprocess
import shlex
from google import genai
from google.genai import types

# --- CONFIGURATION ---
WORK_DIR = os.path.abspath("./playground")
MODEL_ID = "gemini-3-pro-preview"
THINKING_LEVEL_CHOICES = {
    "LOW": types.ThinkingLevel.LOW,
    "HIGH": types.ThinkingLevel.HIGH,
    "AUTO": types.ThinkingLevel.THINKING_LEVEL_UNSPECIFIED,
}

# Ensure workspace exists
os.makedirs(WORK_DIR, exist_ok=True)

# --- TOOLS (The Hands) ---


def validate_path(path: str) -> str:
    full_path = os.path.abspath(os.path.join(WORK_DIR, path))
    if not full_path.startswith(WORK_DIR):
        raise ValueError(f"SECURITY ALERT: Access denied to {path}. Stay in {WORK_DIR}")
    return full_path


def run_shell(command: str) -> str:
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
    except Exception as e:
        return f"Error executing command: {e}"


def write_file(file_path: str, contents: str) -> str:
    try:
        safe_path = validate_path(file_path)
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(contents)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error writing file: {e}"


def read_file(file_path: str) -> str:
    try:
        safe_path = validate_path(file_path)
        if not os.path.exists(safe_path):
            return "Error: File not found."
        with open(safe_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


tools_schema = [
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

tool_functions = {
    "run_shell": run_shell,
    "write_file": write_file,
    "read_file": read_file,
}

# --- AGENT LOOP (The Brain) ---


def build_generation_config(
    thinking_level: types.ThinkingLevel,
) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        tools=[types.Tool(function_declarations=tools_schema)],
        thinking_config=types.ThinkingConfig(thinking_level=thinking_level),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Gemini CLI agent.")
    parser.add_argument(
        "--thinking-level",
        choices=THINKING_LEVEL_CHOICES.keys(),
        default="LOW",
        help="Gemini thinking level to use for all requests (LOW, HIGH, AUTO).",
    )
    return parser.parse_args()


def run_agent(thinking_level: types.ThinkingLevel):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Please set GEMINI_API_KEY environment variable.")
        return

    client = genai.Client(api_key=api_key)

    system_prompt = f"""
You are an expert Linux CLI Agent working inside the directory: {WORK_DIR}.
You can run shell commands, write code, and read files.

GUIDELINES:
1. When asked to write code, first write the file, then try to run it to verify it works.
2. If a command fails, read the error, fix the code/command, and try again.
3. Be concise.
"""

    print(f"--- 🐧 Linux CLI Agent (Gemini 3 Pro) started in {WORK_DIR} ---")
    print(
        "Type 'exit' to quit. The agent will ask for approval before running shell commands."
    )

    while True:
        try:
            user_msg = input("\nUser: ")
            if user_msg.lower() in ["exit", "quit"]:
                break

            # Send prompt to model
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=user_msg,
                config=build_generation_config(thinking_level),
            )

            # If the model returns tool calls
            while getattr(response, "function_calls", None):
                for tool_call in response.function_calls:
                    args = tool_call.args
                    tool_name = tool_call.name

                    if tool_name == "run_shell":
                        cmd = args["command"]
                        print(f"\n⚠️  Agent wants to run: '{cmd}'")
                        approval = input("Allow? (y/n): ")
                        if approval.lower() != "y":
                            print("❌ Denied.")
                            result = "User denied permission to execute this command."
                            response = client.models.generate_content(
                                model=MODEL_ID,
                                contents="",
                                config=build_generation_config(thinking_level),
                                # feed the tool result back via function call interface
                                # Note: SDK may differ — adapt accordingly
                                # Here we assume we can simulate the response via a function result
                                # (SDK-specific behaviour)
                            )
                            continue

                    print(f"⚙️  Running {tool_name}...")
                    try:
                        func = tool_functions[tool_name]
                        func_result = func(**args)
                        output_str = str(func_result)
                    except Exception as e:
                        output_str = f"Error: {str(e)}"

                    # Feed result back to model
                    response = client.models.generate_content(
                        model=MODEL_ID,
                        contents=output_str,
                        config=build_generation_config(thinking_level),
                    )

            # Final answer from model
            if response.text:
                print(f"\nAgent: {response.text}")

        except KeyboardInterrupt:
            print("\nExiting.")
            break
        except Exception as e:
            print(f"\nError: {e}")
            break


if __name__ == "__main__":
    args = parse_args()
    selected_level = THINKING_LEVEL_CHOICES[args.thinking_level]
    run_agent(selected_level)
