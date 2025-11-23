"""Gemini agent orchestration, including tool routing."""

from __future__ import annotations

from dataclasses import dataclass, field
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
class ToolEvent:
    """Record describing the output of a tool invocation."""

    name: str
    status: str
    output: str


@dataclass
class AgentReply:
    """Result returned to the UI layer after each interaction."""

    text: Optional[str] = None
    pending_tool: Optional[PendingToolCall] = None
    tool_events: List[ToolEvent] = field(default_factory=list)


class Agent:
    """High-level orchestrator around the Gemini client and available tools."""

    def __init__(self, api_key: str, thinking_level: types.ThinkingLevel):
        self.client = genai.Client(api_key=api_key)
        self.thinking_level = thinking_level
        self.system_prompt = (
            "You are an expert Linux CLI Agent working strictly inside the directory: "
            f"{WORK_DIR}. You can run shell commands, write code, and read files.\n\n"
            "GUIDELINES:\n"
            "1. When asked to write code, first write the file, then try to run it to verify it works.\n"
            "2. If a command fails, read the error, fix the code/command, and try again.\n"
            "3. Be concise.\n"
            "4. When the user wants to inspect file contents (full or partial), prefer the read_file tool and pass `file_path` plus `num_lines` when they request a limited range. Avoid using shell commands like cat/sed for this purpose."
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
            tool_result = {
                "status": "error",
                "output": "User denied permission to execute this command.",
            }
        else:
            tool_result = self._execute_tool_function(pending.tool_name, pending.args)

        tool_event = self._build_tool_event(pending.tool_name, tool_result)
        tool_message = self._format_tool_message(tool_event)

        response = self.client.models.generate_content(
            model=MODEL_ID,
            contents=tool_message,
            config=self._build_generation_config(),
        )
        return self._process_response(response, tool_events=[tool_event])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_generation_config(self) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            tools=[types.Tool(function_declarations=TOOLS_SCHEMA)],
            thinking_config=types.ThinkingConfig(thinking_level=self.thinking_level),
        )

    def _process_response(
        self, response, *, tool_events: Optional[List[ToolEvent]] = None
    ) -> AgentReply:
        text_segments: List[str] = []
        events: List[ToolEvent] = list(tool_events or [])

        while True:
            if getattr(response, "text", None):
                text_segments.append(response.text)

            function_calls = getattr(response, "function_calls", None) or []
            if not function_calls:
                return AgentReply(
                    text=_clean_text(text_segments),
                    tool_events=list(events),
                )

            for call in function_calls:
                if call.name == "run_shell":
                    return AgentReply(
                        text=_clean_text(text_segments),
                        pending_tool=PendingToolCall(
                            tool_name=call.name,
                            args=_normalize_args(call.args),
                        ),
                        tool_events=list(events),
                    )

                response, events = self._respond_with_tool_execution(call, events)
                break

    def _respond_with_tool_execution(
        self, call, events: List[ToolEvent]
    ) -> tuple[object, List[ToolEvent]]:
        tool_result = self._execute_tool_function(call.name, _normalize_args(call.args))
        event = self._build_tool_event(call.name, tool_result)
        events.append(event)
        message = self._format_tool_message(event)
        response = self.client.models.generate_content(
            model=MODEL_ID,
            contents=message,
            config=self._build_generation_config(),
        )
        return response, events

    @staticmethod
    def _execute_tool_function(tool_name: str, args: Dict[str, Any]) -> Dict[str, str]:
        func = TOOL_FUNCTIONS.get(tool_name)
        if not func:
            return {"status": "error", "output": f"Error: Unknown tool '{tool_name}'."}
        try:
            result = func(**args)
            if isinstance(result, dict) and "output" in result:
                status = str(result.get("status", "success"))
                output = str(result.get("output", ""))
                return {"status": status, "output": output}
            return {"status": "success", "output": str(result)}
        except Exception as exc:  # pragma: no cover - defensive guard
            return {
                "status": "error",
                "output": f"Error while running {tool_name}: {exc}",
            }

    @staticmethod
    def _build_tool_event(tool_name: str, result: Dict[str, str]) -> ToolEvent:
        return ToolEvent(
            name=tool_name,
            status=result.get("status", "success"),
            output=result.get("output", ""),
        )

    @staticmethod
    def _format_tool_message(event: ToolEvent) -> str:
        output = event.output or "(no output)"
        return f"Tool {event.name} ({event.status}):\n{output}"


def _normalize_args(raw_args: Any) -> Dict[str, Any]:
    if hasattr(raw_args, "items"):
        return dict(raw_args)
    return raw_args or {}


def _clean_text(segments: List[str]) -> Optional[str]:
    joined = "\n".join(part for part in segments if part)
    return joined.strip() or None
