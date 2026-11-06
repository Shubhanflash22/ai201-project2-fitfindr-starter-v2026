# Running FitFindr

## Setup

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then paste your key into .env
python test.py
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env         # then paste your key into .env
python test.py
```

Setup is done when `python test.py` passes. Activate the virtual environment
every time a new terminal is opened; `(.venv)` should appear at the start of the
prompt.

## First run

```bash
python app.py fields                    # what a listing and a wardrobe item hold
python app.py listings --full -n 6      # read six listings all the way through
python app.py examples                  # queries worth trying
python app.py ask 'vintage graphic tee under $30'
```

Quote queries with single quotes on every operating system. In PowerShell,
`"vintage graphic tee under $30"` in double quotes silently becomes
`vintage graphic tee under `, because PowerShell reads `$30` as a variable and
substitutes nothing. The search then runs with no price ceiling and no error.
Single quotes are literal in PowerShell, bash and zsh alike.

## Commands

| Command | What it does |
|---|---|
| `python test.py` | Checks the environment |
| `python app.py fields` | The fields a listing and a wardrobe item have |
| `python app.py listings` | Browse the data. `--full` for whole records, `-n` for how many |
| `python app.py examples` | Queries worth trying, including one that matches nothing |
| `python app.py ask '...'` | Run the agent on one query (single quotes) |
| `python app.py ask` | Keep asking until an empty line |
| `python agent.py` | Runs both example paths: one that matches, one that can't |
| `python mcp_server.py` | Starts the MCP server |
| `python mcp_client.py` | Asks the server what it offers |
| `python run_eval.py --label before` | Runs every scenario five times and writes the run log to `results/` |
| `python serve.py` | Serves the agent over HTTP instead of exiting |

Flags on `ask`:

| Flag | What it does |
|---|---|
| `--trace` | Print the loop step by step |
| `--empty-wardrobe` | Run as a user with nothing saved |

## Where everything lives

| File | What it does |
|---|---|
| `config.py` | Settings. TEMPERATURE and the cache are at the top |
| `tools.py` | The tools: `search_listings`, `suggest_outfit`, `create_fit_card`, and the stretch `compare_prices` |
| `agent.py` | The planning loop and the session |
| `generate.py` | The only thing that calls out to a model. Handles pacing and quota |
| `trace.py` | The trace helper, and the loop's stop condition |
| `app.py` | The command line |
| `serve.py` | The same agent over HTTP |
| `mcp_server.py` | The MCP server that exposes `search_listings` |
| `mcp_client.py` | Calling an MCP tool from the agent |
| `scenarios.py` | What the tests run |
| `run_eval.py` | Runs the scenarios repeatedly and writes the run log |
| `check_cards.py`, `check_compare.py`, `check_price.py` | Small scripts that check fit cards and the price filter against saved results |
| `criteria.md` | The five acceptance criteria |
| `data/` | 40 listings and the wardrobe schema |
| `utils/data_loader.py` | Loading the data |
| `results/` | Run logs written by `run_eval.py` |

## Fit cards that come out identical

Both settings are at the top of `config.py`. If fit cards are word-for-word
identical every time, it is one of:

- **`CACHE_ENABLED`:** identical prompts reuse the answer already received.
  `run_eval.py` turns it off automatically.
- **`TEMPERATURE`:** at `0.0` the model gives the same words every time. It
  ships at `0.9`.

## Rate limits

Two of the three tools call the model, so one agent run is several requests,
and a few runs back to back can cross the per-minute limit. `generate.py`
handles it:

- It paces itself and says when it is waiting. A pause is not a bug.
- It reuses answers to prompts already sent, while building.
- It stops if a session makes an unreasonable number of calls. For an agent,
  that usually means a loop isn't ending.
- It counts calls and prints the total on exit.

`config.MAX_ITERATIONS` is the loop's own stop condition.

## Troubleshooting

| What you see | What it means |
|---|---|
| `No GEMINI_API_KEY found` | No `.env`, or the key wasn't pasted in. On Windows check it didn't save as `.env.txt` |
| A message saying the model couldn't be reached | Usually a bad key |
| `[rate limit] ... Waiting 34s` | Working as intended |
| `[serve] another request is still running` | `serve.py` answers one request at a time; this one is queued |
| `QuotaGuard: This session has made 300 requests` | A loop isn't ending. Find it before raising the budget |
| `The loop ran 11 times, past MAX_ITERATIONS` | Same problem, caught earlier |
| `The server doesn't offer a tool called '...'` | The name doesn't match what `mcp_server.py` registers |
| MCP returns a string where a list was expected | The call isn't going through `mcp_client.call_tool`, which unwraps it |
| `--trace` prints nothing | `run_agent` has no `trace.step()` calls |
| `IncompleteFieldDefinitionWarning: Field 'lifespan'` | Harmless noise from the MCP library's dependencies |
| A price ceiling is being ignored | Double quotes in PowerShell made `$30` vanish. Use single quotes |
| `UnicodeEncodeError: 'charmap' codec can't encode` | Should not happen, since `config.py` sets the console to UTF-8. It means a file is running without importing `config` |

## Running it as a service

`serve.py` is the same `run_agent()` behind two HTTP routes, so it can stay up
and wait for requests.

```bash
python serve.py
curl -X POST http://localhost:5000/ask \
  -H 'Content-Type: application/json' \
  -d '{"query": "vintage graphic tee under $30"}'
```

On a host, the start command is `gunicorn serve:app`.

| Thing | What it means |
|---|---|
| `PORT` | The host sets the port. Both `serve.py` and `gunicorn` read it, and `serve.py` falls back to `5000` locally. Don't hard-code a port |
| `POST /ask` | `{"query": "...", "wardrobe": {...}}`, wardrobe optional. Returns the session dict, `error` included |
| `GET /health` | Says `ok` if the app is awake |
| One request at a time | A second request waits for the first. An MCP tool call starts a whole second Python process, the free tier's 512 MB has no room for two at once, and `generate.py`'s rate-limit counting assumes one caller. The reasoning is in `serve.py` |
| `gunicorn serve:app`, exactly | Not `-k gevent`, `-k eventlet`, or uvicorn. `mcp_client.call_tool` uses `asyncio.run()`, which won't start inside a running event loop, so an async worker breaks every MCP call |
| The first request is slow | The free tier sleeps after about fifteen minutes of no traffic, and waking it takes around a minute |

`serve.py` has no logging or timing in it.

`results/` is not in `.gitignore`, so run logs are committed with the project.
