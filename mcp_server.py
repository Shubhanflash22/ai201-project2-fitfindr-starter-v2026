"""
FitFindr MCP server.

Exposes search_listings over MCP so any MCP client can call it. Only this tool
is served. It does not call the model.

    python mcp_server.py        starts the server (it sits and waits for a client)
    python mcp_client.py        asks the server what it offers
"""

from mcp.server.fastmcp import FastMCP

from tools import search_listings as _search_listings_impl

# log_level="WARNING" keeps the server from printing an INFO line for every
# request. Without it your terminal fills with "Processing request of type
# CallToolRequest" and the output you actually care about scrolls away.
mcp = FastMCP("fitfindr", log_level="WARNING")


@mcp.tool()
def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search secondhand clothing listings by keywords, with an optional size and
    price ceiling. `description` is free-text keywords like "vintage graphic
    tee"; `size` is a size such as "M" (matched as a whole token, so "M" also
    matches "S/M"); `max_price` is the highest price in US dollars, inclusive.
    Returns a list of listing objects (id, title, description, category,
    style_tags, size, condition, price, colors, brand, platform), best match
    first, at most 10. Returns an empty list when nothing matches.
    """
    return _search_listings_impl(description, size, max_price)


if __name__ == "__main__":
    mcp.run()
