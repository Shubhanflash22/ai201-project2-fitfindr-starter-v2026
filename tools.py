"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import re

import config  # noqa: F401 — you'll use this in search_listings
from generate import generate
from utils.data_loader import load_listings


# ── Helpers (added) ───────────────────────────────────────────────────────────

# Words that describe the request but say nothing about the item.
_STOPWORDS = {
    "a", "an", "the", "in", "on", "for", "of", "to", "and", "or", "with", "me",
    "my", "i", "want", "need", "looking", "find", "show", "some", "something",
    "under", "below", "over", "above", "than", "less", "max", "size", "sized",
    "dollar", "dollars", "price", "budget", "cheap",
}


def _tokens(text: str) -> list[str]:
    """Lowercase alphanumeric tokens, with a crude plural strip (tees -> tee)."""
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return [w[:-1] if len(w) > 3 and w.endswith("s") else w for w in words]


def _size_matches(wanted: str, listing_size: str) -> bool:
    """
    Whole-token size match. 'M' matches 'M' and 'S/M' but not 'XL (oversized)';
    'W30 L30' matches only listings carrying both W30 and L30. Never a substring
    test, so 's' does not match 'us 9' and 'l' does not match 'xl'.
    """
    wanted_tokens = set(re.findall(r"[a-z0-9]+", wanted.lower()))
    listing_tokens = set(re.findall(r"[a-z0-9]+", (listing_size or "").lower()))
    return bool(wanted_tokens) and wanted_tokens <= listing_tokens


def _money(price: float) -> str:
    """$18 for whole prices, $18.50 otherwise."""
    return f"${price:.0f}" if float(price).is_integer() else f"${price:.2f}"


def _describe_item(item: dict) -> str:
    """One line describing a listing, for use inside a prompt."""
    parts = [item["title"], f"{_money(item['price'])}", item["category"]]
    if item.get("colors"):
        parts.append("colors: " + ", ".join(item["colors"]))
    if item.get("style_tags"):
        parts.append("style: " + ", ".join(item["style_tags"]))
    return " | ".join(parts)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    # TODO: replace this with your implementation
    keywords = {w for w in _tokens(description) if w not in _STOPWORDS}
    if not keywords:
        return []

    scored = []
    for item in load_listings():
        if max_price is not None and item["price"] > max_price:
            continue
        if size and not _size_matches(size, item.get("size")):
            continue

        haystack = set(
            _tokens(
                " ".join(
                    [
                        item.get("title") or "",
                        item.get("description") or "",
                        item.get("category") or "",
                        " ".join(item.get("style_tags") or []),
                        " ".join(item.get("colors") or []),
                    ]
                )
            )
        )
        score = len(keywords & haystack)
        if score > 0:
            scored.append((score, item["price"], item))

    # Best match first; ties go to the cheaper listing.
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [item for _, _, item in scored[: config.SEARCH_RESULT_LIMIT]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    # TODO: replace this with your implementation
    items = (wardrobe or {}).get("items") or []
    item_text = _describe_item(new_item)

    if not items:
        prompt = (
            "You are a thrift-fashion stylist. The user is considering this "
            f"secondhand item:\n{item_text}\n\n"
            "They haven't told you what they own. Suggest two outfit ideas "
            "built around this item, using common closet staples. "
            "Be specific and concise. Plain text, no markdown headers."
        )
    else:
        lines = []
        for w in items:
            line = f"- {w['name']} ({w['category']}; {', '.join(w.get('colors') or [])})"
            if w.get("notes"):  # notes can be None — don't print "None"
                line += f" — {w['notes']}"
            lines.append(line)
        prompt = (
            "You are a thrift-fashion stylist. The user is considering this "
            f"secondhand item:\n{item_text}\n\n"
            "Their wardrobe:\n" + "\n".join(lines) + "\n\n"
            "Suggest two outfits that combine the new item with specific pieces "
            "from the wardrobe, naming those pieces exactly. Be concise. "
            "Plain text, no markdown headers."
        )

    return generate(prompt).strip()


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    # TODO: replace this with your implementation
    outfit_text = (outfit or "").strip() or (
        "(no outfit suggestion available — write from the item alone)"
    )

    details = [
        f"Item: {new_item['title']}",
        f"Price: {_money(new_item['price'])}",
        f"Platform: {new_item['platform']}",
    ]
    if new_item.get("brand"):  # brand is None on many listings
        details.append(f"Brand: {new_item['brand']}")

    prompt = (
        "Write a social-media caption for a thrift find. Sound like a real "
        "person posting, not a product description. Exactly two or three "
        "sentences. Mention the item, its price, and the platform once each, "
        "and be specific about the vibe. No hashtags, no emojis, no quotation "
        "marks around the caption.\n\n"
        + "\n".join(details)
        + f"\n\nOutfit idea:\n{outfit_text}"
    )
    return generate(prompt).strip()