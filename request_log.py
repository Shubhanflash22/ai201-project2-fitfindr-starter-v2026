"""
One JSON line per request, written to logs/requests.jsonl.

serve.py calls write() once per /ask request, on every path. A failure to
write the log is reported on stderr and never raised, so logging can never
change what the caller gets back.
"""

import json
import os
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

import config

# AI201_LOG_PATH exists so a test can point the log somewhere unwritable and
# check that the request still succeeds. Normal runs leave it unset.
LOG_PATH = Path(os.getenv("AI201_LOG_PATH") or (config.ROOT / "logs" / "requests.jsonl"))

_write_lock = threading.Lock()

# classify() reads the first words of session["error"], which agent.py writes.
# If those messages are ever reworded, update these prefixes.
_NOTHING_FOUND = "Nothing in the listings matched"
_MODEL_DOWN = "The model couldn't be reached"
_MCP_DOWN = "The search tool couldn't be reached"


def classify(session: dict) -> str:
    """Name the outcome of a run_agent() session that returned normally."""
    error = session.get("error")
    if not error:
        return "ok"
    if error.startswith(_NOTHING_FOUND):
        return "nothing_found"
    if error.startswith(_MODEL_DOWN):
        return "model_unavailable"
    if error.startswith(_MCP_DOWN):
        return "mcp_unavailable"
    return "server_error"


def write(rec: dict, route: str, http_status: int, duration_s: float) -> None:
    """Append one record. Never raises."""
    try:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "request_id": uuid.uuid4().hex[:12],
            "route": route,
            "http_status": http_status,
            "query": rec.get("query"),
            "outcome": rec.get("outcome"),
            "error": rec.get("error"),
            "duration_s": round(duration_s, 3),
            "queued": bool(rec.get("queued", False)),
            "prompt_tokens": rec.get("prompt_tokens"),
            "output_tokens": rec.get("output_tokens"),
            "selected_item_id": rec.get("selected_item_id"),
        }
        line = json.dumps(record, ensure_ascii=False) + "\n"
        with _write_lock:
            LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line)
    except Exception as exc:  # noqa: BLE001 - logging must never break a request
        try:
            print(f"  [request_log] could not write the log: {exc}", file=sys.stderr, flush=True)
        except Exception:  # noqa: BLE001
            pass