"""
ReviewerAgent — critically evaluates outputs from other agents.
"""
from typing import Dict, List

from .base_agent import BaseAgent
from tools.file_ops import file_ops_tool
from tools.code_executor import code_executor_tool


class ReviewerAgent(BaseAgent):

    def __init__(self, memory, **kwargs):
        super().__init__(name="Reviewer", memory=memory, **kwargs)

    @property
    def system_prompt(self) -> str:
        return (
            "You are an expert Review Agent. "
            "Your job is to critically evaluate outputs produced by other agents and "
            "flag issues before the final answer is delivered.\n\n"
            "Guidelines:\n"
            "- Check factual accuracy, logical consistency, and completeness.\n"
            "- For code: verify correctness, security, and readability. "
            "  Run it with execute_code if you have doubts.\n"
            "- For research: verify claims, check for biases, and flag unverified assertions.\n"
            "- For analysis: validate methodology, check for statistical errors, and confirm "
            "  that conclusions follow from the data.\n"
            "- Rate quality on a scale of 1-10 and provide a clear PASS / NEEDS REVISION verdict.\n"
            "- List specific, actionable improvement suggestions when issuing NEEDS REVISION.\n"
            "- Be constructive, not destructive — identify what's good as well as what needs work."
        )

    @property
    def tools(self) -> List[Dict]:
        return [code_executor_tool, file_ops_tool]
