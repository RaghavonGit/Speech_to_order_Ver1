import re

class VegProcessor:
    def __init__(self):
        # EXPANDED VOCABULARY LIST
        self.vocab = {
            # --- OILS & LIQUIDS ---
            "எண்ணெய்": "Oil", "oil": "Oil", "ennai": "Oil", "enna": "Oil",
            "சன்பிளவர் ஆயில்": "Sunflower Oil", "sunflower oil": "Sunflower Oil",
            "நல்லெண்ணெய்": "Sesame Oil", "gingelly oil": "Sesame Oil",
            "கடலை எண்ணெய்": "Groundnut Oil", "peanut oil": "Groundnut Oil",
            "நெய்": "Ghee", "ghee": "Ghee",
            "பால்": "Milk", "milk": "Milk", "paal": "Milk",
            "தயிர்": "Curd", "curd": "Curd", "thayir": "Curd",
            "மோரு": "Buttermilk", "buttermilk": "Buttermilk",

            # --- VEGETABLES (Standard) ---
            "கத்தரிக்காய்": "Brinjal", "eggplant": "Brinjal", "brinjal": "Brinjal",
            "வெங்காயம்": "Onion", "onion": "Onion", "vengayam": "Onion", "big onion": "Onion",
            "சின்ன வெங்காயம்": "Small Onion", "small onion": "Small Onion", "shallots": "Small Onion", 
            "சாம்பார் வெங்காயம்": "Small Onion", "sambar vengayam": "Small Onion", "sambar onion": "Small Onion",
            "தக்காளி": "Tomato", "tomato": "Tomato", "thakkali": "Tomato", "thakali": "Tomato",

            "உருளைக்கிழங்கு": "Potato", "potato": "Potato", "urulai": "Potato", "urulaikizhangu": "Potato",
            "கேரட்": "Carrot", "carrot": "Carrot",
            "பீன்ஸ்": "Beans", "beans": "Beans",
            "பீட்ரூட்": "Beetroot", "beetroot": "Beetroot",
            "முள்ளங்கி": "Radish", "radish": "Radish", "mullangi": "Radish",
            "நூல்கோல்": "Knol Khol", "knol khol": "Knol Khol",
            "சௌசௌ": "Chow Chow", "chow chow": "Chow Chow",
            "கோவைக்காய்": "Ivy Gourd", "ivy gourd": "Ivy Gourd", "kovakkai": "Ivy Gourd",
            "புடலங்காய்": "Snake Gourd", "snake gourd": "Snake Gourd",
            "பாகற்காய்": "Bitter Gourd", "bitter gourd": "Bitter Gourd",
            "சுரைக்காய்": "Bottle Gourd", "bottle gourd": "Bottle Gourd",
            "பூசணிக்காய்": "Pumpkin", "pumpkin": "Pumpkin", "yellow pumpkin": "Pumpkin",
            "வெள்ளரிக்காய்": "Cucumber", "cucumber": "Cucumber",
            "குடைமிளகாய்": "Capsicum", "capsicum": "Capsicum",

            # --- VEGETABLES (Piece-based usually) ---
            "முருங்கைக்காய்": "Drumstick", "drumstick": "Drumstick", "murungakkai": "Drumstick",
            "வெண்டைக்காய்": "Okra", "okra": "Okra", "ladies finger": "Okra", "vendaikkai": "Okra", "vendakkai": "Okra",
            "வாழைக்காய்": "Raw Banana", "raw banana": "Raw Banana", "plantain": "Raw Banana",
            "எலுமிச்சை": "Lemon", "lemon": "Lemon",
            "தேங்காய்": "Coconut", "coconut": "Coconut", "thengai": "Coconut",
            "காலிஃபிளவர்": "Cauliflower", "cauliflower": "Cauliflower",
            "முட்டைக்கோஸ்": "Cabbage", "cabbage": "Cabbage",
            "மக்காச்சோளம்": "Corn", "corn": "Corn", "sweet corn": "Corn",

            # --- LEAFY GREENS (Bunches) ---
            "கீரை": "Spinach", "spinach": "Spinach", "keerai": "Spinach",
            "அரைக்கீரை": "Amaranthus", "siru keerai": "Amaranthus",
            "பாலக்": "Palak", "palak": "Palak",
            "முருங்கை இலை": "Drumstick Leaves", "murungai ilai": "Drumstick Leaves", "murungai keerai": "Drumstick Leaves",
            "கொத்தமல்லி": "Coriander Leaves", "coriander": "Coriander Leaves", "kothamalli": "Coriander Leaves",
            "கருவேப்பிலை": "Curry Leaves", "curry leaves": "Curry Leaves",
            "புதினா": "Mint", "mint": "Mint", "pudina": "Mint",
            "வெங்காயத் தாள்": "Spring Onion", "spring onion": "Spring Onion",

            # --- FRUITS (Pieces/Dozen/Kg) ---
            "வாழைப்பழம்": "Banana", "banana": "Banana", "vazhaipazham": "Banana",
            "ஆப்பிள்": "Apple", "apple": "Apple",
            "ஆரஞ்சு": "Orange", "orange": "Orange",
            "மாம்பழம்": "Mango", "mango": "Mango",
            "திராட்சை": "Grapes", "grapes": "Grapes",
            "மாதுளை": "Pomegranate", "pomegranate": "Pomegranate",
            "பப்பாளி": "Papaya", "papaya": "Papaya",
            "தர்பூசணி": "Watermelon", "watermelon": "Watermelon",
            "கொய்யா": "Guava", "guava": "Guava", "koyya": "Guava",
            "சப்போட்டா": "Sapota", "sapotta": "Sapota", "sapota": "Sapota", "chikoo": "Sapota",
            "சீதாப்பழம்": "Custard Apple", "seethapazham": "Custard Apple", "custard apple": "Custard Apple",
            "பேரிக்காய்": "Pear", "pear": "Pear",

            # --- SPICES & PANTRY (Packets/Grams) ---
            "பூண்டு": "Garlic", "garlic": "Garlic", "poondu": "Garlic",
            "இஞ்சி": "Ginger", "ginger": "Ginger", "inji": "Ginger",
            "பச்சை மிளகாய்": "Green Chilli", "green chilli": "Green Chilli",
            "காய்ந்த மிளகாய்": "Red Chilli", "red chilli": "Red Chilli", "dry chilli": "Red Chilli",
            "மிளகு": "Pepper", "pepper": "Pepper",
            "சீரகம்": "Cumin", "cumin": "Cumin", "jeera": "Cumin",
            "கடுகு": "Mustard", "mustard": "Mustard",
            "வெந்தயம்": "Fenugreek", "fenugreek": "Fenugreek",
            "மஞ்சள் தூள்": "Turmeric Powder", "turmeric": "Turmeric Powder",
            "மிளகாய் தூள்": "Chilli Powder", "chilli powder": "Chilli Powder",
            "மல்லி தூள்": "Coriander Powder", "coriander powder": "Coriander Powder",
            "பெருங்காயம்": "Asafoetida", "hing": "Asafoetida",
            "உப்பு": "Salt", "salt": "Salt",
            "சர்க்கரை": "Sugar", "sugar": "Sugar",
            "வெல்லம்": "Jaggery", "jaggery": "Jaggery",
            "அரிசி": "Rice", "rice": "Rice",
            "துவரம் பருப்பு": "Toor Dal", "toor dal": "Toor Dal",
            "உளுத்தம் பருப்பு": "Urad Dal", "urad dal": "Urad Dal",
            "கடலை பருப்பு": "Chana Dal", "chana dal": "Chana Dal",
            "பாசி பருப்பு": "Moong Dal", "moong dal": "Moong Dal",
            "ரவை": "Rava", "rava": "Rava", "semolina": "Rava",
            "கோதுமை மாவு": "Wheat Flour", "wheat flour": "Wheat Flour", "atta": "Wheat Flour",
            "மைதா": "Maida", "maida": "Maida",
            
            # --- OTHERS ---
            "முட்டை": "Egg", "egg": "Egg", "muttai": "Egg",
            "பிரட்": "Bread", "bread": "Bread",
            "பிஸ்கட்": "Biscuit", "biscuit": "Biscuit",
            "மேகி": "Maggi", "maggi": "Maggi", "noodles": "Maggi"
        }

        # Items that are always measured in Liquid units (L/ml)
        self.liquid_items = {
            "Milk", "Curd", "Buttermilk", "Oil", "Sunflower Oil", "Sesame Oil", 
            "Groundnut Oil", "Ghee", "Castor Oil", "Dish Soap"
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
                found_items.append({
                    "name": name,
                    "local_name": local,
                    "start": m.start(),
                    "end": m.end()
                })

        # Remove duplicate overlaps (e.g. 'small onion' and 'onion')
        found_items.sort(key=lambda x: len(x['local_name']), reverse=True)
        final_items_list = []
        covered_indices = set()
        
        for item in found_items:
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
                dist_before = abs(item['start'] - q['end'])
                dist_after = abs(q['start'] - item['end'])
                
                # Check closest distance
                current_dist = min(dist_before, dist_after)
                
                if current_dist < min_dist and current_dist < 12: # 12 char threshold
                    min_dist = current_dist
                    best_qty = q['qty']
                    best_unit = q['unit']

            # --- SMART DEFAULT UNIT LOGIC ---
            if not best_unit:
                name_lower = item["name"].lower()
                
                if item["name"] in self.liquid_items:
                    best_unit = "liter"
                
                # Items typically sold by piece
                elif item["name"] in ["Coconut", "Cauliflower", "Cabbage", "Pineapple", "Watermelon", 
                                      "Raw Banana", "Corn", "Egg", "Lemon", "Banana", "Apple", "Orange",
                                      "Drumstick", "Sapota", "Custard Apple", "Pear", "Guava"]:
                    best_unit = "pieces"
                elif item['name'] == 'Egg':
                    best_unit="tray"
                # Items typically sold by bunch
                elif item["name"] in ["Spinach", "Coriander Leaves", "Mint", "Curry Leaves", "Spring Onion", 
                                      "Amaranthus", "Palak", "Drumstick Leaves"]:
                    best_unit = "bunch"
                
                # Items typically sold by packet
                elif item["name"] in ["Salt", "Sugar", "Bread", "Biscuit", "Maggi", "Milk", "Curd", "Buttermilk"]:
                    best_unit = "packet" if item["name"] in ["Bread", "Biscuit", "Maggi"] else "liter"

                # Spices often bought in small grams
                elif item["name"] in ["Mustard", "Fenugreek", "Pepper", "Cumin", "Turmeric Powder", "Chilli Powder", "Asafoetida"]:
                    best_unit = "g" 

                else:
                    best_unit = "kg" # Default fallback for standard veg

            results.append({
                "name": item["name"],
                "quantity": best_qty,
                "unit": best_unit,
                "confidence": 0.85 if best_unit else 0.7,
                "instructions": [],
                "category": "veg"
            })

        return results