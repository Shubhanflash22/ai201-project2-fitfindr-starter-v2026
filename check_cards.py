import re
import glob

path = sorted(glob.glob("results/*before.md"))[-1]
text = open(path, encoding="utf-8").read()

section = text.split("### fit card length and price")[1].split("### price ceiling respected")[0]
cards = re.findall(r"Fit card:\s*\n\s*`{3}\n(.*?)\n`{3}", section, re.S)

print(f"File: {path}")
print(f"Found {len(cards)} fit cards\n")

for i, card in enumerate(cards, 1):
    sentences = len(re.findall(r"[.!?]", card))
    has_symbol = "$" in card
    has_words = any(w in card.lower() for w in ["dollar", "buck"])
    print(f"TRY {i} | sentence marks: {sentences} | $ sign: {has_symbol} | price in words: {has_words}")
    print(card)
    print()