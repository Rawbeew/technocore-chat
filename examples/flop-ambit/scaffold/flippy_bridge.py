"""Bridge to flippy router (optional).

If flippy is on PYTHONPATH, this can call its route() for LLM assistance
while keeping Technocore tools local.

Usage:
    PYTHONPATH=/path/to/flippy python scaffold/flippy_bridge.py "summarize room lobby"
"""
import os
import sys


def try_route(prompt: str, model: str | None = None):
    """Attempt to call flippy's route. Returns dict or error."""
    try:
        from src.loomweaver.core import route
    except ImportError:
        return {"ok": False, "error": "flippy not on PYTHONPATH (clone github.com/Rawbeew/flippy)"}

    messages = [{"role": "user", "content": prompt}]
    try:
        return route(messages, model=model)
    except Exception as e:
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python flippy_bridge.py <prompt>")
        sys.exit(1)
    result = try_route(" ".join(sys.argv[1:]))
    import json
    print(json.dumps(result, indent=2, default=str))
