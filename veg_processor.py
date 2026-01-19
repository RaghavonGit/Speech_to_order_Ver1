import re

class VegProcessor:
    def __init__(self):
        # ... (Keep your existing self.vocab dictionary here) ...
        # For brevity, I am not pasting the huge vocab again, 
        # BUT YOU MUST KEEP YOUR FULL VOCAB LIST HERE from the previous file.
        self.vocab = {
            "கத்தரிக்காய்": "Brinjal", "eggplant": "Brinjal", "brinjal": "Brinjal",
            "வெங்காயம்": "Onion", "onion": "Onion", "vengayam": "Onion",
            "தக்காளி": "Tomato", "tomato": "Tomato", "thakkali": "Tomato",
            "உருளைக்கிழங்கு": "Potato", "potato": "Potato", "urulai": "Potato",
            "கேரட்": "Carrot", "carrot": "Carrot",
            "முருங்கைக்காய்": "Drumstick", "drumstick": "Drumstick", 
            "வெண்டைக்காய்": "Okra", "okra": "Okra", "ladies finger": "Okra",
            "பீன்ஸ்": "Beans", "beans": "Beans",
            "பச்சை மிளகாய்": "Green Chilli", "green chilli": "Green Chilli",
            "தேங்காய்": "Coconut", "coconut": "Coconut",
            "எலுமிச்சை": "Lemon", "lemon": "Lemon",
            "கீரை": "Spinach", "spinach": "Spinach", "keerai": "Spinach",
            "கொத்தமல்லி": "Coriander Leaves", "coriander": "Coriander Leaves",
            "கருவேப்பிலை": "Curry Leaves", "curry leaves": "Curry Leaves",
            "புதினா": "Mint", "mint": "Mint",
            "வாழைப்பழம்": "Banana", "banana": "Banana",
            "ஆப்பிள்": "Apple", "apple": "Apple",
            "பால்": "Milk", "milk": "Milk", "paal": "Milk",
            "தயிர்": "Curd", "curd": "Curd", "thayir": "Curd",
            "எண்ணெய்": "Oil", "oil": "Oil", "ennai": "Oil", "enna": "Oil",
            "சன்பிளவர் ஆயில்": "Sunflower Oil", "sunflower oil": "Sunflower Oil",
            "நல்லெண்ணெய்": "Sesame Oil", "gingelly oil": "Sesame Oil",
            "கடலை எண்ணெய்": "Groundnut Oil", "peanut oil": "Groundnut Oil",
            # ... ADD ALL OTHER ITEMS FROM YOUR PREVIOUS FILE ...
            "சர்க்கரை": "Sugar", "sugar": "Sugar",
            "உப்பு": "Salt", "salt": "Salt",
            "அரிசி": "Rice", "rice": "Rice"
        }

        self.liquid_items = {
            "Milk", "Curd", "Oil", "Coconut Oil", "Sunflower Oil", "Sesame Oil", "Groundnut Oil", "Ghee", "Castor Oil", "Dish Soap"
        }

    def segment_text(self, text: str):
        segments = re.split(r'[,;]|\s+and\s+|\s+mattrum\s+', text)
        return [s.strip() for s in segments if s.strip()]

    def normalize_numbers(self, text: str) -> str:
        number_map = {
            "ondru": "1", "onnu": "1", "oru": "1", "one": "1", "ஒரு": "1", "ஒன்னு": "1",
            "rendu": "2", "two": "2", "irandu": "2", "ரெண்டு": "2", "இரண்டு": "2",
            "moonu": "3", "three": "3", "மூன்று": "3", "மூணு": "3",
            "naalu": "4", "four": "4", "நான்கு": "4", "நாலு": "4",
            "anju": "5", "five": "5", "aindhu": "5", "ஐந்து": "5", "அஞ்சு": "5",
            "aaru": "6", "six": "6", "ஆறு": "6",
            "ezhu": "7", "seven": "7", "ஏழு": "7",
            "ettu": "8", "eight": "8", "எட்டு": "8",
            "onbathu": "9", "nine": "9", "ஒன்பது": "9",
            "pathu": "10", "ten": "10", "pattu": "10", "பத்து": "10",
            "arai": "0.5", "half": "0.5", "அரை": "0.5",
            "kaal": "0.25", "quarter": "0.25", "கால்": "0.25",
            "mukaal": "0.75", "three fourth": "0.75", "முக்கால்": "0.75"
        }
        words = text.split()
        for i, word in enumerate(words):
            if word in number_map:
                words[i] = number_map[word]
        return " ".join(words)

    def extract_grocery_items(self, text):
        text = text.lower() if text.isascii() else text
        text = self.normalize_numbers(text)
        
        unit_map = {
            "kg": "kg", "kilogram": "kg", "kilo": "kg", "கிலோ": "kg",
            "gram": "g", "g": "g", "gm": "g", "கிராம்": "g",
            "liter": "liter", "litre": "liter", "l": "liter", "லிட்டர்": "liter",
            "ml": "ml", "milli": "ml",
            "packet": "packets", "packets": "packets", "pkt": "packets", "பாக்கெட்": "packets",
            "piece": "pieces", "pieces": "pieces", "pcs": "pieces", "பீஸ்": "pieces",
            "bunch": "bunch", "bunches": "bunch", "kattu": "bunch", "கட்டு": "bunch",
            "tray": "tray", "ட்ரே": "tray",
            "dozen": "dozen", "டஜன்": "dozen"
        }

        # 1. FIND ALL QUANTITIES (with positions)
        qty_pattern = r'(\d+(?:\.\d+)?)\s*(kg|kilogram|kilo|gram|g|gm|liter|litre|l|ml|milli|packet|packets|pkt|piece|pieces|pcs|bunch|bunches|kattu|dozen|tray|கிலோ|லிட்டர்|கிராம்|பாக்கெட்|பீஸ்|கட்டு|டஜன்|ட்ரே)'
        
        quantities = []
        for m in re.finditer(qty_pattern, text):
            raw_unit = m.group(2)
            quantities.append({
                "qty": m.group(1),
                "unit": unit_map.get(raw_unit, raw_unit),
                "start": m.start(),
                "end": m.end()
            })

        # 2. FIND ALL ITEMS (with positions)
        found_items = []
        for local, name in self.vocab.items():
            # Use regex to find all occurrences of the item name
            for m in re.finditer(re.escape(local), text):
                # Avoid sub-word matches (e.g. matching 'pot' in 'potato') 
                # strictly speaking, but for now simple find is robust enough for Tamil/English mix
                found_items.append({
                    "name": name,
                    "local_name": local,
                    "start": m.start(),
                    "end": m.end()
                })

        # Remove duplicate overlaps (e.g. 'small onion' and 'onion')
        # Sort by length desc, keep longest match covering an index
        found_items.sort(key=lambda x: len(x['local_name']), reverse=True)
        final_items_list = []
        covered_indices = set()
        
        for item in found_items:
            # Check if this index range is already covered by a longer word
            indices = set(range(item['start'], item['end']))
            if not indices.intersection(covered_indices):
                final_items_list.append(item)
                covered_indices.update(indices)

        # Sort items by position in text
        final_items_list.sort(key=lambda x: x['start'])

        # 3. MATCH ITEMS TO NEAREST QUANTITY
        results = []
        for item in final_items_list:
            best_qty = "1"
            best_unit = ""
            
            # Find nearest quantity (look backwards and forwards)
            min_dist = float('inf')
            
            for q in quantities:
                # Dist from end of qty to start of item (qty before item: "1kg tomato")
                dist_before = abs(item['start'] - q['end'])
                # Dist from end of item to start of qty (item before qty: "tomato 1kg")
                dist_after = abs(q['start'] - item['end'])
                
                # Check closest distance, typically within 15 characters
                current_dist = min(dist_before, dist_after)
                
                if current_dist < min_dist and current_dist < 12: # 25 char threshold
                    min_dist = current_dist
                    best_qty = q['qty']
                    best_unit = q['unit']

            # Default Units if none found
            if not best_unit:
                if item["name"] in self.liquid_items:
                    best_unit = "liter"
                # Add "Packet" logic for items usually sold in packets
                elif "Oil" in item["name"] or "Salt" in item["name"]:
                     best_unit = "liter" if "Oil" in item["name"] else "kg"
                elif item["name"] in ["Banana", "Apple", "Egg", "Lemon"]:
                    best_unit = "pieces"
                elif item["name"] in ["Spinach", "Coriander Leaves", "Mint"]:
                    best_unit = "bunch"
                else:
                    best_unit = "kg" # Default fallback

            results.append({
                "name": item["name"],
                "quantity": best_qty,
                "unit": best_unit,
                "confidence": 0.85 if best_unit else 0.7,
                "instructions": [],
                "category": "veg"
            })

        return results