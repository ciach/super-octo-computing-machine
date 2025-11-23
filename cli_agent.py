import os
import sys
import subprocess
import shlex
from google import genai
from google.genai import types

# --- CONFIGURATION ---
# The agent will be LOCKED into this directory.
WORK_DIR = os.path.abspath("./playground")
MODEL_ID = "gemini-3-pro-preview"  # Or "gemini-1.5-pro"

# Ensure workspace exists
os.makedirs(WORK_DIR, exist_ok=True)

# --- 1. SAFE TOOLS (The Hands) ---


def validate_path(path: str) -> str:
    """Ensures the path is inside the WORK_DIR sandbox."""
    # Resolve relative paths (e.g., "../") to absolute paths
    full_path = os.path.abspath(os.path.join(WORK_DIR, path))
    if not full_path.startswith(WORK_DIR):
        raise ValueError(f"SECURITY ALERT: Access denied to {path}. Stay in {WORK_DIR}")
    return full_path


def run_shell(command: str) -> str:
    """Executes a shell command in the sandbox directory.

    Args:
        command: The terminal command to run (e.g., 'ls -la', 'pip install flask')
    """
    # Security: We will ask the user for permission BEFORE running this in the main loop.
    # This function just executes what was approved.
    try:
        # We use shell=True to allow pipes (|) and redirects (>)
        # This is risky without the human approval step we added below!
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORK_DIR,
            capture_output=True,
            text=True,
            timeout=30,  # Prevent hanging commands
        )

        # Combine stdout and stderr so the model sees errors
        output = result.stdout + "\n" + result.stderr
        return output.strip() or "Command executed successfully (no output)."
    except subprocess.TimeoutExpired:
        return "Error: Command timed out."
    except Exception as e:
        return f"Error executing command: {e}"


def write_file(file_path: str, contents: str) -> str:
    """Writes code or text to a file."""
    try:
        safe_path = validate_path(file_path)
        with open(safe_path, "w") as f:
            f.write(contents)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error writing file: {e}"


def read_file(file_path: str) -> str:
    """Reads a file."""
    try:
        safe_path = validate_path(file_path)
        if not os.path.exists(safe_path):
            return "Error: File not found."
        with open(safe_path, "r") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


# Tool Definitions
tools_schema = [
    {
        "name": "run_shell",
        "description": "Executes a Linux shell command. Use this to list files, run python scripts, install packages, or use git.",
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
        "description": "Writes content to a file. Overwrites if exists.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Filename (relative to workspace).",
                },
                "contents": {"type": "string", "description": "The content to write."},
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
                "file_path": {"type": "string", "description": "Filename to read."}
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

# --- 2. THE AGENT LOOP (The Brain) ---


def run_agent():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Please set GEMINI_API_KEY environment variable.")
        return

    client = genai.Client(api_key=api_key)

    # System instruction to set the persona
    system_prompt = f"""
    You are an expert Linux CLI Agent working inside the directory: {WORK_DIR}.
    You can run shell commands, write code, and read files.
    
    GUIDELINES:
    1. When asked to write code, first write the file, then try to run it to verify it works.
    2. If a command fails, read the error, fix the code/command, and try again.
    3. Be concise.
    """

    chat = client.chats.create(
        model=MODEL_ID,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[types.Tool(function_declarations=tools_schema)],
        ),
    )

    print(f"--- 🐧 Linux CLI Agent Started in {WORK_DIR} ---")
    print(
        "Type 'exit' to quit. The agent will ask for approval before running shell commands."
    )

    while True:
        try:
            user_msg = input("\nUser: ")
            if user_msg.lower() in ["exit", "quit"]:
                break

            response = chat.send_message(user_msg)

            # Handle the multi-turn loop (Model -> Tool -> Model...)
            while response.function_calls:
                for tool_call in response.function_calls:
                    args = tool_call.args
                    tool_name = tool_call.name

                    # --- SAFETY CHECK POINT ---
                    if tool_name == "run_shell":
                        cmd = args["command"]
                        print(f"\n⚠️  Agent wants to run: \033[1;33m{cmd}\033[0m")
                        approval = input("Allow? (y/n): ")
                        if approval.lower() != "y":
                            print("❌ Denied.")
                            # Feed the rejection back to the model so it knows
                            result = "User denied permission to execute this command."
                            response = chat.send_message(
                                [
                                    types.Part.from_function_response(
                                        name=tool_name, response={"result": result}
                                    )
                                ]
                            )
                            continue  # Skip execution, go to next loop

                    # Execute Tool
                    print(f"⚙️  Running {tool_name}...")
                    try:
                        func = tool_functions[tool_name]
                        func_result = func(**args)
                        output_str = str(func_result)
                    except Exception as e:
                        output_str = f"Error: {str(e)}"

                    # Send result back to model
                    response = chat.send_message(
                        [
                            types.Part.from_function_response(
                                name=tool_name, response={"result": output_str}
                            )
                        ]
                    )

            # Final text response
            if response.text:
                print(f"\nAgent: {response.text}")

        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    run_agent()
