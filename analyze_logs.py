import json
import statistics
from pathlib import Path


def load(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]


for phase in ("before", "after"):
    for t in (1, 2, 3):
        p = Path(f"results/capstone/{phase}/log_T_t{t}.jsonl")
        if not p.exists():
            continue
        recs = load(p)[1:]  # drop the cold request
        ok = [r for r in recs if r["outcome"] == "ok"]
        timeouts = [r for r in recs if r["outcome"] != "ok" and "timed out" in (r["error"] or "")]
        d = [r["duration_s"] for r in ok]
        line = (f"{phase} t{t}: warm records {len(recs)}, ok {len(ok)}, "
                f"not ok {len(recs) - len(ok)} (timed out: {len(timeouts)})")
        if len(ok) > 2:
            line += (f"; ok median {statistics.median(d):.2f}s, max {max(d):.2f}s, "
                     f"over 4.7s: {sum(1 for x in d if x > 4.7)}")
            try:
                line += f"; corr(duration, output_tokens) {statistics.correlation(d, [r['output_tokens'] for r in ok]):.2f}"
            except statistics.StatisticsError:
                pass
        print(line)