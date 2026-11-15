# FitFindr

Shubhan Mital - Project: FitFindr

**Stretch feature:** a fourth tool, `compare_prices`, that compares the selected item's price with the average of other listings in the same category.

---

## What This Does

FitFindr is a thrifting agent. A user describes what they want in plain language, like "a vintage graphic tee under $30, size M," and the agent searches a file of secondhand listings for matches. It then takes the top match, works out outfit ideas to go with it from the user's wardrobe (or gives general styling advice if the wardrobe is empty), and writes a short caption the user could post. If nothing matches, the agent stops and tells the user what to change, such as the size or the price ceiling, instead of continuing with nothing.

## Tool Inventory

### `search_listings`

- **What it does:** Filters the listings file by price ceiling and size, scores what's left by keyword overlap with the query, and returns the matches best first.
- **Inputs:** `description` (str), `size` (str or None), `max_price` (float or None). `None` means that filter is skipped.
- **Returns:** A list of listing dicts, best match first (ties go to the cheaper listing), at most `config.SEARCH_RESULT_LIMIT` (10). Each dict has the full listing fields: `id` (str), `title` (str), `description` (str), `category` (str), `style_tags` (list[str]), `size` (str), `condition` (str), `price` (float), `colors` (list[str]), `brand` (str or None), `platform` (str).
- **When it has nothing:** An empty list `[]`. Never `None`, and it never raises an exception. A query made only of stopwords also returns `[]`.
- **Matching rules:** Keywords are lowercased with stopwords removed ("a", "under", "in", "size", and so on) and a crude plural strip ("tees" becomes "tee"). A listing's score is the number of query keywords found in its title, description, category, `style_tags`, or `colors`. Listings scoring zero are dropped. `size` matches case-insensitively as a whole token, so "M" matches `M` and `S/M` but not `L` or `XL (oversized)`, and never as a substring. `price` must be less than or equal to `max_price`.

### `suggest_outfit`

- **What it does:** Asks the model for two outfit ideas that pair the new item with pieces from the user's wardrobe.
- **Inputs:** `new_item` (dict, one listing returned by `search_listings`), `wardrobe` (dict with one key, `items`, a list of dicts each holding `id` (str), `name` (str), `category` (str: tops, bottoms, outerwear, shoes, or accessories), `colors` (list[str]), `style_tags` (list[str]), `notes` (str or None)).
- **Returns:** A non-empty string of two outfit ideas, each naming the new item and the wardrobe pieces it pairs with.
- **When it has nothing:** If `wardrobe["items"]` is empty (`{"items": []}`), it returns a string of general styling advice for the new item instead of failing. A `notes` value of `None` is left out of the prompt. If the model call fails, `generate()` raises `ModelUnavailable`, which the loop catches, and the loop shows the user a message saying the model couldn't be reached.

### `create_fit_card`

- **What it does:** Asks the model for a short, postable social-media caption for the find.
- **Inputs:** `outfit` (str, the output of `suggest_outfit`), `new_item` (dict, the selected listing).
- **Returns:** A non-empty string of two or three sentences in a casual voice that mentions the item, its price, and its platform.
- **When it has nothing:** If `brand` is `None`, the prompt leaves the brand out and the card is still written. If `outfit` is empty or whitespace, it writes a caption from `new_item` alone. If the model call fails, `generate()` raises `ModelUnavailable`, which the loop catches, same as `suggest_outfit`.

### `compare_prices` (stretch)

- **What it does:** Compares the selected item's price with the average price of the other listings in the same category.
- **Inputs:** `item` (dict, the selected listing).
- **Returns:** A dict with `category` (str), `average` (float or None), `count` (int), `difference` (float or None, item price minus average), and `verdict` (str, a phrase saying the item is cheaper than, pricier than, or about the average for its category, such as "cheaper than the tops average").
- **When it has nothing:** If no other listing shares the category, `average` and `difference` are `None`, `count` is `0`, and `verdict` says there is nothing to compare against.

## Planning Loop

**Branch rule:** If `search_listings` returns an empty list, put a message in `session["error"]` that names what to change (broader keywords, drop or change the size, raise the price ceiling), leave `session["fit_card"]` as `None`, and return the session without calling `suggest_outfit`. Otherwise, store the first result in `session["selected_item"]` and continue to `suggest_outfit`, then `create_fit_card`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** Regex, with no model call (`agent.py::parse_query`). A price such as "under $30" becomes `max_price` (float), a size such as "size M" or a trailing ", M" becomes `size` (str), and the leftover words become `description`. Phrasing it hasn't seen, like "under thirty dollars" or "size 8", parses to no price or size, so that filter is silently skipped.

**What moves through the session:** In order:

1. `session["parsed"]` (description, size, max_price)
2. `session["search_results"]` (the list from `search_listings`). If it is empty, `session["error"]` is set and the run stops.
3. `session["selected_item"]` (the first result)
4. `session["price_check"]` (from `compare_prices`)
5. `session["outfit_suggestion"]` (from `suggest_outfit`, which reads `selected_item`)
6. `session["fit_card"]` (from `create_fit_card`, which reads the outfit and `selected_item`)

## Sample Run

**One full query**

```
PS> python app.py ask 'vintage graphic tee under $30, size M'

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Outfit 1 (Streetwear Edge):
Pair the Y2K Baby Tee with your baggy straight-leg jeans (dark wash, indigo) and your vintage black denim jacket. Complete the look with your chunky white sneakers and black crossbody bag.

Outfit 2 (Casual Contrast):
Layer the Y2K Baby Tee under your oversized grey crewneck sweatshirt, matched with your wide-leg khaki trousers. Finish with your black combat boots and brown leather belt.

  Fit card: Just scored this little butterfly baby tee on depop for eighteen dollars and the nostalgic early two thousands mall punk energy is immaculate. I am definitely styling it with my baggy dark wash jeans and chunky sneakers for that effortless streetwear look.

0 model calls this session, 2 served from cache
```

**The same agent with a query that matches nothing**

