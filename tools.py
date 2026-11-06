"""
The FitFindr tools.

Each one is a standalone function that can be called and tested on its own.

    search_listings(description, size, max_price)  -> list[dict]
    suggest_outfit(new_item, wardrobe)             -> str
    create_fit_card(outfit, new_item)              -> str
    compare_prices(item)                           -> dict   (stretch)
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings


# ── Helpers ───────────────────────────────────────────────────────────

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

    This tool does not call the model. It is served over MCP (see mcp_server.py).

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Matched as a whole token, case-insensitively, so "M" matches
                     "S/M" but "S" does not match "US 9" and "L" does not match
                     "XL".
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    `brand` is None for most listings.
    """
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

    Calls the model through `generate()`.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions. With an empty wardrobe it
        returns general styling advice instead of raising or returning "".
    """
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

    Calls the model through `generate()`.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption is meant to read like a real post and mention the item, its
    price and its platform once each. Output varies between runs unless
    CACHE_ENABLED is on or TEMPERATURE is 0.0 in config.py.
    """
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
        "marks around the caption. Write the price with a dollar sign and "
        "digits, like $18, never in words.\n\n"
        + "\n".join(details)
        + f"\n\nOutfit idea:\n{outfit_text}"
    )
    return generate(prompt).strip()


# ── Tool 4 (stretch): compare_prices ──────────────────────────────────────────

def compare_prices(item: dict) -> dict:
    """
    Compare an item's price with the average of the other listings in the same
    category. No model call.

    Returns a dict with: category (str), average (float or None), count (int),
    difference (float or None, item price minus average), verdict (str).
    With nothing to compare against, average and difference are None, count is
    0, and verdict says so.
    """
    others = [
        l for l in load_listings()
        if l["category"] == item["category"] and l["id"] != item["id"]
    ]
    if not others:
        return {
            "category": item["category"],
            "average": None,
            "count": 0,
            "difference": None,
            "verdict": "no other listings in this category to compare against",
        }

    average = sum(l["price"] for l in others) / len(others)
    difference = item["price"] - average
    if difference < -1:
        verdict = f"cheaper than the {item['category']} average"
    elif difference > 1:
        verdict = f"pricier than the {item['category']} average"
    else:
        verdict = f"about the {item['category']} average"

    return {
        "category": item["category"],
        "average": round(average, 2),
        "count": len(others),
        "difference": round(difference, 2),
        "verdict": verdict,
    }
