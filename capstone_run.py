"""
Capstone driver. Sends the requests for ONE criterion to a running serve.py,
checks the server's request log, prints the score and saves the raw output.

  python capstone_run.py 1 1 --log LOG
  python capstone_run.py 2 1 --log LOG --type a
  python capstone_run.py 3 1 --stderr STDERR_FILE
  python capstone_run.py 4 1 --log LOG
  python capstone_run.py 5 1 --log LOG

The first number is the criterion, the second is the trial. The server's state
(key, log path, renamed file) is set by hand before each run.
"""
import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://localhost:5000"
FIELDS = ["timestamp", "request_id", "route", "http_status", "query", "outcome",
          "error", "duration_s", "queued", "prompt_tokens", "output_tokens",
          "selected_item_id"]
MATCHING = [
    "vintage graphic tee under $30",
    "90s track jacket in size M",
    "silk slip dress in midi length under $40",
    "platform sneakers size 8",
    "denim jacket under $50",
]
NO_MATCH = [
    "designer ballgown under $5", "leather jacket under $5", "silk scarf under $5",
    "platform boots under $5", "denim shorts under $5", "wool coat under $5",
    "graphic tee under $5", "pleated skirt under $5", "cargo pants under $5",
    "knit sweater under $5",
]
EXPECT = {  # criterion 2: type -> (outcome, http_status)
    "a": ("bad_request", 400),
    "b": ("nothing_found", 200),
    "c": ("model_unavailable", 200),
    "d": ("mcp_unavailable", 200),
    "e": ("server_error", 500),
}
GAP_S = 10            # criterion 4: seconds between request starts
ON_TIME_S = 4.7       # criterion 4: duration_s at or under this is on time
WARM_N = 100
WARM_MIN_ON_TIME = 95


def post(raw):
    req = urllib.request.Request(BASE + "/ask", data=raw,
                                 headers={"Content-Type": "application/json"})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            status, text = resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        status, text = exc.code, exc.read().decode("utf-8")
    try:
        body = json.loads(text)
    except ValueError:
        body = text[:200]
    return status, body, round(time.perf_counter() - started, 3)


def summarize(body):
    if not isinstance(body, dict):
        return {"non_object_body": str(body)[:200]}
    return {k: (str(body[k])[:200] if body.get(k) is not None else None)
            for k in ("error", "fit_card", "outfit_suggestion") if k in body}