```
PS> python app.py ask 'designer ballgown size XXS under $5'

  Nothing in the listings matched description 'designer ballgown', size XXS, under $5.
Things to change: try broader words — 'jacket' finds more than 'cropped corduroy jacket'; drop the size, or try a neighbouring one; raise the price ceiling above $5.

0 model calls this session
```

**The tools, tested one at a time**

`search_listings`, normal case:

```
PS> python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
[{'id': 'lst_017', 'title': 'Mesh Long-Sleeve Top — Black', 'description': 'Sheer black mesh long-sleeve. Great for layering under a graphic tee or over a bralette. Stretchy material, fits true to size.', 'category': 'tops', 'style_tags': ['y2k', 'grunge', 'goth', 'layering'], 'size': 'S/M', 'condition': 'excellent', 'price': 15.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_033', 'title': 'Vintage Band Tee — Faded Grey', 'description': 'Faded grey band-style tee with distressed graphic. Crew neck. Fits boxy. Well-loved but no holes or major damage.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'band tee', 'graphic tee', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 19.0, 'colors': ['grey', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_012', 'title': 'Oversized Crewneck Sweatshirt — Vintage Navy', 'description': 'Perfectly faded navy crewneck. Genuinely vintage — not manufactured distressed. Ribbed cuffs and hem. No graphics, clean.', 'category': 'tops', 'style_tags': ['vintage', 'basics', 'oversized', 'classic'], 'size': 'XL (fits oversized)', 'condition': 'good', 'price': 20.0, 'colors': ['navy'], 'brand': None, 'platform': 'thredUp'}, {'id': 'lst_015', 'title': 'Vintage Graphic Hoodie — Faded Black', 'description': 'Faded black pullover hoodie with barely-visible vintage graphic on the chest. Cozy interior. Some pilling but adds to the worn-in look.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'graphic', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 26.0, 'colors': ['black', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_011', 'title': 'Low-Rise Cargo Pants — Khaki', 'description': 'Y2K era low-rise cargo pants. Lots of pockets. Khaki color, slightly distressed at the hems. Great for layering with a long tee.', 'category': 'bottoms', 'style_tags': ['y2k', 'cargo', '2000s', 'streetwear'], 'size': 'W29', 'condition': 'fair', 'price': 27.0, 'colors': ['khaki', 'tan'], 'brand': None, 'platform': 'poshmark'}]
```

`search_listings`, empty case (exactly `[]`):

```
PS> python -c "from tools import search_listings; print(search_listings('designer ballgown', size='XXS', max_price=5))"
[]
```

`search_listings`, size matching (only `S/M` and `M`, no `L` or `XL`):

```
PS> python -c "from tools import search_listings; print([(i['id'], i['size']) for i in search_listings('tee', size='M')])"
[('lst_017', 'S/M'), ('lst_002', 'S/M')]
```

`suggest_outfit`, example wardrobe (names specific wardrobe pieces):

```
PS> python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
Outfit 1: Casual Streetwear
Pair the Vintage Levi's 501 Jeans with the White ribbed tank top, the Black cropped zip hoodie worn open, and the Chunky white sneakers. Add the Black crossbody bag to finish the look.

Outfit 2: Relaxed Vintage
Style the Vintage Levi's 501 Jeans with the Oversized grey crewneck sweatshirt, cinched at the waist with the Brown leather belt, and the Black combat boots. Throw on the Vintage black denim jacket over top.
```

`suggest_outfit`, empty wardrobe (general advice, no crash):

```
PS> python -c "from tools import suggest_outfit; from utils.data_loader import get_empty_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_empty_wardrobe()))"
Casual Streetwear Look

Pair the vintage Levi's with a classic white boxy crewneck t-shirt tucked in casually. Layer an oversized black vintage leather bomber jacket or a denim jacket over top for a textured double-denim moment. Finish the outfit with well-worn white canvas low-top sneakers like Converse or Vans, a black canvas belt, and a minimalist silver pendant necklace for an effortless, everyday vibe.

Elevated Casual Look

Tuck a fitted black ribbed turtleneck bodysuit into the high-waisted medium wash denim to define your shape. Throw on an oversized houndstooth or camel wool trench coat for a sharp, contrasting silhouette. Complete the look with pointed-toe black leather boots, a structured black leather shoulder bag, and simple gold hoop earrings to easily transition the classic jeans from day to night.
```

`create_fit_card`, cache off so runs can differ. Runs 1 and 2 use the same item; run 3 uses an item with `brand=None`:

```
PS> $env:AI201_CACHE="0"
PS> python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
Finally scored these vintage Levi's 501 jeans in a dreamy medium wash on depop for just 38 dollars. They give off such an effortless 90s off-duty model vibe. I am definitely living in these with my favorite white sneakers from now on.
PS> python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
Just scored these vintage medium wash Levi's 501 jeans on depop for $38 and I am never taking them off. They have that perfectly broken-in 90s slouch that is impossible to fake. Throwing them on with some crisp white sneakers and I am officially set for the weekend.
PS> python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[1]))"
Scored this cute little Y2K butterfly baby tee on depop for just eighteen dollars and I am obsessed. It has that ultimate early 2000s mallrat vibe that I can not get enough of. I am definitely throwing it on with my favorite jeans and white sneakers for my coffee run tomorrow.
PS> Remove-Item Env:AI201_CACHE
```

`compare_prices` (stretch):

```
PS> python -c "from tools import compare_prices; from utils.data_loader import load_listings; print(compare_prices(load_listings()[1]))"
{'category': 'tops', 'average': 22.0, 'count': 14, 'difference': -4.0, 'verdict': 'cheaper than the tops average'}
```

## Run Log - Before

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Item in session matches item passed on | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card is 1 to 3 sentences and includes the price | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Price ceiling respected | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

**Real output from one try per criterion** (from `python run_eval.py --label before`):

**Criterion 1: matching query completes (try 1).** Produced by `agent.py::run_agent`, using `tools.py::search_listings` (via `mcp_server.py`), `suggest_outfit`, and `create_fit_card`.

