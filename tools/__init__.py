"""KALI OSINT Agent — Tool Modules"""
from .passive_recon import PASSIVE_TOOLS
from .active_recon  import ACTIVE_TOOLS

ALL_TOOLS = PASSIVE_TOOLS + ACTIVE_TOOLS
