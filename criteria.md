# Capstone criteria (Project 9)

Written before any capstone results exist. The run log in the README uses these
exact numbers. A "trial" is one complete run of the check, and I do three of
them with nothing changed in between.

## 1. Every /ask request leaves exactly one complete record

In one trial I start the server with an empty log file and send 10 /ask
requests one at a time: 4 matching queries, 3 queries that match nothing, and
3 requests with no query. The number of lines in logs/requests.jsonl equals 10,
each line parses as JSON, and each has all twelve fields: timestamp,
request_id, route, http_status, query, outcome, error, duration_s, queued,
prompt_tokens, output_tokens, selected_item_id (a null value counts as
present).

Target: 10 of 10 requests leave exactly one such record, in each of 3 trials.

Why this target and not stricter or looser: The log is the only way I can find
out what the server did after the fact, so a missing record is a failure I
cannot see, and a doubled record corrupts every average I take from it.
Nothing in this check depends on model wording, so there is no reason to allow
one miss in ten. Looser would let a dropped record hide.

## 2. Each failure type is logged with its own outcome and status

I trigger each of five failures 10 times and read the record:
(a) a request with no query: outcome bad_request, http_status 400;
(b) a query that matches nothing: outcome nothing_found, http_status 200;
(c) the server started with a non-empty invalid GEMINI_API_KEY: outcome
    model_unavailable, http_status 200;
(d) mcp_server.py renamed while the server runs: outcome mcp_unavailable,
    http_status 200;
(e) a request body of [1], a JSON array instead of an object: outcome
    server_error, http_status 500.
For a failure to count, the record's outcome and http_status both equal the
values above, and the http_status equals the status the caller received.

Target: 10 of 10 attempts for each of the five types, in each of 3 trials.

Why: request_log.classify() reads the first words of session["error"] to
decide the outcome, and agent.py returns the model and MCP failures as normal
sessions, so a reworded error message would silently turn them into
server_error. A wrong label would hide which stage broke. The failures are
triggered the same way every time, so I expect all ten.

## 3. A failed log write does not change the response

With AI201_LOG_PATH set to an existing directory, so the file cannot be
opened, I send 10 matching /ask requests. Each returns http_status 200 with a
null error and a non-null fit_card, and the server's stderr shows the "could
not write the log" line for each.

Target: 10 of 10 requests, in each of 3 trials.

Why: logging is there to observe the system, so if it can break an answer the
caller loses the thing they came for. One failed answer in ten is a failure of
the design, not noise, and the check is deterministic.

## 4. Warm requests finish within a stated time

A warm request is any /ask request other than the first one after the server
starts, sent at least 10 seconds after the previous request was sent. For each
trial I start the server fresh with AI201_CACHE=0, send one request that I
discard (the cold start), then send 100 warm requests with matching queries.
Each request counts as on time if duration_s in logs/requests.jsonl is at most
4.7 seconds.

Target: at least 95 of the 100 warm requests are on time, in each of 3 trials.

Why this target and not stricter or looser: In my Milestone 3 log the warm
unpaced requests took 2.425 to 2.83 s, so 4.7 s leaves about 1.9 s above the
slowest, which a single slow model reply or a rate-limit retry would use up.
That makes it possible to fail. The cold first request took 4.302 s, so the
threshold sits just above it, and the definition excludes it. The 10 s gap
keeps me at 6 runs a minute, under the 15 model calls a minute limit, because
the one 43.12 s request came from sending requests faster than that. A user
would tolerate five slow replies in a hundred but not many more, so 95.
Stricter would fail on a normal slow reply; looser would not catch retries.

## 5. A query that matches nothing still stops before suggest_outfit

For 10 queries, each asking for a different kind of item with a price ceiling
of $5 (the cheapest listing is $12), the response has fit_card null and
outfit_suggestion null, and the log record shows prompt_tokens 0 and
output_tokens 0.

Target: 10 of 10 queries, in each of 3 trials.

Why: This is the original behavior the extension must not break. If a no-match
run reached the model, it would spend tokens and return a made-up outfit for
nothing. The search is local, so there is no randomness in this one.