```
[2] search_listings (via MCP)
      →    10 match(es)
[3] select_item
      out: Y2K Baby Tee — Butterfly Print ($18.0, depop)
[5] suggest_outfit
      →    10 wardrobe item(s)
[6] create_fit_card
      out: Found this butterfly print Y2K baby tee on depop for eighteen dollars and the total bratz doll energy is unrea…
  try 1: completed — fit card 227 chars
```

**Criterion 2: impossible query stops early (try 1).** Produced by `agent.py::run_agent` (the branch) and `agent.py::_nothing_found_message`.

```
[2] search_listings (via MCP)
      out: [] (empty)
      →    0 match(es)
[3] branch
      →    search returned []: stopping before suggest_outfit
  try 1: stopped early — Nothing in the listings matched description 'designer ballgo
```

**Criterion 3: selected item matches item passed on (try 1).** Produced by `agent.py::run_agent`.

```
[3] select_item
      out: Denim Jacket — Light Wash, Cropped ($42.0, poshmark)
[5] suggest_outfit
      in:  Denim Jacket — Light Wash, Cropped ($42.0, poshmark)
```

**Criterion 4: fit card length and price (try 1).** Produced by `tools.py::create_fit_card`, read with `check_cards.py`.

```
TRY 1 | sentence marks: 3 | $ sign: False | price in words: True
Scored this little butterfly print Y2K baby tee on depop for just 18 dollars and I am obsessed. The nostalgic street style vibe is immaculate with baggy jeans and a cropped hoodie. It also looks so cute with wide-leg trousers and combat boots for that sweet-yet-edgy contrast.
```

**Criterion 5: price ceiling respected (try 1).** Produced by `tools.py::search_listings`, checked with `check_price.py`.

```
TRY 1 | results: 3 | prices: [24.0, 27.0, 30.0] | over $30: []
```

## Verdicts

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | A matching query completes all three tools | 4 of 5 | MET (5/5) | All five tries of 'vintage graphic tee under $30' ran search, outfit and fit card and returned a fit card. |
| 2 | An impossible query stops before the second tool | 5 of 5 | MET (5/5) | All five tries of the ballgown query ended at the branch, never reached `suggest_outfit`, and returned a message naming what to change. |
| 3 | Item in session matches item passed on | 5 of 5 | MET (5/5) | In all five tries the item at `select_item` and the item shown going into `suggest_outfit` were the same listing. The trace shows title, price and platform, not the literal id. |
| 4 | Fit card is 1 to 3 sentences and includes the price | 4 of 5 | MET (5/5) | I counted sentence marks (2 or 3 in every card) and checked each card for the price. Every card had it, written in words. |
| 5 | Price ceiling respected | 5 of 5 | MET (5/5) | In all five tries of 'denim jacket under $30', every returned price was 30 or less (24, 27, 30). |

## Diagnoses

No criterion was missed, so there is no miss to diagnose. Reading the runs plainly, I think my targets were low in places, and the evidence shows three weak spots my criteria did not catch:

- **Criterion 4 is the one I'd tighten.** It says the card "includes the price," and every card did, but always in words ("eighteen dollars," "18 dollars") and never as "$18." A check for a dollar sign would have failed 5 of 5. The criterion was too loose, and the gap is in the model's output: the prompt in `create_fit_card` never asks for a `$`.
- **Search relevance is looser than my criteria measure.** For 'denim jacket under $30' the search returned shorts, a vest and jeans, because the keyword "denim" matches on its own. Criterion 5 only checks price, so it passed. Earlier, 'graphic tee' ranked a mesh top above real graphic tees, because every match tied on score and the cheaper one won. Place: `search_listings`. Mechanism: ranking by plain keyword overlap, with ties broken by price.
- **Criterion 3 is solid but its evidence is indirect.** The trace prints title, price and platform, not the id, so the check compares those instead of the literal `id`.

## Loop Trace

**Happy path**

```
$ python app.py ask 'vintage graphic tee under $30, size M' --trace
[1] parse_query
      in:  vintage graphic tee under $30, size M
      out: dict with keys: description, size, max_price
[2] search_listings (via MCP)
      in:  dict with keys: description, size, max_price
      out: 8 items: Y2K Baby Tee — Butterfly Print, Mesh Long-Sleeve Top — Black, Henley Long Sleeve — Washed Burgundy … +5 more
      →    8 match(es)
[3] select_item
      out: Y2K Baby Tee — Butterfly Print ($18.0, depop)
[4] compare_prices
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      out: dict with keys: category, average, count, difference, verdict
[5] suggest_outfit
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      out: Outfit 1 (Streetwear Edge): Pair the Y2K Baby Tee with your baggy straight-leg jeans (dark wash, indigo) and y…
      →    10 wardrobe item(s)
[6] create_fit_card
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      out: Just scored this little butterfly baby tee on depop for eighteen dollars and the nostalgic early two thousands…
```

**Empty search** (visibly shorter, because the loop stops at the branch)

```
$ python app.py ask 'designer ballgown size XXS under $5' --trace
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: dict with keys: description, size, max_price
[2] search_listings (via MCP)
      in:  dict with keys: description, size, max_price
      out: [] (empty)
      →    0 match(es)
[3] branch
      →    search returned []: stopping before suggest_outfit
```

**On the MCP move:** I registered `search_listings` in `mcp_server.py` with a description written for a reader who can't see the code (types, units, and the empty case) and swapped the direct call in `agent.py::run_agent` for `mcp_client.call_tool`. The result was the same: the matching query returned the same top item as before, and the empty query still returned `[]`. The only visible change is the trace label, `search_listings (via MCP)`, and each call is slower because the server starts and stops on every call.

## The Improvement

**What I changed:** In `tools.py::create_fit_card`, I added one sentence to the end of the prompt: "Write the price with a dollar sign and digits, like $18, never in words." Nothing else changed in the code. The "after" run used the same scenarios, the same agent, and caching off.

