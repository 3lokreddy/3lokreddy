"""
BaseAgent — abstract foundation for all agents in the system.

Every agent:
  • Has a unique id, name, role description, and a list of tools it can call.
  • Communicates with Claude via the Anthropic API using tool-use.
  • Reads/writes context via SharedMemory.
  • Implements run(task) → str.
"""
import json
import os
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import anthropic

from memory.shared_memory import SharedMemory
from tools.web_search import web_search, web_search_tool
from tools.file_ops import dispatch_file_op, file_ops_tool
from tools.code_executor import execute_code, code_executor_tool


# Map tool names to their Python handler functions
TOOL_HANDLERS = {
    "web_search": lambda inp: web_search(inp["query"], inp.get("num_results", 5)),
    "file_ops": lambda inp: dispatch_file_op(
        inp["action"], inp.get("filename", ""), inp.get("content", "")
    ),
    "execute_code": lambda inp: execute_code(inp["code"], inp.get("timeout", 10)),
}

ALL_TOOLS = [web_search_tool, file_ops_tool, code_executor_tool]


class BaseAgent(ABC):
    """
    Abstract base class for all agents.

    Subclasses must implement:
        system_prompt (property) → str
        tools         (property) → List[Dict]  (subset of ALL_TOOLS)
    """

    def __init__(
        self,
        name: str,
        memory: SharedMemory,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 4096,
        max_tool_rounds: int = 8,
    ):
        self.agent_id = str(uuid.uuid4())[:8]
        self.name = name
        self.memory = memory
        self.model = model
        self.max_tokens = max_tokens
        self.max_tool_rounds = max_tool_rounds
        self._client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # ── Subclass contracts ────────────────────────────────────────────────────

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """The system prompt that defines this agent's role and behaviour."""

    @property
    def tools(self) -> List[Dict]:
        """Tools available to this agent. Override to restrict the set."""
        return ALL_TOOLS

    # ── Public interface ──────────────────────────────────────────────────────

    def run(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Execute `task` and return the agent's final answer as a string.
        Tool calls are handled automatically in an agentic loop.
        """
        task_id = str(uuid.uuid4())[:8]
        self._log(f"Starting task [{task_id}]: {task[:100]}…")

        messages: List[Dict] = [{"role": "user", "content": self._build_user_message(task, context)}]

        for round_num in range(self.max_tool_rounds):
            response = self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self.system_prompt,
                tools=self.tools,
                messages=messages,
            )

            # Append assistant turn
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                # Extract the final text answer
                result = self._extract_text(response.content)
                self.memory.store_result(task_id, self.agent_id, result)
                self._log(f"Finished task [{task_id}]")
                return result

            if response.stop_reason == "tool_use":
                tool_results = self._execute_tools(response.content)
                messages.append({"role": "user", "content": tool_results})
            else:
                break  # unexpected stop reason

        # Fallback if we exhaust rounds
        fallback = f"[{self.name}] Reached maximum tool rounds without a final answer."
        self.memory.store_result(task_id, self.agent_id, fallback)
        return fallback

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _build_user_message(self, task: str, context: Optional[Dict]) -> str:
        parts = [f"Task: {task}"]
        if context:
            parts.append(f"\nContext:\n{json.dumps(context, indent=2, default=str)}")
        return "\n".join(parts)

    def _execute_tools(self, content_blocks: List) -> List[Dict]:
        results = []
        for block in content_blocks:
            if block.type != "tool_use":
                continue
            tool_name = block.name
            tool_input = block.input
            self._log(f"Calling tool '{tool_name}' with input: {str(tool_input)[:120]}")
            handler = TOOL_HANDLERS.get(tool_name)
            if handler:
                try:
                    output = handler(tool_input)
                    content = json.dumps(output) if not isinstance(output, str) else output
                except Exception as exc:
                    content = f"Tool error: {exc}"
            else:
                content = f"Unknown tool: {tool_name}"

            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": content,
            })
        return results

    @staticmethod
    def _extract_text(content_blocks: List) -> str:
        parts = []
        for block in content_blocks:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "\n".join(parts).strip()

    def _log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] [{self.name}#{self.agent_id}] {message}")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, id={self.agent_id})"
