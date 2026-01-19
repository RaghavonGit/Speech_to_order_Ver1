#!/usr/bin/env python3
"""
Tamil Language Processor
Handles Tamil language grocery orders
"""

from base_processor import BaseLanguageProcessor, GroceryItem
from typing import Dict, List, Optional
import re

class TamilProcessor(BaseLanguageProcessor):
    """
    Tamil language processor for grocery orders
    """
    
    def __init__(self):
        super().__init__("tamil")
    
    def load_vocabulary(self) -> Dict[str, str]:
        """
        Load Tamil grocery vocabulary
        """
        vocabulary = {
            # Vegetables
            'தக்காளி': 'tomato',
            'வெங்காயம்': 'onion',
            'பூண்டு': 'garlic',
            'இஞ்சி': 'ginger',
            'கத்தரிக்காய்': 'brinjal',
            'அவரை': 'beans',
            'கேரட்': 'carrot',
            'உருளைக்கிழங்கு': 'potato',
            'காலிஃப்ளவர்': 'cauliflower',
            'முட்டைகோஸ்': 'cabbage',
            'பீர்க்கங்காய்': 'ridge gourd',
            'பூசணிக்காய்': 'pumpkin',
            'வெண்டைக்காய்': 'okra',
            'கீரை': 'spinach',
            'மிளகாய்': 'chili',
            'கருவேப்பிலை': 'curry leaves',
            'கொத்தமல்லி': 'coriander',
            'புதினா': 'mint',
            
            # Fruits
            'ஆப்பிள்': 'apple',
            'வாழைப்பழம்': 'banana',
            'ஆரஞ்சு': 'orange',
            'திராட்சை': 'grapes',
            'மாம்பழம்': 'mango',
            'பப்பாளி': 'papaya',
            'அன்னாசிப்பழம்': 'pineapple',
            'எலுமிச்சை': 'lemon',
            'நெல்லிக்காய்': 'gooseberry',
            'மாதுளை': 'pomegranate',
            
            # Grains & Pulses
            'அரிசி': 'rice',
            'கோதுமை': 'wheat',
            'துவரம்பருப்பு': 'toor dal',
            'பயறு': 'moong dal',
            'உளுந்து': 'urad dal',
            'கடலைப்பருப்பு': 'chana dal',
            'அவல்': 'poha',
            'ரவை': 'semolina',
            'பெருஞ்சீரகம்': 'fennel',
            'மிளகு': 'pepper',
            'சீரகம்': 'cumin',
            'மஞ்சள்': 'turmeric',
            'கொத்தமல்லி விதை': 'coriander seeds',
            
            # Dairy & Proteins
            'பால்': 'milk',
            'தயிர்': 'yogurt',
            'வெண்ணெய்': 'butter',
            'நெய்': 'ghee',
            'பன்னீர்': 'paneer',
            'முட்டை': 'egg',
            'கோழி': 'chicken',
            'மீன்': 'fish',
            'இறைச்சி': 'meat',
            
            # Groceries
            'உப்பு': 'salt',
            'சர்க்கரை': 'sugar',
            'எண்ணெய்': 'oil',
            'டீ': 'tea',
            'காபி': 'coffee',
            'பிஸ்கட்': 'biscuit',
            'ஜாம்': 'jam',
            'தேன்': 'honey',
            'உலர்ந்த திராட்சை': 'raisins',
            'பாதாம்': 'almonds',
            'முந்திரி': 'cashew',
            'பிஸ்தா': 'pistachios'
        }
        
        # Load additional vocabulary from JSON if available
        json_vocab = self.load_json_data("vocabulary.json")
        vocabulary.update(json_vocab)
        
        return vocabulary
    
    def load_units_mapping(self) -> Dict[str, str]:
        """
        Load Tamil units mapping
        """
        units = {
            'கிலோ': 'kg',
            'கிலோகிராம்': 'kg',
            'கிராம்': 'gram',
            'லிட்டர்': 'liter',
            'பாக்கெட்': 'packet',
            'பொட்டலம்': 'packet',
            'எண்ணம்': 'piece',
            'துண்டு': 'piece',
            'டஜன்': 'dozen',
            'மூட்டை': 'bundle',
            'கட்டு': 'bundle',
            'கப்': 'cup',
            'தட்டு': 'plate',
            'பாத்திரம்': 'container',
            'பைப்பு': 'bag',
            'பையன்': 'small bag'
        }
        
        # Load additional units from JSON if available
        json_units = self.load_json_data("units.json")
        units.update(json_units)
        
        return units
    
    def load_numbers_mapping(self) -> Dict[str, str]:
        """
        Load Tamil numbers mapping
        """
        numbers = {
            'ஒன்று': '1',
            'இரண்டு': '2',
            'மூன்று': '3',
            'நான்கு': '4',
            'ஐந்து': '5',
            'ஆறு': '6',
            'ஏழு': '7',
            'எட்டு': '8',
            'ஒன்பது': '9',
            'பத்து': '10',
            'பதினொன்று': '11',
            'பன்னிரண்டு': '12',
            'பதிமூன்று': '13',
            'பதினான்கு': '14',
            'பதினைந்து': '15',
            'பதினாறு': '16',
            'பதினேழு': '17',
            'பதினெட்டு': '18',
            'பத்தொன்பது': '19',
            'இருபது': '20',
            'இருபத்தொன்று': '21',
            'முப்பது': '30',
            'நாற்பது': '40',
            'ஐம்பது': '50',
            'அறுபது': '60',
            'எழுபது': '70',
            'எண்பது': '80',
            'தொண்ணூறு': '90',
            'நூறு': '100',
            'ஆயிரம்': '1000',
            'அரை': '0.5',
            'கால்': '0.25',
            'முக்கால்': '0.75',
            'அரைக்கிலோ': '0.5',
            'கால்கிலோ': '0.25',
            'முக்கால்கிலோ': '0.75'
        }
        
        # Load additional numbers from JSON if available
        json_numbers = self.load_json_data("numbers.json")
        numbers.update(json_numbers)
        
        return numbers
    
    def detect_language_confidence(self, text: str) -> float:
        """
        Calculate confidence score for Tamil language detection
        """
        # Tamil Unicode range
        tamil_chars = set()
        for char in text:
            if '\u0B80' <= char <= '\u0BFF':  # Tamil Unicode block
                tamil_chars.add(char)
        
        # Calculate confidence based on Tamil characters
        total_chars = len([c for c in text if c.isalpha()])
        if total_chars == 0:
            return 0.0
        
        tamil_ratio = len(tamil_chars) / total_chars
        
        # Boost confidence if Tamil-specific words are found
        tamil_indicators = ['என்னும்', 'வேண்டும்', 'இருக்கும்', 'தருகிறேன்', 'தக்காளி', 'வெங்காயம்', 'அரிசி']
        indicator_count = sum(1 for indicator in tamil_indicators if indicator in text)
        
        # Final confidence calculation
        confidence = tamil_ratio * 0.7 + (indicator_count / len(tamil_indicators)) * 0.3
        
        return min(confidence, 1.0)
    
    def segment_text(self, text: str) -> List[str]:
        """
        Tamil-specific text segmentation
        """
        # Tamil-specific separators
        separators = [',', 'மற்றும்', 'மேலும்', 'வேறு', 'இன்னும்', 'கூடுதலாக', 'and', 'also']
        
        # Create regex pattern for separators
        separator_pattern = '|'.join(re.escape(sep) for sep in separators)
        
        # Split text
        segments = re.split(separator_pattern, text, flags=re.IGNORECASE)
        
        # Clean and filter segments
        cleaned_segments = [seg.strip() for seg in segments if seg.strip()]
        
        return cleaned_segments
    
    def normalize_text(self, text: str) -> str:
        """
        Tamil-specific text normalization
        """
        # Base normalization
        text = super().normalize_text(text)
        
        # Tamil-specific normalization
        # Remove common Tamil particles and suffixes that don't affect meaning
        text = re.sub(r'(ஐ|ஆ|அ|ன்|ம்|ய்|ர்|ல்|ன)$', '', text)
        
        # Normalize common variations
        text = text.replace('க்', 'க')
        text = text.replace('ங்', 'ங')
        
        return text
    
    def find_grocery_item_in_text(self, text: str) -> Optional[str]:
        """
        Tamil-specific grocery item finding with fuzzy matching
        """
        # First try exact matching
        result = super().find_grocery_item_in_text(text)
        if result:
            return result
        
        # Tamil-specific fuzzy matching
        words = text.split()
        
        for local_name, english_name in self.vocabulary.items():
            # Check if any word contains the Tamil grocery name
            for word in words:
                # Remove common Tamil suffixes for better matching
                clean_word = re.sub(r'(ஐ|ஆ|அ|ன்|ம்|ய்|ர்|ல்|ன)$', '', word)
                clean_local = re.sub(r'(ஐ|ஆ|அ|ன்|ம்|ய்|ர்|ல்|ன)$', '', local_name)
                
                if clean_local in clean_word or clean_word in clean_local:
                    return english_name
                
                # Check for partial matches (at least 70% similarity)
                if len(clean_local) > 3 and len(clean_word) > 3:
                    common_chars = set(clean_local) & set(clean_word)
                    similarity = len(common_chars) / max(len(set(clean_local)), len(set(clean_word)))
                    if similarity >= 0.7:
                        return english_name
        
        return None