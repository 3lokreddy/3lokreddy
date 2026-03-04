"""
File operations tool for agents.
Agents can read and write files in a sandboxed workspace directory.
"""
import os
import json
from pathlib import Path
from typing import Any, Dict

WORKSPACE_DIR = Path(os.getenv("AGENT_WORKSPACE", "/tmp/agent_workspace"))
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

file_ops_tool: Dict[str, Any] = {
    "name": "file_ops",
    "description": (
        "Read or write a file in the agent workspace. "
        "Use action='read' to retrieve content, action='write' to save content."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["read", "write", "list"],
                "description": "Operation to perform.",
            },
            "filename": {
                "type": "string",
                "description": "Filename (relative to workspace). Required for read/write.",
            },
            "content": {
                "type": "string",
                "description": "Content to write. Required when action='write'.",
            },
        },
        "required": ["action"],
    },
}


def _safe_path(filename: str) -> Path:
    """Resolve and validate path stays inside workspace."""
    target = (WORKSPACE_DIR / filename).resolve()
    if not str(target).startswith(str(WORKSPACE_DIR.resolve())):
        raise ValueError(f"Path traversal attempt blocked: {filename}")
    return target


def read_file(filename: str) -> str:
    path = _safe_path(filename)
    if not path.exists():
        return f"Error: file '{filename}' does not exist in workspace."
    return path.read_text(encoding="utf-8")


def write_file(filename: str, content: str) -> str:
    path = _safe_path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"Successfully wrote {len(content)} characters to '{filename}'."


def list_files() -> str:
    files = [str(p.relative_to(WORKSPACE_DIR)) for p in WORKSPACE_DIR.rglob("*") if p.is_file()]
    return json.dumps(files, indent=2) if files else "Workspace is empty."


def dispatch_file_op(action: str, filename: str = "", content: str = "") -> str:
    if action == "read":
        return read_file(filename)
    elif action == "write":
        return write_file(filename, content)
    elif action == "list":
        return list_files()
    return f"Unknown action: {action}"
