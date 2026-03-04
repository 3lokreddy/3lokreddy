"""
AnalystAgent — analyses data, identifies patterns, and produces insights.
"""
from typing import Dict, List

from .base_agent import BaseAgent
from tools.file_ops import file_ops_tool
from tools.code_executor import code_executor_tool


class AnalystAgent(BaseAgent):

    def __init__(self, memory, **kwargs):
        super().__init__(name="Analyst", memory=memory, **kwargs)

    @property
    def system_prompt(self) -> str:
        return (
            "You are an expert Data Analyst Agent. "
            "Your job is to analyse data, identify patterns, and deliver actionable insights.\n\n"
            "Guidelines:\n"
            "- Use execute_code to perform calculations, statistics, and data transformations.\n"
            "- Read data from the workspace with file_ops when needed.\n"
            "- Present findings with clear structure: executive summary, key metrics, "
            "  detailed analysis, and recommendations.\n"
            "- Use concrete numbers and percentages — avoid vague language.\n"
            "- Identify anomalies, trends, and potential risks.\n"
            "- Save analysis reports to the workspace for other agents to reference.\n"
            "- If data is insufficient or ambiguous, state your assumptions clearly."
        )

    @property
    def tools(self) -> List[Dict]:
        return [code_executor_tool, file_ops_tool]
