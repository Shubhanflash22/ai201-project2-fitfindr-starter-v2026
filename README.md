# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->
FitFindr is a thrifting agent. A user describes what they want in plain language, like "a vintage graphic tee under $30, size M," and the agent searches a file of secondhand listings for matches. It then takes the top match, works out outfit ideas to go with it from the user's wardrobe (or gives general styling advice if the wardrobe is empty), and writes a short caption the user could post. If nothing matches, the agent stops and tells the user what to change, such as the size or the price ceiling, instead of continuing with nothing.

**Stretch feature:** a fourth tool, `compare_prices`, that compares the selected item's price with the average of other listings in the same category.

---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

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
- **When it has nothing:** If `wardrobe["items"]` is empty (`{"items": []}`), it returns a string of general styling advice for the new item instead of failing. `notes` being `None` is left out of the prompt. If the model call fails, `generate()` raises `ModelUnavailable`, which the loop catches, and the loop shows the user a message saying the model couldn't be reached.

### `create_fit_card`

- **What it does:** Asks the model for a short, postable social-media caption for the find.
- **Inputs:** `outfit` (str, the output of `suggest_outfit`), `new_item` (dict, the selected listing).
- **Returns:** A non-empty string of two or three sentences in a casual voice that mentions the item, its price, and its platform.
- **When it has nothing:** If `brand` is `None`, the prompt leaves the brand out and the card is still written. If `outfit` is empty or whitespace, it writes a caption from `new_item` alone. If the model call fails, `generate()` raises `ModelUnavailable`, which the loop catches, same as `suggest_outfit`.

### `compare_prices` (stretch)

- **What it does:** Compares the selected item's price with the average price of the other listings in the same category.
- **Inputs:** `item` (dict, the selected listing).
- **Returns:** A dict with `category` (str), `average` (float or None), `count` (int), `difference` (float or None, item price minus average), and `verdict` (str, one of cheaper than, pricier than, or about the category average).
- **When it has nothing:** If no other listing shares the category, `average` and `difference` are `None`, `count` is `0`, and `verdict` says there is nothing to compare against.

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, put a message in `session["message"]` that names what to change (loosen the size, raise the price ceiling, or try different keywords), leave `session["fit_card"]` as `None`, and stop without calling `suggest_outfit`. Otherwise, store the first result in `session["selected_item"]` and continue to `suggest_outfit`, then `create_fit_card`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** <!-- regex, string splitting, or asking the model — say which -->

**What moves through the session:** which fields, in what order

**Branch rule:** If `search_listings` returns an empty list, put a message in `session["error"]` that names what to change (broader keywords, drop or change the size, raise the price ceiling), leave `session["fit_card"]` as `None`, and return the session without calling `suggest_outfit`. Otherwise, store the first result in `session["selected_item"]` and continue to `suggest_outfit`, then `create_fit_card`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** Regex, with no model call (`agent.py::parse_query`). A price such as "under $30" becomes `max_price` (float), a size such as "size M" or a trailing ", M" becomes `size` (str), and the leftover words become `description`. Phrasing it hasn't seen, like "under thirty dollars" or "size 8", parses to no price or size, so that filter is silently skipped.

**What moves through the session:** In order: `session["parsed"]` (description, size, max_price), then `session["search_results"]` (the list from `search_listings`). If that list is empty, `session["error"]` is set and the run stops. Otherwise `session["selected_item"]` (the first result) is set, `compare_prices` fills `session["price_check"]`, and `selected_item` is read back out for `suggest_outfit`, which sets `session["outfit_suggestion"]`. That is read back out for `create_fit_card`, which sets `session["fit_card"]`.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask '...'

```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"

```

```
$ python -c "from tools import suggest_outfit; ..."

```

```
$ python -c "from tools import create_fit_card; ..."

```

