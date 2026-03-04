"""
Orchestrator — the brain of the multi-agent system.

Responsibilities:
  1. Receive a high-level goal from the user.
  2. Use Claude to decompose the goal into sub-tasks.
  3. Assign each sub-task to the best-fit agent.
  4. Collect results and pass them through the Reviewer.
  5. Synthesise a final, coherent answer.

Orchestration strategies supported:
  • sequential  — tasks run one after another; each can see prior results.
  • parallel    — all tasks dispatched independently (ThreadPoolExecutor).
  • pipeline    — fixed researcher → coder/analyst → reviewer pipeline.
"""
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

import anthropic

from agents import ResearcherAgent, CoderAgent, AnalystAgent, ReviewerAgent
from memory.shared_memory import SharedMemory


# ── Agent registry ────────────────────────────────────────────────────────────

AGENT_DESCRIPTIONS = {
    "researcher": "Finds and summarises information from the web. Best for factual lookups, background research, and news.",
    "coder":      "Writes, tests, and debugs Python code. Best for programming tasks, scripts, and technical implementations.",
    "analyst":    "Analyses data and produces insights. Best for calculations, statistics, pattern recognition, and reports.",
    "reviewer":   "Reviews and quality-checks outputs. Best for validating correctness, catching errors, and rating quality.",
}

ROUTING_TOOL = {
    "name": "route_tasks",
    "description": "Decompose the goal into sub-tasks and assign each to the most suitable agent.",
    "input_schema": {
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "description": "Ordered list of sub-tasks.",
                "items": {
                    "type": "object",
                    "properties": {
                        "task_id":    {"type": "string",  "description": "Short unique id, e.g. 't1'."},
                        "agent":      {"type": "string",  "enum": list(AGENT_DESCRIPTIONS.keys())},
                        "description": {"type": "string", "description": "What this agent should do."},
                        "depends_on": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "task_ids this task needs as input (empty = no dependency).",
                        },
                    },
                    "required": ["task_id", "agent", "description", "depends_on"],
                },
            },
            "strategy": {
                "type": "string",
                "enum": ["sequential", "parallel", "pipeline"],
                "description": "Execution strategy for the tasks.",
            },
        },
        "required": ["tasks", "strategy"],
    },
}


