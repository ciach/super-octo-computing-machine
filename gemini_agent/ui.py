"""Textual-based UI for the Gemini CLI agent."""

from __future__ import annotations

import asyncio
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, Log, Static

from .agent import Agent, AgentReply, PendingToolCall


class CLIApp(App):
    CSS = """
    Screen {
        align: center middle;
    }

    #layout {
        width: 90%;
        height: 85%;
        border: round #555;
        padding: 1;
    }

    #history-label {
        color: #7be;
    }

    #history {
        height: 70%;
        border: round #666;
        padding: 1;
    }

    #inputbox {
        width: 100%;
        border: round green;
    }

    #controls Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
    ]

    def __init__(self, agent: Agent, **kwargs):
        super().__init__(**kwargs)
        self.agent = agent
        self.pending_tool: Optional[PendingToolCall] = None

    def compose(self) -> ComposeResult:
        with Vertical(id="layout"):
            yield Static("Agent History", id="history-label")
            yield Log(id="history")
            yield Input(placeholder="Type your command here...", id="inputbox")
            with Horizontal(id="controls"):
                yield Button("Send", id="sendbtn")
                yield Button("Approve", id="approve", disabled=True)
                yield Button("Deny", id="deny", disabled=True)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    async def on_mount(self) -> None:
        self.query_one("#history", Log).write_line(
            "Welcome to the Gemini CLI agent! Type 'exit' to quit."
        )
        self.query_one("#inputbox", Input).focus()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "sendbtn":
            await self._process_input()
        elif event.button.id == "approve":
            await self._handle_tool_decision(True)
        elif event.button.id == "deny":
            await self._handle_tool_decision(False)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        await self._process_input()

    # ------------------------------------------------------------------
    # Core helpers
    # ------------------------------------------------------------------
    async def _process_input(self) -> None:
        input_box = self.query_one("#inputbox", Input)
        user_msg = input_box.value.strip()
        if not user_msg:
            return
        input_box.value = ""

        history = self.query_one("#history", Log)
        history.write_line("")
        history.write_line(f"User: {user_msg}")

        if user_msg.lower() in {"exit", "quit"}:
            self.exit()
            return

        reply = await asyncio.to_thread(self.agent.handle_user_input, user_msg)
        self._handle_reply(reply)

    async def _handle_tool_decision(self, approved: bool) -> None:
        if not self.pending_tool:
            return

        history = self.query_one("#history", Log)
        decision = "approved" if approved else "denied"
        history.write_line("")
        history.write_line(
            f"User {decision} command: {self.pending_tool.args.get('command', '')}"
        )
        self._toggle_tool_buttons(disabled=True)

        reply = await asyncio.to_thread(
            self.agent.handle_tool_decision, self.pending_tool, approved
        )
        self.pending_tool = None
        self._handle_reply(reply)

    def _handle_reply(self, reply: AgentReply) -> None:
        history = self.query_one("#history", Log)
        if reply.text:
            history.write_line("")
            history.write_line(f"Agent: {reply.text}")

        for event in reply.tool_events:
            history.write_line("")
            history.write_line(f"Agent (tool {event.name}, {event.status}):")
            history.write_line(event.output or "(no output)")

        if reply.pending_tool:
            self.pending_tool = reply.pending_tool
            cmd = self.pending_tool.args.get("command", "")
            history.write_line("")
            history.write_line(f"⚠️ Agent wants to run: {cmd}")
            self._toggle_tool_buttons(disabled=False)
        else:
            self.pending_tool = None
            self._toggle_tool_buttons(disabled=True)

        history.scroll_end(animate=False)

    def _toggle_tool_buttons(self, *, disabled: bool) -> None:
        approve = self.query_one("#approve", Button)
        deny = self.query_one("#deny", Button)
        approve.disabled = disabled
        deny.disabled = disabled


def run_ui(agent: Agent) -> None:
    CLIApp(agent).run()