def read_lines(path):
    p = Path(path)
    if not p.exists():
        return []
    return [l for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def parse(line):
    try:
        return json.loads(line)
    except ValueError:
        return None


def complete(rec):
    return isinstance(rec, dict) and all(f in rec for f in FIELDS)


def query_body(q):
    return json.dumps({"query": q}).encode("utf-8")


def one(raw, log):
    before = len(read_lines(log))
    status, body, secs = post(raw)
    lines = read_lines(log)
    added = len(lines) - before
    rec = parse(lines[-1]) if added == 1 else None
    return {"sent": raw.decode("utf-8"), "status": status, "client_s": secs,
            "response": summarize(body), "lines_added": added, "record": rec}


def run_c1(log):
    if read_lines(log):
        sys.exit("criterion 1 needs an empty log file: start the server with a new AI201_LOG_PATH")
    plan = MATCHING[:4] + NO_MATCH[:3] + [None] * 3
    rows = [one(query_body(q) if q else b"{}", log) for q in plan]
    ok = sum(1 for r in rows if r["lines_added"] == 1 and complete(r["record"])
             and r["record"]["http_status"] == r["status"])
    note = f"lines in log: {len(read_lines(log))} (must be 10)"
    return ok, 10, ok == 10, rows, note


def raw_for(t, i):
    if t == "a":
        return b"{}"
    if t == "e":
        return b"[1]"
    q = NO_MATCH[i % len(NO_MATCH)] if t == "b" else MATCHING[i % len(MATCHING)]
    return query_body(q)


def run_c2(log, t):
    outcome, status = EXPECT[t]
    rows = [one(raw_for(t, i), log) for i in range(10)]
    ok = 0
    for r in rows:
        rec = r["record"]
        if (r["lines_added"] == 1 and complete(rec) and rec["outcome"] == outcome
                and rec["http_status"] == status and r["status"] == status):
            ok += 1
    return ok, 10, ok == 10, rows, f"type {t}: expected outcome={outcome}, status={status}"


def run_c3(stderr_path):
    rows, ok = [], 0
    for i in range(10):
        status, body, secs = post(query_body(MATCHING[i % len(MATCHING)]))
        good = (status == 200 and isinstance(body, dict)
                and body.get("error") is None and bool(body.get("fit_card")))
        ok += good
        rows.append({"i": i + 1, "status": status, "client_s": secs,
                     "response": summarize(body), "response_ok": good})
    time.sleep(1)
    data = Path(stderr_path).read_bytes()
    text = data.decode("utf-16") if data[:2] in (b"\xff\xfe", b"\xfe\xff") else data.decode("utf-8", "replace")
    hits = text.count("could not write the log")
    note = f"stderr lines saying the log could not be written: {hits} (must be 10)"
    return ok, 10, ok == 10 and hits == 10, rows, note


def run_c4(log):
    if read_lines(log):
        sys.exit("criterion 4 needs an empty log file: start a fresh server with a new AI201_LOG_PATH")
    cold_sent = time.monotonic()
    post(query_body(MATCHING[0]))          # cold start, discarded
    prev = cold_sent
    rows = []
    for i in range(WARM_N):
        wait = prev + GAP_S - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        prev = time.monotonic()
        status, body, secs = post(query_body(MATCHING[i % len(MATCHING)]))
        rows.append({"i": i + 1, "status": status, "client_s": secs})
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{WARM_N} sent", flush=True)
    lines = read_lines(log)
    durations = []
    for row, line in zip(rows, lines[1:]):
        rec = parse(line)
        if complete(rec):
            row["duration_s"], row["outcome"] = rec["duration_s"], rec["outcome"]
            durations.append(rec["duration_s"])
    on_time = sum(1 for d in durations if d <= ON_TIME_S)
    not_ok = sum(1 for r in rows if r.get("outcome") != "ok")
    note = f"log lines {len(lines)} (expected {WARM_N + 1}); outcome not ok: {not_ok}"
    if durations:
        note += (f"; duration_s min {min(durations)}, median {statistics.median(durations)}, "
                 f"max {max(durations)}")
    return on_time, WARM_N, on_time >= WARM_MIN_ON_TIME, rows, note


def run_c5(log):
    rows = [one(query_body(q), log) for q in NO_MATCH]
    ok = 0
    for r in rows:
        resp, rec = r["response"], r["record"]
        if (r["status"] == 200 and resp.get("fit_card") is None
                and resp.get("outfit_suggestion") is None and r["lines_added"] == 1
                and complete(rec) and rec["prompt_tokens"] == 0 and rec["output_tokens"] == 0):
            ok += 1
    return ok, 10, ok == 10, rows, "no-match queries, price ceiling $5"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("criterion", type=int, choices=[1, 2, 3, 4, 5])
    ap.add_argument("trial", type=int)
    ap.add_argument("--log")
    ap.add_argument("--type", choices=list("abcde"))
    ap.add_argument("--stderr")
    ap.add_argument("--phase", default="before", choices=["before", "after"])
    a = ap.parse_args()
    c = a.criterion
    if c != 3 and not a.log:
        sys.exit("--log is required")
    if c == 2 and not a.type:
        sys.exit("--type a|b|c|d|e is required for criterion 2")
    if c == 3 and not a.stderr:
        sys.exit("--stderr is required for criterion 3")
    try:
        urllib.request.urlopen(BASE + "/health", timeout=5).read()
    except Exception:
        sys.exit("serve.py is not answering on localhost:5000")

    if c == 1:
        score, total, met, rows, note = run_c1(a.log)
    elif c == 2:
        score, total, met, rows, note = run_c2(a.log, a.type)
    elif c == 3:
        score, total, met, rows, note = run_c3(a.stderr)
    elif c == 4:
        score, total, met, rows, note = run_c4(a.log)
    else:
        score, total, met, rows, note = run_c5(a.log)

    typ = a.type or ""
    out = Path("results") / "capstone" / a.phase
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"c{c}{typ}_t{a.trial}.json"
    path.write_text(json.dumps({"criterion": c, "type": a.type, "trial": a.trial,
                                "score": score, "of": total,
                                "target_met_this_trial": met, "note": note,
                                "details": rows}, indent=2), encoding="utf-8")
    label = f"criterion {c}" + (f" type {a.type}" if a.type else "")
    print(f"{label} trial {a.trial}: {score}/{total}  target met this trial: {'yes' if met else 'no'}")
    print(note)
    print(f"saved {path}")


if __name__ == "__main__":
    main()