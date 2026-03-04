"""
example_tasks.py — runnable examples demonstrating different orchestration patterns.

Run any example:
    cd multi_agent_system
    python examples/example_tasks.py
"""
import os
import sys

# Allow imports from parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator import Orchestrator


EXAMPLES = {
    "1": {
        "name": "Research Task (sequential)",
        "goal": (
            "Research the top 3 benefits of multi-agent AI systems compared to "
            "single-agent systems, then write a concise one-page report."
        ),
    },
    "2": {
        "name": "Coding Task (coder + reviewer)",
        "goal": (
            "Write a Python function that implements a binary search tree with "
            "insert, search, and in-order traversal methods. Include unit tests."
        ),
    },
    "3": {
        "name": "Analysis Task (parallel research + analysis)",
        "goal": (
            "Analyse the trade-offs between REST and GraphQL APIs. "
            "Provide a scoring matrix covering performance, developer experience, "
            "caching, and real-time support."
        ),
    },
    "4": {
        "name": "Full Pipeline (research → code → review)",
        "goal": (
            "Research how rate limiting works in web APIs, then implement a "
            "Python token-bucket rate limiter class, and review the implementation."
        ),
    },
    "5": {
        "name": "Data Analysis Task",
        "goal": (
            "Generate sample sales data for 12 months (using Python), compute "
            "monthly growth rates, identify the best and worst months, and produce "
            "an insights report."
        ),
    },
}


def run_example(key: str) -> None:
    example = EXAMPLES[key]
    print(f"\n{'='*60}")
    print(f"Example {key}: {example['name']}")
    print(f"{'='*60}")

    orch = Orchestrator(verbose=True)
    result = orch.run(example["goal"])

    print(f"\n{'='*60}")
    print("RESULT:")
    print(f"{'='*60}")
    print(result)
    print(f"{'='*60}\n")


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n[!] Set ANTHROPIC_API_KEY before running examples.\n")
        sys.exit(1)

    print("\nAvailable examples:")
    for key, ex in EXAMPLES.items():
        print(f"  {key}. {ex['name']}")

    choice = input("\nEnter example number (or 'all' to run all): ").strip()

    if choice == "all":
        for key in EXAMPLES:
            run_example(key)
    elif choice in EXAMPLES:
        run_example(choice)
    else:
        print(f"Invalid choice: {choice}")
        sys.exit(1)


if __name__ == "__main__":
    main()