**Which failure it was meant to fix:** Criterion 4. My criterion said the fit card "includes the price," and it passed 5 of 5 before the change, but every card wrote the price in words ("eighteen dollars," "18 dollars") and none used a `$` sign. That is a model-output problem: the `create_fit_card` prompt never said how to write the price, so the model chose words. A stricter check for a dollar sign would have failed 5 of 5, so this was the weakest point in my results.

## Run Log - After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Item in session matches item passed on | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card is 1 to 3 sentences and includes the price | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Price ceiling respected | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

**Did it help, and how do I know:** Yes, but the table doesn't show it. Every criterion was MET 5 of 5 before and after, because criterion 4 as I wrote it ("includes the price") was already passing with the price in words. The change shows up in a stricter check on the same fit cards: before, 0 of 5 cards contained a `$` sign and 5 of 5 spelled the price out; after, 5 of 5 contain a `$` sign and 0 of 5 use words. I counted this with `check_compare.py` on the saved results files (`results/run_2026-10-10_1249_before.md` and `results/run_2026-10-10_1305_after.md`). Sentence counts stayed at 2 or 3 per card, so the change didn't break the length limit. The sample is small (5 cards from one item), and the model's output varies, so I can't promise 5 of 5 on every item. What the run does show is that adding one sentence to the prompt moved the price format from 0 of 5 to 5 of 5.

## What's Still Broken

No criterion is missed, but my diagnoses left these open:

- **Search ranking is plain keyword overlap.** 'denim jacket under $30' still returns shorts, a vest and jeans because "denim" matches on its own, and ties go to the cheaper listing, which is how a mesh top outranked real graphic tees. Fixing it would mean weighting title and category matches above description matches. I stopped because my criteria only measure price, so the problem never showed up as a failure.
- **`parse_query` silently skips filters it doesn't recognize.** "Under thirty dollars" and "size 8" parse to no price or size, so the user gets results that ignore what they asked for, with no warning. The fix would be to tell the user which filters were applied.
- **Criterion 3 compares title, price and platform, not the id.** Adding the id to the trace would make the check exact.
- **The improvement is measured on 5 cards from one item.** I can't promise the `$` format holds on every item.
- **Each MCP call starts and stops the server,** so every search is slower than the direct call was. Keeping one server connection open would fix that.

## What I'd Do Differently

I'd reword criterion 4 to "includes the price written with a $ sign," because that is something I can score, and the original wording passed 5 of 5 while hiding the real gap.

I'd also add a criterion that checks whether the search results are relevant, not only whether they are under the price ceiling. Criterion 5 only checks price, so loosely matching results (shorts and a vest for 'denim jacket') passed it.

## How I Used AI

**Moment 1: Tool Inventory spec**

- *What I asked for:* I asked Claude to draft the text for my Tool Inventory spec for my three tools, and to help me decide a few things, including the inputs and what each tool returns when it has nothing.
- *What came back:* It specified `wardrobe` as a plain list of dicts, so the empty case was `[]`.
- *What I changed:* `data/wardrobe_schema.json` shows the wardrobe is a dict with an `items` key, so the empty case is `{"items": []}`. I corrected the spec, and `suggest_outfit` checks `wardrobe.get("items")`, because `if not wardrobe` would treat `{"items": []}` as non-empty and skip the fallback.

**Moment 2: The `run_agent` loop**

- *What I asked for:* I asked Claude to fix the syntax errors in my `run_agent` loop, which I wrote from my branch rule.
- *What came back:* A version with no syntax errors that ran cleanly, with good documentation.
- *What I changed:* I used only the parts I needed: the parser, the loop, and the empty-search message.

# Capstone (Project 9)

## What This Extends

This extends FitFindr, my Project 2 thrifting agent (`run_agent()` in `agent.py`, three tools, search over MCP, two tools calling Gemini through `generate.py`). The new work is an operational layer around `serve.py`: a request log that writes one structured JSON line for every request to `logs/requests.jsonl`, a run path that works from a clean checkout of the Capstone branch (`RUNNING.md`), and latency and token cost measured from that log. The agent, the tools and the search ranking are unchanged.

## The Shape

Shape A, deploy and instrument. `serve.py` was written with no logging, timing or request counting, so the extension is exactly that missing layer. A small helper (`request_log.py`) and a few lines in `serve.py` record, for every request on every path: timestamp, request id, route, HTTP status, query, outcome, error text, duration, whether it queued behind the lock, prompt and output tokens, and the selected item id. Tokens are the difference in `generate.token_counts()` before and after `run_agent()`, taken inside the lock, so they are only valid with `AI201_CACHE=0`. A failure to write the log must never break the request.

Out of scope, decided before building:

- No changes to search ranking or `parse_query`. If the measurements later point there, the one improvement in Milestone 6 may touch it, and only then.
- No replacement of the per-call MCP process spawn.
- No new tools. The logging layer only reads `generate.py`. The one improvement later changed it, because the diagnosis pointed there (see The Improvement).
- No hosting (this is Path B, local with logs) and no UI.

## Running It

Path B, local with logs. The start command is `python serve.py`, with the environment steps in `RUNNING.md`. I tested those instructions from a fresh clone of the Capstone branch in a separate folder: it started, answered `/health` and one `/ask`, and wrote a log record on the first attempt with nothing missing. I then deleted that folder.

## Instrumentation

Every `/ask` request, on every path, appends one JSON line to `logs/requests.jsonl` (written by `request_log.py`, called from `serve.py`). `/health` is not logged. Fields:

- `timestamp`: UTC, when the record was written, so the end of the request
- `request_id`: random 12-character id
- `route`: `/ask`
- `http_status`: the status returned to the caller
- `query`: the query text as received (empty string for a missing one)
- `outcome`: `ok`, `nothing_found`, `model_unavailable`, `mcp_unavailable`, `bad_request` or `server_error`
- `error`: error text, or null
- `duration_s`: seconds from the start of the handler to just before the response is returned, including any wait for the lock
- `queued`: whether the request found the lock already held
- `prompt_tokens`, `output_tokens`: the difference in `generate.token_counts()` before and after `run_agent()`, taken inside the lock. Valid only with `AI201_CACHE=0`, which these runs used. Null when no run happened.
- `selected_item_id`: the listing id the agent picked, or null

