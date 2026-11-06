# Acceptance criteria: FitFindr

Five criteria that say what "working" means for this agent, written
**before** any results existed.

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:** I picked 4 of 5 rather than 5 of 5 because two of the three tools call a model, which can fail or return unusable output on a given try. My search is also a plain keyword match, so some phrasings will miss even when a listing exists.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:** I picked 5 of 5 because this path never reaches a model. It's a plain check on an empty list in `run_agent`, so the outcome is the same every time, and anything less than 5 of 5 would mean a bug in the branch.

---

## 3. The selected item reaches the next tool unchanged

In a happy-path run, the `id` in `session["selected_item"]` equals the `id` of the item passed into `suggest_outfit`, in 5 of 5 tries.

**Why this target:** Search and session handling are plain code with no model involved, so this should never vary. Anything below 5 of 5 would mean a bug in how I read values back out of the session.

---

## 4. The fit card is short and includes the price

Across 5 runs on the same item, every fit card is 1 to 3 sentences and includes the price, in 4 of 5 tries.

**Why this target:** The model gives different words each run, so 5 of 5 is too strict and one bad sample shouldn't fail the whole criterion. A card without a price, or longer than 3 sentences, counts as a FAIL.

> **Note (not a revision):** I left this criterion as written. It
> passed 5 of 5 before and after my change, but "includes the price" let a card
> through that spelled the price out in words ("eighteen dollars") with no `$`.
> The gap was in the model output, so I fixed the `create_fit_card` prompt
> rather than the wording. If I rewrote it, it would read "includes the price
> written with a $ sign".

---

## 5. The price filter respects the ceiling

For a query with `max_price=30`, every listing returned by `search_listings` has `price <= 30`, in 5 of 5 tries.

**Why this target:** The price filter is a plain numeric comparison with no model involved, so anything below 5 of 5 would mean a bug.
