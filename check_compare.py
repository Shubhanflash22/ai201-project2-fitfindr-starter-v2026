import re
import glob

def load_cards(label):
    path = sorted(glob.glob(f"results/*{label}.md"))[-1]
    text = open(path, encoding="utf-8").read()
    section = text.split("### fit card length and price")[1].split("### price ceiling respected")[0]
    return path, re.findall(r"Fit card:\s*\n\s*`{3}\n(.*?)\n`{3}", section, re.S)

for label in ("before", "after"):
    path, cards = load_cards(label)
    print(f"=== {label.upper()} ({path}) | {len(cards)} cards ===")
    for i, card in enumerate(cards, 1):
        sentences = len(re.findall(r"[.!?]", card))
        has_symbol = "$" in card
        has_words = any(w in card.lower() for w in ["dollar", "buck"])
        print(f"TRY {i} | sentence marks: {sentences} | $ sign: {has_symbol} | price in words: {has_words}")
        print(card)
        print()