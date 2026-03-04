"""
CoderAgent — writes, tests, and debugs code.
"""
from typing import Dict, List

from .base_agent import BaseAgent
from tools.file_ops import file_ops_tool
from tools.code_executor import code_executor_tool


class CoderAgent(BaseAgent):

    def __init__(self, memory, **kwargs):
        super().__init__(name="Coder", memory=memory, **kwargs)

    @property
    def system_prompt(self) -> str:
        return (
            "You are an expert Software Engineering Agent specialising in Python. "
            "Your job is to write clean, correct, and well-documented code.\n\n"
            "Guidelines:\n"
            "- Write production-quality Python unless another language is requested.\n"
            "- Always validate your code by running it with execute_code before delivering it.\n"
            "- Fix any errors revealed by test runs — iterate until the code passes.\n"
            "- Include docstrings, type hints, and concise inline comments.\n"
            "- Save finished code to the workspace with file_ops.\n"
            "- Report the final code AND the test output in your response.\n"
            "- Prefer stdlib solutions; add third-party deps only when necessary."
        )

    @property
    def tools(self) -> List[Dict]:
        return [code_executor_tool, file_ops_tool]
