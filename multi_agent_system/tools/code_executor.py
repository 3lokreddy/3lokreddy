"""
Code execution tool — runs Python snippets in a restricted subprocess.
The agent can use this to test generated code before delivering it.
"""
import subprocess
import sys
import tempfile
import textwrap
from typing import Any, Dict

code_executor_tool: Dict[str, Any] = {
    "name": "execute_code",
    "description": (
        "Execute a Python code snippet and return stdout + stderr. "
        "Use this to validate logic, run calculations, or test generated code."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Valid Python code to execute.",
            },
            "timeout": {
                "type": "integer",
                "description": "Max execution time in seconds (default 10, max 30).",
                "default": 10,
            },
        },
        "required": ["code"],
    },
}


def execute_code(code: str, timeout: int = 10) -> Dict[str, str]:
    """
    Run `code` in an isolated subprocess and return {'stdout': ..., 'stderr': ..., 'returncode': ...}.
    """
    timeout = min(int(timeout), 30)  # hard cap

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(textwrap.dedent(code))
        tmp_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "stdout": result.stdout[:4000],
            "stderr": result.stderr[:2000],
            "returncode": str(result.returncode),
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Execution timed out after {timeout}s.",
            "returncode": "-1",
        }
    except Exception as exc:
        return {
            "stdout": "",
            "stderr": str(exc),
            "returncode": "-1",
        }
    finally:
        import os
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
