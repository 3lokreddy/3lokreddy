"""
main.py — entry point for the Multi-Agent Orchestration System.

Usage:
    python main.py
    python main.py --goal "Write a Python web scraper for Hacker News"
    python main.py --goal "Analyse the pros and cons of microservices" --strategy sequential
    python main.py --interactive
"""
import argparse
import os
import sys


def check_api_key() -> bool:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key or key.startswith("sk-ant-placeholder"):
        print(
            "\n[!] ANTHROPIC_API_KEY is not set.\n"
            "    Export your key before running:\n"
            "      export ANTHROPIC_API_KEY='sk-ant-...'\n"
        )
        return False
    return True


def run_goal(goal: str, verbose: bool = True) -> str:
    # Import here so errors surface only when actually running
    from orchestrator import Orchestrator

    orch = Orchestrator(verbose=verbose)
    print(f"\nAgents available: {orch.list_agents()}\n")
    return orch.run(goal)


def interactive_mode() -> None:
    print("\n" + "=" * 60)
    print("  Multi-Agent Orchestration System — Interactive Mode")
    print("  Type 'quit' or 'exit' to stop.")
    print("=" * 60 + "\n")

    while True:
        try:
            goal = input("Enter your goal: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if goal.lower() in {"quit", "exit", "q"}:
            break
        if not goal:
            continue

        result = run_goal(goal)
        print("\n" + "=" * 60)
        print("RESULT:")
        print("=" * 60)
        print(result)
        print("=" * 60 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Multi-Agent Orchestration System powered by Claude"
    )
    parser.add_argument(
        "--goal", "-g",
        type=str,
        default="",
        help="High-level goal for the agent system to accomplish.",
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Start in interactive (REPL) mode.",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress agent-level logging; only show the final result.",
    )
    args = parser.parse_args()

    if not check_api_key():
        sys.exit(1)

    if args.interactive:
        interactive_mode()
        return

    goal = args.goal or (
        "Research the latest developments in multi-agent AI systems and "
        "write a concise summary with key takeaways."
    )

    result = run_goal(goal, verbose=not args.quiet)

    print("\n" + "=" * 60)
    print("FINAL RESULT")
    print("=" * 60)
    print(result)
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
