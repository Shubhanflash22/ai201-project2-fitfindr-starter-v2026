#!/usr/bin/env python3
"""
FitFindr over HTTP.

    python serve.py                       run it locally
    gunicorn serve:app                    run it the way a host runs it

Everything else in this repo exits after one command, which cannot be
deployed. This file starts a web server, waits, and hands each request to the
same `run_agent()` the command line calls. No agent logic lives here: if the
loop works from `python app.py ask`, it works from here.

Two routes:

    POST /ask       {"query": "vintage graphic tee under $30",
                     "wardrobe": {...}}     wardrobe is optional
    GET  /health    is it awake?

`/ask` returns the session dict from `run_agent()` as JSON, unchanged: the same
keys printed from the command line, including `error`. Read `session["error"]`
first.

It runs one request at a time; see the note above `_one_at_a_time`, which also
decides which gunicorn worker can be used.

There is deliberately no logging, timing or request counting in this file.
"""

import os
import sys
import threading

# config first, and before anything that talks to the model: it loads .env and
# fixes the Windows console encoding for every module that imports it.
import config  # noqa: F401

from flask import Flask, jsonify, request

from agent import run_agent
from utils.data_loader import get_example_wardrobe

app = Flask(__name__)


# ── one request at a time ─────────────────────────────────────────────────────
# A web server will happily run two requests at once. Two things in this repo
# assume otherwise:
#
#   - `mcp_client.call_tool` starts `mcp_server.py` as a separate process over
#     stdio, one per call. Two overlapping requests means two extra Python
#     interpreters, and the free hosting tier has 512 MB for all of it.
#   - `generate.py`'s pacing window and its call counter are plain module
#     globals. Two threads sharing them means the per-minute limiter counts
#     something that isn't true.
#
# The lock covers exactly the agent run: the part that spawns processes and
# calls the model. Reading the request, rejecting a bad one, and turning the
# answer into JSON all happen outside it, so a malformed body comes straight
# back with a 400 instead of queueing behind another request.
#
# Serialising the runs costs nothing here (one user asking one question) and
# keeps the deployed behaviour identical to the CLI's. When that stops being an
# acceptable trade, the fix is a real queue, not a bigger lock.
#
# The same constraint decides the start command. `mcp_client.call_tool` wraps
# `asyncio.run()`, which refuses to start when an event loop is already
# running, and an async worker always has one. Under `gunicorn -k gevent` (or
# `-k eventlet`, or an ASGI server like uvicorn) every MCP call fails with
# "asyncio.run() cannot be called from a running event loop".
#
#     gunicorn serve:app              ← right: the DEFAULT sync worker
#     gunicorn -k gevent serve:app    ← breaks every MCP call you make

_one_at_a_time = threading.Lock()


@app.get("/health")
def health():
    """Is the server awake? A host pings something like this to find out."""
    return jsonify({"status": "ok"})


@app.post("/ask")
def ask():
    """
    Run the agent on one query.

        In:   {"query": "...", "wardrobe": {...}}   wardrobe optional; leave it
                                                    out and the same example
                                                    wardrobe the CLI uses is used.
        Out:  the session dict from run_agent(), as JSON.
    """
    payload = request.get_json(silent=True) or {}
    query = (payload.get("query") or "").strip()
    if not query:
        # 400 rather than a stack trace: the caller can act on this one.
        return jsonify({"error": "Send JSON with a 'query' field, e.g. "
                                 '{"query": "vintage graphic tee under $30"}'}), 400

    wardrobe = payload.get("wardrobe")
    if not isinstance(wardrobe, dict):
        wardrobe = get_example_wardrobe()

    # A queued request should look like a queued request. Without this the second
    # caller just sits there, and "slow" and "waiting its turn" look the same from
    # outside.
    #
    # This is not logging. It prints nothing on the normal path, carries no timing
    # and counts nothing; it only notes that this request had to wait. `locked()`
    # can be a moment out of date, so the note is occasionally missed, which
    # nothing depends on.
    if _one_at_a_time.locked():
        print(
            "  [serve] another request is still running. This one is waiting "
            "its turn — serve.py handles one at a time, on purpose.",
            file=sys.stderr,
            flush=True,
        )

    failure = None
    session = None
    with _one_at_a_time:
        try:
            session = run_agent(query, wardrobe)
        except Exception as exc:  # noqa: BLE001 - a 500 with a sentence beats a hang
            failure = f"{type(exc).__name__}: {exc}"

    # Outside the lock: building a response is not work the next caller should
    # be waiting on.
    if failure is not None:
        return jsonify({"error": failure}), 500

    return jsonify(session)


if __name__ == "__main__":
    # A host sets the port through PORT and reaches the process from outside the
    # container. Binding 127.0.0.1 means only the container itself can connect,
    # which looks like a broken app from the browser.
    port = int(os.getenv("PORT", "5000"))

    # Never on by default. Flask's debugger executes code typed into a browser, so
    # a deployed app with it on is a stranger's shell. Set AI201_DEBUG=1 locally
    # for the reloader.
    debug = os.getenv("AI201_DEBUG", "0") == "1"

    print(f"\nFitFindr is listening on http://localhost:{port}")
    print("It runs one request at a time — a second one waits for the first.")
    print("Ask it something (single quotes, as always):\n")
    print(
        f"  curl -X POST http://localhost:{port}/ask \\\n"
        f"    -H 'Content-Type: application/json' \\\n"
        f"    -d '{{\"query\": \"vintage graphic tee under $30\"}}'\n"
    )
    print("Ctrl-C to stop.\n")

    app.run(host="0.0.0.0", port=port, debug=debug)
