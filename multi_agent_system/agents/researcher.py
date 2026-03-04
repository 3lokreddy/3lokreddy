"""
ResearcherAgent — gathers and synthesises information from the web.
"""
from typing import Dict, List

from .base_agent import BaseAgent
from tools.web_search import web_search_tool
from tools.file_ops import file_ops_tool


class ResearcherAgent(BaseAgent):

    def __init__(self, memory, **kwargs):
        super().__init__(name="Researcher", memory=memory, **kwargs)

    @property
    def system_prompt(self) -> str:
        return (
            "You are an expert Research Agent. Your job is to find accurate, "
            "up-to-date information on any topic requested by the orchestrator.\n\n"
            "Guidelines:\n"
            "- Use the web_search tool to look up factual information.\n"
            "- Cross-reference multiple searches when accuracy is critical.\n"
            "- Summarise findings in a clear, structured format (use headings and bullet points).\n"
            "- Cite sources (titles + URLs) at the end of your response.\n"
            "- If information is uncertain or conflicting, say so explicitly.\n"
            "- Save important findings to files using file_ops when asked."
        )

    @property
    def tools(self) -> List[Dict]:
        return [web_search_tool, file_ops_tool]
