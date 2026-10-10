from agent import run_agent
from utils.data_loader import get_example_wardrobe
import config

config.CACHE_ENABLED = False

for i in range(1, 6):
    session = run_agent("denim jacket under $30", get_example_wardrobe())
    prices = [item["price"] for item in session["search_results"]]
    over = [p for p in prices if p > 30]
    print(f"TRY {i} | results: {len(prices)} | prices: {prices} | over $30: {over}")