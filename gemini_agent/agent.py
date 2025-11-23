"""Gemini agent orchestration, including tool routing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

from .config import MODEL_ID, WORK_DIR
from .tools import TOOL_FUNCTIONS, TOOLS_SCHEMA


@dataclass
class PendingToolCall:
    """Metadata for a tool call that requires user approval."""

    tool_name: str
    args: Dict[str, Any]


@dataclass
class AgentReply:
    """Result returned to the UI layer after each interaction."""

    text: Optional[str] = None
    pending_tool: Optional[PendingToolCall] = None


class Agent:
    """High-level orchestrator around the Gemini client and available tools."""

    def __init__(self, api_key: str, thinking_level: types.ThinkingLevel):
        self.client = genai.Client(api_key=api_key)
        self.thinking_level = thinking_level
        self.system_prompt = (
            "You are an expert Linux CLI Agent working inside the directory: "
            f"{WORK_DIR}. You can run shell commands, write code, and read files.\n\n"
            "GUIDELINES:\n"
            "1. When asked to write code, first write the file, then try to run it to verify it works.\n"
            "2. If a command fails, read the error, fix the code/command, and try again.\n"
            "3. Be concise."
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def handle_user_input(self, user_msg: str) -> AgentReply:
        response = self.client.models.generate_content(
            model=MODEL_ID,
            contents=user_msg,
            config=self._build_generation_config(),
        )
        return self._process_response(response)

    def handle_tool_decision(
        self, pending: PendingToolCall, approved: bool
    ) -> AgentReply:
        if not approved:
            tool_output = "User denied permission to execute this command."
        else:
            tool_output = self._execute_tool_function(pending.tool_name, pending.args)

        response = self.client.models.generate_content(
            model=MODEL_ID,
            contents=tool_output,
            config=self._build_generation_config(),
        )
        return self._process_response(response)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_generation_config(self) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            tools=[types.Tool(function_declarations=TOOLS_SCHEMA)],
            thinking_config=types.ThinkingConfig(thinking_level=self.thinking_level),
        )

    def _process_response(self, response) -> AgentReply:
        text_segments: List[str] = []

        while True:
            if getattr(response, "text", None):
                text_segments.append(response.text)

            function_calls = getattr(response, "function_calls", None) or []
            if not function_calls:
                return AgentReply(text=_clean_text(text_segments))

            for call in function_calls:
                if call.name == "run_shell":
                    return AgentReply(
                        text=_clean_text(text_segments),
                        pending_tool=PendingToolCall(
                            tool_name=call.name,
                            args=_normalize_args(call.args),
                        ),
                    )

                response = self._respond_with_tool_execution(call)
                break

    def _respond_with_tool_execution(self, call) -> object:
        output = self._execute_tool_function(call.name, _normalize_args(call.args))
        return self.client.models.generate_content(
            model=MODEL_ID,
            contents=output,
            config=self._build_generation_config(),
        )

    @staticmethod
    def _execute_tool_function(tool_name: str, args: Dict[str, Any]) -> str:
        func = TOOL_FUNCTIONS.get(tool_name)
        if not func:
            return f"Error: Unknown tool '{tool_name}'."
        try:
            return str(func(**args))
        except Exception as exc:  # pragma: no cover - defensive guard
            return f"Error while running {tool_name}: {exc}"


def _normalize_args(raw_args: Any) -> Dict[str, Any]:
    if hasattr(raw_args, "items"):
        return dict(raw_args)
    return raw_args or {}


def _clean_text(segments: List[str]) -> Optional[str]:
    joined = "\n".join(part for part in segments if part)
    return joined.strip() or None
