import os
import re

class VegProcessor:
    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        vocab_path = os.path.join(base_dir, 'veg_vocab_ta.txt')
        with open(vocab_path, encoding='utf-8') as f:
            self.vocab = set(line.strip().lower() for line in f if line.strip())
        # Add English names for demo (expand as needed)
        self.english_vocab = {
            "grasa kana": "Grasa Kana",
            "கிராசே கானா": "Grasa Kana",
            "egg": "Egg",
            "முட்டை": "Egg",
            "oil": "Oil",
            "எண்ணெய்": "Oil",
            "brinjal": "Brinjal (Eggplant)",
            "eggplant": "Brinjal (Eggplant)",
            "கத்தரிக்காய்": "Brinjal (Eggplant)",
            "onion": "Onion",
            "வெங்காயம்": "Onion",
            "tomato": "Tomato",
            "தக்காளி": "Tomato"
        }

    def extract_grocery_items(self, text):
        print("[VegProcessor] Called extract_grocery_items")
        items = []
        text_lower = text.lower()
        print(f"[VegProcessor] Input text: {text_lower}")

        # Patterns for quantity and unit
        qty_unit_patterns = [
            (r'(\d+)\s*(packets?)', "packets"),
            (r'(\d+)\s*(trays?)', "tray"),
            (r'(\d+)\s*(liters?|l)', "liter"),
            (r'(\d+)\s*(kg|kilograms?)', "kg"),
        ]

        all_words = list(self.vocab) + list(self.english_vocab.keys())
        print(f"[VegProcessor] Checking words: {all_words}")
        for word in all_words:
            print(f"[VegProcessor] Checking word: {word}")
            if word in text_lower:
                print(f"[VegProcessor] Found word in text: {word}")
                # Default values
                quantity = "1"
                unit = ""
                # Try to find quantity/unit near the word
                context_window = 30
                for match in re.finditer(re.escape(word), text_lower):
                    start = max(0, match.start() - context_window)
                    end = match.end() + context_window
                    context = text_lower[start:end]
                    print(f"[VegProcessor] Context for '{word}': {context}")
                    for pat, default_unit in qty_unit_patterns:
                        m = re.search(pat, context)
                        if m:
                            quantity = m.group(1)
                            unit = default_unit
                            print(f"[VegProcessor] Found quantity/unit for '{word}': {quantity} {unit}")
                            break
                    break  # Only first occurrence per word

                # Normalize name for output
                name = self.english_vocab.get(word, word)
                print(f"[VegProcessor] Adding item: {name.title()}, {quantity}, {unit}")
                items.append({
                    "name": name.title(),
                    "quantity": quantity,
                    "unit": unit,
                    "confidence": 0.9,
                    "instructions": ""
                })
        print(f"[VegProcessor] Final items: {items}")
        return items 