class Orchestrator:
    """
    Master orchestrator that coordinates multiple specialised agents to solve
    complex, multi-step goals.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        verbose: bool = True,
    ):
        self.model = model
        self.verbose = verbose
        self.memory = SharedMemory()
        self._client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

        # Instantiate all agents, sharing the same memory
        self._agents = {
            "researcher": ResearcherAgent(memory=self.memory, model=model),
            "coder":      CoderAgent(memory=self.memory, model=model),
            "analyst":    AnalystAgent(memory=self.memory, model=model),
            "reviewer":   ReviewerAgent(memory=self.memory, model=model),
        }

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self, goal: str) -> str:
        """
        Execute a high-level goal and return the final synthesised answer.
        """
        self._log(f"\n{'='*60}")
        self._log(f"GOAL: {goal}")
        self._log(f"{'='*60}\n")

        # Step 1: Plan — let Claude decompose and route the goal
        plan = self._plan(goal)
        self._log(f"Plan: {plan['strategy'].upper()} execution of {len(plan['tasks'])} task(s)\n")

        # Step 2: Execute according to strategy
        strategy = plan["strategy"]
        tasks = plan["tasks"]

        if strategy == "parallel":
            results = self._run_parallel(tasks, goal)
        elif strategy == "pipeline":
            results = self._run_pipeline(tasks, goal)
        else:  # sequential (default)
            results = self._run_sequential(tasks, goal)

        # Step 3: Synthesise
        final = self._synthesise(goal, results)
        self._log(f"\n{'='*60}")
        self._log("FINAL ANSWER READY")
        self._log(f"{'='*60}\n")
        return final

    # ── Planning ──────────────────────────────────────────────────────────────

    def _plan(self, goal: str) -> Dict:
        """Call Claude to produce a task plan using the route_tasks tool."""
        agent_desc_str = "\n".join(
            f"  • {name}: {desc}" for name, desc in AGENT_DESCRIPTIONS.items()
        )
        system = (
            "You are an AI orchestration planner. "
            "Given a high-level goal, decompose it into a minimal set of sub-tasks "
            "and assign each to the best agent. "
            "Choose the execution strategy that best fits the task structure.\n\n"
            f"Available agents:\n{agent_desc_str}\n\n"
            "Always include a 'reviewer' task at the end unless the goal is trivial."
        )

        response = self._client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system,
            tools=[ROUTING_TOOL],
            tool_choice={"type": "any"},
            messages=[{"role": "user", "content": f"Goal: {goal}"}],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "route_tasks":
                plan = block.input
                self.memory.set("plan", plan, agent_id="orchestrator")
                return plan

        # Fallback: single researcher task
        return {
            "strategy": "sequential",
            "tasks": [
                {"task_id": "t1", "agent": "researcher", "description": goal, "depends_on": []},
            ],
        }

    # ── Execution strategies ──────────────────────────────────────────────────

    def _run_sequential(self, tasks: List[Dict], goal: str) -> Dict[str, str]:
        results: Dict[str, str] = {}
        for task in tasks:
            ctx = self._build_context(task, results, goal)
            self._log(f"[sequential] Running {task['agent']} → {task['task_id']}: {task['description'][:80]}")
            results[task["task_id"]] = self._agents[task["agent"]].run(task["description"], ctx)
        return results

    def _run_parallel(self, tasks: List[Dict], goal: str) -> Dict[str, str]:
        # Group into waves by dependency order
        completed: Dict[str, str] = {}
        remaining = list(tasks)

        while remaining:
            # Tasks whose dependencies are all satisfied
            wave = [t for t in remaining if all(d in completed for d in t["depends_on"])]
            if not wave:
                self._log("[parallel] Dependency cycle detected — falling back to sequential")
                return self._run_sequential(remaining, goal)

            self._log(f"[parallel] Dispatching wave of {len(wave)} task(s)")
            with ThreadPoolExecutor(max_workers=min(len(wave), 4)) as pool:
                futures = {
                    pool.submit(
                        self._agents[t["agent"]].run,
                        t["description"],
                        self._build_context(t, completed, goal),
                    ): t["task_id"]
                    for t in wave
                }
                for future in as_completed(futures):
                    tid = futures[future]
                    try:
                        completed[tid] = future.result()
                    except Exception as exc:
                        completed[tid] = f"Error: {exc}"

            remaining = [t for t in remaining if t["task_id"] not in completed]

        return completed

    def _run_pipeline(self, tasks: List[Dict], goal: str) -> Dict[str, str]:
        """Convenience alias — pipeline is sequential with explicit context chaining."""
        return self._run_sequential(tasks, goal)

    # ── Synthesis ─────────────────────────────────────────────────────────────

    def _synthesise(self, goal: str, results: Dict[str, str]) -> str:
        """Ask Claude to merge all agent results into a single coherent response."""
        results_text = "\n\n".join(
            f"--- {tid} ---\n{content}" for tid, content in results.items()
        )
        messages = [
            {
                "role": "user",
                "content": (
                    f"Original goal: {goal}\n\n"
                    f"Agent outputs:\n{results_text}\n\n"
                    "Please synthesise these outputs into a single, clear, and complete final answer "
                    "for the user. Remove redundancy, resolve any conflicts, and present the "
                    "information in the most helpful format."
                ),
            }
        ]
        response = self._client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=(
                "You are a synthesis engine. Merge agent outputs into one polished final answer. "
                "Be concise but complete. Use markdown formatting."
            ),
            messages=messages,
        )
        return self._extract_text(response.content)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_context(
        self, task: Dict, results: Dict[str, str], goal: str
    ) -> Dict[str, Any]:
        ctx: Dict[str, Any] = {"overall_goal": goal}
        for dep_id in task.get("depends_on", []):
            if dep_id in results:
                ctx[dep_id] = results[dep_id]
        return ctx

    @staticmethod
    def _extract_text(content_blocks) -> str:
        return "\n".join(
            block.text for block in content_blocks if hasattr(block, "text")
        ).strip()

    def _log(self, message: str) -> None:
        if self.verbose:
            ts = time.strftime("%H:%M:%S")
            print(f"[{ts}] [Orchestrator] {message}")

    # ── Introspection ─────────────────────────────────────────────────────────

    def memory_snapshot(self) -> Dict:
        return self.memory.snapshot()

    def list_agents(self) -> List[str]:
        return list(self._agents.keys())
