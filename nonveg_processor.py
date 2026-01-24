import re

class NonVegProcessor:
    def __init__(self):
        # ... (Keep your existing self.instruction_patterns dictionary here) ...
        self.instruction_patterns = {
            "boneless": [ r"போன்ல", r"bone\s*illa", r"boneless", r"எலும்பு\s*இல்ல" ],
            "with bone": [ r"எலும்போட", r"with\s*bone" ],
            "curry cut": [ r"கரி\s*கட்", r"curry\s*cut", r"medium\s*piece" ],
            "biryani cut": [ r"பிரியாணி\s*கட்", r"big\s*piece" ],
            "minced": [ r"கீமா", r"minced", r"கொத்துக்கறி" ],
            "skin removed": [ r"ஸ்கின்", r"skin", r"தோல்", r"remove" ],
            "cleaned": [ r"சுத்தம்", r"clean" ],
            "head removed": [ r"தலை\s*இல்ல", r"head\s*remove", r"headless" ],
        }

    def segment_text(self, text: str):
        segments = re.split(r'[,;]|\s+and\s+|\s+mattrum\s+', text)
        return [s.strip() for s in segments if s.strip()]

    def normalize_numbers(self, text: str) -> str:
        # Protect meat body-part words
        protected_phrases = ["ஆட்டுக்கால்", "கால் ஆடு", "கால் மட்டன்"]
        for p in protected_phrases:
            text = text.replace(p, p.replace("கால்", "__LEG__"))

        text = re.sub(r'ஒரு\s+ஆஃப்\s+கே\s*ஜி', '0.5 kg', text)
        text = re.sub(r'ஒரு\s+ஹாஃப்\s+கே\s*ஜி', '0.5 kg', text)
        text = re.sub(r'ஒரு\s+அரை\s+கிலோ', '0.5 kg', text)
        number_map = {
            "ondru": "1", "onnu": "1", "oru": "1", "one": "1", "ஒரு": "1", "ஒன்னு": "1",
            "rendu": "2", "two": "2", "irandu": "2", "ரெண்டு": "2", "இரண்டு": "2",
            "moonu": "3", "three": "3", "மூன்று": "3", "மூணு": "3",
            "naalu": "4", "four": "4", "நான்கு": "4", "நாலு": "4",
            "anju": "5", "five": "5", "aindhu": "5", "ஐந்து": "5", "அஞ்சு": "5",
            "arai": "0.5", "half": "0.5", "அரை": "0.5",
            "kaal": "0.25", "quarter": "0.25", "கால்": "0.25",
            "mukaal": "0.75", "three fourth": "0.75", "முக்கால்": "0.75",
            "ஆஃப்": "0.5", "ஹாஃப்": "0.5",
        }
        words = text.split()
        for i, word in enumerate(words):
            if word in number_map:
                words[i] = number_map[word]
        return " ".join(words)

    def extract_instructions(self, text: str):
        instructions = []
        for instr, patterns in self.instruction_patterns.items():
            for pat in patterns:
                if re.search(pat, text):
                    instructions.append(instr)
                    break
        return list(dict.fromkeys(instructions))

    def extract_grocery_items(self, text):
        text = text.lower()
        text = self.normalize_numbers(text)


        unit_map = {
            "kg": "kg", "kilogram": "kg", "kilo": "kg", "கிலோ": "kg","கே ஜி": "kg",
            "gram": "g", "g": "g", "gm": "g", "கிராம்": "g",
            "piece": "pieces", "pieces": "pieces", "pcs": "pieces", "பீஸ்": "pieces","tray": "tray",
            "trays": "tray",
            "ட்ரே": "tray",
            "ட்ரேய்": "tray"

        }

        # 1. FIND QUANTITIES
        qty_pattern = r'(\d+(?:\.\d+)?)\s*(kg|kilogram|kilo|gram|g|gm|piece|pieces|pcs|tray|trays|ட்ரே|ட்\s*ரே|ட்ரேய்|ட\s*ரே)'
        quantities = []
        for m in re.finditer(qty_pattern, text):
            raw_unit = m.group(2)
            quantities.append({
                "qty": m.group(1),
                "unit": unit_map.get(raw_unit, raw_unit),
                "start": m.start(),
                "end": m.end()
            })
            
        # 2. FIND MEAT ITEMS
        meat_vocab = {
            "சிக்கன்": "Chicken", "chicken": "Chicken", "கோழி": "Chicken",
            "மட்டன்": "Mutton", "mutton": "Mutton", "ஆடு": "Mutton",
            "மீன்": "Fish", "fish": "Fish",
            "இறால்": "Prawn", "prawn": "Prawn",
            "நண்டு": "Crab", "crab": "Crab",
            "முட்டை": "Egg", "egg": "Egg",
            "brain": "Brain",
            "பிரைன்": "Brain",
            "leg": "Leg",
            "கால்": "Leg",    
            "liver": "Liver",
            "ஈரல்": "Liver"

        }
        
        found_items = []
        for local, name in meat_vocab.items():
            for m in re.finditer(re.escape(local), text):
                found_items.append({
                    "name": name,
                    "local_name": local,
                    "start": m.start(),
                    "end": m.end()
                })
        
        # Remove overlaps
        found_items.sort(key=lambda x: len(x['local_name']), reverse=True)
        final_items_list = []
        covered_indices = set()
        for item in found_items:
            indices = set(range(item['start'], item['end']))
            if not indices.intersection(covered_indices):
                final_items_list.append(item)
                covered_indices.update(indices)
        final_items_list.sort(key=lambda x: x['start'])

        # 3. MATCH PROXIMITY
        results = []
        for item in final_items_list:
            window = text[max(0, item['start']-20):item['end']+20]
            instructions = self.extract_instructions(window)
            best_qty = "1"
            best_unit = ""
            if best_unit == "tray" and not best_qty:
                best_qty = "1"
            if not quantities:
                best_qty = "1"
            
            min_dist = float('inf')
            for q in quantities:
                dist_before = abs(item['start'] - q['end'])
                dist_after = abs(q['start'] - item['end'])
                current_dist = min(dist_before, dist_after)
                
                if current_dist < min_dist and current_dist < 12 and q['unit'] in ['kg', 'g', 'pieces', 'tray']:
                    min_dist = current_dist
                    best_qty = q['qty']
                    best_unit = q['unit']
            m = re.search(r'\b(0\.5|0\.25|0\.75)\b',window)
            if m:
                best_qty = m.group(1)
                best_unit = 'kg'
            
            # Default overrides
            if item['name'] in ['Egg', 'Crab', 'Leg', 'Head']:
                if best_unit == 'kg': best_unit = 'pieces'
            elif item['name'] == 'Egg':
                best_unit="tray"
            # --- FIX: Prevent "கால்" from becoming 0.25 for leg items ---
            elif item['name'] in ("leg", "goat leg", "mutton leg", "ஆட்டுக்கால்"):
                best_qty = "1"
                best_unit = "pieces"

            elif item['name'] == 'Mutton' and best_qty == '1':
                # Custom logic: Default mutton often implies 0.5kg if ambiguous? 
                # Keeping 1kg for consistency unless specifically handled
                pass
            if not best_unit:
                if item['name'] == 'Egg':
                    best_unit = 'tray'
                elif item['name'] in ['Leg', 'Brain', 'Liver']:
                    best_unit = 'pieces'
                else:
                    best_unit = 'kg'
            if best_qty in ["0.5", "0.25", "0.75"] and not best_unit:
                best_unit = "kg"
            results.append({
                "name": item["name"],
                "quantity": best_qty,
                "unit": best_unit,
                "confidence": 0.9,
                "instructions": instructions.copy(),
                "category": "meat"
            })
            window = text[max(0, item['start']-15):item['end']+15]            
            # --- APPLY DEFAULT UNIT IF STILL EMPTY ---
        return results