A failure to write the log is printed to stderr and never changes the response.

These are 10 entries from a real session: five matching queries, twice, one at a time, cache off.

```
{"timestamp": "2026-11-09T23:01:23.761+00:00", "request_id": "9d84bf0f7cee", "route": "/ask", "http_status": 200, "query": "vintage graphic tee under $30", "outcome": "ok", "error": null, "duration_s": 4.302, "queued": false, "prompt_tokens": 445, "output_tokens": 139, "selected_item_id": "lst_002"}
{"timestamp": "2026-11-09T23:01:26.293+00:00", "request_id": "eb59833b7f5b", "route": "/ask", "http_status": 200, "query": "90s track jacket in size M", "outcome": "ok", "error": null, "duration_s": 2.488, "queued": false, "prompt_tokens": 487, "output_tokens": 175, "selected_item_id": "lst_004"}
{"timestamp": "2026-11-09T23:01:28.975+00:00", "request_id": "bfeb8c1f2cf2", "route": "/ask", "http_status": 200, "query": "silk slip dress in midi length under $40", "outcome": "ok", "error": null, "duration_s": 2.678, "queued": false, "prompt_tokens": 485, "output_tokens": 177, "selected_item_id": "lst_013"}
{"timestamp": "2026-11-09T23:01:31.500+00:00", "request_id": "ba4bbf2b0418", "route": "/ask", "http_status": 200, "query": "platform sneakers size 8", "outcome": "ok", "error": null, "duration_s": 2.52, "queued": false, "prompt_tokens": 442, "output_tokens": 134, "selected_item_id": "lst_019"}
{"timestamp": "2026-11-09T23:01:34.334+00:00", "request_id": "a43a960d7aee", "route": "/ask", "http_status": 200, "query": "denim jacket under $50", "outcome": "ok", "error": null, "duration_s": 2.83, "queued": false, "prompt_tokens": 479, "output_tokens": 180, "selected_item_id": "lst_007"}
{"timestamp": "2026-11-09T23:01:37.001+00:00", "request_id": "3fde5dc84bba", "route": "/ask", "http_status": 200, "query": "vintage graphic tee under $30", "outcome": "ok", "error": null, "duration_s": 2.662, "queued": false, "prompt_tokens": 439, "output_tokens": 142, "selected_item_id": "lst_002"}
{"timestamp": "2026-11-09T23:01:39.766+00:00", "request_id": "7fc7df4796cf", "route": "/ask", "http_status": 200, "query": "90s track jacket in size M", "outcome": "ok", "error": null, "duration_s": 2.76, "queued": false, "prompt_tokens": 464, "output_tokens": 163, "selected_item_id": "lst_004"}
{"timestamp": "2026-11-09T23:02:22.890+00:00", "request_id": "a4239a028e86", "route": "/ask", "http_status": 200, "query": "silk slip dress in midi length under $40", "outcome": "ok", "error": null, "duration_s": 43.12, "queued": false, "prompt_tokens": 473, "output_tokens": 150, "selected_item_id": "lst_013"}
{"timestamp": "2026-11-09T23:02:25.542+00:00", "request_id": "50428c0c4b8c", "route": "/ask", "http_status": 200, "query": "platform sneakers size 8", "outcome": "ok", "error": null, "duration_s": 2.649, "queued": false, "prompt_tokens": 455, "output_tokens": 161, "selected_item_id": "lst_019"}
{"timestamp": "2026-11-09T23:02:27.971+00:00", "request_id": "0714c34a3cb1", "route": "/ask", "http_status": 200, "query": "denim jacket under $50", "outcome": "ok", "error": null, "duration_s": 2.425, "queued": false, "prompt_tokens": 440, "output_tokens": 136, "selected_item_id": "lst_007"}
```

One run stands out: the 8th took 43.12 s against 2.4 to 4.3 s for the others. It was the 16th model call inside the first minute, which fits the 15-requests-a-minute pacing in `generate.py`. The log has no field for pacing waits, so this is a hypothesis, not yet a diagnosis.

## What It Costs

Measured over those 10 runs (all `ok`, cache off): a mean of 460.9 prompt tokens and 155.7 output tokens per run, 616.6 in total. I took the token counts from the `prompt_tokens` and `output_tokens` fields in the log, which come from the usage the service reports, and averaged them. Time per run: mean 6.84 s, median 2.67 s. The mean is inflated by the one 43.12 s paced run; without it the mean is 2.81 s.

For a hundred runs a day: 100 x 616.6 = 61,660 tokens (46,090 prompt, 15,570 output), and about 100 x 2.67 s = 267 s of serving time.

In dollars, at the published rate for gemini-3.5-flash-lite ($0.30 per 1M input tokens, $2.50 per 1M output tokens): 460.9 x 0.30 / 1,000,000 + 155.7 x 2.50 / 1,000,000 = $0.000138 + $0.000389 = about $0.00053 per run. A hundred a day is about $0.053 a day, or about $1.58 over 30 days. The token counts are measured; the rate is the list price, so the dollar figure is that price times my measurement. On the free tier I am on, my actual spend is $0. The counter reads `candidates_token_count`, so any thinking tokens the service bills separately may not be included.

Cross-check on a larger sample. The six latency logs (`results/capstone/*/log_T_t*.jsonl`) hold 329 requests with the cache off, of which 266 were `ok`. I averaged the token fields over those (a one-line script over the logs): 462.6 prompt tokens and 162.2 output tokens, 624.8 in total, which is close to the first 10 runs (616.6), so the token cost per run is stable. The time is not: the median successful request took 5.92 s, not the 2.67 s from my first 10 runs, so the 267 s a day above is too low. At 5.92 s, a hundred runs a day is 100 x 5.92 = 592 s, about 10 minutes of serving time.

