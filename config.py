"""
Settings for FitFindr.

If fit cards come out word-for-word identical every time, it is one of two
things below: the cache handed back an answer it already had, or TEMPERATURE
is 0.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")


# ─── Windows console encoding ────────────────────────────────────────────────
# On Windows the console defaults to cp1252, which cannot represent emoji. The
# model puts emoji in fit cards often, so printing one would crash with a
# UnicodeEncodeError after the model call had already been paid for. Every
# entry point imports config, so fixing it here fixes it everywhere.

if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


# ─── Fit card variation and caching ──────────────────────────────────────────

# How much the model varies between runs. 0.0 gives the same words every time;
# higher gives more variation. Fit cards want variation, since a caption that
# reads identically for two different items is a template.
TEMPERATURE = 0.9

# Identical prompts reuse the answer already received, so re-running the same
# query twenty times while debugging costs one call. Evaluation runs turn this
# off automatically (`run_eval.py`), since five tries have to be five real
# answers.
CACHE_ENABLED = os.getenv("AI201_CACHE", "1") != "0"


# ─── The agent loop ──────────────────────────────────────────────────────────

# Stop condition for the loop. A missing one is the most common architectural
# failure in production agents: the loop runs forever and burns quota. This
# loop is short enough that the limit may never be hit.
MAX_ITERATIONS = 10

# How many search results to consider. The agent uses the first one.
SEARCH_RESULT_LIMIT = 10


# ─── Model ───────────────────────────────────────────────────────────────────

MODEL = os.getenv("AI201_MODEL", "gemini-3.5-flash-lite")


# ─── Rate limiting and quota guards ──────────────────────────────────────────
# One agent run is several requests, because two of the three tools call the
# model, so iterating quickly will cross the per-minute limit. The adapter
# paces requests and says when it is waiting; that pause is not a bug.
#
# REQUESTS_PER_MINUTE is 15 because that is the actual free-tier limit for
# gemini-3.5-flash-lite (the API reports it as
# GenerateRequestsPerMinutePerProjectPerModel-FreeTier, quotaValue 15). Raising
# it does not buy more quota; it only moves the wait from here to the service,
# and a paced wait is much cheaper than a failed run. Two model calls per agent
# run means about seven runs a minute.

REQUESTS_PER_MINUTE = 15
SESSION_REQUEST_BUDGET = 300
MAX_RETRIES = 5

# A model call that hasn't answered after this many seconds is cancelled and
# reported as the model being unavailable. Without it, one stalled call holds
# serve.py's lock forever. AI201_MODEL_TIMEOUT_S exists so a test can shrink it.
MODEL_TIMEOUT_S = float(os.getenv("AI201_MODEL_TIMEOUT_S", "20"))

CACHE_DIR = ROOT / ".cache"


# ─── Paths ───────────────────────────────────────────────────────────────────

DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
