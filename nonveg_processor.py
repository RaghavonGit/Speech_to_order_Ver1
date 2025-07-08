import os
import re

class NonVegProcessor:
    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        vocab_path = os.path.join(base_dir, 'nonveg_vocab_ta.txt')
        with open(vocab_path, encoding='utf-8') as f:
            self.vocab = set(line.strip() for line in f if line.strip())

    def extract_grocery_items(self, text):
        text_lower = text.lower()
        items = []

        # Chicken
        if "சிக்கன்" in text_lower:
            instructions = []
            if "போன்ல" in text_lower or "boneless" in text_lower:
                instructions.append("boneless")
            if "ஸ்கின்" in text_lower or "remove skin" in text_lower or "no skin" in text_lower:
                instructions.append("no skin")
            if "பிளட்ஸ்" in text_lower or "blood" in text_lower or "no blood" in text_lower:
                instructions.append("no blood")
            items.append({
                "name": "சிக்கன்",
                "quantity": "1",
                "unit": "kg",
                "instructions": ", ".join(instructions)
            })

        # Mutton
        if "மட்டன்" in text_lower:
            instructions = []
            if "செஸ்ட் பீசா" in text_lower or "chest piece" in text_lower:
                instructions.append("chest piece")
            items.append({
                "name": "மட்டன்",
                "quantity": "0.5",
                "unit": "kg",
                "instructions": ", ".join(instructions)
            })

        # Leg
        if "கால்" in text_lower or "leg" in text_lower:
            items.append({
                "name": "கால்",
                "quantity": "1",
                "unit": "pcs",
                "instructions": "leg"
            })

        # Brain
        if "பிரைன்" in text_lower or "brain" in text_lower:
            items.append({
                "name": "பிரைன்",
                "quantity": "1",
                "unit": "pcs",
                "instructions": "brain"
            })

        # Liver
        if "ஈரல்" in text_lower or "liver" in text_lower:
            items.append({
                "name": "ஈரல்",
                "quantity": "1",
                "unit": "pcs",
                "instructions": "liver"
            })

        # சுவரொட்டி
        if "சுவரொட்டி" in text_lower:
            items.append({
                "name": "சுவரொட்டி",
                "quantity": "1",
                "unit": "pcs",
                "instructions": ""
            })

        return items 