Redone in dollars at the same list rate: 462.6 x 0.30 / 1,000,000 + 162.2 x 2.50 / 1,000,000 = $0.000139 + $0.000406 = about $0.00054 per run, so about $0.054 a day and about $1.63 over 30 days. On the free tier I am on, my actual spend is $0.

Failures cost very little: the 63 failed requests (all in the runs with the 20 s timeout) used a mean of 90.7 prompt tokens each, about $0.00003 each, because a request that fails on its first model call spends nothing. The cost of the failures is to the user, not to my bill.

## Run Log and Verdicts

Before the improvement (no model-call timeout). Three trials each, nothing changed between them. Raw files are in `results/capstone/before/`.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Every /ask request leaves one complete record | 10/10 | 10/10 | 0/10 (first request hung, trial aborted) | 10/10 | MISSED |
| 2. Each failure type logged with the right outcome and status | 10/10 for each of 5 types | 50/50 | 50/50 | 50/50 | MET |
| 3. A failed log write does not change the response | 10/10 | 10/10 | 10/10 | 2 completed, hung at request 3 (driver recorded 0/10) | MISSED |
| 4. Warm requests at or under 4.7 s | 95/100 | 16/100 (hung at #28, 16 of 27 completed on time) | 22/100 (hung at #46, 22 of 45) | 9/100 (hung at #27, 9 of 26) | MISSED |
| 5. No-match query stops before suggest_outfit | 10/10 | 10/10 | 10/10 | 10/10 | MET |

Notes on the table:
- Criterion 1, run 1 is the second attempt at that session. The first attempt hung on its second request, and I discarded it. It is an extra example of the same failure.
- In trial 2, criteria 2b, 5 and 2d were run again on a fresh server, because the hang in criterion 1 had locked the first one. None of those three paths calls the model.
- Criterion 1, run 2 has no result file, because the driver crashed on the hang before I added hang handling. The evidence is `driver_t2.txt` and `server_N_t2.out.txt`. The scores for criterion 3, runs 1 and 2 are in `c3_t1.json` and `c3_t2.json`.

Real output. The log records are written by `request_log.write()`, called from `serve.ask()`. The scores and driver lines come from `capstone_run.py` (`run_c1` to `run_c5`).

**Criterion 1**, `log_N_t1.jsonl`:
```
{"timestamp": "2026-11-12T01:34:04.806+00:00", "request_id": "e4ef98a7f9a2", "route": "/ask", "http_status": 200, "query": "vintage graphic tee under $30", "outcome": "ok", "error": null, "duration_s": 5.082, "queued": false, "prompt_tokens": 459, "output_tokens": 149, "selected_item_id": "lst_002"}
```
Run 2, the hang. The driver printed `TimeoutError: timed out` (`driver_t2.txt`), and `server_N_t2.out.txt` ends here, with no `[6] create_fit_card`:
```
[5] suggest_outfit
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      out: Outfit 1: Casual Streetwear Pair the Y2K Baby Tee with the baggy straight-leg jeans (dark wash, indigo), layer…
      →    10 wardrobe item(s)
```

**Criterion 2**, one record per outcome, from `log_N_t1.jsonl` and `log_B_t1.jsonl`:
```
{"timestamp": "2026-11-12T01:34:23.179+00:00", "request_id": "10af5ea663c2", "route": "/ask", "http_status": 400, "query": "", "outcome": "bad_request", "error": "missing or empty 'query' field", "duration_s": 0.0, "queued": false, "prompt_tokens": null, "output_tokens": null, "selected_item_id": null}
{"timestamp": "2026-11-12T01:34:17.704+00:00", "request_id": "bf8b1ae08c45", "route": "/ask", "http_status": 200, "query": "designer ballgown under $5", "outcome": "nothing_found", "error": "Nothing in the listings matched description 'designer ballgown', under $5.\nThings to change: try broader words — 'jacket' finds more than 'cropped corduroy jacket'; raise the price ceiling above $5.", "duration_s": 1.976, "queued": false, "prompt_tokens": 0, "output_tokens": 0, "selected_item_id": null}
{"timestamp": "2026-11-12T01:34:44.734+00:00", "request_id": "f84ee5eb3654", "route": "/ask", "http_status": 500, "query": null, "outcome": "server_error", "error": "AttributeError: 'list' object has no attribute 'get'", "duration_s": 0.0, "queued": false, "prompt_tokens": null, "output_tokens": null, "selected_item_id": null}
{"timestamp": "2026-11-12T01:38:51.106+00:00", "request_id": "6e5694bdc08c", "route": "/ask", "http_status": 200, "query": "vintage graphic tee under $30", "outcome": "mcp_unavailable", "error": "The search tool couldn't be reached over MCP, so nothing was searched. Run `python mcp_client.py` to check the server starts, then try again.\nWhat went wrong: Couldn't call 'search_listings' over MCP: unhandled errors in a TaskGroup (1 sub-exception)\nCheck that mcp_server.py runs on its own first:\n    python mcp_server.py\nIf it exits immediately with an error, fix that before coming back here.", "duration_s": 3.72, "queued": false, "prompt_tokens": 0, "output_tokens": 0, "selected_item_id": null}
{"timestamp": "2026-11-12T01:40:21.131+00:00", "request_id": "72428ebe491f", "route": "/ask", "http_status": 200, "query": "vintage graphic tee under $30", "outcome": "model_unavailable", "error": "The model couldn't be reached, so the outfit and caption steps didn't run. The search worked: 10 listing(s) were found. Check GEMINI_API_KEY in your .env, then run the same query again.\nWhat the service said: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.", "duration_s": 4.271, "queued": false, "prompt_tokens": 0, "output_tokens": 0, "selected_item_id": "lst_002"}
```

**Criterion 3**, `driver_t3.txt` and `stderr_L_t1.txt`:
```
criterion 3 trial 3: 0/10  target met this trial: no
ABORTED: the server hung (no reply after 120 s); the trial stopped here
  [request_log] could not write the log: [Errno 13] Permission denied: 'results\\capstone\\before'
  [request_log] could not write the log: [Errno 13] Permission denied: 'results\\capstone\\before'
```

**Criterion 4**, driver output for the three trials:
```
criterion 4 trial 1: 16/100  target met this trial: no
log lines 28 (expected 101); outcome not ok: 0; request 28 hung (no reply after 120 s); trial stopped, remaining requests count as not on time; duration_s min 3.563, median 4.096, max 8.243
criterion 4 trial 2: 22/100  target met this trial: no
log lines 46 (expected 101); outcome not ok: 0; request 46 hung (no reply after 120 s); trial stopped, remaining requests count as not on time; duration_s min 3.457, median 4.716, max 13.344
criterion 4 trial 3: 9/100  target met this trial: no
log lines 27 (expected 101); outcome not ok: 0; request 27 hung (no reply after 120 s); trial stopped, remaining requests count as not on time; duration_s min 3.589, median 5.17, max 8.765
```

**Criterion 5**, `log_R_t2.jsonl` (tokens 0 means no model call):
```
{"timestamp": "2026-11-12T02:08:57.316+00:00", "request_id": "2e6761a1f50c", "route": "/ask", "http_status": 200, "query": "leather jacket under $5", "outcome": "nothing_found", "error": "Nothing in the listings matched description 'leather jacket', under $5.\nThings to change: try broader words — 'jacket' finds more than 'cropped corduroy jacket'; raise the price ceiling above $5.", "duration_s": 0.993, "queued": false, "prompt_tokens": 0, "output_tokens": 0, "selected_item_id": null}
```

### Diagnoses

Criteria 1, 3 and 4 share one cause, so this is one problem with three symptoms. The stage is the model call in `generate.generate()`, which `suggest_outfit` and `create_fit_card` use. The mechanism is that `generate_content` was called with no timeout. When a call stalled, it never returned. `serve.py` handles one request at a time behind a lock, so that one request held the lock forever and everything behind it waited. A stuck request also left no log record, because `request_log.write()` runs when a request ends. That is a limit of my own instrumentation: it cannot see a request that never finishes. The evidence is the server output stopping after a model step (above), the driver's 120 s timeouts, and no log line for the stuck request. No stall coincided with a `[rate limit]` wait in stderr, so none of them was a backoff sleep. There were six hangs in total, all in sessions that call the model.

Criterion 4 has a second, separate miss: slowness. Of the 98 requests that completed, 47 were at or under 4.7 s, with medians of 4.10, 4.72 and 5.17 s per trial, against 2.4 to 2.8 s in my Milestone 3 log. It is not output length: the correlation between `duration_s` and `output_tokens` is between -0.02 and 0.25 (`analyze_logs.py`). It is not the search stage either: requests that stop after the search have a median of 1.10 s. So the time is in the model calls, whose latency varied between sessions. That is outside my code. The per-call MCP spawn is a fixed cost of about 1 s per run, a fifth of the 4.7 s budget, but it did not vary.

Criterion 2 passed in every trial. One finding along the way: a request body that is valid JSON but not an object, such as `[1]`, returns a 500 and is logged as `server_error`. That matches my criterion, but a 400 would be the better answer.

## The Improvement

**Change:** a 20 s timeout on every model call (`config.MODEL_TIMEOUT_S`, applied in `generate.py`). Diagnosis: the model call had no upper bound, so one stalled call held the server's lock forever (criteria 1, 3 and 4).

**Predictions, written before the re-run:**
- Criterion 1: a stalled request now ends within about 20 s with outcome model_unavailable and leaves a record, so I expect 10/10.
- Criterion 3: a stalled request now returns an error and no fit_card, so a trial that hits a stall will still miss. The timeout stops the hang, it doesn't stop the stall.
- Criterion 4: all 100 requests now finish, so I get a real distribution. I expect it to still miss: the timeout does nothing about requests that are slow without stalling, and a stalled one costs about 20 s.
- Criteria 2 and 5: no change, 10/10. These are my regression check.

Re-run in the same format, written to `results/capstone/after/`:

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict (before to after) |
|---|---|---|---|---|---|
| 1 | 10/10 | 10/10 | 10/10 | 10/10 | MISSED to MET |
| 2 | 10/10 per type | 50/50 | 50/50 | 50/50 | MET to MET |
| 3 | 10/10 | 7/10 | 8/10 | 8/10 | MISSED to MISSED |
| 4 | 95/100 | 3/100 (all 100 ran) | 4/100 (all 100 ran) | 13/100 (hung at #26, 13 of 25) | MISSED to MISSED |
| 5 | 10/10 | 10/10 | 10/10 | 10/10 | MET to MET |

Real output from `results/capstone/after/`. First, a stalled call now ends in a record (`log_N_t*.jsonl`). The 254 prompt tokens show the first model call finished and the second timed out:
```
{"timestamp": "2026-11-12T19:47:15.166+00:00", "request_id": "880ebe14d30e", "route": "/ask", "http_status": 200, "query": "silk slip dress in midi length under $40", "outcome": "model_unavailable", "error": "The model couldn't be reached, so the outfit and caption steps didn't run. The search worked: 5 listing(s) were found. Check GEMINI_API_KEY in your .env, then run the same query again.\nWhat the service said: Couldn't reach the model: The read operation timed out", "duration_s": 23.986, "queued": false, "prompt_tokens": 254, "output_tokens": 102, "selected_item_id": "lst_013"}
```
Criterion 3 (`driver_t1.txt` to `driver_t3.txt`):
```
criterion 3 trial 1: 7/10  target met this trial: no
stderr lines saying the log could not be written: 10 (must be 10)
criterion 3 trial 2: 8/10  target met this trial: no
stderr lines saying the log could not be written: 10 (must be 10)
criterion 3 trial 3: 8/10  target met this trial: no
stderr lines saying the log could not be written: 10 (must be 10)
```
Criterion 4 (driver output, and a timeout record from `log_T_t*.jsonl`):
```
criterion 4 trial 1: 3/100  target met this trial: no
log lines 101 (expected 101); outcome not ok: 38; duration_s min 4.088, median 12.41, max 30.248
criterion 4 trial 2: 4/100  target met this trial: no
log lines 101 (expected 101); outcome not ok: 23; duration_s min 3.641, median 7.819, max 29.628
criterion 4 trial 3: 13/100  target met this trial: no
log lines 26 (expected 101); outcome not ok: 2; request 26 hung (no reply after 120 s); trial stopped, remaining requests count as not on time; duration_s min 3.302, median 4.668, max 22.15
{"timestamp": "2026-11-12T19:52:44.220+00:00", "request_id": "a1d490d01751", "route": "/ask", "http_status": 200, "query": "90s track jacket in size M", "outcome": "model_unavailable", "error": "The model couldn't be reached, so the outfit and caption steps didn't run. The search worked: 4 listing(s) were found. Check GEMINI_API_KEY in your .env, then run the same query again.\nWhat the service said: Couldn't reach the model: The read operation timed out", "duration_s": 22.914, "queued": false, "prompt_tokens": 0, "output_tokens": 0, "selected_item_id": "lst_004"}
```
Trial 3's hang, the end of `server_T_t3.out.txt`:
```
[160] suggest_outfit
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      out: Outfit 1: Pair the Y2K Baby Tee with your baggy straight-leg jeans, dark wash, layered under the vintage black…
      →    10 wardrobe item(s)
```

**Did it help?** Partly. It fixed what it was aimed at: criterion 1 went from a miss to 10/10 in all three trials, because a stalled call now ends in a logged `model_unavailable` record instead of freezing the server. Criterion 4 also completed all 100 requests in two of three trials, where every trial had aborted before. It did not make the system pleasant to use. Of the 225 warm requests across the three "after" criterion 4 trials, 63 failed: 54 were the 20 s timeout firing, 8 were the service answering "high demand, UNAVAILABLE", and 1 was a connection error (`analyze_logs.py` and the `error` fields in the logs). Criterion 3 missed in every trial for the same reason: 7 of the 30 requests came back as model-unavailable errors with no fit card. The property that criterion is about still held, since all 10 log-write failures were absorbed in every trial. Timeouts are also a trade-off. Requests that succeeded took up to 19.8 s in one trial, so in a slow period a 20 s limit may cut off calls that would have finished.

Two caveats on the comparison. The before and after runs were hours apart, and the failure rate swung from 36 timeouts in 100 requests (trial 1) to 16 (trial 2) with identical code, so the service itself was varying and this is not a clean A/B test. And criterion 4, trial 3 still hung at request 26 even with the timeout: the server output stops after `[160] suggest_outfit`. My hypothesis is that the stall was somewhere an HTTP read timeout does not cover, but I did not verify that.

**Against my predictions:** criterion 1 at 10/10 was right. Criterion 3 still missing was right, but I called stalls rare and they were not. Criteria 2 and 5 unchanged was right. Criterion 4 still missing was right, but "all 100 requests finish" was wrong for trial 3.

## What's Still Broken

Two criteria are still missed after the improvement. I made the one improvement the unit asks for, and my data says the next fix is a different change.

**Criterion 3 (a failed log write does not change the response): 7, 8 and 8 of 10.** The property the criterion is about held, since all 10 log-write failures were absorbed in every trial. The misses are model calls that timed out or got a "high demand" error from the service, which `generate.py` does not retry. I would retry a timed-out or UNAVAILABLE call once, and fix the error text, which still tells the user to check GEMINI_API_KEY when the cause is a timeout. I stopped because the failure rate swung a lot between sessions (36, 16 and 2 timeouts in the three criterion 4 trials), and I want to measure a retry in a calmer period before claiming it helps.

**Criterion 4 (95 of 100 warm requests at or under 4.7 s): 3, 4 and 13 of 100.** There are two causes. First, the 20 s timeout does not bound everything: one trial still hung at request 26, so I would wrap each model call in a hard wall-clock deadline and not rely on the client's read timeout. Second, the model calls are slow even when they succeed, with medians of 4.1 to 7.9 s against 2.4 to 2.8 s when I set the target. My log has one duration per request, so I cannot say which stage is slow, and I would add per-stage timings. I left the target as it is: it was measurable and I missed it, which the assignment says is not a reason to revise it.

Smaller things I know about:
- The log cannot see a request that never finishes, because the record is written at the end. A "request started" line would show it.
- A request body that is valid JSON but not an object, such as `[1]`, returns 500 where 400 would be the right answer.
- When the driver aborts on a hang it saves 0/10, even if some requests completed (criterion 3, run 3 completed 2).
- `queued` copies the lock state at the start, so it can miss two requests arriving together.

**If I had another unit:** I would put a hard deadline and one retry around every model call and re-run criteria 1, 3 and 4. That one change addresses the cause behind three of my five criteria, which no other change does.

## How I Used AI

**1. Drafting the criteria.** I asked Claude to write the five criteria with the targets left as placeholders, and to explain how to choose each number. It gave me full draft statements (a record for every request, each failure type, a failed log write, warm latency, and the no-match regression check) and a rule for each number, such as setting the request spacing above the 8 s that the 15-a-minute limit allows. I then chose the numbers myself: 10 of 10 for the checks that do not depend on the model, and 95 of 100 at 4.7 s with 10 s spacing for latency, based on my Milestone 3 warm runs of 2.4 to 2.8 s. 

**2. Diagnosing the hangs.** Several of my trials froze and my driver gave up after 120 s. I pasted the server output and the logs, and Claude pointed out that every stuck request stopped inside a model step and that `generate.py` called the model with no timeout. I did not take that on trust: I searched the stderr files for a rate-limit wait (none appeared in the hung sessions), and I tested the timeout with a 0.05 s value before the real re-run. Claude suggested the predictions I committed before the re-run, and its expectation that stalls would be rare was wrong: 7 of 30 criterion 3 requests failed after the change. The comparison in The Improvement says where the predictions were wrong.