(base) PS C:\Users\shubh\Desktop\Hard disk\College(PG)\Academics at UCSD\Y2Q1\Codepath\AI201 Applications of AI Engineering\Projects\ai201-project2-fitfindr-starter-v2026> (Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ; (& "c:\Users\shubh\Desktop\Hard disk\College(PG)\Academics at UCSD\Y2Q1\Codepath\AI201 Applications of AI Engineering\Projects\ai201-project2-fitfindr-starter-v2026\.venv\Scripts\Activate.ps1")
(.venv) (base) PS C:\Users\shubh\Desktop\Hard disk\College(PG)\Academics at UCSD\Y2Q1\Codepath\AI201 Applications of AI Engineering\Projects\ai201-project2-fitfindr-starter-v2026> # One full query                                                                                    
>> python app.py ask 'vintage graphic tee under $30, size M'                                                                                
>> python app.py ask 'designer ballgown size XXS under $5'
>> 
>> # Tool 1
>> python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
>> 
>> # Tool 2
>> python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
>> 
>> # Tool 3 (cache off so it can vary)
>> $env:AI201_CACHE="0"
>> python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
>> Remove-Item Env:AI201_CACHE
>> 
>> # Tool 4 (stretch)
>> python -c "from tools import compare_prices; from utils.data_loader import load_listings; print(compare_prices(load_listings()[1]))"

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Outfit 1 (Streetwear Edge):
Pair the Y2K Baby Tee with your baggy straight-leg jeans (dark wash, indigo) and your vintage black denim jacket. Complete the look with your chunky white sneakers and black crossbody bag.

Outfit 2 (Casual Contrast):
Layer the Y2K Baby Tee under your oversized grey crewneck sweatshirt, matched with your wide-leg khaki trousers. Finish with your black combat boots and brown leather belt.

  Fit card: Just scored this little butterfly baby tee on depop for eighteen dollars and the nostalgic early two thousands mall punk energyis immaculate. I am definitely styling it with my baggy dark wash jeans and chunky sneakers for that effortless streetwear look.

0 model calls this session, 2 served from cache

  Nothing in the listings matched description 'designer ballgown', size XXS, under $5.
Things to change: try broader words — 'jacket' finds more than 'cropped corduroy jacket'; drop the size, or try a neighbouring one; raise the price ceiling above $5.

0 model calls this session
[{'id': 'lst_017', 'title': 'Mesh Long-Sleeve Top — Black', 'description': 'Sheer black mesh long-sleeve. Great for layering under a graphic tee or over a bralette. Stretchy material, fits true to size.', 'category': 'tops', 'style_tags': ['y2k', 'grunge', 'goth', 'layering'], 'size': 'S/M', 'condition': 'excellent', 'price': 15.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_033', 'title': 'Vintage Band Tee — Faded Grey', 'description': 'Faded grey band-style tee with distressed graphic. Crew neck. Fits boxy. Well-loved but no holes or major damage.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'band tee', 'graphic tee', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 19.0, 'colors': ['grey', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_012', 'title': 'Oversized Crewneck Sweatshirt — Vintage Navy', 'description': 'Perfectly faded navy crewneck. Genuinely vintage — not manufactured distressed. Ribbed cuffs and hem. No graphics, clean.', 'category': 'tops', 'style_tags': ['vintage', 'basics', 'oversized', 'classic'], 'size': 'XL (fits oversized)', 'condition': 'good', 'price': 20.0,'colors': ['navy'], 'brand': None, 'platform': 'thredUp'}, {'id': 'lst_015', 'title': 'Vintage Graphic Hoodie — Faded Black', 'description': 'Faded black pullover hoodie with barely-visible vintage graphic on the chest. Cozy interior. Some pilling but adds to the worn-in look.','category': 'tops', 'style_tags': ['vintage', 'grunge', 'graphic', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 26.0, 'colors': ['black', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_011', 'title': 'Low-Rise Cargo Pants — Khaki', 'description': 'Y2Kera low-rise cargo pants. Lots of pockets. Khaki color, slightly distressed at the hems. Great for layering with a long tee.', 'category': 'bottoms', 'style_tags': ['y2k', 'cargo', '2000s', 'streetwear'], 'size': 'W29', 'condition': 'fair', 'price': 27.0, 'colors': ['khaki', 'tan'], 'brand': None, 'platform': 'poshmark'}]
Outfit 1: Casual Streetwear
Pair the Vintage Levi's 501 Jeans with the White ribbed tank top, the Black cropped zip hoodie worn open, and the Chunky white sneakers. Add the Black crossbody bag to finish the look.

Outfit 2: Relaxed Vintage
Style the Vintage Levi's 501 Jeans with the Oversized grey crewneck sweatshirt, cinched at the waist with the Brown leather belt, and the Black combat boots. Throw on the Vintage black denim jacket over top.
Just scored these vintage medium wash Levi's 501 jeans on depop for thirty eight dollars and they have the absolute best lived-in 90s grunge vibe. I am definitely styling them with my beat-up white sneakers for the easiest everyday uniform. Finding denim that actually fits this well on the first try feels like winning the lottery.
{'category': 'tops', 'average': 22.0, 'count': 14, 'difference': -4.0, 'verdict': 'cheaper than the tops average'}
(.venv) (base) PS C:\Users\shubh\Desktop\Hard disk\College(PG)\Academics at UCSD\Y2Q1\Codepath\AI201 Applications of AI Engineering\Projects\ai201-project2-fitfindr-starter-v2026> 


>> python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
>> 
>> # 2. search_listings: empty case (expect exactly [])
>> python -c "from tools import search_listings; print(search_listings('designer ballgown', size='XXS', max_price=5))"
>> 
>> # 3. search_listings: size matching (expect S/M and M only, no XL or L)
>> python -c "from tools import search_listings; print([(i['id'], i['size']) for i in search_listings('tee', size='M')])"
>> 
>> # 4. suggest_outfit: example wardrobe (should name specific wardrobe pieces)
>> python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
>> 
>> # 5. suggest_outfit: empty wardrobe (should give general advice, no crash)
>> python -c "from tools import suggest_outfit; from utils.data_loader import get_empty_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_empty_wardrobe()))"
>> 
>> # 6. create_fit_card: cache off so the runs can differ. Runs 1-2 are the same item; run 3 has brand=None.
>> $env:AI201_CACHE="0"
>> python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
>> python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
>> python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[1]))"
>> Remove-Item Env:AI201_CACHE
[{'id': 'lst_017', 'title': 'Mesh Long-Sleeve Top — Black', 'description': 'Sheer black mesh long-sleeve. Great for layering under a graphic tee or over a bralette. Stretchy material, fits true to size.', 'category': 'tops', 'style_tags': ['y2k', 'grunge', 'goth', 'layering'], 'size': 'S/M', 'condition': 'excellent', 'price': 15.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_033', 'title': 'Vintage Band Tee — Faded Grey', 'description': 'Faded grey band-styletee with distressed graphic. Crew neck. Fits boxy. Well-loved but no holes or major damage.', 'category': 'tops', 'style_tags': ['vintage', 'grunge','band tee', 'graphic tee', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 19.0, 'colors': ['grey', 'charcoal'], 'brand': None, 'platform':'depop'}, {'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_012', 'title': 'Oversized Crewneck Sweatshirt — Vintage Navy', 'description': 'Perfectly faded navy crewneck. Genuinely vintage — not manufactured distressed. Ribbed cuffs and hem. No graphics, clean.', 'category': 'tops', 'style_tags': ['vintage', 'basics', 'oversized', 'classic'], 'size': 'XL (fits oversized)', 'condition': 'good', 'price': 20.0, 'colors': ['navy'], 'brand': None, 'platform': 'thredUp'}, {'id': 'lst_015', 'title': 'Vintage Graphic Hoodie — Faded Black', 'description': 'Faded black pullover hoodie with barely-visible vintage graphic on the chest. Cozy interior. Some pilling but adds to the worn-in look.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'graphic', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 26.0, 'colors': ['black', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_011', 'title': 'Low-Rise Cargo Pants — Khaki', 'description': 'Y2K era low-rise cargo pants. Lots of pockets. Khaki color, slightly distressed at the hems. Great for layering with a long tee.', 'category': 'bottoms', 'style_tags': ['y2k', 'cargo', '2000s', 'streetwear'], 'size': 'W29', 'condition': 'fair', 'price': 27.0, 'colors': ['khaki', 'tan'], 'brand': None, 'platform': 'poshmark'}]
[]
[('lst_017', 'S/M'), ('lst_002', 'S/M')]
Outfit 1: Casual Streetwear
Pair the Vintage Levi's 501 Jeans with the White ribbed tank top, the Black cropped zip hoodie worn open, and the Chunky white sneakers. Add the Black crossbody bag to finish the look.

Outfit 2: Relaxed Vintage
Style the Vintage Levi's 501 Jeans with the Oversized grey crewneck sweatshirt, cinched at the waist with the Brown leather belt, and the Black combat boots. Throw on the Vintage black denim jacket over top.
Casual Streetwear Look

Pair the vintage Levi's with a classic white boxy crewneck t-shirt tucked in casually. Layer an oversized black vintage leather bomber jacket or a denim jacket over top for a textured double-denim moment. Finish the outfit with well-worn white canvas low-top sneakers like Converse or Vans, a black canvas belt, and a minimalist silver pendant necklace for an effortless, everyday vibe.

Elevated Casual Look

Tuck a fitted black ribbed turtleneck bodysuit into the high-waisted medium wash denim to define your shape. Throw on an oversized houndstooth or camel wool trench coat for a sharp, contrasting silhouette. Complete the look with pointed-toe black leather boots, a structured black leather shoulder bag, and simple gold hoop earrings to easily transition the classic jeans from day to night.
Finally scored these vintage Levi's 501 jeans in a dreamy medium wash on depop for just 38 dollars. They give off such an effortless 90s off-duty model vibe. I am definitely living in these with my favorite white sneakers from now on.
Just scored these vintage medium wash Levi's 501 jeans on depop for $38 and I am never taking them off. They have that perfectly broken-in 90s slouchthat is impossible to fake. Throwing them on with some crisp white sneakers and I am officially set for the weekend.
Scored this cute little Y2K butterfly baby tee on depop for just eighteen dollars and I am obsessed. It has that ultimate early 2000s mallrat vibe that I can not get enough of. I am definitely throwing it on with my favorite jeans and white sneakers for my coffee run tomorrow.
(.venv) (base) PS C:\Users\shubh\Desktop\Hard disk\College(PG)\Academics at UCSD\Y2Q1\Codepath\AI201 Applications of AI Engineering\Projects\ai201-project2-fitfindr-starter-v2026> 

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:*
- *What came back:*
- *What I changed:*

**Moment 2**

- *What I asked for:*
- *What came back:*
- *What I changed:*

**Moment 1**

- *What I asked for:* I asked Claude to draft the text for my Tool Inventory spec for my three tools, and help me decide a few things including the inputs and what each returns when it has nothing.
- *What came back:* It specified `wardrobe` as a plain list of dicts, so the empty case was `[]`.
- *What I changed:* `data/wardrobe_schema.json` shows the wardrobe is a dict with an `items` key, so the empty case is `{"items": []}`. I corrected the spec, and `suggest_outfit` checks `wardrobe.get("items")`, because `if not wardrobe` would treat `{"items": []}` as non-empty and skip the fallback.

**Moment 2**

- *What I asked for:* I asked Claude to edit the `run_agent` loop from my branch rule when it gave syntax errors.
- *What came back:* A version with no syntax errors and clean run along with good documentation.
- *What I changed:* I used only the parts I needed: the parser, the loop, and the empty-search message.


<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
<!-- | 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  | -->
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Item in session matches item passed on | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card is 1 to 3 sentences and includes the price | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Price ceiling respected | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```
Criterion 1: matching query completes (try 1)
Produced by: agent.py::run_agent, using tools.py::search_listings (via mcp_server.py), suggest_outfit and create_fit_card
$ python run_eval.py --label before
[2] search_listings (via MCP)
      →    10 match(es)
[3] select_item
      out: Y2K Baby Tee — Butterfly Print ($18.0, depop)
[5] suggest_outfit
      →    10 wardrobe item(s)
[6] create_fit_card
      out: Found this butterfly print Y2K baby tee on depop for eighteen dollars and the total bratz doll energy is unrea…
  try 1: completed — fit card 227 chars

Criterion 2: impossible query stops early (try 1)
Produced by: agent.py::run_agent (the branch) and agent.py::_nothing_found_message
[2] search_listings (via MCP)
      out: [] (empty)
      →    0 match(es)
[3] branch
      →    search returned []: stopping before suggest_outfit
  try 1: stopped early — Nothing in the listings matched description 'designer ballgo

Criterion 3: selected item matches item passed on (try 1)
Produced by: agent.py::run_agent
[3] select_item
      out: Denim Jacket — Light Wash, Cropped ($42.0, poshmark)
[5] suggest_outfit
      in:  Denim Jacket — Light Wash, Cropped ($42.0, poshmark)

Criterion 4: fit card length and price (try 1)
Produced by: tools.py::create_fit_card, read with check_cards.py
TRY 1 | sentence marks: 3 | $ sign: False | price in words: True
Scored this little butterfly print Y2K baby tee on depop for just 18 dollars and I am obsessed. The nostalgic street style vibe is immaculate with baggy jeans and a cropped hoodie. It also looks so cute with wide-leg trousers and combat boots for that sweet-yet-edgy contrast.

Criterion 5: price ceiling respected (try 1)
Produced by: tools.py::search_listings, checked with check_price.py
TRY 1 | results: 3 | prices: [24.0, 27.0, 30.0] | over $30: []

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->
<!-- 
| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  | -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | A matching query completes all three tools | 4 of 5 | MET (5/5) | All five tries of 'vintage graphic tee under $30' ran search, outfit and fit card and returned a fit card. |
| 2 | An impossible query stops before the second tool | 5 of 5 | MET (5/5) | All five tries of the ballgown query ended at the branch, never reached suggest_outfit, and returned a message naming what to change. |
| 3 | Item in session matches item passed on | 5 of 5 | MET (5/5) | In all five tries the item at select_item and the item shown going into suggest_outfit were the same listing. The trace shows title, price and platform, not the literal id. |
| 4 | Fit card is 1 to 3 sentences and includes the price | 4 of 5 | MET (5/5) | I counted sentence marks (2 or 3 in every card) and checked each card for the price. Every card had it, written in words. |
| 5 | Price ceiling respected | 5 of 5 | MET (5/5) | In all five tries of 'denim jacket under $30', every returned price was 30 or less (24, 27, 30). |

**Diagnoses**
No criterion was missed, so there is no miss to diagnose. Reading the runs plainly, I think my targets were low in places, and the evidence shows two weaknesses my criteria did not catch:

- **Criterion 4 is the one I'd tighten.** It says the card "includes the price", and every card did, but always in words ("eighteen dollars", "18 dollars") and never as "$18". A check for a dollar sign would have failed 5 of 5. The criterion was too loose, and the model's output (the fit card prompt in `create_fit_card` does not ask for a `$`) is where the gap is.
- **Search relevance is looser than my criteria measure.** For 'denim jacket under $30' the search returned shorts, a vest and jeans, because the keyword "denim" matches on its own. Criterion 5 only checks price, so it passed. Earlier, 'graphic tee' ranked a mesh top above real graphic tees, because every match tied on score and the cheaper one won. Tool: `search_listings`. Mechanism: ranking by plain keyword overlap with ties broken by price.
- **Criterion 3 is solid but its evidence is indirect.** The trace prints title, price and platform, not the id, so the check compares those, not the literal `id`.



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

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

**Empty search**

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

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->
I registered `search_listings` in `mcp_server.py` with a description written for a reader who can't see the code (types, units, and the empty case) and swapped the direct call in `agent.py::run_agent` for `mcp_client.call_tool`. The result was the same: the matching query returned the same top item as before, and the empty query still returned `[]`. The only visible change is the trace label, `search_listings (via MCP)`, and each call is slower because the server starts and stops on every call.


---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**
In `tools.py::create_fit_card`, I added one sentence to the end of the prompt: "Write the price with a dollar sign and digits, like $18, never in words." Nothing else changed in the code. The "after" run used the same scenarios, the same agent, and caching off.

**Which failure it was meant to fix:**
Criterion 4. My criterion said the fit card "includes the price", and it passed 5 of 5 before the change, but every card wrote the price in words ("eighteen dollars", "18 dollars") and none used a `$` sign. That is a model-output problem: the `create_fit_card` prompt never said how to write the price, so the model chose words. A stricter check for a dollar sign would have failed 5 of 5, so this was the weakest point in my results.

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
<!-- | 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  | -->
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Item in session matches item passed on | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card is 1 to 3 sentences and includes the price | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Price ceiling respected | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->
Yes, but the table doesn't show it. Every criterion was MET 5 of 5 before and after, because criterion 4 as I wrote it ("includes the price") was already passing with the price in words. The change shows up in a stricter check on the same fit cards: before, 0 of 5 cards contained a `$` sign and 5 of 5 spelled the price out; after, 5 of 5 contain a `$` sign and 0 of 5 use words. I counted this with `check_compare.py` on the saved results files (`results/run_2026-10-10_1249_before.md` and `results/run_2026-10-10_1305_after.md`). Sentence counts stayed at 2 or 3 per card, so the change didn't break the length limit. The sample is small (5 cards from one item), and the model's output varies, so I can't promise 5 of 5 on every item. What the run does show is that adding one sentence to the prompt moved the price format from 0 of 5 to 5 of 5.

This also means criterion 4 was worded too loosely. If I revised it, the new version would say "includes the price written with a $ sign", because that is something I can score.


---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
