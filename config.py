"""
KALI OSINT AGENT — Configuration
"""

import os

# ─── API Keys (set via environment variables) ───────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SHODAN_API_KEY    = os.environ.get("SHODAN_API_KEY", "")
VIRUSTOTAL_KEY    = os.environ.get("VIRUSTOTAL_API_KEY", "")

# ─── Agent Settings ──────────────────────────────────────────────────────────
MODEL             = "claude-opus-4-6"
MAX_TOKENS        = 8192
MAX_TOOL_ITERS    = 30          # hard cap on agentic loop iterations

# ─── Recon Modes ─────────────────────────────────────────────────────────────
PASSIVE = "passive"
ACTIVE  = "active"
FULL    = "full"

# ─── Network Timeouts (seconds) ──────────────────────────────────────────────
DNS_TIMEOUT    = 5
HTTP_TIMEOUT   = 10
SOCKET_TIMEOUT = 5
NMAP_TIMEOUT   = 120   # active scans can be slow

# ─── Report Output Directory ─────────────────────────────────────────────────
REPORT_DIR = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(REPORT_DIR, exist_ok=True)
